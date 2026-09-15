from __future__ import annotations

from enum import Enum

from .common import RuleCheck, SpacingLimit, not_applicable_check, not_evaluated_check, spacing_limit_check


class TieRuleScope(str, Enum):
    NONE = "NONE"
    LATERAL_SUPPORT_ONLY = "LATERAL_SUPPORT_ONLY"
    FULL = "FULL"


def select_tie_rule_scope(*, compression_rebar_required: bool, system: str, zone: str) -> TieRuleScope:
    if compression_rebar_required:
        return TieRuleScope.FULL
    if system == "DES" and zone == "C":
        return TieRuleScope.LATERAL_SUPPORT_ONLY
    return TieRuleScope.NONE


def tie_rule_checks(
    *,
    scope: TieRuleScope,
    spacing_mm: float,
    longitudinal_bar_diameter_mm: float | None,
    tie_bar_diameter_mm: float | None,
    width_mm: float | None,
    height_mm: float | None,
) -> tuple[tuple[SpacingLimit, ...], tuple[RuleCheck, ...]]:
    if scope == TieRuleScope.NONE:
        return (), (
            not_applicable_check(
                rule_id="ACI318_25_25_7_2_TIE_SCOPE",
                section="25.7.2",
                reason="Full ties are not activated because compression_rebar_required is false; DES confined lateral support is not applicable",
            ),
        )

    if scope == TieRuleScope.LATERAL_SUPPORT_ONLY:
        return (), (
            not_evaluated_check(
                rule_id="ACI318_25_18_6_4_2_LATERAL_SUPPORT",
                section="18.6.4.2 and 25.7.2.3-25.7.2.4",
                reason="DES confined lateral support applies, but the longitudinal-bar layout and support geometry are deferred to Phase 3",
            ),
        )

    _ = (
        longitudinal_bar_diameter_mm,
        tie_bar_diameter_mm,
        width_mm,
        height_mm,
    )
    return (), (
        not_evaluated_check(
            rule_id="ACI318_25_25_7_2_FULL_TIE_DETAILING",
            section="25.7.2.1-25.7.2.4",
            reason=(
                "FULL tie scope applies, but the Phase 2 contract does not distinguish the smallest and largest "
                "enclosed longitudinal bars, bundled bars, and every transverse component; numerical tie checks "
                "are deferred to Phase 3"
            ),
            provided_value=spacing_mm,
            unit="mm",
        ),
    )
