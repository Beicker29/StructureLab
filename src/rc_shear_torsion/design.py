from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Literal

from .codes.aci318_25 import AciRuleEvaluation, RuleCheck, RuleStatus, evaluate_region_rules
from .io import EtabsFrameData, EtabsStationRow
from .models import (
    BAR_DIAMETERS_MM,
    LEGACY_FIXED_STIRRUP_SPACING_MM,
    OptimizationConfig,
    RegionConfig,
    SpanConfig,
    VariablesConfig,
)
from .optimization import SearchHooks, run_exhaustive_search, run_genetic_search
from .ranking import transverse_alternative_rank_key
from .tolerances import dimensional_comparison_tolerance_mm, torsion_zero_tolerance

FailureMode = Literal[
    "torsion_fail",
    "shear_fail",
    "region_detail_fail",
    "longitudinal_fail",
    "input_fail",
    "ok",
]

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
DEAP_FITNESS_CLASS = "RCFitnessMin"
DEAP_INDIVIDUAL_CLASS = "RCIndividual"
STEEL_DENSITY_KG_PER_MM3 = 7.85e-6
HOOK_LENGTH_MM_BY_BAR: dict[str, float] = {
    "#3": 110.0,
    "#4": 120.0,
    "#5": 140.0,
}
HOOK_LENGTH_FACTOR_FALLBACK = 10.0


DemandSource = Literal["SEISMIC", "GRAVITY"]
TorsionState = Literal["ACTIVE", "INACTIVE", "INCONSISTENT"]


@dataclass(frozen=True)
class DemandScenario:
    source: DemandSource
    station_mm: float
    x_relative: float
    region_id: str
    v_rebar_mm2_per_m: float
    t_transverse_mm2_per_m: float
    t_longitudinal_mm2: float
    torsion_state: TorsionState
    source_row: int | None = None


@dataclass(frozen=True)
class RegionDemand:
    beam_id: str
    span_id: str
    region_id: str
    region_type: Literal["C", "NC"]
    beam_detailing: Literal["DES", "DMO", "DMI"]
    d_mm: float | None
    db_bar: str | None
    min_branches: int | None
    width_mm: float | None
    height_mm: float | None
    cover_side_mm: float | None
    cover_top_mm: float | None
    cover_bottom_mm: float | None
    scenarios: tuple[DemandScenario, ...]
    fc_mpa: float | None = None
    fy_mpa: float | None = None
    region_length_mm: float = 0.0
    compression_rebar_required: bool = False
    d_source: Literal["EXPLICIT", "DEFAULT_RATIO", "SPAN_RATIO"] | None = None
    d_ratio: float | None = None
    longitudinal_bar_diameter_mm: float | None = None
    longitudinal_bars_bundled: Literal[False] = False

    @property
    def governing_t_transverse_scenario(self) -> DemandScenario | None:
        return max(self.scenarios, key=lambda item: item.t_transverse_mm2_per_m, default=None)

    @property
    def governing_combined_scenario(self) -> DemandScenario | None:
        return max(
            self.scenarios,
            key=lambda item: item.v_rebar_mm2_per_m + 2.0 * item.t_transverse_mm2_per_m,
            default=None,
        )

    @property
    def governing_longitudinal_scenario(self) -> DemandScenario | None:
        return max(self.scenarios, key=lambda item: item.t_longitudinal_mm2, default=None)

    @property
    def v_req(self) -> float:
        return max((item.v_rebar_mm2_per_m for item in self.scenarios), default=0.0)

    @property
    def t_req(self) -> float:
        controller = self.governing_t_transverse_scenario
        return controller.t_transverse_mm2_per_m if controller is not None else 0.0

    @property
    def l_req(self) -> float:
        controller = self.governing_longitudinal_scenario
        return controller.t_longitudinal_mm2 if controller is not None else 0.0

    @property
    def station_count(self) -> int:
        return len(self.scenarios)

    @property
    def governing_station(self) -> float | None:
        controller = self.governing_combined_scenario
        return controller.station_mm if controller is not None else None

    @property
    def source_control(self) -> Literal["seismic", "gravity", "mixed"]:
        sources = {
            item.source
            for item in (
                self.governing_t_transverse_scenario,
                self.governing_combined_scenario,
                self.governing_longitudinal_scenario,
            )
            if item is not None
        }
        if sources == {"SEISMIC"}:
            return "seismic"
        if sources == {"GRAVITY"}:
            return "gravity"
        return "mixed"


@dataclass(frozen=True)
class DemandSpacingLimit:
    check_id: str
    maximum_mm: float
    source: DemandSource
    station_mm: float


@dataclass(frozen=True)
class Candidate:
    e_bar: str
    g_bar: str
    g_count: int
    spacing_mm: int
    long_bar: str | None
    long_count: int
    at: float
    at_over_s: float
    av1: float
    av2: float
    av_total: float
    av_over_s: float
    long_provided: float
    f_free: float
    failure_mode: FailureMode
    status: Literal["ok", "fail"]
    message: str
    objective: float
    score: float
    transverse_weight_kg_per_m: float = 0.0
    longitudinal_weight_kg_per_m: float = 0.0
    stirrup_unit_weight_kg: float = 0.0
    controlling_limit: str = ""
    demand_status: RuleStatus = RuleStatus.NOT_EVALUATED
    detailing_status: RuleStatus = RuleStatus.NOT_EVALUATED
    overall_status: RuleStatus = RuleStatus.NOT_EVALUATED
    rule_checks: tuple[RuleCheck, ...] = ()
    governing_code_rule: str | None = None
    governing_code_limit_mm: float | None = None
    governing_demand_check: str | None = None
    governing_demand_spacing_limit_mm: float | None = None
    governing_demand_source: DemandSource | None = None
    governing_demand_station_mm: float | None = None
    governing_project_spacing_limit_mm: float | None = None


@dataclass(frozen=True)
class RegionDesignResult:
    beam_id: str
    span_id: str
    region_id: str
    region_type: str
    source_control: str
    governing_station: float | None
    v_req: float
    t_req: float
    l_req: float
    e_bar: str
    g_bar: str
    g_count: int
    spacing_mm: int
    av1: float
    av2: float
    av_total: float
    at: float
    at_over_s: float
    av_over_s: float
    long_bar: str | None
    long_count: int
    controlling_limit: str
    failure_mode: FailureMode
    status: Literal["ok", "fail"]
    message: str
    objective: float
    method: str
    evaluated_candidates: int
    feasible_candidates: int
    transverse_weight_kg_per_m: float
    longitudinal_weight_kg_per_m: float
    stirrup_unit_weight_kg: float
    long_provided_mm2_override: float | None = None
    base_long_bar: str | None = None
    base_long_count: int | None = None
    extra_long_bar: str | None = None
    extra_long_count: int | None = None
    longitudinal_mode: str | None = None
    longitudinal_arrangement_label: str | None = None
    torsion_governing_source: str | None = None
    torsion_governing_station: float | None = None
    combined_governing_source: str | None = None
    combined_governing_station: float | None = None
    longitudinal_governing_source: str | None = None
    longitudinal_governing_station: float | None = None
    scenario_count: int = 0
    torsion_check_override: bool | None = None
    combined_check_override: bool | None = None
    longitudinal_check_override: bool | None = None
    demand_status: RuleStatus = RuleStatus.NOT_EVALUATED
    detailing_status: RuleStatus = RuleStatus.NOT_EVALUATED
    overall_status: RuleStatus = RuleStatus.NOT_EVALUATED
    rule_checks: tuple[RuleCheck, ...] = ()
    governing_code_rule: str | None = None
    governing_code_limit_mm: float | None = None
    governing_demand_check: str | None = None
    governing_demand_spacing_limit_mm: float | None = None
    governing_demand_source: DemandSource | None = None
    governing_demand_station_mm: float | None = None
    governing_project_spacing_limit_mm: float | None = None
    d_mm: float | None = None
    d_source: str | None = None
    d_ratio: float | None = None
    detailing_system: Literal["DMI", "DMO", "DES"] | None = None


