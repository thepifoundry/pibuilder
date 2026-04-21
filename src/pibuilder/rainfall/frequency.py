"""
Rainfall frequency analysis: 5-distribution fitting with goodness-of-fit selection.

Ground truth: MPSB Rainfall Analysis_China Region.xlsx
Selection rule: among distributions passing BOTH chi-sq and KS tests, return the MAX 100yr RP.
"""

import numpy as np
from scipy import stats
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Distribution(str, Enum):
    LP3 = "LP3"
    GUMBEL = "Gumbel"
    NORMAL = "Normal"
    LOG_NORMAL = "Log Normal"
    PEARSON = "Pearson"


@dataclass
class FitResult:
    distribution: Distribution
    rp_100yr: float
    chi_sq_pass: bool
    ks_pass: bool

    @property
    def both_pass(self) -> bool:
        return self.chi_sq_pass and self.ks_pass


@dataclass
class FrequencyAnalysisResult:
    fits: list[FitResult]
    selected_rp_100yr: float
    selected_method: Distribution
    n: int

    def applicable(self) -> list[FitResult]:
        return [f for f in self.fits if f.both_pass]


def _wilson_hilferty_kt(cs: float, exceedance_prob: float = 0.01) -> float:
    """
    Wilson-Hilferty (1931) exact cube-root formula for Pearson III frequency factor K_T.
    K_T = (2/Cs) * ((1 - Cs²/36 + z·Cs/6)³ - 1)

    Matches Excel to 8 significant figures. The 5-term polynomial expansion is less
    accurate (error up to 0.005 at |Cs| > 1.9).
    """
    z = stats.norm.ppf(1 - exceedance_prob)
    if abs(cs) < 1e-6:
        return float(z)
    inner = 1.0 - cs**2 / 36.0 + z * cs / 6.0
    return (2.0 / cs) * (inner**3 - 1.0)


def _unbiased_skewness(x: np.ndarray) -> float:
    """Sample skewness with n/((n-1)(n-2)) correction — matches Excel SKEW()."""
    n = len(x)
    mu = np.mean(x)
    s = np.std(x, ddof=1)
    return (n / ((n - 1) * (n - 2))) * np.sum(((x - mu) / s) ** 3)


def fit_lp3(data: np.ndarray, exceedance_prob: float = 0.01) -> tuple[float, dict]:
    """Log-Pearson Type III: fit in log space, apply Wilson-Hilferty K_T."""
    y = np.log(data)
    n = len(y)
    mu_y = np.mean(y)
    sigma_y = np.std(y, ddof=1)
    cs = _unbiased_skewness(y)
    kt = _wilson_hilferty_kt(cs, exceedance_prob)
    rp = np.exp(mu_y + kt * sigma_y)
    params = {"mean_ln": mu_y, "std_ln": sigma_y, "cs": cs, "kt": kt,
              "cv": sigma_y / mu_y, "kn": stats.norm.ppf(1 - exceedance_prob)}
    return rp, params


def fit_gumbel(data: np.ndarray, exceedance_prob: float = 0.01) -> tuple[float, dict]:
    """
    Gumbel EV1 (method of moments) using sample std (STDEV / ddof=1).
    K_T = (sqrt(6)/pi) * (y_T - 0.5772)
    """
    mu = np.mean(data)
    sigma = np.std(data, ddof=1)
    T = 1.0 / exceedance_prob
    y_T = -np.log(-np.log(1.0 - 1.0 / T))
    kt = (np.sqrt(6) / np.pi) * (y_T - 0.5772156649)
    rp = mu + kt * sigma
    return rp, {"mean": mu, "std": sigma, "kt": kt, "y_T": y_T}


def fit_normal(data: np.ndarray, exceedance_prob: float = 0.01) -> tuple[float, dict]:
    """Normal distribution: X_T = mean + z_p * std."""
    mu = np.mean(data)
    sigma = np.std(data, ddof=1)
    z = stats.norm.ppf(1 - exceedance_prob)
    rp = mu + z * sigma
    return rp, {"mean": mu, "std": sigma, "z": z}


