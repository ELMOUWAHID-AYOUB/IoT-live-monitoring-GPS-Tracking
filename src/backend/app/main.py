"""
Backend FastAPI - GPS Tracking Platform
Couche 3 & 4: Service CoAP + Auth + MQTT + API REST
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from .database import engine, Base, get_db
from .routers import runners, sessions, measurements, network
from .services.mqtt_service import mqtt_client
from .services.polling_service import start_polling

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initialisation de la base de données...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Connexion MQTT...")
    await mqtt_client.connect()

    logger.info("Démarrage polling CoAP...")
    polling_task = asyncio.create_task(start_polling())

    yield

    # Shutdown
    polling_task.cancel()
    await mqtt_client.disconnect()


app = FastAPI(
    title="GPS Tracking API",
    description="Plateforme IoT Thread - Tracking GPS en temps réel",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(runners.router, prefix="/api", tags=["runners"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(measurements.router, prefix="/api", tags=["measurements"])
app.include_router(network.router, prefix="/api", tags=["network"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gps-tracking-backend"}
