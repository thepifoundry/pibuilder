# Watershed Algorithm Specification

Steps:

1. Load DEM raster
2. Fill sinks in DEM
3. Compute flow direction grid
4. Compute flow accumulation grid
5. Apply stream threshold
6. Extract drainage network
7. Delineate watershed upstream of outlet