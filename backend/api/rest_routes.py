"""
REST API Routes for Eco-Lens backend.

Provides endpoints for sensor data, forecasts, health impacts,
green routing, pollution grids, and global statistics.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from models import (
    SensorData,
    ForecastPoint,
    GreenRoute,
    GridData,
    GlobalStats,
    HealthData,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Global state reference - populated by main.py at startup
# ---------------------------------------------------------------------------
# This dict is shared with main.py's simulation loop. It holds:
#   "sensors": Dict[str, SensorData]     -- current sensor readings
#   "services": Dict[str, Any]           -- service instances
#   "grid": Optional[GridData]           -- latest interpolated grid
#   "stats": GlobalStats                 -- latest global stats

_state: dict = {}


def set_state(state: dict) -> None:
    """Called by main.py to inject the shared state dict."""
    global _state
    _state = state


def _get_sensors_list() -> List[SensorData]:
    """Return all current sensor data as a list."""
    sensors_dict = _state.get("sensors", {})
    return list(sensors_dict.values())


def _get_sensor(sensor_id: str) -> SensorData:
    """Return a single sensor or raise 404."""
    sensors_dict = _state.get("sensors", {})
    sensor = sensors_dict.get(sensor_id)
    if sensor is None:
        raise HTTPException(status_code=404, detail=f"Sensor '{sensor_id}' not found")
    return sensor


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/api/health")
async def health_check():
    """Health check endpoint."""
    sensors = _state.get("sensors", {})
    return {
        "status": "ok",
        "version": "1.0.0",
        "sensors_active": len(sensors),
    }


@router.get("/api/sensors", response_model=List[SensorData])
async def list_sensors():
    """List all sensors with current data."""
    return _get_sensors_list()


@router.get("/api/sensors/{sensor_id}", response_model=SensorData)
async def get_sensor(sensor_id: str):
    """Get specific sensor data."""
    return _get_sensor(sensor_id)


@router.get("/api/sensors/{sensor_id}/history")
async def get_sensor_history(
    sensor_id: str,
    hours: int = Query(default=24, ge=1, le=168),
):
    """Get historical data for a sensor."""
    # Validate sensor exists
    _get_sensor(sensor_id)

    from database import get_history
    history = await get_history(sensor_id, hours=hours)
    return {"sensor_id": sensor_id, "hours": hours, "readings": history}


@router.get("/api/forecast/{sensor_id}", response_model=List[ForecastPoint])
async def get_forecast(sensor_id: str):
    """Get 6-hour pollution forecast for a sensor."""
    # Validate sensor exists
    _get_sensor(sensor_id)

    services = _state.get("services", {})
    forecast_service = services.get("forecast")
    if forecast_service is None:
        raise HTTPException(status_code=503, detail="Forecast service unavailable")

    forecast = forecast_service.generate_forecast(sensor_id, hours_ahead=6, interval_minutes=30)
    return forecast


@router.get("/api/health-impact")
async def get_health_impact():
    """Get health impact summary across all sensors."""
    sensors = _get_sensors_list()
    services = _state.get("services", {})
    health_service = services.get("health")

    if health_service is None:
        raise HTTPException(status_code=503, detail="Health service unavailable")

    health_data_list = [s.health for s in sensors]
    summary = health_service.get_aggregate_health_summary(health_data_list)

    # Include per-sensor breakdown
    per_sensor = []
    for s in sensors:
        per_sensor.append({
            "sensor_id": s.id,
            "name": s.name,
            "health_score": s.health.score,
            "risk_level": s.health.risk_level,
            "equivalent_cigarettes": s.health.equivalent_cigarettes,
            "advisory": s.health.vulnerable_advisory,
        })

    return {
        "summary": summary,
        "sensors": per_sensor,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/routing/green-path", response_model=GreenRoute)
async def get_green_route(
    from_lat: float = Query(..., description="Start latitude"),
    from_lng: float = Query(..., description="Start longitude"),
    to_lat: float = Query(..., description="End latitude"),
    to_lng: float = Query(..., description="End longitude"),
):
    """Get green corridor route minimizing pollution exposure."""
    services = _state.get("services", {})
    routing_service = services.get("routing")

    if routing_service is None:
        raise HTTPException(status_code=503, detail="Routing service unavailable")

    # Update routing service with current sensor data
    sensors = _get_sensors_list()
    routing_service.update_sensors(sensors)

    route = routing_service.find_green_route(from_lat, from_lng, to_lat, to_lng)
    return route


@router.get("/api/grid", response_model=GridData)
async def get_pollution_grid():
    """Get interpolated pollution grid for heatmap visualization."""
    grid = _state.get("grid")
    if grid is not None:
        return grid

    # Generate on demand if not cached
    services = _state.get("services", {})
    mesh_service = services.get("mesh")
    if mesh_service is None:
        raise HTTPException(status_code=503, detail="Mesh service unavailable")

    sensors = _get_sensors_list()
    grid = mesh_service.generate_grid(sensors)
    return grid


@router.get("/api/stats", response_model=GlobalStats)
async def get_global_stats():
    """Get global statistics across all sensors."""
    stats = _state.get("stats")
    if stats is not None:
        return stats

    # Calculate on demand if not cached
    sensors = _get_sensors_list()
    if not sensors:
        return GlobalStats()

    total_vehicles = sum(s.vehicles.total for s in sensors)
    avg_aqi = sum(s.pollution.aqi for s in sensors) / len(sensors)
    avg_pm25 = sum(s.pollution.pm25 for s in sensors) / len(sensors)
    avg_noise = sum(s.noise.db_level for s in sensors) / len(sensors)

    healthiest = min(sensors, key=lambda s: s.pollution.aqi)
    most_polluted = max(sensors, key=lambda s: s.pollution.aqi)

    return GlobalStats(
        active_sensors=len(sensors),
        avg_aqi=round(avg_aqi, 1),
        avg_pm25=round(avg_pm25, 1),
        avg_noise_db=round(avg_noise, 1),
        total_vehicles_detected=total_vehicles,
        healthiest_zone=healthiest.name,
        most_polluted_zone=most_polluted.name,
    )
