# Rainfall Frequency Analysis — Engine Specification

**Module:** `src/pibuilder/rainfall/frequency.py`, `src/pibuilder/rainfall/intensity.py`
**Ground truth:** `docs/ricalcs/MPSB Rainfall Analysis_China Region.xlsx`, `docs/ricalcs/Indargarh Rainfall Analysis.xlsx`
**Test suite:** `tests/test_rainfall_lp3.py`, `tests/test_rainfall_gumbel.py`, `tests/test_rainfall_selection.py`
**Tolerance:** 0.01 mm for individual distribution RPs; 0.5 mm for selected RP.

---

## 1. Purpose

The rainfall frequency analysis engine estimates the **100-year return-period daily rainfall depth** (mm) at any point in the project catchment. This depth is the primary input to the Rational Method peak discharge calculation.

Two data workflows are supported:

| Workflow | Source | Output |
|----------|--------|--------|
| Grid-based (MPSB) | Satellite annual-maximum daily rainfall at 334 × 0.25° grid nodes | 100-year RP depth (mm) per node |
| Gauge-based (Indargarh) | 32-year rain gauge record at a single station | Full IDF table: mm/hr × 5 durations × 5 return periods |

---

## 2. Input Data

### 2.1 MPSB Satellite Grid

- **Source:** Multi-Purpose Satellite-Based product, China Meteorological Administration regional reanalysis.
- **Coverage:** 27.875°–31.125°N, 82.125°–95.625°E (Himalayan region).
- **Resolution:** 0.25° latitude × 0.25° longitude (~28 km node spacing, 334 nodes total).
- **Record:** 20 years of annual-maximum daily rainfall (2000–2019), in mm.
- **Stored in:** `tests/fixtures/mpsb_grid_data.json` (extracted from Excel, 334 points × 20 values).

### 2.2 Indargarh Gauge Station

- **Record:** 32 annual-maximum daily rainfall values (1990–2021), in mm.
- **Stored in:** `tests/fixtures/indargarh_daily_max.json`.

---

## 3. Probability Distributions Fitted

The engine fits five distributions by the **method of moments** — parameters are estimated directly from the sample mean, standard deviation, and skewness. No maximum-likelihood fitting is used; this matches the Excel methodology exactly.

### 3.1 Log-Pearson Type III (LP3)

The standard distribution for flood-frequency analysis in Indian hydrology (IS:5477 Part 4, CWC guidelines).

**Procedure:**

1. Transform the sample to log space: $y_i = \ln(x_i)$
2. Compute moments in log space:
   $$\bar{y} = \frac{1}{n}\sum y_i, \quad s_y = \sqrt{\frac{\sum(y_i-\bar{y})^2}{n-1}}, \quad C_s = \frac{n}{(n-1)(n-2)} \sum\left(\frac{y_i-\bar{y}}{s_y}\right)^3$$
3. Compute the frequency factor $K_T$ via the Wilson-Hilferty transformation (see §4).
4. Back-transform: $X_T = \exp(\bar{y} + K_T \cdot s_y)$

**References:**
- Kite, G.W. (1977). *Frequency and Risk Analysis in Hydrology*. Water Resources Publications, Fort Collins.
- IS:5477 Part 4 (1971). *Methods for Fixing the Capacities of Reservoirs — Flood Estimation*. Bureau of Indian Standards.

### 3.2 Gumbel Extreme Value Type I (EV1)

Widely used for annual-maximum series; the asymptotic distribution of the maximum of a large sample of i.i.d. random variables.

**Procedure:**

1. Compute sample mean $\bar{x}$ and standard deviation $s$ (ddof=1).
2. Compute the reduced variate for return period $T$:
   $$y_T = -\ln\!\left(-\ln\!\left(1 - \frac{1}{T}\right)\right)$$
3. Compute the frequency factor:
   $$K_T = \frac{\sqrt{6}}{\pi}(y_T - 0.5772)$$
4. Design rainfall: $X_T = \bar{x} + K_T \cdot s$

