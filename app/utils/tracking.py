"""Utilitários para enriquecer eventos de tracking (cliques, buscas).

Centraliza extração de IP real (atrás de proxy/CDN), classificação de origem
do tráfego a partir do referrer/UTM, parsing de browser/OS do user-agent e
geração de hash anonimizado para agregações respeitando LGPD.
"""

import hashlib
import re
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs

from fastapi import Request


# Mapeia domínios conhecidos → categoria de origem.
# Ordem importa: prefixos mais específicos antes de genéricos.
_SOURCE_PATTERNS = [
    (r"(^|\.)google\.", "google"),
    (r"(^|\.)bing\.", "bing"),
    (r"(^|\.)duckduckgo\.", "duckduckgo"),
    (r"(^|\.)yahoo\.", "yahoo"),
    (r"(^|\.)yandex\.", "yandex"),
    (r"(^|\.)facebook\.|(^|\.)fb\.", "facebook"),
    (r"(^|\.)instagram\.", "instagram"),
    (r"(^|\.)t\.co|(^|\.)twitter\.|(^|\.)x\.com", "twitter"),
    (r"(^|\.)tiktok\.", "tiktok"),
    (r"(^|\.)youtube\.|(^|\.)youtu\.be", "youtube"),
    (r"(^|\.)linkedin\.", "linkedin"),
    (r"(^|\.)reddit\.", "reddit"),
    (r"(^|\.)telegram\.|(^|\.)t\.me", "telegram"),
    (r"(^|\.)whatsapp\.|(^|\.)wa\.me|api\.whatsapp", "whatsapp"),
    (r"(^|\.)pinterest\.", "pinterest"),
    (r"(^|\.)mercadolivre\.", "mercadolivre"),
    (r"(^|\.)olx\.", "olx"),
    (r"(^|\.)shopee\.", "shopee"),
    (r"(^|\.)amazon\.", "amazon"),
    (r"(^|\.)magazineluiza\.|(^|\.)magalu\.", "magalu"),
]


def get_real_ip(request: Request) -> str:
    """Retorna o IP real do cliente, considerando proxies/CDN.

    Ordem de checagem:
      1. X-Forwarded-For (primeiro IP da lista)
      2. X-Real-IP
      3. CF-Connecting-IP (Cloudflare)
      4. request.client.host
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()

    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()

    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()

    return request.client.host if request.client else "unknown"


def hash_ip(ip: str) -> str:
    """Gera hash determinístico do IP (16 chars) para agregações sem expor."""
    return hashlib.sha256((ip or "unknown").encode()).hexdigest()[:16]


def classify_source(referrer: Optional[str], utm_source: Optional[str] = None) -> str:
    """Classifica a origem do tráfego a partir do referrer e/ou utm_source.

    Retorna uma label curta tipo 'google', 'whatsapp', 'direct', 'site', etc.
    Prioridade: utm_source > referrer.
    """
    if utm_source:
        return utm_source.lower().strip()[:50]

    if not referrer:
        return "direct"

    try:
        host = urlparse(referrer).hostname or ""
    except Exception:
        return "direct"

    if not host:
        return "direct"

    host_lower = host.lower()

    for pattern, label in _SOURCE_PATTERNS:
        if re.search(pattern, host_lower):
            return label

    # Outras origens — registra o domínio raiz para inspeção posterior
    parts = host_lower.split(".")
    if len(parts) >= 2:
        return parts[-2][:50]
    return host_lower[:50]


def extract_utm(url: Optional[str]) -> dict:
    """Extrai utm_source, utm_medium, utm_campaign de uma URL.

    Aceita URL completa ou querystring isolada. Retorna dict com chaves possivelmente None.
    """
    out = {"utm_source": None, "utm_medium": None, "utm_campaign": None}
    if not url:
        return out
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query or url.lstrip("?"))
        for k in out:
            v = qs.get(k)
            if v:
                out[k] = v[0][:100]
    except Exception:
        pass
    return out


def parse_browser(ua: str) -> str:
    """Extrai o nome do navegador do user-agent."""
    if not ua:
        return "unknown"
    u = ua.lower()
    # Ordem importa: Edge contém "Chrome" no UA, Opera contém "Chrome", etc.
    if "edg/" in u or "edge/" in u:
        return "Edge"
    if "opr/" in u or "opera" in u:
        return "Opera"
    if "samsungbrowser" in u:
        return "Samsung"
    if "firefox" in u:
        return "Firefox"
    if "chrome" in u and "safari" in u:
        return "Chrome"
    if "safari" in u and "version/" in u:
        return "Safari"
    if "msie" in u or "trident" in u:
        return "IE"
    return "Other"


def parse_os(ua: str) -> str:
    """Extrai o sistema operacional do user-agent."""
    if not ua:
        return "unknown"
    u = ua.lower()
    if "android" in u:
        return "Android"
    if "iphone" in u or "ipad" in u or "ipod" in u or "ios" in u:
        return "iOS"
    if "windows" in u:
        return "Windows"
    if "mac os x" in u or "macintosh" in u:
        return "macOS"
    if "linux" in u:
        return "Linux"
    return "Other"


def enrich_request(request: Request, body_url: Optional[str] = None) -> dict:
    """Pacote completo de enriquecimento a partir de um Request.

    Retorna dict pronto para popular um ClickEvent ou SearchLog.
    """
    ip = get_real_ip(request)
    ua = request.headers.get("user-agent", "") or ""
    referrer = request.headers.get("referer", "") or ""
    utm = extract_utm(body_url) if body_url else {"utm_source": None, "utm_medium": None, "utm_campaign": None}

    return {
        "ip_address": ip,
        "ip_hash": hash_ip(ip),
        "user_agent": ua,
        "referrer": referrer,
        "browser": parse_browser(ua),
        "os": parse_os(ua),
        "source_category": classify_source(referrer, utm.get("utm_source")),
        **utm,
    }
