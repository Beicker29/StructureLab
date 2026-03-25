from __future__ import annotations

import platform
from importlib.metadata import PackageNotFoundError, version

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/", response_model=HealthResponse)
def root_healthcheck() -> HealthResponse:
    settings = get_settings()
    try:
        app_version = version("StructureLab")
    except PackageNotFoundError:
        try:
            app_version = version("ShearTors_RC")
        except PackageNotFoundError:
            app_version = "0.1.0"
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=app_version,
        python=platform.python_version(),
        environment=settings.app_env,
    )
