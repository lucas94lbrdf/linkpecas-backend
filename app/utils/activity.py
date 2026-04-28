import uuid
import httpx
from fastapi import Request
from sqlalchemy.orm import Session
from app.models.log import ActivityLog


def _get_device(ua: str) -> str:
    if not ua:
        return "unknown"
    ua_lower = ua.lower()
    if any(k in ua_lower for k in ("mobile", "android", "iphone", "windows phone")):
        return "mobile"
    if any(k in ua_lower for k in ("tablet", "ipad")):
        return "tablet"
    return "desktop"


def _get_location(ip: str) -> str | None:
    if not ip:
        return None
    private_prefixes = ("127.", "192.168.", "10.", "172.16.", "172.17.", "172.18.",
                        "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                        "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.",
                        "172.31.", "::1")
    if ip == "localhost" or any(ip.startswith(p) for p in private_prefixes):
        return "Local"
    try:
        resp = httpx.get(
            f"http://ip-api.com/json/{ip}?fields=status,city,regionName,country",
            timeout=3.0,
        )
        data = resp.json()
        if data.get("status") == "success":
            parts = [data.get("city"), data.get("regionName"), data.get("country")]
            return ", ".join(p for p in parts if p) or None
    except Exception:
        pass
    return None


def log_activity(
    db: Session,
    request: Request,
    action: str,
    entity_type: str = None,
    entity_id=None,
    details: str = None,
    user_id=None,
):
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    entry = ActivityLog(
        id=uuid.uuid4(),
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        details=details,
        ip_address=ip,
        user_agent=user_agent,
        http_method=request.method,
        device=_get_device(user_agent or ""),
        location=_get_location(ip),
    )
    db.add(entry)
    db.commit()
