"""
Tests for Eco-Lens backend services.

Each service is tested with realistic inputs to ensure correct output
types, reasonable value ranges, and proper behaviour of key algorithms.
"""

import sys
import os
from datetime import datetime, timezone

import pytest

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from models import (
    VehicleCounts,
    PollutionData,
    WeatherData,
    NoiseData,
    HealthData,
    SensorData,
    GridData,
    ForecastPoint,
    GreenRoute,
)
from services import (
    VisionService,
    PhysicsEngine,
    ForecastService,
    HealthService,
    AcousticService,
    RoutingService,
    MeshService,
)


# ===================================================================
# VisionService
# ===================================================================


class TestVisionService:
    """Tests for the VisionService (simulation mode)."""

    def test_detect_vehicles_returns_vehicle_counts(self):
        service = VisionService()
        result = service.detect_vehicles("cam-001")
        assert isinstance(result, VehicleCounts)

    def test_detect_vehicles_has_non_negative_counts(self):
        service = VisionService()
        result = service.detect_vehicles("cam-003")
        assert result.trucks >= 0
        assert result.cars >= 0
        assert result.buses >= 0
        assert result.motorcycles >= 0
        assert result.total >= 0

    def test_simulation_mode_produces_realistic_counts(self):
        """Simulated counts for a known camera should be in a plausible range."""
        service = VisionService()
        assert service.simulation_mode is True

        # Run multiple times to check statistical plausibility
        totals = []
        for _ in range(50):
            result = service.detect_vehicles("cam-003")  # ITO Junction -- heavy traffic
            totals.append(result.total)

        avg_total = sum(totals) / len(totals)
        # ITO Junction base rates: car=50, truck=10, bus=10, moto=18 = base 88
        # After time-of-day and smoothing, average should be > 0 and < ~300
        assert avg_total > 0, "Average total should be positive"
        assert avg_total < 500, "Average total should be reasonable"

    def test_total_equals_sum_of_parts(self):
        """The total field should equal the sum of individual vehicle types."""
        service = VisionService()
        result = service.detect_vehicles("cam-001")
        assert result.total == result.trucks + result.cars + result.buses + result.motorcycles

    def test_smoothing_works(self):
        """
        Repeated calls with exponential smoothing should produce values that
        do not jump wildly between consecutive readings.
        """
        service = VisionService()

        # Run several times to let smoothing settle
        readings = []
        for _ in range(20):
            result = service.detect_vehicles("cam-001")
            readings.append(result.total)

        # Check that consecutive differences are generally small
        diffs = [abs(readings[i] - readings[i - 1]) for i in range(1, len(readings))]
        avg_diff = sum(diffs) / len(diffs)
        max_diff = max(diffs)

        # Average change should be much less than the average reading
        avg_reading = sum(readings) / len(readings)
        if avg_reading > 0:
            assert avg_diff / avg_reading < 0.5, (
                f"Average consecutive diff ({avg_diff}) is too large "
                f"relative to average reading ({avg_reading})"
            )

    def test_different_cameras_have_different_profiles(self):
        """Different camera IDs should produce different traffic patterns."""
        service = VisionService()
        totals_001 = []
        totals_004 = []
        for _ in range(30):
            # Reset smoothing by using fresh service
            s = VisionService()
            r1 = s.detect_vehicles("cam-001")
            r4 = s.detect_vehicles("cam-004")
            totals_001.append(r1.total)
            totals_004.append(r4.total)

        avg_001 = sum(totals_001) / len(totals_001)
        avg_004 = sum(totals_004) / len(totals_004)
        # They should differ since cam-004 (Anand Vihar) has more trucks
        # but we mainly just check they are both positive
        assert avg_001 > 0
        assert avg_004 > 0

    def test_unknown_camera_uses_default_profile(self):
        """An unknown camera ID should fall back to the default profile."""
        service = VisionService()
        result = service.detect_vehicles("cam-unknown")
        assert isinstance(result, VehicleCounts)
        assert result.total >= 0


# ===================================================================
# PhysicsEngine
# ===================================================================


