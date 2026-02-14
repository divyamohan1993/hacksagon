"""
Tests for Eco-Lens Pydantic models (models.py).

Validates default values, field types, construction with explicit data,
nested model composition, and JSON serialisation.
"""

import sys
import os
from datetime import datetime, timezone

import pytest

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from models import (
    VehicleCounts,
    PollutionData,
    WeatherData,
    NoiseData,
    HealthData,
    SensorData,
    GridData,
    ForecastPoint,
    GreenRoute,
    GlobalStats,
    ParticleData,
    RoutePoint,
    WebSocketMessage,
)


# ===================================================================
# VehicleCounts
# ===================================================================


class TestVehicleCounts:
    """Tests for the VehicleCounts model."""

    def test_defaults(self):
        vc = VehicleCounts()
        assert vc.trucks == 0
        assert vc.cars == 0
        assert vc.buses == 0
        assert vc.motorcycles == 0
        assert vc.total == 0

    def test_explicit_values(self):
        vc = VehicleCounts(trucks=10, cars=50, buses=5, motorcycles=20, total=85)
        assert vc.trucks == 10
        assert vc.cars == 50
        assert vc.buses == 5
        assert vc.motorcycles == 20
        assert vc.total == 85

    def test_partial_values(self):
        vc = VehicleCounts(cars=30, trucks=5)
        assert vc.cars == 30
        assert vc.trucks == 5
        assert vc.buses == 0
        assert vc.motorcycles == 0
        assert vc.total == 0  # total is not auto-calculated

    def test_validation_rejects_wrong_types(self):
        with pytest.raises(Exception):
            VehicleCounts(trucks="not_a_number")


# ===================================================================
# PollutionData
# ===================================================================


class TestPollutionData:
    """Tests for the PollutionData model."""

    def test_defaults(self):
        pd = PollutionData()
        assert pd.pm25 == 0.0
        assert pd.pm10 == 0.0
        assert pd.no2 == 0.0
        assert pd.co == 0.0
        assert pd.aqi == 0
        assert pd.category == "Good"

    def test_explicit_values(self):
        pd = PollutionData(pm25=42.3, pm10=78.5, no2=35.2, co=450.0, aqi=117, category="USG")
        assert pd.pm25 == 42.3
        assert pd.pm10 == 78.5
        assert pd.aqi == 117
        assert pd.category == "USG"


# ===================================================================
# WeatherData
# ===================================================================


class TestWeatherData:
    def test_defaults(self):
        wd = WeatherData()
        assert wd.wind_speed == 0.0
        assert wd.wind_direction == 0.0
        assert wd.temperature == 20.0
        assert wd.humidity == 50.0

    def test_explicit_values(self):
        wd = WeatherData(wind_speed=5.5, wind_direction=180.0, temperature=35.0, humidity=70.0)
        assert wd.wind_speed == 5.5
        assert wd.temperature == 35.0


# ===================================================================
# NoiseData
# ===================================================================


class TestNoiseData:
    def test_defaults(self):
        nd = NoiseData()
        assert nd.db_level == 0.0
        assert nd.category == "Quiet"

    def test_explicit_values(self):
        nd = NoiseData(db_level=75.0, category="Extreme")
        assert nd.db_level == 75.0
        assert nd.category == "Extreme"


# ===================================================================
# HealthData
# ===================================================================


class TestHealthData:
    def test_defaults(self):
        hd = HealthData()
        assert hd.score == 100
        assert hd.risk_level == "Low"
        assert hd.equivalent_cigarettes == 0.0
        assert hd.vulnerable_advisory == "Safe for all groups"

    def test_explicit_values(self):
        hd = HealthData(score=40, risk_level="High", equivalent_cigarettes=3.5, vulnerable_advisory="Stay indoors")
        assert hd.score == 40
        assert hd.risk_level == "High"


# ===================================================================
# SensorData
# ===================================================================


class TestSensorData:
    def test_construction_with_all_fields(self):
        ts = datetime.now(timezone.utc).isoformat()
        sensor = SensorData(
            id="cam-003",
            name="ITO Junction",
            lat=28.6280,
            lng=77.2413,
            status="active",
            vehicles=VehicleCounts(trucks=10, cars=50, buses=10, motorcycles=18, total=88),
            pollution=PollutionData(pm25=55.0, pm10=90.0, no2=40.0, co=500.0, aqi=150, category="Unhealthy"),
            weather=WeatherData(wind_speed=2.5, wind_direction=190.0, temperature=33.0, humidity=60.0),
            noise=NoiseData(db_level=78.0, category="Extreme"),
            health=HealthData(score=45, risk_level="High"),
            timestamp=ts,
        )
        assert sensor.id == "cam-003"
        assert sensor.name == "ITO Junction"
        assert sensor.lat == 28.6280
        assert sensor.lng == 77.2413
        assert sensor.status == "active"
        assert sensor.vehicles.total == 88
        assert sensor.pollution.aqi == 150
        assert sensor.weather.temperature == 33.0
        assert sensor.noise.db_level == 78.0
        assert sensor.health.score == 45
        assert sensor.timestamp == ts

    def test_default_status(self):
        ts = datetime.now(timezone.utc).isoformat()
        sensor = SensorData(
            id="cam-x",
            name="Test",
            lat=0.0,
            lng=0.0,
            vehicles=VehicleCounts(),
            pollution=PollutionData(),
            weather=WeatherData(),
            noise=NoiseData(),
            health=HealthData(),
            timestamp=ts,
        )
        assert sensor.status == "active"

    def test_missing_required_raises(self):
        with pytest.raises(Exception):
            SensorData(id="cam-x", name="Test")  # missing required fields


