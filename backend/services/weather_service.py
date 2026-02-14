"""
Eco-Lens Weather Service
=========================
Fetches real-time weather data from the OpenWeatherMap API for wind,
temperature, and humidity conditions that drive the Gaussian plume model.

Modes:
  1. **Live API** - Real data from OpenWeatherMap (requires API key in
     settings.OPENWEATHERMAP_API_KEY).
  2. **Simulated** - Generates realistic weather using month-aware diurnal
     models when no API key is configured. Wind state uses a smooth random
     walk to avoid discontinuities between successive calls.
  3. **Cached** - Returns the last live result within the TTL window to
     stay within free-tier API rate limits (60 calls/min).

References:
    - OpenWeatherMap Current Weather API: https://openweathermap.org/current
"""

import math
import random
import logging
from datetime import datetime, timezone
from typing import Optional, Dict

import httpx

from config import settings
from models import WeatherData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default Delhi monthly temperature ranges (approximate, Celsius)
# Source: IMD (India Meteorological Department) climate normals for Delhi
# ---------------------------------------------------------------------------
_MONTHLY_TEMP_RANGES: Dict[int, tuple] = {
    1:  ( 4.0,  20.0),
    2:  ( 7.0,  23.0),
    3:  (12.0,  30.0),
    4:  (18.0,  37.0),
    5:  (23.0,  41.0),
    6:  (26.0,  40.0),
    7:  (26.0,  36.0),
    8:  (25.0,  34.0),
    9:  (23.0,  35.0),
    10: (16.0,  33.0),
    11: (10.0,  28.0),
    12: ( 5.0,  22.0),
}


class WeatherService:
    """
    Provides weather data for the Eco-Lens physics engine.

    Supports live API queries, transparent caching, and a smooth
    simulation fallback.
    """

    def __init__(self) -> None:
        self._api_key: str = settings.OPENWEATHERMAP_API_KEY
        self._cache: Optional[WeatherData] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds: int = settings.WEATHER_UPDATE_INTERVAL
        self._base_url = "https://api.openweathermap.org/data/2.5/weather"

        # Smooth random-walk state for simulation
        self._sim_wind_speed: float = 3.5
        self._sim_wind_dir: float = 220.0

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def _is_cache_valid(self) -> bool:
        """Check whether the cached weather is still fresh."""
        if self._cache is None or self._cache_time is None:
            return False
        elapsed = (datetime.now(timezone.utc) - self._cache_time).total_seconds()
        return elapsed < self._cache_ttl_seconds

    def invalidate_cache(self) -> None:
        """Force the next call to fetch fresh data."""
        self._cache = None
        self._cache_time = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_weather(
        self,
        lat: float = settings.MAP_CENTER_LAT,
        lng: float = settings.MAP_CENTER_LNG,
    ) -> WeatherData:
        """
        Fetch current weather for the given coordinates.

        Uses cache first, then live API (if key is set), then simulation.

        Parameters
        ----------
        lat, lng : float
            Geographic coordinates (default: NYC map center).

        Returns
        -------
        WeatherData
            Pydantic model with wind_speed, wind_direction, temperature,
            humidity.
        """
        if self._is_cache_valid() and self._cache is not None:
            return self._cache

        if self._api_key:
            try:
                weather = await self._fetch_from_api(lat, lng)
                self._cache = weather
                self._cache_time = datetime.now(timezone.utc)
                return weather
            except Exception as exc:
                logger.warning(
                    "OpenWeatherMap API call failed, using simulation: %s", exc
                )

        weather = self._simulate_weather()
        self._cache = weather
        self._cache_time = datetime.now(timezone.utc)
        return weather

    # ------------------------------------------------------------------
    # Live API fetch
    # ------------------------------------------------------------------

    async def _fetch_from_api(self, lat: float, lng: float) -> WeatherData:
        """
        Call OpenWeatherMap Current Weather API.

        Raises
        ------
        httpx.HTTPStatusError
            If the API returns a non-2xx status code.
        """
        params = {
            "lat": lat,
            "lon": lng,
            "appid": self._api_key,
            "units": "metric",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(self._base_url, params=params)
            response.raise_for_status()
            data = response.json()

        wind = data.get("wind", {})
        main = data.get("main", {})

        return WeatherData(
            wind_speed=float(wind.get("speed", 3.0)),
            wind_direction=float(wind.get("deg", 220.0)),
            temperature=float(main.get("temp", 20.0)),
            humidity=float(main.get("humidity", 50.0)),
        )

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def _simulate_weather(self) -> WeatherData:
        """
        Generate plausible weather data based on month and time of day.

        Temperature follows a sinusoidal diurnal cycle bounded by monthly
        normals (min at ~05:00, max at ~15:00). Humidity is anti-correlated
        with temperature. Wind speed and direction evolve via a smooth
        random walk to avoid discontinuities.
        """
        now = datetime.now(timezone.utc)
        month = now.month
        hour = now.hour + now.minute / 60.0

        # --- Temperature ---
        temp_lo, temp_hi = _MONTHLY_TEMP_RANGES.get(month, (10.0, 20.0))
        temp_range = temp_hi - temp_lo
        # Sinusoidal daily pattern: minimum at ~05:00, maximum at ~15:00
        daily_phase = math.sin(math.pi * (hour - 5.0) / 12.0)
        temperature = temp_lo + temp_range * max(0.0, min(1.0, (daily_phase + 1.0) / 2.0))
        temperature += random.gauss(0, 1.0)

        # --- Humidity (inversely correlated with temperature) ---
        base_humidity = 60.0 - (temperature - 15.0) * 0.8
        humidity = max(25.0, min(95.0, base_humidity + random.gauss(0, 5.0)))

        # --- Wind speed: smooth random walk ---
        self._sim_wind_speed += random.gauss(0, 0.3)
        self._sim_wind_speed = max(0.5, min(15.0, self._sim_wind_speed))

        # Add a slight diurnal modulation (stronger midday winds)
        diurnal_wind = 0.5 * math.sin(math.pi * (hour - 6.0) / 12.0)
        effective_wind = max(0.5, self._sim_wind_speed + diurnal_wind)

        # --- Wind direction: slow drift ---
        self._sim_wind_dir += random.gauss(0, 5.0)
        self._sim_wind_dir = self._sim_wind_dir % 360.0

        return WeatherData(
            wind_speed=round(effective_wind, 1),
            wind_direction=round(self._sim_wind_dir, 1),
            temperature=round(temperature, 1),
            humidity=round(humidity, 1),
        )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return service status information."""
        return {
            "service": "WeatherService",
            "api_key_set": bool(self._api_key),
            "cache_valid": self._is_cache_valid(),
            "cache_ttl_seconds": self._cache_ttl_seconds,
            "sim_wind_speed": self._sim_wind_speed,
            "sim_wind_dir": self._sim_wind_dir,
        }
