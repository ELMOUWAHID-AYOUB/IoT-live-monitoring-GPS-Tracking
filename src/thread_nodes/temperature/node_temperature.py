#!/usr/bin/env python3
"""
Thread End Device - Temperature Node
CoAP server exposing /temperature resource
IPv6: fd12:3456:789a:1::5 / Port: 5685
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


class TempSimulator:
    """Simule capteur température/humidité/pression extérieur."""
    def __init__(self):
        self.base_temp = 12.0  # printemps cross-country
        self.t = 0

    def read(self):
        self.t += 1
        temp = self.base_temp + 2.0 * math.sin(self.t * 0.1) + random.gauss(0, 0.3)
        humidity = 65.0 + 10.0 * math.cos(self.t * 0.05) + random.gauss(0, 1)
        pressure = 1013.25 + 5.0 * math.sin(self.t * 0.02) + random.gauss(0, 0.5)
        return (
            round(max(-40, min(60, temp)), 2),
            round(max(0, min(100, humidity)), 2),
            round(max(900, min(1100, pressure)), 2)
        )


temp_sim = TempSimulator()


class TemperatureResource(resource.Resource):
    async def render_get(self, request):
        celsius, humidity, pressure = temp_sim.read()
        payload = {
            "celsius": celsius,
            "humidity": humidity,
            "pressure": pressure,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node_id": os.environ.get("NODE_ID", "5"),
            "node_type": "temperature"
        }
        return aiocoap.Message(
            code=aiocoap.CONTENT,
            payload=json.dumps(payload).encode("utf-8")
        )


class HealthResource(resource.Resource):
    async def render_get(self, request):
        payload = {
            "status": "ok",
            "node_id": os.environ.get("NODE_ID", "5"),
            "role": "end_device",
            "type": "temperature",
            "ipv6": os.environ.get("IPV6_ADDR", "fd12:3456:789a:1::5"),
            "uptime": int(time.time())
        }
        return aiocoap.Message(
            code=aiocoap.CONTENT,
            payload=json.dumps(payload).encode("utf-8")
        )


async def main():
    port = int(os.environ.get("COAP_PORT", "5685"))
    print(f"[Temp Node] Démarrage CoAP sur port {port}")
    root = resource.Site()
    root.add_resource(["temperature"], TemperatureResource())
    root.add_resource(["health"], HealthResource())
    await aiocoap.Context.create_server_context(root, bind=("::", port))
    print(f"[Temp Node] ✓ CoAP server ready → coap://[::]:{ port}/temperature")
    await asyncio.get_event_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())
