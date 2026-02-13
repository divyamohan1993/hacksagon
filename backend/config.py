from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"

    # OpenWeatherMap
    OPENWEATHERMAP_API_KEY: str = ""

    # Mode
    SIMULATION_MODE: bool = True

    # Camera feeds
    CAMERA_FEED_URL_1: str = ""
    CAMERA_FEED_URL_2: str = ""
    CAMERA_FEED_URL_3: str = ""

    # Database
    DATABASE_URL: str = "sqlite:///./ecolens.db"

    # Processing
    FRAME_INTERVAL: int = 5  # seconds between frame captures
    SENSOR_UPDATE_INTERVAL: int = 5  # seconds between updates
    WEATHER_UPDATE_INTERVAL: int = 300  # 5 minutes

    # Map bounds (NYC default)
    MAP_CENTER_LAT: float = 40.7580
    MAP_CENTER_LNG: float = -73.9855

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
