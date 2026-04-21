"""
Rainfall intensity computation for EPC hydrology design.

Two workflows are supported:

1. **Grid-based (MPSB)**
   Satellite-derived annual-maximum daily rainfall at 0.25° grid points is
   processed by ``frequency.run_frequency_analysis`` to produce a 100-year
   return-period rainfall depth (mm) at each node.  That depth is the input
   to the Rational Method discharge calculation.

2. **Gauge-based (Indargarh)**
   At stations with a long record of daily maxima, Gumbel EV1 is fitted
   to the annual-maximum series at each target return period.  The resulting
   24-hour rainfall is then scaled to sub-daily durations using the CWC
   (Central Water Commission, India) power-law:

       P_t = P_24 × (t / 24)^(1/3)     (mm)
       I_t = P_t / t                    (mm/hr)

   where t is the duration in hours.

Ground truth
------------
Indargarh gauge station: "Rainfall Analysis" sheet, rows 53-57.
Tolerance: 0.001 mm/hr for all duration × return-period combinations.
"""

import numpy as np
from .frequency import fit_gumbel


STANDARD_DURATIONS_HR = [1, 2, 6, 12, 24]


def duration_rainfall(p_24: float, duration_hr: float) -> float:
    """Scale 24-hour rainfall to a shorter duration using the CWC power-law.

    Formula
    -------
        P_t = P_24 × (t / 24)^(1/3)

    The exponent 1/3 is the Indian standard (CWC) value used throughout the
    MPSB project.  Other regions use different exponents (e.g. 0.25 for some
    European standards) — do not change without explicit SME approval.

    Parameters
    ----------
    p_24 : float
        24-hour rainfall depth in mm (e.g. the Gumbel T-year value).
    duration_hr : float
        Target duration in hours (e.g. 1, 2, 6, 12, 24).

    Returns
    -------
    float
        Rainfall depth for the target duration in mm.
    """
    return p_24 * (duration_hr / 24.0) ** (1.0 / 3.0)


def duration_intensity(p_24: float, duration_hr: float) -> float:
    """Compute average rainfall intensity for a given storm duration.

    Calls duration_rainfall to get P_t and divides by the duration.

    Parameters
    ----------
    p_24 : float
        24-hour rainfall depth in mm.
    duration_hr : float
        Storm duration in hours.

    Returns
    -------
    float
        Average rainfall intensity in mm/hr.
    """
    return duration_rainfall(p_24, duration_hr) / duration_hr


def gumbel_intensity_table(
    annual_max_daily: np.ndarray,
    return_periods: list[int] = None,
    durations_hr: list[float] = None,
) -> dict:
    """Build a complete intensity–duration–frequency (IDF) table using Gumbel EV1.

    For each duration, derives a per-duration intensity series from the 24-hour
    annual-maximum record, fits Gumbel to that series, and returns the T-year
    intensity in mm/hr.  This replicates the Indargarh "Rainfall Analysis" sheet.

    Procedure
    ---------
    1. For each annual-maximum 24-hour value P_24 in the record, compute the
       corresponding intensity series for each target duration using
       duration_intensity(P_24, dur).
    2. Fit Gumbel (method of moments) to each duration's intensity series.
    3. Return the T-year intensity for each duration.

    Parameters
    ----------
    annual_max_daily : np.ndarray
        Annual-maximum daily (24-hour) rainfall depths in mm.
        NaN values are dropped before fitting.
    return_periods : list[int], optional
        Target return periods in years.  Defaults to [2, 5, 10, 50, 100].
    durations_hr : list[float], optional
        Storm durations in hours.  Defaults to [1, 2, 6, 12, 24].

    Returns
    -------
    dict[float, dict[int, float]]
        Nested dict: results[duration_hr][return_period] = intensity_mm_hr.
        Example: results[1][100] = 83.729 (1-hour 100-year intensity, mm/hr).
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
    """Fit Gumbel EV1 to daily annual maxima and return the T-year 24-hour rainfall.

    Convenience wrapper around fit_gumbel for the common case where only the
    24-hour design rainfall depth is needed (e.g. as input to the Rational Method).

    Parameters
    ----------
    annual_max_daily : np.ndarray
        Annual-maximum daily (24-hour) rainfall depths in mm.
    return_period : int, default 100
        Return period in years.

    Returns
    -------
    float
        T-year 24-hour design rainfall depth in mm.
    """
    data = np.asarray(annual_max_daily, dtype=float)
    rp, _ = fit_gumbel(data, exceedance_prob=1.0 / return_period)
    return rp
