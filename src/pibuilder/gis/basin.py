"""
Basin geometry computation from a watershed polygon.

Computes the physical characteristics of a delineated catchment that are
required as inputs to the hydrology and hydraulics engines:

Catchment area (A)
    Planimetric area of the watershed polygon in km².
    Computed by reprojecting to the appropriate UTM zone and using
    shapely geometry area.  Used directly in the Rational Method: Q = C·i·A.

Centroid (lat, lon)
    Geographic centroid of the watershed (EPSG:4326).
    Used to select the MPSB grid point(s) nearest to the catchment for
    rainfall frequency analysis.

Longest flow path (L)
    Length of the main channel from the most remote point to the outlet, in km.
    Derived from the flow direction raster (see watershed.py).
    Used in the time of concentration formula: Tc = f(L, slope, roughness).

Mean slope (S)
    Average slope along the longest flow path (m/m).
    Extracted from the DEM along the channel centreline.
    Used in time of concentration and Manning's equation.

Hypsometric curve
    Elevation–area relationship of the catchment.
    Derived by zonal statistics on the clipped DEM.
    Used for snowmelt and storage routing (future sprint).

NOT YET IMPLEMENTED.  See docs/gis-engine.md for full specification.
"""
