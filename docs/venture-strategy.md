# pibuilder Venture Strategy
## Findings, Analysis, and Roadmap

**Prepared:** April 2026
**Author:** Siddharth (founder), compiled with Claude Code

---

## Part 1 — The Honest Assessment (The Roast)

Before strategy, context. The following is a frank assessment of where things
stood at the start of this conversation.

> You have a hydrology platform where the only working module is rain. Fitting,
> because everything else about this project is also underwater.
>
> Your SME — the one person who knows what half these Excel cells mean — is
> ghosting you in slow motion, and your strategy is apparently to hope the
> tension resolves itself while your ground truth walks out the door with their
> LinkedIn notification.
>
> You've documented three bugs in an Excel file. Congratulations. You have a
> very well-tested reason to distrust a spreadsheet. That's ₹0 in ARR.
>
> Your exit target is ₹830 crores. Your current asset is a CLI tool that tells
> you how much it rained near a mountain. The gap between those two numbers is
> not a roadmap, it's a hallucination.

That said — the code is clean, the architecture is sound, and the market is real.
The rest of this document is the plan to close the gap.

---

## Part 2 — What Has Been Built

### Rainfall Frequency Analysis Engine (Phase 1 — Complete)

The only fully implemented module. It automates the rainfall frequency analysis
currently done manually in Excel across EPC hydrology projects.

**Two workflows:**

| Workflow | Data source | Output |
|---|---|---|
| Grid-based (MPSB) | Satellite annual-max daily rainfall, 334 grid nodes, 0.25° spacing | 100-yr RP depth (mm) per node |
| Gauge-based (Indargarh) | 32-yr rain gauge record (1990–2021) | IDF table: mm/hr × 5 durations × 5 RPs |

**Five distributions fitted:** LP3, Gumbel EV1, Normal, Log-Normal, Pearson III

**Selection rule:** Highest 100-yr RP among distributions passing both chi-square
and KS goodness-of-fit tests. Fallback to LP3 if none pass.

**Validation:** 13 tests, all passing. Tolerance 0.01 mm for individual
distributions, 0.5 mm for selected RP.

**Three Excel bugs found and documented** (see Part 3).

**Query CLI:**
```
.venv/bin/python scripts/rainfall_query.py 29.0 88.5
```

### Everything Else — Scaffolded, Not Built

| Module | Status |
|---|---|
| GIS — watershed delineation, basin geometry | Placeholder |
| Hydrology — SCS CN runoff, Rational Method discharge | Placeholder |
| Hydraulics — Manning's HFL, afflux, freeboard | Placeholder |
| Data pipeline — DEM, shapefile, raster ingestion | Placeholder |
| API layer — FastAPI service | Placeholder |
| Report generation — Jinja2/WeasyPrint PDF | Placeholder |

---

## Part 3 — Excel Bugs Found During Development

Three discrepancies were found between the engine and the Excel workbooks during
Test-Driven Development. Two are confirmed Excel bugs. One was our bug, now fixed.

### Bug 1 — Gumbel STDEVP (1 point, ~2mm impact)

Column 1 of the Gumbel sheet uses `STDEVP()` (population std, ddof=0) instead
of `STDEV()` (sample std, ddof=1). Affects point (27.875°N, 89.125°E) only.
Impact: 164.1mm in Excel vs correct 166.2mm.

**Fix:** Change `STDEVP` → `STDEV` in row 24, col B of the Gumbel sheet.

### Bug 2 — Chi-Square FREQUENCY Row Shift (Most Consequential)

In every chi-square sheet, the `FREQUENCY()` formula in columns 2–334 has a
+4 row shift from a copy-paste error. It references rows 15–34 instead of the
correct 11–30, including 4 statistical summary values (mean, std, Kn, Cs) in the
frequency count and dropping the first 4 data years.

**Impact:** Changes the selected design distribution at 17 northern grid points
(lat > 29°N). RP differences of up to 36mm at some sites.

**Fix:** Every column in row 51 of every chi-sq sheet must use:
```
=FREQUENCY(<column>11:<column>30, $C$2:$C$6)
```

### Bug 3 — Wilson-Hilferty Polynomial (Our Bug, Fixed)

Our initial implementation used the 5-term Taylor polynomial for the K_T
frequency factor. This diverges from the exact cube-root formula at |Cs| > 1.9.
Excel uses the exact formula. We fixed it — now matches Excel to 8 decimal
places across all 334 points.

---

## Part 4 — The SME Situation

### Who She Is

**Sudesna Biswas** — Deputy General Manager, Head of Hydrology & Hydraulics,
Larsen & Toubro EDRC, Mumbai.

