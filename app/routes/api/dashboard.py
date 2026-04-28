import uuid as _uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from app.db.session import get_db
from app.models.user import User
from app.models.ad import Ad
from app.models.click import ClickEvent
from app.routes.api.auth import get_current_user

router = APIRouter()

PLAN_LIMITS = {
    "free": 3,
    "smart": 5,
    "pro": 50,
    "premium": 999999
}

@router.get("/")
def get_user_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    user_plan = (user.plan or "free").lower()
    user_id = user.id

    # 1. Total de Anúncios e Limites
    total_ads = db.query(Ad).filter(Ad.user_id == user_id).count()
    limit = PLAN_LIMITS.get(user_plan, 3)

    # 2. Cliques Totais (Impressões)
    user_ads_ids = db.query(Ad.id).filter(Ad.user_id == user_id).all()
    ad_ids = [ad[0] for ad in user_ads_ids]
    
    total_clicks = db.query(ClickEvent).filter(ClickEvent.ad_id.in_(ad_ids)).count() if ad_ids else 0
    
    # 3. Cliques do Mês Atual (Impressões no dashboard costuma ser tráfego recente)
    month_ago = datetime.utcnow() - timedelta(days=30)
    month_clicks = db.query(ClickEvent).filter(
        ClickEvent.ad_id.in_(ad_ids),
        ClickEvent.clicked_at >= month_ago
    ).count() if ad_ids else 0

    # 4. Dados do Gráfico (Últimos 7 dias)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    clicks_history = db.query(
        func.date(ClickEvent.clicked_at).label('day'),
        func.count(ClickEvent.id).label('count')
    ).filter(
        ClickEvent.ad_id.in_(ad_ids),
        ClickEvent.clicked_at >= seven_days_ago
    ).group_by('day').order_by('day').all() if ad_ids else []
    
    # Formatação dos dias da semana
    days_map = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sab", 6: "Dom"}
    chart_data = []
    for r in clicks_history:
        chart_data.append({
            "day": days_map[r[0].weekday()],
            "clicks": r[1]
        })

    # 5. Anúncios Recentes
    recent = db.query(Ad).filter(Ad.user_id == user_id).order_by(Ad.created_at.desc()).limit(3).all()

    return {
        "total_links": total_ads,
        "plan": user_plan.upper(),
        "plan_limit": limit,
        "used_percentage": (total_ads / limit) * 100 if limit > 0 else 0,
        "links_delta": 0,
        "impressions": f"{total_clicks / 1000:.1f}K" if total_clicks >= 1000 else str(total_clicks),
        "impressions_delta": 0,
        "conversion": 0, 
        "conversion_delta": 0,
        "leads": 0, 
        "leads_delta": 0,
        "chart": chart_data if chart_data else [
            {"day": "Seg", "clicks": 0},
            {"day": "Ter", "clicks": 0},
            {"day": "Qua", "clicks": 0},
            {"day": "Qui", "clicks": 0},
            {"day": "Sex", "clicks": 0},
            {"day": "Sab", "clicks": 0},
            {"day": "Dom", "clicks": 0},
        ],
        "recent_links": [
            {
                "id": str(ad.id),
                "title": ad.title,
                "price": float(ad.price) if ad.price else 0.0,
                "short_code": ad.short_code
            } for ad in recent
        ]
    }


# ── Agrupamento de links ───────────────────────────────────────────────────────

@router.post("/ads/group")
def group_ads(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ad_ids = data.get("ad_ids", [])
    if len(ad_ids) < 2:
        raise HTTPException(400, "Selecione pelo menos 2 anúncios para vincular.")

    ads = db.query(Ad).filter(Ad.id.in_(ad_ids), Ad.user_id == user.id).all()
    if len(ads) < 2:
        raise HTTPException(400, "Anúncios não encontrados ou não pertencem a você.")

    # Reusa group_id existente se algum já estiver em grupo, senão cria novo
    existing = next((a.group_id for a in ads if a.group_id), None)
    group_id = existing or _uuid.uuid4()

    for ad in ads:
        ad.group_id = group_id
    db.commit()

    return {"group_id": str(group_id), "linked": len(ads)}


@router.delete("/ads/{ad_id}/ungroup")
def ungroup_ad(
    ad_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ad = db.query(Ad).filter(Ad.id == ad_id, Ad.user_id == user.id).first()
    if not ad:
        raise HTTPException(404, "Anúncio não encontrado.")
    ad.group_id = None
    db.commit()
    return {"message": "Removido do grupo."}
