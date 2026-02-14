"""
Pytest configuration and shared fixtures for Eco-Lens backend tests.
"""

import sys
import os
from datetime import datetime, timezone

import pytest

# ---------------------------------------------------------------------------
# Ensure the backend package root is importable regardless of how pytest
# is invoked (e.g. ``pytest`` from the backend directory or from the repo root).
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from models import (
    SensorData,
    VehicleCounts,
    PollutionData,
    WeatherData,
    NoiseData,
    HealthData,
    GridData,
    GlobalStats,
    ForecastPoint,
)
from services import (
    VisionService,
    PhysicsEngine,
    WeatherService,
    ForecastService,
    HealthService,
    AcousticService,
    RoutingService,
    MeshService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_sensor() -> SensorData:
    """Return a single SensorData instance with realistic Delhi data."""
    return SensorData(
        id="cam-001",
        name="India Gate",
        lat=28.6129,
        lng=77.2295,
        status="active",
        vehicles=VehicleCounts(trucks=8, cars=45, buses=6, motorcycles=12, total=71),
        pollution=PollutionData(
            pm25=42.3, pm10=78.5, no2=35.2, co=450.0, aqi=117, category="Unhealthy for Sensitive Groups"
        ),
        weather=WeatherData(
            wind_speed=3.5, wind_direction=220.0, temperature=32.0, humidity=55.0
        ),
        noise=NoiseData(db_level=72.4, category="Very Loud"),
        health=HealthData(
            score=62,
            risk_level="Moderate",
            equivalent_cigarettes=1.92,
            vulnerable_advisory="Sensitive individuals (children, elderly, respiratory conditions) should limit prolonged outdoor exertion",
        ),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def mock_sensor_b() -> SensorData:
    """Return a second SensorData instance for multi-sensor tests."""
    return SensorData(
        id="cam-002",
        name="Connaught Place",
        lat=28.6315,
        lng=77.2167,
        status="active",
        vehicles=VehicleCounts(trucks=5, cars=50, buses=4, motorcycles=10, total=69),
        pollution=PollutionData(
            pm25=28.0, pm10=55.0, no2=22.0, co=350.0, aqi=84, category="Moderate"
        ),
        weather=WeatherData(
            wind_speed=4.0, wind_direction=200.0, temperature=31.0, humidity=50.0
        ),
        noise=NoiseData(db_level=68.0, category="Very Loud"),
        health=HealthData(
            score=75,
            risk_level="Moderate",
            equivalent_cigarettes=1.27,
            vulnerable_advisory="Sensitive individuals (children, elderly, respiratory conditions) should limit prolonged outdoor exertion",
        ),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def app_state(mock_sensor, mock_sensor_b) -> dict:
    """
    Create a mock application state dictionary that mirrors the structure
    used by main.py.  Contains two sensors, service instances, precomputed
    grid / stats, and an empty forecast list.
    """
    vision_service = VisionService()
    physics_engine = PhysicsEngine()
    weather_service = WeatherService()
    forecast_service = ForecastService()
    health_service = HealthService()
    acoustic_service = AcousticService()
    routing_service = RoutingService()
    mesh_service = MeshService()

    sensors = {
        mock_sensor.id: mock_sensor,
        mock_sensor_b.id: mock_sensor_b,
    }

    # Precompute stats
    sensor_list = list(sensors.values())
    total_vehicles = sum(s.vehicles.total for s in sensor_list)
    avg_aqi = sum(s.pollution.aqi for s in sensor_list) / len(sensor_list)
    avg_pm25 = sum(s.pollution.pm25 for s in sensor_list) / len(sensor_list)
    avg_noise = sum(s.noise.db_level for s in sensor_list) / len(sensor_list)
    healthiest = min(sensor_list, key=lambda s: s.pollution.aqi)
    most_polluted = max(sensor_list, key=lambda s: s.pollution.aqi)

    stats = GlobalStats(
        active_sensors=len(sensor_list),
        avg_aqi=round(avg_aqi, 1),
        avg_pm25=round(avg_pm25, 1),
        avg_noise_db=round(avg_noise, 1),
        total_vehicles_detected=total_vehicles,
        healthiest_zone=healthiest.name,
        most_polluted_zone=most_polluted.name,
    )

    # Precompute grid
    grid = mesh_service.generate_grid(sensor_list)

    return {
        "sensors": sensors,
        "grid": grid,
        "particles": [],
        "stats": stats,
        "forecast": [],
        "services": {
            "vision": vision_service,
            "physics": physics_engine,
            "weather": weather_service,
            "forecast": forecast_service,
            "health": health_service,
            "acoustic": acoustic_service,
            "routing": routing_service,
            "mesh": mesh_service,
        },
    }
