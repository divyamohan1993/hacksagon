"""
Eco-Lens Mesh Service
======================
Virtual Sensor Mesh with Kriging Spatial Interpolation.

Implements Ordinary Kriging to create a continuous pollution surface from
discrete sensor readings, providing the gold-standard geostatistical
interpolation method used in environmental monitoring.

Algorithm overview:
    1. Given N sensor locations with PM2.5 readings.
    2. Compute the experimental semivariogram (spatial correlation structure).
    3. Fit a theoretical variogram model (spherical) to the empirical data.
    4. For each target grid point, build and solve the Ordinary Kriging
       system of equations to obtain interpolated values with estimation
       variance.

The Kriging system for Ordinary Kriging:

    | gamma(x1,x1)  gamma(x1,x2) ... gamma(x1,xN)  1 |   | w1    |   | gamma(x1,x0) |
    | gamma(x2,x1)  gamma(x2,x2) ... gamma(x2,xN)  1 |   | w2    |   | gamma(x2,x0) |
    |    ...            ...       ...    ...         . | * | ...   | = |     ...       |
    | gamma(xN,x1)  gamma(xN,x2) ... gamma(xN,xN)  1 |   | wN    |   | gamma(xN,x0) |
    |      1            1         ...      1         0 |   | mu    |   |       1       |

Where gamma(h) is the semivariogram value at lag h, w_i are the Kriging
weights, and mu is the Lagrange multiplier for the unbiasedness constraint.

The spherical variogram model:
    gamma(h) = nugget + (sill - nugget) * [1.5*(h/range) - 0.5*(h/range)^3]
                                           for 0 < h <= range
    gamma(h) = sill                        for h > range
    gamma(0) = 0

Also supports IDW as a fast fallback when there are too few sensors
for stable Kriging.

References:
    - Cressie, N. (1993) Statistics for Spatial Data, Revised Ed. Wiley.
    - Isaaks, E.H. & Srivastava, R.M. (1989) Applied Geostatistics.
      Oxford University Press.
    - Matheron, G. (1963) Principles of Geostatistics. Economic Geology,
      58, 1246-1266.
"""

import math
import logging
from typing import List, Tuple, Dict, Optional

from models import GridData, SensorData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default grid bounds (NYC area)
# ---------------------------------------------------------------------------
_DEFAULT_BOUNDS = {
    "north": 40.82,
    "south": 40.70,
    "east": -73.78,
    "west": -74.02,
}

_DEFAULT_RESOLUTION = 30

# Earth radius in km
_EARTH_RADIUS_KM = 6371.0

# Minimum distance to prevent singularity (km)
_MIN_DISTANCE_KM = 0.05

# IDW power parameter (fallback)
_IDW_POWER = 2.5

