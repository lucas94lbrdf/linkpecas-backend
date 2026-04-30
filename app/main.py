# ==========================================================
# app/main.py
# LINKPEÇAS API ROUTES
# FastAPI
# ==========================================================
import os
import json
from fastapi import FastAPI, Response, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import get_db
from app.models.ad import Ad
from app.models.setting import SystemSetting
from app.utils.encryption import decrypt
from app.routes.api.auth import router as auth_router
from app.routes.api.ads import router as ads_router
from app.routes.api.analytics import router as analytics_router
from app.routes.api.communities import router as communities_router
from app.routes.api.marketplaces import router as marketplaces_router
from app.routes.api.users import router as users_router
from app.routes.api.admin import router as admin_router
from app.routes.api.dashboard import router as dashboard_router
from app.routes.api.shops import router as shops_router
from app.routes.api.public import router as public_router
from app.routes.api.categories import router as categories_router
from app.routes.api.vehicles import router as vehicles_router
from app.routes.api.payments import router as payments_router
from app.routes.api.enthusiast import router as enthusiast_router
from prometheus_fastapi_instrumentator import Instrumentator
from openai import OpenAI


# Removido: cliente OpenAI global estático para permitir leitura dinâmica do banco


app = FastAPI(
    title="LinkPeças API",
    version="1.0.0"
)

# Monitoramento do Prometheus
Instrumentator().instrument(app).expose(app)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://linkpecas.online",
        "https://www.linkpecas.online",
        "https://linkpecas-frontend.arandudigital8.workers.dev"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(ads_router, prefix="/api/ads", tags=["Ads"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(communities_router, prefix="/api/communities", tags=["Communities"])
app.include_router(marketplaces_router, prefix="/api/marketplaces", tags=["Marketplaces"])

app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(shops_router, prefix="/api/shops", tags=["Shops"])
app.include_router(public_router, prefix="/api/public", tags=["Public"])
app.include_router(categories_router, prefix="/api/categories", tags=["Categories"])
app.include_router(vehicles_router, prefix="/api", tags=["Vehicles"])
app.include_router(payments_router, prefix="/api/payments", tags=["Payments"])
app.include_router(enthusiast_router, prefix="/api/enthusiast", tags=["Enthusiast"])


@app.get("/")
def health():
    return {"status": "ok"}


# Cria o modelo de dados que a rota vai receber
class MensagemCliente(BaseModel):
    texto: str

# Rota do nosso Balconista Inteligente
@app.post("/chat/balcao")
def chat_balcao(mensagem: MensagemCliente, db: Session = Depends(get_db)):
    setting = db.query(SystemSetting).filter(SystemSetting.key == "openai_api_key").first()
    api_key = decrypt(setting.value) if setting and setting.value else os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return {"error": "API Key não configurada"}
        
    client = OpenAI(api_key=api_key)
    
    prompt_sistema = """
    Você é um balconista de auto peças experiente e direto ao ponto.
    O cliente vai enviar uma mensagem pedindo uma peça.
    Sua missão é extrair 4 informações:
    1. peca (ex: Bomba d'água, Pastilha de freio)
    2. carro (ex: Corsa, Gol)
    3. ano (ex: 2002, 2015)
    4. motor (ex: 1.6, 1.0, 8v)

    Se faltar alguma dessas 4 informações na mensagem, a variável "pergunta" deve conter a pergunta que você faria ao cliente para descobrir o que falta (ex: "Qual o ano e a motorização do seu Corsa?").
    Se você tiver as 4 informações, a variável "pergunta" deve ser null.

    Responda ESTRITAMENTE em formato JSON, com as chaves: peca, carro, ano, motor, pergunta.
    Valores que você não encontrou devem ser null.
    """

    resposta_ia = client.chat.completions.create(
        model="gpt-4o-mini", # Modelo super rápido e barato
        response_format={ "type": "json_object" }, # Força a IA a cuspir um JSON perfeito
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": mensagem.texto}
        ],
        temperature=0.2 # Deixa a IA mais focada e menos criativa
    )

    # Converte o texto JSON que a IA devolveu para um Dicionário Python
    dados_extraidos = json.loads(resposta_ia.choices[0].message.content)
    
    return dados_extraidos

@app.get("/sitemap.xml")
def sitemap(db: Session = Depends(get_db)):
    ads = db.query(Ad).filter(Ad.status == "active").all()
    
    urlset = []
    urlset.append('<url><loc>https://linkpecas.online/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>')
    urlset.append('<url><loc>https://linkpecas.online/ofertas</loc><changefreq>daily</changefreq><priority>0.9</priority></url>')
    urlset.append('<url><loc>https://linkpecas.online/lojas</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>')
    
    for ad in ads:
        # Pega a data de atualização ou criação
        lastmod = ad.updated_at if hasattr(ad, 'updated_at') and ad.updated_at else ad.created_at
        lastmod_str = lastmod.strftime("%Y-%m-%d") if lastmod else "2026-04-30"
        
        # Link do produto baseado no ID ou slug (o frontend usa /product/:id)
        # O ideal seria usar o slug se existir, mas o frontend route é /product/:id
        loc = f"https://linkpecas.online/product/{ad.id}"
        
        urlset.append(f'<url><loc>{loc}</loc><lastmod>{lastmod_str}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>')
        
    sitemap_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{"".join(urlset)}\n</urlset>'
    
    return Response(content=sitemap_xml, media_type="application/xml")
