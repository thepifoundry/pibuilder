"""
TDD: Gumbel 100yr RP must match:
1. MPSB Excel 'Gumbel 100yr RP' column (grid-based annual max).
2. Indargarh 'Rainfall Analysis' final intensity table (gauge-based).
"""

import numpy as np
import pytest
from pibuilder.rainfall.frequency import fit_gumbel
from pibuilder.rainfall.intensity import gumbel_intensity_table, duration_intensity


TOLERANCE_RP = 0.01      # mm for return period rainfall
TOLERANCE_INTENSITY = 0.001  # mm/hr for intensity


class TestGumbelMPSB:
    """Gumbel 100yr RP must match MPSB Excel for all grid points."""

    # Excel bug: cell (27.875, 89.125) uses STDEVP (population std) instead of STDEV.
    # Our implementation is correct (ddof=1 = STDEV). Expected = our ddof=1 value.
    BUGGY_EXCEL_POINT = (27.875, 89.125)

    def test_gumbel_first_grid_point(self, mpsb_grid_data):
        """Regression: first grid point (27.875, 89.125) with correct ddof=1."""
        data = mpsb_grid_data[(27.875, 89.125)]
        rp, _ = fit_gumbel(data)
        expected = 166.19878425484214  # ddof=1; Excel has STDEVP bug → 164.121
        assert abs(rp - expected) < TOLERANCE_RP, f"Gumbel RP: got {rp:.4f}, expected {expected:.4f}"

    def test_gumbel_all_grid_points(self, mpsb_grid_data, mpsb_ground_truth):
        """Gumbel 100yr RP matches Excel for all MPSB grid points (excluding known Excel STDEVP bug)."""
        failures = []
        for gt in mpsb_ground_truth:
            lat, lon = gt["lat"], gt["lon"]
            if (lat, lon) == self.BUGGY_EXCEL_POINT:
                continue  # Excel uses STDEVP for this cell — known bug, skip
            expected = gt["gumbel"]["rp"]
            if expected is None or (lat, lon) not in mpsb_grid_data:
                continue
            data = mpsb_grid_data[(lat, lon)]
            rp, _ = fit_gumbel(data)
            diff = abs(rp - expected)
            if diff > TOLERANCE_RP:
                failures.append(f"({lat},{lon}): got {rp:.4f}, expected {expected:.4f}, diff={diff:.4f}")

        assert not failures, f"Gumbel mismatch at {len(failures)} points:\n" + "\n".join(failures[:10])


class TestGumbelIndargarh:
    """
    Indargarh gauge station: Gumbel applied to intensity series (not daily rainfall).
    Ground truth: rows 53-57 of 'Rainfall Analysis' sheet.
    """

    def test_100yr_1h_intensity(self, indargarh_daily_max, indargarh_ground_truth):
        """100yr 1H intensity = 83.729 mm/hr (Indargarh ground truth)."""
        table = gumbel_intensity_table(indargarh_daily_max, return_periods=[100], durations_hr=[1])
        got = table[1][100]
        expected = indargarh_ground_truth[1][100]
        assert abs(got - expected) < TOLERANCE_INTENSITY, (
            f"1H 100yr intensity: got {got:.4f}, expected {expected:.4f}"
        )

    def test_full_intensity_table(self, indargarh_daily_max, indargarh_ground_truth):
        """All durations × all return periods must match Indargarh Excel."""
        table = gumbel_intensity_table(
            indargarh_daily_max,
            return_periods=[2, 5, 10, 50, 100],
            durations_hr=[1, 2, 6, 12, 24],
        )
        failures = []
        for dur, period_map in indargarh_ground_truth.items():
            for T, expected in period_map.items():
                if expected is None:
                    continue
                got = table[dur][T]
                diff = abs(got - expected)
                if diff > TOLERANCE_INTENSITY:
                    failures.append(f"dur={dur}H T={T}yr: got {got:.5f}, expected {expected:.5f}, diff={diff:.5f}")

        assert not failures, f"Intensity table mismatch:\n" + "\n".join(failures)

    def test_duration_scaling_formula(self):
        """P_t = P_24 * (t/24)^(1/3) — verify the CWC scaling law directly."""
        p_24 = 100.0
        # 1H: 100 * (1/24)^(1/3) = 100 * 0.3467 = 34.67 mm
        p_1h = 100.0 * (1.0 / 24.0) ** (1.0 / 3.0)
        intensity_1h = p_1h / 1.0
        # cross-check against direct call
        from pibuilder.rainfall.intensity import duration_intensity
        assert abs(duration_intensity(p_24, 1) - intensity_1h) < 1e-10

    def test_indargarh_data_length(self, indargarh_daily_max):
        """Should load 32 years of data (1990-2021)."""
        assert len(indargarh_daily_max) == 32, f"Expected 32 years, got {len(indargarh_daily_max)}"
