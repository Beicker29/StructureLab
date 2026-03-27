from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .design import (
    BAR_AREAS_MM2,
    DEAP_FITNESS_CLASS,
    DEAP_INDIVIDUAL_CLASS,
    RegionDemand,
    RegionDesignResult,
    longitudinal_mass_kg_per_m,
    requires_longitudinal_design,
    stirrup_count_in_region,
)
from .models import OptimizationConfig
from .optimization import SearchHooks, run_exhaustive_search, run_genetic_search

DEAP_SPAN_FITNESS_CLASS = f"{DEAP_FITNESS_CLASS}SpanCoupled"
DEAP_SPAN_INDIVIDUAL_CLASS = f"{DEAP_INDIVIDUAL_CLASS}SpanCoupled"
LARGE_EXHAUSTIVE_SPACE = 250_000


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


def _evaluate_longitudinal_region(
    demand: RegionDemand,
    *,
    base_long_bar: str,
    base_long_count: int,
    extra_long_bar: str,
    extra_long_count: int,
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
        return True, "no se requiere", provided, 0, None

    if provided < demand.l_req:
        return False, "Along_real < Along_req", provided, 0, None

    total_count = base_long_count + extra_long_count
    layers = 0
    s2_mm: float | None = None

    if demand.l_req > 0.0:
        if total_count < 2 or total_count % 2 != 0:
            return False, "Longitudinal bars must be arranged as 2 bars per layer", provided, 0, None

        if demand.d_mm is None or demand.height_mm is None:
            return False, "Longitudinal layering checks require d_mm and height_mm", provided, 0, None
        layers = total_count // 2
        available_range = 2.0 * demand.d_mm - demand.height_mm
        base_layers = 0.5 * float(max(0, base_long_count))
        s2_denominator = base_layers + 1.0

        if layers > 1:
            if available_range <= 0.0:
                return False, "2*d - h must be > 0 to place multiple longitudinal layers", provided, layers, None
            s2_mm = available_range / s2_denominator
            if s2_mm > 300.0:
                return False, f"Longitudinal layer spacing s2={s2_mm:.1f} mm exceeds 300 mm", provided, layers, s2_mm

    return True, "ok", provided, layers, s2_mm


def _estimate_search_space(domain_sizes: list[int], *, cap: int = 10**12) -> int:
    total = 1
    for size in domain_sizes:
        total *= max(1, int(size))
        if total >= cap:
            return cap
    return total


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

    long_weight_kg_per_m = longitudinal_mass_kg_per_m(state.long_provided_mm2)
    long_region_weight_kg = long_weight_kg_per_m * region_length_m

    base_bar = span_candidate.base_long_bar if span_candidate.base_long_count > 0 else None
    base_count = span_candidate.base_long_count if span_candidate.base_long_count > 0 else None
    extra_bar = state.extra_long_bar if state.extra_long_count > 0 else None
    extra_count = state.extra_long_count if state.extra_long_count > 0 else None

    effective_long_count = max(0, span_candidate.base_long_count) + max(0, state.extra_long_count)
    effective_long_bar = ""
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
        is_deep_beam=demand.is_deep_beam,
        longitudinal_mode="span_coupled",
        longitudinal_arrangement_label=state.arrangement_label,
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
        long_bar="",
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
        is_deep_beam=demand.is_deep_beam,
        longitudinal_mode="span_coupled",
        longitudinal_arrangement_label="no se requiere",
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

    region_extra_count_domains: list[list[int]] = []
    for demand in demands:
        if requires_longitudinal_design(demand):
            region_extra_count_domains.append(default_extra_counts)
        else:
            region_extra_count_domains.append([0])

    domain_sizes: list[int] = [len(base_long_bars), len(base_long_counts)]
    for extra_counts in region_extra_count_domains:
        domain_sizes.extend([len(extra_long_bars), len(extra_counts)])

    evaluation_cache: dict[tuple[int, ...], SpanCandidate] = {}
    span_length_m = max(0.0, span_length_mm / 1000.0)

    def decode(individual: list[int]) -> tuple[str, int, list[tuple[str, int]]]:
        offset = 0
        base_long_bar = str(base_long_bars[individual[offset]])
        offset += 1
        base_long_count = int(base_long_counts[individual[offset]])
        offset += 1

        decoded_regions: list[tuple[str, int]] = []
        for extra_counts in region_extra_count_domains:
            extra_long_bar = str(extra_long_bars[individual[offset]])
            offset += 1
            extra_long_count = int(extra_counts[individual[offset]])
            offset += 1
            decoded_regions.append((extra_long_bar, extra_long_count))

        return base_long_bar, base_long_count, decoded_regions

    def evaluate_individual(individual: list[int]) -> SpanCandidate:
        key = tuple(int(gene) for gene in individual)
        cached = evaluation_cache.get(key)
        if cached is not None:
            return cached

        base_long_bar, base_long_count, decoded_regions = decode(individual)
        base_long_area = BAR_AREAS_MM2.get(base_long_bar, 0.0) * base_long_count
        objective = longitudinal_mass_kg_per_m(base_long_area) * span_length_m

        states: list[SpanRegionState] = []
        for demand, decoded in zip(demands, decoded_regions):
            extra_long_bar, extra_long_count = decoded
            long_ok, long_message, long_provided, layers, s2_mm = _evaluate_longitudinal_region(
                demand,
                base_long_bar=base_long_bar,
                base_long_count=base_long_count,
                extra_long_bar=extra_long_bar,
                extra_long_count=extra_long_count,
            )
            if not long_ok:
                failed = _failed_candidate(
                    base_long_bar=base_long_bar,
                    base_long_count=base_long_count,
                    failure_mode="longitudinal_fail",
                    message=f"{demand.span_id}/{demand.region_id}: {long_message}",
                    objective=objective + 2.0e4,
                )
                evaluation_cache[key] = failed
                return failed

            extra_long_area = BAR_AREAS_MM2[extra_long_bar] * extra_long_count
            region_length_m = max(0.0, demand.region_length_mm / 1000.0)
            extra_long_region_kg = longitudinal_mass_kg_per_m(extra_long_area) * region_length_m
            objective += extra_long_region_kg

            states.append(
                SpanRegionState(
                    demand=demand,
                    extra_long_bar=extra_long_bar,
                    extra_long_count=extra_long_count,
                    long_provided_mm2=long_provided,
                    layers=layers,
                    s2_mm=s2_mm,
                    arrangement_label=_arrangement_label(
                        base_long_bar,
                        base_long_count,
                        extra_long_bar,
                        extra_long_count,
                    ),
                )
            )

        resolved = SpanCandidate(
            base_long_bar=base_long_bar,
            base_long_count=base_long_count,
            states=tuple(states),
            status="ok",
            failure_mode="ok",
            message="Longitudinal candidate satisfies checks",
            objective=objective,
            score=objective,
        )
        evaluation_cache[key] = resolved
        return resolved

    hooks = SearchHooks[SpanCandidate](
        evaluate=evaluate_individual,
        score=lambda candidate: candidate.score,
        objective=lambda candidate: candidate.objective,
        is_feasible=lambda candidate: candidate.status == "ok",
        failure_mode=lambda candidate: candidate.failure_mode,
    )

    search_space = _estimate_search_space(domain_sizes)
    use_genetic = True

    if use_genetic:
        ga = optimization.genetic_algorithm
        raw_outcome = run_genetic_search(
            domain_sizes=domain_sizes,
            population_size=ga.population_size,
            generations=ga.generations,
            crossover_rate=ga.crossover_rate,
            mutation_rate=ga.mutation_rate,
            elite_count=ga.elite_count,
            hooks=hooks,
            seed=42,
            fitness_class_name=DEAP_SPAN_FITNESS_CLASS,
            individual_class_name=DEAP_SPAN_INDIVIDUAL_CLASS,
        )
        method = f"{method_prefix}_genetic"
    else:
        raw_outcome = run_exhaustive_search(domain_sizes=domain_sizes, hooks=hooks)
        method = f"{method_prefix}_exhaustive"

    selected = raw_outcome.selected

    feasible_unique: dict[tuple[object, ...], SpanCandidate] = {}
    for candidate in evaluation_cache.values():
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
                evaluated_candidates=raw_outcome.evaluated_candidates,
                feasible_candidates=raw_outcome.feasible_candidates,
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
                    evaluated_candidates=raw_outcome.evaluated_candidates,
                    feasible_candidates=raw_outcome.feasible_candidates,
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
        evaluated_candidates=raw_outcome.evaluated_candidates,
        feasible_candidates=raw_outcome.feasible_candidates,
        failure_counts=raw_outcome.failure_counts,
    )
