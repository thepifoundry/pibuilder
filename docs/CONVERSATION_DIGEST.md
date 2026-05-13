# PI Builder — Conversation Digest
## Key Decisions and Refinements (May 2026)

This document captures everything from the founding strategy conversation that is
directly relevant to building PI Builder. Claude Code should read this alongside
the user stories to understand WHY certain decisions were made.

---

## 1. The Core UX Vision

**One click on the map. Five minutes. Full DPR-compliant report.**

The engineer clicks a coordinate on a map. The system:
- Delineates the catchment from CartoDEM
- Retrieves IMD rainfall (66 years)
- Fits 5 distributions, selects best-fit with GoF rationale
- Runs 3-4 discharge methods (appropriate to region + catchment size)
- Solves Manning's for HFL
- Computes Lacey scour
- Generates a 40-60 page DPR-format PDF

Every parameter the engineer would normally choose is decided autonomously by the
system with a written rationale and textbook citation. The engineer reviews and
optionally overrides specific decisions. Regeneration from override takes <30 seconds
(cached intermediates re-used).

This is NOT a tool where the engineer picks the distribution, enters parameters,
runs each step. That's the old model (Bentley, CivilGEO, HEC-RAS). PI Builder's
model is: system decides, engineer reviews.

---

## 2. Textbook-First, Not Excel-First

**Critical framing that affects every formula implementation:**

The L&T Excel files (Indargarh, MPSB) are validation test cases, not methodology sources.

- PI Builder implements **published IRC/IS codes and standard textbooks**
- The Excel sheets validate that our implementation is correct
- Where L&T's Excel diverges from the published standard, **the standard wins**
- This makes the system defensible in court, certifiable by IRC, usable by all consultancies

Every formula in code traces to a citation in `docs/06_authoritative_sources.md`.
The docstring pattern is mandatory — not optional.

---

## 3. Global Architecture from Day 1

PI Builder starts in India but is designed for global deployment from the first commit.

**What this means in code:**

```python
# Data sources: adapter pattern
class RainfallDataSource(ABC):
    @abstractmethod
    def get_annual_maxima(self, lat, lon, start_year, end_year): ...

class IMDAdapter(RainfallDataSource): ...      # India
class BMKGAdapter(RainfallDataSource): ...     # Indonesia
class TMDAdapter(RainfallDataSource): ...      # Thailand

# Design codes: pluggable config
class StandardsEngine(ABC):
    @abstractmethod
    def get_return_period(self, project_type): ...
    @abstractmethod
    def get_runoff_coefficients(self, land_use, soil_group): ...

class IRCSp13_2022(StandardsEngine): ...       # India
class AASHTO_LRFD(StandardsEngine): ...        # Americas
```

Nothing India-specific is hardcoded in core engines.
India-specific implementations live in `src/pi_builder/adapters/` and `src/pi_builder/standards/irc/`.

---

## 4. Competitive Landscape

**Rain2Flood (QGIS plugin):** Exists. Does IMD/CHIRPS retrieval + Gumbel/LP3/GEV + SCS-CN.
26 votes on QGIS plugin registry. NOT a serious commercial threat — no validation corpus,
no DPR reports, no IRC compliance, no enterprise UX, no support contract. Validates
that the ingredients work. Does not validate that a product exists.

**CivilGEO (GeoHECRAS/GeoHECHMS):** G2 Leader, wraps HEC-RAS/HEC-HMS with AutoCAD UI.
Proves market pays for hydrology workflow automation. Does NOT do rainfall frequency analysis
(the bottleneck step). PI Builder goes upstream of CivilGEO. Complementary, not competitive.

**AQUAH (CU Boulder, ICCV 2025):** AI agent for US hydrology — drives HEC-HMS autonomously
from natural language. Formally published Oct 2025. US-focused, US data sources.
Direct validation of our thesis. The Indian-context equivalent is wide open.
Expect US commercialization within 18-24 months — that's the competitive clock.

