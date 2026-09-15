from __future__ import annotations

from .applicability import ApplicabilityStatus, required_fields, torsion_rule_applicability
from .common import (
    RuleCheck,
    SpacingLimit,
    boolean_check,
    not_applicable_check,
    not_evaluated_check,
    spacing_limit_check,
)


def check_closed_stirrup_for_torsion(
    *,
    torsion_states: tuple[str, ...],
    minimum_branches: int | None,
    provided_branches: int,
    station: float | None = None,
) -> RuleCheck:
    applicability = torsion_rule_applicability(torsion_states)
    if applicability.status == ApplicabilityStatus.NOT_APPLICABLE:
        return not_applicable_check(
            rule_id="ACI318_25_9_7_6_3_1_CLOSED_STIRRUP",
            section="9.7.6.3.1",
            reason=applicability.reason,
            station=station,
        )
    if applicability.status == ApplicabilityStatus.MISSING_DATA:
        return not_evaluated_check(
            rule_id="ACI318_25_9_7_6_3_1_CLOSED_STIRRUP",
            section="9.7.6.3.1",
            reason=applicability.reason,
            station=station,
        )
    required_branches = max(2, minimum_branches or 2)
    return boolean_check(
        rule_id="ACI318_25_9_7_6_3_1_CLOSED_STIRRUP",
        section="9.7.6.3.1",
        reason="Active torsion requires closed stirrups or hoops; the current scheme represents a closed stirrup with at least two legs",
        satisfied=(minimum_branches is None or minimum_branches >= 2)
        and provided_branches >= required_branches,
        required_value=required_branches,
        provided_value=provided_branches,
        unit="branches",
        station=station,
    )


def torsion_spacing_limits(
    *,
    torsion_states: tuple[str, ...],
    spacing_mm: float,
    width_mm: float | None,
    height_mm: float | None,
    cover_side_mm: float | None,
    cover_top_mm: float | None,
    cover_bottom_mm: float | None,
    station: float | None = None,
) -> tuple[tuple[SpacingLimit, ...], tuple[RuleCheck, ...]]:
    applicability = torsion_rule_applicability(torsion_states)
    rule_id = "ACI318_25_9_7_6_3_3_TORSION_SPACING"
    if applicability.status == ApplicabilityStatus.NOT_APPLICABLE:
        return (), (
            not_applicable_check(
                rule_id=rule_id,
                section="9.7.6.3.3",
                reason=applicability.reason,
                station=station,
            ),
        )
    if applicability.status == ApplicabilityStatus.MISSING_DATA:
        return (), (
            not_evaluated_check(
                rule_id=rule_id,
                section="9.7.6.3.3",
                reason=applicability.reason,
                provided_value=spacing_mm,
                unit="mm",
                station=station,
            ),
        )

    decision = required_fields(
        width_mm=width_mm,
        height_mm=height_mm,
        cover_side_mm=cover_side_mm,
        cover_top_mm=cover_top_mm,
        cover_bottom_mm=cover_bottom_mm,
    )
    if decision.status == ApplicabilityStatus.MISSING_DATA:
        return (), (
            not_evaluated_check(
                rule_id=rule_id,
                section="9.7.6.3.3",
                reason=f"Active torsion: {decision.reason}",
                provided_value=spacing_mm,
                unit="mm",
                station=station,
            ),
        )

    assert width_mm is not None
    assert height_mm is not None
    assert cover_side_mm is not None
    assert cover_top_mm is not None
    assert cover_bottom_mm is not None
    stirrup_width_mm = width_mm - 2.0 * cover_side_mm
    stirrup_height_mm = height_mm - cover_top_mm - cover_bottom_mm
    if stirrup_width_mm <= 0.0 or stirrup_height_mm <= 0.0:
        return (), (
            not_evaluated_check(
                rule_id=rule_id,
                section="9.7.6.3.3",
                reason="Active torsion but the closed-stirrup dimensions are non-positive",
                provided_value=spacing_mm,
                unit="mm",
                station=station,
            ),
        )

    ph_mm = 2.0 * (stirrup_width_mm + stirrup_height_mm)
    reason = "Transverse torsional reinforcement is required because at least one demand scenario has active torsion"
    limits = (
        spacing_limit_check(
            rule_id="ACI318_25_9_7_6_3_3_PH_OVER_8",
            section="9.7.6.3.3",
            reason=reason,
            maximum_mm=ph_mm / 8.0,
            provided_mm=spacing_mm,
            label="Ph/8",
            station=station,
        ),
        spacing_limit_check(
            rule_id="ACI318_25_9_7_6_3_3_300_MM",
            section="9.7.6.3.3",
            reason=reason,
            maximum_mm=300.0,
            provided_mm=spacing_mm,
            label="300",
            station=station,
        ),
    )
    return limits, tuple(limit.check for limit in limits)
