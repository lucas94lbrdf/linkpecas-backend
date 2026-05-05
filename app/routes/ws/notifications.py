"""
app/routes/ws/notifications.py

Rota WebSocket: /ws/notifications?token=<access_token>

- Autentica via JWT na query string
- Mantém conexão aberta com heartbeat a cada 30s
- Persiste cada notificação recebida na tabela `notifications`
- Ao desconectar, remove do ConnectionManager
"""

import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.websocket_manager import manager
from app.db.session import SessionLocal
from app.models.user import User
from app.models.notification import Notification
from app.routes.api.auth import SECRET_KEY, ALGORITHM

logger = logging.getLogger("ws.notifications")

router = APIRouter()

HEARTBEAT_INTERVAL = 30  # segundos


def _verify_ws_token(token: str, db: Session) -> User | None:
    """Valida JWT e retorna o User, ou None se inválido."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        email = payload.get("sub")
        if not email:
            return None
        user = db.query(User).filter(User.email == email).first()
        return user
    except JWTError:
        return None


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    db: Session = SessionLocal()
    try:
        # ── Autenticação ──────────────────────────────────────────────────
        user = _verify_ws_token(token, db)
        if not user:
            await websocket.close(code=4001, reason="Token inválido ou expirado")
            return

        user_id = str(user.id)

        # ── Conectar ──────────────────────────────────────────────────────
        await manager.connect(websocket, user_id)

        # Notificações não lidas pendentes ao reconectar
        pending = (
            db.query(Notification)
            .filter(Notification.user_id == user.id, Notification.is_read == False)
            .order_by(Notification.created_at.asc())
            .limit(20)
            .all()
        )
        for notif in pending:
            try:
                await websocket.send_json({
                    "type": notif.type,
                    "id": str(notif.id),
                    "data": notif.data,
                    "created_at": notif.created_at.isoformat() if notif.created_at else None,
                    "is_read": notif.is_read,
                })
            except Exception:
                break

        # ── Loop principal ────────────────────────────────────────────────
        async def heartbeat():
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                try:
                    await websocket.send_json({"type": "ping", "ts": datetime.utcnow().isoformat()})
                except Exception:
                    break

        heartbeat_task = asyncio.create_task(heartbeat())

        try:
            while True:
                # Aguarda mensagem do cliente (ex: pong, mark_read)
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                    if msg.get("type") == "pong":
                        pass  # keepalive
                    elif msg.get("type") == "mark_read" and msg.get("id"):
                        notif = db.query(Notification).filter(
                            Notification.id == msg["id"],
                            Notification.user_id == user.id
                        ).first()
                        if notif:
                            notif.is_read = True
                            db.commit()
                except Exception:
                    pass

        except WebSocketDisconnect:
            pass
        finally:
            heartbeat_task.cancel()

    finally:
        await manager.disconnect(str(user.id) if user else "unknown")
        db.close()
