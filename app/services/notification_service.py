"""
app/services/notification_service.py

Centraliza criação, persistência e envio de notificações.

Uso:
    from app.services.notification_service import notify

    await notify(db, user_id, "ad_approved", {"ad_id": "...", "title": "..."})
"""

import json
import logging
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.core.websocket_manager import manager

logger = logging.getLogger("notification_service")


async def notify(
    db: Session,
    user_id: str | UUID,
    type: str,
    data: Dict[str, Any],
) -> Notification:
    """
    1. Persiste notificação no banco
    2. Envia via WebSocket (se usuário conectado) + Redis Pub/Sub
    """
    user_id_str = str(user_id)

    # ── Persistência ─────────────────────────────────────────────────────────
    notif = Notification(
        user_id=user_id,
        type=type,
        data_json=json.dumps(data, ensure_ascii=False),
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # ── Envio em tempo real ──────────────────────────────────────────────────
    message = {
        "type": type,
        "id": str(notif.id),
        "data": data,
        "created_at": notif.created_at.isoformat() if notif.created_at else None,
        "is_read": False,
    }

    try:
        await manager.send_to_user(user_id_str, message)
    except Exception as e:
        logger.warning(f"Falha ao enviar notificação WS para {user_id_str}: {e}")

    return notif


# ── Helpers tipados ──────────────────────────────────────────────────────────

async def notify_ad_approved(db: Session, user_id, ad_id: str, title: str):
    return await notify(db, user_id, "ad_approved", {"ad_id": ad_id, "title": title})


async def notify_ad_rejected(db: Session, user_id, ad_id: str, title: str, reason: str = ""):
    return await notify(db, user_id, "ad_rejected", {"ad_id": ad_id, "title": title, "reason": reason})


async def notify_ad_expired(db: Session, user_id, ad_id: str, title: str, expired_at: str = ""):
    return await notify(db, user_id, "ad_expired", {"ad_id": ad_id, "title": title, "expired_at": expired_at})


async def notify_new_lead(db: Session, user_id, ad_id: str, buyer_name: str, message: str = ""):
    return await notify(db, user_id, "new_lead", {"ad_id": ad_id, "buyer_name": buyer_name, "message": message})


async def notify_plan_updated(db: Session, user_id, old_plan: str, new_plan: str):
    return await notify(db, user_id, "plan_updated", {"old_plan": old_plan, "new_plan": new_plan})


async def notify_ad_deactivated(db: Session, user_id, ad_id: str, title: str, reason: str = "link_unavailable"):
    return await notify(db, user_id, "ad_deactivated", {"ad_id": ad_id, "title": title, "reason": reason})
