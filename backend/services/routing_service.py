"""
Eco-Lens Routing Service
==========================
Pollution-Aware Green Corridor Routing using A* pathfinding on a
grid graph with pollution-weighted edge costs.

Algorithm:
    1. Overlay a regular grid graph over the city bounds (~200m spacing).
    2. Each grid node has a pollution cost from IDW-interpolated PM2.5.
    3. Edge weight = haversine_distance * (1 + pollution_weight * normalized_pm25).
    4. Run A* with Haversine heuristic to find minimum-cost (lowest-exposure) path.
    5. Compare with shortest (direct) path to quantify exposure reduction.

The green route trades a modest increase in distance for a significant
reduction in cumulative PM2.5 exposure, enabling pedestrians and cyclists
to make informed routing choices.

References:
    - Hart, P.E., Nilsson, N.J. & Raphael, B. (1968) A Formal Basis for
      the Heuristic Determination of Minimum Cost Paths. IEEE Transactions
      on Systems Science and Cybernetics, SSC-4(2), 100-107.
    - Haversine formula for great-circle distance.
"""

import math
import heapq
import logging
from typing import List, Dict, Tuple, Optional

from models import GreenRoute, SensorData

logger = logging.getLogger(__name__)

# Grid resolution for route planning
_GRID_STEP = 0.002  # degrees (~200m in NYC latitude)

# Earth radius in km
_EARTH_RADIUS_KM = 6371.0

