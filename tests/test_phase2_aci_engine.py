from __future__ import annotations

import inspect
import unittest

from rc_shear_torsion.codes.aci318_25 import RuleStatus, evaluate_region_rules
from rc_shear_torsion.codes.aci318_25.applicability import (
    ApplicabilityStatus,
    torsion_rule_applicability,
)
from rc_shear_torsion.codes.aci318_25.common import (
    ACI_CODE_ID,
    ACI_CODE_SOURCE,
    not_applicable_check,
    not_evaluated_check,
    select_controlling_spacing_limit,
    spacing_limit_check,
)
from rc_shear_torsion.codes.aci318_25.shear import maximum_shear_spacing_limits
from rc_shear_torsion.codes.aci318_25.ties import TieRuleScope, select_tie_rule_scope
from rc_shear_torsion.codes.aci318_25.torsion import (
    check_minimum_transverse_reinforcement_for_torsion,
    torsion_spacing_limits,
)
from rc_shear_torsion import optimization
from rc_shear_torsion.design import Candidate, RegionDesignResult


def _evaluate(
    *,
    system: str,
    zone: str = "C",
    torsion_active: bool = False,
    compression_rebar_required: bool = False,
    spacing_mm: float = 100.0,
    include_geometry: bool = True,
):
    return evaluate_region_rules(
        system=system,
        zone=zone,
        spacing_mm=spacing_mm,
        d_mm=600.0,
        longitudinal_bar_diameter_mm=15.9,
        transverse_bar_diameter_mm=9.5,
        minimum_branches=2,
        provided_branches=2,
        compression_rebar_required=compression_rebar_required,
        torsion_states=("ACTIVE" if torsion_active else "INACTIVE",),
        torsion_station=2000.0,
        width_mm=300.0 if include_geometry else None,
        height_mm=600.0 if include_geometry else None,
        cover_side_mm=40.0 if include_geometry else None,
        cover_top_mm=40.0 if include_geometry else None,
        cover_bottom_mm=40.0 if include_geometry else None,
        fc_mpa=28.0,
        fy_mpa=420.0,
        required_av_per_s_mm2_per_m=10.0,
        shear_station=1000.0,
        provided_combined_transverse_mm2_per_m=1420.0,
        closed_stirrup_bar_diameter_mm=9.5,
    )


