from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .design import BAR_AREAS_MM2, RegionDesignResult


@dataclass(frozen=True)
class RegionChecks:
    torsion: bool
    shear: bool
    longitudinal: bool
    detailing: bool


@dataclass(frozen=True)
class CanonicalRegionResult:
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
    controlling_limit: str
    av1: float
    av2: float
    av_total: float
    at: float
    at_over_s: float
    av_over_s: float
    long_bar: str
    long_count: int
    long_provided_mm2: float
    base_long_bar: str | None
    base_long_count: int | None
    extra_long_bar: str | None
    extra_long_count: int | None
    longitudinal_mode: str | None
    longitudinal_arrangement_label: str | None
    checks: RegionChecks
    failure_mode: str
    status: str
    message: str
    method: str
    objective: float
    evaluated_candidates: int
    feasible_candidates: int
    transverse_weight_kg_per_m: float
    longitudinal_weight_kg_per_m: float
    total_weight_kg_per_m: float
    stirrup_unit_weight_kg: float
    torsion_governing_source: str | None = None
    torsion_governing_station: float | None = None
    combined_governing_source: str | None = None
    combined_governing_station: float | None = None
    longitudinal_governing_source: str | None = None
    longitudinal_governing_station: float | None = None
    scenario_count: int = 0


def _longitudinal_provided_mm2(result: RegionDesignResult) -> float:
    if result.long_provided_mm2_override is not None:
        return float(result.long_provided_mm2_override)
    return BAR_AREAS_MM2.get(result.long_bar, 0.0) * result.long_count


def _checks(result: RegionDesignResult, long_provided_mm2: float) -> RegionChecks:
    return RegionChecks(
        torsion=(
            result.torsion_check_override
            if result.torsion_check_override is not None
            else result.at_over_s >= result.t_req
        ),
        shear=(
            result.combined_check_override
            if result.combined_check_override is not None
            else result.av_over_s >= result.v_req
        ),
        longitudinal=(
            result.longitudinal_check_override
            if result.longitudinal_check_override is not None
            else long_provided_mm2 >= result.l_req
        ),
        detailing=result.failure_mode != "region_detail_fail",
    )


def to_canonical_region_result(result: RegionDesignResult) -> CanonicalRegionResult:
    long_provided_mm2 = _longitudinal_provided_mm2(result)
    checks = _checks(result, long_provided_mm2)
    total_weight = result.transverse_weight_kg_per_m + result.longitudinal_weight_kg_per_m
    return CanonicalRegionResult(
        beam_id=result.beam_id,
        span_id=result.span_id,
        region_id=result.region_id,
        region_type=result.region_type,
        source_control=result.source_control,
        governing_station=result.governing_station,
        v_req=result.v_req,
        t_req=result.t_req,
        l_req=result.l_req,
        e_bar=result.e_bar,
        g_bar=result.g_bar,
        g_count=result.g_count,
        spacing_mm=result.spacing_mm,
        controlling_limit=result.controlling_limit,
        av1=result.av1,
        av2=result.av2,
        av_total=result.av_total,
        at=result.at,
        at_over_s=result.at_over_s,
        av_over_s=result.av_over_s,
        long_bar=result.long_bar,
        long_count=result.long_count,
        long_provided_mm2=long_provided_mm2,
        base_long_bar=result.base_long_bar,
        base_long_count=result.base_long_count,
        extra_long_bar=result.extra_long_bar,
        extra_long_count=result.extra_long_count,
        longitudinal_mode=result.longitudinal_mode,
        longitudinal_arrangement_label=result.longitudinal_arrangement_label,
        checks=checks,
        failure_mode=result.failure_mode,
        status=result.status,
        message=result.message,
        method=result.method,
        objective=result.objective,
        evaluated_candidates=result.evaluated_candidates,
        feasible_candidates=result.feasible_candidates,
        transverse_weight_kg_per_m=result.transverse_weight_kg_per_m,
        longitudinal_weight_kg_per_m=result.longitudinal_weight_kg_per_m,
        total_weight_kg_per_m=total_weight,
        stirrup_unit_weight_kg=result.stirrup_unit_weight_kg,
        torsion_governing_source=result.torsion_governing_source,
        torsion_governing_station=result.torsion_governing_station,
        combined_governing_source=result.combined_governing_source,
        combined_governing_station=result.combined_governing_station,
        longitudinal_governing_source=result.longitudinal_governing_source,
        longitudinal_governing_station=result.longitudinal_governing_station,
        scenario_count=result.scenario_count,
    )


def to_canonical_region_results(results: Iterable[RegionDesignResult]) -> list[CanonicalRegionResult]:
    return [to_canonical_region_result(result) for result in results]


