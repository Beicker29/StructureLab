from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook

from .design import BeamSummary, RegionDesignResult, SpanSummary


DESIGN_COLUMNS = [
    "beam_id",
    "span_id",
    "region_id",
    "region_type",
    "source_control",
    "governing_station",
    "VRebar_req",
    "TTrnRebar_req",
    "TLngRebar_req",
    "E_bar",
    "G_bar",
    "G_count",
    "spacing_mm",
    "controlling_limit",
    "Av1",
    "Av2",
    "Av_total",
    "At",
    "At_over_s",
    "Av_over_s",
    "long_bar",
    "long_count",
    "failure_mode",
    "status",
    "message",
]


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_design_results(path: Path, region_results: Iterable[RegionDesignResult]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "design_results"
    sheet.append(DESIGN_COLUMNS)
    for result in region_results:
        sheet.append(
            [
                result.beam_id,
                result.span_id,
                result.region_id,
                result.region_type,
                result.source_control,
                result.governing_station,
                result.v_req,
                result.t_req,
                result.l_req,
                result.e_bar,
                result.g_bar,
                result.g_count,
                result.spacing_mm,
                result.controlling_limit,
                result.av1,
                result.av2,
                result.av_total,
                result.at,
                result.at_over_s,
                result.av_over_s,
                result.long_bar,
                result.long_count,
                result.failure_mode,
                result.status,
                result.message,
            ]
        )
    workbook.save(path)


def write_summary(path: Path, span_summaries: Iterable[SpanSummary], beam_summaries: Iterable[BeamSummary]) -> None:
    workbook = Workbook()
    span_sheet = workbook.active
    span_sheet.title = "span_summary"
    span_sheet.append(
        ["beam_id", "span_id", "total_regions", "ok_regions", "fail_regions", "status", "message"]
    )
    for summary in span_summaries:
        span_sheet.append(
            [
                summary.beam_id,
                summary.span_id,
                summary.total_regions,
                summary.ok_regions,
                summary.fail_regions,
                summary.status,
                summary.message,
            ]
        )

    beam_sheet = workbook.create_sheet("beam_summary")
    beam_sheet.append(["beam_id", "total_spans", "ok_spans", "fail_spans", "status"])
    for summary in beam_summaries:
        beam_sheet.append(
            [summary.beam_id, summary.total_spans, summary.ok_spans, summary.fail_spans, summary.status]
        )

    workbook.save(path)


def write_optimized_results(path: Path, region_results: Iterable[RegionDesignResult]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "optimized_regions"
    sheet.append(
        [
            "beam_id",
            "span_id",
            "region_id",
            "method",
            "status",
            "failure_mode",
            "objective",
            "source_control",
            "governing_station",
            "E_bar",
            "G_bar",
            "G_count",
            "spacing_mm",
            "controlling_limit",
            "long_bar",
            "long_count",
            "transverse_weight_kg_per_m",
            "longitudinal_weight_kg_per_m",
            "total_weight_kg_per_m",
            "evaluated_candidates",
            "feasible_candidates",
        ]
    )
    for result in region_results:
        sheet.append(
            [
                result.beam_id,
                result.span_id,
                result.region_id,
                result.method,
                result.status,
                result.failure_mode,
                result.objective,
                result.source_control,
                result.governing_station,
                result.e_bar,
                result.g_bar,
                result.g_count,
                result.spacing_mm,
                result.controlling_limit,
                result.long_bar,
                result.long_count,
                result.transverse_weight_kg_per_m,
                result.longitudinal_weight_kg_per_m,
                result.transverse_weight_kg_per_m + result.longitudinal_weight_kg_per_m,
                result.evaluated_candidates,
                result.feasible_candidates,
            ]
        )
    workbook.save(path)


def write_reinforcement_schedule(
    path: Path,
    region_results: Iterable[RegionDesignResult],
    region_lengths_mm: dict[tuple[str, str, str], float] | None = None,
    region_alternatives: dict[tuple[str, str, str], list[RegionDesignResult]] | None = None,
) -> None:
    lengths_mm = region_lengths_mm or {}
    alternatives = region_alternatives or {}
    workbook = Workbook()
    region_sheet = workbook.active
    region_sheet.title = "por_region"
    region_sheet.append(
        [
            "viga_id",
            "vano_id",
            "region_id",
            "opcion",
            "longitud_region_mm",
            "estado",
            "arreglo_transversal",
            "limite_controlante",
            "cantidad_estribos_region",
            "arreglo_longitudinal",
            "peso_unitario_estribo_kg",
            "peso_transversal_region_kg",
            "peso_longitudinal_region_kg",
            "peso_total_region_kg",
        ]
    )

    span_acc: dict[tuple[str, str], dict[str, float | int]] = {}
    ordered_results = sorted(region_results, key=lambda result: (result.beam_id, result.span_id, result.region_id))
    for base_result in ordered_results:
        key_region = (base_result.beam_id, base_result.span_id, base_result.region_id)
        options = alternatives.get(key_region) or [base_result]
        best_option_data: tuple[float, float, float] | None = None

        for option_idx, result in enumerate(options, start=1):
            transverse_arrangement = ""
            cantidad_estribos_region = 0
            if result.e_bar and result.spacing_mm > 0:
                if result.g_bar and result.g_count > 0:
                    transverse_arrangement = f"1E {result.e_bar} + {result.g_count}G {result.g_bar} @ {result.spacing_mm} mm"
                else:
                    transverse_arrangement = f"1E {result.e_bar} @ {result.spacing_mm} mm"

            longitudinal_arrangement = ""
            if result.long_bar and result.long_count > 0:
                longitudinal_arrangement = f"{result.long_count} x {result.long_bar}"

            estado = "cumple" if result.status == "ok" else "falla"
            longitud_region_mm = lengths_mm.get((result.beam_id, result.span_id, result.region_id), 0.0)
            if result.spacing_mm > 0 and longitud_region_mm > 0.0:
                # Estribo: conjunto formado por estribo cerrado exterior + ganchos.
                cantidad_estribos_region = max(1, math.floor(longitud_region_mm / float(result.spacing_mm)) + 1)
            longitud_region_m = max(0.0, longitud_region_mm / 1000.0)
            peso_unitario_estribo_kg = result.stirrup_unit_weight_kg
            peso_transversal_region_kg = peso_unitario_estribo_kg * cantidad_estribos_region
            peso_longitudinal_region_kg = result.longitudinal_weight_kg_per_m * longitud_region_m
            total_weight = peso_transversal_region_kg + peso_longitudinal_region_kg
            region_sheet.append(
                [
                    result.beam_id,
                    result.span_id,
                    result.region_id,
                    option_idx,
                    longitud_region_mm,
                    estado,
                    transverse_arrangement,
                    result.controlling_limit,
                    cantidad_estribos_region,
                    longitudinal_arrangement,
                    peso_unitario_estribo_kg,
                    peso_transversal_region_kg,
                    peso_longitudinal_region_kg,
                    total_weight,
                ]
            )
            if option_idx == 1:
                best_option_data = (
                    peso_transversal_region_kg,
                    peso_longitudinal_region_kg,
                    total_weight,
                )

        key = (base_result.beam_id, base_result.span_id)
        if key not in span_acc:
            span_acc[key] = {
                "total_regions": 0,
                "ok_regions": 0,
                "fail_regions": 0,
                "transverse_weight_sum_kg": 0.0,
                "longitudinal_weight_sum_kg": 0.0,
                "total_weight_sum_kg": 0.0,
            }
        span_row = span_acc[key]
        span_row["total_regions"] = int(span_row["total_regions"]) + 1
        if base_result.status == "ok":
            span_row["ok_regions"] = int(span_row["ok_regions"]) + 1
        else:
            span_row["fail_regions"] = int(span_row["fail_regions"]) + 1
        if best_option_data is not None:
            span_row["transverse_weight_sum_kg"] = float(span_row["transverse_weight_sum_kg"]) + best_option_data[0]
            span_row["longitudinal_weight_sum_kg"] = float(span_row["longitudinal_weight_sum_kg"]) + best_option_data[1]
            span_row["total_weight_sum_kg"] = float(span_row["total_weight_sum_kg"]) + best_option_data[2]

    span_sheet = workbook.create_sheet("por_vano")
    span_sheet.append(
        [
            "viga_id",
            "vano_id",
            "regiones_totales",
            "regiones_cumplen",
            "regiones_fallan",
            "peso_transversal_total_kg",
            "peso_longitudinal_total_kg",
            "peso_total_kg",
        ]
    )
    for beam_id, span_id in sorted(span_acc.keys()):
        span_row = span_acc[(beam_id, span_id)]
        span_sheet.append(
            [
                beam_id,
                span_id,
                int(span_row["total_regions"]),
                int(span_row["ok_regions"]),
                int(span_row["fail_regions"]),
                float(span_row["transverse_weight_sum_kg"]),
                float(span_row["longitudinal_weight_sum_kg"]),
                float(span_row["total_weight_sum_kg"]),
            ]
        )

    workbook.save(path)


def write_run_log(path: Path, lines: Iterable[str]) -> None:
    content = "\n".join(lines) + "\n"
    path.write_text(content, encoding="utf-8")


def span_summary_from_results(beam_id: str, span_id: str, results: list[RegionDesignResult], message: str = "") -> SpanSummary:
    ok_regions = sum(1 for result in results if result.status == "ok")
    fail_regions = len(results) - ok_regions
    return SpanSummary(
        beam_id=beam_id,
        span_id=span_id,
        total_regions=len(results),
        ok_regions=ok_regions,
        fail_regions=fail_regions,
        status="ok" if fail_regions == 0 else "fail",
        message=message,
    )


def beam_summary_from_spans(beam_id: str, span_summaries: list[SpanSummary]) -> BeamSummary:
    ok_spans = sum(1 for summary in span_summaries if summary.status == "ok")
    fail_spans = len(span_summaries) - ok_spans
    return BeamSummary(
        beam_id=beam_id,
        total_spans=len(span_summaries),
        ok_spans=ok_spans,
        fail_spans=fail_spans,
        status="ok" if fail_spans == 0 else "fail",
    )