# ===================================================================
# GridData
# ===================================================================


class TestGridData:
    def test_construction(self):
        gd = GridData(
            bounds={"north": 28.7, "south": 28.5, "east": 77.4, "west": 77.0},
            resolution=5,
            values=[[10.0] * 5 for _ in range(5)],
        )
        assert gd.resolution == 5
        assert len(gd.values) == 5
        assert len(gd.values[0]) == 5
        assert gd.bounds["north"] == 28.7


# ===================================================================
# ForecastPoint
# ===================================================================


class TestForecastPoint:
    def test_construction(self):
        fp = ForecastPoint(
            timestamp="2026-02-14T12:00:00Z",
            predicted_pm25=35.5,
            confidence_lower=28.0,
            confidence_upper=43.0,
        )
        assert fp.predicted_pm25 == 35.5
        assert fp.confidence_lower == 28.0
        assert fp.confidence_upper == 43.0


# ===================================================================
# GreenRoute
# ===================================================================


class TestGreenRoute:
    def test_construction(self):
        gr = GreenRoute(
            path=[[28.61, 77.22], [28.62, 77.23], [28.63, 77.24]],
            total_distance_km=2.5,
            avg_pollution=30.0,
            estimated_exposure=75.0,
            comparison={
                "shortest_path_exposure": 100.0,
                "green_path_exposure": 75.0,
                "reduction_percent": 25.0,
            },
        )
        assert len(gr.path) == 3
        assert gr.total_distance_km == 2.5
        assert gr.comparison["reduction_percent"] == 25.0


# ===================================================================
# GlobalStats
# ===================================================================


class TestGlobalStats:
    def test_defaults(self):
        gs = GlobalStats()
        assert gs.active_sensors == 0
        assert gs.avg_aqi == 0.0
        assert gs.avg_pm25 == 0.0
        assert gs.avg_noise_db == 0.0
        assert gs.total_vehicles_detected == 0
        assert gs.healthiest_zone == ""
        assert gs.most_polluted_zone == ""

    def test_explicit_values(self):
        gs = GlobalStats(
            active_sensors=6,
            avg_aqi=105.0,
            avg_pm25=38.0,
            avg_noise_db=70.0,
            total_vehicles_detected=500,
            healthiest_zone="Dwarka Sec-8",
            most_polluted_zone="ITO Junction",
        )
        assert gs.active_sensors == 6
        assert gs.most_polluted_zone == "ITO Junction"


# ===================================================================
# ParticleData
# ===================================================================


class TestParticleData:
    def test_construction(self):
        p = ParticleData(
            x=77.2295, y=28.6129, vx=0.00001, vy=-0.00001,
            concentration=0.7, age=3.5, source_id="cam-001",
        )
        assert p.x == 77.2295
        assert p.source_id == "cam-001"


# ===================================================================
# RoutePoint
# ===================================================================


class TestRoutePoint:
    def test_construction(self):
        rp = RoutePoint(lat=28.6129, lng=77.2295)
        assert rp.lat == 28.6129
        assert rp.lng == 77.2295


# ===================================================================
# WebSocketMessage
# ===================================================================


class TestWebSocketMessage:
    def test_serialization(self, mock_sensor):
        ts = datetime.now(timezone.utc).isoformat()
        msg = WebSocketMessage(
            type="sensor_update",
            timestamp=ts,
            sensors=[mock_sensor],
            grid=None,
            particles=[],
            stats=GlobalStats(active_sensors=1),
            forecast=[],
        )
        data = msg.model_dump()
        assert data["type"] == "sensor_update"
        assert data["timestamp"] == ts
        assert len(data["sensors"]) == 1
        assert data["sensors"][0]["id"] == "cam-001"
        assert data["stats"]["active_sensors"] == 1
        assert data["grid"] is None
        assert data["particles"] == []
        assert data["forecast"] == []

    def test_json_serialization(self, mock_sensor):
        ts = datetime.now(timezone.utc).isoformat()
        msg = WebSocketMessage(
            type="sensor_update",
            timestamp=ts,
            sensors=[mock_sensor],
            stats=GlobalStats(),
        )
        json_str = msg.model_dump_json()
        assert isinstance(json_str, str)
        assert "sensor_update" in json_str
        assert "cam-001" in json_str

    def test_default_type(self, mock_sensor):
        ts = datetime.now(timezone.utc).isoformat()
        msg = WebSocketMessage(
            timestamp=ts,
            sensors=[mock_sensor],
            stats=GlobalStats(),
        )
        assert msg.type == "sensor_update"
