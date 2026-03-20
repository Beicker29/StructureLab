from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


@dataclass
class AppError(Exception):
    message: str
    status_code: int = 500
    code: str = "internal_error"


class InvalidUploadError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=422, code="invalid_upload")


class JobNotFoundError(AppError):
    def __init__(self, job_id: str) -> None:
        super().__init__(
            message=f"Job '{job_id}' no existe",
            status_code=404,
            code="job_not_found",
        )


class JobNotReadyError(AppError):
    def __init__(self, job_id: str, status_value: str) -> None:
        super().__init__(
            message=f"Job '{job_id}' no esta listo para descarga (estado={status_value})",
            status_code=409,
            code="job_not_ready",
        )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message},
        )
