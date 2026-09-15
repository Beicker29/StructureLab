from __future__ import annotations

from pathlib import Path
from typing import Any

from .design import (
    RegionDemand,
    build_region_demands,
    make_failed_region_result,
    optimize_region,
    top_region_alternatives,
    to_region_result,
)
from .io import load_etabs_sources
from .models import load_case_config
from .report import (
    beam_summary_from_spans,
    ensure_output_dir,
    span_summary_from_results,
    write_design_results,
    write_optimized_results,
    write_reinforcement_schedule,
    write_run_log,
    write_summary,
)
from .span_coupled import optimize_span_coupled


def _to_non_negative(value: float | None) -> float:
    if value is None:
        return 0.0
    return value if value >= 0.0 else 0.0


def _resolved_span_supports(spans: list[Any]) -> dict[str, tuple[float, float]]:
    if not spans:
        return {}
    supports = [
        [_to_non_negative(getattr(span, "support_left_mm", None)), _to_non_negative(getattr(span, "support_right_mm", None))]
        for span in spans
    ]
    for index in range(len(supports) - 1):
        shared = max(supports[index][1], supports[index + 1][0])
        supports[index][1] = shared
        supports[index + 1][0] = shared
    return {spans[index].id: (supports[index][0], supports[index][1]) for index in range(len(spans))}


