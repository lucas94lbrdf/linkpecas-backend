from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.db.session import get_db
from app.models.ad import Ad
from app.models.click import ClickEvent
from app.routes.api.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/")
def get_user_analytics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Retorna analytics baseados no plano do usuário.
    """
    plan = (user.role == "admin") and "premium" or (user.plan or "free").lower()
    user_ads = db.query(Ad.id).filter(Ad.user_id == user.id).all()
    ad_ids = [ad.id for ad in user_ads]

    if not ad_ids:
        return {"plan": plan, "summary": {}, "details": {}}

    # --- MÉTRICAS BÁSICAS (FREE+) ---
    total_clicks = db.query(ClickEvent).filter(ClickEvent.ad_id.in_(ad_ids)).count()
    
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    last_7_days_clicks = db.query(ClickEvent).filter(
        ClickEvent.ad_id.in_(ad_ids),
        ClickEvent.clicked_at >= seven_days_ago
    ).count()

    top_link_query = db.query(
        Ad.title, 
        func.count(ClickEvent.id).label('clicks')
    ).join(ClickEvent, Ad.id == ClickEvent.ad_id)\
     .filter(Ad.user_id == user.id)\
     .group_by(Ad.title)\
     .order_by(desc('clicks'))\
     .first()
    
    top_link = top_link_query[0] if top_link_query else "Nenhum"
    
    last_click_query = db.query(ClickEvent.clicked_at)\
                         .filter(ClickEvent.ad_id.in_(ad_ids))\
                         .order_by(desc(ClickEvent.clicked_at))\
                         .first()
    last_click = last_click_query[0] if last_click_query else None

    response = {
        "plan": plan,
        "summary": {
            "total_clicks": total_clicks,
            "last_7_days": last_7_days_clicks,
            "top_link": top_link,
            "last_click": last_click
        }
    }

    # --- MÉTRICAS ESSENCIAIS (SMART+) ---
    if plan in ["smart", "pro", "premium"]:
        # Cliques por link
        clicks_by_link = db.query(
            Ad.title, 
            func.count(ClickEvent.id).label('clicks')
        ).join(ClickEvent, Ad.id == ClickEvent.ad_id)\
         .filter(Ad.user_id == user.id)\
         .group_by(Ad.title)\
         .order_by(desc('clicks'))\
         .all()
        
        response["clicks_by_link"] = [{"title": r[0], "clicks": r[1]} for r in clicks_by_link]

        # Cliques por dia (últimos 30 dias)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        clicks_by_day = db.query(
            func.date(ClickEvent.clicked_at).label('day'),
            func.count(ClickEvent.id)
        ).filter(
            ClickEvent.ad_id.in_(ad_ids),
            ClickEvent.clicked_at >= thirty_days_ago
        ).group_by('day').order_by('day').all()
        
        response["clicks_by_day"] = [{"day": str(r[0]), "clicks": r[1]} for r in clicks_by_day]

        # Origem principal
        top_sources = db.query(
            ClickEvent.source,
            func.count(ClickEvent.id).label('count')
        ).filter(ClickEvent.ad_id.in_(ad_ids))\
         .group_by(ClickEvent.source)\
         .order_by(desc('count'))\
         .limit(5).all()
        
        response["top_sources"] = [{"source": r[0] or "Direto", "count": r[1]} for r in top_sources]

    # --- MÉTRICAS COMPLETAS (PRO+) ---
    if plan in ["pro", "premium"]:
        # Detalhamento de origem (subsource, campaign, creative)
        # Campaign performance
        campaigns = db.query(
            ClickEvent.campaign,
            func.count(ClickEvent.id).label('count')
        ).filter(ClickEvent.ad_id.in_(ad_ids), ClickEvent.campaign != None)\
         .group_by(ClickEvent.campaign)\
         .order_by(desc('count')).all()
        
        response["campaigns"] = [{"name": r[0], "clicks": r[1]} for r in campaigns]

        # Devices
        devices = db.query(
            ClickEvent.device,
            func.count(ClickEvent.id).label('count')
        ).filter(ClickEvent.ad_id.in_(ad_ids))\
         .group_by(ClickEvent.device).all()
        
        response["devices"] = [{"name": r[0] or "Desconhecido", "count": r[1]} for r in devices]

        # Cities
        cities = db.query(
            ClickEvent.city,
            func.count(ClickEvent.id).label('count')
        ).filter(ClickEvent.ad_id.in_(ad_ids), ClickEvent.city != None)\
         .group_by(ClickEvent.city)\
         .order_by(desc('count')).limit(10).all()
        
        response["top_cities"] = [{"name": r[0], "count": r[1]} for r in cities]

    # --- MÉTRICAS AVANÇADAS (PREMIUM) ---
    if plan == "premium":
        # Mocking some advanced metrics as requested (previsão IA, benchmarking etc)
        response["advanced"] = {
            "prediction": "Crescimento estimado de 15% nos próximos 30 dias",
            "benchmarking": "Sua performance está 24% acima da média da categoria",
            "roi_estimate": 4.2
        }

    return response

# --- NOVAS ROTAS DE ANALYTICS GLOBAL (ADMIN) ---

@router.get("/marketplaces")
def get_marketplaces_analytics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    data = db.query(
        Ad.marketplace, 
        func.count(ClickEvent.id).label('clicks')
    ).join(ClickEvent, Ad.id == ClickEvent.ad_id)\
     .group_by(Ad.marketplace)\
     .order_by(desc('clicks')).all()
     
    return [{"name": r[0] or "Outros", "value": r[1]} for r in data]


@router.get("/top-manufacturers")
def get_top_manufacturers(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    # Usando o modelo Manufacturer (já importado) e AdCompatibility
    from app.models.vehicle import Manufacturer
    from app.models.ad_compatibility import AdCompatibility
    
    # Cliques nos anúncios que tem compatibilidade
    data = db.query(
        Manufacturer.name,
        func.count(ClickEvent.id).label('clicks')
    ).join(AdCompatibility, Manufacturer.id == AdCompatibility.manufacturer_id)\
     .join(Ad, Ad.id == AdCompatibility.ad_id)\
     .join(ClickEvent, Ad.id == ClickEvent.ad_id)\
     .group_by(Manufacturer.name)\
     .order_by(desc('clicks'))\
     .limit(10).all()
     
    return [{"name": r[0], "clicks": r[1]} for r in data]


@router.get("/communities-performance")
def get_communities_performance(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    from app.models.community import Community
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    from sqlalchemy import cast

    # Agrupa por comunidade e anúncio para ver qual produto performa melhor em qual grupo
    # Filtramos apenas cliques de comunidade
    data = db.query(
        Community.name.label('community_name'),
        Ad.title.label('ad_title'),
        Ad.slug.label('ad_slug'),
        func.count(ClickEvent.id).label('clicks')
    ).select_from(ClickEvent)\
     .join(Ad, ClickEvent.ad_id == Ad.id)\
     .join(Community, cast(ClickEvent.source_ref, PG_UUID) == Community.id)\
     .filter(ClickEvent.source_type == 'community')\
     .group_by(Community.name, Ad.title, Ad.slug)\
     .order_by(desc('clicks')).limit(20).all()
     
    return [
        {
            "community": r.community_name,
            "product": r.ad_title,
            "slug": r.ad_slug,
            "clicks": r.clicks
        } for r in data
    ]


@router.get("/top-demands")
def get_top_demands(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito")
        
    from app.models.search_log import SearchLog
    
    # Buscas mais frequentes onde não houve resultados (demanda reprimida)
    data = db.query(
        SearchLog.term,
        SearchLog.origin,
        func.count(SearchLog.id).label('searches')
    ).filter(SearchLog.results_found == 0)\
     .group_by(SearchLog.term, SearchLog.origin)\
     .order_by(desc('searches')).limit(10).all()
     
    return [{"term": r[0] or "N/A", "origin": r[1], "searches": r[2]} for r in data]