from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from app.services.email_service import send_account_blocked
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.user import User
from app.models.ad import Ad 
from app.models.click import ClickEvent
from app.models.log import ActivityLog
from app.models.vehicle import Manufacturer, VehicleModel
from app.routes.api.auth import get_admin_user
router = APIRouter(dependencies=[Depends(get_admin_user)])


def simple_slugify(value: str) -> str:
    return (
        value.lower()
        .strip()
        .replace("/", "-")
        .replace(" ", "-")
        .replace("_", "-")
    )

# --- OVERVIEW (DASHBOARD ADMIN) ---

ACTION_LABELS = {
    "USER_LOGIN":    "Fez login",
    "USER_REGISTER": "Se cadastrou",
    "AD_CREATE":     "Criou um anúncio",
    "AD_UPDATE":     "Atualizou um anúncio",
    "AD_DELETE":     "Removeu um anúncio",
}

@router.get("/overview")
def get_admin_overview(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)

    # ── contagens ──────────────────────────────────────────────────────────────
    total_users  = db.query(User).count()
    active_ads   = db.query(Ad).filter(Ad.status == "active").count()
    pending_ads  = db.query(Ad).filter(Ad.status == "pending").count()
    total_views  = db.query(func.sum(Ad.views_count)).scalar() or 0
    total_clicks = db.query(func.sum(Ad.clicks_count)).scalar() or 0
    conversion   = round(total_clicks / total_views * 100, 2) if total_views > 0 else 0.0

    # ── valor do catálogo (soma preços anúncios ativos) ────────────────────────
    catalog_value = float(db.query(func.sum(Ad.price)).filter(Ad.status == "active").scalar() or 0)
    catalog_str   = f"{catalog_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # ── top 3 anúncios (por views) ─────────────────────────────────────────────
    top_ads = db.query(Ad).filter(Ad.status == "active").order_by(desc(Ad.views_count)).limit(3).all()
    top_ads_data = [
        {"title": a.title, "views": a.views_count or 0, "clicks": a.clicks_count or 0,
         "ctr": round((a.clicks_count or 0) / (a.views_count or 1) * 100, 1)}
        for a in top_ads
    ]

    # ── gráfico: cliques por dia nos últimos 30 dias ───────────────────────────
    clicks_query = (
        db.query(func.date(ClickEvent.clicked_at).label("day"), func.count(ClickEvent.id).label("n"))
        .filter(ClickEvent.clicked_at >= thirty_days_ago)
        .group_by(func.date(ClickEvent.clicked_at))
        .order_by(func.date(ClickEvent.clicked_at))
        .all()
    )
    clicks_map = {str(r.day): r.n for r in clicks_query}
    chart = []
    for i in range(30):
        d = thirty_days_ago + timedelta(days=i)
        chart.append({"day": d.strftime("%d/%m"), "revenue": clicks_map.get(d.strftime("%Y-%m-%d"), 0)})

    # ── atividade recente (activity_logs) ──────────────────────────────────────
    recent_logs = db.query(ActivityLog).order_by(desc(ActivityLog.created_at)).limit(8).all()
    activity = []
    for log in recent_logs:
        user = db.query(User).filter(User.id == log.user_id).first() if log.user_id else None
        diff  = now - log.created_at if log.created_at else timedelta(0)
        secs  = diff.total_seconds()
        if secs < 60:
            time_str = "agora"
        elif secs < 3600:
            time_str = f"{int(secs/60)}min atrás"
        elif secs < 86400:
            time_str = f"{int(secs/3600)}h atrás"
        else:
            time_str = f"{diff.days}d atrás"

        activity.append({
            "user":   user.name if user else "Sistema",
            "action": ACTION_LABELS.get(log.action, log.action),
            "detail": log.details or "",
            "time":   time_str,
        })

    return {
        "total_users":   total_users,
        "users_delta":   0,
        "active_ads":    active_ads,
        "pending_ads":   pending_ads,
        "ads_delta":     0,
        "total_views":   total_views,
        "total_clicks":  total_clicks,
        "conversion":    conversion,
        "catalog_value": catalog_str,
        "revenue":       catalog_str,
        "revenue_delta": 0,
        "chart":         chart,
        "activity":      activity,
        "top_ads":       top_ads_data,
    }


