"""
API Router - Topologie réseau Thread
"""
from fastapi import APIRouter
from ..services.coap_service import coap_get

router = APIRouter()

THREAD_NODES = [
    {"id": "1", "role": "leader",     "ipv6": "fd12:3456:789a:1::1", "type": "coordinator", "port": 5680},
    {"id": "2", "role": "router",     "ipv6": "fd12:3456:789a:1::2", "type": "relay",        "port": 5681},
    {"id": "3", "role": "end_device", "ipv6": "fd12:3456:789a:1::3", "type": "gps",          "port": 5683},
    {"id": "4", "role": "end_device", "ipv6": "fd12:3456:789a:1::4", "type": "battery",      "port": 5684},
    {"id": "5", "role": "end_device", "ipv6": "fd12:3456:789a:1::5", "type": "temperature",  "port": 5685},
]


@router.get("/network/topology")
async def get_topology():
    """Retourne la topologie du réseau Thread simulé."""
    return {
        "network": "ThreadNet-GPS",
        "panid": "0xDEAD",
        "channel": 15,
        "prefix": "fd12:3456:789a:1::/64",
        "nodes": THREAD_NODES
    }


@router.get("/network/nodes/{node_id}/health")
async def node_health(node_id: str):
    """Vérifie l'état d'un noeud Thread via CoAP."""
    node = next((n for n in THREAD_NODES if n["id"] == node_id), None)
    if not node:
        return {"error": "Node introuvable"}

    data = await coap_get(node["ipv6"], node["port"], "health")
    return data or {"status": "unreachable", "node_id": node_id}
