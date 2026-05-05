"""
app/services/link_health_alerting.py

Alert system for link health degradation.
- Logs critical alerts to Loki-compatible structured logging.
- Notifies admins via WebSocket when a shop exceeds the broken-link threshold.
"""

import asyncio
import logging
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.models.ad import Ad
from app.models.user import User

logger = logging.getLogger("link_health_alerts")

# Thresholds
MARKETPLACE_HEALTH_THRESHOLD = 80.0   # Alerta se saúde cair abaixo de 80%
SHOP_BROKEN_THRESHOLD = 5             # Alerta se lojista tiver > 5 links quebrados


def check_marketplace_alerts(db: Session):
    """
    Verifica a taxa de saúde por marketplace.
    Se qualquer marketplace cair abaixo do threshold, loga alerta crítico (Loki-compatible).
    """
    rows = (
        db.query(
            Ad.marketplace,
            func.count(Ad.id).label("total"),
            func.sum(case((Ad.link_status == "active", 1), else_=0)).label("available"),
        )
        .filter(Ad.external_url.isnot(None), Ad.external_url != "")
        .group_by(Ad.marketplace)
        .all()
    )

    alerts = []
    for r in rows:
        if r.total == 0:
            continue
        health_rate = (r.available / r.total) * 100
        if health_rate < MARKETPLACE_HEALTH_THRESHOLD:
            alert_msg = (
                f"CRITICAL: Marketplace '{r.marketplace}' health dropped to {health_rate:.1f}% "
                f"({r.available}/{r.total} links available). Threshold: {MARKETPLACE_HEALTH_THRESHOLD}%"
            )
            logger.critical(alert_msg, extra={
                "alert_type": "marketplace_health_degraded",
                "marketplace": r.marketplace,
                "health_rate": round(health_rate, 1),
                "total": r.total,
                "available": r.available,
                "threshold": MARKETPLACE_HEALTH_THRESHOLD,
            })
            alerts.append({
                "marketplace": r.marketplace,
                "health_rate": round(health_rate, 1),
                "total": r.total,
                "available": r.available,
            })

    return alerts


def check_shop_alerts(db: Session):
    """
    Verifica lojistas com excesso de links quebrados.
    Se algum lojista ultrapassar o threshold, envia notificação ao admin.
    """
    rows = (
        db.query(
            User.id.label("shop_id"),
            func.coalesce(User.shop_name, User.name).label("shop_name"),
            func.sum(case((Ad.link_status == "unavailable", 1), else_=0)).label("broken"),
            func.count(Ad.id).label("total"),
        )
        .join(Ad, User.id == Ad.user_id)
        .filter(Ad.external_url.isnot(None), Ad.external_url != "")
        .group_by(User.id, User.shop_name, User.name)
        .having(func.sum(case((Ad.link_status == "unavailable", 1), else_=0)) > SHOP_BROKEN_THRESHOLD)
        .all()
    )

    alerts = []
    for r in rows:
        alert_msg = (
            f"WARNING: Shop '{r.shop_name}' (id={r.shop_id}) has {r.broken} broken links "
            f"out of {r.total}. Threshold: {SHOP_BROKEN_THRESHOLD}"
        )
        logger.warning(alert_msg, extra={
            "alert_type": "shop_broken_links",
            "shop_id": str(r.shop_id),
            "shop_name": r.shop_name,
            "broken_links": r.broken,
            "total_ads": r.total,
        })
        alerts.append({
            "shop_id": str(r.shop_id),
            "shop_name": r.shop_name,
            "broken_links": r.broken,
            "total_ads": r.total,
        })

    # Notify all admins via WebSocket if there are shop alerts
    if alerts:
        _notify_admins_async(db, alerts)

    return alerts


def _notify_admins_async(db: Session, shop_alerts: list):
    """Fire-and-forget admin notifications."""
    try:
        from app.services.notification_service import notify

        admin_users = db.query(User).filter(User.role == "admin").all()
        for admin in admin_users:
            for alert in shop_alerts:
                try:
                    asyncio.create_task(
                        notify(
                            db,
                            admin.id,
                            "admin_link_alert",
                            {
                                "shop_name": alert["shop_name"],
                                "broken_links": alert["broken_links"],
                                "message": f"Lojista '{alert['shop_name']}' tem {alert['broken_links']} links quebrados.",
                            },
                        )
                    )
                except RuntimeError:
                    # No event loop running (called from Celery worker)
                    logger.info(f"Skipping WS notification in sync context for admin {admin.id}")
    except Exception as e:
        logger.error(f"Failed to send admin notifications: {e}")


def run_all_alerts(db: Session):
    """Run all alert checks. Call from Celery beat or after a batch check."""
    marketplace_alerts = check_marketplace_alerts(db)
    shop_alerts = check_shop_alerts(db)
    return {
        "marketplace_alerts": marketplace_alerts,
        "shop_alerts": shop_alerts,
    }
