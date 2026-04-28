from app.db.session import SessionLocal
from app.models.ad import Ad

db = SessionLocal()
ads = db.query(Ad).all()
fixed = 0
for ad in ads:
    url = ad.external_url or ""
    new_mkt = ad.marketplace
    if "mercadolivre.com" in url:
        new_mkt = "Mercado Livre"
    elif "shopee.com" in url or "shp.ee" in url:
        new_mkt = "Shopee"
    elif "amazon.com" in url:
        new_mkt = "Amazon"
    elif "aliexpress.com" in url:
        new_mkt = "AliExpress"
    
    if new_mkt != ad.marketplace:
        ad.marketplace = new_mkt
        fixed += 1

db.commit()
print(f"Corrigidos {fixed} anuncios no banco de dados.")
