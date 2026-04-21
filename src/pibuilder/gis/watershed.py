"""
DEM-based watershed delineation using WhiteboxTools.

Workflow
--------
The standard hydrological conditioning and delineation pipeline:

1. **Fill sinks** (WBT: FillDepressions or BreachDepressions)
   Removes spurious low points that would trap flow.  Breaching is preferred
   for near-flat terrain; filling is used where breaching creates unrealistic
   channels.

2. **Flow direction** (WBT: D8Pointer)
   Computes the D8 (eight-direction) flow direction raster from the
   conditioned DEM.  Each cell drains to the steepest downslope neighbour.

3. **Flow accumulation** (WBT: D8FlowAccumulation)
   Accumulates upstream contributing cells.  The outlet point is identified
   as the cell with the maximum accumulation within the project boundary.

4. **Stream network** (WBT: ExtractStreams)
   Thresholds the accumulation raster to extract the channel network.
   Threshold is calibrated to match mapped watercourses (typically 1–5% of
   maximum accumulation depending on DEM resolution).

5. **Watershed** (WBT: Watershed)
   Delineates the contributing area draining to the outlet point.  Output
   is a raster mask; vectorised with rasterio/shapely for downstream use.

Ground truth
------------
Basin boundaries are cross-checked against Survey of India topographic sheets
and the project's cadastral shapefile.  Allowable area error: ±2%.

NOT YET IMPLEMENTED.  See docs/watershed-algorithm-spec.md for full spec.
"""
