# PI Builder — Claude Code Context

## What This Project Is

PI Builder is an AI-native hydrology platform for Indian bridge and culvert infrastructure design.
It automates the workflow: coordinate → catchment delineation → rainfall frequency analysis →
peak discharge → High Flood Level → DPR-compliant report.

The system implements published Indian standards (IRC SP-13:2022, IS 5477, CWC sub-zone reports)
and international textbooks (Subramanya, Raghunath, Chow). Every formula must cite its source.

\---

## Read These First (In Order)

1. `docs/06\_authoritative\_sources.md` — Textbooks, IS/IRC codes, data sources. Mandatory before
writing any formula. Every function docstring must cite from this document.
2. `docs/README.md` — Master index of all documentation.
3. `GAMEPLAN.md` — 18-week project timeline, phases, go/no-go gates.

\---

## When Implementing a Story

1. Find the story in `docs/USER\_STORIES/epic\_N\_\*.md`
2. Read the full spec: Background → Acceptance Criteria → Method/Formulas → Code Skeleton → Test Cases
3. Write tests FIRST (acceptance criteria = test scaffold)
4. Implement to match the code skeleton signatures exactly
5. Add textbook citation in every docstring — see format below

### Docstring Citation Format (Mandatory)

```python
def gumbel\_frequency\_factor(T: int, n: int) -> float:
    """Compute Gumbel frequency factor K\_T.

    K\_T = -(sqrt(6)/pi) \* (0.5772 + ln(ln(T/(T-1))))

    Reference:
        Subramanya, K. (2013). Engineering Hydrology, 4th ed.
        McGraw Hill India. Eq. 7.20.

        Chow, V.T., Maidment, D.R., Mays, L.W. (1988).
        Applied Hydrology. McGraw-Hill. Eq. 12.3.5.

    Args:
        T: Return period in years (e.g., 100 for 100-yr flood)
        n: Sample size for finite-sample correction

    Returns:
        Dimensionless frequency factor K\_T
    """
```

\---

## Architecture (5 Layers)

```
UI (React + Leaflet)
    ↓
API Layer (FastAPI) — orchestrates, does not compute
    ↓
Domain Services (Python modules in src/pi\_builder/domain/)
    ├── rainfall/        ← Epic 2: frequency analysis, IMD reduction, IDF
    ├── gis/             ← Epic 3: DEM processing, watershed, catchment metrics
    ├── hydrology/       ← Epic 4: discharge methods (Rational/SCS-CN/Inglis/Dicken/Ryves/SUH)
    ├── hydraulics/      ← Epic 5: Manning's, Lacey's, scour
    ├── validation/      ← Epic 6: backtest engine, historical corpus
    └── reports/         ← Epic 7: DPR-compliant PDF generator
    ↓
Async Workers (RQ + Redis) — for heavy compute (DEM, large rasters)
    ↓
Data Layer (PostgreSQL + PostGIS + Object Store)
```

\---

## Key Design Principles

### 1\. Pluggable Adapters for Global Extensibility

Data sources and design codes must use the adapter/plugin pattern — NOT hardcoded India-specific:

```python
# WRONG — hardcoded to India
rainfall = imd\_client.get\_gridded\_data(lat, lon)

# CORRECT — adapter pattern
rainfall = rainfall\_source.get\_data(lat, lon)
# where rainfall\_source is IMDAdapter, BMKGAdapter, TMDAdapter, etc.
```

Same for design codes: IRC SP-13:2022 rules are one configuration of the rules engine.
AASHTO, Eurocode, SNI (Indonesia) are other configurations. The engine is country-agnostic.

### 2\. Multi-Method Discharge (Never Single Method)

Always run ALL applicable methods and present a comparison. Never return just one discharge value.
The system recommends; the engineer decides. See Epic 4 for method-selection decision table.

### 3\. Every Output Is Auditable

Every computed value must have a traceable audit trail:

* Which data source (IMD grid point X,Y, years 1958-2023)
* Which formula (Gumbel MoM, Subramanya Eq. 7.20)
* Which parameters (mean=87.3mm, std=22.1mm)
* Which decision (LP3 selected as best-fit: KS=0.087 < critical 0.166)

### 4\. Confidence Levels on Every Output

Low confidence ≠ wrong. Flag it explicitly. The system must say:
"Manning's n = 0.040 (Medium confidence — DEM cross-section, recommend field survey)"

\---

## Repository Structure

