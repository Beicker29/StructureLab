from __future__ import annotations

from typing import Any

from fastapi import UploadFile

from app.core.errors import InvalidUploadError
from app.domain.case_payload import build_validated_case_payload
from app.domain.ingestion import (
    extract_design_sections_by_unique_name,
    extract_geometry_sections,
    extract_unique_names_from_excel,
    parse_optimization_overrides,
    parse_span_layout_json,
    resolve_span_pairs,
)
from app.services.case_service import (
    ensure_upload_suffix,
    merge_optimization_defaults,
    read_upload_bytes,
)

_GEOMETRY_UNIT_FACTORS_TO_MM = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
    "in": 25.4,
}


def _geometry_unit_factor_to_mm(units: str) -> float:
    normalized = (units or "").strip().lower()
    if normalized not in _GEOMETRY_UNIT_FACTORS_TO_MM:
        allowed = ", ".join(sorted(_GEOMETRY_UNIT_FACTORS_TO_MM.keys()))
        raise InvalidUploadError(f"geometry_units invalido: '{units}'. Valores permitidos: {allowed}")
    return _GEOMETRY_UNIT_FACTORS_TO_MM[normalized]


def _scale_geometry_sections(
    sections: dict[str, dict[str, float]],
    factor_to_mm: float,
) -> dict[str, dict[str, float]]:
    if factor_to_mm == 1.0:
        return sections
    return {
        name: {
            "width_mm": float(values["width_mm"]) * factor_to_mm,
            "height_mm": float(values["height_mm"]) * factor_to_mm,
        }
        for name, values in sections.items()
    }


def _resolve_span_dimensions(
    *,
    pair: dict[str, str],
    seismic_design_sections: dict[str, str],
    gravity_design_sections: dict[str, str],
    geometry_sections: dict[str, dict[str, float]],
) -> tuple[float, float]:
    seismic_name = pair["seismic"]
    gravity_name = pair["gravity"]
    seismic_section = seismic_design_sections.get(seismic_name, "")
    gravity_section = gravity_design_sections.get(gravity_name, "")

    section_candidates: list[str] = []
    if seismic_section:
        section_candidates.append(seismic_section)
    if gravity_section and gravity_section not in section_candidates:
        section_candidates.append(gravity_section)

    if not section_candidates:
        raise InvalidUploadError(
            f"No se encontro DesignSect para vano seismic='{seismic_name}' y gravity='{gravity_name}'"
        )

    matched: list[tuple[str, dict[str, float]]] = [
        (section_name, geometry_sections[section_name])
        for section_name in section_candidates
        if section_name in geometry_sections
    ]
    if not matched:
        raise InvalidUploadError(
            "No fue posible asignar geometria para el vano "
            f"seismic='{seismic_name}' gravity='{gravity_name}'. "
            f"DesignSect detectados={section_candidates} no existen en geometria(Name)."
        )

    if len(matched) == 1:
        geometry = matched[0][1]
        return float(geometry["width_mm"]), float(geometry["height_mm"])

    # Si sismo y gravedad apuntan a dos secciones distintas existentes, usamos la mas conservadora.
    selected = max(matched, key=lambda item: item[1]["width_mm"] * item[1]["height_mm"])
    geometry = selected[1]
    return float(geometry["width_mm"]), float(geometry["height_mm"])


def build_case_payload_from_form(
    *,
    seismic_excel: UploadFile,
    gravity_excel: UploadFile,
    geometry_excel: UploadFile | None = None,
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
    d_ratio_default: float | None,
    geometry_units: str,
    db_bar: str,
    min_branches_c: int,
    min_branches_nc: int,
    region_c_ratio: float,
    frame_names_csv: str | None,
    frame_pairs_json: str | None,
    optimization_overrides_json: str | None,
    span_layout_json: str | None = None,
) -> dict[str, Any]:
    normalized_sheet_name = sheet_name.strip()
    if not normalized_sheet_name:
        raise InvalidUploadError("sheet_name no puede estar vacio")

    ensure_upload_suffix(seismic_excel, {".xlsx"}, "seismic_excel")
    ensure_upload_suffix(gravity_excel, {".xlsx"}, "gravity_excel")
    seismic_bytes = read_upload_bytes(seismic_excel, max_upload_bytes)
    gravity_bytes = read_upload_bytes(gravity_excel, max_upload_bytes)

    geometry_sections: dict[str, dict[str, float]] = {}
    seismic_design_sections: dict[str, str] = {}
    gravity_design_sections: dict[str, str] = {}
    if geometry_excel is not None:
        ensure_upload_suffix(geometry_excel, {".xlsx"}, "geometry_excel")
        geometry_bytes = read_upload_bytes(geometry_excel, max_upload_bytes)
        geometry_sections = extract_geometry_sections(geometry_bytes, "geometry_excel")
        factor_to_mm = _geometry_unit_factor_to_mm(geometry_units)
        geometry_sections = _scale_geometry_sections(geometry_sections, factor_to_mm)

        seismic_design_sections = extract_design_sections_by_unique_name(
            seismic_bytes,
            normalized_sheet_name,
            "seismic_excel",
        )
        gravity_design_sections = extract_design_sections_by_unique_name(
            gravity_bytes,
            normalized_sheet_name,
            "gravity_excel",
        )

    seismic_names = extract_unique_names_from_excel(seismic_bytes, normalized_sheet_name, "seismic_excel")
    gravity_names = extract_unique_names_from_excel(gravity_bytes, normalized_sheet_name, "gravity_excel")
    span_layout = parse_span_layout_json(span_layout_json)

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

    span_dimensions_by_pair: dict[tuple[str, str, str], tuple[float, float]] = {}
    if geometry_sections:
        for pair in span_pairs:
            span_dimensions_by_pair[
                (
                    str(pair.get("id", "")),
                    str(pair.get("seismic", "")),
                    str(pair.get("gravity", "")),
                )
            ] = _resolve_span_dimensions(
                pair=pair,
                seismic_design_sections=seismic_design_sections,
                gravity_design_sections=gravity_design_sections,
                geometry_sections=geometry_sections,
            )

    return build_validated_case_payload(
        case_name=case_name,
        sheet_name=normalized_sheet_name,
        units_rebar_per_length=units_rebar_per_length,
        beam_id=beam_id,
        detailing=detailing,
        cover_side_mm=cover_side_mm,
        cover_top_mm=cover_top_mm,
        cover_bottom_mm=cover_bottom_mm,
        fc_mpa=fc_mpa,
        fy_mpa=fy_mpa,
        width_mm=width_mm,
        height_mm=height_mm,
        d_mm=d_mm,
        d_ratio_default=d_ratio_default,
        db_bar=db_bar,
        min_branches_c=min_branches_c,
        min_branches_nc=min_branches_nc,
        region_c_ratio=region_c_ratio,
        span_pairs=span_pairs,
        span_layout=span_layout,
        optimization_payload=optimization_payload,
        span_dimensions_by_pair=span_dimensions_by_pair,
    )
