"""
Command-line tool: look up the 100-year design rainfall for a coordinate.

Usage
-----
    python scripts/rainfall_query.py <lat> <lon>

Example
-------
    python scripts/rainfall_query.py 29.0 88.5

The tool finds the nearest MPSB grid point (0.25° spacing), runs the full
five-distribution frequency analysis, and prints the selected 100-year
return-period rainfall in mm along with which distribution was chosen and
the goodness-of-fit results for all five distributions.

Grid coverage: lat 27.875–31.125°N, lon 82.125–95.625°E (Himalayan region).
Nearest-point search uses Euclidean distance in degrees (adequate at this scale).
"""

import sys
import json
import math
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pibuilder.rainfall.frequency import run_frequency_analysis
import numpy as np

FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures"


def load_grid():
    records = json.loads((FIXTURES / "mpsb_grid_data.json").read_text())
    return {(r["lat"], r["lon"]): np.array(r["values"], dtype=float) for r in records}


def nearest_point(grid: dict, lat: float, lon: float):
    best_pt = min(grid.keys(), key=lambda pt: math.hypot(pt[0] - lat, pt[1] - lon))
    dist_deg = math.hypot(best_pt[0] - lat, best_pt[1] - lon)
    dist_km = dist_deg * 111.0  # rough conversion
    return best_pt, dist_km


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/rainfall_query.py <lat> <lon>")
        print("Example: python scripts/rainfall_query.py 29.0 88.5")
        sys.exit(1)

    try:
        query_lat = float(sys.argv[1])
        query_lon = float(sys.argv[2])
    except ValueError:
        print("Error: lat and lon must be numbers.")
        sys.exit(1)

    grid = load_grid()
    (grid_lat, grid_lon), dist_km = nearest_point(grid, query_lat, query_lon)
    data = grid[(grid_lat, grid_lon)]

    result = run_frequency_analysis(data)

    print()
    print(f"  Query:        ({query_lat}, {query_lon})")
    print(f"  Nearest grid: ({grid_lat}, {grid_lon})  [{dist_km:.1f} km away]")
    print(f"  Data years:   {result.n}  (annual-max daily rainfall, mm)")
    print()
    print(f"  ┌─────────────────────────────────────────────────────────┐")
    print(f"  │  100-year design rainfall:  {result.selected_rp_100yr:>8.1f} mm              │")
    print(f"  │  Selected distribution:     {result.selected_method.value:<20s}       │")
    print(f"  └─────────────────────────────────────────────────────────┘")
    print()
    print("  All distributions:")
    print(f"  {'Distribution':<16} {'100yr RP (mm)':>14} {'Chi-sq':>8} {'KS':>6} {'Selected':>10}")
    print(f"  {'-'*16} {'-'*14} {'-'*8} {'-'*6} {'-'*10}")
    for fit in result.fits:
        rp_str = f"{fit.rp_100yr:.2f}" if not math.isnan(fit.rp_100yr) else "   ERROR"
        chi = "PASS" if fit.chi_sq_pass else "FAIL"
        ks = "PASS" if fit.ks_pass else "FAIL"
        sel = "<-- SELECTED" if fit.distribution == result.selected_method else ""
        print(f"  {fit.distribution.value:<16} {rp_str:>14} {chi:>8} {ks:>6} {sel}")
    print()


if __name__ == "__main__":
    main()
