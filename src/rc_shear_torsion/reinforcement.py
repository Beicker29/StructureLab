"""Existing reinforcing-bar catalog and mass conversions, in mm and kg.

The allowed input labels intentionally remain narrower than the full catalog.
Values and fallback calculations are preserved from models.py and design.py.
"""
from __future__ import annotations

ALLOWED_BAR_LABELS = ("#2", "#3", "#4", "#5", "#6", "#7", "#8", "#9", "#10", "#11")
BAR_DIAMETERS_MM: dict[str, float] = {
    "#2": 6.4,
    "#3": 9.5,
    "#4": 12.7,
    "#5": 15.9,
    "#6": 19.1,
    "#7": 22.2,
    "#8": 25.4,
    "#9": 28.7,
    "#10": 32.3,
    "#11": 35.8,
    "#14": 43.0,
    "#18": 57.3,
}

BAR_AREAS_MM2: dict[str, float] = {
    "#2": 32.0,
    "#3": 71.0,
    "#4": 129.0,
    "#5": 199.0,
    "#6": 284.0,
    "#7": 387.0,
    "#8": 510.0,
    "#9": 645.0,
    "#10": 819.0,
    "#11": 1006.0,
    "#14": 1452.0,
    "#18": 2581.0,
}

BAR_MASS_KG_PER_M: dict[str, float] = {
    "#2": 0.250,
    "#3": 0.560,
    "#4": 0.994,
    "#5": 1.552,
    "#6": 2.235,
    "#7": 3.042,
    "#8": 3.973,
    "#9": 5.060,
    "#10": 6.404,
    "#11": 7.907,
    "#14": 11.380,
    "#18": 20.240,
}
STEEL_DENSITY_KG_PER_MM3 = 7.85e-6


def bar_mass_kg_per_m(bar: str | None, count: int = 1) -> float:
    if count <= 0:
        return 0.0
    unit_mass = BAR_MASS_KG_PER_M.get(bar)
    if unit_mass is not None:
        return float(unit_mass) * float(count)

    area = BAR_AREAS_MM2.get(bar)
    if area is None or area <= 0.0:
        return 0.0
    return longitudinal_mass_kg_per_m(area * float(count))


def longitudinal_mass_kg_per_m(long_provided_mm2: float) -> float:
    return long_provided_mm2 * 1000.0 * STEEL_DENSITY_KG_PER_MM3
