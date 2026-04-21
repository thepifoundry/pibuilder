# Excel Model Bugs — MPSB Rainfall Analysis

Confirmed bugs in `docs/ricalcs/MPSB Rainfall Analysis_China Region.xlsx`.
Discovered during TDD implementation of the rainfall frequency analysis engine.
Each bug is proven by reading the raw Excel formulas and comparing computed values.

---

## Bug 1: Gumbel Sheet — STDEVP in Column 1 Only

**Sheet:** `gumbel (ks test)`
**Row:** 24 ("Std Dev")
**Affected points:** (27.875, 89.125) only

### What the bug is
The first data column uses `STDEVP()` (population standard deviation, ddof=0).
Every other column uses `STDEV()` (sample standard deviation, ddof=1).

### Evidence
```
Column (27.875, 89.125): stored std = 25.506793  →  np.std(data, ddof=0) = 25.506793  ✓
Column (28.125, 89.125): stored std = 22.175520  →  np.std(data, ddof=1) = 22.175520  ✓
                                                  →  np.std(data, ddof=0) = 21.614024  ✗
```

### Impact
The 100-year RP for (27.875, 89.125) is computed as 164.121mm instead of the
correct 166.199mm — a difference of ~2mm. All other 333 Gumbel values are correct.

### Our implementation
Uses `ddof=1` everywhere (correct). The first point's expected value in
`test_gumbel_first_grid_point` is set to our ddof=1 value (166.199mm), not Excel's.
The all-grid test skips this point with a documented comment.

---

## Bug 2: Chi-Square Test — FREQUENCY Formula Row Range Shift

**Sheet:** `pearson(chi sq)`, and by extension all chi-sq sheets
**Row:** 51 ("Obs Frequency")
**Affected points:** All 333 columns except the first (27.875, 89.125)

### What the bug is
The observed frequency count uses Excel's `FREQUENCY()` function. In the first
column (B), the formula correctly references the 20 data rows:

```
Column B (first):  =FREQUENCY(B11:B30, $C$2:$C$6)   ← rows 11–30 = 20 data years
```

In every other column, the row range has shifted by +4 due to a copy-paste
relative reference error:

```
Column C onward:   =FREQUENCY(C15:C34, $C$2:$C$6)   ← rows 15–34 = WRONG
```

Rows 15–34 contain:
- Rows 15–30: the **last 16 years** of data (2004–2019)
- Rows 31–34: **statistical values** — mean, std, Kn, Cs

So the observed frequency for 333/334 points is computed on 16 data values plus
4 non-data numbers (e.g., mean=117.05, std=32.14, Kn=2.326, Cs=1.41).

### Evidence
For point (29.125, 88.625), data sorted: [66.72, 84.21, ..., 157.86, 214.35]

```
Correct count (rows 11–30, all 20 years):
  [50,100):  6    [100,150): 12   [150,200): 1   [200,250): 1   [250,300): 0

Excel count (rows 15–34, 16 data + mean/std/Kn/Cs):
  [50,100):  9    [100,150):  9   [150,200): 1   [200,250): 1   [250,300): 0
```

The mean (117.05) and std (32.14) fall in the [100,150) bin, inflating it.
Kn (2.326) and Cs (1.41) fall in the [0,50) range, not counted in any bin,
but their presence removes 4 data points from the tally (only 16 of 20 years used).

### Impact
The corrupted observed frequencies produce inflated chi-square statistics,
causing distributions (especially Pearson III) to fail chi-sq at high-Cs
northern grid points where they would otherwise pass.

This changes the selected distribution at **17 grid points**:

| Point | Excel selects | We select | Excel chi-sq basis |
|-------|--------------|-----------|-------------------|
| (29.125, 88.625) | LP3 = 221.9 | Pearson = 222.7 | Corrupted obs |
| (29.125, 90.625) | LogNorm = 245.3 | Pearson = 257.3 | Corrupted obs |
| (29.125, 91.625) | LP3 = 200.4 | Pearson = 224.0 | Corrupted obs |
| (29.125, 92.375) | LP3 = 203.0 | Pearson = 203.6 | Corrupted obs |
| (29.375, 83.875) | LogNorm = 237.3 | Pearson = 241.9 | Corrupted obs |
| (29.375, 85.625) | LP3 = 238.9 | Pearson = 206.3 | Corrupted obs |
| (29.375, 91.625) | LP3 = 225.4 | Gumbel = 227.2 | Corrupted obs |
| (29.375, 91.875) | LP3 = 227.2 | Pearson = 231.5 | Corrupted obs |
| (29.375, 94.375) | Gumbel = 197.5 | Normal = 174.5 | LP3 = #NUM! + corrupted obs |
| (29.875, 83.625) | LP3 = 295.9 | Pearson = 306.8 | Corrupted obs |
| (29.875, 95.125) | LP3 = 397.8 | Pearson = 402.0 | Corrupted obs |
| (30.125, 85.125) | LP3 = 270.9 | Pearson = 235.1 | Corrupted obs |
| (30.125, 94.625) | Gumbel = 159.6 | Pearson = 161.2 | Corrupted obs |
| (30.375, 82.625) | LP3 = 295.1 | Pearson = 285.3 | Corrupted obs |
| (30.375, 91.375) | LogNorm = 267.5 | LP3 = 242.6 | Corrupted obs |
| (30.375, 95.625) | LP3 = 196.7 | Pearson = 198.8 | Corrupted obs |
| (30.625, 82.625) | LP3 = 285.7 | Pearson = 291.2 | Corrupted obs |

All 17 are in the northern high-elevation region (lat > 29°) where Cs tends
to be large (high positive skewness), making the Pearson III fit sensitive
to the chi-sq pass/fail threshold.

### Our implementation
Uses all 20 data values with the correct fixed bins [50,100,150,200,250,300]mm.
The 17 discrepant points are listed in `KNOWN_EXCEL_CHISQ_BUG_POINTS` in
`tests/test_rainfall_selection.py` and emit a warning rather than a test failure.

---

## Bug 3: Wilson-Hilferty — Polynomial vs Exact Formula

**Not strictly an Excel bug — Excel is correct. Our initial implementation was wrong.**

### Background
The Wilson-Hilferty (1931) frequency factor K_T for the Pearson III distribution
has two equivalent forms:

**Exact (cube-root):**
```
K_T = (2/Cs) × [(1 - Cs²/36 + z·Cs/6)³ - 1]
```

**Polynomial (5-term Taylor expansion of the above):**
```
K_T = z + (z²-1)k + (z³-6z)k²/3 - (z²-1)k³ + zk⁴ + k⁵/3
where k = Cs/6
```

Both are correct for small |Cs|. For |Cs| > ~1.9 the polynomial diverges from
the exact formula.

### Evidence
At (29.375, 94.375) with Cs = -2.102904:

```
Exact formula:    Kt = 0.95084110  (matches Excel to 8 decimal places)
Polynomial:       Kt = 0.94731537  (error = 0.00353)
scipy pearson3:   Kt = 0.94484135  (worse — different parameterisation)
```

The polynomial error of 0.0035 in Kt translates to ~0.17mm error in the
final 100-year RP — above the 0.01mm test tolerance.

### Our implementation
Uses the exact cube-root formula. Matches Excel to 8 decimal places across
all 334 grid points including the 5 with |Cs| > 1.9.

---

## Summary Table

| Bug | Sheet | Scope | RP Impact | Status |
|-----|-------|-------|-----------|--------|
| STDEVP in Gumbel col 1 | `gumbel (ks test)` | 1 point | ~2mm | Documented, not replicated |
| FREQUENCY row shift in chi-sq | All chi-sq sheets | 333 points | Changes selection at 17 points | Documented, not replicated |
| Polynomial WH (our bug, not Excel) | N/A | Would affect 5 points | Up to 0.27mm | Fixed — exact formula used |

---

## Recommendation for SME

The chi-sq FREQUENCY formula bug (Bug 2) is the most consequential. To fix it
in Excel, the formula in row 51 of every chi-sq sheet should be:

```
=FREQUENCY(<column>11:<column>30, $C$2:$C$6)
```

for every column, not just the first. The current formula for all columns
after the first is shifted to rows 15–34, contaminating the observed frequencies
with mean, std, Kn, and Cs values.

The 17 affected grid points are all in the northern high-elevation region. At
these points our implementation selects Pearson III more frequently than Excel
does — because with correct chi-sq, Pearson passes when Excel's buggy test
rejects it. Whether Pearson is actually the better fit at those points is a
separate question for the SME to review.
