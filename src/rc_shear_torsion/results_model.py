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


def _longitudinal_provided_mm2(result: RegionDesignResult) -> float:
    return BAR_AREAS_MM2.get(result.long_bar, 0.0) * result.long_count


def _checks(result: RegionDesignResult, long_provided_mm2: float) -> RegionChecks:
    return RegionChecks(
        torsion=result.at_over_s >= result.t_req,
        shear=result.av_over_s >= result.v_req,
        longitudinal=long_provided_mm2 >= result.l_req,
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
    )


def to_canonical_region_results(results: Iterable[RegionDesignResult]) -> list[CanonicalRegionResult]:
    return [to_canonical_region_result(result) for result in results]
