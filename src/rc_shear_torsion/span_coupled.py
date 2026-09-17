from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .codes.aci318_25.longitudinal_torsion import (
    MAX_LONGITUDINAL_TORSION_BAR_SPACING_MM,
    longitudinal_torsion_bar_spacing_mm,
    minimum_longitudinal_torsion_bar_count,
    minimum_longitudinal_torsion_bar_diameter_mm,
    vertical_distribution_range_mm,
)

from .design import (
    RegionDemand,
    RegionDesignResult,
    requires_longitudinal_design,
    scenario_reference,
    stirrup_count_in_region,
)
from .models import OptimizationConfig
from .reinforcement import BAR_AREAS_MM2, BAR_DIAMETERS_MM, bar_mass_kg_per_m

@dataclass(frozen=True)
class SpanRegionState:
    demand: RegionDemand
    extra_long_bar: str
    extra_long_count: int
    long_provided_mm2: float
    layers: int
    s2_mm: float | None
    arrangement_label: str


@dataclass(frozen=True)
class SpanCandidate:
    base_long_bar: str
    base_long_count: int
    states: tuple[SpanRegionState, ...]
    status: Literal["ok", "fail"]
    failure_mode: str
    message: str
    objective: float
    score: float


@dataclass(frozen=True)
class SpanOptimizationOutcome:
    results: list[RegionDesignResult]
    alternatives_by_region: dict[tuple[str, str], list[RegionDesignResult]]
    method: str
    evaluated_candidates: int
    feasible_candidates: int
    failure_counts: dict[str, int]


def _failed_candidate(
    *,
    base_long_bar: str,
    base_long_count: int,
    failure_mode: str,
    message: str,
    objective: float = 1.0e9,
) -> SpanCandidate:
    penalty = 1.0e6
    return SpanCandidate(
        base_long_bar=base_long_bar,
        base_long_count=base_long_count,
        states=tuple(),
        status="fail",
        failure_mode=failure_mode,
        message=message,
        objective=objective,
        score=objective + penalty,
    )


def _arrangement_label(base_bar: str, base_count: int, extra_bar: str, extra_count: int) -> str:
    if base_count <= 0 and extra_count <= 0:
        return "no se requiere"
    if base_count <= 0 and extra_count > 0:
        return f"{extra_count} x {extra_bar}"
    if extra_count <= 0:
        return f"{base_count} x {base_bar}"
    if extra_bar == base_bar:
        return f"{base_count + extra_count} x {base_bar}"
    return f"{base_count} x {base_bar} + {extra_count} x {extra_bar}"


def longitudinal_vertical_range_mm(demand: RegionDemand) -> float | None:
    """Vertical distance delimited by the existing top and bottom flexural steel."""
    if demand.d_mm is None or demand.height_mm is None:
        return None
    return vertical_distribution_range_mm(
        height_mm=demand.height_mm,
        d_mm=demand.d_mm,
    )


def longitudinal_layer_spacing_mm(demand: RegionDemand, total_count: int) -> float | None:
    """Spacing of intermediate torsional side-face bars per ACI 318-25 9.7.5.1."""
    if demand.d_mm is None or demand.height_mm is None:
        return None
    return longitudinal_torsion_bar_spacing_mm(
        height_mm=demand.height_mm,
        d_mm=demand.d_mm,
        total_torsion_bar_count=total_count,
    )


def minimum_longitudinal_count_for_distribution(demand: RegionDemand) -> int | None:
    """Smallest even total count satisfying the adopted 300 mm distribution limit."""
    if demand.d_mm is None or demand.height_mm is None:
        return None
    return minimum_longitudinal_torsion_bar_count(
        height_mm=demand.height_mm,
        d_mm=demand.d_mm,
    )


def minimum_torsion_longitudinal_bar_diameter_mm(transverse_spacing_mm: float) -> float:
    """ACI 318-25 9.7.5.2 minimum diameter for longitudinal torsional bars."""
    return minimum_longitudinal_torsion_bar_diameter_mm(transverse_spacing_mm)


