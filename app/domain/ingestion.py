from __future__ import annotations

import json
from io import BytesIO
from typing import Any

from openpyxl import load_workbook

from app.core.errors import InvalidUploadError
from rc_shear_torsion.io import REQUIRED_COLUMNS, as_text, find_header


def _natural_name_key(value: str) -> tuple[int, Any]:
    text = value.strip()
    if text.isdigit():
        return (0, int(text))
    return (1, text)


def extract_unique_names_from_excel(excel_bytes: bytes, sheet_name: str, field_name: str) -> set[str]:
    try:
        workbook = load_workbook(filename=BytesIO(excel_bytes), read_only=True, data_only=True)
    except Exception as exc:
        raise InvalidUploadError(f"No fue posible leer '{field_name}' como archivo Excel valido") from exc

    if sheet_name not in workbook.sheetnames:
        raise InvalidUploadError(f"La hoja '{sheet_name}' no existe en '{field_name}'")

    worksheet = workbook[sheet_name]
    try:
        header_row_idx, header_map = find_header(worksheet.iter_rows(min_row=1, max_row=30, values_only=True))
    except ValueError as exc:
        raise InvalidUploadError(
            f"'{field_name}' no tiene encabezado ETABS valido en las primeras 30 filas"
        ) from exc
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in header_map]
    if missing_columns:
        raise InvalidUploadError(
            f"'{field_name}' no contiene columnas requeridas: {', '.join(missing_columns)}"
        )

    names: set[str] = set()
    for row in worksheet.iter_rows(min_row=header_row_idx + 1, values_only=True):
        if row is None:
            continue
        unique_name = as_text(row[header_map["UniqueName"]])
        station_value = row[header_map["Station"]]
        if not unique_name or station_value in (None, ""):
            continue
        names.add(unique_name)

    if not names:
        raise InvalidUploadError(
            f"'{field_name}' no contiene filas validas con columnas UniqueName y Station"
        )
    return names


def parse_csv_names(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_pairs_json(raw: str | None) -> list[dict[str, str]]:
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidUploadError("frame_pairs_json debe ser un JSON valido") from exc

    if not isinstance(payload, list):
        raise InvalidUploadError("frame_pairs_json debe ser una lista de objetos")

    parsed_pairs: list[dict[str, str]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise InvalidUploadError(f"frame_pairs_json[{index}] debe ser un objeto")
        seismic = str(item.get("seismic", "")).strip()
        gravity = str(item.get("gravity", "")).strip()
        span_id = str(item.get("id", "")).strip() or f"S{index}"
        if not seismic or not gravity:
            raise InvalidUploadError(
                f"frame_pairs_json[{index}] requiere 'seismic' y 'gravity'"
            )
        parsed_pairs.append({"id": span_id, "seismic": seismic, "gravity": gravity})
    return parsed_pairs


def parse_optimization_overrides(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidUploadError("optimization_overrides_json debe ser JSON valido") from exc
    if not isinstance(payload, dict):
        raise InvalidUploadError("optimization_overrides_json debe ser un objeto JSON")
    return payload


def resolve_span_pairs(
    *,
    seismic_names: set[str],
    gravity_names: set[str],
    frame_names_csv: str | None,
    frame_pairs_json: str | None,
) -> list[dict[str, str]]:
    span_pairs = parse_pairs_json(frame_pairs_json)
    if span_pairs:
        for pair in span_pairs:
            if pair["seismic"] not in seismic_names:
                raise InvalidUploadError(f"El vano seismic '{pair['seismic']}' no existe en seismic_excel")
            if pair["gravity"] not in gravity_names:
                raise InvalidUploadError(f"El vano gravity '{pair['gravity']}' no existe en gravity_excel")
        return span_pairs

    csv_names = parse_csv_names(frame_names_csv)
    if csv_names:
        for frame_name in csv_names:
            if frame_name not in seismic_names:
                raise InvalidUploadError(f"El vano '{frame_name}' no existe en seismic_excel")
            if frame_name not in gravity_names:
                raise InvalidUploadError(f"El vano '{frame_name}' no existe en gravity_excel")
        return [
            {"id": f"S{index}", "seismic": frame_name, "gravity": frame_name}
            for index, frame_name in enumerate(csv_names, start=1)
        ]

    shared = sorted(seismic_names & gravity_names, key=_natural_name_key)
    if not shared:
        raise InvalidUploadError(
            "No se encontraron UniqueName comunes entre seismic_excel y gravity_excel. "
            "Usa frame_pairs_json para mapear vanos distintos."
        )
    return [
        {"id": f"S{index}", "seismic": frame_name, "gravity": frame_name}
        for index, frame_name in enumerate(shared, start=1)
    ]