The constant 0.5772 is the Euler-Mascheroni constant $\gamma \approx 0.57721566$.

**References:**
- Gumbel, E.J. (1958). *Statistics of Extremes*. Columbia University Press, New York.
- Chow, V.T., Maidment, D.R., Mays, L.W. (1988). *Applied Hydrology*. McGraw-Hill, New York. Chapter 12.

### 3.3 Normal Distribution

$$X_T = \bar{x} + z_p \cdot s$$

where $z_p = \Phi^{-1}(1-p)$ is the standard normal deviate and $p = 1/T$ is the annual exceedance probability.

Used as a reference case. Rarely selected for high-skewness Himalayan data.

### 3.4 Log-Normal (2-parameter)

Equivalent to LP3 with $C_s = 0$ — no skewness correction in log space:

$$X_T = \exp(\bar{y} + z_p \cdot s_y)$$

where $\bar{y}$ and $s_y$ are the mean and standard deviation of $\ln(x)$.

**References:**
- Chow, V.T. (1954). "The log-probability law and its engineering applications." *Proc. ASCE*, 80(536).

### 3.5 Pearson Type III

Structurally identical to LP3 but moments are computed on raw rainfall values (not log-transformed):

$$X_T = \bar{x} + K_T \cdot s$$

where $K_T$ is the Wilson-Hilferty factor using the raw-data skewness $C_s$.

**References:**
- Pearson, K. (1895). "Contributions to the mathematical theory of evolution, II: Skew variation in homogeneous material." *Phil. Trans. R. Soc.*, 186, 343–414.

---

## 4. Wilson-Hilferty Frequency Factor

The T-year frequency factor $K_T$ for the Pearson III family is computed using the **exact cube-root transformation** of Wilson and Hilferty (1931):

$$K_T = \frac{2}{C_s}\left[\left(1 - \frac{C_s^2}{36} + z \cdot \frac{C_s}{6}\right)^3 - 1\right]$$

where $z = \Phi^{-1}(1-p)$ is the standard normal deviate.

When $|C_s| < 10^{-6}$ the formula is numerically unstable; in this limit the Pearson III collapses to Normal and $K_T = z$ exactly.

### Why the exact formula, not the polynomial

Many hydrology textbooks (e.g. Subramanya 2008) present a 5-term Taylor expansion of the above:

$$K_T \approx z + (z^2-1)k + \frac{z^3-6z}{3}k^2 - (z^2-1)k^3 + zk^4 + \frac{k^5}{3}, \quad k = \frac{C_s}{6}$$

This polynomial is accurate for $|C_s| \lesssim 1.5$ but diverges for larger skewness. At $C_s = -2.103$ (observed at grid point 29.375°N, 94.375°E) the polynomial gives $K_T = 0.9473$ versus the exact value $K_T = 0.9508$ — an error of 0.0035, which propagates to ~0.17 mm error in the final RP. The test tolerance is 0.01 mm, so the polynomial fails.

The Excel workbook uses the exact formula. Our implementation matches Excel to 8 decimal places across all 334 grid points.

**Reference:**
- Wilson, E.B. and Hilferty, M.M. (1931). "The distribution of chi-square." *Proceedings of the National Academy of Sciences*, 17(12), 684–688.

---

## 5. Unbiased Skewness

The coefficient of skewness uses the Fisher-corrected (unbiased) estimator, which matches Excel's `SKEW()` function:

$$C_s = \frac{n}{(n-1)(n-2)} \sum_{i=1}^{n}\left(\frac{x_i - \bar{x}}{s}\right)^3$$

where $s$ is the sample standard deviation with $n-1$ in the denominator (ddof=1). For LP3 this is applied to $y_i = \ln(x_i)$; for Pearson III it is applied to the raw $x_i$.

---

## 6. Goodness-of-Fit Tests

Each distribution is evaluated by two tests. A distribution is **accepted** only if it passes both. The final design rainfall is the maximum RP among all accepted distributions.

### 6.1 Chi-Square Test

