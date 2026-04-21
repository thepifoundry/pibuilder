"""
Rainfall intensity computation.

Two workflows:
1. Grid-based (MPSB): annual max rainfall at each grid point → frequency analysis → 100yr RP (mm)
2. Gauge-based (Indargarh): daily annual max → Gumbel → duration scaling → intensity (mm/hr)

Duration scaling (CWC/Indian standard):
    P_t = P_24 * (t / 24)^(1/3)   where t is duration in hours
    Intensity_t = P_t / t          (mm/hr)
"""

import numpy as np
from .frequency import fit_gumbel


STANDARD_DURATIONS_HR = [1, 2, 6, 12, 24]


def duration_rainfall(p_24: float, duration_hr: float) -> float:
    """CWC duration scaling: P_t = P_24 * (t/24)^(1/3)."""
    return p_24 * (duration_hr / 24.0) ** (1.0 / 3.0)


def duration_intensity(p_24: float, duration_hr: float) -> float:
    """Rainfall intensity in mm/hr for given duration."""
    return duration_rainfall(p_24, duration_hr) / duration_hr


def gumbel_intensity_table(
    annual_max_daily: np.ndarray,
    return_periods: list[int] = None,
    durations_hr: list[float] = None,
) -> dict:
    """
    Gauge-based analysis using Gumbel distribution (Indargarh workflow).

    Returns a dict keyed by duration (hr) → {return_period: intensity_mm_hr}.
    """
    if return_periods is None:
        return_periods = [2, 5, 10, 50, 100]
    if durations_hr is None:
        durations_hr = STANDARD_DURATIONS_HR

    data = np.asarray(annual_max_daily, dtype=float)
    data = data[~np.isnan(data)]

    # Compute intensity series for each duration
    results: dict[float, dict[int, float]] = {}
    for dur in durations_hr:
        intensity_series = np.array([duration_intensity(p, dur) for p in data])
        period_intensities = {}
        for T in return_periods:
            rp, _ = fit_gumbel(intensity_series, exceedance_prob=1.0 / T)
            period_intensities[T] = rp
        results[dur] = period_intensities

    return results


def gumbel_p24_for_return_period(
    annual_max_daily: np.ndarray,
    return_period: int = 100,
) -> float:
    """
    Fit Gumbel to daily annual maxima, return P_24 for given return period (mm).
    Used when only the 24hr design rainfall is needed (feeds into Rational Method).
    """
    data = np.asarray(annual_max_daily, dtype=float)
    rp, _ = fit_gumbel(data, exceedance_prob=1.0 / return_period)
    return rp
