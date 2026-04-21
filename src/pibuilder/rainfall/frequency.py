"""
Rainfall frequency analysis engine.

Fits five probability distributions to a sample of annual-maximum daily rainfall
values and selects the design rainfall using a two-test goodness-of-fit procedure.

Ground truth
------------
MPSB Rainfall Analysis_China Region.xlsx.  Each distribution has its own sheet
(e.g. "log pearson (ks test)", "gumbel (ks test)").  The "summary" sheet holds
the final selected 100-year return-period (RP) values used for project design.

Distributions fitted
--------------------
1. Log-Pearson Type III (LP3) — log-space Pearson III via Wilson-Hilferty K_T
2. Gumbel EV1               — method of moments, K_T = (√6/π)(y_T − 0.5772)
3. Normal                   — X_T = μ + z·σ
4. Log-Normal (2-parameter) — LP3 with Cs = 0 (no skew correction)
5. Pearson Type III         — same as LP3 but fit on raw data, not log-transformed

Selection rule
--------------
Among distributions that pass *both* chi-square and Kolmogorov-Smirnov tests,
return the one with the highest 100-year RP.  If no distribution passes both
tests, fall back to LP3 (replicates Excel behaviour).

Test parameters
---------------
- Chi-square: fixed bins [50, 100, 150, 200, 250, 300] mm, df = 2,
  critical value = chi2.ppf(0.95, 2) ≈ 5.991.  Same for all distributions.
- KS test: critical value = 1.36 / √n  (alpha = 0.05 large-sample approximation).

Known Excel bugs (not replicated here)
---------------------------------------
- Gumbel sheet column 1: uses STDEVP (population std, ddof=0) instead of STDEV.
  Our implementation uses ddof=1 everywhere.
- Chi-sq FREQUENCY formula: columns 2-334 reference rows 15-34 instead of 11-30,
  contaminating observed counts with statistical summary rows.  Causes 17
  selection discrepancies documented in KNOWN_EXCEL_CHISQ_BUG_POINTS.
See docs/rainfall-engine-bugs.md for full evidence and impact analysis.
"""

import numpy as np
from scipy import stats
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Distribution(str, Enum):
    """Enumeration of supported probability distributions.

    Values match the column headers in the MPSB Excel summary sheet so they
    can be used directly in output reports and fixture comparisons.
    """

    LP3 = "LP3"
    GUMBEL = "Gumbel"
    NORMAL = "Normal"
    LOG_NORMAL = "Log Normal"
    PEARSON = "Pearson"


@dataclass
class FitResult:
    """Result of fitting a single probability distribution to the rainfall sample.

    Attributes
    ----------
    distribution : Distribution
        Which distribution was fitted.
    rp_100yr : float
        100-year return-period rainfall depth in mm.  NaN if the fit failed
        (e.g. numerical error in log-space for zero or negative data).
    chi_sq_pass : bool
        True if the chi-square statistic is ≤ the critical value (5.991).
    ks_pass : bool
        True if the KS statistic is ≤ 1.36/√n.
    """

    distribution: Distribution
    rp_100yr: float
    chi_sq_pass: bool
    ks_pass: bool

    @property
    def both_pass(self) -> bool:
        """True when the distribution passes both goodness-of-fit tests."""
        return self.chi_sq_pass and self.ks_pass


@dataclass
class FrequencyAnalysisResult:
    """Full result of running the five-distribution frequency analysis.

    Attributes
    ----------
    fits : list[FitResult]
        One entry per distribution in fitting order (LP3, Gumbel, Normal,
        Log-Normal, Pearson III).
    selected_rp_100yr : float
        The design 100-year RP in mm — max RP over passing distributions,
        or the LP3 value if no distribution passes both tests.
    selected_method : Distribution
        Which distribution produced selected_rp_100yr.
    n : int
        Number of non-NaN data values used in the analysis.
    """

    fits: list[FitResult]
    selected_rp_100yr: float
    selected_method: Distribution
    n: int

    def applicable(self) -> list[FitResult]:
        """Return the subset of fits that pass both chi-sq and KS tests."""
        return [f for f in self.fits if f.both_pass]