Tests whether observed frequency counts in fixed rainfall bins are consistent with the fitted theoretical distribution.

**Bins:** $[50, 100), [100, 150), [150, 200), [200, 250), [250, 300)$ mm — five bins, fixed for all distributions and all grid points.

**Statistic:**
$$\chi^2 = \sum_{j=1}^{5} \frac{(O_j - E_j)^2}{E_j}$$

where $O_j$ is the count of observed values in bin $j$ and $E_j = n \cdot [F(b_{j+1}) - F(b_j)]$ is the expected count from the fitted CDF.

If any bin has $E_j = 0$ but $O_j > 0$ the statistic is set to $\infty$ (automatic fail).

**Degrees of freedom:** $df = 2$ for all distributions (fixed across the project). This gives:
$$\chi^2_{\text{crit}} = \chi^2_{0.95,\,2} \approx 5.991$$

**Decision:** Pass if $\chi^2 \leq 5.991$.

**Note on Excel bug:** In the MPSB workbook the `FREQUENCY()` formula in columns 2–334 of every chi-square sheet references rows 15–34 instead of rows 11–30. This includes 16 data years and 4 statistical summary rows (mean, std, $K_n$, $C_s$) — corrupting the observed counts. Our implementation always uses all $n$ data values and is therefore statistically correct. The 17 grid points where this bug changes the selected distribution are listed in `KNOWN_EXCEL_CHISQ_BUG_POINTS` in `tests/test_rainfall_selection.py`. See `docs/rainfall-engine-bugs.md` §Bug 2.

**References:**
- Pearson, K. (1900). "On the criterion that a given system of deviations from the probable in the case of a correlated system of variables is such that it can be reasonably supposed to have arisen from random sampling." *Phil. Mag.*, 50(302), 157–175.

### 6.2 Kolmogorov-Smirnov Test

A non-parametric test comparing the empirical distribution function $F_n(x)$ with the theoretical CDF $F(x)$.

**Statistic:**
$$D_n = \sup_x |F_n(x) - F(x)|$$

Computed via `scipy.stats.kstest`.

**Critical value** (large-sample, $\alpha = 0.05$):
$$D_{\text{crit}} = \frac{1.36}{\sqrt{n}}$$

**Decision:** Pass if $D_n \leq D_{\text{crit}}$.

For $n = 20$ data years: $D_{\text{crit}} = 1.36 / \sqrt{20} \approx 0.304$.

**References:**
- Kolmogorov, A.N. (1933). "Sulla determinazione empirica di una legge di distribuzione." *Giornale dell'Istituto Italiano degli Attuari*, 4, 83–91.
- Smirnov, N.V. (1948). "Table for estimating the goodness of fit of empirical distributions." *Annals of Mathematical Statistics*, 19, 279–281.

---

## 7. Selection Rule

Among all distributions that pass both the chi-square and KS tests, the one with the **highest 100-year RP** is selected as the design value. This is the conservative choice — when multiple distributions are statistically acceptable, the larger estimate is used.

**Fallback:** If no distribution passes both tests, LP3 is used unconditionally. This replicates the Excel behaviour and ensures a design value is always produced.

```
applicable = [f for f in fits if f.chi_sq_pass and f.ks_pass]
if applicable:
    selected = max(applicable, key=lambda f: f.rp_100yr)
else:
    selected = LP3_result
```

---

## 8. Duration Scaling (Gauge Workflow)

For the Indargarh gauge station workflow, the 24-hour rainfall for a given return period is scaled to sub-daily durations using the CWC (Central Water Commission, India) power-law:

$$P_t = P_{24} \cdot \left(\frac{t}{24}\right)^{1/3}$$

where $P_t$ is the rainfall depth (mm) for duration $t$ hours, and $P_{24}$ is the 24-hour Gumbel T-year value.

The corresponding **intensity** (mm/hr) is:

$$I_t = \frac{P_t}{t} = \frac{P_{24}}{t} \cdot \left(\frac{t}{24}\right)^{1/3}$$

