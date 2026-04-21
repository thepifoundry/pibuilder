"""
pibuilder — EPC Hydrology Intelligence Platform.

Package structure
-----------------
pibuilder.rainfall
    Frequency analysis (LP3, Gumbel, Normal, Log-Normal, Pearson III),
    duration scaling, and IDF table generation.

pibuilder.gis
    DEM-based watershed delineation (WhiteboxTools) and basin geometry
    extraction (area, slope, longest flow path).

pibuilder.hydrology
    SCS Curve Number runoff depth and Rational Method / SCS peak discharge.

pibuilder.hydraulics
    High Flood Level computation via Manning's equation and afflux estimation.

pibuilder.data
    Loaders for DEM, shapefiles, and rainfall grids; ETL transforms
    (reproject, clip, resample, gap-fill).

pibuilder.api
    FastAPI service layer exposing the analysis pipeline as REST endpoints.

pibuilder.report
    Jinja2 / WeasyPrint PDF report generation for EPC submission packages.

Status
------
Rainfall engine (pibuilder.rainfall) is fully implemented and tested against
the MPSB Excel ground truth.  All other sub-packages are placeholders pending
their respective implementation sprints.
"""
