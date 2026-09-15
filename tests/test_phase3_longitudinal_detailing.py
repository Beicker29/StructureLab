from __future__ import annotations

import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.domain.case_payload import build_validated_case_payload
from app.domain.ingestion import parse_span_layout_json
from app.services.case_service import merge_optimization_defaults
from rc_shear_torsion.codes.aci318_25 import RuleStatus
from rc_shear_torsion.codes.aci318_25.common import select_controlling_spacing_limit
from rc_shear_torsion.codes.aci318_25.ties import (
    TieRuleScope,
    check_transverse_reinforcement_size,
    tie_rule_checks,
)
from rc_shear_torsion.design import (
    DemandScenario,
    RegionDemand,
    build_region_demands,
    classify_torsion_state,
    evaluate_candidate,
    optimize_region_exhaustive,
    spacing_domain_for_region,
)
from rc_shear_torsion.io import EtabsFrameData, EtabsStationRow
from rc_shear_torsion.models import CaseConfig, VariablesConfig


ROOT = Path(__file__).resolve().parents[1]


def _form_payload(
    *,
    db_bar: str = "#6",
    compression_rebar_required: bool = False,
    span_layout: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return build_validated_case_payload(
        case_name="phase3",
        sheet_name="Conc Bm Sum - ACI 318-08",
        units_rebar_per_length="mm2/m",
        beam_id="B1",
        detailing="DMI",
        cover_side_mm=40.0,
        cover_top_mm=40.0,
        cover_bottom_mm=40.0,
        fc_mpa=28.0,
        fy_mpa=420.0,
        width_mm=150.0,
        height_mm=750.0,
        d_mm=675.0,
        d_ratio_default=0.9,
        db_bar=db_bar,
        min_branches_c=4,
        min_branches_nc=2,
        region_c_ratio=0.2,
        span_pairs=[{"id": "S1", "seismic": "1", "gravity": "1"}],
        span_layout=span_layout,
        optimization_payload=merge_optimization_defaults(None),
        compression_rebar_required=compression_rebar_required,
    )


def _frame(source_name: str) -> EtabsFrameData:
    rows = tuple(
        EtabsStationRow(
            story="L1",
            label="B1",
            unique_name=source_name,
            design_sect="B150X750",
            station=station,
            as_top=0.0,
            as_bot=0.0,
            v_rebar_req=0.0,
            t_lng_req=0.0,
            t_trn_req=0.0,
            source_row=index,
        )
        for index, station in enumerate((0.0, 500.0, 1000.0), start=1)
    )
    return EtabsFrameData(unique_name=source_name, stations=rows)


def _tie_evaluation(
    *,
    longitudinal_mm: float,
    transverse_mm: float,
    width_mm: float,
    height_mm: float,
    spacing_mm: float = 100.0,
):
    return tie_rule_checks(
        scope=TieRuleScope.FULL,
        system="DMI",
        zone="NC",
        spacing_mm=spacing_mm,
        longitudinal_bar_diameter_mm=longitudinal_mm,
        tie_bar_diameter_mm=transverse_mm,
        width_mm=width_mm,
        height_mm=height_mm,
    )


class Phase3LongitudinalDetailingTests(unittest.TestCase):
    def test_d_remains_h_times_ratio_when_diameter_and_checkbox_change(self) -> None:
        baseline = _form_payload(db_bar="#3", compression_rebar_required=False)
        changed = _form_payload(db_bar="#8", compression_rebar_required=True)

        for payload in (baseline, changed):
            span = payload["beams"][0]["spans"][0]  # type: ignore[index]
            self.assertTrue(all(region["d_mm"] == 675.0 for region in span["regions"]))
            self.assertTrue(all(region["d_ratio"] == 0.9 for region in span["regions"]))
        changed_span = changed["beams"][0]["spans"][0]  # type: ignore[index]
        self.assertEqual(changed_span["longitudinal_bar_diameter_mm"], 25.4)
        self.assertTrue(changed_span["compression_rebar_required"])

    def test_span_checkbox_and_bar_flow_from_ui_shape_to_domain(self) -> None:
        raw = json.dumps(
            [
                {
                    "id": "S1",
                    "seismic": "1",
                    "gravity": "1",
                    "d_ratio": 0.9,
                    "longitudinal_bar": "#5",
                    "compression_rebar_required": True,
                    "support_left_mm": 0,
                    "support_right_mm": 0,
                    "regions": [
                        {"id": "R1", "from": 0.0, "to": 0.2, "type": "C"},
                        {"id": "R2", "from": 0.2, "to": 0.8, "type": "NC"},
                        {"id": "R3", "from": 0.8, "to": 1.0, "type": "C"},
                    ],
                }
            ]
        )
        span_layout = parse_span_layout_json(raw)
        payload = _form_payload(span_layout=span_layout)
        config = CaseConfig.model_validate(payload)
        span = config.beams[0].spans[0]

        self.assertEqual(span.longitudinal_bar_diameter_mm, 15.9)
        self.assertTrue(span.compression_rebar_required)
        self.assertFalse(span.longitudinal_bars_bundled)
        demands, errors = build_region_demands(
            beam_id="B1",
            beam_detailing="DMI",
            beam_cover_side_mm=40.0,
            beam_cover_top_mm=40.0,
            beam_cover_bottom_mm=40.0,
            beam_fc_mpa=28.0,
            beam_fy_mpa=420.0,
            span=span,
            seismic_frame=_frame("1"),
            gravity_frame=_frame("1"),
        )
        self.assertEqual(errors, [])
        self.assertTrue(all(item.compression_rebar_required for item in demands))
        self.assertTrue(all(item.longitudinal_bar_diameter_mm == 15.9 for item in demands))
        self.assertTrue(all(not item.longitudinal_bars_bundled for item in demands))

    def test_legacy_json_defaults_compression_to_false_and_preserves_db_bar(self) -> None:
        payload = _form_payload()
        span_payload = payload["beams"][0]["spans"][0]  # type: ignore[index]
        span_payload.pop("compression_rebar_required")
        span_payload.pop("longitudinal_bar_diameter_mm")
        span_payload["regions"][0]["db_bar"] = "#5"

        config = CaseConfig.model_validate(payload)

        self.assertFalse(config.beams[0].spans[0].compression_rebar_required)
        self.assertEqual(config.beams[0].spans[0].regions[0].db_bar, "#5")

    def test_legacy_beam_compression_flag_migrates_to_span(self) -> None:
        payload = _form_payload()
        beam = payload["beams"][0]  # type: ignore[index]
        beam["compression_rebar_required"] = True
        beam["spans"][0].pop("compression_rebar_required")

        config = CaseConfig.model_validate(payload)

        self.assertTrue(config.beams[0].spans[0].compression_rebar_required)

    def test_aci_9_7_6_4_2_is_not_applicable_without_required_compression_steel(self) -> None:
        check = check_transverse_reinforcement_size(
            scope=TieRuleScope.NONE,
            longitudinal_bar_diameter_mm=19.1,
            transverse_bar_diameter_mm=6.4,
        )
        self.assertEqual(check.status, RuleStatus.NOT_APPLICABLE)

    def test_aci_9_7_6_4_2_no_32_or_smaller_requires_no_10_transverse(self) -> None:
        passing = check_transverse_reinforcement_size(
            scope=TieRuleScope.FULL,
            longitudinal_bar_diameter_mm=32.3,
            transverse_bar_diameter_mm=9.5,
        )
        failing = check_transverse_reinforcement_size(
            scope=TieRuleScope.FULL,
            longitudinal_bar_diameter_mm=32.3,
            transverse_bar_diameter_mm=6.4,
        )
        self.assertEqual((passing.required_value, passing.status), (9.5, RuleStatus.PASS))
        self.assertAlmostEqual(failing.margin or 0.0, -3.1)
        self.assertEqual(failing.status, RuleStatus.FAIL)

    def test_aci_9_7_6_4_2_no_36_or_larger_requires_no_13_transverse(self) -> None:
        failing = check_transverse_reinforcement_size(
            scope=TieRuleScope.FULL,
            longitudinal_bar_diameter_mm=35.8,
            transverse_bar_diameter_mm=9.5,
        )
        passing = check_transverse_reinforcement_size(
            scope=TieRuleScope.FULL,
            longitudinal_bar_diameter_mm=35.8,
            transverse_bar_diameter_mm=12.7,
        )
        self.assertEqual((failing.required_value, failing.status), (12.7, RuleStatus.FAIL))
        self.assertEqual((passing.margin, passing.status), (0.0, RuleStatus.PASS))

    def test_bundled_bars_are_fixed_false_and_have_no_ui_control(self) -> None:
        payload = _form_payload()
        span = payload["beams"][0]["spans"][0]  # type: ignore[index]
        self.assertFalse(span["longitudinal_bars_bundled"])
        span["longitudinal_bars_bundled"] = True
        with self.assertRaises(ValidationError):
            CaseConfig.model_validate(payload)

        html = (ROOT / "app/ui/templates/ui.html").read_text(encoding="utf-8")
        javascript = (ROOT / "app/ui/static/ui.js").read_text(encoding="utf-8")
        self.assertNotIn('name="longitudinal_bars_bundled"', html)
        self.assertNotIn("span-longitudinal-bars-bundled", javascript)
        self.assertIn("span-compression-rebar-required", javascript)
        self.assertIn("span-longitudinal-bar", javascript)

    def test_ui_bar_catalog_reaches_no_36_transition(self) -> None:
        html = (ROOT / "app/ui/templates/ui.html").read_text(encoding="utf-8")
        javascript = (ROOT / "app/ui/static/ui.js").read_text(encoding="utf-8")

        self.assertIn("<option>#10</option><option>#11</option>", html)
        self.assertIn("<option>#10</option><option>#11</option>", javascript)

    def test_rule_registry_records_completed_and_deferred_tie_rules(self) -> None:
        registry = (
            ROOT / "references/codes/aci/ACI_318_25/IMPLEMENTED_RULES.yaml"
        ).read_text(encoding="utf-8")

        self.assertIn("ACI318_25_9_7_6_4_2_TRANSVERSE_SIZE", registry)
        self.assertIn("ACI318_25_9_7_6_4_3_SIXTEEN_DB_LONGITUDINAL", registry)
        self.assertIn("ACI318_25_9_7_6_4_4_LONGITUDINAL_BAR_ARRANGEMENT", registry)
        self.assertIn("ACI318_25_18_6_4_2_LATERAL_SUPPORT", registry)
        self.assertIn("Bundled longitudinal bars are outside module scope", registry)

    def test_aci_9_7_6_4_3_can_be_controlled_by_sixteen_db(self) -> None:
        limits, _ = _tie_evaluation(
            longitudinal_mm=9.5,
            transverse_mm=12.7,
            width_mm=300.0,
            height_mm=600.0,
        )
        controlling = select_controlling_spacing_limit(limits)
        self.assertEqual(controlling.check.rule_id, "ACI318_25_9_7_6_4_3_SIXTEEN_DB_LONGITUDINAL")
        self.assertEqual(controlling.maximum_mm, 152.0)

    def test_aci_9_7_6_4_3_can_be_controlled_by_forty_eight_db(self) -> None:
        limits, _ = _tie_evaluation(
            longitudinal_mm=35.8,
            transverse_mm=6.4,
            width_mm=600.0,
            height_mm=750.0,
        )
        controlling = select_controlling_spacing_limit(limits)
        self.assertEqual(controlling.check.rule_id, "ACI318_25_9_7_6_4_3_FORTY_EIGHT_DB_TRANSVERSE")
        self.assertAlmostEqual(controlling.maximum_mm, 307.2)

    def test_aci_9_7_6_4_3_can_be_controlled_by_least_beam_dimension(self) -> None:
        limits, _ = _tie_evaluation(
            longitudinal_mm=35.8,
            transverse_mm=12.7,
            width_mm=250.0,
            height_mm=750.0,
        )
        controlling = select_controlling_spacing_limit(limits)
        self.assertEqual(controlling.check.rule_id, "ACI318_25_9_7_6_4_3_LEAST_BEAM_DIMENSION")
        self.assertEqual(controlling.maximum_mm, 250.0)

    def test_tie_spacing_limit_participates_in_dynamic_s_max_real(self) -> None:
        scenario = DemandScenario(
            source="SEISMIC",
            station_mm=0.0,
            x_relative=0.5,
            region_id="R1",
            v_rebar_mm2_per_m=0.0,
            t_transverse_mm2_per_m=0.0,
            t_longitudinal_mm2=0.0,
            torsion_state="INACTIVE",
        )
        region = RegionDemand(
            beam_id="B1",
            span_id="S1",
            region_id="R1",
            region_type="NC",
            beam_detailing="DMI",
            d_mm=675.0,
            db_bar=None,
            min_branches=2,
            width_mm=600.0,
            height_mm=750.0,
            cover_side_mm=40.0,
            cover_top_mm=40.0,
            cover_bottom_mm=40.0,
            scenarios=(scenario,),
            fc_mpa=28.0,
            fy_mpa=420.0,
            compression_rebar_required=True,
            longitudinal_bar_diameter_mm=9.5,
            longitudinal_bars_bundled=False,
        )
        variables = VariablesConfig(
            E_bars=["#3"],
            G_bars=["#3"],
            G_counts=[0],
            longitudinal_bars=["#4"],
            longitudinal_bar_counts=[2],
        )

        domain = spacing_domain_for_region(region, variables, [0])
        selected = optimize_region_exhaustive(region, variables).selected

        self.assertEqual(domain[-1], 150)
        self.assertEqual(selected.spacing_mm, 150)
        self.assertEqual(
            selected.controlling_limit,
            "ACI318_25_9_7_6_4_3_SIXTEEN_DB_LONGITUDINAL",
        )

    def test_aci_9_7_6_4_4_remains_not_evaluated(self) -> None:
        _, checks = _tie_evaluation(
            longitudinal_mm=19.1,
            transverse_mm=9.5,
            width_mm=300.0,
            height_mm=600.0,
        )
        arrangement = next(check for check in checks if check.section == "9.7.6.4.4")
        self.assertEqual(arrangement.status, RuleStatus.NOT_EVALUATED)
        self.assertIn("positions", arrangement.applicability_reason)

    def test_des_lateral_support_geometry_remains_not_evaluated(self) -> None:
        _, checks = tie_rule_checks(
            scope=TieRuleScope.LATERAL_SUPPORT_ONLY,
            system="DES",
            zone="C",
            spacing_mm=100.0,
            longitudinal_bar_diameter_mm=19.1,
            tie_bar_diameter_mm=9.5,
            width_mm=300.0,
            height_mm=600.0,
        )
        support = next(check for check in checks if check.rule_id == "ACI318_25_18_6_4_2_LATERAL_SUPPORT")
        self.assertEqual(support.status, RuleStatus.NOT_EVALUATED)
        self.assertEqual(support.section, "18.6.4.2 and 25.7.2.3")

    def test_torsion_states_keep_phase2_contract(self) -> None:
        inactive = classify_torsion_state(0.0, 0.0)
        active = classify_torsion_state(10.0, 100.0)
        inconsistent = classify_torsion_state(10.0, 0.0)
        self.assertEqual((inactive, active, inconsistent), ("INACTIVE", "ACTIVE", "INCONSISTENT"))

        region = RegionDemand(
            beam_id="B1",
            span_id="S1",
            region_id="R1",
            region_type="NC",
            beam_detailing="DMI",
            d_mm=675.0,
            db_bar=None,
            min_branches=2,
            width_mm=300.0,
            height_mm=750.0,
            cover_side_mm=40.0,
            cover_top_mm=40.0,
            cover_bottom_mm=40.0,
            scenarios=(
                DemandScenario(
                    source="SEISMIC",
                    station_mm=0.0,
                    x_relative=0.0,
                    region_id="R1",
                    v_rebar_mm2_per_m=0.0,
                    t_transverse_mm2_per_m=0.0,
                    t_longitudinal_mm2=0.0,
                    torsion_state="INACTIVE",
                ),
            ),
            longitudinal_bar_diameter_mm=19.1,
        )
        candidate = evaluate_candidate(
            region,
            e_bar="#3",
            g_bar="#3",
            g_count=0,
            spacing_mm=100,
            long_bar=None,
            long_count=0,
            check_longitudinal=True,
        )
        self.assertIsNone(candidate.long_bar)
        self.assertEqual((candidate.long_count, candidate.long_provided), (0, 0.0))


if __name__ == "__main__":
    unittest.main()
