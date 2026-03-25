from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


@dataclass(frozen=True)
class Settings:
    app_env: str
    storage_dir: Path
    api_key: str | None
    max_upload_mb: int
    log_level: str
    service_name: str

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    app_env = os.environ.get("APP_ENV", "production")
    storage_dir = Path(os.environ.get("APP_STORAGE_DIR", "storage")).resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("APP_API_KEY")
    max_upload_mb = _env_int("APP_MAX_UPLOAD_MB", 25)
    log_level = os.environ.get("APP_LOG_LEVEL", "INFO")

    return Settings(
        app_env=app_env,
        storage_dir=storage_dir,
        api_key=api_key,
        max_upload_mb=max_upload_mb,
        log_level=log_level,
        service_name="StructureLab API",
    )


