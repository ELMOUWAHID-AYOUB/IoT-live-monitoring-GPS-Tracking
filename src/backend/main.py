"""
GPS Thread Tracking - Backend API
Architecture IoT 5 couches - FastAPI + PostgreSQL + MQTT
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
import psycopg2
import psycopg2.extras
import paho.mqtt.client as mqtt
import os
import math
import random
import json
import threading
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ─── CONFIG ──────────────────────────────────────────────
DB_URL = os.getenv("DATABASE_URL", "postgresql://tracker:tracker123@postgres:5432/gps_tracking")
MQTT_HOST = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

# Adresses IPv6 ULA du réseau Thread simulé
THREAD_NODES = {
    "leader":      "fd00:db8::1",
    "router":      "fd00:db8::2",
    "gps":         "fd00:db8::10",
    "battery":     "fd00:db8::11",
    "temperature": "fd00:db8::12",
}

# ─── DATABASE ────────────────────────────────────────────
def get_db():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)

def init_db():
    for attempt in range(10):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS runners (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(150) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    runner_id INTEGER REFERENCES runners(id),
                    session_uuid VARCHAR(36) DEFAULT gen_random_uuid()::text,
                    started_at TIMESTAMP DEFAULT NOW(),
                    ended_at TIMESTAMP,
                    total_distance FLOAT DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE
                );

                CREATE TABLE IF NOT EXISTS gps_measurements (
                    id SERIAL PRIMARY KEY,
                    session_id INTEGER REFERENCES sessions(id),
                    latitude FLOAT NOT NULL,
                    longitude FLOAT NOT NULL,
                    altitude FLOAT,
                    distance_from_prev FLOAT DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS sensor_measurements (
                    id SERIAL PRIMARY KEY,
                    session_id INTEGER REFERENCES sessions(id),
                    type VARCHAR(20) NOT NULL,
                    value FLOAT NOT NULL,
                    unit VARCHAR(10),
                    timestamp TIMESTAMP DEFAULT NOW()
                );
            """)
            conn.commit()
            cur.close()
            conn.close()
            log.info("✅ Base de données initialisée")
            return
        except Exception as e:
            log.warning(f"DB pas prête ({attempt+1}/10): {e}")
            time.sleep(3)
    log.error("❌ Impossible de connecter à la base de données")

# ─── MQTT ────────────────────────────────────────────────
mqtt_client = mqtt.Client(client_id="gps_backend")
mqtt_connected = False

def on_mqtt_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        log.info(f"✅ MQTT connecté à {MQTT_HOST}:{MQTT_PORT}")
    else:
        log.warning(f"MQTT échec connexion rc={rc}")

mqtt_client.on_connect = on_mqtt_connect

def mqtt_connect():
    for attempt in range(10):
        try:
            mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            mqtt_client.loop_start()
            return
        except Exception as e:
            log.warning(f"MQTT pas prêt ({attempt+1}/10): {e}")
            time.sleep(3)

def publish(topic: str, data: dict):
    if mqtt_connected:
        mqtt_client.publish(topic, json.dumps(data, default=str), qos=1)
        log.info(f"MQTT → {topic}")

# ─── HAVERSINE ───────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2) -> float:
    """Distance en mètres entre deux points GPS (formule de Haversine)"""
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ─── SIMULATION CoAP / THREAD ────────────────────────────
# Parcours cross-country simulé autour de Troyes
WAYPOINTS = [
    (48.2973, 4.0744), (48.2985, 4.0780), (48.3000, 4.0820),
    (48.3010, 4.0860), (48.2998, 4.0900), (48.2975, 4.0920),
    (48.2960, 4.0890), (48.2945, 4.0850), (48.2950, 4.0800),
]
_wp_idx = 0
_wp_prog = 0.0
_battery = 92.0

