"""
app/routes/api/link_health.py

Endpoints administrativos para monitoramento de saúde dos links.
Alimenta o painel /admin/link-health no frontend.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, desc, and_, case, cast, Date
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ad import Ad
from app.models.link_check import LinkCheck
from app.models.user import User
from app.routes.api.auth import get_admin_user
from app.tasks.link_checker_tasks import check_all_active_links, check_single_link

logger = logging.getLogger("link_health")

router = APIRouter(dependencies=[Depends(get_admin_user)])


def _ad_base_query(db: Session, marketplace: Optional[str] = None):
    q = db.query(Ad).filter(Ad.external_url.isnot(None), Ad.external_url != "")
    if marketplace:
        q = q.filter(Ad.marketplace == marketplace)
    return q


# ─── a) Summary ─────────────────────────────────────────────────────────────────

@router.get("/summary")
def get_link_health_summary(
    marketplace: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Resumo geral da saúde dos links: totais, taxa de saúde, duração média."""
    base_q = _ad_base_query(db, marketplace)

    total_monitored = base_q.count()
    total_available = base_q.filter(
        (Ad.link_status == "active") | (Ad.link_status.is_(None))
    ).count()
    total_unavailable = base_q.filter(Ad.link_status == "unavailable").count()
    total_error = base_q.filter(Ad.link_status == "error").count()
    total_pending = base_q.filter(
        Ad.link_status == "pending_review"
    ).count()

    # Saúde considera ativos sobre o que já foi verificado (active+unavailable+error).
    verified = total_available + total_unavailable + total_error
    health_rate = round((total_available / verified) * 100, 1) if verified > 0 else 0.0

    dur_q = db.query(func.avg(LinkCheck.check_duration_ms))
    last_q = db.query(func.max(LinkCheck.checked_at))
    if marketplace:
        dur_q = dur_q.filter(LinkCheck.marketplace == marketplace)
        last_q = last_q.filter(LinkCheck.marketplace == marketplace)
    avg_duration = dur_q.scalar()
    avg_check_duration_ms = round(float(avg_duration), 1) if avg_duration else 0.0
    last_check = last_q.scalar()

    # Refresh Prometheus gauges
    try:
        from app.core.link_health_metrics import refresh_gauges_from_db
        refresh_gauges_from_db(db)
    except Exception:
        pass

    return {
        "total_monitored": total_monitored,
        "total_available": total_available,
        "total_unavailable": total_unavailable,
        "total_error": total_error,
        "total_pending": total_pending,
        "health_rate": health_rate,
        "avg_check_duration_ms": avg_check_duration_ms,
        "last_full_check_at": last_check.isoformat() if last_check else None,
        "marketplace": marketplace,
    }


# ─── b) By Marketplace ──────────────────────────────────────────────────────────

