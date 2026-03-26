from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Literal

from .io import EtabsFrameData, EtabsStationRow
from .models import OptimizationConfig, RegionConfig, SpanConfig, VariablesConfig
from .optimization import SearchHooks, run_exhaustive_search, run_genetic_search

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
}

BAR_DIAMETERS_MM: dict[str, float] = {
    "#2": 6.4,
    "#3": 9.5,
    "#4": 12.7,
    "#5": 15.9,
    "#6": 19.1,
    "#7": 22.2,
    "#8": 25.4,
    "#9": 28.7,
    "#10": 32.3,
    "#11": 35.8,
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


@dataclass(frozen=True)
class StationDemand:
    station: float
    x_rel: float
    region_id: str
    v_req: float
    t_req: float
    l_req: float
    source_v: Literal["seismic", "gravity", "mixed"]
    source_t: Literal["seismic", "gravity", "mixed"]
    source_l: Literal["seismic", "gravity", "mixed"]
    seismic_row: EtabsStationRow
    gravity_row: EtabsStationRow


@dataclass(frozen=True)
class RegionDemand:
    beam_id: str
    span_id: str
    region_id: str
    region_type: Literal["C", "NC"]
    beam_detailing: Literal["DES", "DMO"]
    d_mm: float | None
    db_bar: str | None
    min_branches: int | None
    width_mm: float | None
    height_mm: float | None
    cover_side_mm: float | None
    cover_top_mm: float | None
    cover_bottom_mm: float | None
    source_control: Literal["seismic", "gravity", "mixed"]
    governing_station: float | None
    v_req: float
    t_req: float
    l_req: float
    station_count: int
    is_deep_beam: bool = False
    fc_mpa: float | None = None
    fy_mpa: float | None = None
    region_length_mm: float = 0.0


@dataclass(frozen=True)
class Candidate:
    e_bar: str
    g_bar: str
    g_count: int
    spacing_mm: int
    long_bar: str
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
    long_bar: str
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
    is_deep_beam: bool | None = None
    longitudinal_mode: str | None = None
    longitudinal_arrangement_label: str | None = None


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
    beam_detailing: Literal["DES", "DMO"],
    beam_cover_side_mm: float | None,
    beam_cover_top_mm: float | None,
    beam_cover_bottom_mm: float | None,
    beam_fc_mpa: float | None,
    beam_fy_mpa: float | None,
    span: SpanConfig,
    seismic_frame: EtabsFrameData,
    gravity_frame: EtabsFrameData,
) -> tuple[list[RegionDemand], list[str]]:
    if len(seismic_frame.stations) != len(gravity_frame.stations):
        return [], [
            f"Span {span.id}: station count mismatch seismic={len(seismic_frame.stations)} "
            f"gravity={len(gravity_frame.stations)}"
        ]

    seismic_stations = [row.station for row in seismic_frame.stations]
    gravity_stations = [row.station for row in gravity_frame.stations]
    if seismic_stations != gravity_stations:
        return [], [f"Span {span.id}: station sequence mismatch between seismic and gravity"]

    station_min = min(seismic_stations) if seismic_stations else 0.0
    station_max = max(seismic_stations) if seismic_stations else 0.0
    span_length_mm = station_max - station_min
    if span_length_mm <= 0.0:
        return [], [f"Span {span.id}: invalid station length={span_length_mm}; cannot compute relative position"]

    region_stations: dict[str, list[StationDemand]] = {region.id: [] for region in span.regions}
    errors: list[str] = []

    for seismic_row, gravity_row in zip(seismic_frame.stations, gravity_frame.stations):
        x_rel = (seismic_row.station - station_min) / span_length_mm
        region = locate_region(span.regions, x_rel)
        if region is None:
            errors.append(
                f"Span {span.id}: station {seismic_row.station} with x_rel={x_rel:.6f} is outside region map"
            )
            continue

        source_v, v_req = envelope_source(seismic_row.v_rebar_req, gravity_row.v_rebar_req)
        source_t, t_req = envelope_source(seismic_row.t_trn_req, gravity_row.t_trn_req)
        source_l, l_req = envelope_source(seismic_row.t_lng_req, gravity_row.t_lng_req)

        region_stations[region.id].append(
            StationDemand(
                station=seismic_row.station,
                x_rel=x_rel,
                region_id=region.id,
                v_req=v_req,
                t_req=t_req,
                l_req=l_req,
                source_v=source_v,
                source_t=source_t,
                source_l=source_l,
                seismic_row=seismic_row,
                gravity_row=gravity_row,
            )
        )

    if errors:
        return [], errors

    demands: list[RegionDemand] = []
    for region in span.regions:
        stations = region_stations.get(region.id, [])
        if not stations:
            errors.append(f"Span {span.id} region {region.id}: no stations were assigned")
            continue

        v_req = max(station.v_req for station in stations)
        t_req = max(station.t_req for station in stations)
        l_req = max(station.l_req for station in stations)
        governing = max(stations, key=lambda station: station.v_req + 2.0 * station.t_req)
        source_control = region_source_control(stations)
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
                source_control=source_control,
                governing_station=governing.station,
                v_req=v_req,
                t_req=t_req,
                l_req=l_req,
                station_count=len(stations),
                is_deep_beam=span.is_deep_beam,
                fc_mpa=beam_fc_mpa,
                fy_mpa=beam_fy_mpa,
                region_length_mm=(region.to - region.from_) * span_length_mm,
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


