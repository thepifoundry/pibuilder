"""Shared fixtures: load ground truth from JSON fixtures (extracted from Excel once)."""

import json
import pytest
import numpy as np
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def mpsb_ground_truth() -> list[dict]:
    """
    Returns list of dicts from the MPSB summary sheet.
    Each dict: {lat, lon, selected_rp_100yr, adopted_method, per-dist rp+fit flags}
    """
    data = json.loads((FIXTURES / "mpsb_ground_truth.json").read_text())
    return data


@pytest.fixture(scope="session")
def mpsb_grid_data() -> dict:
    """Returns dict (lat, lon) -> np.ndarray of 20 annual max rainfall values."""
    records = json.loads((FIXTURES / "mpsb_grid_data.json").read_text())
    return {(r["lat"], r["lon"]): np.array(r["values"], dtype=float) for r in records}


@pytest.fixture(scope="session")
def indargarh_daily_max() -> np.ndarray:
    """Annual max daily rainfall for Indargarh, 1990-2021 (32 values)."""
    values = json.loads((FIXTURES / "indargarh_daily_max.json").read_text())
    return np.array(values, dtype=float)


@pytest.fixture(scope="session")
def indargarh_ground_truth() -> dict:
    """
    Final intensity table from Indargarh sheet.
    Returns dict: {duration_hr -> {return_period -> intensity_mm_hr}}
    """
    raw = json.loads((FIXTURES / "indargarh_ground_truth.json").read_text())
    return {int(dur): {int(T): v for T, v in periods.items()} for dur, periods in raw.items()}