@router.get("/by-marketplace")
def get_link_health_by_marketplace(
    marketplace: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Distribuição de saúde agrupada por marketplace."""
    q = (
        db.query(
            Ad.marketplace,
            func.count(Ad.id).label("total"),
            func.sum(case(((Ad.link_status == "active") | (Ad.link_status.is_(None)), 1), else_=0)).label("available"),
            func.sum(case((Ad.link_status == "unavailable", 1), else_=0)).label("unavailable"),
            func.sum(case((Ad.link_status == "error", 1), else_=0)).label("error"),
            func.sum(case((Ad.link_status == "pending_review", 1), else_=0)).label("pending"),
        )
        .filter(Ad.external_url.isnot(None), Ad.external_url != "")
        .group_by(Ad.marketplace)
        .order_by(desc("total"))
    )
    if marketplace:
        q = q.filter(Ad.marketplace == marketplace)

    rows = q.all()

    out = []
    for r in rows:
        verified = int(r.available or 0) + int(r.unavailable or 0) + int(r.error or 0)
        out.append({
            "marketplace": r.marketplace or "Desconhecido",
            "total": int(r.total or 0),
            "available": int(r.available or 0),
            "unavailable": int(r.unavailable or 0),
            "error": int(r.error or 0),
            "pending": int(r.pending or 0),
            "health_rate": round((int(r.available or 0) / verified) * 100, 1) if verified > 0 else 0.0,
        })
    return out


# ─── c) Trend ────────────────────────────────────────────────────────────────────

@router.get("/trend")
def get_link_health_trend(
    period: str = Query(default="30d", pattern=r"^\d+[dw]$"),
    marketplace: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Série temporal de disponibilidade, agrupada por dia."""
    unit = period[-1]
    amount = int(period[:-1])
    days = amount * 7 if unit == "w" else amount

    since = datetime.utcnow() - timedelta(days=days)

    q = (
        db.query(
            cast(LinkCheck.checked_at, Date).label("date"),
            func.count(LinkCheck.id).label("total_checks"),
            func.sum(case((LinkCheck.is_available == True, 1), else_=0)).label("available_count"),
            func.sum(case((LinkCheck.is_available == False, 1), else_=0)).label("unavailable_count"),
        )
        .filter(LinkCheck.checked_at >= since)
        .group_by(cast(LinkCheck.checked_at, Date))
        .order_by(cast(LinkCheck.checked_at, Date))
    )
    if marketplace:
        q = q.filter(LinkCheck.marketplace == marketplace)

    rows = q.all()
    return [
        {
            "date": str(r.date),
            "total_checks": int(r.total_checks or 0),
            "available_count": int(r.available_count or 0),
            "unavailable_count": int(r.unavailable_count or 0),
            "health_rate": round((int(r.available_count or 0) / int(r.total_checks or 1)) * 100, 1) if r.total_checks else 0.0,
        }
        for r in rows
    ]


# ─── d) Recent Deactivations ────────────────────────────────────────────────────

@router.get("/recent-deactivations")
def get_recent_deactivations(
    limit: int = Query(default=20, ge=1, le=100),
    marketplace: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Últimas desativações automáticas por link indisponível."""
    q = (
        db.query(LinkCheck, Ad, User)
        .join(Ad, LinkCheck.ad_id == Ad.id)
        .outerjoin(User, Ad.user_id == User.id)
        .filter(LinkCheck.is_available == False)
        .order_by(desc(LinkCheck.checked_at))
    )
    if marketplace:
        q = q.filter(Ad.marketplace == marketplace)
    rows = q.limit(limit * 3).all()  # buffer pra deduplicar abaixo

    seen = set()
    results = []
    for check, ad, user in rows:
        if str(ad.id) in seen:
            continue
        seen.add(str(ad.id))

        signals = check.signals_json or {}
        if signals.get("http_404"):
            reason = "Erro 404"
        elif signals.get("out_of_stock_text"):
            reason = "Produto Esgotado"
        elif signals.get("redirect_home"):
            reason = "Redirecionado para Home"
        elif signals.get("timeout"):
            reason = "Timeout"
        else:
            reason = "Link Indisponível"

        results.append({
            "ad_id": str(ad.id),
            "ad_title": ad.title,
            "shop_name": (user.shop_name or user.name) if user else "Desconhecido",
            "marketplace": ad.marketplace,
            "reason": reason,
            "http_status": check.http_status,
            "deactivated_at": check.checked_at.isoformat() if check.checked_at else None,
        })
        if len(results) >= limit:
            break

    return results


# ─── e) Worst Shops ─────────────────────────────────────────────────────────────

@router.get("/worst-shops")
def get_worst_shops(
    limit: int = Query(default=10, ge=1, le=50),
    marketplace: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Top lojistas com mais links quebrados."""
    q = (
        db.query(
            User.id.label("shop_id"),
            func.coalesce(User.shop_name, User.name).label("shop_name"),
            func.count(Ad.id).label("total_ads"),
            func.sum(case((Ad.link_status == "unavailable", 1), else_=0)).label("broken_links"),
        )
        .join(Ad, User.id == Ad.user_id)
        .filter(Ad.external_url.isnot(None), Ad.external_url != "")
        .group_by(User.id, User.shop_name, User.name)
        .having(func.sum(case((Ad.link_status == "unavailable", 1), else_=0)) > 0)
        .order_by(desc("broken_links"))
        .limit(limit)
    )
    if marketplace:
        q = q.filter(Ad.marketplace == marketplace)

    return [
        {
            "shop_id": str(r.shop_id),
            "shop_name": r.shop_name or "Sem Nome",
            "total_ads": int(r.total_ads or 0),
            "broken_links": int(r.broken_links or 0),
            "broken_rate": round((int(r.broken_links or 0) / int(r.total_ads or 1)) * 100, 1) if r.total_ads else 0.0,
        }
        for r in q.all()
    ]


# ─── f) Check History ───────────────────────────────────────────────────────────

@router.get("/check-history/{ad_id}")
def get_check_history(
    ad_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Histórico de verificações de um anúncio específico."""
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anúncio não encontrado")

    checks = (
        db.query(LinkCheck)
        .filter(LinkCheck.ad_id == ad_id)
        .order_by(desc(LinkCheck.checked_at))
        .limit(limit)
        .all()
    )

    return {
        "ad_id": str(ad.id),
        "ad_title": ad.title,
        "current_status": ad.link_status,
        "external_url": ad.external_url,
        "checks": [
            {
                "id": str(c.id),
                "http_status": c.http_status,
                "is_available": c.is_available,
                "signals": c.signals_json or {},
                "price_found": c.price_found,
                "price_previous": c.price_previous,
                "error_message": c.error_message,
                "check_duration_ms": c.check_duration_ms,
                "checked_at": c.checked_at.isoformat() if c.checked_at else None,
            }
            for c in checks
        ],
    }


# ─── Force Check ─────────────────────────────────────────────────────────────────

@router.post("/force-check")
def force_check_all_links(
    marketplace: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Admin força verificação completa de todos os links fora do horário agendado."""
    q = db.query(Ad).filter(Ad.external_url.isnot(None), Ad.external_url != "")
    if marketplace:
        q = q.filter(Ad.marketplace == marketplace)
    count = q.count()

    if count == 0:
        return {"queued_checks": 0, "estimated_time_minutes": 0}

    if marketplace:
        # Enfileira apenas os anúncios filtrados
        for ad in q.all():
            check_single_link.delay(str(ad.id), ad.external_url)
    else:
        check_all_active_links.delay()

    estimated_minutes = max(1, round((count * 2) / 60))
    logger.info(f"Admin forçou verificação de {count} links (marketplace={marketplace}). ETA: {estimated_minutes}min")

    return {
        "queued_checks": count,
        "estimated_time_minutes": estimated_minutes,
    }