def _wilson_hilferty_kt(cs: float, exceedance_prob: float = 0.01) -> float:
    """Compute the Pearson III frequency factor K_T via the Wilson-Hilferty (1931) transformation.

    Uses the exact cube-root form, NOT the 5-term polynomial expansion found in
    some textbooks.  The polynomial diverges from the exact result by up to 0.005
    when |Cs| > ~1.9, translating to ~0.17 mm error in the final RP — above the
    0.01 mm test tolerance.  Excel uses the exact formula; so do we.

    Formula
    -------
        z = norm.ppf(1 - p)                     # standard normal deviate
        K_T = (2/Cs) × [(1 − Cs²/36 + z·Cs/6)³ − 1]

    When |Cs| < 1e-6 the distribution collapses to Normal, so K_T = z.

    Parameters
    ----------
    cs : float
        Coefficient of skewness (sample, unbiased — see _unbiased_skewness).
        Computed in log space for LP3, raw space for Pearson III.
    exceedance_prob : float, default 0.01
        Annual exceedance probability.  0.01 → 100-year return period.

    Returns
    -------
    float
        Dimensionless frequency factor K_T.

    References
    ----------
    Wilson & Hilferty (1931).  "The distribution of chi-square."
    PNAS 17(12): 684-688.
    """
    z = stats.norm.ppf(1 - exceedance_prob)
    if abs(cs) < 1e-6:
        return float(z)
    inner = 1.0 - cs**2 / 36.0 + z * cs / 6.0
    return (2.0 / cs) * (inner**3 - 1.0)


def _unbiased_skewness(x: np.ndarray) -> float:
    """Compute the unbiased sample skewness coefficient (Cs).

    Uses the n / ((n-1)(n-2)) correction factor, which matches Excel's SKEW()
    function exactly.  This is the standard "Fisher-corrected" skewness, not
    the biased moment estimator.

    Formula
    -------
        Cs = [n / ((n-1)(n-2))] × Σ((xᵢ - x̄) / s)³

    where s is the sample standard deviation (ddof=1).

    Parameters
    ----------
    x : np.ndarray
        1-D array of data values.  For LP3 this is log-transformed rainfall;
        for Pearson III it is raw rainfall in mm.

    Returns
    -------
    float
        Unbiased sample skewness (dimensionless).
    """
    n = len(x)
    mu = np.mean(x)
    s = np.std(x, ddof=1)
    return (n / ((n - 1) * (n - 2))) * np.sum(((x - mu) / s) ** 3)


