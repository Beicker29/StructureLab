from __future__ import annotations

from typing import Any

from app.core.errors import DomainValidationAppError, InvalidUploadError
from rc_shear_torsion.domain.errors import DomainValidationError
from rc_shear_torsion.domain.validation import validate_case_payload
from rc_shear_torsion.reinforcement import BAR_DIAMETERS_MM


def _to_non_negative_support(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    if parsed < 0.0:
        return 0.0
    return parsed


def _to_positive_ratio(value: Any, *, field_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidUploadError(f"{field_name} debe ser numerico") from exc
    if parsed <= 0.0 or parsed > 1.0:
        raise InvalidUploadError(f"{field_name} debe estar en (0, 1]")
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


def _build_default_regions(
    *,
    ratio: float,
    span_width_mm: float,
    span_height_mm: float,
    span_d_mm: float,
    span_d_source: str,
    span_d_ratio: float,
    min_branches_c: int,
    min_branches_nc: int,
) -> list[dict[str, Any]]:
    middle_to = 1.0 - ratio
    return [
        {
            "id": "R1",
            "from": 0.0,
            "to": ratio,
            "type": "C",
            "d_mm": span_d_mm,
            "d_source": span_d_source,
            "d_ratio": span_d_ratio,
            "min_branches": min_branches_c,
            "width_mm": span_width_mm,
            "height_mm": span_height_mm,
        },
        {
            "id": "R2",
            "from": ratio,
            "to": middle_to,
            "type": "NC",
            "d_mm": span_d_mm,
            "d_source": span_d_source,
            "d_ratio": span_d_ratio,
            "min_branches": min_branches_nc,
            "width_mm": span_width_mm,
            "height_mm": span_height_mm,
        },
        {
            "id": "R3",
            "from": middle_to,
            "to": 1.0,
            "type": "C",
            "d_mm": span_d_mm,
            "d_source": span_d_source,
            "d_ratio": span_d_ratio,
            "min_branches": min_branches_c,
            "width_mm": span_width_mm,
            "height_mm": span_height_mm,
        },
    ]


def _build_regions_for_span(
    *,
    span_meta: dict[str, Any] | None,
    span_width_mm: float,
    span_height_mm: float,
    span_d_mm: float,
    span_d_source: str,
    span_d_ratio: float,
    min_branches_c: int,
    min_branches_nc: int,
    region_c_ratio: float,
) -> list[dict[str, Any]]:
    if not span_meta:
        return _build_default_regions(
            ratio=region_c_ratio,
            span_width_mm=span_width_mm,
            span_height_mm=span_height_mm,
            span_d_mm=span_d_mm,
            span_d_source=span_d_source,
            span_d_ratio=span_d_ratio,
            min_branches_c=min_branches_c,
            min_branches_nc=min_branches_nc,
        )

    configured_regions = span_meta.get("regions")
    if isinstance(configured_regions, list) and configured_regions:
        output_regions: list[dict[str, Any]] = []
        for region in configured_regions:
            region_type = str(region["type"]).upper()
            has_explicit_d = region.get("d_mm") is not None
            min_branches_value = region.get("min_branches")
            if min_branches_value is None:
                min_branches_value = min_branches_c if region_type == "C" else min_branches_nc
            region_payload = {
                    "id": region["id"],
                    "from": region["from"],
                    "to": region["to"],
                    "type": region_type,
                    "d_mm": region.get("d_mm") if region.get("d_mm") is not None else span_d_mm,
                    "d_source": "EXPLICIT" if has_explicit_d else span_d_source,
                    "d_ratio": None if has_explicit_d else span_d_ratio,
                    "min_branches": min_branches_value,
                    "width_mm": region.get("width_mm") if region.get("width_mm") is not None else span_width_mm,
                    "height_mm": region.get("height_mm") if region.get("height_mm") is not None else span_height_mm,
                }
            if region.get("db_bar"):
                # Compatibility boundary for legacy region-level cases.
                region_payload["db_bar"] = region["db_bar"]
            output_regions.append(region_payload)
        return output_regions

    ratio = span_meta.get("c_ratio_extremos")
    if ratio is None:
        ratio = region_c_ratio

    return _build_default_regions(
        ratio=float(ratio),
        span_width_mm=span_width_mm,
        span_height_mm=span_height_mm,
        span_d_mm=span_d_mm,
        span_d_source=span_d_source,
        span_d_ratio=span_d_ratio,
        min_branches_c=min_branches_c,
        min_branches_nc=min_branches_nc,
    )


def build_validated_case_payload(
    *,
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
    db_bar: str,
    min_branches_c: int,
    min_branches_nc: int,
    region_c_ratio: float,
    span_pairs: list[dict[str, str]],
    span_layout: list[dict[str, Any]] | None,
    optimization_payload: dict[str, Any],
    span_dimensions_by_pair: dict[tuple[str, str, str], tuple[float, float]] | None = None,
    compression_rebar_required: bool = False,
) -> dict[str, Any]:
    normalized_case_name = case_name.strip() or "case_from_form"
    normalized_sheet_name = sheet_name.strip()
    if not normalized_sheet_name:
        raise InvalidUploadError("sheet_name no puede estar vacio")

    normalized_beam_id = beam_id.strip() or "B1"
    if region_c_ratio <= 0.0 or region_c_ratio >= 0.5:
        raise InvalidUploadError("region_c_ratio debe estar entre 0 y 0.5")

    if d_ratio_default is None:
        if height_mm <= 0.0:
            raise InvalidUploadError("height_mm debe ser > 0 para inferir d_ratio_default")
        d_ratio_default = d_mm / height_mm
    default_d_ratio = _to_positive_ratio(d_ratio_default, field_name="d_ratio_default")
    if db_bar not in BAR_DIAMETERS_MM:
        raise InvalidUploadError("db_bar no es una barra longitudinal soportada")
    default_longitudinal_bar_diameter_mm = BAR_DIAMETERS_MM[db_bar]

    span_layout_by_id: dict[str, dict[str, Any]] = {}
    if span_layout:
        for span_item in span_layout:
            span_layout_by_id[span_item["id"]] = span_item

    spans: list[dict[str, Any]] = []
    pair_dimensions = span_dimensions_by_pair or {}

    for index, pair in enumerate(span_pairs, start=1):
        span_meta = span_layout_by_id.get(pair.get("id", ""))
        span_id = (str(pair.get("id", "")).strip() if span_layout else f"{normalized_beam_id}.{index}") or f"{normalized_beam_id}.{index}"

        pair_key = (
            str(pair.get("id", "")),
            str(pair.get("seismic", "")),
            str(pair.get("gravity", "")),
        )
        span_width_mm, span_height_mm = pair_dimensions.get(pair_key, (float(width_mm), float(height_mm)))

        span_d_ratio_raw = span_meta.get("d_ratio") if span_meta else None
        span_d_source = "DEFAULT_RATIO" if span_d_ratio_raw is None else "SPAN_RATIO"
        span_d_ratio = _to_positive_ratio(
            default_d_ratio if span_d_ratio_raw is None else span_d_ratio_raw,
            field_name=f"d_ratio vano {span_id}",
        )
        span_d_mm = span_height_mm * span_d_ratio
        span_payload: dict[str, Any] = {
            "id": span_id,
            "seismic": pair["seismic"],
            "gravity": pair["gravity"],
            "regions": _build_regions_for_span(
                span_meta=span_meta,
                span_width_mm=span_width_mm,
                span_height_mm=span_height_mm,
                span_d_mm=span_d_mm,
                span_d_source=span_d_source,
                span_d_ratio=span_d_ratio,
                min_branches_c=min_branches_c,
                min_branches_nc=min_branches_nc,
                region_c_ratio=region_c_ratio,
            ),
        }
        if span_meta:
            # Accept the initial Phase 3 form contract only as a compatibility
            # boundary. CaseConfig consolidates agreeing values globally and
            # rejects conflicts instead of treating these as span overrides.
            if span_meta.get("longitudinal_bar_diameter_mm") is not None:
                span_payload["longitudinal_bar_diameter_mm"] = span_meta[
                    "longitudinal_bar_diameter_mm"
                ]
            if span_meta.get("compression_rebar_required") is not None:
                span_payload["compression_rebar_required"] = span_meta[
                    "compression_rebar_required"
                ]
            if span_meta.get("support_left_mm") is not None:
                span_payload["support_left_mm"] = span_meta["support_left_mm"]
            if span_meta.get("support_right_mm") is not None:
                span_payload["support_right_mm"] = span_meta["support_right_mm"]
            if span_meta.get("clear_length_mm") is not None:
                span_payload["clear_length_mm"] = span_meta["clear_length_mm"]

        spans.append(span_payload)

    _harmonize_adjacent_supports(spans)

    case_payload = {
        "case_name": normalized_case_name,
        "longitudinal_bar_diameter_mm": default_longitudinal_bar_diameter_mm,
        "compression_rebar_required": bool(compression_rebar_required),
        "longitudinal_bars_bundled": False,
        "inputs": {
            "seismic_excel": "seismic.xlsx",
            "gravity_excel": "gravity.xlsx",
            "sheet_name": normalized_sheet_name,
        },
        "units": {"rebar_per_length": units_rebar_per_length},
        "beams": [
            {
                "beam_id": normalized_beam_id,
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

