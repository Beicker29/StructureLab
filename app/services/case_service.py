from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.core.errors import InvalidUploadError


def read_upload_bytes(upload: UploadFile, max_bytes: int) -> bytes:
    upload.file.seek(0)
    data = upload.file.read()
    if len(data) > max_bytes:
        raise InvalidUploadError(
            f"El archivo '{upload.filename or 'sin_nombre'}' excede el limite de tamano"
        )
    return data


def ensure_upload_suffix(upload: UploadFile, allowed: set[str], field_name: str) -> None:
    filename = upload.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed:
        raise InvalidUploadError(
            f"'{field_name}' debe tener extension {sorted(allowed)} (archivo recibido: '{filename}')"
        )


def save_excel_upload(upload: UploadFile, destination: Path, max_bytes: int, field_name: str) -> None:
    ensure_upload_suffix(upload, {".xlsx"}, field_name)
    content = read_upload_bytes(upload, max_bytes=max_bytes)
    destination.write_bytes(content)


def load_case_json(upload: UploadFile, max_bytes: int) -> dict:
    ensure_upload_suffix(upload, {".json"}, "case_json")
    content = read_upload_bytes(upload, max_bytes=max_bytes)
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidUploadError("El archivo case_json no es un JSON UTF-8 valido") from exc

    if not isinstance(payload, dict):
        raise InvalidUploadError("El case_json debe contener un objeto JSON en la raiz")
    if "inputs" not in payload or not isinstance(payload["inputs"], dict):
        raise InvalidUploadError("El case_json debe contener la clave 'inputs' como objeto")
    return payload


def normalize_case_inputs(payload: dict) -> dict:
    normalized = dict(payload)
    inputs = dict(normalized["inputs"])
    # Paths relativos al directorio input del job.
    inputs["seismic_excel"] = "seismic.xlsx"
    inputs["gravity_excel"] = "gravity.xlsx"
    normalized["inputs"] = inputs
    return normalized


def write_case_json(payload: dict, destination: Path) -> None:
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def merge_optimization_defaults(overrides: dict[str, Any] | None) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "enabled": True,
        "objective": "min_weight",
        "variables": {
            "E_bars": ["#3", "#4", "#6"],
            "G_bars": ["#3", "#4", "#6"],
            "G_counts": [0, 1, 2, 3, 4, 5],
            "stirrup_spacing_mm": [70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200],
            "longitudinal_bars": ["#4", "#5", "#6"],
            "longitudinal_bar_counts": [2, 4, 6, 8, 10, 12, 14],
        },
        "genetic_algorithm": {
            "population_size": 60,
            "generations": 80,
            "crossover_rate": 0.9,
            "mutation_rate": 0.1,
            "elite_count": 3,
        },
    }
    if not overrides:
        return defaults

    merged = dict(defaults)
    for key, value in overrides.items():
        if key not in merged:
            merged[key] = value
            continue
        if isinstance(merged[key], dict) and isinstance(value, dict):
            nested = dict(merged[key])
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return merged
