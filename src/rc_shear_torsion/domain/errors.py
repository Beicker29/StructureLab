from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class DomainIssue:
    code: str
    field: str
    message: str
    severity: Literal["error", "warning"] = "error"
    context: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "field": self.field,
            "message": self.message,
            "severity": self.severity,
        }
        if self.context:
            payload["context"] = self.context
        return payload


class DomainValidationError(ValueError):
    def __init__(self, issues: list[DomainIssue]) -> None:
        self.issues = issues
        if issues:
            first = issues[0]
            summary = f"Domain validation failed ({len(issues)} issues): {first.field}: {first.message}"
        else:
            summary = "Domain validation failed"
        super().__init__(summary)

    def to_dicts(self) -> list[dict[str, Any]]:
        return [issue.to_dict() for issue in self.issues]