# Maximum A* iterations to prevent runaway searches
_MAX_ITERATIONS = 15000


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Haversine distance between two points in kilometers.

    Parameters
    ----------
    lat1, lng1, lat2, lng2 : float
        Coordinates in decimal degrees.

    Returns
    -------
    float
        Great-circle distance in km.
    """
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS_KM * c


def _snap_to_grid(value: float, step: float) -> float:
    """Snap a coordinate to the nearest grid point."""
    return round(round(value / step) * step, 6)


class RoutingService:
    """
    Green corridor route planner using pollution-weighted A* search.

    Finds the path between two geographic points that minimizes
    cumulative PM2.5 inhalation exposure, then compares it with the
    shortest geometric path to quantify the exposure benefit.
    """

    def __init__(self) -> None:
        self._sensor_cache: List[SensorData] = []

    def update_sensors(self, sensors: List[SensorData]) -> None:
        """
        Update the internal sensor cache for pollution interpolation.

        Should be called each time sensor data is refreshed (typically
        every 5 seconds).

        Parameters
        ----------
        sensors : list of SensorData
            Current sensor readings with positions and pollution data.
        """
        self._sensor_cache = list(sensors)

    # ==================================================================
    # Pollution interpolation (IDW)
    # ==================================================================

    def _interpolate_pollution_at(self, lat: float, lng: float) -> float:
        """
        Inverse Distance Weighting (power=2) interpolation of PM2.5
        at an arbitrary point from surrounding sensors.

        Parameters
        ----------
        lat, lng : float
            Target coordinates.

        Returns
        -------
        float
            Interpolated PM2.5 in ug/m3.
        """
        if not self._sensor_cache:
            return 15.0  # default urban background

        weighted_sum = 0.0
        weight_total = 0.0

        for sensor in self._sensor_cache:
            dist = _haversine(lat, lng, sensor.lat, sensor.lng)
            dist = max(dist, 0.01)  # prevent singularity
            w = 1.0 / (dist ** 2)
            weighted_sum += w * sensor.pollution.pm25
            weight_total += w

        if weight_total == 0:
            return 15.0
        return weighted_sum / weight_total

    # ==================================================================
    # Grid neighbor generation
    # ==================================================================

    @staticmethod
    def _get_neighbors(
        lat: float, lng: float, step: float
    ) -> List[Tuple[float, float]]:
        """
        Return 8-connected grid neighbors of a node.

        Produces all cardinal and diagonal adjacent grid cells.
        """
        neighbors = []
        for dlat in (-step, 0, step):
            for dlng in (-step, 0, step):
                if dlat == 0 and dlng == 0:
                    continue
                nlat = round(lat + dlat, 6)
                nlng = round(lng + dlng, 6)
                neighbors.append((nlat, nlng))
        return neighbors

    # ==================================================================
    # A* search
    # ==================================================================

    def _a_star(
        self,
        start: Tuple[float, float],
        goal: Tuple[float, float],
        step: float,
        pollution_weight: float = 2.0,
    ) -> List[Tuple[float, float]]:
        """
        A* search on a grid graph with pollution-weighted edge costs.

        Edge cost = distance_km * (1 + pollution_weight * pm25 / 50.0)

        The heuristic is straight-line Haversine distance (admissible
        since it underestimates the true cost when pollution > 0).

        Parameters
        ----------
        start : tuple of (lat, lng)
            Starting grid node.
        goal : tuple of (lat, lng)
            Goal grid node.
        step : float
            Grid spacing in degrees.
        pollution_weight : float
            Scaling factor for pollution cost (0 = shortest path).

        Returns
        -------
        list of (lat, lng) tuples
            The path from start to goal.
        """
        open_set: List[Tuple[float, Tuple[float, float]]] = []
        heapq.heappush(open_set, (0.0, start))

        came_from: Dict[Tuple[float, float], Optional[Tuple[float, float]]] = {
            start: None
        }
        g_score: Dict[Tuple[float, float], float] = {start: 0.0}

        goal_lat, goal_lng = goal
        goal_threshold = step * 111.0 * 1.5  # km threshold for "close enough"
        iterations = 0

        while open_set and iterations < _MAX_ITERATIONS:
            iterations += 1
            _, current = heapq.heappop(open_set)

            # Check if we've reached the goal
            dist_to_goal = _haversine(current[0], current[1], goal_lat, goal_lng)
            if dist_to_goal < goal_threshold:
                # Reconstruct path
                path = [goal]
                node: Optional[Tuple[float, float]] = current
                while node is not None:
                    path.append(node)
                    node = came_from.get(node)
                path.reverse()
                return path

            for neighbor in self._get_neighbors(current[0], current[1], step):
                nlat, nlng = neighbor

                # Edge distance
                dist_km = _haversine(current[0], current[1], nlat, nlng)

                # Pollution at the neighbor node
                pollution = self._interpolate_pollution_at(nlat, nlng)

                # Weighted edge cost: distance + pollution penalty
                edge_cost = dist_km * (1.0 + pollution_weight * (pollution / 50.0))
                tentative_g = g_score[current] + edge_cost

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    g_score[neighbor] = tentative_g
                    # Heuristic: straight-line distance to goal (admissible)
                    h = _haversine(nlat, nlng, goal_lat, goal_lng)
                    f = tentative_g + h
                    heapq.heappush(open_set, (f, neighbor))
                    came_from[neighbor] = current

        # Fallback: straight line if search exhausted
        logger.warning(
            "A* search did not converge after %d iterations, "
            "returning straight-line path",
            iterations,
        )
        return [start, goal]

    # ==================================================================
    # Path analysis
    # ==================================================================

    def _compute_path_exposure(
        self, path: List[Tuple[float, float]]
    ) -> Tuple[float, float]:
        """
        Compute total distance (km) and cumulative pollution exposure
        along a path.

        Exposure = sum of (segment_distance * PM2.5_at_midpoint) for
        each path segment.

        Parameters
        ----------
        path : list of (lat, lng) tuples

        Returns
        -------
        tuple of (total_distance_km, total_exposure)
        """
        total_dist = 0.0
        total_exposure = 0.0

        for i in range(len(path) - 1):
            lat1, lng1 = path[i]
            lat2, lng2 = path[i + 1]
            seg_dist = _haversine(lat1, lng1, lat2, lng2)

            midpoint_lat = (lat1 + lat2) / 2.0
            midpoint_lng = (lng1 + lng2) / 2.0
            seg_pollution = self._interpolate_pollution_at(midpoint_lat, midpoint_lng)

            total_dist += seg_dist
            total_exposure += seg_pollution * seg_dist

        return total_dist, total_exposure

    # ==================================================================
    # Public API
    # ==================================================================

    def find_green_route(
        self,
        from_lat: float,
        from_lng: float,
        to_lat: float,
        to_lng: float,
    ) -> GreenRoute:
        """
        Find the lowest-pollution route between two points.

        Runs A* twice:
        1. With ``pollution_weight=2.0`` for the green (low-exposure) route.
        2. With ``pollution_weight=0.0`` for the shortest geometric path.

        Returns a comparison showing exposure reduction percentage.

        Parameters
        ----------
        from_lat, from_lng : float
            Origin coordinates.
        to_lat, to_lng : float
            Destination coordinates.

        Returns
        -------
        GreenRoute
            Pydantic model with path, total_distance_km, avg_pollution,
            estimated_exposure, and comparison dict.
        """
        step = _GRID_STEP
        start = (_snap_to_grid(from_lat, step), _snap_to_grid(from_lng, step))
        goal = (_snap_to_grid(to_lat, step), _snap_to_grid(to_lng, step))

        # Green (pollution-minimizing) route
        green_path = self._a_star(start, goal, step, pollution_weight=2.0)
        green_dist, green_exposure = self._compute_path_exposure(green_path)

        # Shortest geometric path (no pollution penalty)
        short_path = self._a_star(start, goal, step, pollution_weight=0.0)
        short_dist, short_exposure = self._compute_path_exposure(short_path)

        # Exposure reduction percentage
        if short_exposure > 0:
            reduction = round((1.0 - green_exposure / short_exposure) * 100.0, 1)
        else:
            reduction = 0.0

        # Convert path to [[lat, lng], ...] format
        path_coords = [[round(p[0], 6), round(p[1], 6)] for p in green_path]

        avg_pollution = green_exposure / green_dist if green_dist > 0 else 0.0

        return GreenRoute(
            path=path_coords,
            total_distance_km=round(green_dist, 2),
            avg_pollution=round(avg_pollution, 1),
            estimated_exposure=round(green_exposure, 1),
            comparison={
                "shortest_path_exposure": round(short_exposure, 1),
                "green_path_exposure": round(green_exposure, 1),
                "reduction_percent": max(0.0, reduction),
                "shortest_path_distance_km": round(short_dist, 2),
                "green_path_distance_km": round(green_dist, 2),
            },
        )

    # ==================================================================
    # Diagnostics
    # ==================================================================

    def get_status(self) -> dict:
        """Return service status information."""
        return {
            "service": "RoutingService",
            "algorithm": "A* with pollution-weighted edges",
            "grid_step_degrees": _GRID_STEP,
            "max_iterations": _MAX_ITERATIONS,
            "sensors_cached": len(self._sensor_cache),
        }
