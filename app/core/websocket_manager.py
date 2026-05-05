"""
app/core/websocket_manager.py

ConnectionManager com suporte a Redis Pub/Sub para escalar
entre múltiplas instâncias de backend.

Fluxo:
  - Cada instância mantém conexões WS locais no dict `_connections`
  - Ao publicar para um user_id, publica no canal Redis `notif:{user_id}`
  - Um subscriber Redis escuta todos os canais e repassa ao WS local
"""

import asyncio
import json
import logging
import os
from typing import Dict

import redis.asyncio as aioredis
from fastapi import WebSocket

logger = logging.getLogger("websocket_manager")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/")

# Canal global para broadcast
BROADCAST_CHANNEL = "notif:*"


class ConnectionManager:
    def __init__(self):
        # user_id (str) → WebSocket
        self._connections: Dict[str, WebSocket] = {}
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if not self._redis:
            self._redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        return self._redis

    # ── Ciclo de vida ────────────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self._connections[user_id] = websocket
        logger.info(f"WS conectado: user_id={user_id} | total={len(self._connections)}")

    async def disconnect(self, user_id: str):
        self._connections.pop(user_id, None)
        logger.info(f"WS desconectado: user_id={user_id} | total={len(self._connections)}")

    # ── Envio ────────────────────────────────────────────────────────────────

    async def send_to_user(self, user_id: str, message: dict):
        """
        Entrega para a conexão local se existir,
        E publica no Redis para outras instâncias.
        """
        payload = json.dumps(message, ensure_ascii=False)

        # 1. Entrega local
        ws = self._connections.get(str(user_id))
        if ws:
            try:
                await ws.send_text(payload)
            except Exception as e:
                logger.warning(f"Falha ao enviar WS local para {user_id}: {e}")
                await self.disconnect(str(user_id))

        # 2. Publica no Redis (para outras instâncias)
        try:
            r = await self._get_redis()
            await r.publish(f"notif:{user_id}", payload)
        except Exception as e:
            logger.warning(f"Redis publish falhou para {user_id}: {e}")

    async def broadcast(self, message: dict):
        """Envia para todos os usuários conectados nesta instância."""
        payload = json.dumps(message, ensure_ascii=False)
        dead = []
        for uid, ws in self._connections.items():
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(uid)
        for uid in dead:
            await self.disconnect(uid)

    # ── Redis subscriber (rodar como background task no startup) ─────────────

    async def start_redis_subscriber(self):
        """
        Escuta todos os canais `notif:*` no Redis e entrega
        mensagens para conexões WS locais desta instância.
        """
        try:
            r = await self._get_redis()
            self._pubsub = r.pubsub()
            await self._pubsub.psubscribe(BROADCAST_CHANNEL)
            logger.info("Redis Pub/Sub subscriber iniciado (notif:*)")

            async for raw in self._pubsub.listen():
                if raw["type"] == "pmessage":
                    channel: str = raw["channel"]
                    user_id = channel.removeprefix("notif:")
                    data = raw["data"]
                    ws = self._connections.get(user_id)
                    if ws:
                        try:
                            await ws.send_text(data)
                        except Exception:
                            await self.disconnect(user_id)
        except asyncio.CancelledError:
            logger.info("Redis subscriber cancelado.")
        except Exception as e:
            logger.error(f"Erro no Redis subscriber: {e}")


# Instância global — importada por main.py e pelas rotas
manager = ConnectionManager()
