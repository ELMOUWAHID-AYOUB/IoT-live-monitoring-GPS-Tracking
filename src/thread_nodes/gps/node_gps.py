#!/usr/bin/env python3
"""
Thread End Device - GPS Node
Simule un noeud Thread GPS avec serveur CoAP
IPv6: fd12:3456:789a:1::3 / Port: 5683
"""
import asyncio
import json
import math
import random
import time
import os
from datetime import datetime, timezone

import aiocoap
import aiocoap.resource as resource


# ── Simulation d'un coureur (route cross-country autour de Troyes) ─────────────
BASE_LAT = 48.2973
BASE_LON = 4.0744
ROUTE_RADIUS_KM = 2.5

class GPSSimulator:
    """Simule un GPS qui suit un coureur sur un circuit."""
    def __init__(self):
        self.angle = 0.0
        self.noise = 0.0001
        self.speed_deg_per_step = 0.5  # ~55m par lecture

    def next_position(self):
        self.angle = (self.angle + self.speed_deg_per_step) % 360
        rad = math.radians(self.angle)
        lat = BASE_LAT + (ROUTE_RADIUS_KM / 111.0) * math.cos(rad) + random.gauss(0, self.noise)
        lon = BASE_LON + (ROUTE_RADIUS_KM / (111.0 * math.cos(math.radians(BASE_LAT)))) * math.sin(rad) + random.gauss(0, self.noise)
        alt = 110.0 + 15.0 * math.sin(rad * 3) + random.gauss(0, 0.5)
        return lat, lon, alt


gps_sim = GPSSimulator()


class GPSResource(resource.Resource):
    """Ressource CoAP /gps - retourne position courante."""

    async def render_get(self, request):
        lat, lon, alt = gps_sim.next_position()
        payload = {
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "alt": round(alt, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node_id": os.environ.get("NODE_ID", "3"),
            "node_type": "gps"
        }
        return aiocoap.Message(
            code=aiocoap.CONTENT,
            payload=json.dumps(payload).encode("utf-8")
        )


class HealthResource(resource.Resource):
    """Ressource CoAP /health - statut du noeud."""

    async def render_get(self, request):
        payload = {
            "status": "ok",
            "node_id": os.environ.get("NODE_ID", "3"),
            "role": "end_device",
            "type": "gps",
            "ipv6": os.environ.get("IPV6_ADDR", "fd12:3456:789a:1::3"),
            "uptime": int(time.time())
        }
        return aiocoap.Message(
            code=aiocoap.CONTENT,
            payload=json.dumps(payload).encode("utf-8")
        )


async def main():
    port = int(os.environ.get("COAP_PORT", "5683"))
    print(f"[GPS Node] Démarrage CoAP sur port {port}")
    print(f"[GPS Node] IPv6: {os.environ.get('IPV6_ADDR', 'fd12:3456:789a:1::3')}")

    root = resource.Site()
    root.add_resource(["gps"], GPSResource())
    root.add_resource(["health"], HealthResource())

    await aiocoap.Context.create_server_context(root, bind=("::", port))
    print(f"[GPS Node] ✓ CoAP server ready → coap://[::]:{ port}/gps")
    await asyncio.get_event_loop().create_future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