@dataclass(frozen=True)
class SpanSummary:
    beam_id: str
    span_id: str
    total_regions: int
    ok_regions: int
    fail_regions: int
    status: Literal["ok", "fail"]
    message: str


@dataclass(frozen=True)
class BeamSummary:
    beam_id: str
    total_spans: int
    ok_spans: int
    fail_spans: int
    status: Literal["ok", "fail"]


@dataclass(frozen=True)
class OptimizationOutcome:
    selected: Candidate
    evaluated_candidates: int
    feasible_candidates: int
    method: str
    failure_counts: dict[str, int]


def build_region_demands(
    *,
    beam_id: str,
    beam_detailing: Literal["DES", "DMO", "DMI"],
    beam_cover_side_mm: float | None,
    beam_cover_top_mm: float | None,
    beam_cover_bottom_mm: float | None,
    beam_fc_mpa: float | None,
    beam_fy_mpa: float | None,
    span: SpanConfig,
    seismic_frame: EtabsFrameData,
    gravity_frame: EtabsFrameData,
    compression_rebar_required: bool = False,
    longitudinal_bar_diameter_mm: float | None = None,
    torsion_tolerance: float = torsion_zero_tolerance,
) -> tuple[list[RegionDemand], list[str]]:
    if torsion_tolerance < 0.0:
        return [], [f"Span {span.id}: torsion tolerance must be >= 0"]

    all_rows = tuple(seismic_frame.stations) + tuple(gravity_frame.stations)
    if not all_rows:
        return [], [f"Span {span.id}: no seismic or gravity stations were provided"]

    station_min = min(row.station for row in all_rows)
    station_max = max(row.station for row in all_rows)
    span_length_mm = station_max - station_min
    if span_length_mm <= 0.0:
        return [], [f"Span {span.id}: invalid station length={span_length_mm}; cannot compute relative position"]

    region_scenarios: dict[str, list[DemandScenario]] = {region.id: [] for region in span.regions}
    errors: list[str] = []

    for source, rows in (
        ("SEISMIC", seismic_frame.stations),
        ("GRAVITY", gravity_frame.stations),
    ):
        for ordinal, row in enumerate(rows, start=1):
            x_rel = (row.station - station_min) / span_length_mm
            region = locate_region(span.regions, x_rel)
            if region is None:
                errors.append(
                    f"Span {span.id}: {source} station {row.station} with "
                    f"x_rel={x_rel:.6f} is outside region map"
                )
                continue

            region_scenarios[region.id].append(
                DemandScenario(
                    source=source,
                    station_mm=row.station,
                    x_relative=x_rel,
                    region_id=region.id,
                    v_rebar_mm2_per_m=row.v_rebar_req,
                    t_transverse_mm2_per_m=row.t_trn_req,
                    t_longitudinal_mm2=row.t_lng_req,
                    torsion_state=classify_torsion_state(
                        row.t_trn_req,
                        row.t_lng_req,
                        tolerance=torsion_tolerance,
                    ),
                    source_row=row.source_row if row.source_row is not None else ordinal,
                )
            )

    if errors:
        return [], errors

    demands: list[RegionDemand] = []
    for region in span.regions:
        scenarios = region_scenarios.get(region.id, [])
        if not scenarios:
            errors.append(f"Span {span.id} region {region.id}: no stations were assigned")
            continue

        demands.append(
            RegionDemand(
                beam_id=beam_id,
                span_id=span.id,
                region_id=region.id,
                region_type=region.type,
                beam_detailing=beam_detailing,
                d_mm=region.d_mm,
                db_bar=region.db_bar,
                min_branches=region.min_branches,
                width_mm=region.width_mm,
                height_mm=region.height_mm,
                cover_side_mm=beam_cover_side_mm,
                cover_top_mm=beam_cover_top_mm,
                cover_bottom_mm=beam_cover_bottom_mm,
                scenarios=tuple(scenarios),
                fc_mpa=beam_fc_mpa,
                fy_mpa=beam_fy_mpa,
                region_length_mm=(region.to - region.from_) * span_length_mm,
                compression_rebar_required=compression_rebar_required,
                d_source=region.d_source,
                d_ratio=region.d_ratio,
                longitudinal_bar_diameter_mm=(
                    longitudinal_bar_diameter_mm
                    if longitudinal_bar_diameter_mm is not None
                    else BAR_DIAMETERS_MM.get(region.db_bar or "")
                ),
                longitudinal_bars_bundled=False,
            )
        )

    if errors:
        return [], errors
    return demands, []


def locate_region(regions: list[RegionConfig], x_rel: float) -> RegionConfig | None:
    for index, region in enumerate(regions):
        is_last = index == len(regions) - 1
        if (region.from_ <= x_rel < region.to) or (is_last and region.from_ <= x_rel <= region.to):
            return region
    return None


def classify_torsion_state(
    t_transverse_mm2_per_m: float,
    t_longitudinal_mm2: float,
    *,
    tolerance: float = torsion_zero_tolerance,
) -> TorsionState:
    if tolerance < 0.0:
        raise ValueError("torsion tolerance must be >= 0")
    transverse_active = t_transverse_mm2_per_m > tolerance
    longitudinal_active = t_longitudinal_mm2 > tolerance
    if transverse_active and longitudinal_active:
        return "ACTIVE"
    if not transverse_active and not longitudinal_active:
        return "INACTIVE"
    return "INCONSISTENT"


def scenario_reference(scenario: DemandScenario) -> str:
    row = f", source_row={scenario.source_row}" if scenario.source_row is not None else ""
    return f"source={scenario.source}, station_mm={scenario.station_mm}{row}"


def governing_demand_spacing_limit(
    region: RegionDemand,
    *,
    at_mm2: float,
    ag_mm2: float,
    g_count: int,
) -> DemandSpacingLimit | None:
    """Return the physical-demand upper bound on spacing for one bar scheme."""
    limits: list[DemandSpacingLimit] = []
    combined_area_mm2 = (2.0 * at_mm2) + (g_count * ag_mm2)

    for scenario in region.scenarios:
        if scenario.torsion_state == "INCONSISTENT":
            continue

        if scenario.t_transverse_mm2_per_m > torsion_zero_tolerance:
            limits.append(
                DemandSpacingLimit(
                    check_id="TORSION_TRANSVERSE_DEMAND",
                    maximum_mm=at_mm2 * 1000.0 / scenario.t_transverse_mm2_per_m,
                    source=scenario.source,
                    station_mm=scenario.station_mm,
                )
            )

        combined_demand = (
            scenario.v_rebar_mm2_per_m
            + 2.0 * scenario.t_transverse_mm2_per_m
        )
        if combined_demand <= torsion_zero_tolerance:
            continue
        if scenario.t_transverse_mm2_per_m <= torsion_zero_tolerance:
            check_id = "SHEAR_DEMAND"
        elif scenario.v_rebar_mm2_per_m <= torsion_zero_tolerance:
            check_id = "TORSION_TRANSVERSE_DEMAND"
        else:
            check_id = "SHEAR_TORSION_COMBINED_DEMAND"
        limits.append(
            DemandSpacingLimit(
                check_id=check_id,
                maximum_mm=combined_area_mm2 * 1000.0 / combined_demand,
                source=scenario.source,
                station_mm=scenario.station_mm,
            )
        )

    return min(limits, key=lambda item: item.maximum_mm) if limits else None