**Bentley / Autodesk:** Deep pockets, existing customer base, investing in AI.
Not building Indian-context tools. The real risk is they acquire a Rain2Flood-style stack
and bundle it. By then, we need 300+ bridge corpus and IRC endorsement as the moat.

---

## 5. IRC SP-13 Is 2022, Not 2004

Every reference to IRC SP-13 in code, docs, and reports must say **IRC SP-13:2022**.
The 2004 edition has been superseded. Using stale code references signals amateur
in any customer or regulatory conversation.

Purchase from: irc.gov.in (also IRC:5-2015, IRC:78-2014)

---

## 6. The Discharge Decision Table

Multi-method is mandatory. The recommendation engine (Story 4.8) uses this table:

| Catchment Area | Region/State | Methods to Run | Recommended |
|---|---|---|---|
| < 25 sq km | Any | Rational, SCS-CN | Rational |
| 25-500 sq km | Maharashtra / Western Ghats | Rational, SCS-CN, Inglis | Median |
| 25-500 sq km | Northern India (UP/MP/Bihar) | Rational, SCS-CN, Dicken's | Median |
| 25-500 sq km | South Coastal (TN/AP coast) | Rational, SCS-CN, Ryves | Median |
| 500-5000 sq km | Any | SCS-CN, CWC SUH (sub-zone) | CWC SUH if sub-zone data available |
| > 5000 sq km | Any | CWC SUH, observed gauge data | Gauged always > ungauged |

CWC sub-zone mapping must be implemented as a spatial lookup against the CWC
Watershed Atlas of India (shapefile, available from cwc.gov.in).

---

## 7. The Autonomous Decision Logic

The click-to-report flow requires the system to make ~10 decisions autonomously.
Each decision has a documented rationale written into the output report.

Key decisions the system makes (full spec in `docs/07_orchestration.md`):

1. **Catchment outlet** — snap to stream if click is within 50m of stream centerline
2. **DEM source** — CartoDEM v3 R1 first, ALOS AW3D30 fallback, MERIT 90m for >10,000 sq km
3. **Rainfall data** — IMD gridded always; cross-validate with CWC/IMD station if within 10km
4. **Best-fit distribution** — 5 distributions × 2 GoF tests (KS + Chi-square); lowest KS among Pass distributions; fallback Gumbel with warning
5. **Discharge methods** — apply decision table above (item 6)
6. **Curve Number** — NBSS soil × Bhuvan LULC → IRC SP-13:2022 Annex lookup; area-weighted
7. **Time of concentration** — Kirpich + Bransby Williams + California; report median
8. **Manning's n** — Bhuvan LULC land cover at cross-section → Chow (1959) Table 5-6 lookup
9. **Cross-section** — perpendicular to flow at click coordinate from CartoDEM; flag for survey
10. **Scour** — Lacey's regime per IRC SP-13:2022 §6; pier multiplier 1.5 per IRC SP-13:2022 §6.5

---

## 8. Validation Corpus Strategy

The validation corpus is the moat. Target:

**Bootstrap (Week 1, no RTI needed):**
- 26 CWC sub-zone flood estimation reports → 30-40 worked examples
- Academic papers (Springer, ResearchGate, IIT Roorkee) → 10-15 cases
- The 2 L&T Excel files → 2 cases

**RTI pipeline (Weeks 4-12):**
- NHAI bridge DPRs stratified by: Godavari, Krishna, Brahmaputra, Narmada, coastal MH
- Target 40-50 additional cases with full hydrology annexures

**Real flood validation (Weeks 12-20):**
- CWC gauge records for 2018 Kerala, 2020 Hyderabad, 2023 Himachal floods
- Run PI Builder backwards: catchment → predicted Q → compare to gauged Q

The corpus spreadsheet schema is in `docs/DATA_OPS/rti_strategy.md` (Section 7.2).
The backtest engine (Epic 6) automatically runs every new corpus entry through the system.

---

## 9. The Ecosystem and Target Customer