def envelope_source(seismic_value: float, gravity_value: float) -> tuple[Literal["seismic", "gravity", "mixed"], float]:
    if seismic_value > gravity_value:
        return "seismic", seismic_value
    if gravity_value > seismic_value:
        return "gravity", gravity_value
    return "mixed", seismic_value


def region_source_control(stations: list[StationDemand]) -> Literal["seismic", "gravity", "mixed"]:
    v_src, _ = envelope_source(
        max(station.seismic_row.v_rebar_req for station in stations),
        max(station.gravity_row.v_rebar_req for station in stations),
    )
    t_src, _ = envelope_source(
        max(station.seismic_row.t_trn_req for station in stations),
        max(station.gravity_row.t_trn_req for station in stations),
    )
    l_src, _ = envelope_source(
        max(station.seismic_row.t_lng_req for station in stations),
        max(station.gravity_row.t_lng_req for station in stations),
    )
    if v_src == t_src == l_src and v_src in {"seismic", "gravity"}:
        return v_src
    return "mixed"


def evaluate_candidate(region: RegionDemand, *, e_bar: str, g_bar: str, g_count: int, spacing_mm: int, long_bar: str, long_count: int) -> Candidate:
    if e_bar not in BAR_AREAS_MM2 or g_bar not in BAR_AREAS_MM2 or long_bar not in BAR_AREAS_MM2:
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

    at = BAR_AREAS_MM2[e_bar]
    ag = BAR_AREAS_MM2[g_bar]
    along = BAR_AREAS_MM2[long_bar] * long_count
    at_over_s = at * 1000.0 / spacing_mm
    f_free = 1.0 - (region.t_req / at_over_s if at_over_s > 0 else math.inf)
    av1 = max(0.0, f_free) * at * 2.0
    av2 = g_count * ag
    av_total = av1 + av2
    av_over_s = av_total * 1000.0 / spacing_mm

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

    if at_over_s < region.t_req:
        return failed_candidate(
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing_mm,
            long_bar=long_bar,
            long_count=long_count,
            failure_mode="torsion_fail",
            message="(At/s)_real < TTrnRebar_req",
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
            deficit=deficit_ratio(region.t_req, at_over_s),
        )
    if f_free < 0.0:
        return failed_candidate(
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing_mm,
            long_bar=long_bar,
            long_count=long_count,
            failure_mode="torsion_fail",
            message="f_free < 0.0",
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
            deficit=abs(f_free),
        )
    if av_over_s < region.v_req:
        return failed_candidate(
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing_mm,
            long_bar=long_bar,
            long_count=long_count,
            failure_mode="shear_fail",
            message="(Av_total/s)_real < VRebar_req",
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
            deficit=deficit_ratio(region.v_req, av_over_s),
        )
    region_rule_ok, region_rule_message, controlling_limit = check_region_rule(
        region,
        spacing_mm=spacing_mm,
        g_count=g_count,
        long_count=long_count,
        e_bar=e_bar,
        g_bar=g_bar,
    )
    if not region_rule_ok:
        return failed_candidate(
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing_mm,
            long_bar=long_bar,
            long_count=long_count,
            failure_mode="region_detail_fail",
            message=region_rule_message,
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
        long_provided=along,
        f_free=f_free,
        failure_mode="ok",
        status="ok",
        message="Candidate satisfies torsion, shear, and detailing checks",
        objective=objective,
        score=objective,
        transverse_weight_kg_per_m=transverse_weight_kg_per_m,
        longitudinal_weight_kg_per_m=0.0,
        stirrup_unit_weight_kg=stirrup_unit_weight_kg,
        controlling_limit=controlling_limit,
    )


