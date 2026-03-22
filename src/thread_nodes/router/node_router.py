#!/usr/bin/env python3
"""
Thread Router Node - Relay between end devices and leader
IPv6: fd12:3456:789a:1::2
"""
import asyncio
import json
import time
import os
from datetime import datetime, timezone

import aiocoap
import aiocoap.resource as resource


class RouterResource(resource.Resource):
    async def render_get(self, request):
        payload = {
            "role": "router",
            "status": "active",
            "routes": ["fd12:3456:789a:1::3", "fd12:3456:789a:1::4", "fd12:3456:789a:1::5"],
            "uptime": int(time.time()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return aiocoap.Message(code=aiocoap.CONTENT, payload=json.dumps(payload).encode())


async def main():
    print("[Router] Démarrage noeud Thread Router")
    root = resource.Site()
    root.add_resource(["router"], RouterResource())
    root.add_resource(["health"], RouterResource())
    await aiocoap.Context.create_server_context(root, bind=("::", 5681))
    print("[Router] ✓ Router active on port 5681")
    await asyncio.get_event_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())