**Primary customer (Year 1-2):** Mid-size private DPR consultancies
Examples: CES, ICT, LEA Associates, Roughton International, Sheladia Associates, SMEC India
They have 20-50 engineers, 50-100 bridge projects/year, no in-house software capability.
Pain is real. Budget exists. Decision cycle is 1-3 months.

**Secondary customer (Year 2-3):** Government-owned consultancies
WAPCOS, RITES — larger, slower, but massive project pipeline.

**Platform play (Year 3+):** When PMC firms (AECOM India, Mott MacDonald, WSP)
use PI Builder to review EPC-submitted hydrology, EPC's consultants are forced to adopt.
You win without a sales call to L&T.

**L&T / Adani / Reliance:** Not Year 1 customers. They are Year 3-4 customers or acquirers.
- L&T: Internal adoption or acquisition (₹50-200cr range)
- Adani: Airports + Roads + Green Energy site assessment
- Reliance: Green Energy site hydrology (Jamnagar complex scale)

---

## 10. Pricing Anchors

For first customer conversations (Week 18+):

- **₹6L/year per consultancy** (unlimited users at one office) — starter price
- **₹25-50K per complex project add-on** — for projects needing advanced analysis
- **₹15-20L/year** for enterprise (large firms, multi-office)
- **₹25L/year** for government PWD/WAPCOS type clients

ROI conversation: "Your hydrology team spends 2-6 weeks per bridge. We compress that to
2 hours. At ₹15L/year per hydrology engineer fully loaded cost, 5 engineers = ₹75L/year.
We cost ₹6L/year and multiply their capacity 10X."

---

## 11. The 10-100X Claim — Use Carefully

**What's true:** 30-70X time reduction on the analysis task itself (2 weeks → 2 hours)
**What's true with caveats:** 3-10X on engineer project throughput (trust builds over 6-18 months)
**What's not true:** 10-100X on overall project lifecycle (analysis is 5-20% of total time)

Use: "10-50X faster hydrology analysis with better validation, applied to more projects
than current economics permit." That's defensible. "10-100X faster bridges" is not.

---

## 12. What CivilGEO Proves

CivilGEO is G2 Leader (8 consecutive years) for civil engineering design software.
They wrap HEC-RAS/HEC-HMS with a CAD interface. Their user reviews say "days → seconds."

**Implication for PI Builder:**
- Market WILL pay for hydrology workflow automation (proven)
- CivilGEO solves HEC-RAS setup (step 3-4 in the workflow)
- PI Builder solves rainfall frequency analysis + discharge (step 1-2)
- We go upstream of CivilGEO and are complementary, not competitive

In customer conversations: "CivilGEO speeds up HEC-RAS. We automate the rainfall analysis
your team still does in Excel before they open CivilGEO. Use both, or use us for standard
projects where HEC-RAS is overkill."

---

## 13. Domain Advisor Requirement

This is not optional. A retired CWC/NHAI/AECOM senior hydrologist at ₹2-3L/month
for 1-2 days/week is the minimum credibility threshold for customer conversations.

They should:
1. Review the discharge method decision table (item 6 above) for accuracy
2. Review the DPR report template and confirm it matches submission standards
3. Validate the first 20 backtest cases before any customer conversation
4. Make first customer introductions (their network > your cold outreach)

Start outreach in Week 1. Contract by Week 3.

---

## 14. Non-Goals (Explicit — Do Not Build for V1)

- Real-time flood forecasting (different product, different customer)
- 2D hydrodynamic modeling (TUFLOW/HEC-RAS 2D equivalent)
- Urban stormwater drainage (IRC SP-50, different customer — ULBs)
- Coastal / tidal hydrology (different physics)
- Groundwater modeling (MODFLOW territory — permanently out of scope)
- Multi-tenancy at MVP (single-org deployment first)
- Mobile-first UI (engineers work on desktops; mobile is read-only viewer)

---

*Generated from founding strategy conversation, May 2026.*
*Replicate faithfully into the repo. Do not summarise further — Claude Code needs the detail.*
