"""
Peak discharge computation: Rational Method and SCS Unit Hydrograph.

Rational Method
---------------
The primary design method used in the MPSB EPC project for catchments up to
~25 km²:

    Q = (C × i × A) / 3.6

where:
    Q  = peak discharge (m³/s)
    C  = runoff coefficient (dimensionless, 0–1)
    i  = design rainfall intensity for duration = Tc (mm/hr)
    A  = catchment area (km²)
    3.6 = unit conversion factor (mm/hr × km² → m³/s)

The rainfall intensity i is obtained from the frequency analysis engine
(intensity.py) at the return period specified by the design standard
(typically 100 years for bridge design).

The time of concentration Tc is computed using the Kirpich formula:
    Tc = 0.0195 × L^0.77 × S^(-0.385)   (minutes)
where L is the longest flow path (m) and S is the mean slope (m/m).

Runoff coefficient C
    Tabulated by land use and soil group per IS:5477 / CWC guidelines.
    For ungauged Himalayan catchments the MPSB project uses C = 0.55–0.70
    depending on vegetation density and slope.

SCS Peak Discharge (future)
----------------------------
For larger catchments (> 25 km²) or where a hydrograph shape is required:
    Q_p = q_u × A × Q_r × F_pond

where q_u is the unit peak discharge (m³/s/km²/mm) from the dimensionless
unit hydrograph, Q_r is SCS runoff depth (from runoff.py), and F_pond is a
pond/swamp adjustment factor.

NOT YET IMPLEMENTED.  See docs/discharge-calculation-methods.md.
"""
