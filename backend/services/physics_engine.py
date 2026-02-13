"""
Eco-Lens Physics Engine
========================
Gaussian Plume Dispersion Model for estimating pollutant concentrations
from vehicle emission sources.

Implements the full Gaussian plume equation:

    C(x,y,z) = Q / (2*pi*u*sigma_y*sigma_z)
                * exp(-y^2 / (2*sigma_y^2))
                * [exp(-(z-H)^2 / (2*sigma_z^2)) + exp(-(z+H)^2 / (2*sigma_z^2))]

Where:
    Q       = emission rate (g/s) from EPA AP-42 emission factors
    u       = wind speed (m/s)
    sigma_y = lateral dispersion coefficient (Pasquill-Gifford)
    sigma_z = vertical dispersion coefficient (Pasquill-Gifford)
    H       = effective stack height (vehicle exhaust ~0.3-0.5m)
    x       = downwind distance (m)
    y       = crosswind distance (m)
    z       = receptor height (1.5m breathing zone)

EPA emission factors derived from AP-42 Chapter 13.2.1 (Unpaved Roads)
and MOVES model for on-road vehicles, converted to g/vehicle/s at
typical urban speeds (~25 km/h with stop-and-go).

Pasquill-Gifford stability classes (A through F) are determined from
wind speed and solar radiation proxy (time of day).

References:
    - Turner, D.B. (1994) Workbook of Atmospheric Dispersion Estimates
    - EPA AP-42, Fifth Edition, Volume I
    - Pasquill, F. (1961) The Estimation of the Dispersion of Windborne Material
"""

import math
import random
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional

from models import VehicleCounts, PollutionData, WeatherData, ParticleData, GridData

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# EPA-derived emission factors (grams per vehicle per second)
# Approximated from EPA AP-42 and MOVES for urban stop-and-go (~25 km/h)
# ---------------------------------------------------------------------------
_EMISSION_FACTORS: Dict[str, Dict[str, float]] = {
    "trucks":      {"pm25": 0.070, "pm10": 0.120, "no2": 2.50, "co": 1.80},
    "cars":        {"pm25": 0.005, "pm10": 0.010, "no2": 0.15, "co": 1.20},
    "buses":       {"pm25": 0.055, "pm10": 0.095, "no2": 2.10, "co": 1.50},
    "motorcycles": {"pm25": 0.008, "pm10": 0.015, "no2": 0.10, "co": 2.50},
}

# ---------------------------------------------------------------------------
# Pasquill-Gifford stability class parameters
# sigma_y(x) = coeff * x^exp  (x in km, result in km, then convert to m)
# sigma_z(x) = coeff * x^exp  (same units)
# From Turner (1994) curve-fit approximations
# ---------------------------------------------------------------------------
_STABILITY_PARAMS: Dict[str, Dict[str, float]] = {
    "A": {"sy_c": 0.22,  "sy_e": 0.94, "sz_c": 0.20,  "sz_e": 0.94},
    "B": {"sy_c": 0.16,  "sy_e": 0.92, "sz_c": 0.12,  "sz_e": 0.92},
    "C": {"sy_c": 0.11,  "sy_e": 0.91, "sz_c": 0.08,  "sz_e": 0.85},
    "D": {"sy_c": 0.08,  "sy_e": 0.89, "sz_c": 0.06,  "sz_e": 0.82},
    "E": {"sy_c": 0.06,  "sy_e": 0.86, "sz_c": 0.03,  "sz_e": 0.78},
    "F": {"sy_c": 0.04,  "sy_e": 0.83, "sz_c": 0.016, "sz_e": 0.72},
}

# ---------------------------------------------------------------------------
# EPA AQI breakpoints for PM2.5 (24-hour, ug/m3)
# ---------------------------------------------------------------------------
_AQI_BREAKPOINTS: List[Tuple[float, float, int, int, str]] = [
    (0.0,   12.0,   0,   50, "Good"),
    (12.1,  35.4,  51,  100, "Moderate"),
    (35.5,  55.4, 101,  150, "Unhealthy for Sensitive Groups"),
    (55.5, 150.4, 151,  200, "Unhealthy"),
    (150.5, 250.4, 201, 300, "Very Unhealthy"),
    (250.5, 500.4, 301, 500, "Hazardous"),
]


