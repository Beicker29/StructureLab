from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse

from app.dependencies.security import require_api_key
from app.schemas.jobs import JobCreateResponse, JobStatusResponse
from app.services.job_service import build_zip, create_job, get_job, run_job

router = APIRouter(
    prefix="/v1/jobs",
    tags=["jobs"],
    dependencies=[Depends(require_api_key)],
)


def _parse_dt(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    return datetime.fromisoformat(raw)


def _status_payload(meta: dict) -> JobStatusResponse:
    artifacts = sorted(meta.get("artifacts", {}).keys())
    return JobStatusResponse(
        job_id=meta["job_id"],
        status=meta["status"],
        created_at=_parse_dt(meta["created_at"]),  # type: ignore[arg-type]
        updated_at=_parse_dt(meta["updated_at"]),  # type: ignore[arg-type]
        started_at=_parse_dt(meta.get("started_at")),
        finished_at=_parse_dt(meta.get("finished_at")),
        error=meta.get("error"),
        artifacts=artifacts,
    )


@router.post("", response_model=JobCreateResponse, status_code=202)
def create_job_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    case_json: UploadFile = File(...),
    seismic_excel: UploadFile = File(...),
    gravity_excel: UploadFile = File(...),
) -> JobCreateResponse:
    meta = create_job(
        case_json=case_json,
        seismic_excel=seismic_excel,
        gravity_excel=gravity_excel,
    )
    job_id = meta["job_id"]
    background_tasks.add_task(run_job, job_id)

    base_url = str(request.base_url).rstrip("/")
    return JobCreateResponse(
        job_id=job_id,
        status=meta["status"],
        created_at=_parse_dt(meta["created_at"]),  # type: ignore[arg-type]
        status_url=f"{base_url}/v1/jobs/{job_id}",
        download_url=f"{base_url}/v1/jobs/{job_id}/download",
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_endpoint(job_id: str) -> JobStatusResponse:
    meta = get_job(job_id)
    return _status_payload(meta)


@router.get("/{job_id}/download")
def download_job_reports(job_id: str) -> FileResponse:
    zip_path = build_zip(job_id)
    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"{job_id}_reports.zip",
    )

