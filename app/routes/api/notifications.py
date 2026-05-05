"""
app/routes/api/notifications.py

Rotas REST para notificações (fallback para quem não suporta WebSocket).

GET    /api/notifications           → listar com paginação
GET    /api/notifications/unread-count → contador de não lidas
PATCH  /api/notifications/{id}/read → marcar uma como lida
PATCH  /api/notifications/read-all  → marcar todas como lidas
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.routes.api.auth import get_current_user

router = APIRouter()


def _serialize(n: Notification) -> dict:
    return {
        "id": str(n.id),
        "type": n.type,
        "data": n.data,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("/notifications")
def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista notificações do usuário autenticado com paginação."""
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        q = q.filter(Notification.is_read == False)
    total = q.count()
    items = q.order_by(Notification.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "items": [_serialize(n) for n in items],
    }


@router.get("/notifications/unread-count")
def unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna a quantidade de notificações não lidas."""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).count()
    return {"unread_count": count}


@router.patch("/notifications/read-all")
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marca todas as notificações do usuário como lidas."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"message": "Todas as notificações foram marcadas como lidas."}


@router.patch("/notifications/{notification_id}/read")
def mark_one_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marca uma notificação específica como lida."""
    try:
        nid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(400, "ID inválido")

    notif = db.query(Notification).filter(
        Notification.id == nid,
        Notification.user_id == current_user.id,
    ).first()

    if not notif:
        raise HTTPException(404, "Notificação não encontrada")

    notif.is_read = True
    db.commit()
    return _serialize(notif)
