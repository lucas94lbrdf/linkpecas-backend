import uuid

from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import case, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ad import Ad
from app.models.ad_compatibility import AdCompatibility
from app.models.click import ClickEvent
from app.models.user import User
from app.models.vehicle import Manufacturer, VehicleModel
from app.models.setting import SystemSetting
from app.utils.activity import _get_device, _get_location

router = APIRouter()


def build_public_ad_payload(ad: Ad, user_plan: str | None = None):
    # Valores padrão seguros
    try:
        price = float(ad.price) if ad.price else 0.0
    except (TypeError, ValueError):
        price = 0.0
        
    try:
        old_price = float(ad.old_price) if ad.old_price else None
    except (TypeError, ValueError):
        old_price = None

    try:
        avg_rating = float(ad.average_rating) if ad.average_rating is not None else 0.0
    except (TypeError, ValueError):
        avg_rating = 0.0

    return {
        "id": str(ad.id),
        "title": ad.title,
        "slug": ad.slug,
        "price": price,
        "oldPrice": old_price,
        "image": ad.image_url,
        "marketplace": ad.marketplace,
        "category": ad.category or "pecas",
        "clicks": ad.clicks_count or 0,
        "views": ad.views_count or 0,
        "rating": avg_rating if avg_rating > 0 else 5.0,
        "rating_count": int(ad.rating_count or 0),
        "plan": user_plan,
        "is_universal": bool(ad.is_universal),
        "manufacturer_id": str(ad.manufacturer_id) if ad.manufacturer_id else None,
        "model_id": str(ad.model_id) if ad.model_id else None,
        "year_start": ad.year_start,
        "year_end": ad.year_end,
        "engine": ad.engine,
        "condition": ad.condition,
        "warranty": ad.warranty,
    }


@router.get("/ads")
def search_ads(
    q: str = None,
    category: str = None,
    brand: str = None,
    model: str = None,
    year: int = None,
    include_universal: bool = True,
    db: Session = Depends(get_db),
):
    plan_priority = case(
        (User.plan == "premium", 4),
        (User.plan == "pro", 3),
        (User.plan == "smart", 2),
        else_=1,
    )
    query = (
        db.query(Ad, User.plan.label("user_plan"))
        .join(User, Ad.user_id == User.id)
        .filter(Ad.status == "active")
    )

    if category and category != "all":
        query = query.filter(Ad.category == category)

    if q:
        search_term = f"%{q}%"
        query = query.filter(or_(Ad.title.ilike(search_term), Ad.description.ilike(search_term)))

    if brand and model:
        manufacturer = db.query(Manufacturer).filter(Manufacturer.slug == brand).first()
        model_obj = (
            db.query(VehicleModel)
            .filter(
                VehicleModel.slug == model,
                VehicleModel.manufacturer_id == (manufacturer.id if manufacturer else None),
            )
            .first()
            if manufacturer
            else None
        )
        if manufacturer and model_obj:
            # IDs de ads com compatibilidade na nova tabela
            compat_sub = (
                db.query(AdCompatibility.ad_id)
                .filter(
                    AdCompatibility.manufacturer_id == manufacturer.id,
                    AdCompatibility.model_id == model_obj.id,
                )
            )
            if year:
                compat_sub = compat_sub.filter(
                    (AdCompatibility.year_start.is_(None) | (AdCompatibility.year_start <= year)),
                    (AdCompatibility.year_end.is_(None)   | (AdCompatibility.year_end   >= year)),
                )
            compat_ids = compat_sub.subquery()

            # Compatibilidade legada (campo direto no Ad)
            legacy_filter = (
                Ad.is_universal.is_(False)
                & (Ad.manufacturer_id == manufacturer.id)
                & (Ad.model_id == model_obj.id)
            )
            if year:
                legacy_filter = legacy_filter & (
                    (Ad.year_start.is_(None) | (Ad.year_start <= year))
                    & (Ad.year_end.is_(None) | (Ad.year_end >= year))
                )

            vehicle_filter = legacy_filter | Ad.id.in_(compat_ids)

            if include_universal:
                query = query.filter(vehicle_filter | Ad.is_universal.is_(True))
            else:
                query = query.filter(vehicle_filter)
        else:
            query = query.filter(Ad.is_universal.is_(True)) if include_universal else query.filter(False)

    results = query.order_by(plan_priority.desc(), Ad.views_count.desc(), Ad.created_at.desc()).limit(40).all()
    return [build_public_ad_payload(ad, user_plan) for ad, user_plan in results]


@router.get("/ads/trending")
def get_trending_ads(db: Session = Depends(get_db)):
    plan_priority = case(
        (User.plan == "premium", 4),
        (User.plan == "pro", 3),
        (User.plan == "smart", 2),
        else_=1,
    )
    results = (
        db.query(Ad, User.plan.label("user_plan"))
        .join(User, Ad.user_id == User.id)
        .filter(Ad.status == "active")
        .order_by(plan_priority.desc(), Ad.views_count.desc())
        .limit(8)
        .all()
    )
    return [build_public_ad_payload(ad, user_plan) for ad, user_plan in results]