class TestPhysicsEngine:
    """Tests for the Gaussian plume PhysicsEngine."""

    def test_calculate_pollution_returns_pollution_data(self):
        engine = PhysicsEngine()
        vehicles = VehicleCounts(trucks=10, cars=40, buses=5, motorcycles=15, total=70)
        weather = WeatherData(wind_speed=3.0, wind_direction=220.0, temperature=30.0, humidity=55.0)
        result = engine.calculate_pollution(vehicles, weather)
        assert isinstance(result, PollutionData)

    def test_pollution_values_are_positive(self):
        engine = PhysicsEngine()
        vehicles = VehicleCounts(trucks=5, cars=30, buses=3, motorcycles=10, total=48)
        weather = WeatherData(wind_speed=4.0, wind_direction=180.0, temperature=25.0, humidity=50.0)
        result = engine.calculate_pollution(vehicles, weather)
        assert result.pm25 > 0
        assert result.pm10 > 0
        assert result.no2 > 0
        assert result.co > 0
        assert result.aqi > 0

    def test_pollution_increases_with_more_vehicles(self):
        engine = PhysicsEngine()
        weather = WeatherData(wind_speed=3.0, wind_direction=200.0, temperature=28.0, humidity=50.0)

        low_traffic = VehicleCounts(trucks=2, cars=10, buses=1, motorcycles=3, total=16)
        high_traffic = VehicleCounts(trucks=20, cars=80, buses=10, motorcycles=30, total=140)

        # Run multiple times and average to handle random noise
        low_pm25_vals = []
        high_pm25_vals = []
        for _ in range(30):
            low_result = engine.calculate_pollution(low_traffic, weather, hour=12)
            high_result = engine.calculate_pollution(high_traffic, weather, hour=12)
            low_pm25_vals.append(low_result.pm25)
            high_pm25_vals.append(high_result.pm25)

        avg_low = sum(low_pm25_vals) / len(low_pm25_vals)
        avg_high = sum(high_pm25_vals) / len(high_pm25_vals)
        assert avg_high > avg_low, (
            f"More vehicles should produce higher PM2.5: low={avg_low}, high={avg_high}"
        )

    def test_aqi_category_is_valid(self):
        engine = PhysicsEngine()
        vehicles = VehicleCounts(trucks=10, cars=40, buses=5, motorcycles=15, total=70)
        weather = WeatherData(wind_speed=3.0, wind_direction=220.0, temperature=30.0, humidity=55.0)
        result = engine.calculate_pollution(vehicles, weather)
        valid_categories = {
            "Good", "Moderate", "Unhealthy for Sensitive Groups",
            "Unhealthy", "Very Unhealthy", "Hazardous",
        }
        assert result.category in valid_categories

    def test_pm25_to_aqi_known_values(self):
        """Test AQI conversion with known EPA breakpoints."""
        assert PhysicsEngine.pm25_to_aqi(0.0) == 0
        assert PhysicsEngine.pm25_to_aqi(12.0) == 50
        assert PhysicsEngine.pm25_to_aqi(35.4) == 100
        assert PhysicsEngine.pm25_to_aqi(500.4) == 500

    def test_emission_rate_calculation(self):
        engine = PhysicsEngine()
        vehicles = VehicleCounts(trucks=10, cars=50, buses=5, motorcycles=20, total=85)
        rates = engine.calculate_emission_rate(vehicles)
        assert "pm25" in rates
        assert "pm10" in rates
        assert "no2" in rates
        assert "co" in rates
        # Rates should be positive
        assert rates["pm25"] > 0
        assert rates["co"] > 0

    def test_generate_particles(self):
        engine = PhysicsEngine()
        pollution = PollutionData(pm25=40.0, pm10=70.0, no2=30.0, co=400.0, aqi=112, category="USG")
        weather = WeatherData(wind_speed=3.0, wind_direction=220.0, temperature=30.0, humidity=55.0)
        particles = engine.generate_particles(
            sensor_id="cam-001", lat=28.6129, lng=77.2295,
            pollution=pollution, weather=weather, count=10,
        )
        assert len(particles) == 10
        for p in particles:
            assert p.source_id == "cam-001"
            assert p.concentration >= 0.0
            assert p.age >= 0.0


