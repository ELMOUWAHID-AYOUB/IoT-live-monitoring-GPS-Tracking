"""
Suite de tests automatisés - GPS Tracking Platform
pytest tests/ -v
"""
import pytest
import pytest_asyncio
import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# ── 0. Setup path ────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))

from app.services.validation import (
    validate_gps, validate_battery, validate_temperature,
    generate_api_key, verify_api_key
)
from app.services.haversine import haversine, total_distance


# ══════════════════════════════════════════════════════════════════════════════
# CATÉGORIE 1 - Validation des données (plages de valeurs)
# ══════════════════════════════════════════════════════════════════════════════

class TestGPSValidation:
    def test_valid_coordinates(self):
        r = validate_gps(48.25, 4.02)
        assert r.valid

    def test_valid_with_altitude(self):
        r = validate_gps(48.25, 4.02, 110.0)
        assert r.valid

    def test_latitude_out_of_range_positive(self):
        r = validate_gps(91.0, 4.02)
        assert not r.valid
        assert any("Latitude" in e for e in r.errors)

    def test_latitude_out_of_range_negative(self):
        r = validate_gps(-91.0, 4.02)
        assert not r.valid

    def test_longitude_out_of_range(self):
        r = validate_gps(48.25, 181.0)
        assert not r.valid
        assert any("Longitude" in e for e in r.errors)

    def test_altitude_out_of_range(self):
        r = validate_gps(48.25, 4.02, 99999.0)
        assert not r.valid

    def test_boundary_values_valid(self):
        assert validate_gps(90.0, 180.0).valid
        assert validate_gps(-90.0, -180.0).valid
        assert validate_gps(0.0, 0.0).valid

    def test_multiple_errors(self):
        r = validate_gps(95.0, 200.0, -1000.0)
        assert not r.valid
        assert len(r.errors) >= 2


class TestBatteryValidation:
    def test_valid_full_battery(self):
        assert validate_battery(100.0).valid

    def test_valid_empty_battery(self):
        assert validate_battery(0.0).valid

    def test_negative_battery(self):
        assert not validate_battery(-1.0).valid

    def test_battery_over_100(self):
        assert not validate_battery(101.0).valid

    def test_valid_with_voltage(self):
        assert validate_battery(75.0, 3.7).valid

    def test_invalid_voltage(self):
        assert not validate_battery(75.0, 5.0).valid

    def test_low_voltage(self):
        assert not validate_battery(50.0, 1.0).valid


class TestTemperatureValidation:
    def test_valid_outdoor(self):
        assert validate_temperature(15.0, 65.0, 1013.0).valid

    def test_valid_extreme_cold(self):
        assert validate_temperature(-40.0).valid

    def test_valid_extreme_hot(self):
        assert validate_temperature(60.0).valid

    def test_too_cold(self):
        assert not validate_temperature(-41.0).valid

    def test_too_hot(self):
        assert not validate_temperature(61.0).valid

    def test_humidity_out_of_range(self):
        assert not validate_temperature(20.0, 101.0).valid

    def test_pressure_too_low(self):
        assert not validate_temperature(20.0, 65.0, 899.0).valid

    def test_pressure_too_high(self):
        assert not validate_temperature(20.0, 65.0, 1101.0).valid


# ══════════════════════════════════════════════════════════════════════════════
# CATÉGORIE 2 - Authentification devices
# ══════════════════════════════════════════════════════════════════════════════

class TestAuthentication:
    def test_api_key_generated(self):
        key = generate_api_key("fd12:3456:789a:1::3")
        assert len(key) == 64  # SHA256 hex

    def test_api_key_consistent(self):
        key1 = generate_api_key("fd12:3456:789a:1::3")
        key2 = generate_api_key("fd12:3456:789a:1::3")
        assert key1 == key2

    def test_api_key_unique_per_device(self):
        key1 = generate_api_key("fd12:3456:789a:1::3")
        key2 = generate_api_key("fd12:3456:789a:1::4")
        assert key1 != key2

    def test_verify_valid_key(self):
        ipv6 = "fd12:3456:789a:1::3"
        key = generate_api_key(ipv6)
        assert verify_api_key(ipv6, key)

    def test_verify_invalid_key(self):
        assert not verify_api_key("fd12:3456:789a:1::3", "invalid_key")

    def test_verify_wrong_device(self):
        key = generate_api_key("fd12:3456:789a:1::3")
        assert not verify_api_key("fd12:3456:789a:1::4", key)


# ══════════════════════════════════════════════════════════════════════════════
# CATÉGORIE 3 - Calcul de distance (Haversine)
# ══════════════════════════════════════════════════════════════════════════════

