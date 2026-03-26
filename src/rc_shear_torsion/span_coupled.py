from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from .design import (
    BAR_AREAS_MM2,
    Candidate,
    DEAP_FITNESS_CLASS,
    DEAP_INDIVIDUAL_CLASS,
    RegionDemand,
    RegionDesignResult,
    evaluate_candidate,
    g_count_domain_for_region,
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
class SpanRegionGeneDomain:
    allowed_g_counts: list[int]


@dataclass(frozen=True)
class SpanRegionState:
    demand: RegionDemand
    transverse: Candidate
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
    alternatives_by_region: dict[str, list[RegionDesignResult]]
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
    spacing_mm: int,
    av_total: float,
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

        if layers > 1:
            if available_range <= 0.0:
                return False, "2*d - h must be > 0 to place multiple longitudinal layers", provided, layers, None
            s2_mm = available_range / float(layers - 1)
            if s2_mm > 300.0:
                return False, f"Longitudinal layer spacing s2={s2_mm:.1f} mm exceeds 300 mm", provided, layers, s2_mm

    if demand.is_deep_beam:
        if demand.d_mm is None or demand.width_mm is None:
            return False, "Deep-beam checks require d_mm and width_mm", provided, layers, s2_mm

        s1_limit = min(demand.d_mm / 5.0, 300.0)
        if float(spacing_mm) > s1_limit:
            return (
                False,
                f"Deep beam requires s1 <= min(d/5,300)={s1_limit:.1f} mm (got {spacing_mm})",
                provided,
                layers,
                s2_mm,
            )

        min_av_total = 0.0025 * demand.width_mm * float(spacing_mm)
        if av_total < min_av_total:
            return (
                False,
                f"Deep beam requires Av_total >= 0.0025*b*s1 ({min_av_total:.2f} mm2)",
                provided,
                layers,
                s2_mm,
            )

        if layers > 1:
            assert s2_mm is not None
            s2_limit = min(demand.d_mm / 5.0, 300.0)
            if s2_mm > s2_limit:
                return (
                    False,
                    f"Deep beam requires s2 <= min(d/5,300)={s2_limit:.1f} mm (got {s2_mm:.1f})",
                    provided,
                    layers,
                    s2_mm,
                )

            a_layer = provided / float(layers)
            min_a_layer = 0.0025 * demand.width_mm * s2_mm
            if a_layer < min_a_layer:
                return (
                    False,
                    f"Deep beam requires A_layer >= 0.0025*b*s2 ({min_a_layer:.2f} mm2)",
                    provided,
                    layers,
                    s2_mm,
                )

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
    method: str,
    evaluated_candidates: int,
    feasible_candidates: int,
) -> RegionDesignResult:
    demand = state.demand
    transverse = state.transverse
    region_length_m = max(0.0, demand.region_length_mm / 1000.0)
    transverse_region_weight_kg = transverse.stirrup_unit_weight_kg * stirrup_count_in_region(
        demand.region_length_mm,
        transverse.spacing_mm,
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
        e_bar=transverse.e_bar,
        g_bar=transverse.g_bar,
        g_count=transverse.g_count,
        spacing_mm=transverse.spacing_mm,
        av1=transverse.av1,
        av2=transverse.av2,
        av_total=transverse.av_total,
        at=transverse.at,
        at_over_s=transverse.at_over_s,
        av_over_s=transverse.av_over_s,
        long_bar=effective_long_bar,
        long_count=effective_long_count,
        controlling_limit=transverse.controlling_limit,
        failure_mode=transverse.failure_mode,
        status=transverse.status,
        message=transverse.message,
        objective=transverse_region_weight_kg + long_region_weight_kg,
        method=method,
        evaluated_candidates=evaluated_candidates,
        feasible_candidates=feasible_candidates,
        transverse_weight_kg_per_m=transverse.transverse_weight_kg_per_m,
        longitudinal_weight_kg_per_m=long_weight_kg_per_m,
        stirrup_unit_weight_kg=transverse.stirrup_unit_weight_kg,
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
    method: str,
    message: str,
    failure_mode: str = "longitudinal_fail",
) -> RegionDesignResult:
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
        e_bar="",
        g_bar="",
        g_count=0,
        spacing_mm=0,
        av1=0.0,
        av2=0.0,
        av_total=0.0,
        at=0.0,
        at_over_s=0.0,
        av_over_s=0.0,
        long_bar="",
        long_count=0,
        controlling_limit="",
        failure_mode=failure_mode,
        status="fail",
        message=message,
        objective=1.0e9,
        method=method,
        evaluated_candidates=0,
        feasible_candidates=0,
        transverse_weight_kg_per_m=0.0,
        longitudinal_weight_kg_per_m=0.0,
        stirrup_unit_weight_kg=0.0,
        is_deep_beam=demand.is_deep_beam,
        longitudinal_mode="span_coupled",
    )