def failed_candidate(
    *,
    e_bar: str,
    g_bar: str,
    g_count: int,
    spacing_mm: int,
    long_bar: str,
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
) -> Candidate:
    penalty = 1.0e6 * (1.0 + max(deficit, 0.0))
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
    )


def check_region_rule(
    region: RegionDemand,
    *,
    spacing_mm: int,
    g_count: int,
    long_count: int,
    e_bar: str,
    g_bar: str,
) -> tuple[bool, str, str]:
    if region.beam_detailing not in {"DMO", "DES"}:
        return True, "Detailing rule check: not applicable", "N/A"

    if region.beam_detailing == "DES":
        if region.region_type != "C":
            return True, "DES detailing rule check: not applicable", "N/A"
        if region.db_bar not in BAR_DIAMETERS_MM:
            return False, f"Unsupported db_bar for detailing checks: {region.db_bar}", ""
        if e_bar not in BAR_DIAMETERS_MM:
            return False, f"Unsupported stirrup bar for detailing checks: {e_bar}", ""
        if g_bar not in BAR_DIAMETERS_MM:
            return False, f"Unsupported branch bar for detailing checks: {g_bar}", ""
        if region.d_mm is None:
            return False, "DES region C requires d_mm and db_bar in case.json", ""

        db_mm = BAR_DIAMETERS_MM[region.db_bar]
        branch_diameter = BAR_DIAMETERS_MM[g_bar] if g_count > 0 else math.inf
        dest = min(BAR_DIAMETERS_MM[e_bar], branch_diameter)
        limits: list[tuple[str, float]] = [
            ("d/4", region.d_mm / 4.0),
            ("6db", 6.0 * db_mm),
            ("150", 150.0),
            ("16db", 16.0 * db_mm),
            ("48dest", 48.0 * dest),
        ]
        if (
            region.width_mm is None
            or region.height_mm is None
            or region.cover_side_mm is None
            or region.cover_top_mm is None
            or region.cover_bottom_mm is None
        ):
            return False, "DES region C requires width_mm, height_mm, and beam covers for Ph/8 limit", ""
        stirrup_width_mm = region.width_mm - 2.0 * region.cover_side_mm
        stirrup_height_mm = region.height_mm - (region.cover_top_mm + region.cover_bottom_mm)
        if stirrup_width_mm <= 0.0 or stirrup_height_mm <= 0.0:
            return False, "DES region C Ph/8 limit invalid: non-positive closed stirrup dimensions", ""
        ph_mm = 2.0 * (stirrup_width_mm + stirrup_height_mm)
        limits.append(("Ph/8", ph_mm / 8.0))

        controlling_name, max_spacing = min(limits, key=lambda item: item[1])
        if float(spacing_mm) > max_spacing:
            formatted_limits = ", ".join(f"{name}={value:.1f}" for name, value in limits)
            return (
                False,
                "DES region C spacing limit failed: "
                f"s={spacing_mm} > min({formatted_limits}) = {max_spacing:.1f} mm",
                controlling_name,
            )
        return True, "DES region C detailing checks satisfied", controlling_name

    if region.db_bar not in BAR_DIAMETERS_MM:
        return False, f"Unsupported db_bar for detailing checks: {region.db_bar}", ""
    if e_bar not in BAR_DIAMETERS_MM:
        return False, f"Unsupported stirrup bar for detailing checks: {e_bar}", ""
    if g_bar not in BAR_DIAMETERS_MM:
        return False, f"Unsupported branch bar for detailing checks: {g_bar}", ""

    if region.region_type == "C":
        if region.d_mm is None or region.min_branches is None:
            return False, "DMO region C requires d_mm, db_bar, and min_branches in case.json", ""
        if region.t_req > 0.0 and region.min_branches < 2:
            return (
                False,
                "DMO region C with TTrnRebar>0 requires min_branches >= 2 "
                "(closed stirrup equivalent)",
                "",
            )

        db_mm = BAR_DIAMETERS_MM[region.db_bar]
        d_limit = region.d_mm / 4.0
        db8_limit = 8.0 * db_mm
        mm150_limit = 150.0
        db16_limit = 16.0 * db_mm
        branch_diameter = BAR_DIAMETERS_MM[g_bar] if g_count > 0 else math.inf
        dest = min(BAR_DIAMETERS_MM[e_bar], branch_diameter)
        dest48_limit = 48.0 * dest
        dest24_limit = 24.0 * dest

        limits: list[tuple[str, float]] = [
            ("d/4", d_limit),
            ("8db", db8_limit),
            ("150", mm150_limit),
            ("16db", db16_limit),
            ("48dest", dest48_limit),
            ("24dest", dest24_limit),
        ]
        controlling_name, max_spacing = min(limits, key=lambda item: item[1])
        if float(spacing_mm) > max_spacing:
            return (
                False,
                "DMO region C spacing limit failed: "
                f"s={spacing_mm} > min(d/4={d_limit:.1f}, 8db={db8_limit:.1f}, 150={mm150_limit:.1f}, "
                f"16db={db16_limit:.1f}, 48dest={dest48_limit:.1f}, 24dest={dest24_limit:.1f}) = {max_spacing:.1f} mm",
                controlling_name,
            )

        _ = long_count
        provided_branches = 2 + g_count
        if provided_branches < region.min_branches:
            return (
                False,
                "DMO region C minimum branches failed: "
                f"provided={provided_branches} < required={region.min_branches}",
                controlling_name,
            )

        return True, "DMO region C detailing checks satisfied", controlling_name

    if region.region_type != "NC":
        return True, "Detailing rule check: unsupported region type skipped", "N/A"

    if region.d_mm is None:
        return False, "DMO region NC requires d_mm in case.json", ""
    if region.t_req > 0.0 and region.min_branches is not None and region.min_branches < 2:
        return (
            False,
            "DMO region NC with TTrnRebar>0 requires min_branches >= 2 "
            "(closed stirrup equivalent)",
            "",
        )
    if region.fc_mpa is None or region.fy_mpa is None:
        return False, "DMO region NC requires beam fc_mpa and fy_mpa", ""
    if region.width_mm is None:
        return False, "DMO region NC requires width_mm to evaluate spacing limits", ""

    db_mm = BAR_DIAMETERS_MM[region.db_bar]
    branch_diameter = BAR_DIAMETERS_MM[g_bar] if g_count > 0 else math.inf
    dest = min(BAR_DIAMETERS_MM[e_bar], branch_diameter)

    vs_req_n = (region.v_req / 1000.0) * region.fy_mpa * region.d_mm
    v33_n = 0.33 * region.fc_mpa * region.width_mm * region.d_mm

    limits: list[tuple[str, float]] = [
        ("16db", 16.0 * db_mm),
        ("48dest", 48.0 * dest),
    ]
    if vs_req_n < v33_n:
        limits.append(("d/2", region.d_mm / 2.0))
    else:
        limits.append(("d/4", region.d_mm / 4.0))

    if region.t_req > 0.0:
        if (
            region.height_mm is None
            or region.cover_side_mm is None
            or region.cover_top_mm is None
            or region.cover_bottom_mm is None
        ):
            return (
                False,
                "DMO region NC with TTrnRebar>0 requires height_mm and beam covers for Ph/8 limit",
                "",
            )
        stirrup_width_mm = region.width_mm - 2.0 * region.cover_side_mm
        stirrup_height_mm = region.height_mm - (region.cover_top_mm + region.cover_bottom_mm)
        if stirrup_width_mm <= 0.0 or stirrup_height_mm <= 0.0:
            return False, "DMO region NC Ph/8 limit invalid: non-positive closed stirrup dimensions", ""
        ph_mm = 2.0 * (stirrup_width_mm + stirrup_height_mm)
        limits.append(("Ph/8", ph_mm / 8.0))

    controlling_name, max_spacing = min(limits, key=lambda item: item[1])
    if float(spacing_mm) > max_spacing:
        formatted_limits = ", ".join(f"{name}={value:.1f}" for name, value in limits)
        return (
            False,
            "DMO region NC spacing limit failed: "
            f"s={spacing_mm} > min({formatted_limits}) = {max_spacing:.1f} mm "
            f"[Vrebar*fy*d={vs_req_n:.1f} N, 0.33f'c*bw*d={v33_n:.1f} N]",
            controlling_name,
        )

    return True, "DMO region NC detailing checks satisfied", controlling_name


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