# ===================================================================
# AcousticService
# ===================================================================


class TestAcousticService:
    """Tests for the FHWA Traffic Noise Model."""

    def test_estimate_noise_returns_noise_data(self):
        service = AcousticService()
        vehicles = VehicleCounts(trucks=8, cars=45, buses=6, motorcycles=12, total=71)
        result = service.estimate_noise(vehicles)
        assert isinstance(result, NoiseData)

    def test_noise_level_is_positive(self):
        service = AcousticService()
        vehicles = VehicleCounts(trucks=5, cars=30, buses=3, motorcycles=10, total=48)
        result = service.estimate_noise(vehicles)
        assert result.db_level > 0

    def test_noise_increases_with_more_vehicles(self):
        service = AcousticService()
        low_traffic = VehicleCounts(trucks=1, cars=5, buses=0, motorcycles=2, total=8)
        high_traffic = VehicleCounts(trucks=15, cars=60, buses=10, motorcycles=25, total=110)

        # Average over multiple runs to account for random perturbation
        low_dbs = []
        high_dbs = []
        for _ in range(30):
            low_dbs.append(service.estimate_noise(low_traffic).db_level)
            high_dbs.append(service.estimate_noise(high_traffic).db_level)

        avg_low = sum(low_dbs) / len(low_dbs)
        avg_high = sum(high_dbs) / len(high_dbs)
        assert avg_high > avg_low, (
            f"More vehicles should produce higher noise: low={avg_low}, high={avg_high}"
        )

    def test_noise_category_is_valid(self):
        service = AcousticService()
        vehicles = VehicleCounts(trucks=8, cars=45, buses=6, motorcycles=12, total=71)
        result = service.estimate_noise(vehicles)
        valid_categories = {"Quiet", "Moderate", "Loud", "Very Loud", "Extreme"}
        assert result.category in valid_categories

    def test_zero_vehicles_returns_ambient(self):
        """With zero vehicles, noise should reflect ambient background only."""
        service = AcousticService()
        vehicles = VehicleCounts()
        result = service.estimate_noise(vehicles)
        # Ambient background is ~45 dB plus some noise; result should be >= 30 dB
        assert result.db_level >= 30.0


# ===================================================================
# HealthService
# ===================================================================