class PhysicsEngine:
    """
    Computes pollutant concentrations using EPA emission factors and the
    Gaussian plume atmospheric dispersion model with Pasquill-Gifford
    stability classes.
    """

    # Default receptor parameters
    _RECEPTOR_HEIGHT = 1.5      # meters (breathing zone)
    _SOURCE_HEIGHT = 0.5        # meters (vehicle tailpipe)
    _RECEPTOR_DOWNWIND = 50.0   # meters (representative distance from road)

    def __init__(self) -> None:
        self._stability_class = "D"

    # ==================================================================
    # Stability classification
    # ==================================================================

    def _get_stability_class(self, wind_speed: float, hour: int) -> str:
        """
        Estimate Pasquill-Gifford stability class from wind speed and
        approximate solar radiation (using hour as a proxy).

        Daytime (strong insolation):
            u < 2 -> A (extremely unstable)
            2 <= u < 3 -> B (moderately unstable)
            3 <= u < 5 -> C (slightly unstable)
            u >= 5 -> D (neutral)

        Nighttime (clear sky):
            u < 3 -> F (moderately stable)
            3 <= u < 5 -> E (slightly stable)
            u >= 5 -> D (neutral)
        """
        is_daytime = 7 <= hour <= 18
        if is_daytime:
            if wind_speed < 2.0:
                return "A"
            elif wind_speed < 3.0:
                return "B"
            elif wind_speed < 5.0:
                return "C"
            else:
                return "D"
        else:
            if wind_speed < 3.0:
                return "F"
            elif wind_speed < 5.0:
                return "E"
            else:
                return "D"

    # ==================================================================
    # Core Gaussian plume equation
    # ==================================================================

    def _gaussian_plume(
        self,
        Q: float,
        u: float,
        x: float,
        y: float,
        z: float,
        H: float,
        stability: str,
    ) -> float:
        """
        Compute concentration (ug/m3) at point (x, y, z) using the
        Gaussian plume equation with ground reflection.

        Parameters
        ----------
        Q : float
            Emission rate (g/s).
        u : float
            Wind speed (m/s).
        x : float
            Downwind distance (m). Must be > 0.
        y : float
            Crosswind distance (m).
        z : float
            Receptor height above ground (m).
        H : float
            Effective source height (m).
        stability : str
            Pasquill-Gifford stability class (A-F).

        Returns
        -------
        float
            Concentration in micrograms per cubic meter (ug/m3).
        """
        if x <= 0 or u < 0.3:
            # Calm/stagnant conditions: use simple box model fallback
            mixing_height = 100.0  # meters
            box_area = 200.0 * 200.0  # m^2
            return (Q * 1e6) / (box_area * mixing_height) * 0.5

        params = _STABILITY_PARAMS.get(stability, _STABILITY_PARAMS["D"])

        # Dispersion coefficients: sigma(x) in meters
        x_km = x / 1000.0
        sigma_y = params["sy_c"] * (x_km ** params["sy_e"]) * 1000.0
        sigma_z = params["sz_c"] * (x_km ** params["sz_e"]) * 1000.0

        # Clamp to prevent division by zero
        sigma_y = max(sigma_y, 1.0)
        sigma_z = max(sigma_z, 1.0)
        u = max(u, 0.5)

        # Gaussian plume equation with ground reflection term
        coeff = Q / (2.0 * math.pi * u * sigma_y * sigma_z)
        lateral = math.exp(-0.5 * (y / sigma_y) ** 2)
        vertical = (
            math.exp(-0.5 * ((z - H) / sigma_z) ** 2)
            + math.exp(-0.5 * ((z + H) / sigma_z) ** 2)
        )

        # g/m3 -> ug/m3
        concentration_ug_m3 = coeff * lateral * vertical * 1e6
        return concentration_ug_m3

    # ==================================================================
    # Emission rate calculation
    # ==================================================================

    def calculate_emission_rate(self, vehicle_counts: VehicleCounts) -> Dict[str, float]:
        """
        Calculate total emission rate Q (g/s) for each pollutant from
        vehicle counts using EPA emission factors.

        Parameters
        ----------
        vehicle_counts : VehicleCounts
            Current vehicle counts by type.

        Returns
        -------
        dict
            Emission rates in g/s keyed by pollutant name.
        """
        rates: Dict[str, float] = {"pm25": 0.0, "pm10": 0.0, "no2": 0.0, "co": 0.0}

        vehicle_map = {
            "trucks": vehicle_counts.trucks,
            "cars": vehicle_counts.cars,
            "buses": vehicle_counts.buses,
            "motorcycles": vehicle_counts.motorcycles,
        }

        for vtype, count in vehicle_map.items():
            factors = _EMISSION_FACTORS[vtype]
            for pollutant, factor_gs in factors.items():
                rates[pollutant] += count * factor_gs

        return rates

    # ==================================================================
    # Dispersion calculation
    # ==================================================================

    def calculate_dispersion(
        self,
        Q: Dict[str, float],
        wind_speed: float,
        wind_direction: float,
        distance: float = 100.0,
        hour: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Calculate pollutant concentrations at a receptor point downwind.

        Parameters
        ----------
        Q : dict
            Emission rates in g/s for each pollutant.
        wind_speed : float
            Wind speed in m/s.
        wind_direction : float
            Wind direction in degrees (meteorological convention).
        distance : float
            Downwind distance to receptor (m).
        hour : int, optional
            Hour of day for stability class determination.

        Returns
        -------
        dict
            Concentrations in ug/m3 for each pollutant.
        """
        if hour is None:
            hour = datetime.now(timezone.utc).hour

        stability = self._get_stability_class(wind_speed, hour)
        self._stability_class = stability

        concentrations: Dict[str, float] = {}
        for pollutant, q_val in Q.items():
            c = self._gaussian_plume(
                Q=q_val,
                u=wind_speed,
                x=distance,
                y=0.0,  # directly downwind
                z=self._RECEPTOR_HEIGHT,
                H=self._SOURCE_HEIGHT,
                stability=stability,
            )
            concentrations[pollutant] = c

        return concentrations

    # ==================================================================
    # Full pollution calculation (vehicles + weather -> pollution)
    # ==================================================================

    def calculate_pollution(
        self,
        vehicles: VehicleCounts,
        weather: WeatherData,
        hour: Optional[int] = None,
    ) -> PollutionData:
        """
        Convert vehicle counts and weather into pollution concentrations.

        Uses the Gaussian plume model at a representative receptor point
        50m downwind of the road. Adds ambient background concentrations
        and applies temperature/humidity corrections.

        Parameters
        ----------
        vehicles : VehicleCounts
            Current vehicle counts by type.
        weather : WeatherData
            Current weather conditions.
        hour : int, optional
            Hour of day (UTC). Auto-detected if not provided.

        Returns
        -------
        PollutionData
            Pydantic model with pm25, pm10, no2, co, aqi, category.
        """
        if hour is None:
            hour = datetime.now(timezone.utc).hour

        stability = self._get_stability_class(weather.wind_speed, hour)
        self._stability_class = stability

        emission_rates = self.calculate_emission_rate(vehicles)

        # Representative receptor: 50m downwind, 0m crosswind, 1.5m height
        downwind = self._RECEPTOR_DOWNWIND
        crosswind = 0.0

        pm25 = self._gaussian_plume(
            emission_rates["pm25"], weather.wind_speed, downwind, crosswind,
            self._RECEPTOR_HEIGHT, self._SOURCE_HEIGHT, stability,
        )
        pm10 = self._gaussian_plume(
            emission_rates["pm10"], weather.wind_speed, downwind, crosswind,
            self._RECEPTOR_HEIGHT, self._SOURCE_HEIGHT, stability,
        )
        no2 = self._gaussian_plume(
            emission_rates["no2"], weather.wind_speed, downwind, crosswind,
            self._RECEPTOR_HEIGHT, self._SOURCE_HEIGHT, stability,
        )
        co = self._gaussian_plume(
            emission_rates["co"], weather.wind_speed, downwind, crosswind,
            self._RECEPTOR_HEIGHT, self._SOURCE_HEIGHT, stability,
        )

        # Add ambient background levels (ug/m3) - typical urban background
        pm25 += 5.0 + random.gauss(0, 0.5)
        pm10 += 12.0 + random.gauss(0, 1.0)
        no2 += 15.0 + random.gauss(0, 1.5)
        co += 200.0 + random.gauss(0, 20.0)

        # Temperature correction: higher temps increase photochemical NO2
        temp_factor = 1.0 + max(0, (weather.temperature - 20.0)) * 0.01
        no2 *= temp_factor

        # Humidity correction: higher humidity increases particulate formation
        humidity_factor = 1.0 + max(0, (weather.humidity - 60.0)) * 0.005
        pm25 *= humidity_factor
        pm10 *= humidity_factor

        # Clamp to physically realistic ranges
        pm25 = max(1.0, round(pm25, 1))
        pm10 = max(2.0, round(pm10, 1))
        no2 = max(2.0, round(no2, 1))
        co = max(50.0, round(co, 1))

        aqi = self.pm25_to_aqi(pm25)
        category = self.get_aqi_category(aqi)

        return PollutionData(
            pm25=pm25,
            pm10=pm10,
            no2=no2,
            co=co,
            aqi=aqi,
            category=category,
        )

    # ==================================================================
    # Concentration grid (for heatmap visualization)
    # ==================================================================

    def calculate_concentration_grid(
        self,
        sensors: List[dict],
        grid_bounds: Dict[str, float],
        resolution: int = 20,
    ) -> GridData:
        """
        Calculate a 2D grid of PM2.5 concentrations for heatmap display.

        For each grid cell, sums contributions from all sensor/source
        locations using the Gaussian plume model, accounting for wind
        direction to determine downwind vs upwind geometry.

        Parameters
        ----------
        sensors : list of dict
            Each dict must have: lat, lng, emission_rate (g/s for PM2.5),
            wind_speed, wind_direction.
        grid_bounds : dict
            Keys: north, south, east, west (lat/lng bounds).
        resolution : int
            Number of grid cells per dimension.

        Returns
        -------
        GridData
            Pydantic model with bounds, resolution, and 2D values array.
        """
        north = grid_bounds["north"]
        south = grid_bounds["south"]
        east = grid_bounds["east"]
        west = grid_bounds["west"]

        lat_step = (north - south) / resolution
        lng_step = (east - west) / resolution

        grid: List[List[float]] = []
        hour = datetime.now(timezone.utc).hour

        for row in range(resolution):
            grid_row: List[float] = []
            cell_lat = north - (row + 0.5) * lat_step

            for col in range(resolution):
                cell_lng = west + (col + 0.5) * lng_step

                total_concentration = 0.0

                for sensor in sensors:
                    s_lat = sensor["lat"]
                    s_lng = sensor["lng"]
                    q_pm25 = sensor.get("emission_rate", 0.01)
                    ws = sensor.get("wind_speed", 3.0)
                    wd = sensor.get("wind_direction", 180.0)

                    stability = self._get_stability_class(ws, hour)

                    # Convert lat/lng difference to meters
                    dlat = cell_lat - s_lat
                    dlng = cell_lng - s_lng
                    dy_m = dlat * 111320.0  # meters per degree latitude
                    dx_m = dlng * 111320.0 * math.cos(math.radians(s_lat))

                    # Rotate into wind coordinate system
                    # Wind direction is where wind comes FROM (meteorological)
                    wind_rad = math.radians(wd)
                    # Downwind (x) = distance in direction wind is blowing TO
                    x_wind = dx_m * math.sin(wind_rad) + dy_m * math.cos(wind_rad)
                    y_wind = dx_m * math.cos(wind_rad) - dy_m * math.sin(wind_rad)

                    # Only compute for downwind points (plume doesn't go upwind)
                    if x_wind > 1.0:
                        c = self._gaussian_plume(
                            Q=q_pm25, u=ws, x=x_wind, y=y_wind,
                            z=self._RECEPTOR_HEIGHT, H=self._SOURCE_HEIGHT,
                            stability=stability,
                        )
                        total_concentration += c

                # Add ambient background
                total_concentration += 5.0

                grid_row.append(round(total_concentration, 2))

            grid.append(grid_row)

        return GridData(
            bounds=grid_bounds,
            resolution=resolution,
            values=grid,
        )

    # ==================================================================
    # AQI calculation
    # ==================================================================

    @staticmethod
    def pm25_to_aqi(pm25: float) -> int:
        """
        Convert PM2.5 concentration (ug/m3) to US EPA Air Quality Index.

        Uses the standard piecewise linear interpolation between EPA
        breakpoints (40 CFR Part 58, Appendix G).

        Parameters
        ----------
        pm25 : float
            PM2.5 concentration in micrograms per cubic meter.

        Returns
        -------
        int
            AQI value (0-500).
        """
        pm25 = max(0.0, pm25)
        for bp_lo, bp_hi, aqi_lo, aqi_hi, _ in _AQI_BREAKPOINTS:
            if pm25 <= bp_hi:
                aqi = ((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (pm25 - bp_lo) + aqi_lo
                return round(aqi)
        return 500

    @staticmethod
    def get_aqi_category(aqi: int) -> str:
        """
        Get the EPA health concern category for a given AQI value.

        Parameters
        ----------
        aqi : int
            Air Quality Index value.

        Returns
        -------
        str
            Health concern category label.
        """
        if aqi <= 50:
            return "Good"
        elif aqi <= 100:
            return "Moderate"
        elif aqi <= 150:
            return "Unhealthy for Sensitive Groups"
        elif aqi <= 200:
            return "Unhealthy"
        elif aqi <= 300:
            return "Very Unhealthy"
        else:
            return "Hazardous"

    # ==================================================================
    # Particle visualization
    # ==================================================================

    def generate_particles(
        self,
        sensor_id: str,
        lat: float,
        lng: float,
        pollution: PollutionData,
        weather: WeatherData,
        count: int = 15,
    ) -> List[ParticleData]:
        """
        Generate visualization particles representing pollutant dispersion
        from a sensor location. Particles drift with the wind and include
        turbulent diffusion.

        Parameters
        ----------
        sensor_id : str
            Source sensor identifier.
        lat, lng : float
            Sensor coordinates.
        pollution : PollutionData
            Current pollution levels at this sensor.
        weather : WeatherData
            Current weather conditions.
        count : int
            Number of particles to generate.

        Returns
        -------
        list of ParticleData
        """
        particles: List[ParticleData] = []

        # Wind vector in coordinate-space units
        wind_rad = math.radians(weather.wind_direction)
        wind_vx = weather.wind_speed * math.sin(wind_rad) * 0.00001
        wind_vy = weather.wind_speed * math.cos(wind_rad) * 0.00001

        # Concentration factor for particle opacity
        concentration_factor = min(pollution.pm25 / 50.0, 1.0)

        for _ in range(count):
            # Random offset from sensor center
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0.0001, 0.003)
            dx = radius * math.cos(angle)
            dy = radius * math.sin(angle)

            # Turbulent diffusion component
            turbulence_x = random.gauss(0, 0.000005)
            turbulence_y = random.gauss(0, 0.000005)

            particles.append(
                ParticleData(
                    x=lng + dx,
                    y=lat + dy,
                    vx=wind_vx + turbulence_x,
                    vy=wind_vy + turbulence_y,
                    concentration=concentration_factor * random.uniform(0.3, 1.0),
                    age=random.uniform(0, 10),
                    source_id=sensor_id,
                )
            )

        return particles

    # ==================================================================
    # Diagnostics
    # ==================================================================

    def get_status(self) -> dict:
        """Return engine status information."""
        return {
            "service": "PhysicsEngine",
            "current_stability_class": self._stability_class,
            "emission_factors": _EMISSION_FACTORS,
            "receptor_height_m": self._RECEPTOR_HEIGHT,
            "source_height_m": self._SOURCE_HEIGHT,
        }