def fit_lp3(data: np.ndarray, exceedance_prob: float = 0.01) -> tuple[float, dict]:
    """Fit the Log-Pearson Type III distribution and compute the design rainfall.

    Transforms data to log space, then fits a Pearson III distribution using
    the method of moments (mean, standard deviation, skewness coefficient).
    The T-year quantile is computed via the Wilson-Hilferty K_T factor.

    Formula
    -------
        y = ln(X)
        ln(X_T) = ȳ + K_T × s_y
        X_T = exp(ln(X_T))

    where K_T is the Wilson-Hilferty frequency factor for the skewness Cs
    of the log-transformed series.

    Matches the MPSB "log pearson (ks test)" sheet exactly for all 334 grid
    points at the 0.01 mm tolerance level.

    Parameters
    ----------
    data : np.ndarray
        Annual-maximum daily rainfall values in mm (raw, not log-transformed).
        Must be strictly positive (log-transform will fail for zero/negative).
    exceedance_prob : float, default 0.01
        Annual exceedance probability.  0.01 → 100-year RP.

    Returns
    -------
    rp : float
        T-year return-period rainfall depth in mm.
    params : dict
        Intermediate parameters for diagnostics and CDF construction:
        - mean_ln  : mean of log-transformed values
        - std_ln   : standard deviation of log-transformed values (ddof=1)
        - cs       : skewness coefficient of log-transformed values
        - kt       : Wilson-Hilferty frequency factor
        - cv       : coefficient of variation in log space (std_ln / mean_ln)
        - kn       : standard normal deviate z (= norm.ppf(1 - p))
    """
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
    """Fit the Gumbel Extreme Value Type I (EV1) distribution by method of moments.

    The Gumbel distribution is widely used for annual maximum series.  The method
    of moments estimator expresses the T-year quantile in terms of the sample mean
    and standard deviation:

    Formula
    -------
        y_T = -ln(-ln(1 - 1/T))          # reduced variate
        K_T = (√6 / π) × (y_T − 0.5772) # frequency factor (Euler-Mascheroni)
        X_T = μ + K_T × σ

    Standard deviation uses ddof=1 (Excel STDEV).  The first column of the MPSB
    Gumbel sheet incorrectly uses STDEVP (ddof=0) — that is a known Excel bug
    and is NOT replicated here.  See docs/rainfall-engine-bugs.md Bug 1.

    Parameters
    ----------
    data : np.ndarray
        Annual-maximum daily rainfall values in mm.
    exceedance_prob : float, default 0.01
        Annual exceedance probability.  0.01 → 100-year RP.

    Returns
    -------
    rp : float
        T-year return-period rainfall depth in mm.
    params : dict
        Intermediate parameters:
        - mean  : sample mean (mm)
        - std   : sample standard deviation, ddof=1 (mm)
        - kt    : Gumbel frequency factor (dimensionless)
        - y_T   : Gumbel reduced variate at return period T
    """
    mu = np.mean(data)
    sigma = np.std(data, ddof=1)
    T = 1.0 / exceedance_prob
    y_T = -np.log(-np.log(1.0 - 1.0 / T))
    kt = (np.sqrt(6) / np.pi) * (y_T - 0.5772156649)
    rp = mu + kt * sigma
    return rp, {"mean": mu, "std": sigma, "kt": kt, "y_T": y_T}


def fit_normal(data: np.ndarray, exceedance_prob: float = 0.01) -> tuple[float, dict]:
    """Fit a Normal distribution by method of moments.

    Formula
    -------
        X_T = μ + z_p × σ

    where z_p = norm.ppf(1 - p) is the standard normal deviate.

    Parameters
    ----------
    data : np.ndarray
        Annual-maximum daily rainfall values in mm.
    exceedance_prob : float, default 0.01
        Annual exceedance probability.

    Returns
    -------
    rp : float
        T-year return-period rainfall depth in mm.
    params : dict
        - mean : sample mean (mm)
        - std  : sample standard deviation, ddof=1 (mm)
        - z    : standard normal deviate
    """
    mu = np.mean(data)
    sigma = np.std(data, ddof=1)
    z = stats.norm.ppf(1 - exceedance_prob)
    rp = mu + z * sigma
    return rp, {"mean": mu, "std": sigma, "z": z}


def fit_lognormal(data: np.ndarray, exceedance_prob: float = 0.01) -> tuple[float, dict]:
    """Fit a 2-parameter Log-Normal distribution by method of moments.

    Identical to LP3 with skewness Cs = 0 (no skew correction in log space).
    The standard normal deviate z replaces the Wilson-Hilferty K_T.

    Formula
    -------
        y = ln(X)
        ln(X_T) = ȳ + z × s_y
        X_T = exp(ln(X_T))

    Parameters
    ----------
    data : np.ndarray
        Annual-maximum daily rainfall values in mm (must be strictly positive).
    exceedance_prob : float, default 0.01
        Annual exceedance probability.

    Returns
    -------
    rp : float
        T-year return-period rainfall depth in mm.
    params : dict
        - mean_ln : mean of log-transformed values
        - std_ln  : standard deviation of log-transformed values (ddof=1)
        - z       : standard normal deviate
    """
    y = np.log(data)
    mu_y = np.mean(y)
    sigma_y = np.std(y, ddof=1)
    z = stats.norm.ppf(1 - exceedance_prob)
    rp = np.exp(mu_y + z * sigma_y)
    return rp, {"mean_ln": mu_y, "std_ln": sigma_y, "z": z}


