from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from app.services.job_service import get_job, get_job_case_payload


def _normalize_header(value: Any) -> str:
    return str(value or "").strip().lower()


def _header_map(row: tuple[Any, ...]) -> dict[str, int]:
    return {_normalize_header(value): index for index, value in enumerate(row)}


def _find_col(columns: dict[str, int], *names: str) -> int | None:
    for name in names:
        key = _normalize_header(name)
        if key in columns:
            return columns[key]
    return None


def _as_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def _as_non_negative_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _as_int(value: Any) -> int | None:
    parsed = _as_float(value)
    if parsed is None:
        return None
    return int(round(parsed))


def _norm_match(value: str) -> str:
    return " ".join(value.lower().split())


def _read_optimized_regions(path: Path | None) -> dict[tuple[str, str], dict[str, Any]]:
    if path is None or not path.exists():
        return {}

    workbook = load_workbook(path, data_only=True, read_only=True)
    sheet = workbook["optimized_regions"] if "optimized_regions" in workbook.sheetnames else workbook[workbook.sheetnames[0]]
    iterator = sheet.iter_rows(values_only=True)
    header_row = next(iterator, None)
    if header_row is None:
        return {}

    columns = _header_map(header_row)
    span_col = _find_col(columns, "span_id", "vano_id")
    region_col = _find_col(columns, "region_id")
    e_bar_col = _find_col(columns, "e_bar")
    g_bar_col = _find_col(columns, "g_bar")
    g_count_col = _find_col(columns, "g_count")
    spacing_col = _find_col(columns, "spacing_mm")
    long_bar_col = _find_col(columns, "long_bar")
    long_count_col = _find_col(columns, "long_count")
    status_col = _find_col(columns, "status")
    if span_col is None or region_col is None:
        return {}

    output: dict[tuple[str, str], dict[str, Any]] = {}
    for row in iterator:
        span_id = _as_text(row[span_col])
        region_id = _as_text(row[region_col])
        if not span_id or not region_id:
            continue
        status = _as_text(row[status_col]) if status_col is not None else "ok"
        if status and status.lower() not in {"ok", "cumple"}:
            continue

        e_bar = _as_text(row[e_bar_col]) if e_bar_col is not None else ""
        g_bar = _as_text(row[g_bar_col]) if g_bar_col is not None else ""
        g_count = _as_int(row[g_count_col]) if g_count_col is not None else None
        spacing = _as_int(row[spacing_col]) if spacing_col is not None else None
        long_bar = _as_text(row[long_bar_col]) if long_bar_col is not None else ""
        long_count = _as_int(row[long_count_col]) if long_count_col is not None else None

        if e_bar and g_bar and g_count is not None and spacing is not None:
            transverse = f"1E {e_bar} + {g_count}G {g_bar} @ {spacing} mm"
        elif e_bar and spacing is not None:
            transverse = f"1E {e_bar} @ {spacing} mm"
        else:
            transverse = ""

        if long_count is not None and long_bar:
            longitudinal = f"{long_count}{long_bar}"
            longitudinal_schedule = f"{long_count} x {long_bar}"
        else:
            longitudinal = ""
            longitudinal_schedule = ""

        output[(span_id, region_id)] = {
            "spacing_mm": spacing,
            "transverse_label": transverse,
            "longitudinal_label": longitudinal,
            "longitudinal_schedule_label": longitudinal_schedule,
        }
    return output


def _read_schedule_rows(path: Path | None) -> dict[tuple[str, str], list[dict[str, Any]]]:
    if path is None or not path.exists():
        return {}

    workbook = load_workbook(path, data_only=True, read_only=True)
    sheet = workbook["por_region"] if "por_region" in workbook.sheetnames else workbook[workbook.sheetnames[0]]
    iterator = sheet.iter_rows(values_only=True)
    header_row = next(iterator, None)
    if header_row is None:
        return {}

    columns = _header_map(header_row)
    span_col = _find_col(columns, "span_id", "vano_id")
    region_col = _find_col(columns, "region_id")
    option_col = _find_col(columns, "option", "opcion")
    length_col = _find_col(columns, "longitud_region_mm", "region_length_mm", "length_mm")
    trans_col = _find_col(columns, "arreglo_transversal", "transverse_arrangement")
    long_col = _find_col(columns, "arreglo_longitudinal", "longitudinal_arrangement")
    if span_col is None or region_col is None or length_col is None:
        return {}

    output: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in iterator:
        span_id = _as_text(row[span_col])
        region_id = _as_text(row[region_col])
        if not span_id or not region_id:
            continue
        length_mm = _as_float(row[length_col])
        if length_mm is None:
            continue
        option = _as_int(row[option_col]) if option_col is not None else None
        transverse = _as_text(row[trans_col]) if trans_col is not None else ""
        longitudinal = _as_text(row[long_col]) if long_col is not None else ""
        output[(span_id, region_id)].append(
            {
                "length_mm": length_mm,
                "option": option,
                "transverse_label": transverse,
                "longitudinal_label": longitudinal,
            }
        )
    return output