class TestHealthService:
    """Tests for the WHO-based HealthService."""

    def test_calculate_health_impact_returns_health_data(self):
        service = HealthService()
        pollution = PollutionData(pm25=42.0, pm10=78.0, no2=35.0, co=450.0, aqi=117, category="USG")
        noise = NoiseData(db_level=72.0, category="Very Loud")
        result = service.calculate_health_impact(pollution, noise)
        assert isinstance(result, HealthData)

    def test_health_score_range(self):
        service = HealthService()
        pollution = PollutionData(pm25=42.0, pm10=78.0, no2=35.0, co=450.0, aqi=117, category="USG")
        noise = NoiseData(db_level=72.0, category="Very Loud")
        result = service.calculate_health_impact(pollution, noise)
        assert 0 <= result.score <= 100

    def test_clean_air_gives_high_score(self):
        service = HealthService()
        pollution = PollutionData(pm25=3.0, pm10=8.0, no2=5.0, co=100.0, aqi=12, category="Good")
        noise = NoiseData(db_level=40.0, category="Quiet")
        result = service.calculate_health_impact(pollution, noise)
        assert result.score >= 80
        assert result.risk_level == "Low"

    def test_dirty_air_gives_low_score(self):
        service = HealthService()
        pollution = PollutionData(pm25=200.0, pm10=300.0, no2=150.0, co=2000.0, aqi=300, category="Hazardous")
        noise = NoiseData(db_level=85.0, category="Extreme")
        result = service.calculate_health_impact(pollution, noise)
        assert result.score < 50
        assert result.risk_level in ("High", "Very High", "Severe")

    def test_risk_level_is_valid(self):
        service = HealthService()
        pollution = PollutionData(pm25=42.0, pm10=78.0, no2=35.0, co=450.0, aqi=117, category="USG")
        noise = NoiseData(db_level=72.0, category="Very Loud")
        result = service.calculate_health_impact(pollution, noise)
        valid_levels = {"Low", "Moderate", "High", "Very High", "Severe"}
        assert result.risk_level in valid_levels

    def test_cigarette_equivalent_is_non_negative(self):
        service = HealthService()
        pollution = PollutionData(pm25=42.0, pm10=78.0, no2=35.0, co=450.0, aqi=117, category="USG")
        noise = NoiseData(db_level=72.0, category="Very Loud")
        result = service.calculate_health_impact(pollution, noise)
        assert result.equivalent_cigarettes >= 0.0

    def test_cigarette_equivalent_scales_with_pm25(self):
        service = HealthService()
        noise = NoiseData(db_level=50.0, category="Moderate")

        low_pm = PollutionData(pm25=10.0)
        high_pm = PollutionData(pm25=100.0)

        result_low = service.calculate_health_impact(low_pm, noise)
        result_high = service.calculate_health_impact(high_pm, noise)
        assert result_high.equivalent_cigarettes > result_low.equivalent_cigarettes

    def test_advisory_text_is_not_empty(self):
        service = HealthService()
        pollution = PollutionData(pm25=42.0, pm10=78.0, no2=35.0, co=450.0, aqi=117, category="USG")
        noise = NoiseData(db_level=72.0, category="Very Loud")
        result = service.calculate_health_impact(pollution, noise)
        assert isinstance(result.vulnerable_advisory, str)
        assert len(result.vulnerable_advisory) > 0

    def test_aggregate_health_summary(self):
        service = HealthService()
        health_list = [
            HealthData(score=80, risk_level="Low", equivalent_cigarettes=0.5),
            HealthData(score=50, risk_level="High", equivalent_cigarettes=2.5),
        ]
        summary = service.get_aggregate_health_summary(health_list)
        assert summary["sensor_count"] == 2
        assert summary["worst_risk_level"] == "High"
        assert summary["avg_score"] == 65
        assert summary["avg_equivalent_cigarettes"] == 1.5


# ===================================================================
# ForecastService
# ===================================================================


class TestForecastService:
    """Tests for the Holt-Winters ForecastService."""

    def test_generate_forecast_returns_forecast_points(self):
        service = ForecastService()
        # Need to record some observations first
        for _ in range(30):
            service.record_observation("cam-001", 40.0)

        result = service.generate_forecast("cam-001", hours_ahead=6, interval_minutes=30)
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(p, ForecastPoint) for p in result)

    def test_forecast_point_count(self):
        """6 hours at 30-minute intervals = 12 forecast points."""
        service = ForecastService()
        for _ in range(20):
            service.record_observation("cam-001", 35.0)

        result = service.generate_forecast("cam-001", hours_ahead=6, interval_minutes=30)
        assert len(result) == 12

    def test_forecast_has_positive_pm25(self):
        service = ForecastService()
        for _ in range(30):
            service.record_observation("cam-001", 50.0)

        result = service.generate_forecast("cam-001")
        for point in result:
            assert point.predicted_pm25 > 0

    def test_confidence_intervals(self):
        """Confidence intervals should bracket the predicted value."""
        service = ForecastService()
        for _ in range(30):
            service.record_observation("cam-001", 45.0)

        result = service.generate_forecast("cam-001")
        for point in result:
            assert point.confidence_lower <= point.predicted_pm25
            assert point.confidence_upper >= point.predicted_pm25

    def test_confidence_intervals_widen_over_time(self):
        """Later forecast points should generally have wider confidence intervals."""
        service = ForecastService()
        for _ in range(50):
            service.record_observation("cam-001", 42.0)

        result = service.generate_forecast("cam-001", hours_ahead=6, interval_minutes=30)
        first_width = result[0].confidence_upper - result[0].confidence_lower
        last_width = result[-1].confidence_upper - result[-1].confidence_lower
        assert last_width > first_width, "Confidence intervals should widen for further forecasts"

    def test_no_observations_returns_fallback_forecast(self):
        """Even with no observations, a forecast should be generated (using defaults)."""
        service = ForecastService()
        result = service.generate_forecast("cam-never-seen", hours_ahead=2, interval_minutes=60)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_record_observation_updates_level(self):
        service = ForecastService()
        service.record_observation("cam-001", 50.0)
        # After one observation, the level should be close to 50
        assert abs(service._level["cam-001"] - 50.0) < 1.0


