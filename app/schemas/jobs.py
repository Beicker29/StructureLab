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


class RegionOptionSelection(BaseModel):
    span_id: str = Field(min_length=1)
    region_id: str = Field(min_length=1)
    option: int | None = Field(default=None, ge=1)
    transverse_label: str | None = None
    longitudinal_label: str | None = None


class JobSelectionSaveRequest(BaseModel):
    selections: list[RegionOptionSelection] = Field(default_factory=list)


class JobSelectionSaveResponse(BaseModel):
    job_id: str
    saved_regions: int
    artifact_name: str
    artifact_url: str