def simulate_coap_gps() -> dict:
    """Simule GET coap://[fd00:db8::10]:5683/gps"""
    global _wp_idx, _wp_prog
    wp1 = WAYPOINTS[_wp_idx]
    wp2 = WAYPOINTS[(_wp_idx + 1) % len(WAYPOINTS)]
    lat = wp1[0] + (wp2[0] - wp1[0]) * _wp_prog + random.gauss(0, 0.00001)
    lon = wp1[1] + (wp2[1] - wp1[1]) * _wp_prog + random.gauss(0, 0.00001)
    _wp_prog += 0.15
    if _wp_prog >= 1.0:
        _wp_prog = 0.0
        _wp_idx = (_wp_idx + 1) % len(WAYPOINTS)
    return {
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "altitude": round(100 + random.uniform(-5, 5), 1),
        "device_ipv6": THREAD_NODES["gps"],
        "protocol": "CoAP/RFC7252",
        "timestamp": datetime.utcnow().isoformat(),
    }

def simulate_coap_battery() -> dict:
    """Simule GET coap://[fd00:db8::11]:5683/battery"""
    global _battery
    _battery = max(0, _battery - random.uniform(0.05, 0.2))
    return {
        "value": round(_battery, 1),
        "unit": "%",
        "device_ipv6": THREAD_NODES["battery"],
        "protocol": "CoAP/RFC7252",
        "timestamp": datetime.utcnow().isoformat(),
    }

def simulate_coap_temperature() -> dict:
    """Simule GET coap://[fd00:db8::12]:5683/temperature"""
    hour = datetime.utcnow().hour
    temp = 12.0 + 5 * math.sin((hour - 6) * math.pi / 12) + random.gauss(0, 0.5)
    return {
        "value": round(temp, 1),
        "unit": "°C",
        "device_ipv6": THREAD_NODES["temperature"],
        "protocol": "CoAP/RFC7252",
        "timestamp": datetime.utcnow().isoformat(),
    }

# ─── SCHEMAS ─────────────────────────────────────────────
class RunnerIn(BaseModel):
    name: str
    email: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Nom requis")
        return v.strip()

class SessionIn(BaseModel):
    runner_id: int

class GpsIn(BaseModel):
    session_id: int
    lat: float
    lon: float
    altitude: Optional[float] = None

    @field_validator("lat")
    @classmethod
    def check_lat(cls, v):
        if not -90 <= v <= 90:
            raise ValueError(f"Latitude invalide: {v} (doit être dans [-90, 90])")
        return v

    @field_validator("lon")
    @classmethod
    def check_lon(cls, v):
        if not -180 <= v <= 180:
            raise ValueError(f"Longitude invalide: {v} (doit être dans [-180, 180])")
        return v

class BatteryIn(BaseModel):
    session_id: int
    value: float

    @field_validator("value")
    @classmethod
    def check_battery(cls, v):
        if not 0 <= v <= 100:
            raise ValueError(f"Batterie invalide: {v} (doit être dans [0, 100])")
        return v

class TempIn(BaseModel):
    session_id: int
    value: float

    @field_validator("value")
    @classmethod
    def check_temp(cls, v):
        if not -40 <= v <= 60:
            raise ValueError(f"Température invalide: {v} (doit être dans [-40, 60])")
        return v

# ─── APP ─────────────────────────────────────────────────
app = FastAPI(
    title="GPS Thread Tracking API",
    description="Architecture IoT 5 couches - Thread / CoAP / MQTT / FastAPI / PostgreSQL",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()
    threading.Thread(target=mqtt_connect, daemon=True).start()

# ─── HEALTH ──────────────────────────────────────────────
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "mqtt_connected": mqtt_connected}

