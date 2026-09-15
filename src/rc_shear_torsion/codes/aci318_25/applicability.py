from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ApplicabilityStatus(str, Enum):
    APPLIES = "APPLIES"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MISSING_DATA = "MISSING_DATA"


@dataclass(frozen=True)
class ApplicabilityDecision:
    status: ApplicabilityStatus
    reason: str
    missing_fields: tuple[str, ...] = ()


def required_fields(**values: object | None) -> ApplicabilityDecision:
    missing = tuple(name for name, value in values.items() if value is None)
    if missing:
        return ApplicabilityDecision(
            status=ApplicabilityStatus.MISSING_DATA,
            reason=f"Missing required data: {', '.join(missing)}",
            missing_fields=missing,
        )
    return ApplicabilityDecision(ApplicabilityStatus.APPLIES, "All required data are available")


def torsion_rule_applicability(torsion_states: Iterable[str]) -> ApplicabilityDecision:
    states = tuple(torsion_states)
    if not states:
        return ApplicabilityDecision(
            ApplicabilityStatus.MISSING_DATA,
            "No physical demand scenarios are available to classify torsion",
            ("torsion_states",),
        )
    if any(state == "INCONSISTENT" for state in states):
        return ApplicabilityDecision(
            ApplicabilityStatus.MISSING_DATA,
            "Torsion state is inconsistent and cannot be treated as active or inactive",
            ("consistent_torsion_state",),
        )
    if any(state == "ACTIVE" for state in states):
        return ApplicabilityDecision(
            ApplicabilityStatus.APPLIES,
            "At least one physical demand scenario has active torsion",
        )
    return ApplicabilityDecision(
        ApplicabilityStatus.NOT_APPLICABLE,
        "All physical demand scenarios have inactive torsion",
    )


def shear_minimum_applicability(*, vu_n: float | None) -> ApplicabilityDecision:
    if vu_n is None:
        return ApplicabilityDecision(
            ApplicabilityStatus.MISSING_DATA,
            "Vu and the data needed to evaluate the threshold in ACI 318-25 §9.6.3.1 are unavailable",
            ("Vu", "phi", "lambda", "Vc_or_applicable_threshold"),
        )
    return ApplicabilityDecision(
        ApplicabilityStatus.MISSING_DATA,
        "Vu alone is insufficient to establish the independent applicability of Av,min",
        ("phi", "lambda", "Vc_or_applicable_threshold"),
    )