def _pick_schedule_row(
    rows: list[dict[str, Any]],
    optimized: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not rows:
        return None
    if optimized:
        opt_trans = _norm_match(str(optimized.get("transverse_label") or ""))
        opt_long = _norm_match(str(optimized.get("longitudinal_schedule_label") or ""))
        if opt_trans:
            for row in rows:
                row_trans = _norm_match(str(row.get("transverse_label") or ""))
                row_long = _norm_match(str(row.get("longitudinal_label") or ""))
                if row_trans == opt_trans and (not opt_long or row_long == opt_long):
                    return row
    rows_sorted = sorted(rows, key=lambda item: item.get("option") if item.get("option") is not None else 999_999)
    return rows_sorted[0] if rows_sorted else None


def _build_span_preview(
    span: dict[str, Any],
    *,
    optimized_map: dict[tuple[str, str], dict[str, Any]],
    schedule_map: dict[tuple[str, str], list[dict[str, Any]]],
    default_span_length_mm: float = 6000.0,
) -> dict[str, Any]:
    span_id = _as_text(span.get("id")) or "S1"
    support_left_mm = _as_non_negative_float(span.get("support_left_mm"))
    support_right_mm = _as_non_negative_float(span.get("support_right_mm"))
    regions = span.get("regions") if isinstance(span.get("regions"), list) else []
    region_rows: list[dict[str, Any]] = []
    region_lengths: list[float] = []
    any_estimated = False

    for index, region in enumerate(regions, start=1):
        region_id = _as_text(region.get("id")) or f"R{index}"
        region_type = _as_text(region.get("type")) or "NC"
        start_ratio = _as_float(region.get("from")) or 0.0
        end_ratio = _as_float(region.get("to")) or 0.0
        if end_ratio < start_ratio:
            end_ratio = start_ratio
        ratio = max(end_ratio - start_ratio, 0.0)
        optimized = optimized_map.get((span_id, region_id))
        schedule_row = _pick_schedule_row(schedule_map.get((span_id, region_id), []), optimized)

        if schedule_row and schedule_row.get("length_mm"):
            length_mm = float(schedule_row["length_mm"])
            length_estimated = False
        else:
            length_mm = max(default_span_length_mm * ratio, 1.0)
            length_estimated = True
            any_estimated = True

        spacing_mm = optimized.get("spacing_mm") if optimized else None
        if spacing_mm is None:
            spacing_mm = 100 if region_type.upper() == "C" else 200
            spacing_estimated = True
        else:
            spacing_estimated = False

        transverse_label = (optimized or {}).get("transverse_label") or f"{region_type.upper()} @ {spacing_mm} mm est."
        longitudinal_label = (optimized or {}).get("longitudinal_label") or "long. n/d"

        region_rows.append(
            {
                "region_id": region_id,
                "type": region_type.upper(),
                "from": start_ratio,
                "to": end_ratio,
                "length_mm": int(round(length_mm)),
                "length_estimated": length_estimated,
                "spacing_mm": int(round(float(spacing_mm))),
                "spacing_estimated": spacing_estimated,
                "transverse_label": transverse_label,
                "longitudinal_label": longitudinal_label,
            }
        )
        region_lengths.append(length_mm)

    span_length_mm = int(round(sum(region_lengths))) if region_lengths else int(default_span_length_mm)
    if not region_rows:
        any_estimated = True
    return {
        "span_id": span_id,
        "seismic": _as_text(span.get("seismic")),
        "gravity": _as_text(span.get("gravity")),
        "support_left_mm": int(round(support_left_mm)) if support_left_mm is not None else None,
        "support_right_mm": int(round(support_right_mm)) if support_right_mm is not None else None,
        "length_mm": span_length_mm,
        "length_estimated": any_estimated,
        "regions": region_rows,
    }


def build_job_preview_payload(job_id: str) -> dict[str, Any]:
    meta = get_job(job_id)
    case_payload = get_job_case_payload(job_id)
    artifacts = meta.get("artifacts", {})
    optimized_path = Path(artifacts["optimized_results.xlsx"]) if "optimized_results.xlsx" in artifacts else None
    schedule_path = Path(artifacts["reinforcement_schedule.xlsx"]) if "reinforcement_schedule.xlsx" in artifacts else None

    optimized_map = _read_optimized_regions(optimized_path)
    schedule_map = _read_schedule_rows(schedule_path)

    beams = case_payload.get("beams") if isinstance(case_payload.get("beams"), list) else []
    beam = beams[0] if beams else {}
    spans = beam.get("spans") if isinstance(beam.get("spans"), list) else []
    span_rows = [
        _build_span_preview(
            span,
            optimized_map=optimized_map,
            schedule_map=schedule_map,
        )
        for span in spans
    ]

    total_span_mm = sum(span_row.get("length_mm", 0) for span_row in span_rows)
    total_support_mm = sum(
        int(span_row.get("support_right_mm", 0) or 0)
        for span_row in span_rows
    )
    if total_span_mm <= 0:
        total_span_mm = 6000

    return {
        "job_id": job_id,
        "status": meta.get("status"),
        "beam": {
            "beam_id": beam.get("beam_id"),
            "detailing": beam.get("detailing"),
            "fc_mpa": beam.get("fc_mpa"),
            "fy_mpa": beam.get("fy_mpa"),
            "width_mm": beam.get("width_mm"),
            "height_mm": beam.get("height_mm"),
        },
        "spans": span_rows,
        "total_span_mm": int(round(total_span_mm)),
        "total_support_mm": int(round(total_support_mm)),
        "total_system_mm": int(round(total_span_mm + total_support_mm)),
        "total_span_estimated": any(span_row.get("length_estimated", True) for span_row in span_rows),
        "data_source": {
            "optimized_results": bool(optimized_map),
            "reinforcement_schedule": bool(schedule_map),
        },
    }
