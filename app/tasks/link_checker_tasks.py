import asyncio
import logging
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.ad import Ad
from app.services.availability_checker import check_link

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.link_checker_tasks.check_single_link")
def check_single_link(ad_id: str, url: str):
    logger.info(f"Checking link for ad {ad_id}: {url}")
    db = SessionLocal()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        loop.run_until_complete(check_link(ad_id, url, db))
    except Exception as e:
        logger.error(f"Error checking link {url}: {e}")
    finally:
        db.close()

@celery_app.task(name="app.tasks.link_checker_tasks.check_all_active_links")
def check_all_active_links():
    logger.info("Starting batch check for all active links")
    db = SessionLocal()
    try:
        ads = db.query(Ad).filter(
            Ad.status == 'active',
            Ad.external_url.isnot(None),
            Ad.external_url != ''
        ).all()
        
        for ad in ads:
            # Enqueue individual tasks to process in parallel
            check_single_link.delay(str(ad.id), ad.external_url)

        # Refresh Prometheus gauges snapshot
        try:
            from app.core.link_health_metrics import refresh_gauges_from_db
            refresh_gauges_from_db(db)
        except Exception as e:
            logger.warning(f"Prometheus gauge refresh failed: {e}")

        # Run alert checks
        try:
            from app.services.link_health_alerting import run_all_alerts
            alerts = run_all_alerts(db)
            if alerts.get("marketplace_alerts"):
                logger.critical(f"Marketplace alerts triggered: {alerts['marketplace_alerts']}")
            if alerts.get("shop_alerts"):
                logger.warning(f"Shop alerts triggered: {alerts['shop_alerts']}")
        except Exception as e:
            logger.warning(f"Alert checks failed: {e}")

    except Exception as e:
        logger.error(f"Error scheduling batch link checks: {e}")
    finally:
        db.close()