# --- USUÁRIOS ---

@router.get("/users")
def get_admin_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@router.put("/users/{user_id}/role")
def update_user_role(user_id: str, role: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    user.role = role
    db.commit()
    return {"message": "Cargo atualizado"}

class BlockUserSchema(BaseModel):
    reason: str

@router.post("/users/{user_id}/block")
def block_user(user_id: str, data: BlockUserSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Inativa a conta mudando role (ou adicionando um status_conta)
    user.role = "blocked"
    db.commit()

    # Dispara e-mail avisando o lojista
    send_account_blocked(user.email, user.name, data.reason)

    return {"message": "Conta bloqueada e e-mail enviado com sucesso"}

@router.post("/users/{user_id}/unblock")
def unblock_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    user.role = "seller" # Volta pro papel padrão
    db.commit()
    return {"message": "Conta reativada com sucesso"}

@router.delete("/users/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    db.delete(user)
    db.commit()
    return {"message": "Usuário excluído permanentemente"}

# --- ANÚNCIOS (ADS) ---

@router.get("/ads")
def get_admin_ads(db: Session = Depends(get_db)):
    ads = db.query(Ad).order_by(
        case(
            (Ad.status == "pending", 0),
            (Ad.status == "active", 1),
            else_=2
        )
    ).all()
    
    results = []
    for ad in ads:
        seller = db.query(User).filter(User.id == ad.user_id).first()
        results.append({
            "id": str(ad.id),
            "title": ad.title,
            "price": float(ad.price) if ad.price else 0,
            "status": ad.status,
            "marketplace": ad.marketplace,
            "is_universal": bool(ad.is_universal),
            "manufacturer_id": str(ad.manufacturer_id) if ad.manufacturer_id else None,
            "model_id": str(ad.model_id) if ad.model_id else None,
            "year_start": ad.year_start,
            "year_end": ad.year_end,
            "seller_name": seller.name if seller else "Desconhecido",
            "created_at": ad.created_at
        })
    return results

@router.patch("/ads/{ad_id}")
def update_ad_status(ad_id: str, data: dict, db: Session = Depends(get_db)):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anúncio não encontrado")
    
    new_status = data.get("status")
    if new_status:
        ad.status = new_status
        db.commit()

    return {"message": "Status atualizado", "new_status": ad.status}

from datetime import datetime
from app.services.email_service import send_product_expired
from sqlalchemy.orm import joinedload

@router.post("/cron/check-expired-ads")
def check_expired_ads(db: Session = Depends(get_db)):
    # Busca anúncios ativos que já passaram da data de expiração
    expired_ads = db.query(Ad).options(joinedload(Ad.user)).filter(
        Ad.status == "active",
        Ad.expires_at < datetime.utcnow()
    ).all()

    count = 0
    for ad in expired_ads:
        ad.status = "expired"
        
        # Só tenta enviar e-mail se o usuário existir
        if ad.user:
            try:
                send_product_expired(ad.user.email, ad.user.name, ad.title)
            except Exception as e:
                print(f"Erro ao enviar email para {ad.user.email}: {e}")
        
        count += 1

    if count > 0:
        db.commit()

    return {"message": f"{count} anúncios foram marcados como expirados e os e-mails enviados."}


@router.patch("/ads/{ad_id}/compatibility")
def update_ad_compatibility(ad_id: str, data: dict, db: Session = Depends(get_db)):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anúncio não encontrado")

    is_universal = bool(data.get("is_universal", True))
    ad.is_universal = is_universal

    if is_universal:
        ad.manufacturer_id = None
        ad.model_id = None
        ad.year_start = None
        ad.year_end = None
        ad.engine = None
    else:
        manufacturer_id = data.get("manufacturer_id")
        model_id = data.get("model_id")
        if not manufacturer_id or not model_id:
            raise HTTPException(422, "manufacturer_id e model_id são obrigatórios.")
        model = db.query(VehicleModel).filter(VehicleModel.id == model_id).first()
        if not model:
            raise HTTPException(404, "Modelo não encontrado")
        if str(model.manufacturer_id) != manufacturer_id:
            raise HTTPException(422, "Modelo não pertence à montadora informada")

        ad.manufacturer_id = manufacturer_id
        ad.model_id = model_id
        ad.year_start = data.get("year_start")
        ad.year_end = data.get("year_end")
        ad.engine = data.get("engine")

    db.commit()
    return {"message": "Compatibilidade atualizada"}


# --- CATÁLOGO DE VEÍCULOS ---


@router.get("/manufacturers")
def list_admin_manufacturers(db: Session = Depends(get_db)):
    items = db.query(Manufacturer).order_by(Manufacturer.name.asc()).all()
    return [
        {
            "id": str(item.id),
            "name": item.name,
            "slug": item.slug,
            "logo_url": item.logo_url,
            "is_active": item.is_active,
        }
        for item in items
    ]


@router.post("/manufacturers")
def create_manufacturer(data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    if not name:
        raise HTTPException(422, "name é obrigatório")

    slug = (data.get("slug") or simple_slugify(name)).strip()
    exists = db.query(Manufacturer).filter(Manufacturer.slug == slug).first()
    if exists:
        raise HTTPException(409, "slug já existente")

    item = Manufacturer(
        name=name,
        slug=slug,
        logo_url=data.get("logo_url"),
        is_active=bool(data.get("is_active", True)),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "name": item.name, "slug": item.slug}


@router.put("/manufacturers/{manufacturer_id}")
def update_manufacturer(manufacturer_id: str, data: dict, db: Session = Depends(get_db)):
    item = db.query(Manufacturer).filter(Manufacturer.id == manufacturer_id).first()
    if not item:
        raise HTTPException(404, "Montadora não encontrada")

    if "name" in data and data["name"]:
        item.name = data["name"].strip()
    if "slug" in data and data["slug"]:
        item.slug = data["slug"].strip()
    if "logo_url" in data:
        item.logo_url = data["logo_url"]
    if "is_active" in data:
        item.is_active = bool(data["is_active"])

    db.commit()
    return {"message": "Montadora atualizada"}


@router.delete("/manufacturers/{manufacturer_id}")
def delete_manufacturer(manufacturer_id: str, db: Session = Depends(get_db)):
    item = db.query(Manufacturer).filter(Manufacturer.id == manufacturer_id).first()
    if not item:
        raise HTTPException(404, "Montadora não encontrada")
    db.delete(item)
    db.commit()
    return {"message": "Montadora removida"}


@router.get("/models")
def list_admin_models(manufacturer_id: str = None, db: Session = Depends(get_db)):
    query = db.query(VehicleModel)
    if manufacturer_id:
        query = query.filter(VehicleModel.manufacturer_id == manufacturer_id)
    rows = query.order_by(VehicleModel.name.asc()).all()
    return [
        {
            "id": str(item.id),
            "manufacturer_id": str(item.manufacturer_id),
            "name": item.name,
            "slug": item.slug,
            "vehicle_type": item.vehicle_type,
            "generation": item.generation,
            "image_url": item.image_url,
            "is_active": item.is_active,
        }
        for item in rows
    ]


@router.post("/models")
def create_model(data: dict, db: Session = Depends(get_db)):
    manufacturer_id = data.get("manufacturer_id")
    name = (data.get("name") or "").strip()
    if not manufacturer_id or not name:
        raise HTTPException(422, "manufacturer_id e name são obrigatórios")

    manufacturer = db.query(Manufacturer).filter(Manufacturer.id == manufacturer_id).first()
    if not manufacturer:
        raise HTTPException(404, "Montadora não encontrada")

    slug = (data.get("slug") or simple_slugify(name)).strip()
    exists = (
        db.query(VehicleModel)
        .filter(VehicleModel.manufacturer_id == manufacturer_id, VehicleModel.slug == slug)
        .first()
    )
    if exists:
        raise HTTPException(409, "Modelo já cadastrado para essa montadora")

    item = VehicleModel(
        manufacturer_id=manufacturer_id,
        name=name,
        slug=slug,
        vehicle_type=data.get("vehicle_type") or "car",
        generation=data.get("generation") or None,
        image_url=data.get("image_url") or None,
        is_active=bool(data.get("is_active", True)),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "name": item.name, "slug": item.slug}


@router.put("/models/{model_id}")
def update_model(model_id: str, data: dict, db: Session = Depends(get_db)):
    item = db.query(VehicleModel).filter(VehicleModel.id == model_id).first()
    if not item:
        raise HTTPException(404, "Modelo não encontrado")

    if "name" in data and data["name"]:
        item.name = data["name"].strip()
    if "slug" in data and data["slug"]:
        item.slug = data["slug"].strip()
    if "vehicle_type" in data and data["vehicle_type"]:
        item.vehicle_type = data["vehicle_type"]
    if "generation" in data:
        item.generation = data["generation"] or None
    if "image_url" in data:
        item.image_url = data["image_url"] or None
    if "is_active" in data:
        item.is_active = bool(data["is_active"])

    db.commit()
    return {"message": "Modelo atualizado"}


@router.delete("/models/{model_id}")
def delete_model(model_id: str, db: Session = Depends(get_db)):
    item = db.query(VehicleModel).filter(VehicleModel.id == model_id).first()
    if not item:
        raise HTTPException(404, "Modelo não encontrado")
    db.delete(item)
    db.commit()
    return {"message": "Modelo removido"}

# --- ANALYTICS V2 ---

@router.get("/analytics/v2")
def get_advanced_analytics(db: Session = Depends(get_db)):
    # 1. Cliques Totais
    total_clicks = db.query(ClickEvent).count()
    
    # 2. Visualizações Totais (Soma de views_count de todos os Ads)
    total_views = db.query(func.sum(Ad.views_count)).scalar() or 0
    
    # 3. CTR Global
    ctr = (total_clicks / total_views * 100) if total_views > 0 else 0
    
    # 4. Volume de Cliques (últimos 7 dias)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    clicks_history = db.query(
        func.date(ClickEvent.clicked_at).label('day'),
        func.count(ClickEvent.id).label('value')
    ).filter(ClickEvent.clicked_at >= seven_days_ago)\
     .group_by('day').order_by('day').all()
    
    revenue_data = [{"day": str(r[0]), "value": r[1]} for r in clicks_history]

    # 5. Distribuição de Dispositivos
    devices_query = db.query(
        ClickEvent.device,
        func.count(ClickEvent.id).label('value')
    ).group_by(ClickEvent.device).all()
    
    total_devices = sum(r[1] for r in devices_query)
    devices = [{"name": (r[0] or "Desconhecido").capitalize(), "value": round((r[1]/total_devices*100), 1) if total_devices > 0 else 0} for r in devices_query]

    # 6. Origem do Tráfego
    sources_query = db.query(
        ClickEvent.source,
        func.count(ClickEvent.id).label('value')
    ).group_by(ClickEvent.source).order_by(desc('value')).limit(5).all()
    
    sources = [{"name": r[0] or "Direto", "value": round((r[1]/total_clicks*100), 1) if total_clicks > 0 else 0} for r in sources_query]

    # 7. Atividade por Horário (Pico)
    hourly_query = db.query(
        func.extract('hour', ClickEvent.clicked_at).label('hour'),
        func.count(ClickEvent.id).label('visits')
    ).group_by('hour').order_by('hour').all()
    
    # Garantir que temos todas as 24 horas
    hourly_map = {int(r[0]): r[1] for r in hourly_query}
    hourly_data = [{"hour": f"{h:02d}h", "visits": hourly_map.get(h, 0)} for h in range(24)]

    # 8. Top Lojas (Baseado em cliques acumulados)
    top_stores_query = db.query(
        User.shop_name,
        func.sum(Ad.clicks_count).label('total_clicks')
    ).join(Ad, User.id == Ad.user_id)\
     .group_by(User.shop_name)\
     .order_by(desc('total_clicks'))\
     .limit(5).all()
    
    top_stores = [{"name": r[0] or "Loja Sem Nome", "clicks": int(r[1] or 0), "growth": 12} for r in top_stores_query]

    # 9. Métricas Detalhadas (Top Produtos)
    top_products_query = db.query(
        Ad.title,
        User.shop_name,
        Ad.views_count,
        Ad.clicks_count
    ).join(User, Ad.user_id == User.id)\
     .order_by(desc(Ad.clicks_count))\
     .limit(10).all()
    
    detailed_metrics = [{
        "title": r[0],
        "shop_name": r[1],
        "visits": r[2],
        "clicks": r[3],
        "conv_rate": round((r[3] / r[2] * 100), 1) if r[2] > 0 else 0
    } for r in top_products_query]

    return {
        "total_sessions": f"{total_clicks / 1000:.1f}K" if total_clicks >= 1000 else str(total_clicks),
        "ctr": round(ctr, 2),
        "conversion": 4.5, # Exemplo fixo por enquanto
        "revenue": revenue_data,
        "devices": devices,
        "sources": sources,
        "hourly": hourly_data,
        "top_stores": top_stores,
        "detailed_metrics": detailed_metrics,
        "total_items": len(detailed_metrics)
    }

# --- LOGS ---

@router.get("/logs")
def get_admin_logs(
    type: str = "activity", # "activity" or "traffic"
    limit: int = 100,
    db: Session = Depends(get_db)
):
    if type == "traffic":
        logs = db.query(ClickEvent).order_by(desc(ClickEvent.clicked_at)).limit(limit).all()
        results = []
        for log in logs:
            ad = db.query(Ad).filter(Ad.id == log.ad_id).first()
            results.append({
                "id": str(log.id),
                "timestamp": log.clicked_at,
                "action": "CLICK",
                "entity": ad.title if ad else "Anúncio Removido",
                "source": log.source or "Direto",
                "details": f"Device: {log.device or 'N/A'} | IP: {log.ip_hash[:8]}...",
                "status": "success"
            })
        return results
    else:
        logs = db.query(ActivityLog).order_by(desc(ActivityLog.created_at)).limit(limit).all()
        results = []
        for log in logs:
            user = db.query(User).filter(User.id == log.user_id).first()
            results.append({
                "id": str(log.id),
                "timestamp": log.created_at,
                "action": log.action,
                "user": user.name if user else "Sistema",
                "entity": f"{log.entity_type} ({log.entity_id})",
                "details": log.details,
                "status": "info"
            })
        return results

# --- ANALYTICS TABELA DETALHADA ---

@router.get("/analytics/filter-options")
def get_filter_options(db: Session = Depends(get_db)):
    marketplaces = [r[0] for r in db.query(Ad.marketplace).filter(Ad.marketplace != None).distinct().all()]
    categories   = [r[0] for r in db.query(Ad.category).filter(Ad.category != None).distinct().all()]
    statuses     = [r[0] for r in db.query(Ad.status).filter(Ad.status != None).distinct().all()]
    sellers      = [r[0] for r in db.query(User.shop_name).filter(User.shop_name != None).distinct().all()]
    return {
        "marketplaces": sorted(marketplaces),
        "categories":   sorted(categories),
        "statuses":     sorted(statuses),
        "sellers":      sorted(sellers),
    }


@router.get("/analytics/clicks")
def get_clicks_detailed(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    search: Optional[str] = Query(default=None),
    marketplace: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    ad_status: Optional[str] = Query(default=None),
    seller: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    sort_by: Optional[str] = Query(default="clicks_count"),
    sort_dir: Optional[str] = Query(default="desc"),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Ad, User)
        .outerjoin(User, Ad.user_id == User.id)
    )

    if search:
        term = f"%{search}%"
        query = query.filter(Ad.title.ilike(term) | User.shop_name.ilike(term) | User.name.ilike(term))
    if marketplace:
        query = query.filter(Ad.marketplace == marketplace)
    if category:
        query = query.filter(Ad.category == category)
    if ad_status:
        query = query.filter(Ad.status == ad_status)
    if seller:
        query = query.filter(User.shop_name == seller)
    if date_from:
        try:
            query = query.filter(Ad.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(Ad.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    total = query.count()

    sort_map = {
        "clicks_count": Ad.clicks_count,
        "views_count":  Ad.views_count,
        "price":        Ad.price,
        "created_at":   Ad.created_at,
    }
    sort_col = sort_map.get(sort_by, Ad.clicks_count)
    query = query.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())

    rows = query.offset((page - 1) * limit).limit(limit).all()

    # último clique registrado por ad (para device/ip/city quando disponível)
    ad_ids = [ad.id for ad, _ in rows]
    last_clicks: dict = {}
    if ad_ids:
        subq = (
            db.query(ClickEvent)
            .filter(ClickEvent.ad_id.in_(ad_ids))
            .order_by(ClickEvent.clicked_at.desc())
            .all()
        )
        seen: set = set()
        for c in subq:
            if c.ad_id not in seen:
                last_clicks[c.ad_id] = c
                seen.add(c.ad_id)

    results = []
    for ad, user in rows:
        lc = last_clicks.get(ad.id)
        views  = ad.views_count or 0
        clicks = ad.clicks_count or 0
        ctr = round((clicks / views * 100), 1) if views > 0 else 0.0

        results.append({
            "ad_id":        str(ad.id),
            "ad_title":     ad.title,
            "ad_slug":      ad.slug,
            "short_code":   ad.short_code,
            "shop_name":    (user.shop_name or user.name) if user else "—",
            "category":     ad.category,
            "marketplace":  ad.marketplace,
            "price":        float(ad.price) if ad.price else None,
            "old_price":    float(ad.old_price) if ad.old_price else None,
            "free_shipping": bool(ad.free_shipping),
            "ad_status":    ad.status,
            "created_at":   ad.created_at.isoformat() if ad.created_at else None,
            "expires_at":   ad.expires_at.isoformat() if ad.expires_at else None,
            "views_count":  views,
            "clicks_count": clicks,
            "ctr":          ctr,
            # dados do último clique (quando disponível)
            "last_click_at": lc.clicked_at.isoformat() if lc and lc.clicked_at else None,
            "last_device":   lc.device if lc else None,
            "last_city":     lc.city if lc else None,
            "last_state":    lc.state if lc else None,
            "last_source":   lc.source if lc else None,
            "last_referrer": lc.referrer if lc else None,
            "last_ip":       (lc.ip_hash[:12] + "...") if lc and lc.ip_hash and len(lc.ip_hash) > 12 else (lc.ip_hash if lc else None),
        })

    return {
        "data":  results,
        "total": total,
        "page":  page,
        "pages": max(1, (total + limit - 1) // limit),
        "limit": limit,
    }


# --- PLANOS ---

@router.get("/plans")
def get_plans():
    return [
        {"id": 1, "name": "Free", "price": 0, "link_limit": 3, "status": "Ativo"},
        {"id": 2, "name": "Smart", "price": 9.90, "link_limit": 5, "status": "Ativo"},
        {"id": 3, "name": "Pro", "price": 29.90, "link_limit": 50, "status": "Ativo"},
        {"id": 4, "name": "Premium", "price": 79.00, "link_limit": 9999, "status": "Ativo"}
    ]
