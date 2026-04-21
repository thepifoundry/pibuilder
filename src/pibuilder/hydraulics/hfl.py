"""
High Flood Level (HFL) computation for bridge and culvert design.

The HFL is the water surface elevation at the bridge site corresponding to
the design flood discharge (typically 100-year return period).  It determines
the minimum soffit level of the bridge deck.

Manning's Equation (normal depth)
----------------------------------
For a prismatic channel cross-section the normal depth y_n satisfying
Manning's equation is found iteratively:

    Q = (1/n) × A(y) × R(y)^(2/3) × S^(1/2)

where:
    Q    = design discharge (m³/s), from discharge.py
    n    = Manning's roughness coefficient (dimensionless)
    A(y) = cross-sectional flow area at depth y (m²)
    R(y) = hydraulic radius = A(y) / P(y) (m)
    P(y) = wetted perimeter (m)
    S    = longitudinal bed slope (m/m)

The equation is solved numerically (bisection or Newton-Raphson) for y.

Cross-section geometry
-----------------------
Survey cross-sections are digitised from site surveys.  The geometry is
stored as paired (station, elevation) arrays.  Area and perimeter are
computed by trapezoidal integration at any trial water depth.

Afflux
------
The HFL at the bridge site may differ from the normal depth in the
unconstricted channel due to bridge abutment contraction.  The Nagler
formula or the Indian Roads Congress (IRC:5) method is used to estimate
afflux and add it to the normal depth.

Freeboard
---------
Final bridge soffit = HFL + afflux + design freeboard (typically 0.60 m
for plain reaches, 0.90 m for hilly streams per IRC:5-2015).

NOT YET IMPLEMENTED.  See docs/hfl-calculation-methods.md and
docs/hydraulics-engine.md.
"""
