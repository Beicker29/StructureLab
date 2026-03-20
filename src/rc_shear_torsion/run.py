from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
    write_reinforcement_schedule,
    span_summary_from_results,
    write_design_results,
    write_optimized_results,
    write_run_log,
    write_summary,
)


def ensure_python_312() -> None:
    if sys.version_info[:2] != (3, 12):
        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        raise RuntimeError(
            "This project requires Python 3.12.x. "
            f"Current interpreter: {version}. "
            "Use python3.12 to create/activate the virtual environment."
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rc_shear_torsion.run")
    parser.add_argument("case_json", help="Path to case.json")
    parser.add_argument("--out", default="results/", help="Output root directory")
    return parser


def run_case(case_json: str | Path, out_root: str | Path) -> Path:
    case_path = Path(case_json).resolve()
    config = load_case_config(case_path)
    sources = load_etabs_sources(config, case_path.parent)
    region_lengths_mm: dict[tuple[str, str, str], float] = {}

    log_lines: list[str] = []
    log_lines.append(f"case_name={config.case_name}")
    log_lines.append(f"case_file={case_path}")
    for source_name, source_data in sources.items():
        log_lines.append(
            f"source={source_name} unique_names={len(source_data.by_unique_name)} "
            f"rows={source_data.row_count} skipped_rows={source_data.skipped_rows}"
        )
        for warning in source_data.warnings:
            log_lines.append(f"warning: {warning}")

    all_region_results = []
    region_alternatives: dict[tuple[str, str, str], list] = {}
    all_span_summaries = []
    all_beam_summaries = []

    def add_failed_span_regions(beam, span, message: str, span_results: list) -> None:
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
                source_control="mixed",
                governing_station=None,
                v_req=0.0,
                t_req=0.0,
                l_req=0.0,
                station_count=0,
                fc_mpa=beam.fc_mpa,
                fy_mpa=beam.fy_mpa,
            )
            failed_result = make_failed_region_result(
                demand,
                failure_mode="input_fail",
                message=message,
            )
            span_results.append(failed_result)
            region_alternatives[(beam.beam_id, span.id, region.id)] = [failed_result]

    for beam in config.beams:
        beam_span_summaries = []
        for span in beam.spans:
            span_results = []
            seismic_frame = sources["seismic"].by_unique_name.get(span.seismic)
            gravity_frame = sources["gravity"].by_unique_name.get(span.gravity)
            stations = [row.station for row in seismic_frame.stations] if seismic_frame is not None else []
            if not stations and gravity_frame is not None:
                stations = [row.station for row in gravity_frame.stations]
            span_length_mm = (max(stations) - min(stations)) if stations else 0.0
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
                        region_alternatives[(beam.beam_id, span.id, demand.region_id)] = top_region_alternatives(
                            demand,
                            config.optimization.variables,
                            top_n=5,
                        )
                        log_lines.append(
                            f"region={beam.beam_id}/{span.id}/{demand.region_id} method={outcome.method} "
                            f"status={result.status} failure_mode={result.failure_mode} "
                            f"evaluated={outcome.evaluated_candidates} feasible={outcome.feasible_candidates}"
                        )

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
    )
    write_run_log(output_dir / "run_log.txt", log_lines)

    return output_dir


def main(argv: list[str] | None = None) -> int:
    ensure_python_312()
    parser = build_parser()
    args = parser.parse_args(argv)
    output_dir = run_case(args.case_json, args.out)
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
