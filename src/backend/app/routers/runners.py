"""
API Router - Runners (Couche 4: API REST)
Flux 1: POST /api/runners → Enregistrement coureur + devices
"""
import hashlib
import hmac
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db, Runner, Device, Session as TrackSession
from ..services.validation import generate_api_key

router = APIRouter()
DEVICE_SECRET = os.environ.get("DEVICE_SECRET", "thread_iot_secret_key")


# ── Schémas Pydantic ──────────────────────────────────────────────────────────

class DeviceCreate(BaseModel):
    ipv6_address: str
    device_type: str   # gps | battery | temperature
    coap_port: int

class RunnerCreate(BaseModel):
    name: str
    email: str
    devices: List[DeviceCreate] = []

class RunnerResponse(BaseModel):
    id: int
    name: str
    email: str
    devices: List[dict] = []


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/runners", response_model=dict, status_code=201)
async def create_runner(body: RunnerCreate, db: AsyncSession = Depends(get_db)):
    """Enregistre un coureur avec ses devices IoT."""
    # Vérifier email unique
    existing = await db.execute(select(Runner).where(Runner.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, detail="Email déjà enregistré")

    # Créer runner
    runner = Runner(name=body.name, email=body.email)
    db.add(runner)
    await db.flush()

    # Créer devices
    created_devices = []
    for d in body.devices:
        if d.device_type not in ("gps", "battery", "temperature"):
            raise HTTPException(400, detail=f"Type device invalide: {d.device_type}")
        api_key = generate_api_key(d.ipv6_address)
        device = Device(
            runner_id=runner.id,
            ipv6_address=d.ipv6_address,
            device_type=d.device_type,
            coap_port=d.coap_port,
            api_key=api_key
        )
        db.add(device)
        created_devices.append({"type": d.device_type, "ipv6": d.ipv6_address, "api_key": api_key})

    await db.commit()
    return {"id": runner.id, "name": runner.name, "email": runner.email, "devices": created_devices}


@router.get("/runners", response_model=List[dict])
async def list_runners(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Runner))
    runners = result.scalars().all()
    return [{"id": r.id, "name": r.name, "email": r.email} for r in runners]


@router.get("/runners/{runner_id}")
async def get_runner(runner_id: int, db: AsyncSession = Depends(get_db)):
    runner = await db.get(Runner, runner_id)
    if not runner:
        raise HTTPException(404, detail="Coureur introuvable")

    devices_result = await db.execute(select(Device).where(Device.runner_id == runner_id))
    devices = devices_result.scalars().all()

    return {
        "id": runner.id,
        "name": runner.name,
        "email": runner.email,
        "devices": [{"id": d.id, "type": d.device_type, "ipv6": d.ipv6_address, "port": d.coap_port} for d in devices]
    }