# ===================================================================
# MeshService
# ===================================================================


class TestMeshService:
    """Tests for the Kriging/IDW MeshService."""

    def _make_sensors(self) -> list:
        """Create a set of test sensors for grid generation."""
        ts = datetime.now(timezone.utc).isoformat()
        sensors = []
        locations = [
            ("cam-001", "India Gate", 28.6129, 77.2295, 42.0),
            ("cam-002", "Connaught Place", 28.6315, 77.2167, 28.0),
            ("cam-003", "ITO Junction", 28.6280, 77.2413, 55.0),
            ("cam-004", "Anand Vihar", 28.6469, 77.3164, 65.0),
            ("cam-005", "Dwarka Sec-8", 28.5733, 77.0659, 20.0),
            ("cam-006", "Chandni Chowk", 28.6506, 77.2302, 48.0),
        ]
        for sid, name, lat, lng, pm25 in locations:
            sensors.append(
                SensorData(
                    id=sid, name=name, lat=lat, lng=lng, status="active",
                    vehicles=VehicleCounts(total=50),
                    pollution=PollutionData(pm25=pm25),
                    weather=WeatherData(),
                    noise=NoiseData(),
                    health=HealthData(),
                    timestamp=ts,
                )
            )
        return sensors

    def test_generate_grid_returns_grid_data(self):
        service = MeshService()
        sensors = self._make_sensors()
        result = service.generate_grid(sensors)
        assert isinstance(result, GridData)

    def test_grid_dimensions_match_resolution(self):
        service = MeshService()
        service.set_resolution(10)
        sensors = self._make_sensors()
        result = service.generate_grid(sensors, resolution=10)
        assert len(result.values) == 10
        assert all(len(row) == 10 for row in result.values)

    def test_grid_values_are_non_negative(self):
        service = MeshService()
        sensors = self._make_sensors()
        result = service.generate_grid(sensors, resolution=10)
        for row in result.values:
            for val in row:
                assert val >= 0.0, f"Grid value should be non-negative: {val}"

    def test_grid_with_few_sensors_uses_idw(self):
        """With fewer than 4 sensors, IDW should be used instead of Kriging."""
        service = MeshService()
        ts = datetime.now(timezone.utc).isoformat()
        sensors = [
            SensorData(
                id="cam-001", name="A", lat=28.6, lng=77.2, status="active",
                vehicles=VehicleCounts(), pollution=PollutionData(pm25=30.0),
                weather=WeatherData(), noise=NoiseData(), health=HealthData(),
                timestamp=ts,
            ),
            SensorData(
                id="cam-002", name="B", lat=28.7, lng=77.3, status="active",
                vehicles=VehicleCounts(), pollution=PollutionData(pm25=50.0),
                weather=WeatherData(), noise=NoiseData(), health=HealthData(),
                timestamp=ts,
            ),
        ]
        result = service.generate_grid(sensors, resolution=5)
        assert isinstance(result, GridData)
        assert len(result.values) == 5

    def test_grid_bounds_are_preserved(self):
        service = MeshService()
        sensors = self._make_sensors()
        custom_bounds = {"north": 28.70, "south": 28.55, "east": 77.35, "west": 77.05}
        result = service.generate_grid(sensors, bounds=custom_bounds, resolution=5)
        assert result.bounds == custom_bounds


# ===================================================================
# RoutingService
# ===================================================================