def optimize_span_coupled(
    demands: list[RegionDemand],
    optimization: OptimizationConfig,
    *,
    span_length_mm: float,
    top_n: int = 10,
) -> SpanOptimizationOutcome:
    method_prefix = "span_coupled"
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
    span_needs_longitudinal = any(requires_longitudinal_design(demand) for demand in demands)
    if span_needs_longitudinal:
        base_long_bars = list(variables.longitudinal_bars)
        base_long_counts = list(variables.longitudinal_bar_counts)
        extra_long_bars = list(variables.longitudinal_bars)
        extra_long_counts = sorted({0, *variables.longitudinal_bar_counts})
    else:
        base_long_bars = [variables.longitudinal_bars[0]]
        base_long_counts = [0]
        extra_long_bars = [variables.longitudinal_bars[0]]
        extra_long_counts = [0]

    if not base_long_bars or not base_long_counts:
        message = "longitudinal_bars and longitudinal_bar_counts cannot be empty"
        failed_results = [_failed_region_result(demand, method=f"{method_prefix}_none", message=message) for demand in demands]
        return SpanOptimizationOutcome(
            results=failed_results,
            alternatives_by_region={demand.region_id: [row] for demand, row in zip(demands, failed_results)},
            method=f"{method_prefix}_none",
            evaluated_candidates=0,
            feasible_candidates=0,
            failure_counts={"input_fail": 1},
        )

    region_domains: list[SpanRegionGeneDomain] = []
    for demand in demands:
        allowed_g_counts, min_required_g = g_count_domain_for_region(demand, variables.G_counts)
        if not allowed_g_counts:
            message = (
                f"No G_counts satisfy min_branches={demand.min_branches}; "
                f"required G_count >= {min_required_g}"
            )
            failed_results = [_failed_region_result(item, method=f"{method_prefix}_none", message=message) for item in demands]
            return SpanOptimizationOutcome(
                results=failed_results,
                alternatives_by_region={item.region_id: [row] for item, row in zip(demands, failed_results)},
                method=f"{method_prefix}_none",
                evaluated_candidates=0,
                feasible_candidates=0,
                failure_counts={"input_fail": 1},
            )
        region_domains.append(SpanRegionGeneDomain(allowed_g_counts=list(allowed_g_counts)))

    domain_sizes: list[int] = [len(base_long_bars), len(base_long_counts)]
    for region_domain in region_domains:
        domain_sizes.extend(
            [
                len(variables.E_bars),
                len(variables.G_bars),
                len(region_domain.allowed_g_counts),
                len(variables.stirrup_spacing_mm),
                len(extra_long_bars),
                len(extra_long_counts),
            ]
        )

    evaluation_cache: dict[tuple[int, ...], SpanCandidate] = {}

    def decode(individual: list[int]) -> tuple[str, int, list[tuple[str, str, int, int, str, int]]]:
        offset = 0
        base_long_bar = str(base_long_bars[individual[offset]])
        offset += 1
        base_long_count = int(base_long_counts[individual[offset]])
        offset += 1

        decoded_regions: list[tuple[str, str, int, int, str, int]] = []
        for region_domain in region_domains:
            e_bar = str(variables.E_bars[individual[offset]])
            offset += 1
            g_bar = str(variables.G_bars[individual[offset]])
            offset += 1
            g_count = int(region_domain.allowed_g_counts[individual[offset]])
            offset += 1
            spacing_mm = int(variables.stirrup_spacing_mm[individual[offset]])
            offset += 1
            extra_long_bar = str(extra_long_bars[individual[offset]])
            offset += 1
            extra_long_count = int(extra_long_counts[individual[offset]])
            offset += 1
            decoded_regions.append((e_bar, g_bar, g_count, spacing_mm, extra_long_bar, extra_long_count))
        return base_long_bar, base_long_count, decoded_regions

    def evaluate_individual(individual: list[int]) -> SpanCandidate:
        key = tuple(int(gene) for gene in individual)
        cached = evaluation_cache.get(key)
        if cached is not None:
            return cached

        base_long_bar, base_long_count, decoded_regions = decode(individual)
        base_long_area = BAR_AREAS_MM2.get(base_long_bar, 0.0) * base_long_count
        span_length_m = max(0.0, span_length_mm / 1000.0)
        objective = longitudinal_mass_kg_per_m(base_long_area) * span_length_m

        states: list[SpanRegionState] = []
        for demand, decoded in zip(demands, decoded_regions):
            e_bar, g_bar, g_count, spacing_mm, extra_long_bar, extra_long_count = decoded
            transverse = evaluate_candidate(
                demand,
                e_bar=e_bar,
                g_bar=g_bar,
                g_count=g_count,
                spacing_mm=spacing_mm,
                long_bar=base_long_bar,
                long_count=base_long_count,
            )
            if transverse.status != "ok":
                failed = _failed_candidate(
                    base_long_bar=base_long_bar,
                    base_long_count=base_long_count,
                    failure_mode=transverse.failure_mode,
                    message=(
                        f"{demand.span_id}/{demand.region_id}: {transverse.message}"
                    ),
                    objective=objective + 1.0e4,
                )
                evaluation_cache[key] = failed
                return failed

            long_ok, long_message, long_provided, layers, s2_mm = _evaluate_longitudinal_region(
                demand,
                base_long_bar=base_long_bar,
                base_long_count=base_long_count,
                extra_long_bar=extra_long_bar,
                extra_long_count=extra_long_count,
                spacing_mm=spacing_mm,
                av_total=transverse.av_total,
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

            transverse_region_kg = transverse.stirrup_unit_weight_kg * stirrup_count_in_region(
                demand.region_length_mm,
                spacing_mm,
            )
            extra_long_area = BAR_AREAS_MM2[extra_long_bar] * extra_long_count
            region_length_m = max(0.0, demand.region_length_mm / 1000.0)
            extra_long_region_kg = longitudinal_mass_kg_per_m(extra_long_area) * region_length_m
            objective += transverse_region_kg + extra_long_region_kg

            states.append(
                SpanRegionState(
                    demand=demand,
                    transverse=transverse,
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
            message="Span candidate satisfies transverse and longitudinal checks",
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
    use_genetic = optimization.enabled or search_space > LARGE_EXHAUSTIVE_SPACE

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
                    state.demand.region_id,
                    state.transverse.e_bar,
                    state.transverse.g_bar,
                    state.transverse.g_count,
                    state.transverse.spacing_mm,
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
    if selected.status == "ok" and all(selected is not candidate for candidate in feasible_sorted):
        feasible_sorted.insert(0, selected)
    top_candidates = feasible_sorted[: max(1, int(top_n))]

    if selected.status == "ok":
        selected_results = [
            _region_result_from_state(
                state=state,
                span_candidate=selected,
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
                method=method,
                message=selected.message,
                failure_mode=selected.failure_mode,
            )
            for demand in demands
        ]

    alternatives_by_region: dict[str, list[RegionDesignResult]] = {}
    if top_candidates:
        for demand_index, demand in enumerate(demands):
            alternatives_by_region[demand.region_id] = [
                _region_result_from_state(
                    state=candidate.states[demand_index],
                    span_candidate=candidate,
                    method=f"{method_prefix}_top",
                    evaluated_candidates=raw_outcome.evaluated_candidates,
                    feasible_candidates=raw_outcome.feasible_candidates,
                )
                for candidate in top_candidates
            ]
    else:
        for result in selected_results:
            alternatives_by_region[result.region_id] = [result]

    return SpanOptimizationOutcome(
        results=selected_results,
        alternatives_by_region=alternatives_by_region,
        method=method,
        evaluated_candidates=raw_outcome.evaluated_candidates,
        feasible_candidates=raw_outcome.feasible_candidates,
        failure_counts=raw_outcome.failure_counts,
    )