@router.get("/ads/offers")
def get_offer_ads(db: Session = Depends(get_db)):
    plan_priority = case(
        (User.plan == "premium", 4),
        (User.plan == "pro", 3),
        (User.plan == "smart", 2),
        else_=1,
    )
    results = (
        db.query(Ad, User.plan.label("user_plan"))
        .join(User, Ad.user_id == User.id)
        .filter(Ad.status == "active", Ad.old_price.is_not(None))
        .order_by(plan_priority.desc(), Ad.views_count.desc(), Ad.created_at.desc())
        .limit(12)
        .all()
    )
    return [build_public_ad_payload(ad, user_plan) for ad, user_plan in results]


@router.get("/ads/{identifier}")
def get_public_ad(identifier: str, db: Session = Depends(get_db)):
    ad = db.query(Ad).filter((Ad.slug == identifier) | (Ad.short_code == identifier)).first()
    if not ad:
        try:
            ad = db.query(Ad).filter(Ad.id == uuid.UUID(identifier)).first()
        except (ValueError, AttributeError):
            pass
    if not ad:
        raise HTTPException(404, "Produto não encontrado")

    seller = db.query(User).filter(User.id == ad.user_id).first()
    manufacturer = (
        db.query(Manufacturer).filter(Manufacturer.id == ad.manufacturer_id).first()
        if ad.manufacturer_id else None
    )
    model = db.query(VehicleModel).filter(VehicleModel.id == ad.model_id).first() if ad.model_id else None

    price = float(ad.price) if ad.price else 0.0
    old_price = float(ad.old_price) if ad.old_price else None

    # ── Montar todas as opções de preço ──────────────────────────────────────
    all_options = []

    # 1. Opção principal
    all_options.append({
        "ad_id":        str(ad.id),
        "marketplace":  ad.marketplace,
        "price":        price,
        "url":          ad.external_url,
        "free_shipping": bool(ad.free_shipping),
        "is_primary":   True,
    })

    # 2. Opções inline do próprio anúncio
    for opt in (ad.marketplace_options or []):
        all_options.append({
            "ad_id":        str(ad.id),
            "marketplace":  opt.get("marketplace", ""),
            "price":        float(opt.get("price", 0)),
            "url":          opt.get("url", ""),
            "free_shipping": bool(opt.get("free_shipping", False)),
            "is_primary":   False,
        })

    # 3. Anúncios do mesmo grupo (outros anúncios linkados)
    if ad.group_id:
        siblings = db.query(Ad).filter(
            Ad.group_id == ad.group_id,
            Ad.id != ad.id,
            Ad.status == "active",
        ).all()
        for sib in siblings:
            all_options.append({
                "ad_id":        str(sib.id),
                "marketplace":  sib.marketplace,
                "price":        float(sib.price) if sib.price else 0,
                "url":          sib.external_url,
                "free_shipping": bool(sib.free_shipping),
                "is_primary":   False,
            })
            for opt in (sib.marketplace_options or []):
                all_options.append({
                    "ad_id":        str(sib.id),
                    "marketplace":  opt.get("marketplace", ""),
                    "price":        float(opt.get("price", 0)),
                    "url":          opt.get("url", ""),
                    "free_shipping": bool(opt.get("free_shipping", False)),
                    "is_primary":   False,
                })

    # Ordenar por preço crescente
    all_options.sort(key=lambda x: x["price"])
    # Marcar o menor preço
    if all_options:
        min_price = all_options[0]["price"]
        for opt in all_options:
            opt["is_best"] = opt["price"] == min_price

    return {
        "id":           str(ad.id),
        "title":        ad.title,
        "description":  ad.description,
        "price":        price,
        "old_price":    old_price,
        "image":        ad.image_url,
        "image_urls":   ad.image_urls or [],
        "url":          ad.external_url,
        "marketplace":  ad.marketplace,
        "city":         ad.city,
        "state":        ad.state,
        "category":     ad.category,
        "free_shipping": ad.free_shipping or False,
        "rating":       float(ad.average_rating) if ad.average_rating is not None else 5.0,
        "reviews":      int(ad.rating_count or 0),
        "shop_name":    seller.shop_name if seller else "Loja Parceira",
        "shop_slug":    seller.shop_slug if seller else "loja-parceira",
        "is_universal": bool(ad.is_universal),
        "group_id":     str(ad.group_id) if ad.group_id else None,
        "manufacturer": (
            {"id": str(manufacturer.id), "name": manufacturer.name, "slug": manufacturer.slug}
            if manufacturer else None
        ),
        "model": ({"id": str(model.id), "name": model.name, "slug": model.slug} if model else None),
        "year_start":   ad.year_start,
        "year_end":     ad.year_end,
        "engine":       ad.engine,
        "condition":    ad.condition,
        "warranty":     ad.warranty,
        "communities":  [{"id": str(c.id), "name": c.name, "slug": c.slug} for c in ad.communities] if hasattr(ad, 'communities') else [],
        "all_options":  all_options,
    }