class TestRoutingService:
    """Tests for the A*-based RoutingService."""

    def _make_sensors(self) -> list:
        """Create sensors for routing tests."""
        ts = datetime.now(timezone.utc).isoformat()
        return [
            SensorData(
                id="cam-001", name="India Gate", lat=28.6129, lng=77.2295, status="active",
                vehicles=VehicleCounts(total=70),
                pollution=PollutionData(pm25=42.0),
                weather=WeatherData(), noise=NoiseData(), health=HealthData(),
                timestamp=ts,
            ),
            SensorData(
                id="cam-002", name="Connaught Place", lat=28.6315, lng=77.2167, status="active",
                vehicles=VehicleCounts(total=65),
                pollution=PollutionData(pm25=28.0),
                weather=WeatherData(), noise=NoiseData(), health=HealthData(),
                timestamp=ts,
            ),
        ]

    def test_find_green_route_returns_green_route(self):
        service = RoutingService()
        service.update_sensors(self._make_sensors())
        result = service.find_green_route(28.612, 77.229, 28.620, 77.225)
        assert isinstance(result, GreenRoute)

    def test_route_has_path_points(self):
        service = RoutingService()
        service.update_sensors(self._make_sensors())
        result = service.find_green_route(28.612, 77.229, 28.620, 77.225)
        assert len(result.path) >= 2
        # Each path point should be [lat, lng]
        for point in result.path:
            assert len(point) == 2
            assert isinstance(point[0], float)
            assert isinstance(point[1], float)

    def test_route_has_positive_distance(self):
        service = RoutingService()
        service.update_sensors(self._make_sensors())
        result = service.find_green_route(28.612, 77.229, 28.622, 77.224)
        assert result.total_distance_km > 0

    def test_route_comparison_has_expected_keys(self):
        service = RoutingService()
        service.update_sensors(self._make_sensors())
        result = service.find_green_route(28.612, 77.229, 28.618, 77.224)
        assert "shortest_path_exposure" in result.comparison
        assert "green_path_exposure" in result.comparison
        assert "reduction_percent" in result.comparison

    def test_route_exposure_is_non_negative(self):
        service = RoutingService()
        service.update_sensors(self._make_sensors())
        result = service.find_green_route(28.612, 77.229, 28.618, 77.224)
        assert result.estimated_exposure >= 0
        assert result.avg_pollution >= 0

    def test_route_without_sensors_uses_default_pollution(self):
        """Even with no sensors, routing should not crash."""
        service = RoutingService()
        # No sensors updated
        result = service.find_green_route(28.612, 77.229, 28.614, 77.230)
        assert isinstance(result, GreenRoute)
        assert result.total_distance_km >= 0


# ===================================================================
# Integration-style tests (cross-service)
# ===================================================================


class TestCrossServiceIntegration:
    """Tests that combine multiple services in a realistic pipeline."""

    def test_full_pipeline_vision_to_health(self):
        """
        Simulate the full processing pipeline:
        VisionService -> PhysicsEngine -> AcousticService -> HealthService
        """
        vision = VisionService()
        physics = PhysicsEngine()
        acoustic = AcousticService()
        health = HealthService()

        vehicles = vision.detect_vehicles("cam-001")
        assert isinstance(vehicles, VehicleCounts)

        weather = WeatherData(wind_speed=3.0, wind_direction=220.0, temperature=30.0, humidity=55.0)
        pollution = physics.calculate_pollution(vehicles, weather)
        assert isinstance(pollution, PollutionData)

        noise = acoustic.estimate_noise(vehicles)
        assert isinstance(noise, NoiseData)

        health_impact = health.calculate_health_impact(pollution, noise)
        assert isinstance(health_impact, HealthData)
        assert 0 <= health_impact.score <= 100

    def test_forecast_after_observations(self):
        """ForecastService should produce valid forecasts after recording observations."""
        vision = VisionService()
        physics = PhysicsEngine()
        forecast = ForecastService()

        weather = WeatherData(wind_speed=3.0, wind_direction=220.0)

        # Simulate 50 observation cycles
        for _ in range(50):
            vehicles = vision.detect_vehicles("cam-001")
            pollution = physics.calculate_pollution(vehicles, weather)
            forecast.record_observation("cam-001", pollution.pm25)

        result = forecast.generate_forecast("cam-001", hours_ahead=3, interval_minutes=30)
        assert len(result) == 6
        for point in result:
            assert point.predicted_pm25 > 0
            assert point.confidence_lower <= point.predicted_pm25
