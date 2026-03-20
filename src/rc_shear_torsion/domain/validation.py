from __future__ import annotations

from typing import Any, Mapping

from rc_shear_torsion.models import CaseConfig

from .errors import DomainValidationError
from .rules import validate_case_rules


def validate_case_config(config: CaseConfig) -> CaseConfig:
    issues = validate_case_rules(config)
    if issues:
        raise DomainValidationError(issues)
    return config


def validate_case_payload(payload: Mapping[str, Any]) -> CaseConfig:
    config = CaseConfig.model_validate(payload)
    return validate_case_config(config)