def _evaluate_longitudinal_region(
    demand: RegionDemand,
    *,
    base_long_bar: str,
    base_long_count: int,
    extra_long_bar: str,
    extra_long_count: int,
    transverse_spacing_mm: float | None = None,
) -> tuple[bool, str, float, int, float | None]:
    if base_long_count < 0 or extra_long_count < 0:
        return False, "Longitudinal bar counts must be >= 0", 0.0, 0, None

    if base_long_count > 0 and base_long_bar not in BAR_AREAS_MM2:
        return False, "Unsupported longitudinal bar designation", 0.0, 0, None
    if extra_long_count > 0 and extra_long_bar not in BAR_AREAS_MM2:
        return False, "Unsupported longitudinal bar designation", 0.0, 0, None

    base_area = BAR_AREAS_MM2.get(base_long_bar, 0.0) * base_long_count
    extra_area = BAR_AREAS_MM2.get(extra_long_bar, 0.0) * extra_long_count
    provided = base_area + extra_area

    needs_longitudinal = requires_longitudinal_design(demand)
    if not needs_longitudinal:
        return True, "no se requiere", 0.0, 0, None

    failing_scenario = next(
        (scenario for scenario in demand.scenarios if scenario.t_longitudinal_mm2 > provided),
        None,
    )
    if failing_scenario is not None:
        return (
            False,
            f"Along_real < TLngRebar at {scenario_reference(failing_scenario)}",
            provided,
            0,
            None,
        )

    total_count = base_long_count + extra_long_count
    layers = 0
    s2_mm: float | None = None

    if any(scenario.t_longitudinal_mm2 > 0.0 for scenario in demand.scenarios):
        if total_count < 2 or total_count % 2 != 0:
            return False, "Longitudinal bars must be arranged as 2 bars per layer", provided, 0, None

        if demand.d_mm is None or demand.height_mm is None:
            return False, "Longitudinal layering checks require d_mm and height_mm", provided, 0, None
        layers = total_count // 2
        available_range = longitudinal_vertical_range_mm(demand)
        if available_range is None:
            return False, "Longitudinal layering checks require d_mm and height_mm", provided, layers, None
        if available_range <= 0.0:
            return False, "2*d - h must be > 0 to place longitudinal side-face bars", provided, layers, None

        s2_mm = longitudinal_layer_spacing_mm(demand, total_count)
        if s2_mm is None:
            return False, "Longitudinal bar count must be even", provided, layers, None
        if s2_mm > MAX_LONGITUDINAL_TORSION_BAR_SPACING_MM:
            return (
                False,
                f"ACI 318-25 9.7.5.1 longitudinal spacing sL={s2_mm:.1f} mm exceeds 300 mm",
                provided,
                layers,
                s2_mm,
            )

        if transverse_spacing_mm is not None:
            minimum_diameter_mm = minimum_torsion_longitudinal_bar_diameter_mm(
                transverse_spacing_mm
            )
            for role, bar, count in (
                ("base", base_long_bar, base_long_count),
                ("additional", extra_long_bar, extra_long_count),
            ):
                if count <= 0:
                    continue
                diameter_mm = BAR_DIAMETERS_MM.get(bar)
                if diameter_mm is None or diameter_mm < minimum_diameter_mm:
                    return (
                        False,
                        (
                            f"ACI 318-25 9.7.5.2 {role} bar {bar} diameter "
                            f"{diameter_mm or 0.0:.1f} mm is less than {minimum_diameter_mm:.1f} mm"
                        ),
                        provided,
                        layers,
                        s2_mm,
                    )

    return True, "ok", provided, layers, s2_mm


