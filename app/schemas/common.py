from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    python: str
    environment: str


class ErrorDetail(BaseModel):
    code: str
    field: str
    message: str
    severity: Literal["error", "warning"] = "error"
    context: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)

