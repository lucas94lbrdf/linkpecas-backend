# ==========================================================
# app/main.py
# AUTO MARKETPLACE API ROUTES
# FastAPI
# ==========================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI(
    title="Auto Marketplace API",
    version="1.0.0"
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
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
