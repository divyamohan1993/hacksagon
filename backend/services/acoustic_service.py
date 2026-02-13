"""
Eco-Lens Acoustic Service
===========================
Traffic noise estimation using the FHWA Traffic Noise Model (TNM)
methodology.

Calculates equivalent continuous sound level (Leq) from traffic
composition, speed, and receptor distance using reference emission
levels and logarithmic energy summation.

Individual vehicle noise at receptor:
    L = L_ref + 10*log10(v/v_ref) - 10*log10(d/d_ref) - alpha_air*(d/1000)

Traffic flow Leq (N vehicles of same type):
    L_fleet = L_single + 10*log10(N)

Mixed traffic total:
    L_total = 10 * log10( sum(10^(L_i/10)) )

Reference Sound Emission Levels (FHWA TNM):
    Heavy Truck:   84 dB(A) at 50 km/h, 15m
    Car/Sedan:     67 dB(A) at 50 km/h, 15m
    Bus:           81 dB(A) at 40 km/h, 15m
    Motorcycle:    78 dB(A) at 50 km/h, 15m

Noise propagation includes:
    - Geometric spreading (line-source attenuation)
    - Atmospheric absorption (~5 dB/km at 1 kHz, 20C, 50% RH)
    - Ground effect (mixed surface absorption)

References:
    - FHWA Traffic Noise Model Technical Manual (FHWA-PD-96-010)
    - ISO 9613-2: Attenuation of sound during propagation outdoors
    - WHO Environmental Noise Guidelines for the European Region (2018)
"""

import math
import random
import logging
from typing import Dict, List

from models import VehicleCounts, NoiseData, GridData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Reference emission levels
# ---------------------------------------------------------------------------
_NOISE_REF: Dict[str, Dict[str, float]] = {
    "trucks": {
        "L_ref": 84.0,    # dB(A) at reference conditions
        "v_ref": 50.0,     # km/h reference speed
        "d_ref": 15.0,     # meters reference distance
    },
    "cars": {
        "L_ref": 67.0,
        "v_ref": 50.0,
        "d_ref": 15.0,
    },
    "buses": {
        "L_ref": 81.0,
        "v_ref": 40.0,
        "d_ref": 15.0,
    },
    "motorcycles": {
        "L_ref": 78.0,
        "v_ref": 50.0,
        "d_ref": 15.0,
    },
}

# Atmospheric absorption coefficient (dB/km at ~1 kHz, 20C, 50% RH)
_ATMOS_ABSORPTION = 5.0

# Ground absorption factor (0 = hard surface, 1 = soft ground)
_GROUND_FACTOR = 0.5

# ---------------------------------------------------------------------------
# Noise categories based on WHO Environmental Noise Guidelines (2018)
# ---------------------------------------------------------------------------
_NOISE_CATEGORIES = [
    (0.0,  45.0,  "Quiet"),
    (45.0, 55.0,  "Moderate"),
    (55.0, 65.0,  "Loud"),
    (65.0, 75.0,  "Very Loud"),
    (75.0, 999.0, "Extreme"),
]


def _db_add(*levels: float) -> float:
    """
    Add decibel levels using energy summation:
        L_total = 10 * log10( sum(10^(L_i/10)) )

    This is the physically correct way to combine independent sound
    sources (incoherent addition).
    """
    total_energy = sum(10.0 ** (lev / 10.0) for lev in levels if lev > 0)
    if total_energy <= 0:
        return 0.0
    return 10.0 * math.log10(total_energy)