def longitudinal_mass_kg_per_m(long_provided_mm2: float) -> float:
    return long_provided_mm2 * 1000.0 * STEEL_DENSITY_KG_PER_MM3


def requires_longitudinal_design(region: RegionDemand) -> bool:
    return bool(region.is_deep_beam or region.l_req > 0.0)


def select_longitudinal_independent(
    region: RegionDemand,
    variables: VariablesConfig,
) -> tuple[str, int, float, bool]:
    if not requires_longitudinal_design(region):
        return "", 0, 0.0, True

    options: list[tuple[float, str, int]] = []
    for long_bar in variables.longitudinal_bars:
        for long_count in variables.longitudinal_bar_counts:
            provided = BAR_AREAS_MM2[long_bar] * long_count
            options.append((provided, long_bar, long_count))
    options.sort(key=lambda item: item[0])

    for provided, long_bar, long_count in options:
        if provided >= region.l_req:
            return long_bar, long_count, provided, True

    provided, long_bar, long_count = options[-1]
    return long_bar, long_count, provided, False


def _attach_candidate_longitudinal_mass(
    candidate: Candidate,
    region: RegionDemand,
) -> Candidate:
    longitudinal_mass_per_m = longitudinal_mass_kg_per_m(candidate.long_provided)
    region_length_m = max(0.0, region.region_length_mm / 1000.0)
    longitudinal_mass_region_kg = longitudinal_mass_per_m * region_length_m
    transverse_mass_region_kg = candidate.stirrup_unit_weight_kg * stirrup_count_in_region(
        region.region_length_mm,
        candidate.spacing_mm,
    )
    if transverse_mass_region_kg <= 0.0:
        transverse_mass_region_kg = candidate.objective

    objective = transverse_mass_region_kg + longitudinal_mass_region_kg
    score = candidate.score + longitudinal_mass_region_kg
    if candidate.status == "ok":
        score = objective

    return Candidate(
        e_bar=candidate.e_bar,
        g_bar=candidate.g_bar,
        g_count=candidate.g_count,
        spacing_mm=candidate.spacing_mm,
        long_bar=candidate.long_bar,
        long_count=candidate.long_count,
        at=candidate.at,
        at_over_s=candidate.at_over_s,
        av1=candidate.av1,
        av2=candidate.av2,
        av_total=candidate.av_total,
        av_over_s=candidate.av_over_s,
        long_provided=candidate.long_provided,
        f_free=candidate.f_free,
        failure_mode=candidate.failure_mode,
        status=candidate.status,
        message=candidate.message,
        objective=objective,
        score=score,
        transverse_weight_kg_per_m=candidate.transverse_weight_kg_per_m,
        longitudinal_weight_kg_per_m=longitudinal_mass_per_m,
        stirrup_unit_weight_kg=candidate.stirrup_unit_weight_kg,
        controlling_limit=candidate.controlling_limit,
    )


