from __future__ import annotations

from .common import AciRuleEvaluation, RuleCheck, RuleStatus, SpacingLimit, select_controlling_spacing_limit
from .seismic import (
    SeismicTransverseRegionKind,
    seismic_spacing_limits,
    seismic_transverse_region_checks,
)
from .shear import check_minimum_shear_reinforcement, maximum_shear_spacing_limits
from .ties import TieRuleScope, select_tie_rule_scope, tie_rule_checks
from .torsion import (
    check_closed_stirrup_for_torsion,
    check_minimum_transverse_reinforcement_for_torsion,
    torsion_spacing_limits,
)


def evaluate_region_rules(
    *,
    system: str,
    zone: str,
    spacing_mm: float,
    d_mm: float | None,
    longitudinal_bar_diameter_mm: float | None,
    transverse_bar_diameter_mm: float | None,
    minimum_branches: int | None,
    provided_branches: int,
    compression_rebar_required: bool,
    torsion_states: tuple[str, ...],
    torsion_station: float | None,
    width_mm: float | None,
    height_mm: float | None,
    cover_side_mm: float | None,
    cover_top_mm: float | None,
    cover_bottom_mm: float | None,
    fc_mpa: float | None,
    fy_mpa: float | None,
    required_av_per_s_mm2_per_m: float | None,
    shear_station: float | None,
    provided_combined_transverse_mm2_per_m: float | None = None,
    closed_stirrup_bar_diameter_mm: float | None = None,
    seismic_zone_length_mm: float | None = None,
    first_seismic_transverse_distance_mm: float | None = None,
    seismic_region_kind: SeismicTransverseRegionKind | str | None = None,
    des_yielding_extension_before_mm: float | None = None,
    des_yielding_extension_after_mm: float | None = None,
) -> AciRuleEvaluation:
    checks: list[RuleCheck] = []
    spacing_limits: list[SpacingLimit] = []

    minimum_shear = check_minimum_shear_reinforcement(vu_n=None, station=shear_station)
    checks.append(minimum_shear)

    shear_limits, shear_checks = maximum_shear_spacing_limits(
        spacing_mm=spacing_mm,
        d_mm=d_mm,
        fc_mpa=fc_mpa,
        bw_mm=width_mm,
        fy_mpa=fy_mpa,
        required_av_per_s_mm2_per_m=required_av_per_s_mm2_per_m,
        station=shear_station,
    )
    spacing_limits.extend(shear_limits)
    checks.extend(shear_checks)

    checks.append(
        check_minimum_transverse_reinforcement_for_torsion(
            torsion_states=torsion_states,
            fc_mpa=fc_mpa,
            bw_mm=width_mm,
            fyt_mpa=fy_mpa,
            provided_combined_mm2_per_m=provided_combined_transverse_mm2_per_m,
            station=torsion_station,
        )
    )
    checks.append(
        check_closed_stirrup_for_torsion(
            torsion_states=torsion_states,
            minimum_branches=minimum_branches,
            provided_branches=provided_branches,
            station=torsion_station,
        )
    )
    torsion_limits, torsion_checks = torsion_spacing_limits(
        torsion_states=torsion_states,
        spacing_mm=spacing_mm,
        width_mm=width_mm,
        height_mm=height_mm,
        cover_side_mm=cover_side_mm,
        cover_top_mm=cover_top_mm,
        cover_bottom_mm=cover_bottom_mm,
        closed_stirrup_bar_diameter_mm=closed_stirrup_bar_diameter_mm,
        station=torsion_station,
    )
    spacing_limits.extend(torsion_limits)
    checks.extend(torsion_checks)

    seismic_limits, seismic_checks = seismic_spacing_limits(
        system=system,
        zone=zone,
        spacing_mm=spacing_mm,
        d_mm=d_mm,
        longitudinal_bar_diameter_mm=longitudinal_bar_diameter_mm,
        transverse_bar_diameter_mm=transverse_bar_diameter_mm,
        fy_mpa=fy_mpa,
    )
    spacing_limits.extend(seismic_limits)
    checks.extend(seismic_checks)
    checks.extend(
        seismic_transverse_region_checks(
            system=system,
            zone=zone,
            h_mm=height_mm,
            provided_zone_length_mm=seismic_zone_length_mm,
            first_distance_mm=first_seismic_transverse_distance_mm,
            region_kind=seismic_region_kind,
            yielding_extension_before_mm=des_yielding_extension_before_mm,
            yielding_extension_after_mm=des_yielding_extension_after_mm,
        )
    )

    tie_scope = select_tie_rule_scope(
        compression_rebar_required=compression_rebar_required,
        system=system,
        zone=zone,
    )
    tie_limits, tie_checks = tie_rule_checks(
        scope=tie_scope,
        system=system,
        zone=zone,
        spacing_mm=spacing_mm,
        longitudinal_bar_diameter_mm=longitudinal_bar_diameter_mm,
        tie_bar_diameter_mm=transverse_bar_diameter_mm,
        width_mm=width_mm,
        height_mm=height_mm,
    )
    spacing_limits.extend(tie_limits)
    checks.extend(tie_checks)

    limits_tuple = tuple(spacing_limits)
    return AciRuleEvaluation(
        checks=tuple(checks),
        spacing_limits=limits_tuple,
        controlling_limit=select_controlling_spacing_limit(limits_tuple),
    )


__all__ = [
    "AciRuleEvaluation",
    "RuleCheck",
    "RuleStatus",
    "SeismicTransverseRegionKind",
    "SpacingLimit",
    "TieRuleScope",
    "evaluate_region_rules",
    "select_tie_rule_scope",
]
