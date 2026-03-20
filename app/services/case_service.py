from __future__ import annotations

import json
from pathlib import Path

from fastapi import UploadFile

from app.core.errors import InvalidUploadError


def _read_upload(upload: UploadFile, max_bytes: int) -> bytes:
    data = upload.file.read()
    if len(data) > max_bytes:
        raise InvalidUploadError(
            f"El archivo '{upload.filename or 'sin_nombre'}' excede el limite de tamano"
        )
    return data


def _ensure_suffix(upload: UploadFile, allowed: set[str], field_name: str) -> None:
    filename = upload.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed:
        raise InvalidUploadError(
            f"'{field_name}' debe tener extension {sorted(allowed)} (archivo recibido: '{filename}')"
        )


def save_excel_upload(upload: UploadFile, destination: Path, max_bytes: int, field_name: str) -> None:
    _ensure_suffix(upload, {".xlsx"}, field_name)
    content = _read_upload(upload, max_bytes=max_bytes)
    destination.write_bytes(content)


def load_case_json(upload: UploadFile, max_bytes: int) -> dict:
    _ensure_suffix(upload, {".json"}, "case_json")
    content = _read_upload(upload, max_bytes=max_bytes)
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