class Phase2AciEngineTests(unittest.TestCase):
    def test_rule_check_contains_complete_traceability_contract(self) -> None:
        evaluation = _evaluate(system="DMI")
        check = evaluation.checks[0]
        self.assertEqual(check.code, ACI_CODE_ID)
        self.assertEqual(check.source, ACI_CODE_SOURCE)
        self.assertTrue(check.rule_id)
        self.assertTrue(check.section)
        self.assertIn(check.status, set(RuleStatus))
        self.assertIsNotNone(check.applicability_reason)

    def test_dmi_without_torsion(self) -> None:
        evaluation = _evaluate(system="DMI", torsion_active=False)
        self.assertFalse(any(limit.label == "Ph/8" for limit in evaluation.spacing_limits))
        self.assertTrue(any(check.section == "18.3" for check in evaluation.checks))

    def test_dmi_with_torsion(self) -> None:
        evaluation = _evaluate(system="DMI", torsion_active=True)
        self.assertTrue(any(limit.label == "Ph/8" for limit in evaluation.spacing_limits))
        self.assertTrue(any(check.section == "9.7.6.3.1" for check in evaluation.checks))

    def test_dmo_without_torsion(self) -> None:
        evaluation = _evaluate(system="DMO", torsion_active=False)
        labels = {limit.label for limit in evaluation.spacing_limits}
        self.assertTrue({"d/4", "8db", "24dest", "300"}.issubset(labels))
        self.assertNotIn("Ph/8", labels)

    def test_dmo_with_torsion(self) -> None:
        evaluation = _evaluate(system="DMO", torsion_active=True)
        labels = {limit.label for limit in evaluation.spacing_limits}
        self.assertIn("Ph/8", labels)
        self.assertIn("24dest", labels)

    def test_des_without_torsion(self) -> None:
        evaluation = _evaluate(system="DES", torsion_active=False)
        labels = {limit.label for limit in evaluation.spacing_limits}
        self.assertIn("6db", labels)
        self.assertNotIn("Ph/8", labels)

    def test_des_with_torsion(self) -> None:
        evaluation = _evaluate(system="DES", torsion_active=True)
        labels = {limit.label for limit in evaluation.spacing_limits}
        self.assertIn("6db", labels)
        self.assertIn("Ph/8", labels)

    def test_dmo_non_confined_uses_d_over_2(self) -> None:
        evaluation = _evaluate(system="DMO", zone="NC")
        limit = next(
            limit for limit in evaluation.spacing_limits
            if limit.check.rule_id == "ACI318_25_18_4_2_5_D_OVER_2"
        )
        self.assertEqual(limit.maximum_mm, 300.0)

    def test_des_non_confined_uses_d_over_2(self) -> None:
        evaluation = _evaluate(system="DES", zone="NC")
        limit = next(
            limit for limit in evaluation.spacing_limits
            if limit.check.rule_id == "ACI318_25_18_6_4_5_D_OVER_2"
        )
        self.assertEqual(limit.maximum_mm, 300.0)

    def test_des_grade_550_uses_five_db(self) -> None:
        arguments = dict(
            system="DES",
            zone="C",
            spacing_mm=70.0,
            d_mm=600.0,
            longitudinal_bar_diameter_mm=15.9,
            transverse_bar_diameter_mm=9.5,
            minimum_branches=2,
            provided_branches=2,
            compression_rebar_required=False,
            torsion_states=("INACTIVE",),
            torsion_station=2000.0,
            width_mm=300.0,
            height_mm=600.0,
            cover_side_mm=40.0,
            cover_top_mm=40.0,
            cover_bottom_mm=40.0,
            fc_mpa=28.0,
            fy_mpa=550.0,
            required_av_per_s_mm2_per_m=10.0,
            shear_station=1000.0,
        )
        evaluation = evaluate_region_rules(**arguments)
        limit = next(limit for limit in evaluation.spacing_limits if limit.label == "5db")
        self.assertEqual(limit.maximum_mm, 79.5)
        self.assertEqual(limit.check.section, "18.6.4.4(d)")

    def test_zero_torsion_makes_every_torsion_rule_not_applicable(self) -> None:
        evaluation = _evaluate(system="DMI", torsion_active=False)
        torsion_checks = [
            check
            for check in evaluation.checks
            if check.section in {"9.7.6.3.1", "9.7.6.3.3"}
        ]
        self.assertTrue(torsion_checks)
        self.assertTrue(all(check.status == RuleStatus.NOT_APPLICABLE for check in torsion_checks))

    def test_ph_over_8_exists_only_with_active_torsion(self) -> None:
        inactive = _evaluate(system="DMI", torsion_active=False)
        active = _evaluate(system="DMI", torsion_active=True)
        self.assertFalse(any(limit.label == "Ph/8" for limit in inactive.spacing_limits))
        ph_limit = next(limit for limit in active.spacing_limits if limit.label == "Ph/8")
        self.assertEqual(ph_limit.check.section, "9.7.6.3.3")

    def test_ph_uses_centerline_perimeter_of_exterior_closed_stirrup(self) -> None:
        limits, _ = torsion_spacing_limits(
            torsion_states=("ACTIVE",),
            spacing_mm=100.0,
            width_mm=300.0,
            height_mm=600.0,
            cover_side_mm=40.0,
            cover_top_mm=40.0,
            cover_bottom_mm=40.0,
            closed_stirrup_bar_diameter_mm=9.5,
        )
        ph_limit = next(limit for limit in limits if limit.label == "Ph/8")
        expected_ph_mm = 2.0 * (210.5 + 510.5)
        self.assertEqual(ph_limit.maximum_mm, expected_ph_mm / 8.0)

    def test_active_torsion_missing_stirrup_diameter_is_not_evaluated(self) -> None:
        limits, checks = torsion_spacing_limits(
            torsion_states=("ACTIVE",),
            spacing_mm=100.0,
            width_mm=300.0,
            height_mm=600.0,
            cover_side_mm=40.0,
            cover_top_mm=40.0,
            cover_bottom_mm=40.0,
        )
        self.assertEqual(limits, ())
        self.assertEqual(checks[0].status, RuleStatus.NOT_EVALUATED)
        self.assertIn("closed_stirrup_bar_diameter_mm", checks[0].applicability_reason)

    def test_active_torsion_checks_combined_transverse_minimum(self) -> None:
        failed = check_minimum_transverse_reinforcement_for_torsion(
            torsion_states=("ACTIVE",),
            fc_mpa=25.0,
            bw_mm=300.0,
            fyt_mpa=420.0,
            provided_combined_mm2_per_m=200.0,
        )
        self.assertEqual(failed.section, "9.6.4.2")
        self.assertEqual(failed.required_value, 250.0)
        self.assertEqual(failed.status, RuleStatus.FAIL)
        self.assertEqual(failed.margin, -50.0)

        passed = check_minimum_transverse_reinforcement_for_torsion(
            torsion_states=("ACTIVE",),
            fc_mpa=25.0,
            bw_mm=300.0,
            fyt_mpa=420.0,
            provided_combined_mm2_per_m=250.0,
        )
        self.assertEqual(passed.status, RuleStatus.PASS)

    def test_inactive_torsion_makes_combined_minimum_not_applicable(self) -> None:
        check = check_minimum_transverse_reinforcement_for_torsion(
            torsion_states=("INACTIVE",),
            fc_mpa=None,
            bw_mm=None,
            fyt_mpa=None,
            provided_combined_mm2_per_m=None,
        )
        self.assertEqual(check.status, RuleStatus.NOT_APPLICABLE)

    def test_dmo_confined_uses_confirmed_300_mm_limit(self) -> None:
        evaluation = _evaluate(system="DMO", torsion_active=False)
        dmo_limits = [
            limit
            for limit in evaluation.spacing_limits
            if limit.check.rule_id.startswith("ACI318_25_18_4_2_4")
        ]
        absolute = next(limit for limit in dmo_limits if limit.label == "300")
        self.assertEqual(absolute.maximum_mm, 300.0)
        self.assertEqual(absolute.check.section, "18.4.2.4(d)")
        self.assertNotIn("150", {limit.label for limit in dmo_limits})

    def test_compression_false_does_not_activate_full_ties(self) -> None:
        self.assertEqual(
            select_tie_rule_scope(
                compression_rebar_required=False,
                system="DMO",
                zone="C",
            ),
            TieRuleScope.NONE,
        )

    def test_compression_true_selects_full_ties(self) -> None:
        self.assertEqual(
            select_tie_rule_scope(
                compression_rebar_required=True,
                system="DMI",
                zone="NC",
            ),
            TieRuleScope.FULL,
        )
        evaluation = _evaluate(system="DMI", zone="NC", compression_rebar_required=True)
        full_check = next(check for check in evaluation.checks if "FULL_TIE" in check.rule_id)
        self.assertEqual(full_check.status, RuleStatus.NOT_EVALUATED)
        self.assertEqual(full_check.section, "9.7.6.4.1-9.7.6.4.4")

    def test_des_confined_selects_lateral_support_only(self) -> None:
        self.assertEqual(
            select_tie_rule_scope(
                compression_rebar_required=False,
                system="DES",
                zone="C",
            ),
            TieRuleScope.LATERAL_SUPPORT_ONLY,
        )
        evaluation = _evaluate(system="DES", zone="C")
        support = next(check for check in evaluation.checks if "LATERAL_SUPPORT" in check.rule_id)
        self.assertEqual(support.status, RuleStatus.NOT_EVALUATED)

    def test_non_applicable_rule_has_no_numeric_values(self) -> None:
        check = not_applicable_check(rule_id="TEST_NA", section="test", reason="not applicable")
        self.assertEqual(check.status, RuleStatus.NOT_APPLICABLE)
        self.assertIsNone(check.required_value)
        self.assertIsNone(check.provided_value)
        self.assertIsNone(check.margin)

    def test_missing_required_geometry_is_not_evaluated(self) -> None:
        evaluation = _evaluate(system="DMI", torsion_active=True, include_geometry=False)
        torsion_spacing = next(
            check for check in evaluation.checks if check.rule_id.endswith("TORSION_SPACING")
        )
        self.assertEqual(torsion_spacing.status, RuleStatus.NOT_EVALUATED)
        self.assertNotEqual(evaluation.detailing_status, RuleStatus.PASS)

    def test_av_min_without_vu_is_not_evaluated(self) -> None:
        evaluation = _evaluate(system="DMI")
        minimum = next(check for check in evaluation.checks if "AV_MIN_APPLICABILITY" in check.rule_id)
        self.assertEqual(minimum.status, RuleStatus.NOT_EVALUATED)
        self.assertIn("Vu", minimum.applicability_reason)

    def test_minimum_spacing_uses_only_evaluated_limits(self) -> None:
        limits = (
            spacing_limit_check(
                rule_id="L200",
                section="test",
                reason="test",
                maximum_mm=200.0,
                provided_mm=100.0,
                label="200",
            ),
            spacing_limit_check(
                rule_id="L150",
                section="test",
                reason="test",
                maximum_mm=150.0,
                provided_mm=100.0,
                label="150",
            ),
        )
        _ = not_applicable_check(rule_id="NA", section="test", reason="test")
        _ = not_evaluated_check(rule_id="NE", section="test", reason="test")
        controlling = select_controlling_spacing_limit(limits)
        self.assertIsNotNone(controlling)
        self.assertEqual(controlling.label, "150")

    def test_general_shear_spacing_uses_aci_sqrt_threshold(self) -> None:
        limits, checks = maximum_shear_spacing_limits(
            spacing_mm=200.0,
            d_mm=600.0,
            fc_mpa=25.0,
            bw_mm=300.0,
            fy_mpa=420.0,
            required_av_per_s_mm2_per_m=1200.0,
            station=123.0,
        )
        self.assertEqual({limit.label for limit in limits}, {"d/4", "300"})
        self.assertTrue(all(check.station == 123.0 for check in checks))
        self.assertTrue(all("22.5.8.5.3" in check.section for check in checks))

    def test_general_shear_spacing_low_case_has_both_table_limits(self) -> None:
        limits, _ = maximum_shear_spacing_limits(
            spacing_mm=200.0,
            d_mm=600.0,
            fc_mpa=25.0,
            bw_mm=300.0,
            fy_mpa=420.0,
            required_av_per_s_mm2_per_m=10.0,
        )
        self.assertEqual(
            {limit.check.rule_id: limit.maximum_mm for limit in limits},
            {
                "ACI318_25_9_7_6_2_2_LOW_D_LIMIT": 300.0,
                "ACI318_25_9_7_6_2_2_LOW_ABSOLUTE_LIMIT": 600.0,
            },
        )

    def test_not_evaluated_never_aggregates_to_pass(self) -> None:
        evaluation = _evaluate(system="DMI")
        self.assertEqual(evaluation.detailing_status, RuleStatus.NOT_EVALUATED)

    def test_domain_prepares_separate_demand_detailing_and_overall_statuses(self) -> None:
        for model in (Candidate, RegionDesignResult):
            fields = model.__dataclass_fields__
            self.assertIn("demand_status", fields)
            self.assertIn("detailing_status", fields)
            self.assertIn("overall_status", fields)
            self.assertIn("rule_checks", fields)

    def test_optimizer_contains_no_aci_rule_formula(self) -> None:
        source = inspect.getsource(optimization)
        for forbidden in ("ACI318", "Ph/8", "16db", "48db", "0.33"):
            self.assertNotIn(forbidden, source)

    def test_torsion_applicability_rejects_inconsistent_state(self) -> None:
        decision = torsion_rule_applicability(("INCONSISTENT",))
        self.assertEqual(decision.status, ApplicabilityStatus.MISSING_DATA)


if __name__ == "__main__":
    unittest.main()
