import random
import re
import string
import unicodedata
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl, Field
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.ad import Ad
from app.models.ad_compatibility import AdCompatibility
from app.models.click import ClickEvent
from app.models.user import User
from app.models.vehicle import Manufacturer, VehicleModel
from app.models.community import Community
from app.models.rating import AdRating
from app.routes.api.auth import get_current_user
from app.utils.activity import log_activity

PLAN_LIMITS = {
    "free": 3,
    "smart": 5,
    "pro": 50,
    "premium": 999999,
}

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def generate_short_code() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=5))


def parse_optional_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="expires_at inválido") from exc


def validate_vehicle_payload(data: "AdSchema", db: Session):
    current_year = datetime.utcnow().year + 1
    if data.is_universal:
        return None, None, None, None, None

    y_start = data.year_start
    y_end = data.year_end
    eng = data.engine

    # Tenta obter IDs da raiz ou da primeira compatibilidade
    m_id = data.manufacturer_id
    md_id = data.model_id
    
    if (not m_id or not md_id) and data.compatibilities and len(data.compatibilities) > 0:
        first = data.compatibilities[0]
        if not m_id: m_id = first.manufacturer_id
        if not md_id: md_id = first.model_id
        if y_start is None: y_start = first.year_start
        if y_end is None: y_end = first.year_end
        if eng is None: eng = first.engine

    if not m_id or not md_id:
        raise HTTPException(
            status_code=422,
            detail="Produtos compatíveis exigem manufacturer_id e model_id (ou lista de compatibilidades).",
        )

    manufacturer = db.query(Manufacturer).filter(Manufacturer.id == m_id).first()
    if not manufacturer:
        raise HTTPException(status_code=404, detail="Montadora não encontrada.")

    model = db.query(VehicleModel).filter(VehicleModel.id == md_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Modelo não encontrado.")

    if str(model.manufacturer_id) != str(m_id):
        raise HTTPException(
            status_code=422,
            detail="O modelo informado não pertence à montadora selecionada.",
        )


    if y_start and (y_start < 1900 or y_start > current_year):
        raise HTTPException(status_code=422, detail="year_start fora do intervalo permitido.")

    if y_end and (y_end < 1900 or y_end > current_year):
        raise HTTPException(status_code=422, detail="year_end fora do intervalo permitido.")

    if y_start and y_end and y_end < y_start:
        raise HTTPException(status_code=422, detail="year_end deve ser maior ou igual ao year_start.")

    return manufacturer, model, y_start, y_end, eng


def serialize_ad(ad: Ad, db: Session = None):
    base = {
        "id": str(ad.id),
        "title": ad.title,
        "slug": ad.slug,
        "description": ad.description,
        "price": float(ad.price) if ad.price else 0.0,
        "old_price": float(ad.old_price) if ad.old_price else None,
        "category": ad.category,
        "image_url": ad.image_url,
        "image_urls": ad.image_urls or [],
        "url": ad.external_url,
        "marketplace": ad.marketplace,
        "city": ad.city,
        "state": ad.state,
        "status": ad.status,
        "free_shipping": bool(ad.free_shipping),
        "is_universal": bool(ad.is_universal),
        "manufacturer_id": str(ad.manufacturer_id) if ad.manufacturer_id else None,
        "model_id": str(ad.model_id) if ad.model_id else None,
        "condition": ad.condition,
        "warranty": ad.warranty,
        "communities": [{"id": str(c.id), "name": c.name} for c in ad.communities] if hasattr(ad, 'communities') else [],
        "year_start": ad.year_start,
        "year_end": ad.year_end,
        "engine": ad.engine,
        "expires_at": ad.expires_at.isoformat() if ad.expires_at else None,
        "compatibilities": [],
    }
    if db:
        base["compatibilities"] = _load_compatibilities(ad.id, db)
    return base


def _load_compatibilities(ad_id, db: Session) -> list:
    from app.models.ad_compatibility import AdCompatibility
    rows = db.query(AdCompatibility).filter(AdCompatibility.ad_id == ad_id).all()
    result = []
    for r in rows:
        mfg   = db.query(Manufacturer).filter(Manufacturer.id == r.manufacturer_id).first() if r.manufacturer_id else None
        model = db.query(VehicleModel).filter(VehicleModel.id == r.model_id).first() if r.model_id else None
        result.append({
            "id":                str(r.id),
            "manufacturer_id":   str(r.manufacturer_id) if r.manufacturer_id else None,
            "manufacturer_name": mfg.name if mfg else None,
            "model_id":          str(r.model_id) if r.model_id else None,
            "model_name":        model.name if model else None,
            "year_start":        r.year_start,
            "year_end":          r.year_end,
            "engine":            r.engine,
            "note":              r.note,
        })
    return result


def _sync_compatibilities(ad: Ad, items: list, db: Session):
    """Substitui todas as compatibilidades do anúncio pela lista fornecida."""
    from app.models.ad_compatibility import AdCompatibility
    db.query(AdCompatibility).filter(AdCompatibility.ad_id == ad.id).delete()

    first = None
    for item in items:
        if not item.manufacturer_id or not item.model_id:
            continue
        compat = AdCompatibility(
            ad_id=ad.id,
            manufacturer_id=item.manufacturer_id,
            model_id=item.model_id,
            year_start=item.year_start,
            year_end=item.year_end,
            engine=item.engine,
            note=item.note,
        )
        db.add(compat)
        if first is None:
            first = item

    # Atualiza os campos legados com a primeira entrada (para buscas retrocompatíveis)
    if first:
        ad.manufacturer_id = first.manufacturer_id
        ad.model_id = first.model_id
        ad.year_start = first.year_start
        ad.year_end = first.year_end
        ad.engine = first.engine
    elif not items:
        # Lista vazia: mantém is_universal como estava
        pass


class MarketplaceOption(BaseModel):
    marketplace: str
    price: float
    url: HttpUrl
    free_shipping: bool = False


class CompatibilityItem(BaseModel):
    manufacturer_id: Optional[str] = None
    model_id: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    engine: Optional[str] = None
    note: Optional[str] = None


class AdSchema(BaseModel):
    title: str
    slug: Optional[str] = None
    description: Optional[str] = None
    price: float
    old_price: Optional[float] = None
    category: str = "pecas"
    url: HttpUrl
    image_url: Optional[str] = None
    image_urls: list[str] = Field(default_factory=list)
    marketplace: str
    city: Optional[str] = None
    state: Optional[str] = None
    expires_at: Optional[str] = None
    free_shipping: bool = False

    is_universal: bool = True
    # Campos legados (compatibilidade única) — mantidos para não quebrar dados antigos
    manufacturer_id: Optional[str] = None
    model_id: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    engine: Optional[str] = None

    # Nova lista de compatibilidades múltiplas
    compatibilities: list[CompatibilityItem] = Field(default_factory=list)

    marketplace_options: list[MarketplaceOption] = Field(default_factory=list)
    group_id: Optional[str] = None
    condition: Optional[str] = "new"
    warranty: Optional[str] = None
    community_ids: list[str] = Field(default_factory=list)


@router.post("/")
def create_ad(
    request: Request,
    data: AdSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_plan = (current_user.plan or "free").lower()
    count = db.query(Ad).filter(Ad.user_id == current_user.id).count()
    limit = PLAN_LIMITS.get(user_plan, 5)

    if count >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Limite do plano '{user_plan.upper()}' atingido ({limit} links). Faça um upgrade para continuar!",
        )

    manufacturer, model, y_start, y_end, eng = validate_vehicle_payload(data, db)
    slug = data.slug or slugify(data.title)
    short_code = generate_short_code()

    ad = Ad(
        title=data.title,
        slug=slug,
        short_code=short_code,
        description=data.description,
        price=data.price,
        old_price=data.old_price,
        category=data.category,
        image_url=data.image_url,
        image_urls=data.image_urls,
        external_url=str(data.url),
        marketplace=data.marketplace,
        status="pending",
        views_count=0,
        clicks_count=0,
        unique_clicks=0,
        city=data.city,
        state=data.state,
        free_shipping=data.free_shipping,
        expires_at=parse_optional_datetime(data.expires_at),
        user_id=current_user.id,
        is_universal=data.is_universal,
        condition=data.condition or "new",
        warranty=data.warranty,
        manufacturer_id=(manufacturer.id if manufacturer else None),
        model_id=(model.id if model else None),
        year_start=(None if data.is_universal else y_start),
        year_end=(None if data.is_universal else y_end),
        engine=(None if data.is_universal else eng),
    )

    ad.marketplace_options = [o.model_dump() | {"url": str(o.url)} for o in data.marketplace_options]
    if data.group_id:
        ad.group_id = data.group_id

    db.add(ad)
    db.flush()  # garante ad.id antes de inserir compatibilidades

    if data.compatibilities is not None:
        _sync_compatibilities(ad, data.compatibilities, db)

    if data.community_ids:
        communities = db.query(Community).filter(Community.id.in_(data.community_ids)).all()
        ad.communities = communities

    db.commit()

    log_activity(db, request, "AD_CREATE", "ad", str(ad.id),
                 f"Link criado: '{data.title}'", current_user.id)

    # Dispara e-mails baseados no status do anúncio
    from app.services.email_service import send_product_created, send_product_pending
    try:
        if ad.status == "pending":
            send_product_pending(current_user.email, current_user.name, ad.title)
        else:
            send_product_created(current_user.email, current_user.name, ad.title)
    except Exception as e:
        print(f"Failed to send email: {e}")

    return {
        "message": "created",
        "slug": slug,
        "short_code": short_code,
        "tracking_url": f"http://localhost:8000/api/ads/go/{short_code}",
    }


@router.get("/")
def list_ads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Se for admin, vê tudo. Se não, vê apenas os seus.
    if current_user.role == "admin":
        return db.query(Ad).all()
    return db.query(Ad).filter(Ad.user_id == current_user.id).all()


@router.get("/universal")
def list_universal_ads(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    ads = (
        db.query(Ad)
        .filter(Ad.status == "active", Ad.is_universal.is_(True))
        .order_by(Ad.views_count.desc(), Ad.created_at.desc())
        .limit(limit)
        .all()
    )
    return [serialize_ad(ad) for ad in ads]


@router.get("/category/{slug}")
def list_ads_by_category(
    slug: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    ads = (
        db.query(Ad)
        .filter(Ad.status == "active", Ad.category == slug)
        .order_by(Ad.views_count.desc(), Ad.created_at.desc())
        .limit(limit)
        .all()
    )
    return [serialize_ad(ad) for ad in ads]


@router.get("/by-vehicle")
def list_ads_by_vehicle(
    brand: str = Query(..., description="slug da montadora"),
    model: str = Query(..., description="slug do modelo"),
    year: Optional[int] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    manufacturer = db.query(Manufacturer).filter(Manufacturer.slug == brand).first()
    if not manufacturer:
        return []

    model_obj = (
        db.query(VehicleModel)
        .filter(
            VehicleModel.slug == model,
            VehicleModel.manufacturer_id == manufacturer.id,
        )
        .first()
    )
    if not model_obj:
        return []

    query = db.query(Ad).filter(
        Ad.status == "active",
        Ad.is_universal.is_(False),
        Ad.manufacturer_id == manufacturer.id,
        Ad.model_id == model_obj.id,
    )
    if year:
        query = query.filter(
            (Ad.year_start.is_(None) | (Ad.year_start <= year))
            & (Ad.year_end.is_(None) | (Ad.year_end >= year))
        )

    ads = query.order_by(Ad.views_count.desc(), Ad.created_at.desc()).limit(limit).all()
    return [serialize_ad(ad) for ad in ads]


@router.get("/{ad_id}")
def get_ad(ad_id: str, db: Session = Depends(get_db)):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "not found")
    return serialize_ad(ad, db)


@router.get("/go/{identifier}")
def go(
    identifier: str,
    request: Request,
    src: str = None,
    grp: str = None,
    camp: str = None,
    ad: str = None,
    source: str = None,
    ref: str = None,
    db: Session = Depends(get_db),
):
    item = db.query(Ad).filter(Ad.short_code == identifier).first()
    if not item:
        item = db.query(Ad).filter(Ad.slug == identifier).first()
    if not item:
        raise HTTPException(404, "not found")

    ip_addr = request.client.host if request.client else "unknown"
    import hashlib
    masked_ip = hashlib.sha256(ip_addr.encode()).hexdigest()[:16]

    from datetime import datetime, timedelta
    recent_click = db.query(ClickEvent).filter(
        ClickEvent.ad_id == item.id,
        ClickEvent.ip_hash == masked_ip,
        ClickEvent.clicked_at >= datetime.utcnow() - timedelta(seconds=10)
    ).first()

    if recent_click:
        return RedirectResponse(item.external_url, status_code=302)

    click = ClickEvent(
        ad_id=item.id,
        source=src,
        subsource=grp,
        campaign=camp,
        creative=ad,
        source_type=source,
        source_ref=ref,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        ip_hash=masked_ip,
    )

    db.add(click)
    item.clicks_count += 1
    db.commit()

    return RedirectResponse(item.external_url, status_code=302)


@router.put("/{ad_id}")
def update_ad(
    request: Request,
    ad_id: str,
    data: AdSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "not found")

    # Verificação de segurança: Dono ou Admin
    if ad.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Acesso negado: Você não é o proprietário deste anúncio.")

    manufacturer, model, y_start, y_end, eng = validate_vehicle_payload(data, db)

    ad.title = data.title
    ad.description = data.description
    ad.price = data.price
    ad.old_price = data.old_price
    ad.category = data.category
    ad.image_url = data.image_url
    ad.image_urls = data.image_urls
    ad.external_url = str(data.url)
    ad.marketplace = data.marketplace
    ad.city = data.city
    ad.state = data.state
    ad.free_shipping = data.free_shipping
    ad.expires_at = parse_optional_datetime(data.expires_at)
    ad.is_universal = data.is_universal
    ad.condition = data.condition or "new"
    ad.warranty = data.warranty
    ad.manufacturer_id = manufacturer.id if manufacturer else None
    ad.model_id = model.id if model else None
    ad.year_start = None if data.is_universal else y_start
    ad.year_end = None if data.is_universal else y_end
    ad.engine = None if data.is_universal else eng

    if data.slug:
        ad.slug = data.slug
    else:
        ad.slug = slugify(data.title)

    ad.marketplace_options = [o.model_dump() | {"url": str(o.url)} for o in data.marketplace_options]
    if data.group_id is not None:
        ad.group_id = data.group_id if data.group_id else None

    if data.compatibilities is not None:
        _sync_compatibilities(ad, data.compatibilities, db)

    if data.community_ids:
        communities = db.query(Community).filter(Community.id.in_(data.community_ids)).all()
        ad.communities = communities

    db.commit()

    log_activity(db, request, "AD_UPDATE", "ad", ad_id,
                 f"Link atualizado: '{data.title}'", current_user.id)

    return {"message": "updated"}


@router.delete("/{ad_id}")
def delete_ad(
    request: Request,
    ad_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "not found")

    # Verificação de segurança: Dono ou Admin
    if ad.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Acesso negado: Você não tem permissão para remover este anúncio.")

    title = ad.title
    db.delete(ad)
    db.commit()

    log_activity(db, request, "AD_DELETE", "ad", ad_id,
                 f"Link removido: '{title}'", current_user.id)

    return {"message": "deleted"}

class RatingSchema(BaseModel):
    score: int = Field(..., ge=1, le=5)

@router.post("/{ad_id}/rate")
def rate_ad(
    ad_id: str,
    rating_data: RatingSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anúncio não encontrado")
    
    # Verifica se já avaliou
    existing_rating = db.query(AdRating).filter(
        AdRating.user_id == current_user.id,
        AdRating.ad_id == ad.id
    ).first()
    
    if existing_rating:
        # Atualiza avaliação existente
        existing_rating.score = rating_data.score
    else:
        # Cria nova avaliação
        new_rating = AdRating(
            user_id=current_user.id,
            ad_id=ad.id,
            score=rating_data.score
        )
        db.add(new_rating)
    
    db.flush()
    
    # Recalcula média
    ratings = db.query(AdRating).filter(AdRating.ad_id == ad.id).all()
    count = len(ratings)
    total = sum(r.score for r in ratings)
    avg = total / count if count > 0 else 0
    
    ad.average_rating = avg
    ad.rating_count = count
    
    db.commit()
    
    return {
        "message": "Avaliação registrada com sucesso",
        "average_rating": float(avg),
        "rating_count": count
    }
