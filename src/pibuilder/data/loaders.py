"""
Data ingestion layer — DEM, shapefiles, and rainfall rasters.

Responsibilities
----------------
- Load Digital Elevation Model (DEM) rasters from GeoTIFF files using rasterio.
  DEMs are the primary input for watershed delineation and slope calculation.
- Load basin / catchment boundary shapefiles (GeoPackage or shapefile format)
  using geopandas.  Boundaries are used to clip DEMs and aggregate rainfall.
- Load satellite rainfall grids (MPSB format) from Excel or netCDF.
  Each grid point has 20 annual-maximum daily rainfall values (2000-2019).
- Load gauge station daily rainfall records (e.g. Indargarh) from Excel.

All loaders return data in a consistent coordinate reference system (CRS).
The project standard is EPSG:4326 (WGS-84 geographic) for interchange; rasterio
operations may reproject to UTM internally for area/distance calculations.

NOT YET IMPLEMENTED.  This module is a placeholder for the data pipeline sprint.
See docs/dem-processing-pipeline.md and docs/rainfall-data-pipeline.md.
"""
