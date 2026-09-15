from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.errors import AppError
from app.dependencies.security import require_api_key
from app.schemas.common import ErrorResponse
from app.schemas.jobs import (
    JobCreateResponse,
    JobSelectionSaveRequest,
    JobSelectionSaveResponse,
    JobStatusResponse,
    RegionOptionSelection,
    SpanOptionSelection,
)
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
    save_selected_options_report,
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


SELECTION_VALIDATION_RESPONSE = {
    "model": ErrorResponse,
    "description": "La seleccion de alternativas por region es invalida",
    "content": {
        "application/json": {
            "example": {
                "error": "invalid_selection",
                "message": "La opcion 8 no existe para la region S1/R2",
                "details": [],
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


def _job_create_payload(request: Request, meta: dict) -> JobCreateResponse:
    job_id = meta["job_id"]
    base_url = str(request.base_url).rstrip("/")
    return JobCreateResponse(
        job_id=job_id,
        status=meta["status"],
        created_at=_parse_dt(meta["created_at"]),  # type: ignore[arg-type]
        status_url=f"{base_url}/v1/jobs/{job_id}",
        download_url=f"{base_url}/v1/jobs/{job_id}/download",
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

    return _job_create_payload(request, meta)


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
    d_ratio_default: float | None = Form(default=0.9),
    geometry_units: str = Form("mm"),
    db_bar: str = Form("#6"),
    compression_rebar_required: bool = Form(False),
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
        d_ratio_default=d_ratio_default,
        geometry_units=geometry_units,
        db_bar=db_bar,
        compression_rebar_required=compression_rebar_required,
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

    return _job_create_payload(request, meta)


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




@router.post(
    "/{job_id}/selection",
    response_model=JobSelectionSaveResponse,
    responses={
        404: JOB_NOT_FOUND_RESPONSE,
        409: JOB_NOT_READY_RESPONSE,
        422: SELECTION_VALIDATION_RESPONSE,
    },
)
def save_job_selection_endpoint(
    job_id: str,
    payload: JobSelectionSaveRequest,
    request: Request,
) -> JobSelectionSaveResponse:
    preview = build_job_preview_payload(job_id)
    spans = preview.get("spans") if isinstance(preview.get("spans"), list) else []

    region_data: dict[tuple[str, str], dict] = {}
    for span in spans:
        span_id = str(span.get("span_id") or "").strip()
        if not span_id:
            continue
        regions = span.get("regions") if isinstance(span.get("regions"), list) else []
        for region in regions:
            region_id = str(region.get("region_id") or "").strip()
            options = region.get("options") if isinstance(region.get("options"), list) else []
            normalized_rows = sorted(
                [
                    {
                        "option": int(opt.get("option")),
                        "transverse_label": str(opt.get("transverse_label") or "").strip(),
                        "longitudinal_label": str(opt.get("longitudinal_label") or "").strip(),
                        "base_longitudinal_label": str(opt.get("base_longitudinal_label") or "").strip(),
                        "additional_longitudinal_label": str(opt.get("additional_longitudinal_label") or "").strip(),
                        "weight_total_kg": float(opt.get("weight_total_kg") or 0.0),
                        "weight_transverse_kg": float(opt.get("weight_transverse_kg") or 0.0),
                        "weight_longitudinal_kg": float(opt.get("weight_longitudinal_kg") or 0.0),
                    }
                    for opt in options
                    if opt.get("option") is not None
                ],
                key=lambda item: (
                    float(item.get("weight_total_kg") or 0.0),
                    int(item.get("option") or 0),
                ),
            )
            if not region_id or not normalized_rows:
                continue

            best_row = normalized_rows[0]
            trans_map: dict[str, dict] = {}
            long_map: dict[str, dict] = {}

            preview_transverse_options = (
                region.get("transverse_options") if isinstance(region.get("transverse_options"), list) else []
            )
            for option in preview_transverse_options:
                trans_label = str(option.get("label") or "").strip()
                if not trans_label:
                    continue
                item: dict[str, float | int | str] = {
                    "label": trans_label,
                    "weight_kg": float(option.get("weight_kg") or 0.0),
                }
                if option.get("stirrup_count") is not None:
                    try:
                        item["stirrup_count"] = int(option.get("stirrup_count"))
                    except (TypeError, ValueError):
                        pass
                if option.get("stirrup_unit_weight_kg") is not None:
                    try:
                        item["stirrup_unit_weight_kg"] = float(option.get("stirrup_unit_weight_kg"))
                    except (TypeError, ValueError):
                        pass
                trans_map[trans_label] = item

            preview_longitudinal_options = (
                region.get("longitudinal_options") if isinstance(region.get("longitudinal_options"), list) else []
            )
            for option in preview_longitudinal_options:
                long_label = str(option.get("label") or "").strip()
                if not long_label:
                    continue
                long_map[long_label] = {
                    "label": long_label,
                    "weight_kg": float(option.get("weight_kg") or 0.0),
                }

            for row in normalized_rows:
                trans_label = row["transverse_label"]
                long_label = row["longitudinal_label"]
                trans_weight = float(row.get("weight_transverse_kg") or 0.0)
                long_weight = float(row.get("weight_longitudinal_kg") or 0.0)

                if trans_label:
                    current = trans_map.get(trans_label)
                    if current is None or trans_weight < float(current.get("weight_kg") or 0.0):
                        updated: dict[str, float | int | str] = {
                            "label": trans_label,
                            "weight_kg": trans_weight,
                        }
                        if current is not None and current.get("stirrup_count") is not None:
                            updated["stirrup_count"] = int(current["stirrup_count"])
                        if current is not None and current.get("stirrup_unit_weight_kg") is not None:
                            updated["stirrup_unit_weight_kg"] = float(current["stirrup_unit_weight_kg"])
                        trans_map[trans_label] = updated

                if long_label:
                    current = long_map.get(long_label)
                    if current is None or long_weight < float(current.get("weight_kg") or 0.0):
                        long_map[long_label] = {
                            "label": long_label,
                            "weight_kg": long_weight,
                        }

            if not trans_map and best_row["transverse_label"]:
                trans_map[best_row["transverse_label"]] = {
                    "label": best_row["transverse_label"],
                    "weight_kg": float(best_row.get("weight_transverse_kg") or 0.0),
                }
            if not long_map and best_row["longitudinal_label"]:
                long_map[best_row["longitudinal_label"]] = {
                    "label": best_row["longitudinal_label"],
                    "weight_kg": float(best_row.get("weight_longitudinal_kg") or 0.0),
                }
            region_data[(span_id, region_id)] = {
                "best": best_row,
                "rows": normalized_rows,
                "transverse_options": sorted(trans_map.values(), key=lambda item: float(item["weight_kg"])),
                "longitudinal_options": sorted(long_map.values(), key=lambda item: float(item["weight_kg"])),
            }

    if not region_data:
        raise AppError(
            message="No hay alternativas por region disponibles para este job.",
            status_code=422,
            code="selection_unavailable",
        )

    span_region_data: dict[str, list[tuple[str, dict]]] = {}
    for (span_id, region_id), data in region_data.items():
        span_region_data.setdefault(span_id, []).append((region_id, data))

    span_longitudinal_options: dict[str, list[dict]] = {}
    span_option_rows: dict[str, dict[int, dict[str, dict]]] = {}
    for span_id, items in span_region_data.items():
        common_labels: set[str] | None = None
        for _, data in items:
            labels = {
                str(option.get("label") or "").strip()
                for option in data["longitudinal_options"]
                if str(option.get("label") or "").strip()
            }
            common_labels = labels if common_labels is None else (common_labels & labels)

        options: list[dict] = []
        if common_labels:
            for label in common_labels:
                weight_sum = 0.0
                for _, data in items:
                    option = next(
                        (
                            entry
                            for entry in data["longitudinal_options"]
                            if str(entry.get("label") or "").strip() == label
                        ),
                        None,
                    )
                    weight_sum += float((option or {}).get("weight_kg") or 0.0)
                options.append({"label": label, "weight_kg": weight_sum, "coverage": len(items)})
            options.sort(key=lambda item: (float(item["weight_kg"]), str(item["label"])))
        else:
            union: dict[str, dict] = {}
            for _, data in items:
                for option in data["longitudinal_options"]:
                    label = str(option.get("label") or "").strip()
                    if not label:
                        continue
                    entry = union.setdefault(label, {"label": label, "weight_kg": 0.0, "coverage": 0})
                    entry["weight_kg"] = float(entry["weight_kg"]) + float(option.get("weight_kg") or 0.0)
                    entry["coverage"] = int(entry["coverage"]) + 1
            options = sorted(
                union.values(),
                key=lambda item: (-int(item["coverage"]), float(item["weight_kg"]), str(item["label"])),
            )

        span_longitudinal_options[span_id] = options[:10]

        common_option_numbers: set[int] | None = None
        for _, data in items:
            numbers = {
                int(row["option"])
                for row in data["rows"]
                if row.get("option") is not None
            }
            common_option_numbers = numbers if common_option_numbers is None else (common_option_numbers & numbers)

        option_map: dict[int, dict[str, dict]] = {}
        for option_number in sorted(common_option_numbers or []):
            per_region: dict[str, dict] = {}
            for region_id, data in items:
                row = next((row for row in data["rows"] if int(row["option"]) == option_number), None)
                if row is None:
                    per_region = {}
                    break
                per_region[region_id] = row
            if per_region:
                option_map[option_number] = per_region
        span_option_rows[span_id] = option_map

    requested_map: dict[tuple[str, str], RegionOptionSelection] = {}
    for item in payload.selections:
        key = (item.span_id.strip(), item.region_id.strip())
        if not key[0] or not key[1]:
            raise AppError(
                message="Cada seleccion debe incluir span_id y region_id validos.",
                status_code=422,
                code="invalid_selection",
            )
        if key in requested_map:
            raise AppError(
                message=f"La region {key[0]}/{key[1]} esta repetida en la seleccion.",
                status_code=422,
                code="invalid_selection",
            )
        requested_map[key] = item

    requested_span_map: dict[str, SpanOptionSelection] = {}
    for item in payload.span_selections:
        span_id = item.span_id.strip()
        if not span_id:
            raise AppError(
                message="Cada seleccion por vano debe incluir span_id valido.",
                status_code=422,
                code="invalid_selection",
            )
        if span_id in requested_span_map:
            raise AppError(
                message=f"El vano {span_id} esta repetido en span_selections.",
                status_code=422,
                code="invalid_selection",
            )
        if span_id not in span_region_data:
            raise AppError(
                message=f"El vano {span_id} no existe en el preview del job.",
                status_code=422,
                code="invalid_selection",
            )
        requested_span_map[span_id] = item

    invalid_regions = sorted(
        [f"{span_id}/{region_id}" for (span_id, region_id) in requested_map if (span_id, region_id) not in region_data]
    )
    if invalid_regions:
        raise AppError(
            message=f"Estas regiones no existen en el preview del job: {', '.join(invalid_regions)}",
            status_code=422,
            code="invalid_selection",
        )

    resolved_rows: list[dict] = []
    for key in sorted(region_data.keys()):
        span_id, region_id = key
        data = region_data[key]
        best = data["best"]

        trans_lookup = {item["label"]: item for item in data["transverse_options"] if item.get("label")}
        long_lookup = {item["label"]: item for item in data["longitudinal_options"] if item.get("label")}

        req = requested_map.get(key)
        span_req = requested_span_map.get(span_id)
        selected_transverse_label: str | None = None
        selected_longitudinal_label: str | None = None
        selected_base_longitudinal_label: str | None = None
        selected_additional_longitudinal_label: str | None = None

        if req is not None:
            if req.transverse_label:
                selected_transverse_label = req.transverse_label.strip()
            if req.longitudinal_label:
                selected_longitudinal_label = req.longitudinal_label.strip()
            if req.base_longitudinal_label:
                selected_base_longitudinal_label = req.base_longitudinal_label.strip()
            if req.additional_longitudinal_label:
                selected_additional_longitudinal_label = req.additional_longitudinal_label.strip()
            if req.option is not None and (not selected_transverse_label or not selected_longitudinal_label):
                option_row = next((row for row in data["rows"] if int(row["option"]) == int(req.option)), None)
                if option_row is None:
                    raise AppError(
                        message=f"La opcion {req.option} no existe para la region {span_id}/{region_id}.",
                        status_code=422,
                        code="invalid_selection",
                    )
                selected_transverse_label = selected_transverse_label or option_row["transverse_label"]
                selected_longitudinal_label = selected_longitudinal_label or option_row["longitudinal_label"]
                selected_base_longitudinal_label = selected_base_longitudinal_label or str(
                    option_row.get("base_longitudinal_label") or ""
                ).strip()
                selected_additional_longitudinal_label = selected_additional_longitudinal_label or str(
                    option_row.get("additional_longitudinal_label") or ""
                ).strip()

        if not selected_longitudinal_label and span_req is not None:
            span_options = span_longitudinal_options.get(span_id, [])
            option_rows = span_option_rows.get(span_id, {})
            if span_req.longitudinal_label:
                selected_longitudinal_label = span_req.longitudinal_label.strip()
            elif span_req.option is not None:
                span_option_number = int(span_req.option)
                option_row = (option_rows.get(span_option_number) or {}).get(region_id)
                if option_row is not None:
                    selected_longitudinal_label = str(option_row.get("longitudinal_label") or "").strip()
                    selected_base_longitudinal_label = selected_base_longitudinal_label or str(
                        option_row.get("base_longitudinal_label") or ""
                    ).strip()
                    selected_additional_longitudinal_label = selected_additional_longitudinal_label or str(
                        option_row.get("additional_longitudinal_label") or ""
                    ).strip()
                else:
                    option_index = span_option_number - 1
                    if option_index < 0 or option_index >= len(span_options):
                        raise AppError(
                            message=f"La opcion {span_req.option} no existe para el vano {span_id}.",
                            status_code=422,
                            code="invalid_selection",
                        )
                    selected_longitudinal_label = str(span_options[option_index]["label"])

        selected_longitudinal_label = selected_longitudinal_label or str(best.get("longitudinal_label") or "").strip()
        if not selected_transverse_label:
            compatible_rows = [
                row
                for row in data["rows"]
                if row["longitudinal_label"] == selected_longitudinal_label
            ]
            if selected_base_longitudinal_label:
                compatible_rows = [
                    row
                    for row in compatible_rows
                    if str(row.get("base_longitudinal_label") or "").strip() == selected_base_longitudinal_label
                ]
            if selected_additional_longitudinal_label:
                compatible_rows = [
                    row
                    for row in compatible_rows
                    if str(row.get("additional_longitudinal_label") or "").strip()
                    == selected_additional_longitudinal_label
                ]
            if compatible_rows:
                compatible_rows = sorted(
                    compatible_rows,
                    key=lambda row: (
                        float(row.get("weight_total_kg") or 0.0),
                        int(row.get("option") or 0),
                    ),
                )
                selected_transverse_label = str(compatible_rows[0].get("transverse_label") or "").strip()
            else:
                selected_transverse_label = str(best.get("transverse_label") or "").strip()

        if selected_transverse_label not in trans_lookup:
            raise AppError(
                message=f"El estribo '{selected_transverse_label}' no existe para la region {span_id}/{region_id}.",
                status_code=422,
                code="invalid_selection",
            )
        if selected_longitudinal_label not in long_lookup:
            raise AppError(
                message=f"El refuerzo longitudinal '{selected_longitudinal_label}' no existe para la region {span_id}/{region_id}.",
                status_code=422,
                code="invalid_selection",
            )

        selected_transverse = trans_lookup[selected_transverse_label]
        selected_longitudinal = long_lookup[selected_longitudinal_label]

        selected_combo_candidates = [
            row
            for row in data["rows"]
            if row["transverse_label"] == selected_transverse_label
            and row["longitudinal_label"] == selected_longitudinal_label
        ]
        if selected_base_longitudinal_label:
            selected_combo_candidates = [
                row
                for row in selected_combo_candidates
                if str(row.get("base_longitudinal_label") or "").strip() == selected_base_longitudinal_label
            ]
        if selected_additional_longitudinal_label:
            selected_combo_candidates = [
                row
                for row in selected_combo_candidates
                if str(row.get("additional_longitudinal_label") or "").strip() == selected_additional_longitudinal_label
            ]
        selected_combo = (
            sorted(
                selected_combo_candidates,
                key=lambda row: (
                    float(row.get("weight_total_kg") or 0.0),
                    int(row.get("option") or 0),
                ),
            )[0]
            if selected_combo_candidates
            else None
        )
        if selected_combo is None:
            raise AppError(
                message=(
                    f"La combinacion seleccionada no existe para la region {span_id}/{region_id} "
                    f"(transversal='{selected_transverse_label}', longitudinal='{selected_longitudinal_label}')."
                ),
                status_code=422,
                code="invalid_selection",
            )

        best_weight = float(best.get("weight_total_kg") or 0.0)
        selected_transverse_weight = float(selected_transverse.get("weight_kg") or 0.0)
        selected_longitudinal_weight = float(selected_longitudinal.get("weight_kg") or 0.0)
        combo_transverse_weight = selected_combo.get("weight_transverse_kg")
        combo_longitudinal_weight = selected_combo.get("weight_longitudinal_kg")
        combo_total_weight = selected_combo.get("weight_total_kg")
        if combo_transverse_weight is not None:
            selected_transverse_weight = float(combo_transverse_weight or 0.0)
        if combo_longitudinal_weight is not None:
            selected_longitudinal_weight = float(combo_longitudinal_weight or 0.0)
        if combo_total_weight is not None:
            selected_weight = float(combo_total_weight or 0.0)
        else:
            selected_weight = selected_transverse_weight + selected_longitudinal_weight
        diff_pct = ((selected_weight - best_weight) / best_weight * 100.0) if best_weight > 0 else None

        resolved_rows.append(
            {
                "span_id": span_id,
                "region_id": region_id,
                "best_option": best["option"],
                "selected_option": int(selected_combo["option"]) if selected_combo is not None else None,
                "best_transverse_label": best.get("transverse_label") or "",
                "best_longitudinal_label": best.get("longitudinal_label") or "",
                "selected_transverse_label": selected_transverse_label,
                "selected_longitudinal_label": selected_longitudinal_label,
                "selected_base_longitudinal_label": str(selected_combo.get("base_longitudinal_label") or "").strip(),
                "selected_additional_longitudinal_label": str(
                    selected_combo.get("additional_longitudinal_label") or ""
                ).strip(),
                "best_weight_kg": best_weight,
                "selected_weight_kg": selected_weight,
                "selected_transverse_weight_kg": selected_transverse_weight,
                "selected_longitudinal_weight_kg": selected_longitudinal_weight,
                "difference_kg": selected_weight - best_weight,
                "difference_pct": diff_pct,
            }
        )

    saved = save_selected_options_report(job_id, resolved_rows=resolved_rows)
    base_url = str(request.base_url).rstrip("/")
    artifact_name = str(saved["artifact_name"])
    return JobSelectionSaveResponse(
        job_id=job_id,
        saved_regions=int(saved["saved_regions"]),
        artifact_name=artifact_name,
        artifact_url=f"{base_url}/v1/jobs/{job_id}/artifacts/{artifact_name}",
    )


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