# ─── THREAD NETWORK ──────────────────────────────────────
@app.get("/api/network", tags=["thread"])
def get_thread_network():
    """Documentation de la topologie réseau Thread IPv6"""
    return {
        "prefix_ula": "fd00:db8::/64",
        "nodes": [
            {"role": "Leader",      "ipv6": THREAD_NODES["leader"],      "type": "coordinator"},
            {"role": "Router",      "ipv6": THREAD_NODES["router"],      "type": "relay"},
            {"role": "End Device",  "ipv6": THREAD_NODES["gps"],         "type": "gps",
             "coap": f"coap://[{THREAD_NODES['gps']}]:5683/gps"},
            {"role": "End Device",  "ipv6": THREAD_NODES["battery"],     "type": "battery",
             "coap": f"coap://[{THREAD_NODES['battery']}]:5683/battery"},
            {"role": "End Device",  "ipv6": THREAD_NODES["temperature"], "type": "temperature",
             "coap": f"coap://[{THREAD_NODES['temperature']}]:5683/temperature"},
        ]
    }

# ─── RUNNERS ─────────────────────────────────────────────
@app.get("/api/runners", tags=["runners"])
def list_runners():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM runners ORDER BY created_at DESC")
    rows = cur.fetchall(); cur.close(); conn.close()
    return [dict(r) for r in rows]

@app.post("/api/runners", status_code=201, tags=["runners"])
def create_runner(body: RunnerIn):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute(
            "INSERT INTO runners (name, email) VALUES (%s, %s) RETURNING *",
            (body.name, body.email)
        )
        row = dict(cur.fetchone()); conn.commit(); cur.close(); conn.close()
        return row
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Email déjà utilisé")
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/runners/{runner_id}", tags=["runners"])
def get_runner(runner_id: int):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM runners WHERE id = %s", (runner_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    if not row: raise HTTPException(404, "Coureur introuvable")
    return dict(row)

# ─── SESSIONS ────────────────────────────────────────────
@app.post("/api/sessions", status_code=201, tags=["sessions"])
def create_session(body: SessionIn):
    conn = get_db(); cur = conn.cursor()
    # Vérif runner
    cur.execute("SELECT id FROM runners WHERE id = %s", (body.runner_id,))
    if not cur.fetchone():
        cur.close(); conn.close()
        raise HTTPException(404, "Coureur introuvable")
    # Désactiver sessions actives
    cur.execute(
        "UPDATE sessions SET is_active=FALSE, ended_at=NOW() WHERE runner_id=%s AND is_active=TRUE",
        (body.runner_id,)
    )
    cur.execute(
        "INSERT INTO sessions (runner_id) VALUES (%s) RETURNING *",
        (body.runner_id,)
    )
    row = dict(cur.fetchone()); conn.commit(); cur.close(); conn.close()
    return row

@app.get("/api/sessions", tags=["sessions"])
def list_sessions():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM sessions ORDER BY started_at DESC LIMIT 20")
    rows = cur.fetchall(); cur.close(); conn.close()
    return [dict(r) for r in rows]

@app.get("/api/sessions/{session_id}", tags=["sessions"])
def get_session(session_id: int):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    if not row: raise HTTPException(404, "Session introuvable")
    return dict(row)

@app.patch("/api/sessions/{session_id}/stop", tags=["sessions"])
def stop_session(session_id: int):
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET is_active=FALSE, ended_at=NOW() WHERE id=%s",
        (session_id,)
    )
    conn.commit(); cur.close(); conn.close()
    return {"message": "Session arrêtée"}

