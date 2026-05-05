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


# ─── a) Summary ─────────────────────────────────────────────────────────────────

@router.get("/summary")
def get_link_health_summary(db: Session = Depends(get_db)):
    """Resumo geral da saúde dos links: totais, taxa de saúde, duração média."""
    base_q = db.query(Ad).filter(
        Ad.external_url.isnot(None),
        Ad.external_url != ""
    )

    total_monitored = base_q.count()
    total_available = base_q.filter(Ad.link_status == "active").count()
    total_unavailable = base_q.filter(Ad.link_status == "unavailable").count()
    total_error = base_q.filter(Ad.link_status == "error").count()
    total_pending = base_q.filter(Ad.link_status == "pending_review").count()

    health_rate = round((total_available / total_monitored) * 100, 1) if total_monitored > 0 else 0.0

    avg_duration = db.query(func.avg(LinkCheck.check_duration_ms)).scalar()
    avg_check_duration_ms = round(float(avg_duration), 1) if avg_duration else 0.0

    last_check = db.query(func.max(LinkCheck.checked_at)).scalar()

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
    }


# ─── b) By Marketplace ──────────────────────────────────────────────────────────

@router.get("/by-marketplace")
def get_link_health_by_marketplace(db: Session = Depends(get_db)):
    """Distribuição de saúde agrupada por marketplace."""
    rows = (
        db.query(
            Ad.marketplace,
            func.count(Ad.id).label("total"),
            func.sum(case((Ad.link_status == "active", 1), else_=0)).label("available"),
            func.sum(case((Ad.link_status == "unavailable", 1), else_=0)).label("unavailable"),
            func.sum(case((Ad.link_status == "error", 1), else_=0)).label("error"),
        )
        .filter(Ad.external_url.isnot(None), Ad.external_url != "")
        .group_by(Ad.marketplace)
        .order_by(desc("total"))
        .all()
    )

    return [
        {
            "marketplace": r.marketplace or "Desconhecido",
            "total": r.total,
            "available": r.available,
            "unavailable": r.unavailable,
            "error": r.error,
            "health_rate": round((r.available / r.total) * 100, 1) if r.total > 0 else 0.0,
        }
        for r in rows
    ]


# ─── c) Trend ────────────────────────────────────────────────────────────────────

@router.get("/trend")
def get_link_health_trend(
    period: str = Query(default="30d", pattern=r"^\d+[dw]$"),
    db: Session = Depends(get_db),
):
    """Série temporal de disponibilidade, agrupada por dia."""
    # Parse period
    unit = period[-1]
    amount = int(period[:-1])
    if unit == "w":
        days = amount * 7
    else:
        days = amount

    since = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(
            cast(LinkCheck.checked_at, Date).label("date"),
            func.count(LinkCheck.id).label("total_checks"),
            func.sum(case((LinkCheck.is_available == True, 1), else_=0)).label("available_count"),
            func.sum(case((LinkCheck.is_available == False, 1), else_=0)).label("unavailable_count"),
        )
        .filter(LinkCheck.checked_at >= since)
        .group_by(cast(LinkCheck.checked_at, Date))
        .order_by(cast(LinkCheck.checked_at, Date))
        .all()
    )

    return [
        {
            "date": str(r.date),
            "total_checks": r.total_checks,
            "available_count": r.available_count,
            "unavailable_count": r.unavailable_count,
            "health_rate": round((r.available_count / r.total_checks) * 100, 1) if r.total_checks > 0 else 0.0,
        }
        for r in rows
    ]


# ─── d) Recent Deactivations ────────────────────────────────────────────────────

@router.get("/recent-deactivations")
def get_recent_deactivations(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Últimas desativações automáticas por link indisponível."""
    rows = (
        db.query(LinkCheck, Ad, User)
        .join(Ad, LinkCheck.ad_id == Ad.id)
        .outerjoin(User, Ad.user_id == User.id)
        .filter(LinkCheck.is_available == False)
        .order_by(desc(LinkCheck.checked_at))
        .limit(limit)
        .all()
    )

    # Deduplica por ad_id (mostra só a última desativação de cada anúncio)
    seen = set()
    results = []
    for check, ad, user in rows:
        if str(ad.id) in seen:
            continue
        seen.add(str(ad.id))

        # Determina motivo a partir dos sinais
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

    return results


# ─── e) Worst Shops ─────────────────────────────────────────────────────────────

@router.get("/worst-shops")
def get_worst_shops(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Top lojistas com mais links quebrados."""
    rows = (
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
        .all()
    )

    return [
        {
            "shop_id": str(r.shop_id),
            "shop_name": r.shop_name or "Sem Nome",
            "total_ads": r.total_ads,
            "broken_links": r.broken_links,
            "broken_rate": round((r.broken_links / r.total_ads) * 100, 1) if r.total_ads > 0 else 0.0,
        }
        for r in rows
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
def force_check_all_links(db: Session = Depends(get_db)):
    """Admin força verificação completa de todos os links fora do horário agendado."""
    count = (
        db.query(Ad)
        .filter(
            Ad.external_url.isnot(None),
            Ad.external_url != "",
        )
        .count()
    )

    if count == 0:
        return {"queued_checks": 0, "estimated_time_minutes": 0}

    # Dispara a task Celery assíncrona
    check_all_active_links.delay()

    # Estimativa: ~2s por link (delay + request + parse)
    estimated_minutes = max(1, round((count * 2) / 60))

    logger.info(f"Admin forçou verificação de {count} links. ETA: {estimated_minutes}min")

    return {
        "queued_checks": count,
        "estimated_time_minutes": estimated_minutes,
    }
