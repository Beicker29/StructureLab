from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import JobNotFoundError, JobNotReadyError
from app.models.job import JobRecord
from app.services.case_service import (
    load_case_json,
    normalize_case_inputs,
    save_excel_upload,
    write_case_json,
)
from rc_shear_torsion.run import run_case

EXPECTED_REPORTS = [
    "design_results.xlsx",
    "summary.xlsx",
    "optimized_results.xlsx",
    "reinforcement_schedule.xlsx",
    "run_log.txt",
]

_meta_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jobs_root() -> Path:
    root = get_settings().storage_dir / "jobs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _job_dir(job_id: str) -> Path:
    return _jobs_root() / job_id


def _job_meta_path(job_id: str) -> Path:
    return _job_dir(job_id) / "job.json"


def _write_json_atomic(path: Path, payload: dict) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _save_job(meta: JobRecord) -> None:
    path = _job_meta_path(meta["job_id"])
    with _meta_lock:
        _write_json_atomic(path, meta)


def _load_job(job_id: str) -> JobRecord:
    path = _job_meta_path(job_id)
    if not path.exists():
        raise JobNotFoundError(job_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload


def _create_job_from_payload(
    case_payload: dict,
    seismic_excel: UploadFile,
    gravity_excel: UploadFile,
) -> JobRecord:
    settings = get_settings()
    job_id = uuid.uuid4().hex
    job_dir = _job_dir(job_id)
    input_dir = job_dir / "input"
    output_root = job_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    seismic_path = input_dir / "seismic.xlsx"
    gravity_path = input_dir / "gravity.xlsx"
    case_path = input_dir / "case.json"

    save_excel_upload(seismic_excel, seismic_path, settings.max_upload_bytes, field_name="seismic_excel")
    save_excel_upload(gravity_excel, gravity_path, settings.max_upload_bytes, field_name="gravity_excel")

    normalized_case = normalize_case_inputs(case_payload)
    write_case_json(normalized_case, case_path)

    created_at = _now_iso()
    meta: JobRecord = {
        "job_id": job_id,
        "status": "queued",
        "created_at": created_at,
        "updated_at": created_at,
        "started_at": None,
        "finished_at": None,
        "error": None,
        "paths": {
            "job_dir": str(job_dir),
            "input_dir": str(input_dir),
            "output_root": str(output_root),
            "case_json": str(case_path),
            "seismic_excel": str(seismic_path),
            "gravity_excel": str(gravity_path),
        },
        "output_dir": None,
        "artifacts": {},
        "zip_path": None,
    }
    _save_job(meta)
    return meta


def create_job(case_json: UploadFile, seismic_excel: UploadFile, gravity_excel: UploadFile) -> JobRecord:
    settings = get_settings()
    case_payload = load_case_json(case_json, settings.max_upload_bytes)
    return _create_job_from_payload(case_payload, seismic_excel, gravity_excel)


def create_job_from_case_payload(
    case_payload: dict,
    seismic_excel: UploadFile,
    gravity_excel: UploadFile,
) -> JobRecord:
    return _create_job_from_payload(case_payload, seismic_excel, gravity_excel)


def run_job(job_id: str) -> None:
    meta = _load_job(job_id)
    meta["status"] = "running"
    meta["started_at"] = _now_iso()
    meta["updated_at"] = meta["started_at"]
    _save_job(meta)

    try:
        case_json_path = Path(meta["paths"]["case_json"])
        output_root = Path(meta["paths"]["output_root"])
        output_dir = run_case(case_json_path, output_root)

        artifacts: dict[str, str] = {}
        for filename in EXPECTED_REPORTS:
            candidate = output_dir / filename
            if candidate.exists():
                artifacts[filename] = str(candidate)

        finished_at = _now_iso()
        meta["status"] = "completed"
        meta["updated_at"] = finished_at
        meta["finished_at"] = finished_at
        meta["output_dir"] = str(output_dir)
        meta["artifacts"] = artifacts
        meta["error"] = None
        _save_job(meta)
    except Exception as exc:
        failed_at = _now_iso()
        meta["status"] = "failed"
        meta["updated_at"] = failed_at
        meta["finished_at"] = failed_at
        meta["error"] = str(exc)
        _save_job(meta)


def get_job(job_id: str) -> JobRecord:
    return _load_job(job_id)


def get_job_case_payload(job_id: str) -> dict:
    meta = _load_job(job_id)
    case_json_path = Path(meta["paths"]["case_json"])
    if not case_json_path.exists():
        raise JobNotFoundError(job_id)
    return json.loads(case_json_path.read_text(encoding="utf-8"))


def build_zip(job_id: str) -> Path:
    meta = _load_job(job_id)
    status_value = meta["status"]
    if status_value != "completed":
        raise JobNotReadyError(job_id, status_value)

    artifacts = meta.get("artifacts", {})
    if not artifacts:
        raise JobNotReadyError(job_id, status_value)

    zip_path = _job_dir(job_id) / f"{job_id}_reports.zip"
    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as zip_file:
        for filename in EXPECTED_REPORTS:
            full_path = artifacts.get(filename)
            if not full_path:
                continue
            file_path = Path(full_path)
            if file_path.exists():
                zip_file.write(file_path, arcname=filename)

    meta["zip_path"] = str(zip_path)
    meta["updated_at"] = _now_iso()
    _save_job(meta)
    return zip_path