class ClickRequest(BaseModel):
    marketplace: str = None
    url: str = None
    source_type: str = None
    source_ref: str = None

@router.post("/ads/{identifier}/click")
def register_click(identifier: str, data: ClickRequest, request: Request, db: Session = Depends(get_db)):
    ad = db.query(Ad).filter((Ad.slug == identifier) | (Ad.short_code == identifier)).first()
    if not ad:
        try:
            ad = db.query(Ad).filter(Ad.id == uuid.UUID(identifier)).first()
        except ValueError:
            ad = None

    if ad:
        # Trava anti-spam: 10 segundos por IP
        ip = request.client.host if request.client else "unknown"
        import hashlib
        masked_ip = hashlib.sha256(ip.encode()).hexdigest()[:16]

        recent_click = db.query(ClickEvent).filter(
            ClickEvent.ad_id == ad.id,
            ClickEvent.ip_hash == masked_ip,
            ClickEvent.clicked_at >= datetime.utcnow() - timedelta(seconds=10)
        ).first()

        if recent_click:
            return {"status": "ignored", "reason": "rate_limit"}

        ad.clicks_count = (ad.clicks_count or 0) + 1

        ua = request.headers.get("user-agent", "")
        referer = request.headers.get("referer", "")

        click = ClickEvent(
            id=uuid.uuid4(),
            ad_id=ad.id,
            marketplace=data.marketplace or ad.marketplace,
            external_url=data.url or ad.external_url,
            source_type=data.source_type,
            source_ref=data.source_ref,
            referrer=referer,
            user_agent=ua,
            device=_get_device(ua),
            ip_hash=masked_ip,
        )
        db.add(click)
        db.commit()

        try:
            loc = _get_location(ip)
            if loc and loc != "Local":
                parts = [p.strip() for p in loc.split(",")]
                if len(parts) >= 2:
                    click.city = parts[0]
                    click.state = parts[1] if len(parts) > 1 else None
                db.commit()
        except Exception:
            pass

    return {"status": "ok"}


@router.post("/ads/{identifier}/view")
def register_view(identifier: str, db: Session = Depends(get_db)):
    ad = db.query(Ad).filter((Ad.slug == identifier) | (Ad.short_code == identifier)).first()
    if not ad:
        try:
            ad = db.query(Ad).filter(Ad.id == uuid.UUID(identifier)).first()
        except ValueError:
            ad = None

    if ad:
        # Trava anti-spam simples para views (opcional, mas recomendada)
        # Note: views não salvam IP no modelo atual, então apenas incrementamos.
        # Se quisermos ser rigorosos, precisaríamos salvar logs de views também.
        ad.views_count = (ad.views_count or 0) + 1
        db.commit()
    return {"status": "ok"}


@router.get("/shops/{slug}")
def get_shop_public(slug: str, db: Session = Depends(get_db)):
    shop = db.query(User).filter(User.shop_slug == slug).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Loja não encontrada")

    ads = (
        db.query(Ad)
        .filter(Ad.user_id == shop.id, Ad.status == "active")
        .order_by(Ad.views_count.desc(), Ad.created_at.desc())
        .limit(60)
        .all()
    )

    return {
        "shop": {
            "id": str(shop.id),
            "name": shop.shop_name or shop.name,
            "slug": shop.shop_slug,
            "description": shop.shop_description,
            "location": shop.shop_location,
            "logo": shop.shop_logo,
        },
        "ads": [
            {
                "id": str(ad.id),
                "title": ad.title,
                "slug": ad.slug,
                "price": float(ad.price) if ad.price else 0.0,
                "old_price": float(ad.old_price) if ad.old_price else None,
                "image": ad.image_url,
                "marketplace": ad.marketplace,
                "is_universal": bool(ad.is_universal),
            }
            for ad in ads
        ],
    }

from pydantic import BaseModel

class SearchLogSchema(BaseModel):
    term: str = None
    vehicle_context: str = None
    origin: str = "site"
    results_found: int = 0

@router.post("/logs/searches")
def log_search(data: SearchLogSchema, db: Session = Depends(get_db)):
    from app.models.search_log import SearchLog
    
    # Não salva se for vazio
    if not data.term and not data.vehicle_context:
        return {"status": "ignored"}
        
    log = SearchLog(
        term=data.term,
        vehicle_context=data.vehicle_context,
        origin=data.origin,
        results_found=data.results_found
    )
    db.add(log)
    db.commit()
    
    return {"status": "ok"}

@router.get("/tracking")
def get_tracking_ids(db: Session = Depends(get_db)):
    keys = ["google_analytics_id", "google_tag_manager_id", "google_search_console_id", "recaptcha_site_key"]
    settings = db.query(SystemSetting).filter(SystemSetting.key.in_(keys)).all()

    return {s.key: s.value for s in settings}
 