```
pi-builder/
├── CLAUDE.md                    ← YOU ARE HERE
├── GAMEPLAN.md                  ← 18-week project timeline
├── pyproject.toml               ← uv + dependencies
├── docker-compose.yml           ← Postgres+PostGIS+Redis local stack
├── docs/
│   ├── README.md                ← Master index
│   ├── 06\_authoritative\_sources.md  ← CRITICAL — all textbook/code refs
│   ├── ENGINES/                 ← Existing engine architecture docs
│   │   ├── system-architecture.md
│   │   ├── rainfall-engine.md
│   │   ├── gis-engine.md
│   │   ├── hydrology-engine.md
│   │   └── hydraulics-engine.md
│   ├── USER\_STORIES/            ← Detailed implementation specs
│   │   ├── epic\_1\_data\_foundation.md
│   │   ├── epic\_2\_rainfall.md
│   │   ├── epic\_3\_4\_gis\_hydrology.md
│   │   ├── epic\_5\_8\_hydraulics\_reports\_ui.md
│   │   └── roadmap.md
│   └── STRATEGIC\_CONTEXT/      ← For founder/advisor reference
│       ├── strategic\_refinement.md
│       └── pros\_cons\_analysis.md
├── src/pi\_builder/
│   ├── api/                     ← FastAPI routes
│   ├── domain/
│   │   ├── rainfall/            ← Epic 2 (partially built)
│   │   ├── gis/                 ← Epic 3
│   │   ├── hydrology/           ← Epic 4
│   │   ├── hydraulics/          ← Epic 5
│   │   ├── validation/          ← Epic 6
│   │   └── reports/             ← Epic 7
│   ├── adapters/                ← Data source adapters (IMD, CWC, CartoDEM)
│   │   ├── rainfall/
│   │   │   ├── base.py          ← Abstract RainfallDataSource
│   │   │   ├── imd\_adapter.py   ← India: IMD gridded
│   │   │   └── cwc\_adapter.py   ← India: CWC gauge stations
│   │   └── dem/
│   │       ├── base.py          ← Abstract DEMSource
│   │       └── cartoderm\_adapter.py
│   └── standards/               ← Design code rules engine
│       ├── base.py              ← Abstract StandardsEngine
│       └── irc/
│           ├── sp13\_2022.py     ← IRC SP-13:2022 rules
│           └── irc5\_2015.py     ← IRC:5-2015 return period table
├── tests/
│   ├── fixtures/
│   │   ├── indargarh\_rainfall.py    ← L\&T Excel test case 1
│   │   ├── mpsb\_gridded.py          ← L\&T Excel test case 2
│   │   └── cwc\_subzone\_cases.py     ← CWC worked examples
│   └── domain/                      ← Mirrors src/pi\_builder/domain/
└── data/
    ├── sample\_dem/              ← Small CartoDEM tile for unit tests
    └── irc\_tables/              ← Runoff coefficient tables, ARF table
```

\---

## Current Build State (as of May 2026)

### Built (Epic 2 — Rainfall Engine)

Claude Code has built the rainfall intensity calculation engine based on the L\&T Excel workflow.
Status: REVIEW REQUIRED — see the validation targets below before proceeding.

### Not Yet Built

* Epic 1: Data Foundation (database schema, IMD/CWC ingestion pipelines)
* Epic 3: GIS Engine (DEM processing, watershed delineation)
* Epic 4: Hydrology Engine (discharge methods)
* Epic 5: Hydraulics Engine (Manning's, Lacey's)
* Epic 6: Validation/Backtest Engine
* Epic 7: Report Generator
* Epic 8: UI

### Immediate Priority (Before Building New Features)

1. Validate the existing rainfall engine against the two L\&T test cases:

   * Indargarh (1990-2021): Gumbel output must match L\&T Excel within 2%
   * MPSB gridded: best-fit distribution must match L\&T on >80% of grid cells
2. Refactor any hardcoded IMD/CWC references to use the adapter pattern
3. Add textbook citations to all existing docstrings

\---

## Validation Targets (The Ground Truth)

The system is validated against a corpus of historical bridge projects.
Every release must run the full backtest suite:

```bash
pytest tests/backtest/ -v --corpus data/validation\_corpus.xlsx
```

Targets:

* Month 1: 2 cases (L\&T Excel files), error < 2%
* Month 3: 30-40 cases (CWC sub-zone reports), mean error < 15%
* Month 6: 100+ cases (RTI bridge DPRs), mean error < 15%

\---

## Running Locally

```bash
# Start data services
docker-compose up -d postgres redis

# Install dependencies
uv sync

# Run tests
pytest tests/ -v

# Start API
uvicorn src.pi\_builder.api.main:app --reload
```

\---

## Standards Reference (Quick Lookup)

|What you're implementing|Read this first|
|-|-|
|Any formula|docs/06\_authoritative\_sources.md Tier 2 (textbooks)|
|IRC compliance|docs/06\_authoritative\_sources.md Tier 1 (IRC SP-13:2022)|
|Discharge methods|docs/USER\_STORIES/epic\_3\_4\_gis\_hydrology.md Epic 4|
|Rainfall frequency|docs/USER\_STORIES/epic\_2\_rainfall.md|
|DEM processing|docs/USER\_STORIES/epic\_3\_4\_gis\_hydrology.md Epic 3|
|Report format|docs/USER\_STORIES/epic\_5\_8\_hydraulics\_reports\_ui.md Epic 7|

\---

## What Not to Build (Explicit Non-Goals for V1)

* Real-time flood forecasting
* 2D hydrodynamic modeling (HEC-RAS 2D equivalent)
* Urban drainage stormwater (different codes, different customers)
* Coastal/tidal hydrology
* Groundwater modeling
* Multi-tenancy

