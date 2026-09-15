from __future__ import annotations

import math
from enum import Enum

from ...tolerances import reinforcement_grade_tolerance_mpa
from .applicability import ApplicabilityStatus, required_fields
from .common import (
    RuleCheck,
    SpacingLimit,
    maximum_length_check,
    minimum_length_check,
    not_applicable_check,
    not_evaluated_check,
    spacing_limit_check,
)


class SeismicTransverseRegionKind(str, Enum):
    BEAM_END = "BEAM_END"
    POTENTIAL_FLEXURAL_YIELDING = "POTENTIAL_FLEXURAL_YIELDING"
    OTHER = "OTHER"


_VALID_SEISMIC_REGION_KINDS = frozenset(
    item.value for item in SeismicTransverseRegionKind
)


def _region_kind_value(
    region_kind: SeismicTransverseRegionKind | str | None,
) -> str | None:
    if isinstance(region_kind, SeismicTransverseRegionKind):
        return region_kind.value
    return region_kind


def check_seismic_transverse_zone_extent(
    *,
    system: str,
    zone: str,
    h_mm: float | None,
    provided_zone_length_mm: float | None,
    region_kind: SeismicTransverseRegionKind | str | None = None,
    yielding_extension_before_mm: float | None = None,
    yielding_extension_after_mm: float | None = None,
) -> RuleCheck:
    """Check hoop/closed-stirrup region extent independently of spacing."""
    if system == "DMI":
        return not_applicable_check(
            rule_id="ACI318_25_18_3_SEISMIC_TRANSVERSE_ZONE",
            section="18.3",
            reason="ACI 318-25 Section 18.3 does not define the DMO or DES transverse-reinforcement regions",
            candidate_dependent=False,
        )
    if zone not in {"C", "NC"}:
        return not_evaluated_check(
            rule_id="ACI318_25_SEISMIC_TRANSVERSE_ZONE",
            section="18.4.2.4 or 18.6.4.1",
            reason=f"Unsupported seismic zone: {zone}",
            provided_value=provided_zone_length_mm,
            unit="mm",
            candidate_dependent=False,
        )

    if system == "DMO":
        rule_id = "ACI318_25_18_4_2_4_END_ZONE_LENGTH"
        if zone == "NC":
            return not_applicable_check(
                rule_id=rule_id,
                section="18.4.2.4",
                reason="The DMO region is outside the confined end-region overlay",
                candidate_dependent=False,
            )
        required_mm = 2.0 * h_mm if h_mm is not None and h_mm > 0.0 else None
        if required_mm is None or provided_zone_length_mm is None or provided_zone_length_mm <= 0.0:
            return not_evaluated_check(
                rule_id=rule_id,
                section="18.4.2.4",
                reason="DMO end-zone extent requires positive total beam height h_mm and the actual zone length measured from the support face toward midspan",
                required_value=required_mm if required_mm is not None else "2h",
                provided_value=provided_zone_length_mm,
                unit="mm",
                candidate_dependent=False,
            )
        return minimum_length_check(
            rule_id=rule_id,
            section="18.4.2.4",
            reason="DMO confined end region measured from the face of the supporting member toward midspan",
            minimum_mm=required_mm,
            provided_mm=provided_zone_length_mm,
            candidate_dependent=False,
        )

    if system != "DES":
        return not_evaluated_check(
            rule_id="ACI318_25_SEISMIC_TRANSVERSE_ZONE",
            section="18.4.2.4 or 18.6.4.1",
            reason=f"Unsupported seismic detailing system: {system}",
            provided_value=provided_zone_length_mm,
            unit="mm",
            candidate_dependent=False,
        )

    kind = _region_kind_value(region_kind)
    if kind is None:
        return not_evaluated_check(
            rule_id="ACI318_25_18_6_4_1_REGION_DEFINITION",
            section="18.6.4.1(a)-(b)",
            reason="DES requires the region basis (beam end or probable inelastic flexural-yielding section); that information is not available",
            required_value="BEAM_END or POTENTIAL_FLEXURAL_YIELDING",
            provided_value=None,
            candidate_dependent=False,
        )
    if kind not in _VALID_SEISMIC_REGION_KINDS:
        return not_evaluated_check(
            rule_id="ACI318_25_18_6_4_1_REGION_DEFINITION",
            section="18.6.4.1(a)-(b)",
            reason=f"Unsupported DES transverse-region kind: {kind}",
            provided_value=kind,
            candidate_dependent=False,
        )
    if kind == SeismicTransverseRegionKind.OTHER.value:
        if zone == "C":
            return not_evaluated_check(
                rule_id="ACI318_25_18_6_4_1_REGION_DEFINITION",
                section="18.6.4.1(a)-(b)",
                reason="A DES confined region was supplied without a beam-end or probable-yielding basis",
                provided_value=kind,
                candidate_dependent=False,
            )
        return not_applicable_check(
            rule_id="ACI318_25_18_6_4_1_REGION_DEFINITION",
            section="18.6.4.1(a)-(b)",
            reason="The identified DES region is neither a beam end nor a probable inelastic flexural-yielding region",
            candidate_dependent=False,
        )
    if zone != "C":
        return not_evaluated_check(
            rule_id="ACI318_25_18_6_4_1_REGION_DEFINITION",
            section="18.6.4.1(a)-(b)",
            reason=f"DES region kind {kind} requires hoops or closed stirrups, but the region is classified as {zone}",
            provided_value=zone,
            candidate_dependent=False,
        )

    required_mm = 2.0 * h_mm if h_mm is not None and h_mm > 0.0 else None
    if kind == SeismicTransverseRegionKind.BEAM_END.value:
        rule_id = "ACI318_25_18_6_4_1_A_END_ZONE_LENGTH"
        if required_mm is None or provided_zone_length_mm is None or provided_zone_length_mm <= 0.0:
            return not_evaluated_check(
                rule_id=rule_id,
                section="18.6.4.1(a)",
                reason="DES beam-end extent requires positive total beam height h_mm and the actual zone length measured from the column face toward midspan",
                required_value=required_mm if required_mm is not None else "2h",
                provided_value=provided_zone_length_mm,
                unit="mm",
                candidate_dependent=False,
            )
        return minimum_length_check(
            rule_id=rule_id,
            section="18.6.4.1(a)",
            reason="DES beam-end region measured from the face of the supporting column toward midspan",
            minimum_mm=required_mm,
            provided_mm=provided_zone_length_mm,
            candidate_dependent=False,
        )

    rule_id = "ACI318_25_18_6_4_1_B_YIELD_ZONE_EXTENSION"
    if (
        required_mm is None
        or yielding_extension_before_mm is None
        or yielding_extension_after_mm is None
        or yielding_extension_before_mm <= 0.0
        or yielding_extension_after_mm <= 0.0
    ):
        provided = (
            f"before={yielding_extension_before_mm}, after={yielding_extension_after_mm}"
            if yielding_extension_before_mm is not None or yielding_extension_after_mm is not None
            else None
        )
        return not_evaluated_check(
            rule_id=rule_id,
            section="18.6.4.1(b)",
            reason="DES probable-yielding region requires positive total beam height h_mm and actual hoop extensions on both sides of the section",
            required_value=required_mm if required_mm is not None else "2h on each side",
            provided_value=provided,
            unit="mm",
            candidate_dependent=False,
        )
    governing_extension_mm = min(
        yielding_extension_before_mm,
        yielding_extension_after_mm,
    )
    return minimum_length_check(
        rule_id=rule_id,
        section="18.6.4.1(b)",
        reason=(
            "DES probable inelastic flexural-yielding region; provided value is the "
            "shorter of the two extensions from the section"
        ),
        minimum_mm=required_mm,
        provided_mm=governing_extension_mm,
        candidate_dependent=False,
    )


