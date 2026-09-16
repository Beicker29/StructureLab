from __future__ import annotations

from typing import Any


def transverse_alternative_rank_key(
    *,
    weight_kg: float | None,
    spacing_mm: float | int | None,
    stable_tie_break: tuple[Any, ...] = (),
) -> tuple[Any, ...]:
    """Rank feasible transverse alternatives by regional weight, then spacing.

    Exact numeric values are used: presentation rounding does not create weight
    ties.  ``stable_tie_break`` is only consulted after the mandatory criteria.
    """

    weight_rank = float(weight_kg) if weight_kg is not None else float("inf")
    spacing_rank = -float(spacing_mm) if spacing_mm is not None else float("inf")
    return (weight_rank, spacing_rank, *stable_tie_break)
