from __future__ import annotations

from typing import Any

from fastapi import UploadFile

from app.domain.ingestion import (
    extract_unique_names_from_excel,
    parse_optimization_overrides,
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
    span_pairs = resolve_span_pairs(
        seismic_names=seismic_names,
        gravity_names=gravity_names,
        frame_names_csv=frame_names_csv,
        frame_pairs_json=frame_pairs_json,
    )

    optimization_overrides = parse_optimization_overrides(optimization_overrides_json)
    optimization_payload = merge_optimization_defaults(optimization_overrides)

    spans: list[dict[str, Any]] = []
    middle_to = 1.0 - region_c_ratio
    for index, pair in enumerate(span_pairs, start=1):
        span_id = f"{beam_id}.{index}"
        spans.append(
            {
                "id": span_id,
                "seismic": pair["seismic"],
                "gravity": pair["gravity"],
                "regions": [
                    {
                        "id": "R1",
                        "from": 0.0,
                        "to": region_c_ratio,
                        "type": "C",
                        "d_mm": d_mm,
                        "db_bar": db_bar,
                        "min_branches": min_branches_c,
                        "width_mm": width_mm,
                        "height_mm": height_mm,
                    },
                    {
                        "id": "R2",
                        "from": region_c_ratio,
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
                ],
            }
        )

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
