#!/usr/bin/env python3
"""
Thread Leader Node - Elected dynamically in Thread network
Provides network topology and routing information via CoAP
IPv6: fd12:3456:789a:1::1
"""
import asyncio
import json
import time
import os
from datetime import datetime, timezone

import aiocoap
import aiocoap.resource as resource

THREAD_NODES = [
    {"id": "1", "role": "leader",     "ipv6": "fd12:3456:789a:1::1", "type": "coordinator"},
    {"id": "2", "role": "router",     "ipv6": "fd12:3456:789a:1::2", "type": "relay"},
    {"id": "3", "role": "end_device", "ipv6": "fd12:3456:789a:1::3", "type": "gps",         "coap_port": 5683},
    {"id": "4", "role": "end_device", "ipv6": "fd12:3456:789a:1::4", "type": "battery",     "coap_port": 5684},
    {"id": "5", "role": "end_device", "ipv6": "fd12:3456:789a:1::5", "type": "temperature", "coap_port": 5685},
]


class TopologyResource(resource.Resource):
    async def render_get(self, request):
        payload = {
            "network": "ThreadNet-GPS",
            "panid": "0xDEAD",
            "channel": 15,
            "prefix": "fd12:3456:789a:1::/64",
            "leader": THREAD_NODES[0],
            "nodes": THREAD_NODES,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return aiocoap.Message(code=aiocoap.CONTENT, payload=json.dumps(payload).encode())


class HealthResource(resource.Resource):
    async def render_get(self, request):
        payload = {"status": "ok", "role": "leader", "uptime": int(time.time())}
        return aiocoap.Message(code=aiocoap.CONTENT, payload=json.dumps(payload).encode())


async def main():
    print("[Leader] Démarrage noeud Thread Leader")
    root = resource.Site()
    root.add_resource(["topology"], TopologyResource())
    root.add_resource(["health"], HealthResource())
    await aiocoap.Context.create_server_context(root, bind=("::", 5680))
    print("[Leader] ✓ Network leader active on port 5680")
    await asyncio.get_event_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())
