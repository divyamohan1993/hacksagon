from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class VehicleCounts(BaseModel):
    trucks: int = 0
    cars: int = 0
    buses: int = 0
    motorcycles: int = 0
    total: int = 0


class PollutionData(BaseModel):
    pm25: float = 0.0
    pm10: float = 0.0
    no2: float = 0.0
    co: float = 0.0
    aqi: int = 0
    category: str = "Good"


class WeatherData(BaseModel):
    wind_speed: float = 0.0
    wind_direction: float = 0.0
    temperature: float = 20.0
    humidity: float = 50.0


class NoiseData(BaseModel):
    db_level: float = 0.0
    category: str = "Quiet"


class HealthData(BaseModel):
    score: int = 100
    risk_level: str = "Low"
    equivalent_cigarettes: float = 0.0
    vulnerable_advisory: str = "Safe for all groups"


class SensorData(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    status: str = "active"
    vehicles: VehicleCounts
    pollution: PollutionData
    weather: WeatherData
    noise: NoiseData
    health: HealthData
    timestamp: str


class GridData(BaseModel):
    bounds: dict  # {north, south, east, west}
    resolution: int
    values: List[List[float]]


class ForecastPoint(BaseModel):
    timestamp: str
    predicted_pm25: float
    confidence_lower: float
    confidence_upper: float


class RoutePoint(BaseModel):
    lat: float
    lng: float


class GreenRoute(BaseModel):
    path: List[List[float]]
    total_distance_km: float
    avg_pollution: float
    estimated_exposure: float
    comparison: dict  # {shortest_path_exposure, green_path_exposure, reduction_percent}


class ParticleData(BaseModel):
    x: float
    y: float
    vx: float
    vy: float
    concentration: float
    age: float
    source_id: str


class GlobalStats(BaseModel):
    active_sensors: int = 0
    avg_aqi: float = 0.0
    avg_pm25: float = 0.0
    avg_noise_db: float = 0.0
    total_vehicles_detected: int = 0
    healthiest_zone: str = ""
    most_polluted_zone: str = ""


class WebSocketMessage(BaseModel):
    type: str = "sensor_update"
    timestamp: str
    sensors: List[SensorData]
    grid: Optional[GridData] = None
    particles: List[ParticleData] = []
    stats: GlobalStats
    forecast: List[ForecastPoint] = []
