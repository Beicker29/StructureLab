from __future__ import annotations

import math

from ...tolerances import reinforcement_grade_tolerance_mpa
from .applicability import ApplicabilityStatus, required_fields
from .common import RuleCheck, SpacingLimit, not_applicable_check, not_evaluated_check, spacing_limit_check


def seismic_spacing_limits(
    *,
    system: str,
    zone: str,
    spacing_mm: float,
    d_mm: float | None,
    longitudinal_bar_diameter_mm: float | None,
    transverse_bar_diameter_mm: float | None,
    fy_mpa: float | None,
) -> tuple[tuple[SpacingLimit, ...], tuple[RuleCheck, ...]]:
    if system == "DMI":
        return (), (
            not_applicable_check(
                rule_id="ACI318_25_18_3_DMI_SEISMIC_SPACING",
                section="18.3",
                reason="ACI 318-25 §18.3 does not add a beam transverse-spacing limit for ordinary moment frames",
            ),
        )
    if zone not in {"C", "NC"}:
        return (), (
            not_evaluated_check(
                rule_id="ACI318_25_SEISMIC_SPACING_ZONE",
                section="18.4.2 or 18.6.4",
                reason=f"Unsupported seismic zone: {zone}",
                provided_value=spacing_mm,
                unit="mm",
            ),
        )

    if system == "DMO" and zone == "NC":
        if d_mm is None:
            return (), (
                not_evaluated_check(
                    rule_id="ACI318_25_18_4_2_5_D_OVER_2",
                    section="18.4.2.5",
                    reason="DMO non-confined region requires d_mm",
                    provided_value=spacing_mm,
                    unit="mm",
                ),
            )
        limit = spacing_limit_check(
            rule_id="ACI318_25_18_4_2_5_D_OVER_2",
            section="18.4.2.5",
            reason="DMO transverse reinforcement throughout the beam outside the end-region overlay",
            maximum_mm=d_mm / 2.0,
            provided_mm=spacing_mm,
            label="d/2",
        )
        return (limit,), (limit.check,)

    if system == "DES" and zone == "NC":
        if d_mm is None:
            return (), (
                not_evaluated_check(
                    rule_id="ACI318_25_18_6_4_5_D_OVER_2",
                    section="18.6.4.5",
                    reason="DES non-confined region requires d_mm",
                    provided_value=spacing_mm,
                    unit="mm",
                ),
            )
        limit = spacing_limit_check(
            rule_id="ACI318_25_18_6_4_5_D_OVER_2",
            section="18.6.4.5",
            reason="DES region where hoops are not required",
            maximum_mm=d_mm / 2.0,
            provided_mm=spacing_mm,
            label="d/2",
        )
        return (limit,), (limit.check,)

    if system == "DMO" and zone == "C":
        decision = required_fields(
            d_mm=d_mm,
            longitudinal_bar_diameter_mm=longitudinal_bar_diameter_mm,
            transverse_bar_diameter_mm=transverse_bar_diameter_mm,
        )
        if decision.status == ApplicabilityStatus.MISSING_DATA:
            return (), (
                not_evaluated_check(
                    rule_id="ACI318_25_18_4_2_4_DMO_CONFINED_SPACING",
                    section="18.4.2.4(a)-(d)",
                    reason=decision.reason,
                    provided_value=spacing_mm,
                    unit="mm",
                ),
            )
        assert d_mm is not None
        assert longitudinal_bar_diameter_mm is not None
        assert transverse_bar_diameter_mm is not None
        values = (
            ("D_OVER_4", "18.4.2.4(a)", "d/4", d_mm / 4.0),
            ("EIGHT_DB", "18.4.2.4(b)", "8db", 8.0 * longitudinal_bar_diameter_mm),
            ("TWENTY_FOUR_DBT", "18.4.2.4(c)", "24dest", 24.0 * transverse_bar_diameter_mm),
            ("ABSOLUTE_300", "18.4.2.4(d)", "300", 300.0),
        )
        limits = tuple(
            spacing_limit_check(
                rule_id=f"ACI318_25_18_4_2_4_{suffix}",
                section=section,
                reason="DMO confined end region defined by ACI 318-25 §18.4.2.4",
                maximum_mm=maximum,
                provided_mm=spacing_mm,
                label=label,
            )
            for suffix, section, label, maximum in values
        )
        return limits, tuple(limit.check for limit in limits)

    if system == "DES" and zone == "C":
        limits: list[SpacingLimit] = []
        checks: list[RuleCheck] = []
        if d_mm is None:
            checks.append(
                not_evaluated_check(
                    rule_id="ACI318_25_18_6_4_4_D_OVER_4",
                    section="18.6.4.4(a)",
                    reason="DES confined region requires d_mm",
                    provided_value=spacing_mm,
                    unit="mm",
                )
            )
        else:
            limits.append(
                spacing_limit_check(
                    rule_id="ACI318_25_18_6_4_4_D_OVER_4",
                    section="18.6.4.4(a)",
                    reason="DES confined region where hoops are required by §18.6.4.1",
                    maximum_mm=d_mm / 4.0,
                    provided_mm=spacing_mm,
                    label="d/4",
                )
            )

        if longitudinal_bar_diameter_mm is None or fy_mpa is None:
            checks.append(
                not_evaluated_check(
                    rule_id="ACI318_25_18_6_4_4_LONGITUDINAL_DB",
                    section="18.6.4.4(c) or (d)",
                    reason="DES confined region requires longitudinal bar diameter and reinforcement grade",
                    provided_value=spacing_mm,
                    unit="mm",
                )
            )
        elif math.isclose(
            fy_mpa,
            420.0,
            rel_tol=0.0,
            abs_tol=reinforcement_grade_tolerance_mpa,
        ):
            limits.append(
                spacing_limit_check(
                    rule_id="ACI318_25_18_6_4_4_SIX_DB_GRADE_420",
                    section="18.6.4.4(c)",
                    reason="DES confined region with Grade 420 primary flexural reinforcement",
                    maximum_mm=6.0 * longitudinal_bar_diameter_mm,
                    provided_mm=spacing_mm,
                    label="6db",
                )
            )
        elif math.isclose(
            fy_mpa,
            550.0,
            rel_tol=0.0,
            abs_tol=reinforcement_grade_tolerance_mpa,
        ):
            limits.append(
                spacing_limit_check(
                    rule_id="ACI318_25_18_6_4_4_FIVE_DB_GRADE_550",
                    section="18.6.4.4(d)",
                    reason="DES confined region with Grade 550 primary flexural reinforcement",
                    maximum_mm=5.0 * longitudinal_bar_diameter_mm,
                    provided_mm=spacing_mm,
                    label="5db",
                )
            )
        else:
            checks.append(
                not_evaluated_check(
                    rule_id="ACI318_25_18_6_4_4_LONGITUDINAL_DB",
                    section="18.6.4.4(c) or (d)",
                    reason=f"Reinforcement grade fy={fy_mpa} MPa is not identified as Grade 420 or Grade 550",
                    provided_value=spacing_mm,
                    unit="mm",
                )
            )

        limits.append(
            spacing_limit_check(
                rule_id="ACI318_25_18_6_4_4_ABSOLUTE_150",
                section="18.6.4.4(b)",
                reason="DES confined region where hoops are required by §18.6.4.1",
                maximum_mm=150.0,
                provided_mm=spacing_mm,
                label="150",
            )
        )
        checks.extend(limit.check for limit in limits)
        return tuple(limits), tuple(checks)

    return (), (
        not_evaluated_check(
            rule_id="ACI318_25_SEISMIC_SYSTEM",
            section="18.3, 18.4, or 18.6",
            reason=f"Unsupported seismic detailing system: {system}",
            provided_value=spacing_mm,
            unit="mm",
        ),
    )
