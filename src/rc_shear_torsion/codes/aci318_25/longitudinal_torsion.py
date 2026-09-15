from __future__ import annotations

import math

MAX_LONGITUDINAL_TORSION_BAR_SPACING_MM = 300.0
MIN_LONGITUDINAL_TORSION_BAR_DIAMETER_MM = 10.0
LONGITUDINAL_TORSION_DIAMETER_SPACING_FACTOR = 0.042


def vertical_distribution_range_mm(*, height_mm: float, d_mm: float) -> float:
    """Distance between existing top and bottom longitudinal steel lines."""
    return height_mm - 2.0 * (height_mm - d_mm)


def longitudinal_torsion_bar_spacing_mm(
    *,
    height_mm: float,
    d_mm: float,
    total_torsion_bar_count: int,
) -> float | None:
    """ACI 318-25 9.7.5.1 spacing for intermediate bars on each side face."""
    if total_torsion_bar_count < 0 or total_torsion_bar_count % 2 != 0:
        return None
    vertical_range_mm = vertical_distribution_range_mm(
        height_mm=height_mm,
        d_mm=d_mm,
    )
    return vertical_range_mm / (0.5 * float(total_torsion_bar_count) + 1.0)


def minimum_longitudinal_torsion_bar_count(
    *,
    height_mm: float,
    d_mm: float,
) -> int:
    """Smallest even count satisfying the adopted 300 mm distribution limit."""
    vertical_range_mm = vertical_distribution_range_mm(
        height_mm=height_mm,
        d_mm=d_mm,
    )
    bars_per_side = max(
        0,
        math.ceil(vertical_range_mm / MAX_LONGITUDINAL_TORSION_BAR_SPACING_MM - 1.0),
    )
    return 2 * bars_per_side


def minimum_longitudinal_torsion_bar_diameter_mm(
    transverse_spacing_mm: float,
) -> float:
    """ACI 318-25 9.7.5.2 minimum longitudinal torsional bar diameter."""
    return max(
        LONGITUDINAL_TORSION_DIAMETER_SPACING_FACTOR * transverse_spacing_mm,
        MIN_LONGITUDINAL_TORSION_BAR_DIAMETER_MM,
    )