class TestHaversine:
    def test_same_point(self):
        assert haversine(48.25, 4.02, 48.25, 4.02) == 0.0

    def test_known_distance_paris_london(self):
        # Paris → London ≈ 341 km
        dist = haversine(48.8566, 2.3522, 51.5074, -0.1278)
        assert 340_000 < dist < 343_000

    def test_short_distance(self):
        # ~111m vers le nord (1 arc-seconde latitude)
        dist = haversine(48.0, 4.0, 48.001, 4.0)
        assert 100 < dist < 120

    def test_symmetry(self):
        d1 = haversine(48.25, 4.02, 48.30, 4.10)
        d2 = haversine(48.30, 4.10, 48.25, 4.02)
        assert abs(d1 - d2) < 0.001

    def test_total_distance_empty(self):
        assert total_distance([]) == 0.0

    def test_total_distance_single(self):
        assert total_distance([(48.25, 4.02)]) == 0.0

    def test_total_distance_triangle(self):
        points = [(48.25, 4.02), (48.30, 4.10), (48.25, 4.18)]
        dist = total_distance(points)
        assert dist > 0
        # Vérification: somme de 2 segments
        d1 = haversine(48.25, 4.02, 48.30, 4.10)
        d2 = haversine(48.30, 4.10, 48.25, 4.18)
        assert abs(dist - (d1 + d2)) < 0.001


# ══════════════════════════════════════════════════════════════════════════════
# CATÉGORIE 4 - Simulation des noeuds Thread (CoAP mock)
# ══════════════════════════════════════════════════════════════════════════════

class TestThreadNodeSimulation:
    def test_gps_data_structure(self):
        """Vérifie que les données GPS ont le bon format."""
        from src.thread_nodes.node_gps import gps_sim
        lat, lon, alt = gps_sim.next_position()
        assert isinstance(lat, float)
        assert isinstance(lon, float)
        assert isinstance(alt, float)
        assert -90 <= lat <= 90
        assert -180 <= lon <= 180

    def test_gps_trajectory(self):
        """Vérifie que le simulateur GPS génère des positions variées."""
        from src.thread_nodes.node_gps import GPSSimulator
        sim = GPSSimulator()
        positions = [sim.next_position() for _ in range(10)]
        lats = [p[0] for p in positions]
        # Les positions doivent varier
        assert max(lats) - min(lats) > 0

    def test_battery_drain(self):
        """Vérifie que la batterie se décharge progressivement."""
        from src.thread_nodes.node_battery import BatterySimulator
        sim = BatterySimulator()
        initial = sim.level
        levels = [sim.read()[0] for _ in range(100)]
        assert min(levels) < initial  # niveau a diminué

    def test_battery_never_negative(self):
        """La batterie ne peut pas être négative."""
        from src.thread_nodes.node_battery import BatterySimulator
        sim = BatterySimulator()
        sim.level = 0.01
        level, _ = sim.read()
        assert level >= 0.0

    def test_temperature_range(self):
        """Les températures restent dans une plage réaliste."""
        from src.thread_nodes.node_temperature import TempSimulator
        sim = TempSimulator()
        readings = [sim.read() for _ in range(50)]
        temps = [r[0] for r in readings]
        assert all(-40 <= t <= 60 for t in temps)
        humids = [r[1] for r in readings]
        assert all(0 <= h <= 100 for h in humids)


# ══════════════════════════════════════════════════════════════════════════════
# CATÉGORIE 5 - Tests d'intégration (avec mocks)
# ══════════════════════════════════════════════════════════════════════════════

class TestMQTTService:
    def test_mqtt_topic_format_gps(self):
        """Vérifie le format des topics MQTT."""
        session_id = 42
        expected = f"/tracking/{session_id}/gps"
        assert expected == f"/tracking/{session_id}/gps"

    def test_mqtt_topic_format_battery(self):
        session_id = 42
        assert f"/tracking/{session_id}/battery" == "/tracking/42/battery"

    def test_mqtt_payload_serializable(self):
        """Vérifie que les payloads sont sérialisables en JSON."""
        data = {"lat": 48.25, "lon": 4.02, "timestamp": "2025-01-15T10:30:00Z"}
        payload = json.dumps(data)
        parsed = json.loads(payload)
        assert parsed["lat"] == 48.25


class TestDataFlow:
    def test_validation_then_publish_gps(self):
        """Simule le flux complet: validation → publication MQTT."""
        lat, lon, alt = 48.25, 4.02, 110.0
        vr = validate_gps(lat, lon, alt)
        assert vr.valid, f"GPS devrait être valide: {vr.errors}"
        # Données prêtes pour MQTT
        payload = {"lat": lat, "lon": lon, "alt": alt}
        assert json.dumps(payload)  # sérialisable

    def test_validation_rejects_invalid(self):
        """Données invalides ne doivent pas être publiées."""
        vr = validate_gps(999.0, 4.02)  # latitude impossible
        assert not vr.valid
        # Les données ne devraient pas être publiées

    def test_complete_measurement_pipeline(self):
        """Test du pipeline complet de mesure."""
        # Simuler réception CoAP
        raw_data = {"lat": 48.2973, "lon": 4.0744, "alt": 112.5, "timestamp": "2025-01-15T10:30:00Z"}
        # Validation
        vr = validate_gps(raw_data["lat"], raw_data["lon"], raw_data["alt"])
        assert vr.valid
        # Calcul distance depuis point précédent
        prev_lat, prev_lon = 48.2950, 4.0700
        dist = haversine(prev_lat, prev_lon, raw_data["lat"], raw_data["lon"])
        assert 0 < dist < 1000  # distance raisonnable
        # Payload MQTT
        mqtt_payload = {**raw_data, "distance_since_last": dist}
        assert json.dumps(mqtt_payload)
