# PI Builder – Engineering Spec

PI Builder is a geospatial platform for automated hydrology analysis used in infrastructure planning (bridges, culverts, drainage systems).

This documentation set provides the **technical blueprint for building the platform**.

---

# Documentation Index

## Product Context

- [EPC Hydrology Workflow](epc-hydrology-workflow.md)

## System Architecture

- [System Architecture](system-architecture.md)
- [Geospatial Processing Architecture](geospatial-processing-architecture.md)

## Core Engines

### GIS

- [GIS Engine](gis-engine.md)
- [DEM Processing Pipeline](dem-processing-pipeline.md)
- [Watershed Algorithm Specification](watershed-algorithm-spec.md)

### Rainfall Analysis

- [Rainfall Engine](rainfall-engine.md)
- [Rainfall Frequency Analysis](rainfall-frequency-analysis.md)
- [Rainfall Data Pipeline](rainfall-data-pipeline.md)

### Hydrology

- [Hydrology Engine](hydrology-engine.md)
- [Discharge Calculation Methods](discharge-calculation-methods.md)

### Hydraulics

- [Hydraulics Engine](hydraulics-engine.md)
- [HFL Calculation Methods](hfl-calculation-methods.md)

---

## Engineering

- [Engineering Principles](engineering-principles.md)
- [Repository Structure](repo-structure.md)

---

## Execution

- [MVP Roadmap](mvp-roadmap.md)
- [Engineering Task Breakdown](engineering-task-breakdown.md)

---

## SME Collaboration

- [SME Knowledge Extraction Guide](sme-knowledge-extraction.md)

---

# Recommended Reading Order

For new engineers joining the project:

1. EPC Hydrology Workflow
2. System Architecture
3. Geospatial Processing Architecture
4. GIS Engine
5. Rainfall Engine
6. Hydrology Engine
7. Hydraulics Engine
8. MVP Roadmap

---

# Goal of the Platform

The goal of PI Builder is to automate the workflow:

Coordinate  
→ Catchment extraction  
→ Rainfall analysis  
→ Runoff estimation  
→ Flood discharge  
→ High Flood Level  
→ Hydrology report