def _region_result_from_state(
    *,
    state: SpanRegionState,
    span_candidate: SpanCandidate,
    transverse_template: RegionDesignResult | None,
    method: str,
    evaluated_candidates: int,
    feasible_candidates: int,
) -> RegionDesignResult:
    demand = state.demand

    if transverse_template is None:
        e_bar = ""
        g_bar = ""
        g_count = 0
        spacing_mm = 0
        av1 = 0.0
        av2 = 0.0
        av_total = 0.0
        at = 0.0
        at_over_s = 0.0
        av_over_s = 0.0
        controlling_limit = ""
        transverse_weight_kg_per_m = 0.0
        stirrup_unit_weight_kg = 0.0
    else:
        e_bar = transverse_template.e_bar
        g_bar = transverse_template.g_bar
        g_count = transverse_template.g_count
        spacing_mm = transverse_template.spacing_mm
        av1 = transverse_template.av1
        av2 = transverse_template.av2
        av_total = transverse_template.av_total
        at = transverse_template.at
        at_over_s = transverse_template.at_over_s
        av_over_s = transverse_template.av_over_s
        controlling_limit = transverse_template.controlling_limit
        transverse_weight_kg_per_m = transverse_template.transverse_weight_kg_per_m
        stirrup_unit_weight_kg = transverse_template.stirrup_unit_weight_kg

    region_length_m = max(0.0, demand.region_length_mm / 1000.0)
    transverse_region_weight_kg = 0.0
    if stirrup_unit_weight_kg > 0.0 and spacing_mm > 0:
        transverse_region_weight_kg = stirrup_unit_weight_kg * stirrup_count_in_region(
            demand.region_length_mm,
            spacing_mm,
        )

    needs_longitudinal = requires_longitudinal_design(demand)
    long_weight_kg_per_m = (
        bar_mass_kg_per_m(span_candidate.base_long_bar, span_candidate.base_long_count)
        + bar_mass_kg_per_m(state.extra_long_bar, state.extra_long_count)
        if needs_longitudinal
        else 0.0
    )
    long_region_weight_kg = long_weight_kg_per_m * region_length_m

    base_bar = span_candidate.base_long_bar if needs_longitudinal and span_candidate.base_long_count > 0 else None
    base_count = span_candidate.base_long_count if needs_longitudinal and span_candidate.base_long_count > 0 else None
    extra_bar = state.extra_long_bar if needs_longitudinal and state.extra_long_count > 0 else None
    extra_count = state.extra_long_count if needs_longitudinal and state.extra_long_count > 0 else None

    effective_long_count = (
        max(0, span_candidate.base_long_count) + max(0, state.extra_long_count)
        if needs_longitudinal
        else 0
    )
    effective_long_bar: str | None = None
    if effective_long_count > 0:
        effective_long_bar = span_candidate.base_long_bar if span_candidate.base_long_count > 0 else (state.extra_long_bar or "")

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
        e_bar=e_bar,
        g_bar=g_bar,
        g_count=g_count,
        spacing_mm=spacing_mm,
        av1=av1,
        av2=av2,
        av_total=av_total,
        at=at,
        at_over_s=at_over_s,
        av_over_s=av_over_s,
        long_bar=effective_long_bar,
        long_count=effective_long_count,
        controlling_limit=controlling_limit,
        failure_mode="ok",
        status="ok",
        message="Longitudinal candidate satisfies checks",
        objective=transverse_region_weight_kg + long_region_weight_kg,
        method=method,
        evaluated_candidates=evaluated_candidates,
        feasible_candidates=feasible_candidates,
        transverse_weight_kg_per_m=transverse_weight_kg_per_m,
        longitudinal_weight_kg_per_m=long_weight_kg_per_m,
        stirrup_unit_weight_kg=stirrup_unit_weight_kg,
        long_provided_mm2_override=state.long_provided_mm2,
        base_long_bar=base_bar,
        base_long_count=base_count,
        extra_long_bar=extra_bar,
        extra_long_count=extra_count,
        longitudinal_mode="span_coupled",
        longitudinal_arrangement_label=state.arrangement_label,
        torsion_governing_source=(
            demand.governing_t_transverse_scenario.source
            if demand.governing_t_transverse_scenario is not None
            else None
        ),
        torsion_governing_station=(
            demand.governing_t_transverse_scenario.station_mm
            if demand.governing_t_transverse_scenario is not None
            else None
        ),
        combined_governing_source=(
            demand.governing_combined_scenario.source
            if demand.governing_combined_scenario is not None
            else None
        ),
        combined_governing_station=(
            demand.governing_combined_scenario.station_mm
            if demand.governing_combined_scenario is not None
            else None
        ),
        longitudinal_governing_source=(
            demand.governing_longitudinal_scenario.source
            if demand.governing_longitudinal_scenario is not None
            else None
        ),
        longitudinal_governing_station=(
            demand.governing_longitudinal_scenario.station_mm
            if demand.governing_longitudinal_scenario is not None
            else None
        ),
        scenario_count=len(demand.scenarios),
        torsion_check_override=(
            transverse_template.torsion_check_override if transverse_template is not None else False
        ),
        combined_check_override=(
            transverse_template.combined_check_override if transverse_template is not None else False
        ),
        longitudinal_check_override=all(
            scenario.t_longitudinal_mm2 <= state.long_provided_mm2
            for scenario in demand.scenarios
        ),
        demand_status=(transverse_template.demand_status if transverse_template is not None else "NOT_EVALUATED"),
        detailing_status=(transverse_template.detailing_status if transverse_template is not None else "NOT_EVALUATED"),
        overall_status=(transverse_template.overall_status if transverse_template is not None else "NOT_EVALUATED"),
        rule_checks=(transverse_template.rule_checks if transverse_template is not None else ()),
        governing_code_rule=(
            transverse_template.governing_code_rule if transverse_template is not None else None
        ),
        governing_code_limit_mm=(
            transverse_template.governing_code_limit_mm if transverse_template is not None else None
        ),
        governing_demand_check=(
            transverse_template.governing_demand_check if transverse_template is not None else None
        ),
        governing_demand_spacing_limit_mm=(
            transverse_template.governing_demand_spacing_limit_mm
            if transverse_template is not None
            else None
        ),
        governing_demand_source=(
            transverse_template.governing_demand_source if transverse_template is not None else None
        ),
        governing_demand_station_mm=(
            transverse_template.governing_demand_station_mm if transverse_template is not None else None
        ),
        governing_project_spacing_limit_mm=(
            transverse_template.governing_project_spacing_limit_mm
            if transverse_template is not None
            else None
        ),
        d_mm=demand.d_mm,
        d_source=demand.d_source,
        d_ratio=demand.d_ratio,
        detailing_system=demand.beam_detailing,
    )