def fit_pearson(data: np.ndarray, exceedance_prob: float = 0.01) -> tuple[float, dict]:
    """Fit a Pearson Type III distribution on raw (non-log) rainfall values.

    Structurally identical to LP3, but the statistics (mean, std, skewness) are
    computed on the raw data rather than on the log-transformed series.

    Formula
    -------
        X_T = μ + K_T × σ

    where K_T is the Wilson-Hilferty frequency factor for the skewness Cs of
    the raw series.

    Parameters
    ----------
    data : np.ndarray
        Annual-maximum daily rainfall values in mm.
    exceedance_prob : float, default 0.01
        Annual exceedance probability.

    Returns
    -------
    rp : float
        T-year return-period rainfall depth in mm.
    params : dict
        - mean : sample mean (mm)
        - std  : sample standard deviation, ddof=1 (mm)
        - cs   : unbiased skewness of raw values
        - kt   : Wilson-Hilferty frequency factor
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
    """Run a one-sample Kolmogorov-Smirnov goodness-of-fit test.

    Uses the large-sample alpha=0.05 critical value 1.36/√n, which matches
    the MPSB Excel KS-test columns.  scipy.stats.kstest provides the statistic;
    we compute our own critical value rather than using scipy's p-value so that
    the pass/fail boundary is identical to Excel.

    Parameters
    ----------
    data : np.ndarray
        Observed sample (raw rainfall in mm for all distributions).
    cdf_func : callable
        Theoretical CDF: cdf_func(x) → probability in [0, 1].
        CDF functions must handle any log-transform internally.

    Returns
    -------
    passes : bool
        True if stat ≤ critical (distribution is not rejected at 5% level).
    stat : float
        KS test statistic D = max|F_n(x) - F(x)|.
    critical : float
        Critical value = 1.36 / √n.
    """
    n = len(data)
    stat, _ = stats.kstest(data, cdf_func)
    critical = 1.36 / np.sqrt(n)  # alpha=0.05 critical value
    passes = stat <= critical
    return passes, stat, critical


def _chi_sq_test(data: np.ndarray, cdf_func) -> tuple[bool, float, float]:
    """Run a chi-square goodness-of-fit test matching the MPSB Excel methodology.

    Excel uses five fixed rainfall bins: [50, 100), [100, 150), [150, 200),
    [200, 250), [250, 300) mm.  Values outside this range are not counted (they
    land in the implicit tails and are excluded — matching the Excel FREQUENCY
    formula behaviour).  Degrees of freedom is fixed at 2 for all distributions,
    giving a critical value of chi2.ppf(0.95, 2) ≈ 5.991.

    The CDF functions passed here handle all internal log-transforms, so raw
    data and raw bin edges work unchanged for every distribution.

    Known Excel bug (NOT replicated)
    ---------------------------------
    In the MPSB file, the FREQUENCY() formula in all chi-sq sheets uses rows
    15–34 instead of rows 11–30 for columns 2–334.  This mixes 16 data years
    with 4 statistical summary rows (mean, std, Kn, Cs).  Our implementation
    always uses all n data values.  See docs/rainfall-engine-bugs.md Bug 2.

    Parameters
    ----------
    data : np.ndarray
        Observed sample (raw rainfall in mm).
    cdf_func : callable
        Theoretical CDF: cdf_func(x) → probability.

    Returns
    -------
    passes : bool
        True if chi2_stat ≤ 5.991.
    chi2_stat : float
        Chi-square statistic.  Set to infinity if any bin has expected=0
        but observed>0.
    critical : float
        Critical value ≈ 5.991 (chi2.ppf(0.95, df=2)).
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
    """Fit five distributions, run goodness-of-fit tests, and select the design rainfall.

    This is the top-level entry point.  It replicates the logic of the MPSB Excel
    "summary" sheet: for each grid point, Excel runs all five distributions, marks
    each as passing or failing both tests, then records the maximum RP among passing
    distributions as the "Selected Final 100yr RP".

    Fitting order: LP3 → Gumbel → Normal → Log-Normal → Pearson III.
    This order matches the column order in the MPSB summary sheet and is
    preserved in FrequencyAnalysisResult.fits.

    Selection rule
    --------------
    1. Collect all distributions where both chi_sq_pass and ks_pass are True.
    2. If any pass, return the one with the highest rp_100yr.
    3. If none pass, return LP3 as fallback (matches Excel behaviour).

    Errors in individual distribution fits (e.g. log of non-positive data) are
    caught silently; the fit is recorded as failed with rp_100yr=NaN.

    Parameters
    ----------
    data : np.ndarray
        Annual-maximum daily rainfall values in mm.  NaN values are dropped.
        Should have at least 10 values for meaningful statistics.
    exceedance_prob : float, default 0.01
        Annual exceedance probability.  0.01 → 100-year RP.

    Returns
    -------
    FrequencyAnalysisResult
        Contains all five FitResult objects plus the selected RP and method.
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


# CDF factories — each returns a callable cdf(x) -> probability in [0, 1].
# These are passed to _ks_test and _chi_sq_test which always work in raw mm space.
# Each factory performs any required transform (e.g. log) internally.

def _make_lp3_cdf(data: np.ndarray, params: dict):
    """Return the LP3 CDF as a function of raw rainfall x (mm).

    In log space the LP3 is a Pearson III, which maps to a Gamma distribution
    via the Wilson-Hilferty parameterisation:
        alpha = 4 / Cs²    (shape)
        beta  = σ_y |Cs| / 2    (scale)
        xi    = μ_y − 2σ_y / Cs (location / lower bound)

    For negative skewness the distribution is reflected (upper-bounded Gamma).
    When |Cs| < 1e-6 it collapses to Log-Normal.
    """
    mu_y, sigma_y, cs = params["mean_ln"], params["std_ln"], params["cs"]
    if abs(cs) < 1e-6:
        return lambda x: stats.norm.cdf(np.log(x), loc=mu_y, scale=sigma_y)
    alpha = 4.0 / (cs ** 2)
    beta_scale = sigma_y * abs(cs) / 2.0
    xi = mu_y - 2.0 * sigma_y / cs
    if cs > 0:
        return lambda x: stats.gamma.cdf((np.log(x) - xi) / beta_scale, a=alpha)
    else:
        return lambda x: 1 - stats.gamma.cdf((np.log(x) - xi) / (-beta_scale), a=alpha)


def _make_gumbel_cdf(data: np.ndarray, params: dict):
    """Return the Gumbel EV1 CDF as a function of raw rainfall x (mm).

    Scale parameter alpha and location parameter u are derived from the sample
    mean and standard deviation (ddof=1):
        alpha = π / (σ √6)
        u     = μ − 0.5772 / alpha
    CDF: F(x) = exp(−exp(−alpha·(x − u)))
    """
    mu, sigma = params["mean"], params["std"]
    alpha = np.pi / (sigma * np.sqrt(6))
    u = mu - 0.5772156649 / alpha
    return lambda x: np.exp(-np.exp(-alpha * (x - u)))


def _make_normal_cdf(data: np.ndarray, params: dict):
    """Return the Normal CDF as a function of raw rainfall x (mm)."""
    mu, sigma = params["mean"], params["std"]
    return lambda x: stats.norm.cdf(x, loc=mu, scale=sigma)


def _make_lognormal_cdf(data: np.ndarray, params: dict):
    """Return the Log-Normal CDF as a function of raw rainfall x (mm).

    Applies log-transform internally: F(x) = Φ((ln x − μ_y) / σ_y).
    """
    mu_y, sigma_y = params["mean_ln"], params["std_ln"]
    return lambda x: stats.norm.cdf(np.log(x), loc=mu_y, scale=sigma_y)


def _make_pearson_cdf(data: np.ndarray, params: dict):
    """Return the Pearson Type III CDF as a function of raw rainfall x (mm).

    Same Gamma parameterisation as _make_lp3_cdf but operating in raw mm space
    rather than log space.  When |Cs| < 1e-6 it collapses to Normal.
    """
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