class AcousticService:
    """
    Estimates environmental noise from traffic composition using the
    FHWA Traffic Noise Model methodology.
    """

    def __init__(self) -> None:
        pass

    # ==================================================================
    # Single vehicle noise
    # ==================================================================

    @staticmethod
    def _single_vehicle_level(
        vehicle_type: str,
        speed_kmh: float = 50.0,
        distance_m: float = 15.0,
    ) -> float:
        """
        Compute the A-weighted sound pressure level from one vehicle
        at a given speed and distance.

        Uses FHWA TNM formula:
            L = L_ref + 10*log10(v/v_ref) - 10*log10(d/d_ref)
                - alpha_atmos * (d/1000) - ground_effect

        For a line source (road), geometric attenuation is 10*log10
        (halving ~3 dB per doubling of distance) rather than 20*log10
        for a point source.

        Parameters
        ----------
        vehicle_type : str
            One of: trucks, cars, buses, motorcycles.
        speed_kmh : float
            Vehicle speed in km/h.
        distance_m : float
            Distance to receptor in meters.

        Returns
        -------
        float
            Sound pressure level in dB(A).
        """
        ref = _NOISE_REF.get(vehicle_type, _NOISE_REF["cars"])
        speed = max(speed_kmh, 5.0)
        dist = max(distance_m, 1.0)

        # Speed correction
        speed_correction = 10.0 * math.log10(speed / ref["v_ref"])

        # Distance attenuation (line source: 10*log10)
        distance_attenuation = 10.0 * math.log10(dist / ref["d_ref"])

        # Atmospheric absorption
        atmos = _ATMOS_ABSORPTION * (dist / 1000.0)

        # Ground effect
        ground_effect = _GROUND_FACTOR * max(0, 3.0 * math.log10(dist / ref["d_ref"]))

        level = (
            ref["L_ref"]
            + speed_correction
            - distance_attenuation
            - atmos
            - ground_effect
        )

        return level

    # ==================================================================
    # Fleet noise
    # ==================================================================

    @staticmethod
    def _fleet_noise_level(single_db: float, count: int) -> float:
        """
        Compute combined noise from N identical incoherent sources.
            L_N = L_single + 10 * log10(N)
        """
        if count <= 0:
            return 0.0
        return single_db + 10.0 * math.log10(count)

    # ==================================================================
    # Public API: estimate noise from vehicle counts
    # ==================================================================

    def estimate_noise(
        self,
        vehicles: VehicleCounts,
        avg_speed: float = 40.0,
        distance: float = 15.0,
    ) -> NoiseData:
        """
        Estimate the equivalent continuous noise level (Leq) at a receptor
        point from the current traffic composition.

        Parameters
        ----------
        vehicles : VehicleCounts
            Current vehicle counts by type.
        avg_speed : float
            Average traffic speed in km/h (default 40 for urban).
        distance : float
            Distance from road centerline to receptor in meters.

        Returns
        -------
        NoiseData
            Pydantic model with db_level and category.
        """
        vehicle_types = {
            "trucks": vehicles.trucks,
            "cars": vehicles.cars,
            "buses": vehicles.buses,
            "motorcycles": vehicles.motorcycles,
        }

        fleet_levels = []
        for vtype, count in vehicle_types.items():
            if count <= 0:
                continue
            single_db = self._single_vehicle_level(vtype, avg_speed, distance)
            fleet_db = self._fleet_noise_level(single_db, count)
            fleet_levels.append(fleet_db)

        if fleet_levels:
            combined_db = _db_add(*fleet_levels)
        else:
            combined_db = 35.0  # quiet background

        # Add urban ambient background noise floor (~45 dB)
        ambient = 45.0
        total_db = _db_add(combined_db, ambient)

        # Small Gaussian perturbation for realism
        total_db += random.gauss(0, 1.0)
        total_db = max(30.0, round(total_db, 1))

        category = self._categorize_noise(total_db)

        return NoiseData(db_level=total_db, category=category)

    # ==================================================================
    # Noise category classification
    # ==================================================================

    @staticmethod
    def _categorize_noise(db_level: float) -> str:
        """Map dB(A) level to a WHO-based noise category."""
        for low, high, label in _NOISE_CATEGORIES:
            if db_level < high:
                return label
        return "Extreme"

    # ==================================================================
    # Noise grid (for heatmap visualization)
    # ==================================================================

    def calculate_noise_grid(
        self,
        sensors: List[dict],
        grid_bounds: Dict[str, float],
        resolution: int = 20,
    ) -> GridData:
        """
        Calculate a 2D grid of noise levels for heatmap display.

        For each grid cell, computes the logarithmic sum of noise
        contributions from all sensor/source locations with distance
        attenuation.

        Parameters
        ----------
        sensors : list of dict
            Each dict must have: lat, lng, db_level (source noise at road).
        grid_bounds : dict
            Keys: north, south, east, west.
        resolution : int
            Grid cells per dimension.

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

        for row in range(resolution):
            grid_row: List[float] = []
            cell_lat = north - (row + 0.5) * lat_step

            for col in range(resolution):
                cell_lng = west + (col + 0.5) * lng_step

                energy_sum = 0.0

                for sensor in sensors:
                    s_lat = sensor["lat"]
                    s_lng = sensor["lng"]
                    source_db = sensor.get("db_level", 65.0)

                    # Distance in meters (flat-earth approximation for short distances)
                    dlat_m = (cell_lat - s_lat) * 111320.0
                    dlng_m = (cell_lng - s_lng) * 111320.0 * math.cos(math.radians(s_lat))
                    dist = math.sqrt(dlat_m ** 2 + dlng_m ** 2)
                    dist = max(dist, 1.0)

                    # Distance attenuation from source (reference at 15m)
                    if dist <= 15.0:
                        atten = 0.0
                    else:
                        atten = 15.0 * math.log10(dist / 15.0)

                    # Atmospheric absorption
                    atmos = _ATMOS_ABSORPTION * (dist / 1000.0)

                    received_db = source_db - atten - atmos
                    if received_db > 0:
                        energy_sum += 10.0 ** (received_db / 10.0)

                # Add ambient background (35 dB)
                energy_sum += 10.0 ** (35.0 / 10.0)

                if energy_sum > 0:
                    total_db = 10.0 * math.log10(energy_sum)
                else:
                    total_db = 35.0

                grid_row.append(round(total_db, 1))

            grid.append(grid_row)

        return GridData(
            bounds=grid_bounds,
            resolution=resolution,
            values=grid,
        )

    # ==================================================================
    # Diagnostics
    # ==================================================================

    def get_status(self) -> dict:
        """Return service status information."""
        return {
            "service": "AcousticService",
            "model": "FHWA Traffic Noise Model",
            "reference_levels": {k: v["L_ref"] for k, v in _NOISE_REF.items()},
            "atmospheric_absorption_db_km": _ATMOS_ABSORPTION,
            "ground_factor": _GROUND_FACTOR,
        }
