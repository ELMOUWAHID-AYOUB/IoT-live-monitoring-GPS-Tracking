"""
Service de Polling - Interroge les noeuds CoAP périodiquement
pour chaque session active, puis publie via MQTT et stocke en BDD
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update

from ..database import AsyncSessionLocal, Session, Device, GPSMeasurement, BatteryMeasurement, TemperatureMeasurement
from .coap_service import poll_gps_node, poll_battery_node, poll_temperature_node
from .validation import validate_gps, validate_battery, validate_temperature
from .haversine import haversine
from .mqtt_service import mqtt_client

logger = logging.getLogger(__name__)
POLL_INTERVAL = 5  # secondes


async def poll_once():
    """Interroge tous les devices des sessions actives."""
    async with AsyncSessionLocal() as db:
        # Sessions actives
        result = await db.execute(
            select(Session).where(Session.is_active == True)
        )
        active_sessions = result.scalars().all()

        for session in active_sessions:
            # Devices de ce runner
            devices_result = await db.execute(
                select(Device).where(Device.runner_id == session.runner_id)
            )
            devices = devices_result.scalars().all()

            for device in devices:
                await poll_device(db, session, device)

        await db.commit()


async def poll_device(db, session, device):
    """Interroge un device CoAP et stocke/publie si valide."""
    host = device.ipv6_address
    port = device.coap_port
    now = datetime.now(timezone.utc)

    if device.device_type == "gps":
        data = await poll_gps_node(host, port)
        if data:
            vr = validate_gps(data["lat"], data["lon"], data.get("alt"))
            if vr.valid:
                meas = GPSMeasurement(
                    session_id=session.id,
                    device_id=device.id,
                    latitude=data["lat"],
                    longitude=data["lon"],
                    altitude=data.get("alt"),
                    timestamp=now
                )
                db.add(meas)
                # Mise à jour distance
                await update_distance(db, session, data["lat"], data["lon"])
                mqtt_client.publish_gps(session.id, data)
                # Alerte batterie critique déjà traitée dans battery
            else:
                logger.warning(f"GPS invalide session {session.id}: {vr.errors}")

    elif device.device_type == "battery":
        data = await poll_battery_node(host, port)
        if data:
            vr = validate_battery(data["level_percent"], data.get("voltage"))
            if vr.valid:
                meas = BatteryMeasurement(
                    session_id=session.id,
                    device_id=device.id,
                    level_percent=data["level_percent"],
                    voltage=data.get("voltage"),
                    timestamp=now
                )
                db.add(meas)
                mqtt_client.publish_battery(session.id, data)
                # Alerte batterie faible
                if data["level_percent"] < 15:
                    mqtt_client.publish_alert(session.id, "LOW_BATTERY",
                        f"Batterie critique: {data['level_percent']:.1f}%")

    elif device.device_type == "temperature":
        data = await poll_temperature_node(host, port)
        if data:
            vr = validate_temperature(data["celsius"], data.get("humidity"), data.get("pressure"))
            if vr.valid:
                meas = TemperatureMeasurement(
                    session_id=session.id,
                    device_id=device.id,
                    celsius=data["celsius"],
                    humidity=data.get("humidity"),
                    pressure=data.get("pressure"),
                    timestamp=now
                )
                db.add(meas)
                mqtt_client.publish_temperature(session.id, data)


async def update_distance(db, session, lat: float, lon: float):
    """Met à jour la distance totale de la session."""
    # Dernière mesure GPS
    from sqlalchemy import select, desc
    result = await db.execute(
        select(GPSMeasurement)
        .where(GPSMeasurement.session_id == session.id)
        .order_by(desc(GPSMeasurement.id))
        .limit(1)
    )
    last = result.scalar_one_or_none()
    if last:
        dist = haversine(last.latitude, last.longitude, lat, lon)
        # Filtre anti-bruit: ignore < 1m ou > 100m/step
        if 1.0 < dist < 100.0:
            session.total_distance_m = (session.total_distance_m or 0.0) + dist


async def start_polling():
    """Boucle de polling principale."""
    logger.info(f"Polling démarré (intervalle: {POLL_INTERVAL}s)")
    while True:
        try:
            await poll_once()
        except Exception as e:
            logger.error(f"Erreur polling: {e}")
        await asyncio.sleep(POLL_INTERVAL)
