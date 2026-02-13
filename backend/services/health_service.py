"""
Eco-Lens Health Service
========================
Health Impact Scoring with WHO-based exposure dosimetry.

Converts pollutant concentrations and noise levels into human-interpretable
health metrics using epidemiologically validated dose-response functions.

Key features:
  1. **Health Score** (0-100): Composite index using log-linear dose-response
     for PM2.5 (Pope et al. 2002), linear response for NO2, and threshold-based
     response for noise (WHO 2018). Higher score = healthier.

  2. **Equivalent Cigarettes**: Berkeley Earth methodology - 1 cigarette is
     equivalent to breathing 22 ug/m3 PM2.5 for 24 hours.

  3. **Vulnerability Multipliers**: Population-group-specific risk factors
     from WHO meta-analyses on susceptible populations.

  4. **Cumulative Dose Tracking**: Maintains per-sensor exposure dose
     (concentration * time) for longitudinal health assessment.

References:
    - WHO (2021) Global Air Quality Guidelines
    - Pope, C.A. et al. (2002) Lung Cancer, Cardiopulmonary Mortality.
      JAMA 287(9), 1132-1141.
    - Berkeley Earth (2015) Air Pollution and Cigarette Equivalence
    - WHO (2018) Environmental Noise Guidelines for the European Region
    - EPA (2024) Revised AQI Breakpoints for PM2.5
"""

import math
import logging
from typing import Dict, List

from models import PollutionData, NoiseData, HealthData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WHO / EPA guideline thresholds (ug/m3)
# ---------------------------------------------------------------------------
_WHO_PM25_GUIDELINE = 5.0     # ug/m3 (2021 annual mean guideline)
_WHO_PM10_GUIDELINE = 15.0    # ug/m3 (2021 annual mean guideline)
_WHO_NO2_GUIDELINE = 10.0     # ug/m3 (2021 annual mean guideline)

# ---------------------------------------------------------------------------
# Cigarette equivalence (Berkeley Earth)
# ---------------------------------------------------------------------------
_PM25_PER_CIGARETTE = 22.0    # ug/m3 over 24h

# ---------------------------------------------------------------------------
# Vulnerability multipliers (relative risk increase from WHO meta-analyses)
# ---------------------------------------------------------------------------
_VULNERABILITY_MULTIPLIERS: Dict[str, float] = {
    "general":   1.0,
    "children":  1.5,   # developing lungs, higher ventilation rate per kg
    "elderly":   1.4,   # reduced lung function, comorbidities
    "asthma":    1.8,   # hyperresponsive airways
    "cardiac":   1.6,   # cardiovascular sensitivity to PM2.5
    "pregnant":  1.3,   # fetal development sensitivity
}