def attach_independent_longitudinal(
    candidate: Candidate,
    region: RegionDemand,
    variables: VariablesConfig,
) -> Candidate:
    needs_longitudinal = requires_longitudinal_design(region)
    long_bar, long_count, long_provided, long_ok = select_longitudinal_independent(region, variables)
    if not needs_longitudinal:
        long_bar = ""
        long_count = 0
        long_provided = 0.0
        message = candidate.message
    elif long_ok:
        message = candidate.message
    else:
        message = (
            f"{candidate.message} | longitudinal independent warning: "
            f"max domain provided={long_provided:.2f} < required={region.l_req:.2f}"
        )

    candidate_with_long = Candidate(
        e_bar=candidate.e_bar,
        g_bar=candidate.g_bar,
        g_count=candidate.g_count,
        spacing_mm=candidate.spacing_mm,
        long_bar=long_bar,
        long_count=long_count,
        at=candidate.at,
        at_over_s=candidate.at_over_s,
        av1=candidate.av1,
        av2=candidate.av2,
        av_total=candidate.av_total,
        av_over_s=candidate.av_over_s,
        long_provided=long_provided,
        f_free=candidate.f_free,
        failure_mode=candidate.failure_mode,
        status=candidate.status,
        message=message,
        objective=candidate.objective,
        score=candidate.score,
        transverse_weight_kg_per_m=candidate.transverse_weight_kg_per_m,
        longitudinal_weight_kg_per_m=(0.0 if not needs_longitudinal else candidate.longitudinal_weight_kg_per_m),
        stirrup_unit_weight_kg=candidate.stirrup_unit_weight_kg,
        controlling_limit=candidate.controlling_limit,
    )
    return _attach_candidate_longitudinal_mass(candidate_with_long, region)

