"""
app/core/link_health_metrics.py

Prometheus metrics for the link-health scraping system.
Integrates with existing Prometheus instrumentator via /metrics.
"""

import logging
from prometheus_client import Gauge, Histogram, Counter

logger = logging.getLogger("link_health_metrics")

# ─── Gauges (current state) ──────────────────────────────────────────────────────

link_health_total = Gauge(
    "link_health_total",
    "Current count of monitored links by marketplace and status",
    ["marketplace", "status"],
)

# ─── Histograms (duration) ───────────────────────────────────────────────────────

link_check_duration_seconds = Histogram(
    "link_check_duration_seconds",
    "Duration of individual link checks",
    ["marketplace"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 30.0, 60.0],
)

# ─── Counters (monotonic events) ─────────────────────────────────────────────────

link_deactivations_total = Counter(
    "link_deactivations_total",
    "Total link deactivations",
    ["marketplace", "reason"],
)


def record_check_result(marketplace: str, is_available: bool, duration_ms: int, signals: dict | None = None):
    """Call after every scraping check to feed Prometheus metrics."""
    status = "available" if is_available else "unavailable"
    duration_s = (duration_ms or 0) / 1000.0

    # Record duration histogram
    link_check_duration_seconds.labels(marketplace=marketplace).observe(duration_s)

    # If deactivated, increment counter
    if not is_available:
        signals = signals or {}
        if signals.get("http_404"):
            reason = "http_404"
        elif signals.get("out_of_stock_text"):
            reason = "out_of_stock"
        elif signals.get("redirect_home"):
            reason = "redirect_home"
        elif signals.get("timeout"):
            reason = "timeout"
        else:
            reason = "unknown"
        link_deactivations_total.labels(marketplace=marketplace, reason=reason).inc()


def refresh_gauges_from_db(db):
    """
    Refreshes the gauge snapshot from the DB.
    Called periodically (e.g. from a Celery beat task or on /summary request).
    """
    try:
        from app.models.ad import Ad
        from sqlalchemy import func, case

        rows = (
            db.query(
                Ad.marketplace,
                Ad.link_status,
                func.count(Ad.id).label("cnt"),
            )
            .filter(Ad.external_url.isnot(None), Ad.external_url != "")
            .group_by(Ad.marketplace, Ad.link_status)
            .all()
        )

        # Reset all known labels first, then set fresh values
        for r in rows:
            mkt = r.marketplace or "unknown"
            st = r.link_status or "pending_review"
            link_health_total.labels(marketplace=mkt, status=st).set(r.cnt)

    except Exception as e:
        logger.error(f"Failed to refresh Prometheus gauges: {e}")
