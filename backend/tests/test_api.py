"""
Tests for the Eco-Lens REST API endpoints (api/rest_routes.py).

Uses httpx.AsyncClient with ASGITransport to drive requests against the
FastAPI app without starting a real server.  Injects a mock application
state before each test so the endpoints have data to return.
"""

import sys
import os
from datetime import datetime, timezone

import pytest

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from models import (
    SensorData,
    VehicleCounts,
    PollutionData,
    WeatherData,
    NoiseData,
    HealthData,
    GlobalStats,
)
from api.rest_routes import router as rest_router, set_state as set_rest_state
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
# Create a minimal FastAPI app for testing (no lifespan, no middleware).
# This avoids triggering database init, background tasks, etc.
# ---------------------------------------------------------------------------
def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(rest_router)
    return app


def _build_test_state() -> dict:
    """Build a self-contained test state dict with two sensors."""
    ts = datetime.now(timezone.utc).isoformat()

    sensor_a = SensorData(
        id="cam-001",
        name="India Gate",
        lat=28.6129,
        lng=77.2295,
        status="active",
        vehicles=VehicleCounts(trucks=8, cars=45, buses=6, motorcycles=12, total=71),
        pollution=PollutionData(pm25=42.3, pm10=78.5, no2=35.2, co=450.0, aqi=117, category="USG"),
        weather=WeatherData(wind_speed=3.5, wind_direction=220.0, temperature=32.0, humidity=55.0),
        noise=NoiseData(db_level=72.4, category="Very Loud"),
        health=HealthData(score=62, risk_level="Moderate", equivalent_cigarettes=1.92),
        timestamp=ts,
    )

    sensor_b = SensorData(
        id="cam-002",
        name="Connaught Place",
        lat=28.6315,
        lng=77.2167,
        status="active",
        vehicles=VehicleCounts(trucks=5, cars=50, buses=4, motorcycles=10, total=69),
        pollution=PollutionData(pm25=28.0, pm10=55.0, no2=22.0, co=350.0, aqi=84, category="Moderate"),
        weather=WeatherData(wind_speed=4.0, wind_direction=200.0, temperature=31.0, humidity=50.0),
        noise=NoiseData(db_level=68.0, category="Very Loud"),
        health=HealthData(score=75, risk_level="Moderate", equivalent_cigarettes=1.27),
        timestamp=ts,
    )

    sensors = {sensor_a.id: sensor_a, sensor_b.id: sensor_b}

    forecast_service = ForecastService()
    # Seed the forecast service so generate_forecast returns data
    for _ in range(20):
        forecast_service.record_observation("cam-001", 42.0)
        forecast_service.record_observation("cam-002", 28.0)

    mesh_service = MeshService()
    sensor_list = list(sensors.values())
    grid = mesh_service.generate_grid(sensor_list)

    avg_aqi = sum(s.pollution.aqi for s in sensor_list) / len(sensor_list)
    stats = GlobalStats(
        active_sensors=2,
        avg_aqi=round(avg_aqi, 1),
        avg_pm25=35.15,
        avg_noise_db=70.2,
        total_vehicles_detected=140,
        healthiest_zone="Connaught Place",
        most_polluted_zone="India Gate",
    )

    return {
        "sensors": sensors,
        "grid": grid,
        "particles": [],
        "stats": stats,
        "forecast": [],
        "services": {
            "vision": VisionService(),
            "physics": PhysicsEngine(),
            "weather": WeatherService(),
            "forecast": forecast_service,
            "health": HealthService(),
            "acoustic": AcousticService(),
            "routing": RoutingService(),
            "mesh": mesh_service,
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_app():
    """Return a fresh test FastAPI app with injected state."""
    app = _create_test_app()
    state = _build_test_state()
    set_rest_state(state)
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_endpoint(test_app):
    """GET /api/health should return status ok."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data["sensors_active"] == 2


@pytest.mark.asyncio
async def test_list_sensors(test_app):
    """GET /api/sensors should return a list of SensorData."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/api/sensors")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    ids = {s["id"] for s in data}
    assert "cam-001" in ids
    assert "cam-002" in ids


@pytest.mark.asyncio
async def test_get_sensor_by_id(test_app):
    """GET /api/sensors/{id} should return the correct sensor."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/api/sensors/cam-001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "cam-001"
    assert data["name"] == "India Gate"
    assert data["pollution"]["pm25"] == 42.3


@pytest.mark.asyncio
async def test_get_sensor_not_found(test_app):
    """GET /api/sensors/{id} with a nonexistent id should return 404."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/api/sensors/cam-999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_forecast_endpoint(test_app):
    """GET /api/forecast/{sensor_id} should return a list of ForecastPoint."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/api/forecast/cam-001")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    point = data[0]
    assert "timestamp" in point
    assert "predicted_pm25" in point
    assert "confidence_lower" in point
    assert "confidence_upper" in point
    # confidence_lower should be <= predicted_pm25 <= confidence_upper
    assert point["confidence_lower"] <= point["predicted_pm25"] <= point["confidence_upper"]


@pytest.mark.asyncio
async def test_forecast_sensor_not_found(test_app):
    """GET /api/forecast/{sensor_id} with a bad id should return 404."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/api/forecast/cam-999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stats_endpoint(test_app):
    """GET /api/stats should return GlobalStats."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["active_sensors"] == 2
    assert data["avg_aqi"] > 0
    assert data["total_vehicles_detected"] == 140
    assert data["healthiest_zone"] == "Connaught Place"
    assert data["most_polluted_zone"] == "India Gate"


@pytest.mark.asyncio
async def test_grid_endpoint(test_app):
    """GET /api/grid should return GridData."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/api/grid")
    assert response.status_code == 200
    data = response.json()
    assert "bounds" in data
    assert "resolution" in data
    assert "values" in data
    assert isinstance(data["values"], list)
    assert len(data["values"]) > 0
    assert len(data["values"][0]) > 0
    # All grid values should be non-negative (PM2.5)
    for row in data["values"]:
        for val in row:
            assert val >= 0.0


@pytest.mark.asyncio
async def test_health_impact_endpoint(test_app):
    """GET /api/health-impact should return health summary and per-sensor data."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/api/health-impact")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "sensors" in data
    assert "timestamp" in data
    assert len(data["sensors"]) == 2
    assert data["summary"]["sensor_count"] == 2


@pytest.mark.asyncio
async def test_sensors_response_structure(test_app):
    """Each sensor in /api/sensors should contain all expected nested fields."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/api/sensors")
    data = response.json()
    sensor = data[0]
    # Top-level fields
    for key in ("id", "name", "lat", "lng", "status", "timestamp"):
        assert key in sensor, f"Missing top-level field: {key}"
    # Nested models
    for key in ("vehicles", "pollution", "weather", "noise", "health"):
        assert key in sensor, f"Missing nested field: {key}"
    # Vehicle fields
    for vkey in ("trucks", "cars", "buses", "motorcycles", "total"):
        assert vkey in sensor["vehicles"]
    # Pollution fields
    for pkey in ("pm25", "pm10", "no2", "co", "aqi", "category"):
        assert pkey in sensor["pollution"]
