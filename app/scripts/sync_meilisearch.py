import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import SessionLocal
from app.models.ad import Ad
from app.models.user import User
from app.models.vehicle import Manufacturer, VehicleModel
from app.services.search_service import client, INDEX_NAME, init_meilisearch_index

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_sync():
    logger.info("Iniciando sincronização completa com Meilisearch...")
    
    init_meilisearch_index()
    
    db = SessionLocal()
    try:
        # Pega a query com joins
        query = db.query(Ad, User, Manufacturer, VehicleModel).outerjoin(
            User, Ad.user_id == User.id
        ).outerjoin(
            Manufacturer, Ad.manufacturer_id == Manufacturer.id
        ).outerjoin(
            VehicleModel, Ad.model_id == VehicleModel.id
        ).filter(Ad.status == 'active')
        
        total_ads = query.count()
        logger.info(f"Encontrados {total_ads} anúncios ativos para indexar.")
        
        if total_ads == 0:
            logger.info("Nenhum anúncio para indexar.")
            return

        batch_size = 1000
        processed = 0
        
        for offset in range(0, total_ads, batch_size):
            ads_batch = query.offset(offset).limit(batch_size).all()
            
            documents = []
            for ad, user, manufacturer, model in ads_batch:
                doc = {
                    "id": str(ad.id),
                    "title": ad.title,
                    "description": ad.description,
                    "vehicle_brand": manufacturer.name if manufacturer else None,
                    "vehicle_model": model.name if model else None,
                    "year_min": ad.year_start,
                    "year_max": ad.year_end,
                    "price": float(ad.price) if ad.price else None,
                    "city": ad.city,
                    "state": ad.state,
                    "status": ad.status,
                    "category_id": str(ad.category_id) if ad.category_id else None,
                    "category_name": ad.category,
                    "shop_id": str(user.id) if user else None,
                    "shop_name": user.shop_name if user else None,
                    "created_at": ad.created_at.timestamp() if ad.created_at else None,
                    "views_count": ad.views_count
                }
                documents.append(doc)
            
            if documents:
                client.index(INDEX_NAME).add_documents(documents)
                processed += len(documents)
                logger.info(f"Indexados {processed}/{total_ads} anúncios...")
                
        logger.info("Sincronização com Meilisearch concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante a sincronização: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_sync()