def _spacing_control_trace(
    *,
    rule_evaluation: AciRuleEvaluation,
    demand_limit: DemandSpacingLimit | None,
    project_limit_mm: float | None,
) -> str:
    code_limit = rule_evaluation.controlling_limit
    options: list[tuple[float, int, str]] = []
    if code_limit is not None:
        options.append((code_limit.maximum_mm, 0, code_limit.check.rule_id))
    if demand_limit is not None:
        options.append((demand_limit.maximum_mm, 1, demand_limit.check_id))
    if project_limit_mm is not None:
        options.append((project_limit_mm, 2, "PROJECT_SPACING_LIMIT"))
    if not options:
        return "N/A"

    _, _, controlling = min(options, key=lambda item: (item[0], item[1]))
    return controlling


def evaluate_candidate(
    region: RegionDemand,
    *,
    e_bar: str,
    g_bar: str,
    g_count: int,
    spacing_mm: int,
    long_bar: str | None,
    long_count: int,
    check_longitudinal: bool = False,
    project_spacing_limit_mm: float | None = None,
) -> Candidate:
    invalid_longitudinal = (
        long_count < 0
        or (long_count > 0 and long_bar not in BAR_AREAS_MM2)
        or (long_count == 0 and long_bar not in {None, "", *BAR_AREAS_MM2})
    )
    if e_bar not in BAR_AREAS_MM2 or g_bar not in BAR_AREAS_MM2 or invalid_longitudinal:
        return failed_candidate(
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing_mm,
            long_bar=long_bar,
            long_count=long_count,
            failure_mode="input_fail",
            message="Unsupported bar designation",
        )
    if spacing_mm <= 0:
        return failed_candidate(
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing_mm,
            long_bar=long_bar,
            long_count=long_count,
            failure_mode="input_fail",
            message="Spacing must be > 0",
        )
    if (
        project_spacing_limit_mm is not None
        and spacing_mm
        > project_spacing_limit_mm + dimensional_comparison_tolerance_mm
    ):
        return failed_candidate(
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing_mm,
            long_bar=long_bar,
            long_count=long_count,
            failure_mode="region_detail_fail",
            message=(
                f"Project spacing limit failed: s={spacing_mm} mm > "
                f"{project_spacing_limit_mm:.1f} mm"
            ),
            controlling_limit="PROJECT_SPACING_LIMIT",
            governing_project_spacing_limit_mm=project_spacing_limit_mm,
            detailing_status=RuleStatus.FAIL,
        )

    at = BAR_AREAS_MM2[e_bar]
    ag = BAR_AREAS_MM2[g_bar]
    along = BAR_AREAS_MM2.get(long_bar, 0.0) * long_count
    at_over_s = at * 1000.0 / spacing_mm
    f_free = 1.0 - (region.t_req / at_over_s if at_over_s > 0 else math.inf)
    av1 = max(0.0, f_free) * at * 2.0
    av2 = g_count * ag
    av_total = av1 + av2
    av_over_s = av_total * 1000.0 / spacing_mm
    combined_capacity = ((2.0 * at) + (g_count * ag)) * 1000.0 / spacing_mm

    stirrup_unit_weight_kg = stirrup_set_unit_weight_kg(
        region=region,
        e_bar=e_bar,
        g_bar=g_bar,
        g_count=g_count,
        at=at,
        ag=ag,
    )
    transverse_weight_kg_per_m = stirrup_unit_weight_kg * (1000.0 / spacing_mm)
    transverse_weight_region_kg = stirrup_unit_weight_kg * stirrup_count_in_region(region.region_length_mm, spacing_mm)
    # Objective of optimization: total transverse weight in the region (kg).
    objective = transverse_weight_region_kg

    if not region.scenarios:
        return failed_candidate(
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing_mm,
            long_bar=long_bar,
            long_count=long_count,
            failure_mode="input_fail",
            message="Region contains no physical demand scenarios",
            objective=objective,
            deficit=1.0,
        )

    inconsistent = next(
        (scenario for scenario in region.scenarios if scenario.torsion_state == "INCONSISTENT"),
        None,
    )
    if inconsistent is not None:
        return failed_candidate(
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing_mm,
            long_bar=long_bar,
            long_count=long_count,
            failure_mode="input_fail",
            message=(
                "Inconsistent torsion demand at "
                f"{scenario_reference(inconsistent)}: TTrn and TLng must both be active or inactive"
            ),
            at=at,
            at_over_s=at_over_s,
            av1=av1,
            av2=av2,
            av_total=av_total,
            av_over_s=av_over_s,
            long_provided=along,
            f_free=f_free,
            objective=objective,
            transverse_weight_kg_per_m=transverse_weight_kg_per_m,
            stirrup_unit_weight_kg=stirrup_unit_weight_kg,
            controlling_limit="N/A" if region.beam_detailing not in {"DMO", "DES"} else "",
            deficit=1.0,
        )

    torsion_failure = next(
        (
            scenario
            for scenario in region.scenarios
            if scenario.t_transverse_mm2_per_m > at_over_s
        ),
        None,
    )
    if torsion_failure is not None:
        return failed_candidate(
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing_mm,
            long_bar=long_bar,
            long_count=long_count,
            failure_mode="torsion_fail",
            message=f"C_T < TTrnRebar at {scenario_reference(torsion_failure)}",
            at=at,
            at_over_s=at_over_s,
            av1=av1,
            av2=av2,
            av_total=av_total,
            av_over_s=av_over_s,
            long_provided=along,
            f_free=f_free,
            objective=objective,
            transverse_weight_kg_per_m=transverse_weight_kg_per_m,
            stirrup_unit_weight_kg=stirrup_unit_weight_kg,
            controlling_limit="N/A" if region.beam_detailing not in {"DMO", "DES"} else "",
            deficit=deficit_ratio(torsion_failure.t_transverse_mm2_per_m, at_over_s),
        )

    combined_failure = next(
        (
            scenario
            for scenario in region.scenarios
            if scenario.v_rebar_mm2_per_m + 2.0 * scenario.t_transverse_mm2_per_m
            > combined_capacity
        ),
        None,
    )
    if combined_failure is not None:
        return failed_candidate(
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing_mm,
            long_bar=long_bar,
            long_count=long_count,
            failure_mode="shear_fail",
            message=f"C_VT < VRebar + 2*TTrnRebar at {scenario_reference(combined_failure)}",
            at=at,
            at_over_s=at_over_s,
            av1=av1,
            av2=av2,
            av_total=av_total,
            av_over_s=av_over_s,
            long_provided=along,
            f_free=f_free,
            objective=objective,
            transverse_weight_kg_per_m=transverse_weight_kg_per_m,
            stirrup_unit_weight_kg=stirrup_unit_weight_kg,
            controlling_limit="N/A" if region.beam_detailing not in {"DMO", "DES"} else "",
            deficit=deficit_ratio(
                combined_failure.v_rebar_mm2_per_m
                + 2.0 * combined_failure.t_transverse_mm2_per_m,
                combined_capacity,
            ),
        )

    if check_longitudinal:
        longitudinal_failure = next(
            (
                scenario
                for scenario in region.scenarios
                if scenario.t_longitudinal_mm2 > along
            ),
            None,
        )
        if longitudinal_failure is not None:
            return failed_candidate(
                e_bar=e_bar,
                g_bar=g_bar,
                g_count=g_count,
                spacing_mm=spacing_mm,
                long_bar=long_bar,
                long_count=long_count,
                failure_mode="longitudinal_fail",
                message=f"Along < TLngRebar at {scenario_reference(longitudinal_failure)}",
                at=at,
                at_over_s=at_over_s,
                av1=av1,
                av2=av2,
                av_total=av_total,
                av_over_s=av_over_s,
                long_provided=along,
                f_free=f_free,
                objective=objective,
                transverse_weight_kg_per_m=transverse_weight_kg_per_m,
                stirrup_unit_weight_kg=stirrup_unit_weight_kg,
                controlling_limit="N/A" if region.beam_detailing not in {"DMO", "DES"} else "",
                deficit=deficit_ratio(longitudinal_failure.t_longitudinal_mm2, along),
            )
    rule_evaluation = evaluate_region_rule_checks(
        region,
        spacing_mm=spacing_mm,
        g_count=g_count,
        e_bar=e_bar,
        g_bar=g_bar,
    )
    demand_spacing_limit = governing_demand_spacing_limit(
        region,
        at_mm2=at,
        ag_mm2=ag,
        g_count=g_count,
    )
    controlling_limit = _spacing_control_trace(
        rule_evaluation=rule_evaluation,
        demand_limit=demand_spacing_limit,
        project_limit_mm=project_spacing_limit_mm,
    )
    code_spacing_limit = rule_evaluation.controlling_limit
    if not rule_evaluation.passes_candidate_dependent_rules:
        return failed_candidate(
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing_mm,
            long_bar=long_bar,
            long_count=long_count,
            failure_mode="region_detail_fail",
            message=format_rule_evaluation_message(region, spacing_mm, rule_evaluation),
            at=at,
            at_over_s=at_over_s,
            av1=av1,
            av2=av2,
            av_total=av_total,
            av_over_s=av_over_s,
            long_provided=along,
            f_free=f_free,
            objective=objective,
            transverse_weight_kg_per_m=transverse_weight_kg_per_m,
            stirrup_unit_weight_kg=stirrup_unit_weight_kg,
            controlling_limit=controlling_limit,
            deficit=1.0,
            demand_status=RuleStatus.PASS,
            detailing_status=RuleStatus.FAIL,
            rule_checks=rule_evaluation.checks,
            governing_code_rule=(
                code_spacing_limit.check.rule_id if code_spacing_limit is not None else None
            ),
            governing_code_limit_mm=(
                code_spacing_limit.maximum_mm if code_spacing_limit is not None else None
            ),
            governing_demand_check=(
                demand_spacing_limit.check_id if demand_spacing_limit is not None else None
            ),
            governing_demand_spacing_limit_mm=(
                demand_spacing_limit.maximum_mm if demand_spacing_limit is not None else None
            ),
            governing_demand_source=(
                demand_spacing_limit.source if demand_spacing_limit is not None else None
            ),
            governing_demand_station_mm=(
                demand_spacing_limit.station_mm if demand_spacing_limit is not None else None
            ),
            governing_project_spacing_limit_mm=project_spacing_limit_mm,
        )

    if rule_evaluation.detailing_status == RuleStatus.FAIL:
        success_message = (
            "Candidate satisfies physical demands and candidate-dependent ACI detailing rules; "
            "one or more fixed regional detailing checks fail"
        )
    elif rule_evaluation.detailing_status == RuleStatus.NOT_EVALUATED:
        success_message = (
            "Candidate satisfies physical demands and evaluated ACI detailing rules; "
            "unresolved ACI rules remain NOT_EVALUATED"
        )
    elif rule_evaluation.detailing_status == RuleStatus.NOT_APPLICABLE:
        success_message = (
            "Candidate satisfies physical demands; ACI detailing rules are NOT_APPLICABLE"
        )
    else:
        success_message = "Candidate satisfies physical demands and ACI detailing rules"

    return Candidate(
        e_bar=e_bar,
        g_bar=g_bar,
        g_count=g_count,
        spacing_mm=spacing_mm,
        long_bar=long_bar,
        long_count=long_count,
        at=at,
        at_over_s=at_over_s,
        av1=av1,
        av2=av2,
        av_total=av_total,
        av_over_s=av_over_s,
        long_provided=along,
        f_free=f_free,
        failure_mode="ok",
        status="ok",
        message=success_message,
        objective=objective,
        score=objective,
        transverse_weight_kg_per_m=transverse_weight_kg_per_m,
        longitudinal_weight_kg_per_m=bar_mass_kg_per_m(long_bar, long_count),
        stirrup_unit_weight_kg=stirrup_unit_weight_kg,
        controlling_limit=controlling_limit,
        demand_status=RuleStatus.PASS,
        detailing_status=rule_evaluation.detailing_status,
        overall_status=(
            RuleStatus.PASS
            if rule_evaluation.detailing_status in {RuleStatus.PASS, RuleStatus.NOT_APPLICABLE}
            else rule_evaluation.detailing_status
        ),
        rule_checks=rule_evaluation.checks,
        governing_code_rule=(
            code_spacing_limit.check.rule_id if code_spacing_limit is not None else None
        ),
        governing_code_limit_mm=(
            code_spacing_limit.maximum_mm if code_spacing_limit is not None else None
        ),
        governing_demand_check=(
            demand_spacing_limit.check_id if demand_spacing_limit is not None else None
        ),
        governing_demand_spacing_limit_mm=(
            demand_spacing_limit.maximum_mm if demand_spacing_limit is not None else None
        ),
        governing_demand_source=(
            demand_spacing_limit.source if demand_spacing_limit is not None else None
        ),
        governing_demand_station_mm=(
            demand_spacing_limit.station_mm if demand_spacing_limit is not None else None
        ),
        governing_project_spacing_limit_mm=project_spacing_limit_mm,
    )


