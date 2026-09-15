from __future__ import annotations

from enum import Enum

from .common import (
    RuleCheck,
    SpacingLimit,
    boolean_check,
    not_applicable_check,
    not_evaluated_check,
    spacing_limit_check,
)


class TieRuleScope(str, Enum):
    NONE = "NONE"
    LATERAL_SUPPORT_ONLY = "LATERAL_SUPPORT_ONLY"
    FULL = "FULL"


# ACI 318M-25 uses No. 10/13 transverse bars and No. 32/36
# longitudinal bars. These are the project catalog diameters for those sizes.
NO_10_DIAMETER_MM = 9.5
NO_13_DIAMETER_MM = 12.7
NO_32_DIAMETER_MM = 32.3
NO_36_DIAMETER_MM = 35.8


def select_tie_rule_scope(*, compression_rebar_required: bool, system: str, zone: str) -> TieRuleScope:
    if compression_rebar_required:
        return TieRuleScope.FULL
    if system == "DES" and zone == "C":
        return TieRuleScope.LATERAL_SUPPORT_ONLY
    return TieRuleScope.NONE


def check_transverse_reinforcement_size(
    *,
    scope: TieRuleScope,
    longitudinal_bar_diameter_mm: float | None,
    transverse_bar_diameter_mm: float | None,
) -> RuleCheck:
    """Evaluate ACI 318M-25 9.7.6.4.2 for individual bars only."""
    rule_id = "ACI318_25_9_7_6_4_2_TRANSVERSE_SIZE"
    if scope != TieRuleScope.FULL:
        return not_applicable_check(
            rule_id=rule_id,
            section="9.7.6.4.2",
            reason="Longitudinal compression reinforcement is not required by design",
        )
    if longitudinal_bar_diameter_mm is None:
        return not_evaluated_check(
            rule_id=rule_id,
            section="9.7.6.4.2",
            reason="The individual longitudinal bar diameter is unavailable",
            provided_value=transverse_bar_diameter_mm,
            unit="mm",
        )

    if longitudinal_bar_diameter_mm <= NO_32_DIAMETER_MM:
        required_mm = NO_10_DIAMETER_MM
        requirement = "No. 10 transverse bar for No. 32 or smaller longitudinal bars"
    elif longitudinal_bar_diameter_mm >= NO_36_DIAMETER_MM:
        required_mm = NO_13_DIAMETER_MM
        requirement = "No. 13 transverse bar for No. 36 or larger longitudinal bars"
    else:
        return not_evaluated_check(
            rule_id=rule_id,
            section="9.7.6.4.2",
            reason=(
                "The supplied diameter does not identify a supported ACI No. 32-or-smaller "
                "or No. 36-or-larger bar designation"
            ),
            provided_value=transverse_bar_diameter_mm,
            unit="mm",
        )

    if transverse_bar_diameter_mm is None:
        return not_evaluated_check(
            rule_id=rule_id,
            section="9.7.6.4.2",
            reason=f"{requirement}; transverse bar diameter is unavailable",
            required_value=required_mm,
            unit="mm",
        )
    return boolean_check(
        rule_id=rule_id,
        section="9.7.6.4.2",
        reason=f"{requirement}; bundled longitudinal bars are outside module scope",
        satisfied=transverse_bar_diameter_mm >= required_mm,
        required_value=required_mm,
        provided_value=transverse_bar_diameter_mm,
        unit="mm",
    )


def _spacing_component(
    *,
    scope: TieRuleScope,
    rule_id: str,
    section: str,
    label: str,
    reason: str,
    maximum_mm: float | None,
    spacing_mm: float,
) -> tuple[SpacingLimit | None, RuleCheck]:
    if scope != TieRuleScope.FULL:
        check = not_applicable_check(
            rule_id=rule_id,
            section=section,
            reason="Longitudinal compression reinforcement is not required by design",
        )
        return None, check
    if maximum_mm is None:
        check = not_evaluated_check(
            rule_id=rule_id,
            section=section,
            reason=reason,
            provided_value=spacing_mm,
            unit="mm",
        )
        return None, check
    limit = spacing_limit_check(
        rule_id=rule_id,
        section=section,
        reason=reason,
        maximum_mm=maximum_mm,
        provided_mm=spacing_mm,
        label=label,
    )
    return limit, limit.check


