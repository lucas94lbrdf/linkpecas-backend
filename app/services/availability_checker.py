import re
import logging
from sqlalchemy.orm import Session
from app.models.ad import Ad
from app.models.link_check import LinkCheck
from .scrapers import MercadoLivreScraper, OlxScraper, ShopeeScraper, GenericScraper
from app.core.link_health_metrics import record_check_result

logger = logging.getLogger(__name__)

async def check_link(ad_id: str, url: str, db: Session) -> LinkCheck:
    """
    Identifies marketplace, runs scraper, calculates score and updates ad.
    """
    domain = ""
    scraper = GenericScraper()
    marketplace = "generic"
    
    if "mercadolivre.com" in url or "mlb" in url:
        marketplace = "mercadolivre"
        scraper = MercadoLivreScraper()
    elif "olx.com.br" in url:
        marketplace = "olx"
        scraper = OlxScraper()
    elif "shopee.com.br" in url:
        marketplace = "shopee"
        scraper = ShopeeScraper()
        
    result = await scraper.check_availability(url)
    
    score = 0
    signals = result.signals
    
    if signals.get('http_404'):
        score += 100
    if signals.get('redirect_home'):
        score += 90
    if signals.get('out_of_stock_text'):
        score += 95
    if signals.get('price_missing'):
        score += 85
    if signals.get('buy_button_missing'):
        score += 80
        
    if result.error and 'Timeout' in result.error:
        score += 60 # Might be cloudflare, retry later

    is_available = score < 80
    
    link_check = LinkCheck(
        ad_id=ad_id,
        external_url=url,
        marketplace=marketplace,
        http_status=result.http_status,
        is_available=is_available,
        signals_json=signals,
        price_found=result.price,
        error_message=result.error,
        check_duration_ms=result.duration_ms
    )
    db.add(link_check)
    
    # Update Ad
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if ad:
        ad.last_link_check_at = link_check.created_at
        if not is_available:
            ad.link_status = 'unavailable'
            ad.status = 'inactive'
            
            # TODO: Send WebSocket notification & email
            import asyncio
            from app.services.notification_service import notify_ad_deactivated
            try:
                asyncio.create_task(notify_ad_deactivated(db, ad.user_id, str(ad.id), ad.title))
            except Exception as e:
                logger.error(f"Failed to notify WS: {e}")
                
        else:
            ad.link_status = 'active'

    # ── Prometheus metrics ────────────────────────────────────────────────────
    try:
        record_check_result(marketplace, is_available, result.duration_ms, signals)
    except Exception as e:
        logger.warning(f"Prometheus metrics recording failed: {e}")
            
    db.commit()
    
    return link_check