def failed_candidate(
    *,
    e_bar: str,
    g_bar: str,
    g_count: int,
    spacing_mm: int,
    long_bar: str | None,
    long_count: int,
    failure_mode: FailureMode,
    message: str,
    at: float = 0.0,
    at_over_s: float = 0.0,
    av1: float = 0.0,
    av2: float = 0.0,
    av_total: float = 0.0,
    av_over_s: float = 0.0,
    long_provided: float = 0.0,
    f_free: float = 0.0,
    objective: float = 1.0e9,
    transverse_weight_kg_per_m: float = 0.0,
    stirrup_unit_weight_kg: float = 0.0,
    controlling_limit: str = "",
    deficit: float = 1.0,
    longitudinal_weight_kg_per_m: float = 0.0,
    demand_status: RuleStatus | None = None,
    detailing_status: RuleStatus | None = None,
    rule_checks: tuple[RuleCheck, ...] = (),
    governing_code_rule: str | None = None,
    governing_code_limit_mm: float | None = None,
    governing_demand_check: str | None = None,
    governing_demand_spacing_limit_mm: float | None = None,
    governing_demand_source: DemandSource | None = None,
    governing_demand_station_mm: float | None = None,
    governing_project_spacing_limit_mm: float | None = None,
) -> Candidate:
    penalty = 1.0e6 * (1.0 + max(deficit, 0.0))
    resolved_demand_status = demand_status
    if resolved_demand_status is None:
        resolved_demand_status = (
            RuleStatus.FAIL
            if failure_mode in {"torsion_fail", "shear_fail", "longitudinal_fail"}
            else RuleStatus.NOT_EVALUATED
        )
    resolved_detailing_status = detailing_status
    if resolved_detailing_status is None:
        resolved_detailing_status = (
            RuleStatus.FAIL if failure_mode == "region_detail_fail" else RuleStatus.NOT_EVALUATED
        )
    return Candidate(
        e_bar=e_bar,
        g_bar=g_bar,
        g_count=g_count,
        spacing_mm=spacing_mm,
        long_bar=long_bar,
        long_count=long_count,
        at=at,
        at_over_s=at_over_s,
        av1=av1,
        av2=av2,
        av_total=av_total,
        av_over_s=av_over_s,
        long_provided=long_provided,
        f_free=f_free,
        failure_mode=failure_mode,
        status="fail",
        message=message,
        objective=objective,
        score=objective + penalty,
        transverse_weight_kg_per_m=transverse_weight_kg_per_m,
        longitudinal_weight_kg_per_m=longitudinal_weight_kg_per_m,
        stirrup_unit_weight_kg=stirrup_unit_weight_kg,
        controlling_limit=controlling_limit,
        demand_status=resolved_demand_status,
        detailing_status=resolved_detailing_status,
        overall_status=RuleStatus.FAIL,
        rule_checks=rule_checks,
        governing_code_rule=governing_code_rule,
        governing_code_limit_mm=governing_code_limit_mm,
        governing_demand_check=governing_demand_check,
        governing_demand_spacing_limit_mm=governing_demand_spacing_limit_mm,
        governing_demand_source=governing_demand_source,
        governing_demand_station_mm=governing_demand_station_mm,
        governing_project_spacing_limit_mm=governing_project_spacing_limit_mm,
    )