- 21 years experience, 14 years in lead/head roles
- M.Plan (Environmental Planning), SPA New Delhi + B.E. Civil, Nagpur University
  + Executive Leadership, IIM Calcutta
- Currently heading hydrology for Delhi Airport, Bangalore Airport, Navi Mumbai
  Airport, Mumbai-Nagpur Expressway, Mumbai-Ganga Expressway, Bullet Train,
  Dedicated Freight Corridors
- Software: HEC-RAS, HEC-HMS, Civil Storm, Watergems, GIS MapInfo, AutoCAD
- Awards: L&T DELTA (design + digital innovation), L&T Pi Gold (process innovation)

This is not a junior consultant. She is one of India's most senior active
infrastructure hydrology engineers.

### The Risk

The rainfall engine is SME-independent — fully documented, tested, and
self-contained. The **four pending engines are not.** Their Excel workbooks,
engineering judgment, and validation ground truth have not been extracted.

If contact ends before extraction: the project is not dead, but the pending
engines would need a replacement SME to re-derive methodology from published
standards — slower and more expensive.

### The Window

Contact is tense but not closed. This is the single highest-priority action
in the entire project right now. One or two focused sessions is all that is
needed — not to continue the relationship, but to not leave institutional
knowledge locked in someone else's head.

### What to Extract (Priority Order)