# Minimum sensors required for Kriging (need enough for variogram)
_MIN_SENSORS_FOR_KRIGING = 4


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance between two points in km."""
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


class MeshService:
    """
    Generates interpolated pollution grids using Ordinary Kriging
    with a spherical variogram model, falling back to Inverse Distance
    Weighting when insufficient data is available.
    """

    def __init__(self) -> None:
        self._bounds = dict(_DEFAULT_BOUNDS)
        self._resolution = _DEFAULT_RESOLUTION
        self._variogram_params: Optional[Dict[str, float]] = None

    def set_bounds(
        self, north: float, south: float, east: float, west: float
    ) -> None:
        """Override the default grid bounds."""
        self._bounds = {
            "north": north,
            "south": south,
            "east": east,
            "west": west,
        }

    def set_resolution(self, resolution: int) -> None:
        """Override the default grid resolution."""
        self._resolution = max(5, min(100, resolution))

    # ==================================================================
    # Haversine distance (meters, for variogram)
    # ==================================================================

    @staticmethod
    def _haversine_meters(
        lat1: float, lng1: float, lat2: float, lng2: float
    ) -> float:
        """Haversine distance in meters."""
        return _haversine(lat1, lng1, lat2, lng2) * 1000.0

    # ==================================================================
    # Experimental Semivariogram
    # ==================================================================

    def _calculate_semivariogram(
        self,
        locations: List[Tuple[float, float]],
        values: List[float],
        n_lags: int = 10,
    ) -> Dict[str, float]:
        """
        Compute the experimental semivariogram and fit a spherical model.

        The empirical semivariogram is estimated using Matheron's classical
        estimator:
            gamma_hat(h) = (1 / 2|N(h)|) * sum_{(i,j) in N(h)} [z(xi) - z(xj)]^2

        where N(h) is the set of all data pairs separated by lag h (+/- tolerance).

        Then fits a spherical variogram model by method of moments:
            nugget = min empirical variance (near-zero lag)
            sill   = overall data variance
            range  = lag at which semivariance first reaches ~sill

        Parameters
        ----------
        locations : list of (lat, lng) tuples
            Sensor positions.
        values : list of float
            PM2.5 readings at each location.
        n_lags : int
            Number of lag bins for the experimental variogram.

        Returns
        -------
        dict
            Keys: nugget, sill, range_param (in meters).
        """
        n = len(locations)
        if n < 2:
            return {"nugget": 0.0, "sill": 1.0, "range_param": 1000.0}

        # Calculate all pairwise distances and squared differences
        distances: List[float] = []
        sq_diffs: List[float] = []

        for i in range(n):
            for j in range(i + 1, n):
                d = self._haversine_meters(
                    locations[i][0], locations[i][1],
                    locations[j][0], locations[j][1],
                )
                sq_diff = (values[i] - values[j]) ** 2
                distances.append(d)
                sq_diffs.append(sq_diff)

        if not distances:
            return {"nugget": 0.0, "sill": 1.0, "range_param": 1000.0}

        # Determine lag bins
        max_dist = max(distances)
        lag_width = max_dist / n_lags if max_dist > 0 else 100.0
        lag_width = max(lag_width, 10.0)  # minimum 10m bin width

        # Compute empirical semivariogram
        lag_centers: List[float] = []
        gamma_values: List[float] = []

        for lag_idx in range(n_lags):
            h_low = lag_idx * lag_width
            h_high = (lag_idx + 1) * lag_width
            h_center = (h_low + h_high) / 2.0

            # Find all pairs in this lag bin
            bin_sq_diffs = [
                sq_diffs[k]
                for k in range(len(distances))
                if h_low <= distances[k] < h_high
            ]

            if bin_sq_diffs:
                # Matheron estimator: gamma(h) = (1/2N) * sum(z_i - z_j)^2
                gamma_h = sum(bin_sq_diffs) / (2.0 * len(bin_sq_diffs))
                lag_centers.append(h_center)
                gamma_values.append(gamma_h)

        if not gamma_values:
            data_var = sum((v - sum(values) / n) ** 2 for v in values) / n
            return {
                "nugget": 0.0,
                "sill": max(data_var, 1.0),
                "range_param": max_dist * 0.5 if max_dist > 0 else 1000.0,
            }

        # Fit spherical model by method-of-moments estimation
        data_variance = sum((v - sum(values) / n) ** 2 for v in values) / n
        sill = max(max(gamma_values), data_variance, 1.0)

        # Nugget: extrapolate from smallest lag (near-origin intercept)
        nugget = max(0.0, gamma_values[0] * 0.5) if gamma_values else 0.0

        # Range: lag at which gamma first exceeds 95% of sill
        range_param = max_dist * 0.5  # default to half max distance
        for i, g in enumerate(gamma_values):
            if g >= 0.95 * sill:
                range_param = lag_centers[i]
                break

        range_param = max(range_param, 100.0)  # minimum 100m range

        return {
            "nugget": nugget,
            "sill": sill,
            "range_param": range_param,
        }

    # ==================================================================
    # Spherical Variogram Model
    # ==================================================================

    @staticmethod
    def _spherical_variogram(
        h: float,
        nugget: float,
        sill: float,
        range_param: float,
    ) -> float:
        """
        Spherical variogram model.

        gamma(h) = 0                                              if h == 0
        gamma(h) = nugget + (sill-nugget)*[1.5*(h/a)-0.5*(h/a)^3]  if 0 < h <= a
        gamma(h) = sill                                           if h > a

        Parameters
        ----------
        h : float
            Lag distance (meters).
        nugget : float
            Nugget effect (variance at zero distance).
        sill : float
            Total variance (plateau).
        range_param : float
            Range parameter a (distance at which sill is reached).

        Returns
        -------
        float
            Semivariogram value at lag h.
        """
        if h <= 0:
            return 0.0

        a = max(range_param, 1.0)
        partial_sill = sill - nugget

        if h <= a:
            hr = h / a
            return nugget + partial_sill * (1.5 * hr - 0.5 * hr ** 3)
        else:
            return sill

    # ==================================================================
    # Ordinary Kriging at a Single Point
    # ==================================================================

    def _ordinary_kriging(
        self,
        known_points: List[Tuple[float, float]],
        known_values: List[float],
        target_point: Tuple[float, float],
        variogram_params: Dict[str, float],
    ) -> float:
        """
        Ordinary Kriging interpolation at a single target point.

        Builds and solves the Kriging system:
            [Gamma + Lagrange] * [weights] = [gamma_target]

        Uses Gauss-Jordan elimination to solve the (N+1) x (N+1) system
        without requiring numpy.

        Parameters
        ----------
        known_points : list of (lat, lng) tuples
            Known sensor locations.
        known_values : list of float
            PM2.5 values at each known location.
        target_point : (lat, lng) tuple
            Location to interpolate.
        variogram_params : dict
            Variogram model parameters (nugget, sill, range_param).

        Returns
        -------
        float
            Kriging estimate of PM2.5 at the target point.
        """
        n = len(known_points)
        nugget = variogram_params["nugget"]
        sill = variogram_params["sill"]
        range_p = variogram_params["range_param"]

        # Build the (N+1) x (N+2) augmented matrix for the Kriging system
        # Last row/col is the Lagrange multiplier constraint
        size = n + 1

        # Initialize augmented matrix [A | b]
        matrix = [[0.0] * (size + 1) for _ in range(size)]

        # Fill the NxN gamma matrix
        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 0.0  # gamma(0) = 0 on diagonal
                else:
                    h = self._haversine_meters(
                        known_points[i][0], known_points[i][1],
                        known_points[j][0], known_points[j][1],
                    )
                    matrix[i][j] = self._spherical_variogram(h, nugget, sill, range_p)

        # Lagrange constraint: last row and column of 1s
        for i in range(n):
            matrix[i][n] = 1.0
            matrix[n][i] = 1.0
        matrix[n][n] = 0.0

        # Right-hand side: gamma from target to each known point, plus 1
        target_lat, target_lng = target_point
        for i in range(n):
            h = self._haversine_meters(
                known_points[i][0], known_points[i][1],
                target_lat, target_lng,
            )
            matrix[i][size] = self._spherical_variogram(h, nugget, sill, range_p)
        matrix[n][size] = 1.0

        # Solve using Gauss-Jordan elimination with partial pivoting
        solution = self._gauss_jordan(matrix, size)

        if solution is None:
            # Fallback to IDW if Kriging system is singular
            return self._idw_single(known_points, known_values, target_point)

        # Kriging estimate: weighted sum of known values
        estimate = 0.0
        for i in range(n):
            estimate += solution[i] * known_values[i]

        # Clamp to reasonable range
        return max(0.0, estimate)

    # ==================================================================
    # Gauss-Jordan Elimination
    # ==================================================================

    @staticmethod
    def _gauss_jordan(
        matrix: List[List[float]], size: int
    ) -> Optional[List[float]]:
        """
        Solve a system of linear equations using Gauss-Jordan elimination
        with partial pivoting.

        Parameters
        ----------
        matrix : list of list of float
            Augmented matrix [A | b] of shape (size, size+1).
        size : int
            Number of equations.

        Returns
        -------
        list of float or None
            Solution vector, or None if the system is singular.
        """
        m = [row[:] for row in matrix]  # deep copy
        n = size

        for col in range(n):
            # Partial pivoting: find row with largest absolute value in column
            max_row = col
            max_val = abs(m[col][col])
            for row in range(col + 1, n):
                if abs(m[row][col]) > max_val:
                    max_val = abs(m[row][col])
                    max_row = row

            if max_val < 1e-12:
                return None  # singular matrix

            # Swap rows
            m[col], m[max_row] = m[max_row], m[col]

            # Eliminate column
            pivot = m[col][col]
            for j in range(n + 1):
                m[col][j] /= pivot

            for row in range(n):
                if row == col:
                    continue
                factor = m[row][col]
                for j in range(n + 1):
                    m[row][j] -= factor * m[col][j]

        # Extract solution
        return [m[i][n] for i in range(n)]

    # ==================================================================
    # IDW fallback (for too few sensors)
    # ==================================================================

    @staticmethod
    def _idw_single(
        known_points: List[Tuple[float, float]],
        known_values: List[float],
        target_point: Tuple[float, float],
        power: float = _IDW_POWER,
    ) -> float:
        """Inverse Distance Weighting interpolation at a single point."""
        if not known_points:
            return 10.0

        weighted_sum = 0.0
        weight_total = 0.0

        target_lat, target_lng = target_point
        for i, (lat, lng) in enumerate(known_points):
            dist = _haversine(target_lat, target_lng, lat, lng)
            dist = max(dist, _MIN_DISTANCE_KM)
            w = 1.0 / (dist ** power)
            weighted_sum += w * known_values[i]
            weight_total += w

        if weight_total == 0:
            return 10.0
        return weighted_sum / weight_total

    # ==================================================================
    # IDW interpolation for full grid (fallback path)
    # ==================================================================

    def _idw_interpolate(
        self,
        target_lat: float,
        target_lng: float,
        sensors: List[SensorData],
        power: float = _IDW_POWER,
    ) -> float:
        """IDW interpolation from SensorData objects."""
        if not sensors:
            return 10.0

        weighted_sum = 0.0
        weight_total = 0.0

        for sensor in sensors:
            dist = _haversine(target_lat, target_lng, sensor.lat, sensor.lng)
            dist = max(dist, _MIN_DISTANCE_KM)
            w = 1.0 / (dist ** power)
            weighted_sum += w * sensor.pollution.pm25
            weight_total += w

        if weight_total == 0:
            return 10.0
        return weighted_sum / weight_total

    # ==================================================================
    # Public API: Generate Interpolated Grid
    # ==================================================================

    def generate_grid(
        self,
        sensors: List[SensorData],
        bounds: Optional[dict] = None,
        resolution: Optional[int] = None,
    ) -> GridData:
        """
        Generate an interpolated PM2.5 pollution grid.

        Uses Ordinary Kriging when >= 4 sensors are available;
        falls back to IDW otherwise.

        Parameters
        ----------
        sensors : list of SensorData
            Current sensor readings with positions and pollution data.
        bounds : dict, optional
            Override grid bounds {north, south, east, west}.
        resolution : int, optional
            Override grid resolution (cells per axis).

        Returns
        -------
        GridData
            Grid with bounds, resolution, and 2D array of PM2.5 values.
        """
        grid_bounds = bounds or self._bounds
        grid_res = resolution or self._resolution

        north = grid_bounds["north"]
        south = grid_bounds["south"]
        east = grid_bounds["east"]
        west = grid_bounds["west"]

        lat_step = (north - south) / grid_res
        lng_step = (east - west) / grid_res

        # Extract locations and values for Kriging
        locations = [(s.lat, s.lng) for s in sensors]
        values = [s.pollution.pm25 for s in sensors]

        use_kriging = len(sensors) >= _MIN_SENSORS_FOR_KRIGING

        if use_kriging:
            # Compute variogram from current sensor data
            vparams = self._calculate_semivariogram(locations, values)
            self._variogram_params = vparams
            logger.debug(
                "Kriging variogram: nugget=%.2f, sill=%.2f, range=%.0fm",
                vparams["nugget"], vparams["sill"], vparams["range_param"],
            )
        else:
            vparams = None

        # Generate the grid
        grid_values: List[List[float]] = []

        for row in range(grid_res):
            lat = north - (row + 0.5) * lat_step
            row_values: List[float] = []

            for col in range(grid_res):
                lng = west + (col + 0.5) * lng_step

                if use_kriging and vparams is not None:
                    pm25 = self._ordinary_kriging(
                        locations, values, (lat, lng), vparams
                    )
                else:
                    pm25 = self._idw_interpolate(lat, lng, sensors)

                row_values.append(round(max(0.0, pm25), 1))

            grid_values.append(row_values)

        return GridData(
            bounds=grid_bounds,
            resolution=grid_res,
            values=grid_values,
        )

    # ==================================================================
    # AQI Grid (converted from PM2.5 grid)
    # ==================================================================

    def generate_aqi_grid(
        self,
        sensors: List[SensorData],
        bounds: Optional[dict] = None,
        resolution: Optional[int] = None,
    ) -> GridData:
        """
        Generate a grid of AQI values by converting the PM2.5 grid
        using EPA breakpoints.

        Parameters
        ----------
        sensors : list of SensorData
        bounds : dict, optional
        resolution : int, optional

        Returns
        -------
        GridData
            Grid of AQI values.
        """
        pm25_grid = self.generate_grid(sensors, bounds, resolution)

        aqi_values: List[List[float]] = []
        for row in pm25_grid.values:
            aqi_row: List[float] = []
            for pm25 in row:
                aqi = self._pm25_to_aqi(pm25)
                aqi_row.append(float(aqi))
            aqi_values.append(aqi_row)

        return GridData(
            bounds=pm25_grid.bounds,
            resolution=pm25_grid.resolution,
            values=aqi_values,
        )

    # ==================================================================
    # PM2.5 to AQI conversion
    # ==================================================================

    @staticmethod
    def _pm25_to_aqi(pm25: float) -> int:
        """Convert PM2.5 (ug/m3) to EPA AQI using standard breakpoints."""
        breakpoints = [
            (0.0,   12.0,   0,  50),
            (12.1,  35.4,  51, 100),
            (35.5,  55.4, 101, 150),
            (55.5, 150.4, 151, 200),
            (150.5, 250.4, 201, 300),
            (250.5, 500.4, 301, 500),
        ]
        pm25 = max(0.0, pm25)
        for bp_lo, bp_hi, aqi_lo, aqi_hi in breakpoints:
            if pm25 <= bp_hi:
                aqi = ((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (pm25 - bp_lo) + aqi_lo
                return round(aqi)
        return 500

    # ==================================================================
    # Diagnostics
    # ==================================================================

    def get_status(self) -> dict:
        """Return service status information."""
        return {
            "service": "MeshService",
            "interpolation_method": "Ordinary Kriging (spherical variogram)",
            "fallback_method": "Inverse Distance Weighting",
            "min_sensors_for_kriging": _MIN_SENSORS_FOR_KRIGING,
            "bounds": self._bounds,
            "resolution": self._resolution,
            "variogram_params": self._variogram_params,
        }