def evaluate_region_rule_checks(
    region: RegionDemand,
    *,
    spacing_mm: int,
    g_count: int,
    e_bar: str,
    g_bar: str,
) -> AciRuleEvaluation:
    longitudinal_diameter = (
        region.longitudinal_bar_diameter_mm
        if region.longitudinal_bar_diameter_mm is not None
        else BAR_DIAMETERS_MM.get(region.db_bar or "")
    )
    e_diameter = BAR_DIAMETERS_MM.get(e_bar)
    g_diameter = BAR_DIAMETERS_MM.get(g_bar) if g_count > 0 else None
    e_area = BAR_AREAS_MM2.get(e_bar)
    g_area = BAR_AREAS_MM2.get(g_bar) if g_count > 0 else 0.0
    transverse_diameter = min(
        diameter for diameter in (e_diameter, g_diameter) if diameter is not None
    ) if e_diameter is not None else None
    shear_controller = max(
        region.scenarios,
        key=lambda scenario: scenario.v_rebar_mm2_per_m,
        default=None,
    )
    torsion_controller = region.governing_t_transverse_scenario
    return evaluate_region_rules(
        system=region.beam_detailing,
        zone=region.region_type,
        spacing_mm=float(spacing_mm),
        d_mm=region.d_mm,
        longitudinal_bar_diameter_mm=longitudinal_diameter,
        transverse_bar_diameter_mm=transverse_diameter,
        minimum_branches=region.min_branches,
        provided_branches=2 + g_count,
        compression_rebar_required=region.compression_rebar_required,
        torsion_states=tuple(scenario.torsion_state for scenario in region.scenarios),
        torsion_station=(torsion_controller.station_mm if torsion_controller is not None else None),
        width_mm=region.width_mm,
        height_mm=region.height_mm,
        cover_side_mm=region.cover_side_mm,
        cover_top_mm=region.cover_top_mm,
        cover_bottom_mm=region.cover_bottom_mm,
        fc_mpa=region.fc_mpa,
        fy_mpa=region.fy_mpa,
        required_av_per_s_mm2_per_m=(
            shear_controller.v_rebar_mm2_per_m if shear_controller is not None else None
        ),
        shear_station=(shear_controller.station_mm if shear_controller is not None else None),
        provided_combined_transverse_mm2_per_m=(
            ((2.0 * e_area) + (g_count * g_area)) * 1000.0 / spacing_mm
            if e_area is not None and g_area is not None and spacing_mm > 0
            else None
        ),
        closed_stirrup_bar_diameter_mm=e_diameter,
        seismic_zone_length_mm=(
            region.region_length_mm if region.region_length_mm > 0.0 else None
        ),
    )


def format_rule_evaluation_message(
    region: RegionDemand,
    spacing_mm: int,
    evaluation: AciRuleEvaluation,
) -> str:
    closed_stirrup_failure = next(
        (
            check
            for check in evaluation.checks
            if check.rule_id == "ACI318_25_9_7_6_3_1_CLOSED_STIRRUP"
            and check.status == RuleStatus.FAIL
        ),
        None,
    )
    if closed_stirrup_failure is not None:
        return (
            f"{region.beam_detailing} region {region.region_type} with TTrnRebar>0 requires "
            "minimum branches: min_branches >= 2 (closed stirrup equivalent)"
        )

    controlling = evaluation.controlling_limit
    if controlling is not None and controlling.check.status == RuleStatus.FAIL:
        formatted_limits = ", ".join(
            f"{limit.label}={limit.maximum_mm:.1f}"
            for limit in evaluation.spacing_limits
            if limit.maximum_mm is not None
        )
        return (
            f"{region.beam_detailing} region {region.region_type} spacing limit failed: "
            f"s={spacing_mm} > min({formatted_limits}) = {controlling.maximum_mm:.1f} mm"
        )

    failure = next(
        (
            check
            for check in evaluation.checks
            if check.status == RuleStatus.FAIL and check.candidate_dependent
        ),
        None,
    )
    return failure.applicability_reason if failure is not None else "ACI detailing rules satisfied"


def deficit_ratio(required: float, provided: float) -> float:
    if required <= 0.0:
        return 0.0
    if provided >= required:
        return 0.0
    return (required - provided) / required


def g_count_domain_for_region(region: RegionDemand, configured_g_counts: list[int]) -> tuple[list[int], int]:
    if region.beam_detailing != "DMO" or region.region_type != "C" or region.min_branches is None:
        return configured_g_counts, 0
    min_required_g = max(0, region.min_branches - 2)
    allowed = [g for g in configured_g_counts if g >= min_required_g]
    return allowed, min_required_g


def stirrup_count_in_region(region_length_mm: float, spacing_mm: int) -> int:
    if spacing_mm <= 0 or region_length_mm <= 0.0:
        return 0
    return max(1, math.floor(region_length_mm / float(spacing_mm)) + 1)