def run_case(case_json: str | Path, out_root: str | Path) -> Path:
    case_path = Path(case_json).resolve()
    config = load_case_config(case_path)
    sources = load_etabs_sources(config, case_path.parent)
    region_lengths_mm: dict[tuple[str, str, str], float] = {}

    log_lines: list[str] = []
    log_lines.append(f"case_name={config.case_name}")
    log_lines.append(f"case_file={case_path}")
    log_lines.append("units_v_rebar=mm2/m")
    log_lines.append("units_t_trn_rebar=mm2/m")
    log_lines.append("units_t_lng_rebar=mm2")
    for source_name, source_data in sources.items():
        log_lines.append(
            f"source={source_name} unique_names={len(source_data.by_unique_name)} "
            f"rows={source_data.row_count} skipped_rows={source_data.skipped_rows}"
        )
        for warning in source_data.warnings:
            log_lines.append(f"warning: {warning}")

    all_region_results: list = []
    region_alternatives: dict[tuple[str, str, str], list] = {}
    transverse_alternatives: dict[tuple[str, str, str], list] = {}
    all_span_summaries: list = []
    all_beam_summaries: list = []

    def add_failed_span_regions(beam: Any, span: Any, message: str, span_results: list) -> None:
        for region in span.regions:
            demand = RegionDemand(
                beam_id=beam.beam_id,
                span_id=span.id,
                region_id=region.id,
                region_type=region.type,
                beam_detailing=beam.detailing,
                d_mm=region.d_mm,
                db_bar=region.db_bar,
                min_branches=region.min_branches,
                width_mm=region.width_mm,
                height_mm=region.height_mm,
                cover_side_mm=beam.cover_side_mm,
                cover_top_mm=beam.cover_top_mm,
                cover_bottom_mm=beam.cover_bottom_mm,
                scenarios=tuple(),
                fc_mpa=beam.fc_mpa,
                fy_mpa=beam.fy_mpa,
                compression_rebar_required=beam.compression_rebar_required,
            )
            failed_result = make_failed_region_result(
                demand,
                failure_mode="input_fail",
                message=message,
            )
            span_results.append(failed_result)
            region_alternatives[(beam.beam_id, span.id, region.id)] = [failed_result]
            transverse_alternatives[(beam.beam_id, span.id, region.id)] = [failed_result]

    for beam in config.beams:
        beam_span_summaries: list = []
        support_by_span = _resolved_span_supports(beam.spans)

        span_results_by_span: dict[str, list] = {}
        span_region_index: dict[tuple[str, str], int] = {}
        beam_demands: list[RegionDemand] = []
        transverse_templates: dict[tuple[str, str], Any] = {}

        for span in beam.spans:
            span_results: list = []
            seismic_frame = sources["seismic"].by_unique_name.get(span.seismic)
            gravity_frame = sources["gravity"].by_unique_name.get(span.gravity)
            stations = [row.station for row in seismic_frame.stations] if seismic_frame is not None else []
            if gravity_frame is not None:
                stations.extend(row.station for row in gravity_frame.stations)
            model_span_length_mm = (max(stations) - min(stations)) if stations else 0.0
            support_left_mm, support_right_mm = support_by_span.get(span.id, (0.0, 0.0))
            clear_length_raw = getattr(span, "clear_length_mm", None)
            clear_length_override_mm = _to_non_negative(clear_length_raw)
            use_override = clear_length_raw is not None and clear_length_override_mm > 0.0
            span_length_mm = clear_length_override_mm if use_override else model_span_length_mm
            length_source = "override" if use_override else "model_station_diff"
            if model_span_length_mm > 0.0 or use_override:
                log_lines.append(
                    f"span={beam.beam_id}/{span.id} model_length_mm={model_span_length_mm:.3f} "
                    f"support_left_mm={support_left_mm:.3f} support_right_mm={support_right_mm:.3f} "
                    f"clear_length_override_mm={clear_length_override_mm:.3f} "
                    f"net_length_mm={span_length_mm:.3f} source={length_source}"
                )
            for region in span.regions:
                region_lengths_mm[(beam.beam_id, span.id, region.id)] = (region.to - region.from_) * span_length_mm

            if seismic_frame is None or gravity_frame is None:
                missing = []
                if seismic_frame is None:
                    missing.append(f"seismic UniqueName '{span.seismic}'")
                if gravity_frame is None:
                    missing.append(f"gravity UniqueName '{span.gravity}'")
                message = f"Span {span.id}: missing {', '.join(missing)}"
                log_lines.append(f"error: {message}")
                add_failed_span_regions(beam, span, message, span_results)
            else:
                region_demands, errors = build_region_demands(
                    beam_id=beam.beam_id,
                    beam_detailing=beam.detailing,
                    beam_cover_side_mm=beam.cover_side_mm,
                    beam_cover_top_mm=beam.cover_top_mm,
                    beam_cover_bottom_mm=beam.cover_bottom_mm,
                    beam_fc_mpa=beam.fc_mpa,
                    beam_fy_mpa=beam.fy_mpa,
                    span=span,
                    seismic_frame=seismic_frame,
                    gravity_frame=gravity_frame,
                    compression_rebar_required=beam.compression_rebar_required,
                )
                if errors:
                    message = "; ".join(errors)
                    log_lines.append(f"error: {message}")
                    add_failed_span_regions(beam, span, message, span_results)
                else:
                    for demand in region_demands:
                        outcome = optimize_region(demand, config.optimization)
                        result = to_region_result(demand, outcome)
                        span_results.append(result)
                        beam_demands.append(demand)
                        transverse_templates[(demand.span_id, demand.region_id)] = result

                        transverse_options = top_region_alternatives(
                            demand,
                            config.optimization.variables,
                            top_n=10,
                            check_longitudinal=(
                                config.optimization.longitudinal_mode == "legacy_region_independent"
                            ),
                        )
                        key_region = (beam.beam_id, span.id, demand.region_id)
                        transverse_alternatives[key_region] = transverse_options or [result]
                        region_alternatives[key_region] = transverse_options or [result]
                        log_lines.append(
                            f"region={beam.beam_id}/{span.id}/{demand.region_id} method={outcome.method} "
                            f"status={result.status} failure_mode={result.failure_mode} "
                            f"evaluated={outcome.evaluated_candidates} feasible={outcome.feasible_candidates}"
                        )

            span_results_by_span[span.id] = span_results
            for idx, result in enumerate(span_results):
                span_region_index[(span.id, result.region_id)] = idx

        if config.optimization.longitudinal_mode == "span_coupled" and beam_demands:
            beam_length_mm = sum(max(0.0, demand.region_length_mm) for demand in beam_demands)
            long_outcome = optimize_span_coupled(
                beam_demands,
                config.optimization,
                span_length_mm=beam_length_mm,
                top_n=200,
                transverse_templates=transverse_templates,
            )

            for updated in long_outcome.results:
                key = (updated.span_id, updated.region_id)
                index = span_region_index.get(key)
                if index is None:
                    continue
                span_results_by_span[updated.span_id][index] = updated

            for (span_id, region_id), options in long_outcome.alternatives_by_region.items():
                region_alternatives[(beam.beam_id, span_id, region_id)] = options

            log_lines.append(
                f"beam_longitudinal={beam.beam_id} method={long_outcome.method} "
                f"evaluated={long_outcome.evaluated_candidates} feasible={long_outcome.feasible_candidates}"
            )

        for span in beam.spans:
            span_results = span_results_by_span.get(span.id, [])
            span_summary = span_summary_from_results(
                beam_id=beam.beam_id,
                span_id=span.id,
                results=span_results,
                message="" if all(result.status == "ok" for result in span_results) else "One or more regions failed",
            )
            beam_span_summaries.append(span_summary)
            all_span_summaries.append(span_summary)
            all_region_results.extend(span_results)

        beam_summary = beam_summary_from_spans(beam.beam_id, beam_span_summaries)
        all_beam_summaries.append(beam_summary)
        log_lines.append(
            f"beam={beam.beam_id} status={beam_summary.status} spans_ok={beam_summary.ok_spans}/{beam_summary.total_spans}"
        )

    output_dir = Path(out_root).resolve() / config.case_name
    ensure_output_dir(output_dir)
    write_design_results(output_dir / "design_results.xlsx", all_region_results)
    write_summary(output_dir / "summary.xlsx", all_span_summaries, all_beam_summaries)
    write_optimized_results(output_dir / "optimized_results.xlsx", all_region_results)
    write_reinforcement_schedule(
        output_dir / "reinforcement_schedule.xlsx",
        all_region_results,
        region_lengths_mm,
        region_alternatives,
        transverse_alternatives=transverse_alternatives,
    )
    write_run_log(output_dir / "run_log.txt", log_lines)

    return output_dir