def optimize_region(region: RegionDemand, optimization: OptimizationConfig) -> OptimizationOutcome:
    if optimization.enabled:
        return optimize_region_ga(region, optimization)
    return optimize_region_exhaustive(region, optimization.variables)


def optimize_region_exhaustive(region: RegionDemand, variables: VariablesConfig) -> OptimizationOutcome:
    allowed_g_counts, min_required_g = g_count_domain_for_region(region, variables.G_counts)
    if not allowed_g_counts:
        selected = failed_candidate(
            e_bar=variables.E_bars[0],
            g_bar=variables.G_bars[0],
            g_count=0,
            spacing_mm=variables.stirrup_spacing_mm[0],
            long_bar=variables.longitudinal_bars[0],
            long_count=variables.longitudinal_bar_counts[0],
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

    domain: list[list[str | int]] = [
        variables.E_bars,
        variables.G_bars,
        allowed_g_counts,
        variables.stirrup_spacing_mm,
    ]
    default_long_bar = variables.longitudinal_bars[0]
    default_long_count = variables.longitudinal_bar_counts[0]

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
        )
        return attach_independent_longitudinal(candidate, region, variables)

    hooks = SearchHooks[Candidate](
        evaluate=evaluate_individual,
        score=lambda candidate: candidate.score,
        objective=lambda candidate: candidate.objective,
        is_feasible=lambda candidate: candidate.status == "ok",
        failure_mode=lambda candidate: candidate.failure_mode,
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


def optimize_region_ga(region: RegionDemand, optimization: OptimizationConfig) -> OptimizationOutcome:
    variables = optimization.variables
    ga = optimization.genetic_algorithm
    allowed_g_counts, min_required_g = g_count_domain_for_region(region, variables.G_counts)
    if not allowed_g_counts:
        selected = failed_candidate(
            e_bar=variables.E_bars[0],
            g_bar=variables.G_bars[0],
            g_count=0,
            spacing_mm=variables.stirrup_spacing_mm[0],
            long_bar=variables.longitudinal_bars[0],
            long_count=variables.longitudinal_bar_counts[0],
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

    domain: list[list[str | int]] = [
        variables.E_bars,
        variables.G_bars,
        allowed_g_counts,
        variables.stirrup_spacing_mm,
    ]
    domain_sizes = [len(values) for values in domain]
    default_long_bar = variables.longitudinal_bars[0]
    default_long_count = variables.longitudinal_bar_counts[0]

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
        )
        resolved = attach_independent_longitudinal(candidate, region, variables)
        evaluation_cache[key] = resolved
        return resolved

    hooks = SearchHooks[Candidate](
        evaluate=evaluate_individual,
        score=lambda candidate: candidate.score,
        objective=lambda candidate: candidate.objective,
        is_feasible=lambda candidate: candidate.status == "ok",
        failure_mode=lambda candidate: candidate.failure_mode,
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
        long_bar=candidate.long_bar,
        long_count=candidate.long_count,
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
    )


def top_region_alternatives(
    region: RegionDemand,
    variables: VariablesConfig,
    *,
    top_n: int = 10,
) -> list[RegionDesignResult]:
    allowed_g_counts, _ = g_count_domain_for_region(region, variables.G_counts)
    if not allowed_g_counts:
        return []

    top_n = max(1, int(top_n))
    needs_longitudinal = requires_longitudinal_design(region)
    long_bar_domain = list(variables.longitudinal_bars)
    long_count_domain = list(variables.longitudinal_bar_counts)
    if not needs_longitudinal:
        long_bar_domain = [variables.longitudinal_bars[0]]
        long_count_domain = [0]

    evaluated: list[Candidate] = []
    for e_bar, g_bar, g_count, spacing, long_bar, long_count in itertools.product(
        variables.E_bars,
        variables.G_bars,
        allowed_g_counts,
        variables.stirrup_spacing_mm,
        long_bar_domain,
        long_count_domain,
    ):
        candidate = evaluate_candidate(
            region,
            e_bar=e_bar,
            g_bar=g_bar,
            g_count=g_count,
            spacing_mm=spacing,
            long_bar=long_bar,
            long_count=long_count,
        )
        if needs_longitudinal and candidate.status == "ok" and candidate.long_provided < region.l_req:
            candidate = failed_candidate(
                e_bar=candidate.e_bar,
                g_bar=candidate.g_bar,
                g_count=candidate.g_count,
                spacing_mm=candidate.spacing_mm,
                long_bar=candidate.long_bar,
                long_count=candidate.long_count,
                failure_mode="longitudinal_fail",
                message="Along_real < Along_req",
                at=candidate.at,
                at_over_s=candidate.at_over_s,
                av1=candidate.av1,
                av2=candidate.av2,
                av_total=candidate.av_total,
                av_over_s=candidate.av_over_s,
                long_provided=candidate.long_provided,
                f_free=candidate.f_free,
                objective=candidate.objective,
                transverse_weight_kg_per_m=candidate.transverse_weight_kg_per_m,
                stirrup_unit_weight_kg=candidate.stirrup_unit_weight_kg,
                controlling_limit=candidate.controlling_limit,
                deficit=deficit_ratio(region.l_req, candidate.long_provided),
            )
        if not needs_longitudinal:
            candidate = Candidate(
                e_bar=candidate.e_bar,
                g_bar=candidate.g_bar,
                g_count=candidate.g_count,
                spacing_mm=candidate.spacing_mm,
                long_bar="",
                long_count=0,
                at=candidate.at,
                at_over_s=candidate.at_over_s,
                av1=candidate.av1,
                av2=candidate.av2,
                av_total=candidate.av_total,
                av_over_s=candidate.av_over_s,
                long_provided=0.0,
                f_free=candidate.f_free,
                failure_mode=candidate.failure_mode,
                status=candidate.status,
                message=candidate.message,
                objective=candidate.objective,
                score=candidate.score,
                transverse_weight_kg_per_m=candidate.transverse_weight_kg_per_m,
                longitudinal_weight_kg_per_m=0.0,
                stirrup_unit_weight_kg=candidate.stirrup_unit_weight_kg,
                controlling_limit=candidate.controlling_limit,
            )
        evaluated.append(_attach_candidate_longitudinal_mass(candidate, region))

    feasible = sorted(
        (candidate for candidate in evaluated if candidate.status == "ok"),
        key=lambda candidate: (candidate.objective, candidate.score),
    )
    feasible_count = len(feasible)

    # Keep alternatives deterministic and aligned with user expectation:
    # "top N" means top feasible candidates sorted by objective/score.
    selected: list[Candidate] = list(feasible[:top_n])
    if len(selected) < top_n:
        failed = sorted(
            (candidate for candidate in evaluated if candidate.status != "ok"),
            key=lambda candidate: candidate.score,
        )
        for candidate in failed:
            selected.append(candidate)
            if len(selected) >= top_n:
                break

    return [
        candidate_to_region_result(
            region,
            candidate,
            method="top_alternativa",
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
        long_bar="",
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