def stirrup_set_unit_weight_kg(
    *,
    region: RegionDemand,
    e_bar: str,
    g_bar: str,
    g_count: int,
    at: float,
    ag: float,
) -> float:
    if (
        region.width_mm is None
        or region.height_mm is None
        or region.cover_side_mm is None
        or region.cover_top_mm is None
        or region.cover_bottom_mm is None
    ):
        # Backward-compatible proxy when geometry is not available.
        return ((2.0 * at) + (g_count * ag)) * 1000.0 * STEEL_DENSITY_KG_PER_MM3

    stirrup_width_mm = region.width_mm - 2.0 * region.cover_side_mm
    stirrup_height_mm = region.height_mm - (region.cover_top_mm + region.cover_bottom_mm)
    if stirrup_width_mm <= 0.0 or stirrup_height_mm <= 0.0:
        return ((2.0 * at) + (g_count * ag)) * 1000.0 * STEEL_DENSITY_KG_PER_MM3

    e_diameter = BAR_DIAMETERS_MM.get(e_bar)
    g_diameter = BAR_DIAMETERS_MM.get(g_bar)
    hook_len_e = HOOK_LENGTH_MM_BY_BAR.get(e_bar, (HOOK_LENGTH_FACTOR_FALLBACK * e_diameter) if e_diameter else 0.0)
    hook_len_g = HOOK_LENGTH_MM_BY_BAR.get(g_bar, (HOOK_LENGTH_FACTOR_FALLBACK * g_diameter) if g_diameter else 0.0)

    # Estribo cerrado exterior: L = 2*(h + b + gancho)
    closed_length_mm = 2.0 * (stirrup_height_mm + stirrup_width_mm + hook_len_e)
    closed_weight_kg = at * closed_length_mm * STEEL_DENSITY_KG_PER_MM3

    # Estribo de una sola rama: L = h + 2*gancho
    single_branch_length_mm = stirrup_height_mm + 2.0 * hook_len_g
    single_branch_weight_kg = ag * single_branch_length_mm * STEEL_DENSITY_KG_PER_MM3

    return closed_weight_kg + max(0, g_count) * single_branch_weight_kg


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

def requires_longitudinal_design(region: RegionDemand) -> bool:
    return any(scenario.torsion_state == "ACTIVE" for scenario in region.scenarios)


def select_longitudinal_independent(
    region: RegionDemand,
    variables: VariablesConfig,
) -> tuple[str | None, int, float, bool]:
    if not requires_longitudinal_design(region):
        return None, 0, 0.0, True

    options: list[tuple[float, str, int]] = []
    for long_bar in variables.longitudinal_bars:
        for long_count in variables.longitudinal_bar_counts:
            provided = BAR_AREAS_MM2[long_bar] * long_count
            options.append((provided, long_bar, long_count))
    options.sort(key=lambda item: item[0])

    for provided, long_bar, long_count in options:
        if all(scenario.t_longitudinal_mm2 <= provided for scenario in region.scenarios):
            return long_bar, long_count, provided, True

    provided, long_bar, long_count = options[-1]
    return long_bar, long_count, provided, False


def uses_dynamic_spacing_catalog(variables: VariablesConfig) -> bool:
    configured = variables.stirrup_spacing_mm
    return configured is None or tuple(configured) == LEGACY_FIXED_STIRRUP_SPACING_MM


def _discrete_spacings_through(
    maximum_mm: float,
    *,
    minimum_mm: int,
    step_mm: int,
) -> list[int]:
    if minimum_mm <= 0 or step_mm <= 0 or maximum_mm <= 0.0:
        return []
    first = int(math.ceil(minimum_mm / step_mm) * step_mm)
    last = int(
        math.floor(
            (maximum_mm + dimensional_comparison_tolerance_mm) / step_mm
        )
        * step_mm
    )
    if last < first:
        return []
    return list(range(first, last + step_mm, step_mm))


def spacing_domain_for_region(
    region: RegionDemand,
    variables: VariablesConfig,
    allowed_g_counts: list[int],
) -> list[int]:
    """Build the spacing search domain without an implicit global maximum."""
    project_limit_mm = variables.stirrup_spacing_project_max_mm
    if not uses_dynamic_spacing_catalog(variables):
        configured = sorted(set(variables.stirrup_spacing_mm or []))
        if project_limit_mm is None:
            return configured
        return [
            spacing
            for spacing in configured
            if spacing <= project_limit_mm + dimensional_comparison_tolerance_mm
        ]

    generated: set[int] = set()
    probe_spacing = variables.stirrup_spacing_min_mm
    for e_bar, g_bar, g_count in itertools.product(
        variables.E_bars,
        variables.G_bars,
        allowed_g_counts,
    ):
        at = BAR_AREAS_MM2.get(e_bar)
        ag = BAR_AREAS_MM2.get(g_bar)
        if at is None or ag is None:
            continue
        demand_limit = governing_demand_spacing_limit(
            region,
            at_mm2=at,
            ag_mm2=ag,
            g_count=g_count,
        )
        rule_evaluation = evaluate_region_rule_checks(
            region,
            spacing_mm=probe_spacing,
            g_count=g_count,
            e_bar=e_bar,
            g_bar=g_bar,
        )
        real_limits = [
            limit
            for limit in (
                (
                    rule_evaluation.controlling_limit.maximum_mm
                    if rule_evaluation.controlling_limit is not None
                    else None
                ),
                demand_limit.maximum_mm if demand_limit is not None else None,
                project_limit_mm,
            )
            if limit is not None
        ]
        if not real_limits:
            continue
        s_max_real = min(real_limits)
        generated.update(
            _discrete_spacings_through(
                s_max_real,
                minimum_mm=variables.stirrup_spacing_min_mm,
                step_mm=variables.stirrup_spacing_step_mm,
            )
        )
    return sorted(generated)


def optimize_region(region: RegionDemand, optimization: OptimizationConfig) -> OptimizationOutcome:
    check_longitudinal = optimization.longitudinal_mode == "legacy_region_independent"
    if optimization.enabled:
        return optimize_region_ga(region, optimization, check_longitudinal=check_longitudinal)
    return optimize_region_exhaustive(
        region,
        optimization.variables,
        check_longitudinal=check_longitudinal,
    )


def optimize_region_exhaustive(
    region: RegionDemand,
    variables: VariablesConfig,
    *,
    check_longitudinal: bool = True,
) -> OptimizationOutcome:
    allowed_g_counts, min_required_g = g_count_domain_for_region(region, variables.G_counts)
    if not allowed_g_counts:
        selected = failed_candidate(
            e_bar=variables.E_bars[0],
            g_bar=variables.G_bars[0],
            g_count=0,
            spacing_mm=(variables.stirrup_spacing_mm or [variables.stirrup_spacing_min_mm])[0],
            long_bar=variables.longitudinal_bars[0],
            long_count=0,
            failure_mode="input_fail",
            message=(
                f"No G_counts satisfy min_branches={region.min_branches}; "
                f"required G_count >= {min_required_g}"
            ),
            objective=1.0e9,
            deficit=1.0,
        )
        return OptimizationOutcome(
            selected=selected,
            evaluated_candidates=0,
            feasible_candidates=0,
            method="exhaustive",
            failure_counts={"input_fail": 1},
        )

    spacing_domain = spacing_domain_for_region(region, variables, allowed_g_counts)
    if not spacing_domain:
        selected = failed_candidate(
            e_bar=variables.E_bars[0],
            g_bar=variables.G_bars[0],
            g_count=allowed_g_counts[0],
            spacing_mm=variables.stirrup_spacing_min_mm,
            long_bar=None,
            long_count=0,
            failure_mode="input_fail",
            message=(
                "No spacing candidate can be generated from evaluated ACI, demand, "
                "or explicit project limits"
            ),
            objective=1.0e9,
            deficit=1.0,
        )
        return OptimizationOutcome(
            selected=selected,
            evaluated_candidates=0,
            feasible_candidates=0,
            method="exhaustive",
            failure_counts={"input_fail": 1},
        )

    domain: list[list[str | int]] = [
        variables.E_bars,
        variables.G_bars,
        allowed_g_counts,
        spacing_domain,
    ]
    if check_longitudinal:
        default_long_bar, default_long_count, _, _ = select_longitudinal_independent(region, variables)
    else:
        default_long_bar = variables.longitudinal_bars[0]
        default_long_count = 0

    def decode(individual: list[int]) -> tuple[str, str, int, int]:
        return (
            str(domain[0][individual[0]]),
            str(domain[1][individual[1]]),
            int(domain[2][individual[2]]),
            int(domain[3][individual[3]]),
        )

    def evaluate_individual(individual: list[int]) -> Candidate:
        e_bar, g_bar, g_count, spacing_mm = decode(individual)
        candidate = evaluate_candidate(
            region,
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing_mm,
            long_bar=default_long_bar,
            long_count=default_long_count,
            check_longitudinal=check_longitudinal,
            project_spacing_limit_mm=variables.stirrup_spacing_project_max_mm,
        )
        return candidate

    hooks = SearchHooks[Candidate](
        evaluate=evaluate_individual,
        score=lambda candidate: candidate.score,
        objective=lambda candidate: candidate.objective,
        is_feasible=lambda candidate: candidate.status == "ok",
        failure_mode=lambda candidate: candidate.failure_mode,
        tie_break=lambda candidate: transverse_alternative_rank_key(
            weight_kg=candidate.objective,
            spacing_mm=candidate.spacing_mm,
            stable_tie_break=(
                candidate.e_bar,
                candidate.g_bar,
                candidate.g_count,
            ),
        ),
    )
    outcome = run_exhaustive_search(
        domain_sizes=[len(values) for values in domain],
        hooks=hooks,
    )
    return OptimizationOutcome(
        selected=outcome.selected,
        evaluated_candidates=outcome.evaluated_candidates,
        feasible_candidates=outcome.feasible_candidates,
        method="exhaustive",
        failure_counts=outcome.failure_counts,
    )


