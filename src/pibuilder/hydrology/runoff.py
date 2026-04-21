"""
Runoff depth estimation using the SCS Curve Number method.

Theory
------
The SCS (Soil Conservation Service, now NRCS) Curve Number (CN) method
estimates direct runoff depth Q from rainfall depth P:

    S  = (25400 / CN) − 254      (potential maximum retention, mm)
    Ia = 0.2 × S                 (initial abstraction, mm)
    Q  = (P − Ia)² / (P − Ia + S)   for P > Ia, else 0

where CN is a dimensionless parameter (0–100) reflecting soil type,
land use, and antecedent moisture condition (AMC).

Curve Number selection
----------------------
CN values for the project watershed are obtained from the MPSB soil survey
and land-use map.  Composite CN for a mixed catchment is the area-weighted
average of individual land-use polygon CNs.

AMC classes:
- AMC I  (dry):    CN_I  = CN_II × 4.2 / (10 − 0.058 × CN_II)
- AMC II (normal): CN_II (tabulated value)
- AMC III (wet):   CN_III = CN_II × 23 / (10 + 0.13 × CN_II)

Design standard uses AMC II unless the SME specifies otherwise.

Outputs
-------
Runoff depth Q in mm.  Feeds into the SCS peak discharge formula in
discharge.py (Q_p = q_u × A × Q_r) or is used directly with the
Rational Method as a check.

NOT YET IMPLEMENTED.  See docs/hydrology-engine.md.
"""
