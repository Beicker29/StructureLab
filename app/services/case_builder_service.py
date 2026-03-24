from __future__ import annotations

from typing import Any

from fastapi import UploadFile

from app.domain.ingestion import (
    extract_unique_names_from_excel,
    parse_optimization_overrides,
    parse_span_layout_json,
    resolve_span_pairs,
)
from app.core.errors import DomainValidationAppError, InvalidUploadError
from app.services.case_service import (
    ensure_upload_suffix,
    merge_optimization_defaults,
    read_upload_bytes,
)
from rc_shear_torsion.domain.errors import DomainValidationError
from rc_shear_torsion.domain.validation import validate_case_payload


def _to_non_negative_support(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    if parsed < 0.0:
        return 0.0
    return parsed


def _harmonize_adjacent_supports(spans: list[dict[str, Any]]) -> None:
    if not spans:
        return
    for span in spans:
        span["support_left_mm"] = _to_non_negative_support(span.get("support_left_mm"))
        span["support_right_mm"] = _to_non_negative_support(span.get("support_right_mm"))

    for index in range(len(spans) - 1):
        current = spans[index]
        next_span = spans[index + 1]
        shared_support = max(
            _to_non_negative_support(current.get("support_right_mm")),
            _to_non_negative_support(next_span.get("support_left_mm")),
        )
        current["support_right_mm"] = shared_support
        next_span["support_left_mm"] = shared_support


def build_case_payload_from_form(
    *,
    seismic_excel: UploadFile,
    gravity_excel: UploadFile,
    max_upload_bytes: int,
    case_name: str,
    sheet_name: str,
    units_rebar_per_length: str,
    beam_id: str,
    detailing: str,
    cover_side_mm: float,
    cover_top_mm: float,
    cover_bottom_mm: float,
    fc_mpa: float,
    fy_mpa: float,
    width_mm: float,
    height_mm: float,
    d_mm: float,
    db_bar: str,
    min_branches_c: int,
    min_branches_nc: int,
    region_c_ratio: float,
    frame_names_csv: str | None,
    frame_pairs_json: str | None,
    optimization_overrides_json: str | None,
    span_layout_json: str | None = None,
) -> dict[str, Any]:
    case_name = case_name.strip() or "case_from_form"
    sheet_name = sheet_name.strip()
    if not sheet_name:
        raise InvalidUploadError("sheet_name no puede estar vacio")
    beam_id = beam_id.strip() or "B1"

    if region_c_ratio <= 0.0 or region_c_ratio >= 0.5:
        raise InvalidUploadError("region_c_ratio debe estar entre 0 y 0.5")

    ensure_upload_suffix(seismic_excel, {".xlsx"}, "seismic_excel")
    ensure_upload_suffix(gravity_excel, {".xlsx"}, "gravity_excel")
    seismic_bytes = read_upload_bytes(seismic_excel, max_upload_bytes)
    gravity_bytes = read_upload_bytes(gravity_excel, max_upload_bytes)

    seismic_names = extract_unique_names_from_excel(seismic_bytes, sheet_name, "seismic_excel")
    gravity_names = extract_unique_names_from_excel(gravity_bytes, sheet_name, "gravity_excel")
    span_layout = parse_span_layout_json(span_layout_json)

    span_layout_by_id: dict[str, dict[str, Any]] = {}
    if span_layout:
        for span_item in span_layout:
            seismic_name = span_item["seismic"]
            gravity_name = span_item["gravity"]
            if seismic_name not in seismic_names:
                raise InvalidUploadError(
                    f"El vano seismic '{seismic_name}' no existe en seismic_excel"
                )
            if gravity_name not in gravity_names:
                raise InvalidUploadError(
                    f"El vano gravity '{gravity_name}' no existe en gravity_excel"
                )
            span_layout_by_id[span_item["id"]] = span_item
        span_pairs = [
            {
                "id": span_item["id"],
                "seismic": span_item["seismic"],
                "gravity": span_item["gravity"],
            }
            for span_item in span_layout
        ]
    else:
        span_pairs = resolve_span_pairs(
            seismic_names=seismic_names,
            gravity_names=gravity_names,
            frame_names_csv=frame_names_csv,
            frame_pairs_json=frame_pairs_json,
        )

    optimization_overrides = parse_optimization_overrides(optimization_overrides_json)
    optimization_payload = merge_optimization_defaults(optimization_overrides)

    spans: list[dict[str, Any]] = []

    def _build_default_regions(ratio: float) -> list[dict[str, Any]]:
        middle_to = 1.0 - ratio
        return [
            {
                "id": "R1",
                "from": 0.0,
                "to": ratio,
                "type": "C",
                "d_mm": d_mm,
                "db_bar": db_bar,
                "min_branches": min_branches_c,
                "width_mm": width_mm,
                "height_mm": height_mm,
            },
            {
                "id": "R2",
                "from": ratio,
                "to": middle_to,
                "type": "NC",
                "d_mm": d_mm,
                "db_bar": db_bar,
                "min_branches": min_branches_nc,
                "width_mm": width_mm,
                "height_mm": height_mm,
            },
            {
                "id": "R3",
                "from": middle_to,
                "to": 1.0,
                "type": "C",
                "d_mm": d_mm,
                "db_bar": db_bar,
                "min_branches": min_branches_c,
                "width_mm": width_mm,
                "height_mm": height_mm,
            },
        ]

    def _build_regions_for_span(span_meta: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not span_meta:
            return _build_default_regions(region_c_ratio)

        configured_regions = span_meta.get("regions")
        if isinstance(configured_regions, list) and configured_regions:
            output_regions: list[dict[str, Any]] = []
            for region in configured_regions:
                region_type = str(region["type"]).upper()
                min_branches_value = region.get("min_branches")
                if min_branches_value is None:
                    min_branches_value = min_branches_c if region_type == "C" else min_branches_nc
                output_regions.append(
                    {
                        "id": region["id"],
                        "from": region["from"],
                        "to": region["to"],
                        "type": region_type,
                        "d_mm": region.get("d_mm") if region.get("d_mm") is not None else d_mm,
                        "db_bar": region.get("db_bar") if region.get("db_bar") else db_bar,
                        "min_branches": min_branches_value,
                        "width_mm": region.get("width_mm") if region.get("width_mm") is not None else width_mm,
                        "height_mm": region.get("height_mm") if region.get("height_mm") is not None else height_mm,
                    }
                )
            return output_regions

        ratio = span_meta.get("c_ratio_extremos")
        if ratio is None:
            ratio = region_c_ratio
        return _build_default_regions(float(ratio))

    for index, pair in enumerate(span_pairs, start=1):
        span_meta = span_layout_by_id.get(pair.get("id", ""))
        span_id = (
            str(pair.get("id", "")).strip() if span_layout else f"{beam_id}.{index}"
        ) or f"{beam_id}.{index}"
        span_payload: dict[str, Any] = {
            "id": span_id,
            "seismic": pair["seismic"],
            "gravity": pair["gravity"],
            "regions": _build_regions_for_span(span_meta),
        }
        if span_meta:
            if span_meta.get("support_left_mm") is not None:
                span_payload["support_left_mm"] = span_meta["support_left_mm"]
            if span_meta.get("support_right_mm") is not None:
                span_payload["support_right_mm"] = span_meta["support_right_mm"]
        spans.append(span_payload)

    _harmonize_adjacent_supports(spans)

    case_payload = {
        "case_name": case_name,
        "inputs": {
            "seismic_excel": "seismic.xlsx",
            "gravity_excel": "gravity.xlsx",
            "sheet_name": sheet_name,
        },
        "units": {"rebar_per_length": units_rebar_per_length},
        "beams": [
            {
                "beam_id": beam_id,
                "detailing": detailing,
                "cover_side_mm": cover_side_mm,
                "cover_top_mm": cover_top_mm,
                "cover_bottom_mm": cover_bottom_mm,
                "fc_mpa": fc_mpa,
                "fy_mpa": fy_mpa,
                "spans": spans,
            }
        ],
        "optimization": optimization_payload,
    }
    try:
        validated = validate_case_payload(case_payload)
    except DomainValidationError as exc:
        raise DomainValidationAppError(
            message="El formulario no cumple reglas de negocio/ingenieria",
            details=exc.to_dicts(),
        ) from exc

    return validated.model_dump(mode="python", by_alias=True)
