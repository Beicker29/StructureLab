from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ...tolerances import dimensional_comparison_tolerance_mm, spacing_comparison_tolerance_mm


ACI_CODE_ID = "ACI_318_25"
ACI_CODE_SOURCE = "ACI 318-25 Code"


class RuleStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(frozen=True)
class RuleCheck:
    rule_id: str
    code: str
    section: str
    status: RuleStatus
    applicability_reason: str
    required_value: float | str | None
    provided_value: float | str | None
    margin: float | None
    unit: str | None
    source: str
    station: float | None
    candidate_dependent: bool = True


@dataclass(frozen=True)
class SpacingLimit:
    label: str
    check: RuleCheck

    @property
    def maximum_mm(self) -> float | None:
        value = self.check.required_value
        return float(value) if isinstance(value, (int, float)) else None


@dataclass(frozen=True)
class AciRuleEvaluation:
    checks: tuple[RuleCheck, ...]
    spacing_limits: tuple[SpacingLimit, ...]
    controlling_limit: SpacingLimit | None

    @property
    def detailing_status(self) -> RuleStatus:
        if any(check.status == RuleStatus.FAIL for check in self.checks):
            return RuleStatus.FAIL
        if any(check.status == RuleStatus.NOT_EVALUATED for check in self.checks):
            return RuleStatus.NOT_EVALUATED
        if any(check.status == RuleStatus.PASS for check in self.checks):
            return RuleStatus.PASS
        return RuleStatus.NOT_APPLICABLE

    @property
    def passes_enforced_rules(self) -> bool:
        return not any(check.status == RuleStatus.FAIL for check in self.checks)

    @property
    def passes_candidate_dependent_rules(self) -> bool:
        return not any(
            check.status == RuleStatus.FAIL and check.candidate_dependent
            for check in self.checks
        )


def spacing_limit_check(
    *,
    rule_id: str,
    section: str,
    reason: str,
    maximum_mm: float,
    provided_mm: float,
    label: str,
    station: float | None = None,
) -> SpacingLimit:
    margin = maximum_mm - provided_mm
    status = (
        RuleStatus.PASS
        if margin >= -spacing_comparison_tolerance_mm
        else RuleStatus.FAIL
    )
    return SpacingLimit(
        label=label,
        check=RuleCheck(
            rule_id=rule_id,
            code=ACI_CODE_ID,
            section=section,
            status=status,
            applicability_reason=reason,
            required_value=maximum_mm,
            provided_value=provided_mm,
            margin=margin,
            unit="mm",
            source=ACI_CODE_SOURCE,
            station=station,
        ),
    )


def not_applicable_check(
    *,
    rule_id: str,
    section: str,
    reason: str,
    station: float | None = None,
    candidate_dependent: bool = True,
) -> RuleCheck:
    return RuleCheck(
        rule_id=rule_id,
        code=ACI_CODE_ID,
        section=section,
        status=RuleStatus.NOT_APPLICABLE,
        applicability_reason=reason,
        required_value=None,
        provided_value=None,
        margin=None,
        unit=None,
        source=ACI_CODE_SOURCE,
        station=station,
        candidate_dependent=candidate_dependent,
    )


def not_evaluated_check(
    *,
    rule_id: str,
    section: str,
    reason: str,
    required_value: float | str | None = None,
    provided_value: float | str | None = None,
    unit: str | None = None,
    station: float | None = None,
    candidate_dependent: bool = True,
) -> RuleCheck:
    return RuleCheck(
        rule_id=rule_id,
        code=ACI_CODE_ID,
        section=section,
        status=RuleStatus.NOT_EVALUATED,
        applicability_reason=reason,
        required_value=required_value,
        provided_value=provided_value,
        margin=None,
        unit=unit,
        source=ACI_CODE_SOURCE,
        station=station,
        candidate_dependent=candidate_dependent,
    )


def boolean_check(
    *,
    rule_id: str,
    section: str,
    reason: str,
    satisfied: bool,
    required_value: float | str | None,
    provided_value: float | str | None,
    unit: str | None = None,
    station: float | None = None,
    candidate_dependent: bool = True,
) -> RuleCheck:
    margin: float | None = None
    if isinstance(required_value, (int, float)) and isinstance(provided_value, (int, float)):
        margin = float(provided_value) - float(required_value)
    return RuleCheck(
        rule_id=rule_id,
        code=ACI_CODE_ID,
        section=section,
        status=RuleStatus.PASS if satisfied else RuleStatus.FAIL,
        applicability_reason=reason,
        required_value=required_value,
        provided_value=provided_value,
        margin=margin,
        unit=unit,
        source=ACI_CODE_SOURCE,
        station=station,
        candidate_dependent=candidate_dependent,
    )


def minimum_length_check(
    *,
    rule_id: str,
    section: str,
    reason: str,
    minimum_mm: float,
    provided_mm: float,
    station: float | None = None,
    candidate_dependent: bool = True,
) -> RuleCheck:
    margin = provided_mm - minimum_mm
    return RuleCheck(
        rule_id=rule_id,
        code=ACI_CODE_ID,
        section=section,
        status=(
            RuleStatus.PASS
            if margin >= -dimensional_comparison_tolerance_mm
            else RuleStatus.FAIL
        ),
        applicability_reason=reason,
        required_value=minimum_mm,
        provided_value=provided_mm,
        margin=margin,
        unit="mm",
        source=ACI_CODE_SOURCE,
        station=station,
        candidate_dependent=candidate_dependent,
    )


def maximum_length_check(
    *,
    rule_id: str,
    section: str,
    reason: str,
    maximum_mm: float,
    provided_mm: float,
    station: float | None = None,
    candidate_dependent: bool = True,
) -> RuleCheck:
    margin = maximum_mm - provided_mm
    return RuleCheck(
        rule_id=rule_id,
        code=ACI_CODE_ID,
        section=section,
        status=(
            RuleStatus.PASS
            if margin >= -dimensional_comparison_tolerance_mm
            else RuleStatus.FAIL
        ),
        applicability_reason=reason,
        required_value=maximum_mm,
        provided_value=provided_mm,
        margin=margin,
        unit="mm",
        source=ACI_CODE_SOURCE,
        station=station,
        candidate_dependent=candidate_dependent,
    )


def select_controlling_spacing_limit(limits: tuple[SpacingLimit, ...]) -> SpacingLimit | None:
    """Select the smallest limit, preferring a seismic-system rule on exact ties.

    Chapter 18 rules describe the specific seismic detailing system.  When one
    of those rules and a general ACI rule produce the same numerical maximum,
    the Chapter 18 rule is the more specific traceability label.  This priority
    does not alter the limit value or the status of any RuleCheck.
    """
    evaluated = [
        limit
        for limit in limits
        if limit.check.status in {RuleStatus.PASS, RuleStatus.FAIL}
        and limit.maximum_mm is not None
    ]
    if not evaluated:
        return None

    def traceability_key(item: SpacingLimit) -> tuple[float, int, str]:
        rule_id = item.check.rule_id
        seismic_priority = 0 if rule_id.startswith("ACI318_25_18_") else 1
        return float(item.maximum_mm), seismic_priority, rule_id

    return min(evaluated, key=traceability_key)
