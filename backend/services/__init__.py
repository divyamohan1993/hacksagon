"""
Eco-Lens Backend Services
=========================
Scientific and AI engines for the Virtual Air Quality Matrix.

Services:
    - VisionService:   YOLOv8 vehicle detection with simulation fallback
    - PhysicsEngine:   Gaussian plume dispersion model (EPA emission factors)
    - WeatherService:  OpenWeatherMap API with cached simulation fallback
    - ForecastService: Holt-Winters triple exponential smoothing for PM2.5
    - HealthService:   WHO dose-response health impact scoring
    - AcousticService: FHWA Traffic Noise Model
    - RoutingService:  Pollution-aware A* green corridor routing
    - MeshService:     Ordinary Kriging spatial interpolation
"""

from .vision_service import VisionService
from .physics_engine import PhysicsEngine
from .weather_service import WeatherService
from .forecast_service import ForecastService
from .health_service import HealthService
from .acoustic_service import AcousticService
from .routing_service import RoutingService
from .mesh_service import MeshService

__all__ = [
    "VisionService",
    "PhysicsEngine",
    "WeatherService",
    "ForecastService",
    "HealthService",
    "AcousticService",
    "RoutingService",
    "MeshService",
]