def tie_rule_checks(
    *,
    scope: TieRuleScope,
    system: str,
    zone: str,
    spacing_mm: float,
    longitudinal_bar_diameter_mm: float | None,
    tie_bar_diameter_mm: float | None,
    width_mm: float | None,
    height_mm: float | None,
) -> tuple[tuple[SpacingLimit, ...], tuple[RuleCheck, ...]]:
    """Evaluate the in-scope tie rules without inferring bar layout."""
    checks: list[RuleCheck] = [
        check_transverse_reinforcement_size(
            scope=scope,
            longitudinal_bar_diameter_mm=longitudinal_bar_diameter_mm,
            transverse_bar_diameter_mm=tie_bar_diameter_mm,
        )
    ]
    limits: list[SpacingLimit] = []

    components = (
        (
            "ACI318_25_9_7_6_4_3_SIXTEEN_DB_LONGITUDINAL",
            "9.7.6.4.3(a)",
            "16db_longitudinal",
            "Maximum spacing is 16db of the individual longitudinal reinforcement",
            16.0 * longitudinal_bar_diameter_mm if longitudinal_bar_diameter_mm is not None else None,
        ),
        (
            "ACI318_25_9_7_6_4_3_FORTY_EIGHT_DB_TRANSVERSE",
            "9.7.6.4.3(b)",
            "48db_transverse",
            "Maximum spacing is 48db of the transverse reinforcement",
            48.0 * tie_bar_diameter_mm if tie_bar_diameter_mm is not None else None,
        ),
        (
            "ACI318_25_9_7_6_4_3_LEAST_BEAM_DIMENSION",
            "9.7.6.4.3(c)",
            "least_beam_dimension",
            "Maximum spacing is the least beam dimension",
            min(width_mm, height_mm) if width_mm is not None and height_mm is not None else None,
        ),
    )
    for rule_id, section, label, reason, maximum_mm in components:
        limit, check = _spacing_component(
            scope=scope,
            rule_id=rule_id,
            section=section,
            label=label,
            reason=reason,
            maximum_mm=maximum_mm,
            spacing_mm=spacing_mm,
        )
        if limit is not None:
            limits.append(limit)
        checks.append(check)

    if scope == TieRuleScope.FULL:
        checks.append(
            not_evaluated_check(
                rule_id="ACI318_25_9_7_6_4_4_LONGITUDINAL_BAR_ARRANGEMENT",
                section="9.7.6.4.4",
                reason=(
                    "Longitudinal bar count, transverse positions, corner bars, alternate bars, "
                    "and clear support distances are outside the current module scope"
                ),
                candidate_dependent=False,
            )
        )
    else:
        checks.append(
            not_applicable_check(
                rule_id="ACI318_25_9_7_6_4_4_LONGITUDINAL_BAR_ARRANGEMENT",
                section="9.7.6.4.4",
                reason="Longitudinal compression reinforcement is not required by design",
                candidate_dependent=False,
            )
        )

    if system == "DES" and zone == "C":
        checks.append(
            not_evaluated_check(
                rule_id="ACI318_25_18_6_4_2_LATERAL_SUPPORT",
                section="18.6.4.2 and 25.7.2.3",
                reason=(
                    "DES confined lateral support applies, but longitudinal bar count, positions, "
                    "supported bars, crossties, and clear distances are outside the current scope"
                ),
                candidate_dependent=False,
            )
        )

    return tuple(limits), tuple(checks)