# ─── MESURES GPS ─────────────────────────────────────────
@app.post("/api/measurements/gps", tags=["measurements"])
def post_gps(body: GpsIn):
    conn = get_db(); cur = conn.cursor()

    # Dernier point pour calculer distance (Haversine)
    cur.execute(
        "SELECT latitude, longitude FROM gps_measurements WHERE session_id=%s ORDER BY timestamp DESC LIMIT 1",
        (body.session_id,)
    )
    last = cur.fetchone()
    dist = 0.0
    if last:
        dist = haversine(last["latitude"], last["longitude"], body.lat, body.lon)

    # Insertion mesure
    cur.execute(
        "INSERT INTO gps_measurements (session_id, latitude, longitude, altitude, distance_from_prev) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (body.session_id, body.lat, body.lon, body.altitude, dist)
    )
    mid = cur.fetchone()["id"]

    # Mise à jour distance totale session
    cur.execute(
        "UPDATE sessions SET total_distance = total_distance + %s WHERE id = %s",
        (dist, body.session_id)
    )
    conn.commit(); cur.close(); conn.close()

    # Publication MQTT (Flux 3)
    publish(f"/tracking/{body.session_id}/gps", {
        "lat": body.lat, "lon": body.lon,
        "altitude": body.altitude,
        "distance_from_prev": round(dist, 2),
    })

    return {"id": mid, "distance_from_prev": round(dist, 2)}

@app.get("/api/measurements/gps/{session_id}", tags=["measurements"])
def get_gps_history(session_id: int):
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        "SELECT * FROM gps_measurements WHERE session_id=%s ORDER BY timestamp ASC",
        (session_id,)
    )
    rows = cur.fetchall(); cur.close(); conn.close()
    return [dict(r) for r in rows]

# ─── MESURES CAPTEURS ────────────────────────────────────
@app.post("/api/measurements/battery", tags=["measurements"])
def post_battery(body: BatteryIn):
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        "INSERT INTO sensor_measurements (session_id, type, value, unit) VALUES (%s,'battery',%s,'%%') RETURNING id",
        (body.session_id, body.value)
    )
    mid = cur.fetchone()["id"]; conn.commit(); cur.close(); conn.close()
    publish(f"/tracking/{body.session_id}/battery", {"value": body.value, "unit": "%"})
    return {"id": mid}

@app.post("/api/measurements/temperature", tags=["measurements"])
def post_temperature(body: TempIn):
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        "INSERT INTO sensor_measurements (session_id, type, value, unit) VALUES (%s,'temperature',%s,'°C') RETURNING id",
        (body.session_id, body.value)
    )
    mid = cur.fetchone()["id"]; conn.commit(); cur.close(); conn.close()
    publish(f"/tracking/{body.session_id}/temperature", {"value": body.value, "unit": "°C"})
    return {"id": mid}

@app.get("/api/measurements/sensors/{session_id}", tags=["measurements"])
def get_sensor_history(session_id: int, type: Optional[str] = None):
    conn = get_db(); cur = conn.cursor()
    if type:
        cur.execute(
            "SELECT * FROM sensor_measurements WHERE session_id=%s AND type=%s ORDER BY timestamp ASC",
            (session_id, type)
        )
    else:
        cur.execute(
            "SELECT * FROM sensor_measurements WHERE session_id=%s ORDER BY timestamp ASC",
            (session_id,)
        )
    rows = cur.fetchall(); cur.close(); conn.close()
    return [dict(r) for r in rows]

# ─── COAP POLL ───────────────────────────────────────────
@app.post("/api/coap/poll/{session_id}", tags=["coap"])
def coap_poll(session_id: int):
    """
    Flux 2: Interroge les noeuds Thread via CoAP (simulé POSIX)
    GET coap://[fd00:db8::10]:5683/gps
    GET coap://[fd00:db8::11]:5683/battery
    GET coap://[fd00:db8::12]:5683/temperature
    """
    results = {}

    # GPS
    gps = simulate_coap_gps()
    results["gps"] = gps
    post_gps(GpsIn(session_id=session_id, lat=gps["lat"], lon=gps["lon"], altitude=gps["altitude"]))

    # Batterie
    batt = simulate_coap_battery()
    results["battery"] = batt
    post_battery(BatteryIn(session_id=session_id, value=batt["value"]))

    # Température
    temp = simulate_coap_temperature()
    results["temperature"] = temp
    post_temperature(TempIn(session_id=session_id, value=temp["value"]))

    return {"session_id": session_id, "coap_responses": results}