**Session 0 — Get the files:**
- Hydraulics calculation workbook (Manning's HFL, afflux, backwater)
- Hydrology calculation workbook (SCS CN, Rational Method, Tc)
- GIS/watershed calculation templates
- Standard DPR report template for bridge hydrology

**Session 1 — GIS and Hydrology judgment calls:**
- DEM source (SRTM 30m / Cartosat 10m / ALOS 12.5m?)
- Time of concentration formula (Kirpich / Bransby-Williams / SCS lag?)
- SCS Curve Number table for Indian land cover and soil groups
- Hydrological Soil Group assignment for Indian soils
- AMC default (AMC-II or adjusted?)
- Rational Method C values by land cover
- CWC regional zone for MPSB catchments
- Design storm return period by structure type

**Session 2 — Hydraulics and standards:**
- Manning's n values for natural streams, engineered channels, culverts
- Afflux limit under IRC:5-2015
- Freeboard above HFL for bridge soffit
- HEC-RAS cross-section setup for bridge crossings
- Scour depth method (Lacey's / IRC:78 / Grip's)
- IS and IRC codes that govern: IS:5477, IS:4890, IRC:5, IRC:6, IRC:78, IRC:SP:13
- MPSB project specifics — sites, rivers, catchment sizes, why satellite data

**Full checklist:** `docs/sme-extraction-checklist.md` and `.pdf`

---

## Part 5 — The Venture Studio Model

### Structure

This is not two simultaneous ventures. It is a **sequenced studio**:

```
Phase 1 (now)        →   Phase 2 (after traction)
pibuilder                Cold chain logistics
EPC hydrology SaaS       Operated by Nancy Narayan
```

### Budget

₹3.5–5 crores allocated across the studio pipeline. Sufficient for Phase 1
(full pibuilder build + first customers) if spent without distraction.

### The $100M Exit Path

A Python library is worth nothing. The same algorithms as a platform — automating
EPC hydrology workflows done manually in Excel across thousands of bridge and road
projects in India and Southeast Asia — is a different story.

**The market:** India's EPC infrastructure market exceeds $150B. Every bridge,
culvert, road, airport, and railway project requires a hydrology design submission.
These are currently done by engineers running Excel sheets, one project at a time.

**The moat:** Validated algorithms (13 tests, Excel-proven), Indian regulatory
compliance built-in (IS:5477, IRC:5-2015, CWC), satellite data integration,
no gauge dependency.

**Likely acquirers at exit:** Bentley Systems, Autodesk Infrastructure, ESRI,
or a large Indian EPC firm (L&T, Sterlite, Dilip Buildcon). Strategic acquirers
pay 8–12x ARR for compliance-heavy, domain-specific infrastructure software.

**The ceiling is real — but the full stack must be working first.**

---

## Part 6 — Nancy Narayan and the Cold Chain Venture

### Who She Is

**Nancy Narayan** — Sales Manager, CMA CGM, Dubai (May 1999–present).

- 25 years at one of the world's top 3 container shipping lines
- Grew freight volume from 5,000–15,000 TEUs (2014) to ~100,000 TEUs (2024)
- Improved repeat business from 20% to 65%
- Deep network: freight agents, forwarders, container ops, rate negotiation
- Career: Logistics Executive → Customer Service Supervisor → Asst. Sales
  Manager → Sales Manager

### Why This Is an Asset, Not a Subsidy Play

The 3% NHB loans and government cold chain subsidies are attractive. They are
also available to every competitor. Nancy's 25-year CMA CGM network — agent
relationships, freight pricing intelligence, port ops knowledge — is not.

That is the moat. Build around her, not around the subsidy.

### Open Questions Before Committing

- Is she planning to leave CMA CGM, and on what timeline?
- Will she operate from India or remotely from Dubai?
- Does she have India-specific cold storage and freight contacts, or primarily UAE/international?
- Written agreement on roles, equity, decision rights, and exit terms — before
  the first rupee moves. A 25-year career means strong opinions. That is an
  asset and a potential collision point. Document it early.

### Sequencing

Cold chain does not start until pibuilder has traction — paying customers and
proven unit economics. Any earlier and the studio model collapses into two
underfunded, distracted ventures.

---

## Part 7 — Staged Project Plan

### Stage 1 — Core Rainfall Engine ✓ Done

Rainfall frequency analysis, IDF tables, CLI query tool, SME spec PDF.
Validated against MPSB + Indargarh Excel. 13 tests passing.

### Stage 2 — Complete the Calculation Stack (3–4 months)

Implement remaining engines in dependency order, each built TDD against
Excel ground truth extracted by Sudesna **before** coding begins:

1. GIS engine — watershed delineation (WhiteboxTools D8), basin area, slope,
   longest flow path
2. Hydrology engine — SCS CN runoff depth, Rational Method + SCS peak discharge
3. Hydraulics engine — Manning's HFL, afflux, freeboard (IRC:5-2015)
4. Data pipeline — DEM, shapefile, rainfall raster ingestion and ETL

**Gate:** SME extraction must complete before Stage 2 starts.

### Stage 3 — Automated Report Generation (1–2 months)

Jinja2/WeasyPrint PDF reports: design basis, distribution selection, HFL tables,
freeboard calculations. This is what an engineer submits to a client.
Automating it is the first visible, billable time saving.

### Stage 4 — API and Multi-Project Platform (2–3 months)

FastAPI service layer. Move from single-project scripts to a platform that
runs analyses for many bridge/culvert sites in batch. Add lightweight web UI
or REST API. This is where it becomes a product, not a library.

### Stage 5 — First Paying Customers (3–6 months)

- SaaS pricing per project or per seat
- 3–5 EPC pilot customers (Indian market first — regulatory alignment built in)
- Audit trail and version control for design values (regulatory requirement)
- ISO/BIS compliance documentation

### Stage 6 — Scale or Exit (12–24 months post Stage 5)

Raise a Series A on ARR, or approach strategic acquirers. The asset at this
point: validated algorithms, regulatory compliance, paying EPC customers,
and a defensible moat.

---

## Part 8 — Key Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| SME contact ends before extraction | Critical | Run extraction sessions immediately — this week |
| Budget split across ventures too early | High | Cold chain starts only after pibuilder traction |
| Nancy not available / not relocating | Medium | Confirm availability and terms before building plans around her |
| No paying customers validate the model | High | Stage 5 gate — get 3 paying customers before scaling |
| Regulatory changes to IRC/IS codes | Low | Engine is parameterised — update constants, not architecture |

---

## Part 9 — Immediate Next Actions

1. **This week:** Contact Sudesna. Frame it professionally and narrowly —
   "one or two sessions to transfer project files before we wrap up." Not a
   relationship repair. A knowledge rescue.

2. **Get the files first** (Priority 0 in checklist) — hydraulics, hydrology,
   watershed workbooks. Everything else can be reconstructed from published
   standards. Her Excel judgments cannot.

3. **Confirm Nancy's availability and timeline** before the cold chain venture
   features in any investor conversation.

4. **Start Stage 2** only after the extraction checklist is substantially complete.

---

## Appendix — Key References

| Reference | Used for |
|---|---|
| Wilson & Hilferty (1931). *PNAS* 17(12). | Exact K_T formula |
| Gumbel, E.J. (1958). *Statistics of Extremes*. | Gumbel EV1 |
| Chow, Maidment & Mays (1988). *Applied Hydrology*. McGraw-Hill. | General frequency analysis |
| IS:5477 Part 4 (1971). Bureau of Indian Standards. | LP3 as Indian hydrology standard |
| CWC (2002). *Flood Estimation — Western Himalayas Zone 7*. | Duration scaling exponent 1/3 |
| IRC:5-2015. | Standard Specifications for Road Bridges |
| IRC:SP:13. | Guidelines for the Design of Small Bridges and Culverts |
