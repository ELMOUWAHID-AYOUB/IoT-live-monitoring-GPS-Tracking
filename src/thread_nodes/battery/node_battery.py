#!/usr/bin/env python3
"""
Thread End Device - Battery Node
CoAP server exposing /battery resource
IPv6: fd12:3456:789a:1::4 / Port: 5684
"""
import asyncio
import json
import random
import time
import os
from datetime import datetime, timezone

import aiocoap
import aiocoap.resource as resource


class BatterySimulator:
    def __init__(self):
        self.level = 95.0 + random.uniform(-5, 5)
        self.voltage = 3.7
        self.drain_rate = 0.02  # % par lecture

    def read(self):
        self.level = max(0.0, self.level - self.drain_rate + random.gauss(0, 0.01))
        self.voltage = 3.0 + (self.level / 100.0) * 1.2
        return self.level, self.voltage


battery_sim = BatterySimulator()


class BatteryResource(resource.Resource):
    async def render_get(self, request):
        level, voltage = battery_sim.read()
        payload = {
            "level_percent": round(level, 2),
            "voltage": round(voltage, 3),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node_id": os.environ.get("NODE_ID", "4"),
            "node_type": "battery"
        }
        return aiocoap.Message(
            code=aiocoap.CONTENT,
            payload=json.dumps(payload).encode("utf-8")
        )


class HealthResource(resource.Resource):
    async def render_get(self, request):
        payload = {
            "status": "ok",
            "node_id": os.environ.get("NODE_ID", "4"),
            "role": "end_device",
            "type": "battery",
            "ipv6": os.environ.get("IPV6_ADDR", "fd12:3456:789a:1::4"),
            "uptime": int(time.time())
        }
        return aiocoap.Message(
            code=aiocoap.CONTENT,
            payload=json.dumps(payload).encode("utf-8")
        )


async def main():
    port = int(os.environ.get("COAP_PORT", "5684"))
    print(f"[Battery Node] Démarrage CoAP sur port {port}")
    root = resource.Site()
    root.add_resource(["battery"], BatteryResource())
    root.add_resource(["health"], HealthResource())
    await aiocoap.Context.create_server_context(root, bind=("::", port))
    print(f"[Battery Node] ✓ CoAP server ready → coap://[::]:{ port}/battery")
    await asyncio.get_event_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())