def optimize_region_ga(
    region: RegionDemand,
    optimization: OptimizationConfig,
    *,
    check_longitudinal: bool | None = None,
) -> OptimizationOutcome:
    variables = optimization.variables
    ga = optimization.genetic_algorithm
    if check_longitudinal is None:
        check_longitudinal = optimization.longitudinal_mode == "legacy_region_independent"
    allowed_g_counts, min_required_g = g_count_domain_for_region(region, variables.G_counts)
    if not allowed_g_counts:
        selected = failed_candidate(
            e_bar=variables.E_bars[0],
            g_bar=variables.G_bars[0],
            g_count=0,
            spacing_mm=(variables.stirrup_spacing_mm or [variables.stirrup_spacing_min_mm])[0],
            long_bar=variables.longitudinal_bars[0],
            long_count=0,
            failure_mode="input_fail",
            message=(
                f"No G_counts satisfy min_branches={region.min_branches}; "
                f"required G_count >= {min_required_g}"
            ),
            objective=1.0e9,
            deficit=1.0,
        )
        return OptimizationOutcome(
            selected=selected,
            evaluated_candidates=0,
            feasible_candidates=0,
            method="genetic",
            failure_counts={"input_fail": 1},
        )

    spacing_domain = spacing_domain_for_region(region, variables, allowed_g_counts)
    if not spacing_domain:
        selected = failed_candidate(
            e_bar=variables.E_bars[0],
            g_bar=variables.G_bars[0],
            g_count=allowed_g_counts[0],
            spacing_mm=variables.stirrup_spacing_min_mm,
            long_bar=None,
            long_count=0,
            failure_mode="input_fail",
            message=(
                "No spacing candidate can be generated from evaluated ACI, demand, "
                "or explicit project limits"
            ),
            objective=1.0e9,
            deficit=1.0,
        )
        return OptimizationOutcome(
            selected=selected,
            evaluated_candidates=0,
            feasible_candidates=0,
            method="genetic",
            failure_counts={"input_fail": 1},
        )

    domain: list[list[str | int]] = [
        variables.E_bars,
        variables.G_bars,
        allowed_g_counts,
        spacing_domain,
    ]
    domain_sizes = [len(values) for values in domain]
    if check_longitudinal:
        default_long_bar, default_long_count, _, _ = select_longitudinal_independent(region, variables)
    else:
        default_long_bar = variables.longitudinal_bars[0]
        default_long_count = 0

    def decode(individual: list[int]) -> tuple[str, str, int, int]:
        return (
            str(domain[0][individual[0]]),
            str(domain[1][individual[1]]),
            int(domain[2][individual[2]]),
            int(domain[3][individual[3]]),
        )

    evaluation_cache: dict[tuple[int, ...], Candidate] = {}

    def evaluate_individual(individual: list[int]) -> Candidate:
        key = tuple(int(gene) for gene in individual)
        cached = evaluation_cache.get(key)
        if cached is not None:
            return cached

        e_bar, g_bar, g_count, spacing_mm = decode(individual)
        candidate = evaluate_candidate(
            region,
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing_mm,
            long_bar=default_long_bar,
            long_count=default_long_count,
            check_longitudinal=check_longitudinal,
            project_spacing_limit_mm=variables.stirrup_spacing_project_max_mm,
        )
        evaluation_cache[key] = candidate
        return candidate

    hooks = SearchHooks[Candidate](
        evaluate=evaluate_individual,
        score=lambda candidate: candidate.score,
        objective=lambda candidate: candidate.objective,
        is_feasible=lambda candidate: candidate.status == "ok",
        failure_mode=lambda candidate: candidate.failure_mode,
        tie_break=lambda candidate: transverse_alternative_rank_key(
            weight_kg=candidate.objective,
            spacing_mm=candidate.spacing_mm,
            stable_tie_break=(
                candidate.e_bar,
                candidate.g_bar,
                candidate.g_count,
            ),
        ),
    )
    outcome = run_genetic_search(
        domain_sizes=domain_sizes,
        population_size=ga.population_size,
        generations=ga.generations,
        crossover_rate=ga.crossover_rate,
        mutation_rate=ga.mutation_rate,
        elite_count=ga.elite_count,
        hooks=hooks,
        seed=42,
        fitness_class_name=DEAP_FITNESS_CLASS,
        individual_class_name=DEAP_INDIVIDUAL_CLASS,
    )
    return OptimizationOutcome(
        selected=outcome.selected,
        evaluated_candidates=outcome.evaluated_candidates,
        feasible_candidates=outcome.feasible_candidates,
        method="genetic",
        failure_counts=outcome.failure_counts,
    )


