from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.routers.health import router as health_router
from app.routers.jobs import router as jobs_router
from app.routers.ui import router as ui_router


def _configure_logging() -> None:
    settings = get_settings()
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


_configure_logging()
settings = get_settings()

app = FastAPI(
    title=settings.service_name,
    version="1.0.0",
    description="API para diseno y optimizacion de refuerzo en vigas RC por cortante y torsion.",
)

register_exception_handlers(app)
app.include_router(health_router)
app.include_router(jobs_router)
app.include_router(ui_router)