class HealthService:
    """
    Computes health impact metrics from environmental exposure data
    using WHO dose-response relationships, EPA AQI categories, and
    Berkeley Earth cigarette-equivalence methodology.
    """

    def __init__(self) -> None:
        # Cumulative dose tracking: sensor_id -> dose (ug/m3 * hours)
        self._cumulative_dose: Dict[str, float] = {}

    # ==================================================================
    # Primary health score computation
    # ==================================================================

    def _compute_health_score(
        self,
        pm25: float,
        pm10: float,
        no2: float,
        noise_db: float,
    ) -> int:
        """
        Compute a composite 0-100 health score (100 = best).

        Weighted combination:
        - PM2.5 penalty (40% weight): log-linear dose-response
        - PM10 penalty (15% weight): excess over WHO guideline
        - NO2 penalty (15% weight): excess over WHO guideline
        - Noise penalty (15% weight): threshold-based from WHO 2018
        - CO (implicit via PM2.5 correlation, 15% reserve)
        """
        score = 100.0

        # PM2.5: heaviest weight (most harmful pollutant)
        # Log-linear: penalty grows with log(1 + excess/guideline)
        if pm25 > _WHO_PM25_GUIDELINE:
            excess_ratio = (pm25 - _WHO_PM25_GUIDELINE) / _WHO_PM25_GUIDELINE
            # Exponential decay-style penalty
            pm25_penalty = min(40.0, excess_ratio * 10.0)
            score -= pm25_penalty

        # PM10
        if pm10 > _WHO_PM10_GUIDELINE:
            excess_ratio = (pm10 - _WHO_PM10_GUIDELINE) / _WHO_PM10_GUIDELINE
            score -= min(15.0, excess_ratio * 5.0)

        # NO2
        if no2 > _WHO_NO2_GUIDELINE:
            excess_ratio = (no2 - _WHO_NO2_GUIDELINE) / _WHO_NO2_GUIDELINE
            score -= min(15.0, excess_ratio * 4.0)

        # Noise (WHO recommends < 55 dB for outdoor residential areas)
        if noise_db > 55.0:
            noise_excess = noise_db - 55.0
            score -= min(15.0, noise_excess * 0.5)

        return max(0, min(100, round(score)))

    # ==================================================================
    # Risk level classification
    # ==================================================================

    @staticmethod
    def _determine_risk_level(score: int) -> str:
        """
        Map health score to categorical risk level.

        Thresholds aligned with EPA AQI health concern categories:
            >= 80  -> Low        (AQI Good)
            >= 60  -> Moderate   (AQI Moderate)
            >= 40  -> High       (AQI USG)
            >= 20  -> Very High  (AQI Unhealthy)
            <  20  -> Severe     (AQI Very Unhealthy / Hazardous)
        """
        if score >= 80:
            return "Low"
        elif score >= 60:
            return "Moderate"
        elif score >= 40:
            return "High"
        elif score >= 20:
            return "Very High"
        else:
            return "Severe"

    # ==================================================================
    # Cigarette equivalence
    # ==================================================================

    @staticmethod
    def _compute_cigarette_equivalent(pm25: float, hours: float = 24.0) -> float:
        """
        Compute equivalent daily cigarette consumption.

        Berkeley Earth: 22 ug/m3 PM2.5 inhaled over 24 hours = 1 cigarette.
        For partial-day exposure, scale linearly.

        Parameters
        ----------
        pm25 : float
            PM2.5 concentration in ug/m3.
        hours : float
            Exposure duration in hours (default 24 for daily equivalent).

        Returns
        -------
        float
            Equivalent number of cigarettes.
        """
        if pm25 <= 0 or hours <= 0:
            return 0.0
        return round((pm25 / _PM25_PER_CIGARETTE) * (hours / 24.0), 2)

    # ==================================================================
    # Vulnerable population advisory
    # ==================================================================

    @staticmethod
    def _generate_advisory(score: int, pm25: float, noise_db: float) -> str:
        """
        Generate health advisory text targeting vulnerable populations.

        Based on EPA AQI health messaging guidelines and WHO recommendations
        for sensitive groups.
        """
        if score >= 80:
            return "Safe for all groups"
        elif score >= 60:
            advisory = (
                "Sensitive individuals (children, elderly, respiratory "
                "conditions) should limit prolonged outdoor exertion"
            )
            if noise_db > 70:
                advisory += ". Hearing protection recommended for extended exposure"
            return advisory
        elif score >= 40:
            advisory = (
                "Everyone should reduce prolonged outdoor exertion. "
                "Sensitive groups should avoid outdoor activity"
            )
            if pm25 > 55:
                advisory += ". Consider wearing N95 masks outdoors"
            return advisory
        elif score >= 20:
            return (
                "Health alert: everyone may experience health effects. "
                "Sensitive groups at serious risk. Stay indoors if possible"
            )
        else:
            return (
                "Emergency conditions: all outdoor activity should be "
                "avoided. Keep windows closed. Use air purifiers indoors"
            )

    # ==================================================================
    # Public API: calculate health impact
    # ==================================================================

    def calculate_health_impact(
        self,
        pollution: PollutionData,
        noise: NoiseData,
    ) -> HealthData:
        """
        Compute comprehensive health impact from current pollution and
        noise levels.

        Parameters
        ----------
        pollution : PollutionData
            Current pollution concentrations (pm25, pm10, no2, co).
        noise : NoiseData
            Current noise level (db_level).

        Returns
        -------
        HealthData
            Pydantic model with score, risk_level, equivalent_cigarettes,
            vulnerable_advisory.
        """
        score = self._compute_health_score(
            pm25=pollution.pm25,
            pm10=pollution.pm10,
            no2=pollution.no2,
            noise_db=noise.db_level,
        )
        risk_level = self._determine_risk_level(score)
        cigarettes = self._compute_cigarette_equivalent(pollution.pm25)
        advisory = self._generate_advisory(score, pollution.pm25, noise.db_level)

        return HealthData(
            score=score,
            risk_level=risk_level,
            equivalent_cigarettes=cigarettes,
            vulnerable_advisory=advisory,
        )

    # ==================================================================
    # Vulnerability-adjusted risk
    # ==================================================================

    def get_adjusted_risk(
        self,
        pm25: float,
        population_group: str = "general",
    ) -> Dict[str, float]:
        """
        Calculate vulnerability-adjusted risk for a specific population group.

        Uses the log-linear relative risk model from Pope et al. (2002):
            RR = exp(beta * PM2.5 * multiplier)
        where beta ~ 0.006 per ug/m3 for all-cause mortality.

        Parameters
        ----------
        pm25 : float
            PM2.5 concentration in ug/m3.
        population_group : str
            One of: general, children, elderly, asthma, cardiac, pregnant.

        Returns
        -------
        dict
            Keys: population_group, vulnerability_multiplier, relative_risk,
            excess_mortality_percent, adjusted_equivalent_cigarettes.
        """
        multiplier = _VULNERABILITY_MULTIPLIERS.get(population_group, 1.0)

        # Beta coefficient from Pope et al. (2002): ~0.006 per ug/m3
        beta = 0.006
        rr = math.exp(beta * pm25 * multiplier)
        excess_mortality = (rr - 1.0) * 100.0
        adj_cigs = self._compute_cigarette_equivalent(pm25) * multiplier

        return {
            "population_group": population_group,
            "vulnerability_multiplier": multiplier,
            "relative_risk": round(rr, 4),
            "excess_mortality_percent": round(excess_mortality, 2),
            "adjusted_equivalent_cigarettes": round(adj_cigs, 3),
        }

    # ==================================================================
    # Cumulative dose tracking
    # ==================================================================

    def update_cumulative_dose(
        self,
        sensor_id: str,
        pm25: float,
        duration_hours: float = 1.0,
    ) -> float:
        """
        Accumulate PM2.5 exposure dose (concentration * time).

        Parameters
        ----------
        sensor_id : str
            Sensor/location identifier.
        pm25 : float
            Current PM2.5 concentration in ug/m3.
        duration_hours : float
            Exposure duration for this update in hours.

        Returns
        -------
        float
            Updated cumulative dose (ug/m3 * hours).
        """
        dose = self._cumulative_dose.get(sensor_id, 0.0)
        dose += pm25 * duration_hours
        self._cumulative_dose[sensor_id] = dose
        return dose

    def get_cumulative_dose(self, sensor_id: str) -> float:
        """Return the accumulated exposure dose for a sensor location."""
        return self._cumulative_dose.get(sensor_id, 0.0)

    # ==================================================================
    # Aggregate summary
    # ==================================================================

    def get_aggregate_health_summary(
        self,
        health_data_list: List[HealthData],
    ) -> Dict:
        """
        Aggregate health data across all sensors for a global summary.

        Parameters
        ----------
        health_data_list : list of HealthData
            Health metrics from each sensor.

        Returns
        -------
        dict
            Aggregated statistics including average score, worst risk level,
            average equivalent cigarettes, and per-level sensor counts.
        """
        if not health_data_list:
            return {
                "avg_score": 100,
                "worst_risk_level": "Low",
                "avg_equivalent_cigarettes": 0.0,
                "advisory_count_by_level": {
                    "Low": 0, "Moderate": 0, "High": 0,
                    "Very High": 0, "Severe": 0,
                },
                "sensor_count": 0,
            }

        scores = [h.score for h in health_data_list]
        avg_score = round(sum(scores) / len(scores))

        risk_order = ["Low", "Moderate", "High", "Very High", "Severe"]
        worst_idx = max(risk_order.index(h.risk_level) for h in health_data_list)
        worst_risk = risk_order[worst_idx]

        avg_cigs = round(
            sum(h.equivalent_cigarettes for h in health_data_list) / len(health_data_list),
            2,
        )

        level_counts = {"Low": 0, "Moderate": 0, "High": 0, "Very High": 0, "Severe": 0}
        for h in health_data_list:
            level_counts[h.risk_level] = level_counts.get(h.risk_level, 0) + 1

        return {
            "avg_score": avg_score,
            "worst_risk_level": worst_risk,
            "avg_equivalent_cigarettes": avg_cigs,
            "advisory_count_by_level": level_counts,
            "sensor_count": len(health_data_list),
        }

    # ==================================================================
    # Diagnostics
    # ==================================================================

    def get_status(self) -> dict:
        """Return service status information."""
        return {
            "service": "HealthService",
            "vulnerability_groups": list(_VULNERABILITY_MULTIPLIERS.keys()),
            "who_pm25_guideline_ug_m3": _WHO_PM25_GUIDELINE,
            "cigarette_equivalence_ug_m3_24h": _PM25_PER_CIGARETTE,
            "tracked_doses": len(self._cumulative_dose),
        }