def _failed_region_result(
    demand: RegionDemand,
    *,
    template: RegionDesignResult | None,
    method: str,
    message: str,
    failure_mode: str = "longitudinal_fail",
) -> RegionDesignResult:
    if template is None:
        e_bar = ""
        g_bar = ""
        g_count = 0
        spacing_mm = 0
        av1 = 0.0
        av2 = 0.0
        av_total = 0.0
        at = 0.0
        at_over_s = 0.0
        av_over_s = 0.0
        controlling_limit = ""
        transverse_weight_kg_per_m = 0.0
        stirrup_unit_weight_kg = 0.0
    else:
        e_bar = template.e_bar
        g_bar = template.g_bar
        g_count = template.g_count
        spacing_mm = template.spacing_mm
        av1 = template.av1
        av2 = template.av2
        av_total = template.av_total
        at = template.at
        at_over_s = template.at_over_s
        av_over_s = template.av_over_s
        controlling_limit = template.controlling_limit
        transverse_weight_kg_per_m = template.transverse_weight_kg_per_m
        stirrup_unit_weight_kg = template.stirrup_unit_weight_kg

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
        e_bar=e_bar,
        g_bar=g_bar,
        g_count=g_count,
        spacing_mm=spacing_mm,
        av1=av1,
        av2=av2,
        av_total=av_total,
        at=at,
        at_over_s=at_over_s,
        av_over_s=av_over_s,
        long_bar=None,
        long_count=0,
        controlling_limit=controlling_limit,
        failure_mode=failure_mode,
        status="fail",
        message=message,
        objective=1.0e9,
        method=method,
        evaluated_candidates=0,
        feasible_candidates=0,
        transverse_weight_kg_per_m=transverse_weight_kg_per_m,
        longitudinal_weight_kg_per_m=0.0,
        stirrup_unit_weight_kg=stirrup_unit_weight_kg,
        long_provided_mm2_override=0.0,
        base_long_bar=None,
        base_long_count=None,
        extra_long_bar=None,
        extra_long_count=None,
        longitudinal_mode="span_coupled",
        longitudinal_arrangement_label="no se requiere",
        torsion_governing_source=(
            demand.governing_t_transverse_scenario.source
            if demand.governing_t_transverse_scenario is not None
            else None
        ),
        torsion_governing_station=(
            demand.governing_t_transverse_scenario.station_mm
            if demand.governing_t_transverse_scenario is not None
            else None
        ),
        combined_governing_source=(
            demand.governing_combined_scenario.source
            if demand.governing_combined_scenario is not None
            else None
        ),
        combined_governing_station=(
            demand.governing_combined_scenario.station_mm
            if demand.governing_combined_scenario is not None
            else None
        ),
        longitudinal_governing_source=(
            demand.governing_longitudinal_scenario.source
            if demand.governing_longitudinal_scenario is not None
            else None
        ),
        longitudinal_governing_station=(
            demand.governing_longitudinal_scenario.station_mm
            if demand.governing_longitudinal_scenario is not None
            else None
        ),
        scenario_count=len(demand.scenarios),
        torsion_check_override=(template.torsion_check_override if template is not None else False),
        combined_check_override=(template.combined_check_override if template is not None else False),
        longitudinal_check_override=False,
        demand_status=(template.demand_status if template is not None else "NOT_EVALUATED"),
        detailing_status=(template.detailing_status if template is not None else "NOT_EVALUATED"),
        overall_status="FAIL",
        rule_checks=(template.rule_checks if template is not None else ()),
        d_mm=demand.d_mm,
        d_source=demand.d_source,
        d_ratio=demand.d_ratio,
        detailing_system=demand.beam_detailing,
    )


