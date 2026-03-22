"""
Service CoAP - Interroge les noeuds Thread (End Devices)
Utilise aiocoap pour requêtes CoAP asynchrones
"""
import asyncio
import json
import logging
import os
from typing import Optional

import aiocoap

logger = logging.getLogger(__name__)
COAP_TIMEOUT = float(os.environ.get("COAP_TIMEOUT", "5"))


async def coap_get(host: str, port: int, path: str) -> Optional[dict]:
    """
    Effectue une requête CoAP GET vers un noeud Thread.

    Args:
        host: adresse IPv6 ou hostname du noeud
        port: port CoAP (default 5683)
        path: ressource (ex: 'gps', 'battery', 'temperature')

    Returns:
        dict du payload JSON ou None si erreur/timeout
    """
    uri = f"coap://[{host}]:{port}/{path}" if ":" in host else f"coap://{host}:{port}/{path}"

    try:
        async with asyncio.timeout(COAP_TIMEOUT):
            ctx = await aiocoap.Context.create_client_context()
            request = aiocoap.Message(code=aiocoap.GET, uri=uri)
            response = await ctx.request(request).response
            await ctx.shutdown()

            if response.code.is_successful():
                return json.loads(response.payload.decode("utf-8"))
            else:
                logger.warning(f"CoAP {uri} → {response.code}")
                return None

    except asyncio.TimeoutError:
        logger.error(f"CoAP timeout: {uri}")
        return None
    except Exception as e:
        logger.error(f"CoAP error {uri}: {e}")
        return None


async def poll_gps_node(host: str, port: int = 5683) -> Optional[dict]:
    return await coap_get(host, port, "gps")


async def poll_battery_node(host: str, port: int = 5684) -> Optional[dict]:
    return await coap_get(host, port, "battery")


async def poll_temperature_node(host: str, port: int = 5685) -> Optional[dict]:
    return await coap_get(host, port, "temperature")
