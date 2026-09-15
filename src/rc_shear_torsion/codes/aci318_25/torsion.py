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


def check_minimum_transverse_reinforcement_for_torsion(
    *,
    torsion_states: tuple[str, ...],
    fc_mpa: float | None,
    bw_mm: float | None,
    fyt_mpa: float | None,
    provided_combined_mm2_per_m: float | None,
    station: float | None = None,
) -> RuleCheck:
    """Check ACI 318-25 9.6.4.2 in consistent SI units."""
    applicability = torsion_rule_applicability(torsion_states)
    rule_id = "ACI318_25_9_6_4_2_COMBINED_TRANSVERSE_MINIMUM"
    if applicability.status == ApplicabilityStatus.NOT_APPLICABLE:
        return not_applicable_check(
            rule_id=rule_id,
            section="9.6.4.2",
            reason=applicability.reason,
            station=station,
        )
    if applicability.status == ApplicabilityStatus.MISSING_DATA:
        return not_evaluated_check(
            rule_id=rule_id,
            section="9.6.4.2",
            reason=applicability.reason,
            provided_value=provided_combined_mm2_per_m,
            unit="mm2/m",
            station=station,
        )

    decision = required_fields(
        fc_mpa=fc_mpa,
        bw_mm=bw_mm,
        fyt_mpa=fyt_mpa,
        provided_combined_mm2_per_m=provided_combined_mm2_per_m,
    )
    if decision.status == ApplicabilityStatus.MISSING_DATA:
        return not_evaluated_check(
            rule_id=rule_id,
            section="9.6.4.2",
            reason=f"Torsional reinforcement is required: {decision.reason}",
            provided_value=provided_combined_mm2_per_m,
            unit="mm2/m",
            station=station,
        )

    assert fc_mpa is not None
    assert bw_mm is not None
    assert fyt_mpa is not None
    assert provided_combined_mm2_per_m is not None
    if fc_mpa <= 0.0 or bw_mm <= 0.0 or fyt_mpa <= 0.0:
        return not_evaluated_check(
            rule_id=rule_id,
            section="9.6.4.2",
            reason=(
                "Torsional reinforcement is required, but fc_mpa, bw_mm, and "
                "fyt_mpa must be positive"
            ),
            provided_value=provided_combined_mm2_per_m,
            unit="mm2/m",
            station=station,
        )

    minimum_mm2_per_mm = max(
        0.062 * (fc_mpa ** 0.5) * bw_mm / fyt_mpa,
        0.35 * bw_mm / fyt_mpa,
    )
    minimum_mm2_per_m = minimum_mm2_per_mm * 1000.0
    return boolean_check(
        rule_id=rule_id,
        section="9.6.4.2",
        reason=(
            "At least one physical demand scenario requires torsional reinforcement; "
            "the greater SI expression in ACI 318-25 9.6.4.2 controls"
        ),
        satisfied=provided_combined_mm2_per_m >= minimum_mm2_per_m,
        required_value=minimum_mm2_per_m,
        provided_value=provided_combined_mm2_per_m,
        unit="mm2/m",
        station=station,
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
        satisfied=provided_branches >= required_branches,
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
    closed_stirrup_bar_diameter_mm: float | None = None,
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
        closed_stirrup_bar_diameter_mm=closed_stirrup_bar_diameter_mm,
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
    assert closed_stirrup_bar_diameter_mm is not None
    stirrup_width_mm = (
        width_mm - 2.0 * cover_side_mm - closed_stirrup_bar_diameter_mm
    )
    stirrup_height_mm = (
        height_mm
        - cover_top_mm
        - cover_bottom_mm
        - closed_stirrup_bar_diameter_mm
    )
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
    reason = (
        "Transverse torsional reinforcement is required because at least one demand "
        "scenario has active torsion; ph is the centerline perimeter of the exterior "
        "closed stirrup"
    )
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
