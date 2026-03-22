"""
Service de validation des données capteurs
Plages définies selon contexte cross-country extérieur
"""
import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Optional, Tuple


DEVICE_SECRET = os.environ.get("DEVICE_SECRET", "thread_iot_secret_key")

# ── Plages de validation strictes ────────────────────────────────────────────
GPS_LAT_RANGE    = (-90.0, 90.0)
GPS_LON_RANGE    = (-180.0, 180.0)
GPS_ALT_RANGE    = (-500.0, 9000.0)   # m
BATTERY_RANGE    = (0.0, 100.0)       # %
VOLTAGE_RANGE    = (2.5, 4.5)         # V (Li-Ion)
TEMP_RANGE       = (-40.0, 60.0)      # °C extérieur
HUMIDITY_RANGE   = (0.0, 100.0)       # %
PRESSURE_RANGE   = (900.0, 1100.0)    # hPa


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]


def validate_gps(lat: float, lon: float, alt: Optional[float] = None) -> ValidationResult:
    errors = []
    if not GPS_LAT_RANGE[0] <= lat <= GPS_LAT_RANGE[1]:
        errors.append(f"Latitude {lat} hors plage {GPS_LAT_RANGE}")
    if not GPS_LON_RANGE[0] <= lon <= GPS_LON_RANGE[1]:
        errors.append(f"Longitude {lon} hors plage {GPS_LON_RANGE}")
    if alt is not None and not GPS_ALT_RANGE[0] <= alt <= GPS_ALT_RANGE[1]:
        errors.append(f"Altitude {alt} hors plage {GPS_ALT_RANGE}")
    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_battery(level: float, voltage: Optional[float] = None) -> ValidationResult:
    errors = []
    if not BATTERY_RANGE[0] <= level <= BATTERY_RANGE[1]:
        errors.append(f"Batterie {level}% hors plage {BATTERY_RANGE}")
    if voltage is not None and not VOLTAGE_RANGE[0] <= voltage <= VOLTAGE_RANGE[1]:
        errors.append(f"Voltage {voltage}V hors plage {VOLTAGE_RANGE}")
    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_temperature(celsius: float, humidity: Optional[float] = None, pressure: Optional[float] = None) -> ValidationResult:
    errors = []
    if not TEMP_RANGE[0] <= celsius <= TEMP_RANGE[1]:
        errors.append(f"Température {celsius}°C hors plage {TEMP_RANGE}")
    if humidity is not None and not HUMIDITY_RANGE[0] <= humidity <= HUMIDITY_RANGE[1]:
        errors.append(f"Humidité {humidity}% hors plage {HUMIDITY_RANGE}")
    if pressure is not None and not PRESSURE_RANGE[0] <= pressure <= PRESSURE_RANGE[1]:
        errors.append(f"Pression {pressure}hPa hors plage {PRESSURE_RANGE}")
    return ValidationResult(valid=len(errors) == 0, errors=errors)


def generate_api_key(device_ipv6: str) -> str:
    """Génère une clé API basée sur l'adresse IPv6 du device."""
    msg = f"{device_ipv6}:{DEVICE_SECRET}".encode()
    return hmac.new(DEVICE_SECRET.encode(), msg, hashlib.sha256).hexdigest()


def verify_api_key(device_ipv6: str, api_key: str) -> bool:
    expected = generate_api_key(device_ipv6)
    return hmac.compare_digest(expected, api_key)