def check_first_seismic_transverse_reinforcement_location(
    *,
    system: str,
    zone: str,
    first_distance_mm: float | None,
    region_kind: SeismicTransverseRegionKind | str | None = None,
) -> RuleCheck:
    """Check first hoop/closed-stirrup location independently of spacing."""
    if system == "DMI":
        return not_applicable_check(
            rule_id="ACI318_25_18_3_FIRST_SEISMIC_TRANSVERSE_LOCATION",
            section="18.3",
            reason="ACI 318-25 Section 18.3 does not define the DMO or DES first-hoop location",
            candidate_dependent=False,
        )
    if zone not in {"C", "NC"}:
        return not_evaluated_check(
            rule_id="ACI318_25_FIRST_SEISMIC_TRANSVERSE_LOCATION",
            section="18.4.2.4 or 18.6.4.4",
            reason=f"Unsupported seismic zone: {zone}",
            provided_value=first_distance_mm,
            unit="mm",
            candidate_dependent=False,
        )

    if system == "DMO":
        rule_id = "ACI318_25_18_4_2_4_FIRST_TRANSVERSE_LOCATION"
        section = "18.4.2.4"
        reason = "DMO first hoop or closed stirrup measured from the face of the supporting member"
        applicable = zone == "C"
    elif system == "DES":
        rule_id = "ACI318_25_18_6_4_4_FIRST_TRANSVERSE_LOCATION"
        section = "18.6.4.4"
        kind = _region_kind_value(region_kind)
        if zone == "C" and kind is None:
            return not_evaluated_check(
                rule_id=rule_id,
                section=section,
                reason="DES first-hoop applicability requires identification of a beam-end region at a supporting column",
                required_value=50.0,
                provided_value=first_distance_mm,
                unit="mm",
                candidate_dependent=False,
            )
        if kind is not None and kind not in _VALID_SEISMIC_REGION_KINDS:
            return not_evaluated_check(
                rule_id=rule_id,
                section=section,
                reason=f"Unsupported DES transverse-region kind: {kind}",
                required_value=50.0,
                provided_value=first_distance_mm,
                unit="mm",
                candidate_dependent=False,
            )
        applicable = zone == "C" and kind == SeismicTransverseRegionKind.BEAM_END.value
        reason = "DES first hoop or closed stirrup measured from the face of the supporting column"
    else:
        return not_evaluated_check(
            rule_id="ACI318_25_FIRST_SEISMIC_TRANSVERSE_LOCATION",
            section="18.4.2.4 or 18.6.4.4",
            reason=f"Unsupported seismic detailing system: {system}",
            provided_value=first_distance_mm,
            unit="mm",
            candidate_dependent=False,
        )

    if not applicable:
        return not_applicable_check(
            rule_id=rule_id,
            section=section,
            reason="The region is not a confined beam end at the face of a supporting member",
            candidate_dependent=False,
        )
    if first_distance_mm is None or first_distance_mm < 0.0:
        return not_evaluated_check(
            rule_id=rule_id,
            section=section,
            reason="The actual distance from the support face to the first hoop or closed stirrup is not available",
            required_value=50.0,
            provided_value=first_distance_mm,
            unit="mm",
            candidate_dependent=False,
        )
    return maximum_length_check(
        rule_id=rule_id,
        section=section,
        reason=reason,
        maximum_mm=50.0,
        provided_mm=first_distance_mm,
        candidate_dependent=False,
    )


def seismic_transverse_region_checks(
    *,
    system: str,
    zone: str,
    h_mm: float | None,
    provided_zone_length_mm: float | None,
    first_distance_mm: float | None,
    region_kind: SeismicTransverseRegionKind | str | None = None,
    yielding_extension_before_mm: float | None = None,
    yielding_extension_after_mm: float | None = None,
) -> tuple[RuleCheck, RuleCheck]:
    return (
        check_seismic_transverse_zone_extent(
            system=system,
            zone=zone,
            h_mm=h_mm,
            provided_zone_length_mm=provided_zone_length_mm,
            region_kind=region_kind,
            yielding_extension_before_mm=yielding_extension_before_mm,
            yielding_extension_after_mm=yielding_extension_after_mm,
        ),
        check_first_seismic_transverse_reinforcement_location(
            system=system,
            zone=zone,
            first_distance_mm=first_distance_mm,
            region_kind=region_kind,
        ),
    )


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