The exponent $1/3$ is the Indian standard value (CWC, 2002). Other standards use different exponents (e.g. 0.25 in some European guidelines).

**Reference:**
- CWC (2002). *Flood Estimation Report for Western Himalayas — Zone 7*. Central Water Commission, New Delhi.

---

## 9. CDF Construction

Each fitted distribution has a corresponding CDF used in the goodness-of-fit tests. All CDFs operate on raw rainfall in mm; log-transforms are handled internally where required.

| Distribution | CDF | Key parameters |
|---|---|---|
| LP3 | Gamma CDF on $\ln(x)$ | $\alpha = 4/C_s^2$, $\beta = s_y|C_s|/2$, $\xi = \bar{y} - 2s_y/C_s$ |
| Gumbel | $\exp(-\exp(-\alpha(x-u)))$ | $\alpha = \pi/(s\sqrt{6})$, $u = \bar{x} - 0.5772/\alpha$ |
| Normal | $\Phi((x-\bar{x})/s)$ | — |
| Log-Normal | $\Phi((\ln x - \bar{y})/s_y)$ | — |
| Pearson III | Gamma CDF on $x$ | Same parameterisation as LP3 but in raw space |

For LP3 and Pearson III with negative skewness ($C_s < 0$) the distribution is upper-bounded; the CDF is reflected: $F(x) = 1 - F_\Gamma((x-\xi)/(-\beta))$.

When $|C_s| < 10^{-6}$, LP3 collapses to Log-Normal and Pearson III collapses to Normal.

---

## 10. Numerical Tolerances

| Quantity | Tolerance | Basis |
|---|---|---|
| LP3 100-year RP | 0.01 mm | Excel floating-point round-trip |
| Gumbel 100-year RP | 0.01 mm | Same |
| Normal 100-year RP | 0.01 mm | Same |
| Log-Normal 100-year RP | 0.01 mm | Same |
| Pearson III 100-year RP | 0.01 mm | Same |
| Wilson-Hilferty $K_T$ | $10^{-6}$ | Direct comparison with Excel Kt column |
| Skewness $C_s$ | $10^{-6}$ | Direct comparison with Excel Cs column |
| Selected RP | 0.5 mm | Looser: depends on test pass/fail boundary |
| Intensity (Indargarh) | 0.001 mm/hr | Excel intensity table precision |

---

## 11. Known Excel Bugs

Full evidence in `docs/rainfall-engine-bugs.md`. Summary:

| # | Location | Bug | Impact | Our implementation |
|---|---|---|---|---|
| 1 | Gumbel sheet, column 1 | `STDEVP` (ddof=0) instead of `STDEV` | ~2 mm error at point (27.875, 89.125) | `ddof=1` everywhere (correct) |
| 2 | All chi-sq sheets, columns 2–334 | `FREQUENCY` row range shifted by +4 | Selection changes at 17 northern grid points | Correct 20-value count always used |
| 3 | Our initial implementation | 5-term WH polynomial instead of exact formula | Up to 0.27 mm at \|Cs\| > 1.9 | Fixed — exact cube-root used |

---

## 12. References

| Reference | Used for |
|---|---|
| Wilson & Hilferty (1931). "The distribution of chi-square." *PNAS* 17(12). | Exact K_T formula |
| Gumbel, E.J. (1958). *Statistics of Extremes*. Columbia University Press. | Gumbel EV1 theory |
| Chow, Maidment & Mays (1988). *Applied Hydrology*. McGraw-Hill. | General frequency analysis methodology |
| Kite, G.W. (1977). *Frequency and Risk Analysis in Hydrology*. Water Resources Publications. | LP3 method |
| Pearson, K. (1895). Phil. Trans. R. Soc. 186. | Pearson III distribution |
| Kolmogorov (1933); Smirnov (1948). | KS test critical values |
| CWC (2002). *Flood Estimation Report — Western Himalayas Zone 7*. | Duration scaling exponent 1/3 |
| IS:5477 Part 4 (1971). Bureau of Indian Standards. | LP3 as standard for Indian hydrology |
