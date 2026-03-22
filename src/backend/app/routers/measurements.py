"""
API Router - Mesures GPS/Batterie/Température
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db, GPSMeasurement, BatteryMeasurement, TemperatureMeasurement

router = APIRouter()


@router.get("/sessions/{session_id}/gps")
async def get_gps_history(session_id: int, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GPSMeasurement)
        .where(GPSMeasurement.session_id == session_id)
        .order_by(desc(GPSMeasurement.timestamp))
        .limit(limit)
    )
    measurements = result.scalars().all()
    return [
        {"lat": m.latitude, "lon": m.longitude, "alt": m.altitude,
         "timestamp": m.timestamp.isoformat()}
        for m in reversed(measurements)
    ]


@router.get("/sessions/{session_id}/battery")
async def get_battery_history(session_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BatteryMeasurement)
        .where(BatteryMeasurement.session_id == session_id)
        .order_by(desc(BatteryMeasurement.timestamp))
        .limit(limit)
    )
    measurements = result.scalars().all()
    return [
        {"level": m.level_percent, "voltage": m.voltage,
         "timestamp": m.timestamp.isoformat()}
        for m in reversed(measurements)
    ]


@router.get("/sessions/{session_id}/temperature")
async def get_temperature_history(session_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TemperatureMeasurement)
        .where(TemperatureMeasurement.session_id == session_id)
        .order_by(desc(TemperatureMeasurement.timestamp))
        .limit(limit)
    )
    measurements = result.scalars().all()
    return [
        {"celsius": m.celsius, "humidity": m.humidity, "pressure": m.pressure,
         "timestamp": m.timestamp.isoformat()}
        for m in reversed(measurements)
    ]


@router.get("/sessions/{session_id}/latest")
async def get_latest(session_id: int, db: AsyncSession = Depends(get_db)):
    """Retourne la dernière mesure de chaque type pour une session."""
    async def last(model, session_id):
        r = await db.execute(
            select(model).where(model.session_id == session_id)
            .order_by(desc(model.timestamp)).limit(1)
        )
        return r.scalar_one_or_none()

    gps  = await last(GPSMeasurement, session_id)
    batt = await last(BatteryMeasurement, session_id)
    temp = await last(TemperatureMeasurement, session_id)

    return {
        "gps": {"lat": gps.latitude, "lon": gps.longitude, "alt": gps.altitude,
                "timestamp": gps.timestamp.isoformat()} if gps else None,
        "battery": {"level": batt.level_percent, "voltage": batt.voltage,
                    "timestamp": batt.timestamp.isoformat()} if batt else None,
        "temperature": {"celsius": temp.celsius, "humidity": temp.humidity, "pressure": temp.pressure,
                        "timestamp": temp.timestamp.isoformat()} if temp else None,
    }
