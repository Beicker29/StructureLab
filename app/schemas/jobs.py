from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


JobStatus = Literal["queued", "running", "completed", "failed"]


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus
    status_url: str
    download_url: str
    created_at: datetime


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    artifacts: list[str] = Field(default_factory=list)

