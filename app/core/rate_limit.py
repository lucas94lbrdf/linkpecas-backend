import time
import logging
from datetime import datetime
from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_ipaddr
import redis

# Configuração do Redis para o Limiter e as estatísticas
redis_url = "redis://redis:6379"
redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

logger = logging.getLogger("rate_limiter")
logger.setLevel(logging.INFO)

def get_remote_address(request: Request) -> str:
    """Extrai IP real do header X-Forwarded-For se existir, senão usa o IP direto."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_ipaddr(request)

# Instância global do Limiter usando Redis
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=redis_url,
    default_limits=["60/minute"]
)

def log_rate_limit_exceeded(ip: str, route: str):
    """Salva estatísticas no Redis e loga o evento para o Loki."""
    now = int(time.time())
    today = datetime.utcnow().strftime('%Y-%m-%d')
    hour = datetime.utcnow().strftime('%Y-%m-%d %H:00')

    # Log para Grafana/Loki
    logger.warning(f"RateLimitExceeded - IP: {ip} - Route: {route} - Timestamp: {now}")

    # Estatísticas no Redis
    try:
        # Total bloqueado por rota hoje
        redis_client.hincrby(f"ratelimit:route:{today}", route, 1)
        redis_client.expire(f"ratelimit:route:{today}", 86400 * 2)

        # Top IPs bloqueados hoje
        redis_client.zincrby(f"ratelimit:ips:{today}", 1, ip)
        redis_client.expire(f"ratelimit:ips:{today}", 86400 * 2)

        # Bloqueados por hora (mantém histórico geral para o gráfico)
        redis_client.hincrby("ratelimit:hourly", hour, 1)
        # Limpa chaves antigas se quiser, mas hourly é pequeno
    except Exception as e:
        logger.error(f"Erro ao salvar stats no Redis: {e}")