def fit_lognormal(data: np.ndarray, exceedance_prob: float = 0.01) -> tuple[float, dict]:
    """
    2-parameter Log-Normal: fit in log space using standard normal z (no skew correction).
    Equivalent to LP3 with Cs=0.
    """
    y = np.log(data)
    mu_y = np.mean(y)
    sigma_y = np.std(y, ddof=1)
    z = stats.norm.ppf(1 - exceedance_prob)
    rp = np.exp(mu_y + z * sigma_y)
    return rp, {"mean_ln": mu_y, "std_ln": sigma_y, "z": z}


def fit_pearson(data: np.ndarray, exceedance_prob: float = 0.01) -> tuple[float, dict]:
    """
    Pearson Type III on raw values (not log-transformed).
    Uses Wilson-Hilferty on the raw skewness.
    """
    mu = np.mean(data)
    sigma = np.std(data, ddof=1)
    cs = _unbiased_skewness(data)
    kt = _wilson_hilferty_kt(cs, exceedance_prob)
    rp = mu + kt * sigma
    return rp, {"mean": mu, "std": sigma, "cs": cs, "kt": kt}


_CHI_SQ_BINS_RAW = np.array([50.0, 100.0, 150.0, 200.0, 250.0, 300.0])
_CHI_SQ_BINS_LOG = np.log(_CHI_SQ_BINS_RAW)
_CHI_SQ_CRITICAL = stats.chi2.ppf(0.95, df=2)  # 5.991 — same for all distributions


def _ks_test(data: np.ndarray, cdf_func) -> tuple[bool, float, float]:
    """
    Kolmogorov-Smirnov goodness-of-fit test at alpha=0.05.
    Returns (passes, statistic, critical_value).
    """
    n = len(data)
    stat, _ = stats.kstest(data, cdf_func)
    critical = 1.36 / np.sqrt(n)  # alpha=0.05 critical value
    passes = stat <= critical
    return passes, stat, critical


def _chi_sq_test(data: np.ndarray, cdf_func) -> tuple[bool, float, float]:
    """
    Chi-square goodness-of-fit test matching MPSB Excel.

    Fixed bins [50, 100, 150, 200, 250, 300] mm. CDF functions handle any
    log transform internally, so raw data and raw bins work for all distributions.
    df=2, critical=5.991 for all distributions.
    Returns (passes, statistic, critical_value).
    """
    n = len(data)
    bins = _CHI_SQ_BINS_RAW

    # Observed: count raw data in each bin
    observed = np.array([
        np.sum((data >= bins[i]) & (data < bins[i + 1]))
        for i in range(len(bins) - 1)
    ], dtype=float)

    # Expected: n * P(bins[i] <= X < bins[i+1]) from theoretical CDF
    expected = n * np.array([
        cdf_func(bins[i + 1]) - cdf_func(bins[i])
        for i in range(len(bins) - 1)
    ])

    # Chi-sq: any bin with exp=0 and obs>0 → infinity (force fail)
    chi2_stat = 0.0
    for o, e in zip(observed, expected):
        if e <= 0.0:
            if o > 0:
                chi2_stat = np.inf
                break
        else:
            chi2_stat += (o - e) ** 2 / e

    passes = chi2_stat <= _CHI_SQ_CRITICAL
    return passes, chi2_stat, _CHI_SQ_CRITICAL


