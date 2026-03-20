from __future__ import annotations

from typing import Literal, TypedDict


JobStatus = Literal["queued", "running", "completed", "failed"]


class JobRecord(TypedDict):
    job_id: str
    status: JobStatus
    created_at: str
    updated_at: str
    started_at: str | None
    finished_at: str | None
    error: str | None
    paths: dict[str, str]
    output_dir: str | None
    artifacts: dict[str, str]
    zip_path: str | None

