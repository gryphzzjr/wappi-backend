from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    auth,
    bots,
    conversations,
    files,
    integrations,
    mercado_pago,
    subscriptions,
    training,
    webhooks,
    whatsapp,
)


app = FastAPI(
    title="Wappi API",
    description="API do Wappi",
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

allowed_origins = [
    "http://localhost:5173",
    "http://localhost:8100",
]

if settings.APP_URL not in allowed_origins:
    allowed_origins.append(settings.APP_URL)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():
    return {
        "name": "Wappi API",
        "status": "online",
        "environment": settings.ENVIRONMENT,
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health():
    return {
        "status": "ok",
    }


# =========================================================
# ROUTERS
# =========================================================

app.include_router(auth.router)
app.include_router(bots.router)
app.include_router(conversations.router)
app.include_router(files.router)
app.include_router(integrations.router)
app.include_router(mercado_pago.router)
app.include_router(subscriptions.router)
app.include_router(training.router)
app.include_router(webhooks.router)
app.include_router(whatsapp.router)