def optimize_span_coupled(
    demands: list[RegionDemand],
    optimization: OptimizationConfig,
    *,
    span_length_mm: float,
    top_n: int = 10,
    transverse_templates: dict[tuple[str, str], RegionDesignResult] | None = None,
) -> SpanOptimizationOutcome:
    method_prefix = "span_coupled"
    templates = transverse_templates or {}

    if not demands:
        return SpanOptimizationOutcome(
            results=[],
            alternatives_by_region={},
            method=f"{method_prefix}_none",
            evaluated_candidates=0,
            feasible_candidates=0,
            failure_counts={"input_fail": 1},
        )

    variables = optimization.variables
    base_long_bars = list(variables.longitudinal_bars)
    base_long_counts = sorted({0, *variables.longitudinal_bar_counts})
    extra_long_bars = list(variables.longitudinal_bars)
    default_extra_counts = sorted({0, *variables.longitudinal_bar_counts})

    if not base_long_bars or not base_long_counts:
        failed_results = [
            _failed_region_result(
                demand,
                template=templates.get((demand.span_id, demand.region_id)),
                method=f"{method_prefix}_none",
                message="longitudinal_bars and longitudinal_bar_counts cannot be empty",
                failure_mode="input_fail",
            )
            for demand in demands
        ]
        return SpanOptimizationOutcome(
            results=failed_results,
            alternatives_by_region={(demand.span_id, demand.region_id): [row] for demand, row in zip(demands, failed_results)},
            method=f"{method_prefix}_none",
            evaluated_candidates=0,
            feasible_candidates=0,
            failure_counts={"input_fail": 1},
        )

    method = f"{method_prefix}_conditional_exhaustive"
    selected = _failed_candidate(
        base_long_bar="",
        base_long_count=0,
        failure_mode="longitudinal_fail",
        message="No feasible conditional longitudinal candidate",
    )

    # The regional longitudinal choice is separable once a span base is fixed.
    # Evaluate that conditional minimum exactly so UI alternatives never depend
    # on whether the stochastic search happened to visit the zero-extra option.
    deterministic_evaluations = 0
    deterministic_candidates: list[SpanCandidate] = []
    if any(requires_longitudinal_design(demand) for demand in demands):
        base_arrangements = [
            (bar, count)
            for count in base_long_counts
            if count > 0
            for bar in base_long_bars
        ]
    else:
        base_arrangements = [("", 0)]
    extra_arrangements = [
        (bar, count)
        for count in default_extra_counts
        for bar in ([""] if count == 0 else extra_long_bars)
    ]

    for base_long_bar, base_long_count in base_arrangements:
        states: list[SpanRegionState] = []
        objective = 0.0
        feasible_base = True

        for demand in demands:
            transverse_template = templates.get((demand.span_id, demand.region_id))
            transverse_spacing_mm = (
                float(transverse_template.spacing_mm)
                if transverse_template is not None and transverse_template.spacing_mm > 0
                else None
            )
            region_options: list[tuple[float, float, int, str, SpanRegionState]] = []
            candidates = extra_arrangements if requires_longitudinal_design(demand) else [("", 0)]
            for extra_long_bar, extra_long_count in candidates:
                deterministic_evaluations += 1
                long_ok, _, long_provided, layers, s2_mm = _evaluate_longitudinal_region(
                    demand,
                    base_long_bar=base_long_bar,
                    base_long_count=base_long_count,
                    extra_long_bar=extra_long_bar,
                    extra_long_count=extra_long_count,
                    transverse_spacing_mm=transverse_spacing_mm,
                )
                if not long_ok:
                    continue

                region_length_m = max(0.0, demand.region_length_mm / 1000.0)
                region_objective = (
                    bar_mass_kg_per_m(base_long_bar, base_long_count)
                    + bar_mass_kg_per_m(extra_long_bar, extra_long_count)
                ) * region_length_m if requires_longitudinal_design(demand) else 0.0
                state = SpanRegionState(
                    demand=demand,
                    extra_long_bar=extra_long_bar,
                    extra_long_count=extra_long_count,
                    long_provided_mm2=long_provided,
                    layers=layers,
                    s2_mm=s2_mm,
                    arrangement_label=(
                        _arrangement_label(
                            base_long_bar,
                            base_long_count,
                            extra_long_bar,
                            extra_long_count,
                        )
                        if requires_longitudinal_design(demand)
                        else "no se requiere"
                    ),
                )
                region_options.append(
                    (
                        region_objective,
                        long_provided,
                        base_long_count + extra_long_count,
                        extra_long_bar,
                        state,
                    )
                )

            if not region_options:
                feasible_base = False
                break

            best_region = min(region_options, key=lambda item: item[:4])
            objective += best_region[0]
            states.append(best_region[4])

        if feasible_base:
            deterministic_candidates.append(
                SpanCandidate(
                    base_long_bar=base_long_bar,
                    base_long_count=base_long_count,
                    states=tuple(states),
                    status="ok",
                    failure_mode="ok",
                    message="Exact conditional longitudinal minimum",
                    objective=objective,
                    score=objective,
                )
            )

    if deterministic_candidates:
        deterministic_selected = min(
            deterministic_candidates,
            key=lambda item: (
                round(item.objective, 12),
                sum(state.extra_long_count for state in item.states),
                -item.base_long_count,
                item.base_long_bar,
            ),
        )
        if selected.status != "ok" or deterministic_selected.objective < selected.objective:
            selected = deterministic_selected

    feasible_unique: dict[tuple[object, ...], SpanCandidate] = {}
    for candidate in deterministic_candidates:
        if candidate.status != "ok":
            continue
        fingerprint = (
            candidate.base_long_bar,
            candidate.base_long_count,
            tuple(
                (
                    state.demand.span_id,
                    state.demand.region_id,
                    state.extra_long_bar,
                    state.extra_long_count,
                )
                for state in candidate.states
            ),
        )
        current = feasible_unique.get(fingerprint)
        if current is None or candidate.objective < current.objective:
            feasible_unique[fingerprint] = candidate

    feasible_sorted = sorted(feasible_unique.values(), key=lambda item: item.objective)
    if selected.status != "ok" and feasible_sorted:
        selected = feasible_sorted[0]

    evaluated_candidates = deterministic_evaluations
    feasible_candidates = len(deterministic_candidates)

    max_candidates = max(1, int(top_n))
    top_candidates: list[SpanCandidate] = []
    if feasible_sorted:
        by_base: dict[tuple[str, int], list[SpanCandidate]] = {}
        for candidate in feasible_sorted:
            key = (candidate.base_long_bar, candidate.base_long_count)
            by_base.setdefault(key, []).append(candidate)

        # Prioritize base diversity first (up to 10 base arrangements), then fill by objective.
        base_keys = sorted(by_base.keys(), key=lambda item: by_base[item][0].objective)[:10]
        per_base_quota = 10
        per_base_count: dict[tuple[str, int], int] = {key: 0 for key in base_keys}

        for key in base_keys:
            candidate = by_base[key][0]
            top_candidates.append(candidate)
            per_base_count[key] = 1
            if len(top_candidates) >= max_candidates:
                break

        depth = 1
        while len(top_candidates) < max_candidates:
            added = False
            for key in base_keys:
                if per_base_count[key] >= per_base_quota:
                    continue
                rows = by_base.get(key, [])
                if depth >= len(rows):
                    continue
                candidate = rows[depth]
                if candidate in top_candidates:
                    continue
                top_candidates.append(candidate)
                per_base_count[key] += 1
                added = True
                if len(top_candidates) >= max_candidates:
                    break
            if not added:
                break
            depth += 1

        if len(top_candidates) < max_candidates:
            for candidate in feasible_sorted:
                if candidate in top_candidates:
                    continue
                top_candidates.append(candidate)
                if len(top_candidates) >= max_candidates:
                    break

    if selected.status == "ok":
        selected_results = [
            _region_result_from_state(
                state=state,
                span_candidate=selected,
                transverse_template=templates.get((state.demand.span_id, state.demand.region_id)),
                method=method,
                evaluated_candidates=evaluated_candidates,
                feasible_candidates=feasible_candidates,
            )
            for state in selected.states
        ]
    else:
        selected_results = [
            _failed_region_result(
                demand,
                template=templates.get((demand.span_id, demand.region_id)),
                method=method,
                message=selected.message,
                failure_mode=selected.failure_mode,
            )
            for demand in demands
        ]

    alternatives_by_region: dict[tuple[str, str], list[RegionDesignResult]] = {}
    if top_candidates:
        for demand_index, demand in enumerate(demands):
            alternatives_by_region[(demand.span_id, demand.region_id)] = [
                _region_result_from_state(
                    state=candidate.states[demand_index],
                    span_candidate=candidate,
                    transverse_template=templates.get((demand.span_id, demand.region_id)),
                    method=f"{method_prefix}_top",
                    evaluated_candidates=evaluated_candidates,
                    feasible_candidates=feasible_candidates,
                )
                for candidate in top_candidates
            ]
    else:
        for result in selected_results:
            alternatives_by_region[(result.span_id, result.region_id)] = [result]

    return SpanOptimizationOutcome(
        results=selected_results,
        alternatives_by_region=alternatives_by_region,
        method=method,
        evaluated_candidates=evaluated_candidates,
        feasible_candidates=feasible_candidates,
        failure_counts={} if selected.status == "ok" else {selected.failure_mode: 1},
    )

