"""
Service MQTT - Publication des données validées vers Mosquitto
Topics: /tracking/{session_id}/gps|battery|temperature
"""
import asyncio
import json
import logging
import os
from datetime import datetime

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT   = int(os.environ.get("MQTT_PORT", "1883"))


class MQTTService:
    def __init__(self):
        self.client = mqtt.Client(client_id="gps-tracking-backend", protocol=mqtt.MQTTv5)
        self.connected = False
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info(f"MQTT connecté → {MQTT_BROKER}:{MQTT_PORT}")
            self.connected = True
        else:
            logger.error(f"MQTT connexion échouée: {rc}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        self.connected = False
        logger.warning("MQTT déconnecté")

    async def connect(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._blocking_connect)

    def _blocking_connect(self):
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"MQTT connect error: {e}")

    async def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish(self, topic: str, payload: dict, qos: int = 1):
        if not self.connected:
            logger.warning(f"MQTT non connecté, abandon publish sur {topic}")
            return False
        msg = json.dumps({**payload, "published_at": datetime.utcnow().isoformat()})
        result = self.client.publish(topic, msg, qos=qos, retain=False)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.debug(f"MQTT → {topic}")
            return True
        logger.error(f"MQTT publish failed: {result.rc}")
        return False

    def publish_gps(self, session_id: int, data: dict):
        return self.publish(f"/tracking/{session_id}/gps", data)

    def publish_battery(self, session_id: int, data: dict):
        return self.publish(f"/tracking/{session_id}/battery", data)

    def publish_temperature(self, session_id: int, data: dict):
        return self.publish(f"/tracking/{session_id}/temperature", data)

    def publish_alert(self, session_id: int, alert_type: str, message: str):
        return self.publish(f"/tracking/{session_id}/alerts", {
            "type": alert_type,
            "message": message
        })


mqtt_client = MQTTService()
