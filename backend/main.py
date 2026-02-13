"""
Eco-Lens Backend - FastAPI Application Entry Point

Virtual Air Quality Matrix that turns traffic cameras into virtual pollution sensors.
Uses Gaussian plume dispersion physics, time-of-day traffic modeling, and real
weather data to generate realistic air quality readings for 6 virtual cameras
placed across NYC.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models import (
    SensorData,
    VehicleCounts,
    PollutionData,
    WeatherData,
    NoiseData,
    HealthData,
    GridData,
    GlobalStats,
    ParticleData,
    ForecastPoint,
)
from database import init_db, save_reading, close_db
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
from api.rest_routes import router as rest_router, set_state as set_rest_state
from api.ws_handler import (
    router as ws_router,
    set_state as set_ws_state,
    broadcast_update,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("ecolens")

# ---------------------------------------------------------------------------
# Virtual camera definitions (NYC locations)
# ---------------------------------------------------------------------------
CAMERAS = [
    {"id": "cam-001", "name": "Times Square",       "lat": 40.7580, "lng": -73.9855},
    {"id": "cam-002", "name": "Brooklyn Bridge",    "lat": 40.7061, "lng": -73.9969},
    {"id": "cam-003", "name": "Central Park South", "lat": 40.7648, "lng": -73.9724},
    {"id": "cam-004", "name": "Wall Street",        "lat": 40.7074, "lng": -74.0113},
    {"id": "cam-005", "name": "Harlem",             "lat": 40.8116, "lng": -73.9465},
    {"id": "cam-006", "name": "Queens Blvd",        "lat": 40.7282, "lng": -73.7949},
]

# ---------------------------------------------------------------------------
# Service instances
# ---------------------------------------------------------------------------
vision_service = VisionService()
physics_engine = PhysicsEngine()
weather_service = WeatherService()
forecast_service = ForecastService()
health_service = HealthService()
acoustic_service = AcousticService()
routing_service = RoutingService()
mesh_service = MeshService()

# ---------------------------------------------------------------------------
# Shared application state
# ---------------------------------------------------------------------------
app_state: Dict = {
    "sensors": {},         # Dict[str, SensorData]
    "grid": None,          # Optional[GridData]
    "particles": [],       # List[ParticleData]
    "stats": GlobalStats(),
    "forecast": [],        # List[ForecastPoint]
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

# Background task handles
_simulation_task: Optional[asyncio.Task] = None
_weather_task: Optional[asyncio.Task] = None

# Current weather (shared across all sensors in simulation)
_current_weather: WeatherData = WeatherData()


# ---------------------------------------------------------------------------
# Weather update loop
# ---------------------------------------------------------------------------
async def weather_update_loop() -> None:
    """Periodically fetch weather data from OpenWeatherMap or simulation."""
    global _current_weather
    logger.info("Weather update loop started (interval: %ds)", settings.WEATHER_UPDATE_INTERVAL)

    while True:
        try:
            _current_weather = await weather_service.fetch_weather(
                lat=settings.MAP_CENTER_LAT,
                lng=settings.MAP_CENTER_LNG,
            )
            logger.info(
                "Weather updated: %.1f C, wind %.1f m/s @ %.0f deg, humidity %.0f%%",
                _current_weather.temperature,
                _current_weather.wind_speed,
                _current_weather.wind_direction,
                _current_weather.humidity,
            )
        except Exception as exc:
            logger.error("Weather update failed: %s", exc)

        await asyncio.sleep(settings.WEATHER_UPDATE_INTERVAL)


# ---------------------------------------------------------------------------
# Compute global statistics
# ---------------------------------------------------------------------------
def compute_global_stats(sensors: Dict[str, SensorData]) -> GlobalStats:
    """Compute aggregate statistics across all sensors."""
    sensor_list = list(sensors.values())
    if not sensor_list:
        return GlobalStats()

    total_vehicles = sum(s.vehicles.total for s in sensor_list)
    avg_aqi = sum(s.pollution.aqi for s in sensor_list) / len(sensor_list)
    avg_pm25 = sum(s.pollution.pm25 for s in sensor_list) / len(sensor_list)
    avg_noise = sum(s.noise.db_level for s in sensor_list) / len(sensor_list)

    healthiest = min(sensor_list, key=lambda s: s.pollution.aqi)
    most_polluted = max(sensor_list, key=lambda s: s.pollution.aqi)

    return GlobalStats(
        active_sensors=len(sensor_list),
        avg_aqi=round(avg_aqi, 1),
        avg_pm25=round(avg_pm25, 1),
        avg_noise_db=round(avg_noise, 1),
        total_vehicles_detected=total_vehicles,
        healthiest_zone=healthiest.name,
        most_polluted_zone=most_polluted.name,
    )


# ---------------------------------------------------------------------------
# Simulation loop
# ---------------------------------------------------------------------------
async def simulation_loop() -> None:
    """
    Main simulation loop. Every SENSOR_UPDATE_INTERVAL seconds:
    1. Detect vehicles at each camera (simulated)
    2. Calculate pollution using Gaussian plume model
    3. Estimate noise levels
    4. Compute health impacts
    5. Generate forecast
    6. Build interpolated grid
    7. Generate particles
    8. Update global stats
    9. Save to database
    10. Broadcast via WebSocket
    """
    logger.info(
        "Simulation loop started (interval: %ds, cameras: %d)",
        settings.SENSOR_UPDATE_INTERVAL,
        len(CAMERAS),
    )

    # Initial weather fetch
    global _current_weather
    try:
        _current_weather = await weather_service.fetch_weather(
            lat=settings.MAP_CENTER_LAT,
            lng=settings.MAP_CENTER_LNG,
        )
    except Exception:
        logger.warning("Initial weather fetch failed, using defaults")

    cycle = 0
    while True:
        try:
            cycle += 1
            now = datetime.now(timezone.utc)
            timestamp = now.isoformat()

            all_particles: List[ParticleData] = []

            for cam in CAMERAS:
                cam_id = cam["id"]

                # 1. Vehicle detection
                vehicles = vision_service.detect_vehicles(cam_id)

                # 2. Pollution calculation (Gaussian plume)
                pollution = physics_engine.calculate_pollution(vehicles, _current_weather)

                # 3. Noise estimation
                noise = acoustic_service.estimate_noise(vehicles)

                # 4. Health impact
                health = health_service.calculate_health_impact(pollution, noise)

                # 5. Record observation for forecasting
                forecast_service.record_observation(cam_id, pollution.pm25)

                # 6. Generate particles
                particles = physics_engine.generate_particles(
                    sensor_id=cam_id,
                    lat=cam["lat"],
                    lng=cam["lng"],
                    pollution=pollution,
                    weather=_current_weather,
                    count=12,
                )
                all_particles.extend(particles)

                # Build sensor data
                sensor = SensorData(
                    id=cam_id,
                    name=cam["name"],
                    lat=cam["lat"],
                    lng=cam["lng"],
                    status="active",
                    vehicles=vehicles,
                    pollution=pollution,
                    weather=_current_weather,
                    noise=noise,
                    health=health,
                    timestamp=timestamp,
                )
                app_state["sensors"][cam_id] = sensor

                # 9. Save to database (every 12th cycle = ~1 minute to avoid DB bloat)
                if cycle % 12 == 0:
                    try:
                        await save_reading(
                            sensor_id=cam_id,
                            pm25=pollution.pm25,
                            pm10=pollution.pm10,
                            no2=pollution.no2,
                            co=pollution.co,
                            aqi=pollution.aqi,
                            noise_db=noise.db_level,
                            trucks=vehicles.trucks,
                            cars=vehicles.cars,
                            buses=vehicles.buses,
                            wind_speed=_current_weather.wind_speed,
                            wind_direction=_current_weather.wind_direction,
                            temperature=_current_weather.temperature,
                        )
                    except Exception as exc:
                        logger.error("DB save failed for %s: %s", cam_id, exc)

            # 7. Build interpolated grid (every 3rd cycle to save CPU)
            if cycle % 3 == 0:
                sensors_list = list(app_state["sensors"].values())
                grid = mesh_service.generate_grid(sensors_list)
                app_state["grid"] = grid

            # 8. Update global stats
            app_state["stats"] = compute_global_stats(app_state["sensors"])
            app_state["particles"] = all_particles

            # Generate forecast for the first sensor (representative)
            if app_state["sensors"]:
                first_id = CAMERAS[0]["id"]
                app_state["forecast"] = forecast_service.generate_forecast(
                    first_id, hours_ahead=6, interval_minutes=30
                )

            # 10. Broadcast to WebSocket clients
            await broadcast_update()

            if cycle % 12 == 0:
                stats = app_state["stats"]
                logger.info(
                    "Cycle %d | AQI: %.0f | PM2.5: %.1f | Vehicles: %d | WS clients active",
                    cycle,
                    stats.avg_aqi,
                    stats.avg_pm25,
                    stats.total_vehicles_detected,
                )

        except Exception as exc:
            logger.error("Simulation loop error: %s", exc, exc_info=True)

        await asyncio.sleep(settings.SENSOR_UPDATE_INTERVAL)


# ---------------------------------------------------------------------------
# Lifespan context manager
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic for the FastAPI application."""
    global _simulation_task, _weather_task

    logger.info("Eco-Lens backend starting up...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Inject shared state into API modules
    set_rest_state(app_state)
    set_ws_state(app_state)

    # Start background tasks
    _weather_task = asyncio.create_task(weather_update_loop())

    if settings.SIMULATION_MODE:
        logger.info("Starting simulation mode")
        _simulation_task = asyncio.create_task(simulation_loop())
    else:
        logger.info("Simulation mode disabled - waiting for real camera feeds")

    logger.info(
        "Eco-Lens backend ready at http://%s:%d",
        settings.HOST,
        settings.PORT,
    )

    yield

    # Shutdown
    logger.info("Eco-Lens backend shutting down...")

    if _simulation_task is not None:
        _simulation_task.cancel()
        try:
            await _simulation_task
        except asyncio.CancelledError:
            pass

    if _weather_task is not None:
        _weather_task.cancel()
        try:
            await _weather_task
        except asyncio.CancelledError:
            pass

    await close_db()
    logger.info("Shutdown complete")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Eco-Lens",
    description="Virtual Air Quality Matrix - Turn traffic cameras into pollution sensors",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rest_router)
app.include_router(ws_router)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level="info",
    )
