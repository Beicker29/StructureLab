from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.dependencies.security import require_api_key
from app.schemas.common import ErrorResponse
from app.schemas.jobs import JobCreateResponse, JobStatusResponse
from app.services.case_builder_service import build_case_payload_from_form
from app.services.job_preview_service import build_job_preview_payload
from app.services.job_service import (
    build_zip,
    create_job,
    create_job_from_case_payload,
    get_job,
    get_artifact_path,
    get_job_case_payload,
    run_job,
)

router = APIRouter(
    prefix="/v1/jobs",
    tags=["jobs"],
    dependencies=[Depends(require_api_key)],
)


JOB_NOT_FOUND_RESPONSE = {
    "model": ErrorResponse,
    "description": "El job solicitado no existe",
    "content": {
        "application/json": {
            "example": {
                "error": "job_not_found",
                "message": "Job 'abc123' no existe",
                "details": [],
            }
        }
    },
}

JOB_NOT_READY_RESPONSE = {
    "model": ErrorResponse,
    "description": "El job existe pero no esta listo para descarga",
    "content": {
        "application/json": {
            "example": {
                "error": "job_not_ready",
                "message": "Job 'abc123' no esta listo para descarga (estado=running)",
                "details": [],
            }
        }
    },
}

JOB_ARTIFACT_NOT_FOUND_RESPONSE = {
    "model": ErrorResponse,
    "description": "El artefacto solicitado no existe para ese job",
    "content": {
        "application/json": {
            "example": {
                "error": "job_artifact_not_found",
                "message": "El artefacto 'x.xlsx' no existe para el job 'abc123'",
                "details": [],
            }
        }
    },
}

INVALID_UPLOAD_RESPONSE = {
    "model": ErrorResponse,
    "description": "Carga invalida o formulario con datos inconsistentes",
    "content": {
        "application/json": {
            "example": {
                "error": "invalid_upload",
                "message": "'seismic_excel' debe tener extension ['.xlsx'] (archivo recibido: 'sismo.csv')",
                "details": [],
            }
        }
    },
}

DOMAIN_VALIDATION_RESPONSE = {
    "model": ErrorResponse,
    "description": "Reglas de negocio/ingenieria incumplidas",
    "content": {
        "application/json": {
            "example": {
                "error": "domain_validation_error",
                "message": "El formulario no cumple reglas de negocio/ingenieria",
                "details": [
                    {
                        "code": "invalid_range",
                        "field": "optimization.genetic_algorithm.population_size",
                        "message": "population_size must be >= 4",
                        "severity": "error",
                    }
                ],
            }
        }
    },
}


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


@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=202,
    responses={
        422: INVALID_UPLOAD_RESPONSE,
    },
)
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


@router.post(
    "/from-form",
    response_model=JobCreateResponse,
    status_code=202,
    responses={
        422: DOMAIN_VALIDATION_RESPONSE,
    },
)
def create_job_from_form_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    seismic_excel: UploadFile = File(...),
    gravity_excel: UploadFile = File(...),
    geometry_excel: UploadFile | None = File(default=None),
    case_name: str = Form("case_from_form"),
    sheet_name: str = Form("Conc Bm Sum - ACI 318-08"),
    units_rebar_per_length: str = Form("mm2/m"),
    beam_id: str = Form("B1"),
    detailing: str = Form("DMO"),
    cover_side_mm: float = Form(40.0),
    cover_top_mm: float = Form(40.0),
    cover_bottom_mm: float = Form(40.0),
    fc_mpa: float = Form(28.0),
    fy_mpa: float = Form(420.0),
    width_mm: float = Form(300.0),
    height_mm: float = Form(600.0),
    d_mm: float = Form(600.0),
    db_bar: str = Form("#6"),
    min_branches_c: int = Form(4),
    min_branches_nc: int = Form(2),
    region_c_ratio: float = Form(0.2),
    frame_names_csv: str | None = Form(default=None),
    frame_pairs_json: str | None = Form(default=None),
    optimization_overrides_json: str | None = Form(default=None),
    span_layout_json: str | None = Form(default=None),
) -> JobCreateResponse:
    settings = get_settings()
    case_payload = build_case_payload_from_form(
        seismic_excel=seismic_excel,
        gravity_excel=gravity_excel,
        geometry_excel=geometry_excel,
        max_upload_bytes=settings.max_upload_bytes,
        case_name=case_name,
        sheet_name=sheet_name,
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
        db_bar=db_bar,
        min_branches_c=min_branches_c,
        min_branches_nc=min_branches_nc,
        region_c_ratio=region_c_ratio,
        frame_names_csv=frame_names_csv,
        frame_pairs_json=frame_pairs_json,
        optimization_overrides_json=optimization_overrides_json,
        span_layout_json=span_layout_json,
    )

    meta = create_job_from_case_payload(
        case_payload=case_payload,
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


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    responses={
        404: JOB_NOT_FOUND_RESPONSE,
    },
)
def get_job_endpoint(job_id: str) -> JobStatusResponse:
    meta = get_job(job_id)
    return _status_payload(meta)


@router.get(
    "/{job_id}/case",
    responses={
        404: JOB_NOT_FOUND_RESPONSE,
    },
)
def get_job_case_endpoint(job_id: str) -> dict:
    return get_job_case_payload(job_id)


@router.get(
    "/{job_id}/preview",
    responses={
        404: JOB_NOT_FOUND_RESPONSE,
    },
)
def get_job_preview_endpoint(job_id: str) -> dict:
    return build_job_preview_payload(job_id)


@router.get(
    "/{job_id}/download",
    responses={
        404: JOB_NOT_FOUND_RESPONSE,
        409: JOB_NOT_READY_RESPONSE,
    },
)
def download_job_reports(job_id: str) -> FileResponse:
    zip_path = build_zip(job_id)
    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"{job_id}_reports.zip",
    )


@router.get(
    "/{job_id}/artifacts/{artifact_name}",
    responses={
        404: JOB_ARTIFACT_NOT_FOUND_RESPONSE,
        409: JOB_NOT_READY_RESPONSE,
    },
)
def download_job_artifact(job_id: str, artifact_name: str) -> FileResponse:
    artifact_path = get_artifact_path(job_id, artifact_name)
    return FileResponse(
        path=artifact_path,
        filename=artifact_name,
    )
