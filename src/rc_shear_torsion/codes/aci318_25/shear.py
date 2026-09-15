from __future__ import annotations

import math

from .applicability import ApplicabilityStatus, required_fields, shear_minimum_applicability
from .common import RuleCheck, SpacingLimit, not_evaluated_check, spacing_limit_check


def check_minimum_shear_reinforcement(
    *,
    vu_n: float | None,
    station: float | None = None,
) -> RuleCheck:
    decision = shear_minimum_applicability(vu_n=vu_n)
    return not_evaluated_check(
        rule_id="ACI318_25_9_6_3_1_AV_MIN_APPLICABILITY",
        section="9.6.3.1",
        reason=decision.reason,
        station=station,
    )


def maximum_shear_spacing_limits(
    *,
    spacing_mm: float,
    d_mm: float | None,
    fc_mpa: float | None,
    bw_mm: float | None,
    fy_mpa: float | None,
    required_av_per_s_mm2_per_m: float | None,
    station: float | None = None,
) -> tuple[tuple[SpacingLimit, ...], tuple[RuleCheck, ...]]:
    decision = required_fields(
        d_mm=d_mm,
        fc_mpa=fc_mpa,
        bw_mm=bw_mm,
        fy_mpa=fy_mpa,
        required_av_per_s_mm2_per_m=required_av_per_s_mm2_per_m,
    )
    if decision.status == ApplicabilityStatus.MISSING_DATA:
        check = not_evaluated_check(
            rule_id="ACI318_25_9_7_6_2_2_SHEAR_SPACING",
            section="9.7.6.2.2, Table 9.7.6.2.2",
            reason=decision.reason,
            provided_value=spacing_mm,
            unit="mm",
            station=station,
        )
        return (), (check,)

    assert d_mm is not None
    assert fc_mpa is not None
    assert bw_mm is not None
    assert fy_mpa is not None
    assert required_av_per_s_mm2_per_m is not None

    required_vs_n = (required_av_per_s_mm2_per_m / 1000.0) * fy_mpa * d_mm
    threshold_n = 0.33 * math.sqrt(fc_mpa) * bw_mm * d_mm
    high_shear = required_vs_n > threshold_n
    factor_label = "d/4" if high_shear else "d/2"
    factor = 4.0 if high_shear else 2.0
    absolute_limit = 300.0 if high_shear else 600.0
    case_reason = (
        f"Required Vs={required_vs_n:.1f} N is "
        f"{'greater than' if high_shear else 'not greater than'} "
        f"0.33*sqrt(fc')*bw*d={threshold_n:.1f} N"
    )
    limits = (
        spacing_limit_check(
            rule_id=f"ACI318_25_9_7_6_2_2_{'HIGH' if high_shear else 'LOW'}_D_LIMIT",
            section="9.7.6.2.2, Table 9.7.6.2.2",
            reason=case_reason,
            maximum_mm=d_mm / factor,
            provided_mm=spacing_mm,
            label=factor_label,
            station=station,
        ),
        spacing_limit_check(
            rule_id=f"ACI318_25_9_7_6_2_2_{'HIGH' if high_shear else 'LOW'}_ABSOLUTE_LIMIT",
            section="9.7.6.2.2, Table 9.7.6.2.2",
            reason=case_reason,
            maximum_mm=absolute_limit,
            provided_mm=spacing_mm,
            label=str(int(absolute_limit)),
            station=station,
        ),
    )
    return limits, tuple(limit.check for limit in limits)