def candidate_to_region_result(
    demand: RegionDemand,
    candidate: Candidate,
    *,
    method: str,
    evaluated_candidates: int,
    feasible_candidates: int,
) -> RegionDesignResult:
    torsion_controller = demand.governing_t_transverse_scenario
    combined_controller = demand.governing_combined_scenario
    longitudinal_controller = demand.governing_longitudinal_scenario
    combined_capacity = (
        ((2.0 * candidate.at) + candidate.av2) * 1000.0 / candidate.spacing_mm
        if candidate.spacing_mm > 0
        else 0.0
    )
    consistent = all(item.torsion_state != "INCONSISTENT" for item in demand.scenarios)
    return RegionDesignResult(
        beam_id=demand.beam_id,
        span_id=demand.span_id,
        region_id=demand.region_id,
        region_type=demand.region_type,
        source_control=demand.source_control,
        governing_station=demand.governing_station,
        v_req=demand.v_req,
        t_req=demand.t_req,
        l_req=demand.l_req,
        e_bar=candidate.e_bar,
        g_bar=candidate.g_bar,
        g_count=candidate.g_count,
        spacing_mm=candidate.spacing_mm,
        av1=candidate.av1,
        av2=candidate.av2,
        av_total=candidate.av_total,
        at=candidate.at,
        at_over_s=candidate.at_over_s,
        av_over_s=candidate.av_over_s,
        long_bar=(candidate.long_bar if candidate.long_count > 0 else None),
        long_count=(candidate.long_count if candidate.long_count > 0 else 0),
        controlling_limit=candidate.controlling_limit,
        failure_mode=candidate.failure_mode,
        status=candidate.status,
        message=candidate.message,
        objective=candidate.objective,
        method=method,
        evaluated_candidates=evaluated_candidates,
        feasible_candidates=feasible_candidates,
        transverse_weight_kg_per_m=candidate.transverse_weight_kg_per_m,
        longitudinal_weight_kg_per_m=candidate.longitudinal_weight_kg_per_m,
        stirrup_unit_weight_kg=candidate.stirrup_unit_weight_kg,
        torsion_governing_source=(torsion_controller.source if torsion_controller else None),
        torsion_governing_station=(torsion_controller.station_mm if torsion_controller else None),
        combined_governing_source=(combined_controller.source if combined_controller else None),
        combined_governing_station=(combined_controller.station_mm if combined_controller else None),
        longitudinal_governing_source=(longitudinal_controller.source if longitudinal_controller else None),
        longitudinal_governing_station=(longitudinal_controller.station_mm if longitudinal_controller else None),
        scenario_count=len(demand.scenarios),
        torsion_check_override=consistent and all(
            item.t_transverse_mm2_per_m <= candidate.at_over_s for item in demand.scenarios
        ),
        combined_check_override=consistent and all(
            item.v_rebar_mm2_per_m + 2.0 * item.t_transverse_mm2_per_m <= combined_capacity
            for item in demand.scenarios
        ),
        longitudinal_check_override=consistent and all(
            item.t_longitudinal_mm2 <= candidate.long_provided for item in demand.scenarios
        ),
        demand_status=candidate.demand_status,
        detailing_status=candidate.detailing_status,
        overall_status=candidate.overall_status,
        rule_checks=candidate.rule_checks,
        governing_code_rule=candidate.governing_code_rule,
        governing_code_limit_mm=candidate.governing_code_limit_mm,
        governing_demand_check=candidate.governing_demand_check,
        governing_demand_spacing_limit_mm=candidate.governing_demand_spacing_limit_mm,
        governing_demand_source=candidate.governing_demand_source,
        governing_demand_station_mm=candidate.governing_demand_station_mm,
        governing_project_spacing_limit_mm=candidate.governing_project_spacing_limit_mm,
        d_mm=demand.d_mm,
        d_source=demand.d_source,
        d_ratio=demand.d_ratio,
        detailing_system=demand.beam_detailing,
    )


def top_region_alternatives(
    region: RegionDemand,
    variables: VariablesConfig,
    *,
    top_n: int | None = 10,
    check_longitudinal: bool = True,
) -> list[RegionDesignResult]:
    allowed_g_counts, _ = g_count_domain_for_region(region, variables.G_counts)
    if not allowed_g_counts:
        return []
    spacing_domain = spacing_domain_for_region(region, variables, allowed_g_counts)
    if not spacing_domain:
        return []

    limit: int | None
    if top_n is None:
        limit = None
    else:
        top_n_int = int(top_n)
        limit = None if top_n_int <= 0 else max(1, top_n_int)
    if check_longitudinal:
        default_long_bar, default_long_count, _, _ = select_longitudinal_independent(region, variables)
    else:
        default_long_bar = variables.longitudinal_bars[0]
        default_long_count = 0

    evaluated: list[Candidate] = []
    for e_bar, g_bar, g_count, spacing in itertools.product(
        variables.E_bars,
        variables.G_bars,
        allowed_g_counts,
        spacing_domain,
    ):
        candidate = evaluate_candidate(
            region,
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing,
            long_bar=default_long_bar,
            long_count=default_long_count,
            check_longitudinal=check_longitudinal,
            project_spacing_limit_mm=variables.stirrup_spacing_project_max_mm,
        )
        evaluated.append(candidate)

    feasible = sorted(
        (candidate for candidate in evaluated if candidate.status == "ok"),
        key=lambda candidate: transverse_alternative_rank_key(
            weight_kg=candidate.objective,
            spacing_mm=candidate.spacing_mm,
            stable_tie_break=(
                candidate.e_bar,
                candidate.g_bar,
                candidate.g_count,
            ),
        ),
    )
    feasible_count = len(feasible)

    selected: list[Candidate] = []
    seen_transverse: set[tuple[str, str, int, int]] = set()
    for candidate in feasible:
        key = (candidate.e_bar, candidate.g_bar, candidate.g_count, candidate.spacing_mm)
        if key in seen_transverse:
            continue
        seen_transverse.add(key)
        selected.append(candidate)
        if limit is not None and len(selected) >= limit:
            break

    if not selected:
        failed = sorted(
            (candidate for candidate in evaluated if candidate.status != "ok"),
            key=lambda candidate: candidate.score,
        )
        for candidate in failed:
            key = (candidate.e_bar, candidate.g_bar, candidate.g_count, candidate.spacing_mm)
            if key in seen_transverse:
                continue
            seen_transverse.add(key)
            selected.append(candidate)
            if limit is not None and len(selected) >= limit:
                break

    return [
        candidate_to_region_result(
            region,
            candidate,
            method="top_transversal",
            evaluated_candidates=len(evaluated),
            feasible_candidates=feasible_count,
        )
        for candidate in selected
    ]
def to_region_result(
    demand: RegionDemand,
    outcome: OptimizationOutcome,
) -> RegionDesignResult:
    return candidate_to_region_result(
        demand,
        outcome.selected,
        method=outcome.method,
        evaluated_candidates=outcome.evaluated_candidates,
        feasible_candidates=outcome.feasible_candidates,
    )


def make_failed_region_result(
    demand: RegionDemand,
    *,
    failure_mode: FailureMode,
    message: str,
) -> RegionDesignResult:
    failed = failed_candidate(
        e_bar="",
        g_bar="",
        g_count=0,
        spacing_mm=0,
        long_bar=None,
        long_count=0,
        failure_mode=failure_mode,
        message=message,
        objective=1.0e9,
        deficit=1.0,
    )
    return candidate_to_region_result(
        demand,
        Candidate(
            e_bar=failed.e_bar,
            g_bar=failed.g_bar,
            g_count=failed.g_count,
            spacing_mm=failed.spacing_mm,
            long_bar=failed.long_bar,
            long_count=failed.long_count,
            at=failed.at,
            at_over_s=failed.at_over_s,
            av1=failed.av1,
            av2=failed.av2,
            av_total=failed.av_total,
            av_over_s=failed.av_over_s,
            long_provided=failed.long_provided,
            f_free=failed.f_free,
            failure_mode=failure_mode,
            status="fail",
            message=message,
            objective=failed.objective,
            score=failed.score,
            transverse_weight_kg_per_m=failed.transverse_weight_kg_per_m,
            longitudinal_weight_kg_per_m=failed.longitudinal_weight_kg_per_m,
            stirrup_unit_weight_kg=failed.stirrup_unit_weight_kg,
        ),
        method="none",
        evaluated_candidates=0,
        feasible_candidates=0,
    )








