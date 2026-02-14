"""
Eco-Lens Vision Service
========================
Vehicle detection and classification using YOLOv8 with intelligent
simulation fallback for demo/offline mode.

When a camera feed is available, runs YOLOv8-nano for real-time vehicle
detection and classification (car, truck, bus, motorcycle). When no camera
or model is available, generates statistically realistic traffic patterns
modulated by time-of-day, day-of-week, and location-specific characteristics.

Uses a bimodal Gaussian traffic profile with smoothing to prevent jarring
jumps between successive readings.
"""

import math
import random
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from models import VehicleCounts

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Location-specific traffic profiles (Delhi, India)
# ---------------------------------------------------------------------------
_LOCATION_PROFILES: Dict[str, Dict[str, float]] = {
    "cam-001": {  # India Gate - tourist & govt traffic
        "car_base": 40,
        "truck_base": 5,
        "bus_base": 8,
        "moto_base": 15,
        "rush_multiplier": 1.5,
        "weekend_factor": 1.3,
    },
    "cam-002": {  # Connaught Place - commercial hub
        "car_base": 45,
        "truck_base": 6,
        "bus_base": 7,
        "moto_base": 12,
        "rush_multiplier": 1.8,
        "weekend_factor": 0.9,
    },
    "cam-003": {  # ITO Junction - major intersection
        "car_base": 50,
        "truck_base": 10,
        "bus_base": 10,
        "moto_base": 18,
        "rush_multiplier": 2.2,
        "weekend_factor": 0.6,
    },
    "cam-004": {  # Anand Vihar - industrial/transport hub
        "car_base": 35,
        "truck_base": 15,
        "bus_base": 12,
        "moto_base": 10,
        "rush_multiplier": 1.9,
        "weekend_factor": 0.5,
    },
    "cam-005": {  # Dwarka Sec-8 - suburban residential
        "car_base": 30,
        "truck_base": 4,
        "bus_base": 5,
        "moto_base": 8,
        "rush_multiplier": 1.6,
        "weekend_factor": 0.7,
    },
    "cam-006": {  # Chandni Chowk - old Delhi congestion
        "car_base": 20,
        "truck_base": 8,
        "bus_base": 6,
        "moto_base": 25,
        "rush_multiplier": 1.4,
        "weekend_factor": 1.1,
    },
}

_DEFAULT_PROFILE: Dict[str, float] = {
    "car_base": 30,
    "truck_base": 5,
    "bus_base": 4,
    "moto_base": 3,
    "rush_multiplier": 1.5,
    "weekend_factor": 0.7,
}


