"""
ETL (Extract-Transform-Load) transforms for geospatial and rainfall data.

Responsibilities
----------------
- **Reproject**: Convert rasters and vector data between CRS using rasterio /
  pyproj / geopandas.  Standard pipeline: source CRS → EPSG:4326 for storage,
  UTM zone (auto-detected from centroid) for metric calculations.
- **Clip**: Mask a DEM or rainfall raster to a catchment boundary polygon.
  Uses rasterio.mask with the basin shapefile geometry.
- **Resample**: Change DEM resolution (e.g. 30 m SRTM → 10 m for WhiteboxTools
  fill-and-drain).  Uses rasterio reproject with bilinear resampling.
- **Gap-fill**: Interpolate missing rainfall values in the satellite grid using
  nearest-neighbour or inverse-distance weighting.  Only applied where the
  MPSB Excel grid has NaN cells (rare — typically <1% of nodes).
- **Aggregate**: Compute catchment-average rainfall from the 0.25° MPSB grid
  using areal weights (Thiessen polygon or simple grid-cell intersection).

NOT YET IMPLEMENTED.  This module is a placeholder for the data pipeline sprint.
See docs/dem-processing-pipeline.md and docs/data-flow-architecture.md.
"""
