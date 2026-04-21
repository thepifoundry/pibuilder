# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Documentation Standards — Mandatory on Every Change

**Every function, class, and module must have a verbose docstring.** This is non-negotiable.

- Module docstring: purpose, ground-truth reference (e.g. which Excel sheet/row), known limitations.
- Class docstring: what it represents, key invariants, typical lifecycle.
- Function/method docstring: what it computes, all parameters with types and units, return value with type and units, algorithm reference (formula name, paper, or Excel sheet row), and any exceptions raised.
- If a formula is used, state it explicitly in the docstring (LaTeX-style inline is fine).
- If a function matches an Excel cell formula, say which sheet and row.
- If behaviour differs from a reference (e.g. a known Excel bug), document the divergence and the reason.

When implementing or modifying any source file, **also update the relevant file under `docs/`** to reflect the change. The docs directory is the SME-facing specification; keep it in sync with the code.

---

## Commands

```bash
# Install in editable mode (run once after clone)
pip install -e ".[dev]"

# Run the full test suite
pytest

# Run a single test file with verbose output
pytest tests/test_rainfall_lp3.py -v

# Run a single test by name
pytest -k "test_lp3_first_grid_point" -v

# Extract ground-truth fixtures from Excel (run once when Excel changes)
python scripts/extract_fixtures.py

# Check test coverage
pytest --cov=pibuilder --cov-report=term-missing
```

---

## Architecture

```
src/pibuilder/
├── rainfall/
│   ├── frequency.py   — 5-distribution fitting (LP3, Gumbel, Normal, LogNorm, Pearson III)
│   │                    chi-sq + KS goodness-of-fit, selection rule = max(RP | both pass)
│   └── intensity.py   — Duration scaling (CWC P_t = P_24·(t/24)^(1/3)) and intensity tables
├── gis/
│   ├── watershed.py   — DEM-based watershed delineation (WhiteboxTools)
│   └── basin.py       — Basin geometry: area, centroid, longest flow path, slope
├── hydrology/
│   ├── runoff.py      — SCS Curve Number runoff depth
│   └── discharge.py   — Rational Method and SCS peak discharge
├── hydraulics/
│   └── hfl.py         — High Flood Level computation (Manning's equation, backwater)
├── data/
│   ├── loaders.py     — DEM, shapefile, rainfall raster ingestion
│   └── etl.py         — ETL transforms: reproject, clip, resample, gap-fill
├── api/               — FastAPI service layer (not yet implemented)
└── report/            — Jinja2/WeasyPrint PDF report generation (not yet implemented)

tests/
├── fixtures/          — JSON ground-truth files extracted from Excel (run extract_fixtures.py)
│   ├── mpsb_ground_truth.json      — 334 grid points × {lp3, gumbel, normal, lognorm, pearson, chi_sq, ks, selected}
│   ├── mpsb_grid_data.json         — 334 grid points × 20 annual-max daily rainfall values (mm)
│   ├── indargarh_daily_max.json    — 32 annual-max daily values (1990–2021, mm)
│   └── indargarh_ground_truth.json — 5 durations × 5 return periods intensity table (mm/hr)
├── conftest.py        — Session-scoped fixtures loading JSON (no Excel dependency at test time)
├── test_rainfall_lp3.py
├── test_rainfall_gumbel.py
└── test_rainfall_selection.py

scripts/
└── extract_fixtures.py — One-shot Excel → JSON extractor (needs openpyxl, reads docs/ricalcs/*.xlsx)

docs/
├── rainfall-engine-bugs.md        — Confirmed Excel bugs with evidence and impact analysis
├── rainfall-frequency-analysis.md — Algorithm specification for frequency.py
├── rainfall-engine.md             — Engine design and ground-truth methodology
└── ...                            — Other domain specs (GIS, hydrology, hydraulics)
```

### Ground-truth files

All numerical ground truth comes from:
- `docs/ricalcs/MPSB Rainfall Analysis_China Region.xlsx` — 334 satellite grid points, sheets per distribution
- `docs/ricalcs/Indargarh Rainfall Analysis.xlsx` — gauge station intensity table

### Key algorithmic invariants

- **LP3**: Wilson-Hilferty K_T uses the exact cube-root formula `(2/Cs)*((1 - Cs²/36 + z·Cs/6)³ - 1)`. The 5-term polynomial diverges at |Cs| > 1.9. Never substitute the polynomial.
- **Gumbel**: Always use `ddof=1` (STDEV). Column 1 of the Excel Gumbel sheet has a STDEVP bug — do not replicate it.
- **Chi-sq**: Fixed bins `[50, 100, 150, 200, 250, 300]` mm, `df=2`, critical `= chi2.ppf(0.95, 2) = 5.991`. Excel's FREQUENCY formula is shifted by 4 rows in columns 2–334 (known bug); our implementation is correct.
- **Selection**: `max(RP)` over distributions where `chi_sq_pass AND ks_pass`. Fall back to LP3 if none pass.
- **Tolerances**: LP3/Gumbel/Normal/LogNorm individual RPs match Excel to 0.01 mm. Selection RP uses 0.5 mm tolerance because it depends on test pass/fail boundaries.

### Known Excel bugs (do not replicate)

See `docs/rainfall-engine-bugs.md` for full evidence. Summary:
1. **Gumbel STDEVP** — cell (27.875, 89.125) uses population std; our impl uses sample std everywhere.
2. **Chi-sq FREQUENCY row shift** — 333/334 columns use wrong row range; causes 17 selection discrepancies listed in `KNOWN_EXCEL_CHISQ_BUG_POINTS` in `test_rainfall_selection.py`.
3. **WH polynomial** — our original bug (now fixed); exact formula required.