class VisionService:
    """
    Vehicle detection and classification service.

    Supports two modes:
      1. **YOLO mode** - Runs YOLOv8-nano on real camera frames for
         object detection.  Requires `ultralytics` and a `.pt` weight file.
      2. **Simulation mode** - Generates realistic traffic counts using
         time-of-day Gaussian profiles, day-of-week adjustments,
         location-specific base rates, and exponential smoothing to
         prevent abrupt changes between successive readings.
    """

    # COCO dataset class IDs for vehicles
    _COCO_CAR = 2
    _COCO_MOTORCYCLE = 3
    _COCO_BUS = 5
    _COCO_TRUCK = 7

    def __init__(self) -> None:
        self.model = None
        self.simulation_mode = True
        self._previous_counts: Dict[str, VehicleCounts] = {}
        self._try_load_model()

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _try_load_model(self) -> None:
        """Attempt to load YOLOv8-nano; silently fall back to simulation."""
        try:
            from ultralytics import YOLO
            self.model = YOLO("yolov8n.pt")
            self.simulation_mode = False
            logger.info("YOLOv8 model loaded successfully")
        except ImportError:
            logger.info("ultralytics not installed - using simulation mode")
            self.simulation_mode = True
        except Exception as exc:
            logger.warning("Failed to load YOLO model: %s - using simulation", exc)
            self.simulation_mode = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_vehicles(
        self, camera_id: str, frame: Optional[bytes] = None
    ) -> VehicleCounts:
        """
        Detect and classify vehicles for a given camera.

        Parameters
        ----------
        camera_id : str
            Camera/sensor identifier (e.g. ``"cam-001"``).
        frame : bytes or numpy.ndarray, optional
            Raw image data.  If provided *and* YOLO is loaded, runs
            real inference.  Otherwise falls back to simulation.

        Returns
        -------
        VehicleCounts
            Pydantic model with trucks, cars, buses, motorcycles, total.
        """
        if not self.simulation_mode and frame is not None:
            counts = self._run_yolo(frame)
        else:
            counts = self._simulate_traffic(camera_id)

        # Smooth with previous reading to avoid jarring jumps
        counts = self._smooth(camera_id, counts)
        self._previous_counts[camera_id] = counts
        return counts

    # ------------------------------------------------------------------
    # YOLO inference
    # ------------------------------------------------------------------

    def _run_yolo(self, frame) -> VehicleCounts:
        """Run YOLOv8 inference on a single frame."""
        results = self.model(frame, verbose=False)
        detections = results[0].boxes.cls.tolist()

        trucks = int(detections.count(self._COCO_TRUCK))
        cars = int(detections.count(self._COCO_CAR))
        buses = int(detections.count(self._COCO_BUS))
        motorcycles = int(detections.count(self._COCO_MOTORCYCLE))
        total = trucks + cars + buses + motorcycles

        return VehicleCounts(
            trucks=trucks,
            cars=cars,
            buses=buses,
            motorcycles=motorcycles,
            total=total,
        )

    # ------------------------------------------------------------------
    # Simulation engine
    # ------------------------------------------------------------------

    def _time_of_day_factor(self, hour: float) -> float:
        """
        Bimodal Gaussian traffic profile.

        Morning peak ~ 08:30, evening peak ~ 17:30, with a midday
        plateau and overnight trough.
        """
        morning = 0.8 * math.exp(-0.5 * ((hour - 8.5) / 1.5) ** 2)
        evening = 1.0 * math.exp(-0.5 * ((hour - 17.5) / 1.8) ** 2)
        midday = 0.5 * math.exp(-0.5 * ((hour - 13.0) / 3.0) ** 2)
        base = 0.15  # overnight floor
        return base + morning + evening + midday

    def _weekend_adjustment(
        self, day_of_week: int, profile: Dict[str, float]
    ) -> float:
        """Return a scalar multiplier for weekend days."""
        if day_of_week >= 5:  # Saturday=5, Sunday=6
            return profile.get("weekend_factor", 0.7)
        return 1.0

    def _simulate_traffic(self, camera_id: str) -> VehicleCounts:
        """
        Generate statistically realistic vehicle counts.

        Combines:
        - Time-of-day Gaussian profile
        - Day-of-week scaling
        - Rush-hour boost from location profile
        - Gaussian noise (~15% CV)
        """
        now = datetime.now(timezone.utc)
        hour = now.hour + now.minute / 60.0
        day_of_week = now.weekday()

        profile = _LOCATION_PROFILES.get(camera_id, _DEFAULT_PROFILE)

        tod_factor = self._time_of_day_factor(hour)
        weekend_adj = self._weekend_adjustment(day_of_week, profile)

        # Rush-hour boost
        is_rush = (7.0 <= hour <= 9.5) or (16.5 <= hour <= 19.0)
        rush_factor = profile["rush_multiplier"] if is_rush else 1.0

        combined = tod_factor * weekend_adj * rush_factor

        def _noisy_count(base: float) -> int:
            raw = base * combined
            noisy = raw + random.gauss(0, max(1.0, raw * 0.15))
            return max(0, round(noisy))

        cars = _noisy_count(profile["car_base"])
        trucks = _noisy_count(profile["truck_base"])
        buses = _noisy_count(profile["bus_base"])
        motorcycles = _noisy_count(profile["moto_base"])

        return VehicleCounts(
            trucks=trucks,
            cars=cars,
            buses=buses,
            motorcycles=motorcycles,
            total=cars + trucks + buses + motorcycles,
        )

    def _smooth(self, camera_id: str, new: VehicleCounts) -> VehicleCounts:
        """
        Exponential smoothing against the previous reading.

        alpha = 0.6 keeps ~60% of the new value, 40% of the old,
        which produces visually smooth but responsive updates.
        """
        prev = self._previous_counts.get(camera_id)
        if prev is None:
            return new

        alpha = 0.6
        cars = round(alpha * new.cars + (1 - alpha) * prev.cars)
        trucks = round(alpha * new.trucks + (1 - alpha) * prev.trucks)
        buses = round(alpha * new.buses + (1 - alpha) * prev.buses)
        motorcycles = round(alpha * new.motorcycles + (1 - alpha) * prev.motorcycles)

        return VehicleCounts(
            trucks=trucks,
            cars=cars,
            buses=buses,
            motorcycles=motorcycles,
            total=cars + trucks + buses + motorcycles,
        )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return service status information."""
        return {
            "service": "VisionService",
            "simulation_mode": self.simulation_mode,
            "model_loaded": self.model is not None,
            "model_name": "yolov8n.pt" if self.model else None,
            "tracked_cameras": list(self._previous_counts.keys()),
        }