def run_frequency_analysis(
    data: np.ndarray,
    exceedance_prob: float = 0.01,
) -> FrequencyAnalysisResult:
    """
    Fit 5 distributions, run chi-sq + KS tests, select max RP among passing distributions.
    This replicates the MPSB Excel 'summary' sheet logic exactly.
    """
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)

    fits = []

    dist_funcs = [
        (Distribution.LP3, fit_lp3, _make_lp3_cdf),
        (Distribution.GUMBEL, fit_gumbel, _make_gumbel_cdf),
        (Distribution.NORMAL, fit_normal, _make_normal_cdf),
        (Distribution.LOG_NORMAL, fit_lognormal, _make_lognormal_cdf),
        (Distribution.PEARSON, fit_pearson, _make_pearson_cdf),
    ]

    for dist_name, fit_fn, cdf_factory in dist_funcs:
        try:
            rp, params = fit_fn(data, exceedance_prob)
            cdf = cdf_factory(data, params)
            ks_pass, _, _ = _ks_test(data, cdf)
            chi_pass, _, _ = _chi_sq_test(data, cdf)
            fits.append(FitResult(dist_name, rp, chi_pass, ks_pass))
        except Exception:
            fits.append(FitResult(dist_name, float("nan"), False, False))

    applicable = [f for f in fits if f.both_pass and not np.isnan(f.rp_100yr)]

    if applicable:
        best = max(applicable, key=lambda f: f.rp_100yr)
    else:
        # Fallback: use LP3 if no distribution passes both tests
        lp3 = next(f for f in fits if f.distribution == Distribution.LP3)
        best = lp3

    return FrequencyAnalysisResult(
        fits=fits,
        selected_rp_100yr=best.rp_100yr,
        selected_method=best.distribution,
        n=n,
    )


# CDF factories — each returns a callable cdf(x) -> probability

def _make_lp3_cdf(data: np.ndarray, params: dict):
    mu_y, sigma_y, cs = params["mean_ln"], params["std_ln"], params["cs"]
    # LP3 in log space = Pearson III on log values
    # Use scipy pearson3 parameterization: shape=skew, loc, scale
    if abs(cs) < 1e-6:
        return lambda x: stats.norm.cdf(np.log(x), loc=mu_y, scale=sigma_y)
    # Wilson-Hilferty: convert to gamma
    alpha = 4.0 / (cs ** 2)
    beta_scale = sigma_y * abs(cs) / 2.0
    xi = mu_y - 2.0 * sigma_y / cs
    if cs > 0:
        return lambda x: stats.gamma.cdf((np.log(x) - xi) / beta_scale, a=alpha)
    else:
        return lambda x: 1 - stats.gamma.cdf((np.log(x) - xi) / (-beta_scale), a=alpha)


def _make_gumbel_cdf(data: np.ndarray, params: dict):
    mu, sigma = params["mean"], params["std"]  # sigma already computed with correct ddof
    alpha = np.pi / (sigma * np.sqrt(6))
    u = mu - 0.5772156649 / alpha
    return lambda x: np.exp(-np.exp(-alpha * (x - u)))


def _make_normal_cdf(data: np.ndarray, params: dict):
    mu, sigma = params["mean"], params["std"]
    return lambda x: stats.norm.cdf(x, loc=mu, scale=sigma)


def _make_lognormal_cdf(data: np.ndarray, params: dict):
    mu_y, sigma_y = params["mean_ln"], params["std_ln"]
    return lambda x: stats.norm.cdf(np.log(x), loc=mu_y, scale=sigma_y)


def _make_pearson_cdf(data: np.ndarray, params: dict):
    mu, sigma, cs = params["mean"], params["std"], params["cs"]
    if abs(cs) < 1e-6:
        return lambda x: stats.norm.cdf(x, loc=mu, scale=sigma)
    alpha = 4.0 / (cs ** 2)
    beta_scale = sigma * abs(cs) / 2.0
    xi = mu - 2.0 * sigma / cs
    if cs > 0:
        return lambda x: stats.gamma.cdf((x - xi) / beta_scale, a=alpha)
    else:
        return lambda x: 1 - stats.gamma.cdf((x - xi) / (-beta_scale), a=alpha)
