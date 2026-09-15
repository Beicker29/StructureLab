from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.services.case_service import merge_optimization_defaults
from app.services.job_preview_service import (
    _build_region_additional_options_by_base,
    _build_span_longitudinal_base_options,
    _build_span_longitudinal_option_sets,
    _expand_span_coupled_options,
)
from rc_shear_torsion.design import DemandScenario, RegionDemand, classify_torsion_state
from rc_shear_torsion.models import OptimizationConfig
from rc_shear_torsion.engine import run_case
from rc_shear_torsion.span_coupled import (
    _evaluate_longitudinal_region,
    longitudinal_layer_spacing_mm,
    longitudinal_vertical_range_mm,
    minimum_longitudinal_count_for_distribution,
    minimum_torsion_longitudinal_bar_diameter_mm,
    optimize_span_coupled,
    SpanOptimizationOutcome,
)


def _region(
    region_id: str = "R1",
    *,
    t_longitudinal_mm2: float = 668.0,
    height_mm: float = 750.0,
    d_mm: float = 675.0,
    region_length_mm: float = 1000.0,
) -> RegionDemand:
    t_transverse = 10.0 if t_longitudinal_mm2 > 0.0 else 0.0
    scenario = DemandScenario(
        source="SEISMIC",
        station_mm=0.0,
        x_relative=0.5,
        region_id=region_id,
        v_rebar_mm2_per_m=0.0,
        t_transverse_mm2_per_m=t_transverse,
        t_longitudinal_mm2=t_longitudinal_mm2,
        torsion_state=classify_torsion_state(t_transverse, t_longitudinal_mm2),
    )
    return RegionDemand(
        beam_id="B1",
        span_id="S1",
        region_id=region_id,
        region_type="NC",
        beam_detailing="DMI",
        d_mm=d_mm,
        db_bar=None,
        min_branches=2,
        width_mm=250.0,
        height_mm=height_mm,
        cover_side_mm=40.0,
        cover_top_mm=40.0,
        cover_bottom_mm=40.0,
        scenarios=(scenario,),
        fc_mpa=28.0,
        fy_mpa=420.0,
        region_length_mm=region_length_mm,
        d_source="SPAN_RATIO",
        d_ratio=d_mm / height_mm,
    )


def _optimization() -> OptimizationConfig:
    payload = merge_optimization_defaults(
        {
            "enabled": True,
            "longitudinal_mode": "span_coupled",
            "variables": {
                "E_bars": ["#3"],
                "G_bars": ["#3"],
                "G_counts": [0],
                "stirrup_spacing_mm": [190],
                "longitudinal_bars": ["#4", "#5"],
                "longitudinal_bar_counts": [2, 4, 6],
            },
            "genetic_algorithm": {
                "population_size": 8,
                "generations": 2,
                "elite_count": 2,
            },
        }
    )
    return OptimizationConfig.model_validate(payload)


def _option_row(result, option: int) -> dict:
    base_label = (
        f"{result.base_long_count} x {result.base_long_bar}"
        if result.base_long_bar and result.base_long_count
        else "no se requiere"
    )
    additional_label = (
        f"{result.extra_long_count} x {result.extra_long_bar}"
        if result.extra_long_bar and result.extra_long_count
        else "no se requiere"
    )
    return {
        "option": option,
        "base_longitudinal_label": base_label,
        "additional_longitudinal_label": additional_label,
        "longitudinal_label": result.longitudinal_arrangement_label,
        "base_long_bar": result.base_long_bar,
        "base_long_count": result.base_long_count,
        "extra_long_bar": result.extra_long_bar,
        "extra_long_count": result.extra_long_count,
        "weight_base_kg": 0.0,
        "weight_additional_kg": 0.0,
        "weight_longitudinal_kg": result.longitudinal_weight_kg_per_m,
        "weight_transverse_kg": 0.0,
        "weight_total_kg": result.longitudinal_weight_kg_per_m,
    }


class PrePhase4LongitudinalAuditTests(unittest.TestCase):
    def test_vertical_range_and_spacing_for_real_750_mm_case(self) -> None:
        region = _region()

        self.assertEqual(longitudinal_vertical_range_mm(region), 600.0)
        self.assertEqual(longitudinal_layer_spacing_mm(region, 0), 600.0)
        self.assertEqual(longitudinal_layer_spacing_mm(region, 2), 300.0)
        self.assertEqual(longitudinal_layer_spacing_mm(region, 4), 200.0)
        self.assertEqual(longitudinal_layer_spacing_mm(region, 6), 150.0)
        self.assertEqual(minimum_longitudinal_count_for_distribution(region), 2)

    def test_same_demand_needs_two_no4_after_4_no4_but_zero_after_4_no5(self) -> None:
        region = _region(t_longitudinal_mm2=668.0)

        four_no4 = _evaluate_longitudinal_region(
            region,
            base_long_bar="#4",
            base_long_count=4,
            extra_long_bar="",
            extra_long_count=0,
            transverse_spacing_mm=190.0,
        )
        six_no4 = _evaluate_longitudinal_region(
            region,
            base_long_bar="#4",
            base_long_count=4,
            extra_long_bar="#4",
            extra_long_count=2,
            transverse_spacing_mm=190.0,
        )
        four_no5 = _evaluate_longitudinal_region(
            region,
            base_long_bar="#5",
            base_long_count=4,
            extra_long_bar="",
            extra_long_count=0,
            transverse_spacing_mm=190.0,
        )

        self.assertFalse(four_no4[0])
        self.assertIn("Along_real < TLngRebar", four_no4[1])
        self.assertEqual(longitudinal_layer_spacing_mm(region, 4), 200.0)
        self.assertTrue(six_no4[0])
        self.assertEqual((six_no4[2], six_no4[3], six_no4[4]), (774.0, 3, 150.0))
        self.assertTrue(four_no5[0])
        self.assertEqual((four_no5[2], four_no5[3], four_no5[4]), (796.0, 2, 200.0))

    def test_area_can_pass_while_distribution_requires_additional_bars(self) -> None:
        region = _region(t_longitudinal_mm2=300.0, height_mm=1125.0, d_mm=1012.5)

        base_only = _evaluate_longitudinal_region(
            region,
            base_long_bar="#5",
            base_long_count=2,
            extra_long_bar="",
            extra_long_count=0,
            transverse_spacing_mm=190.0,
        )
        with_distribution_bars = _evaluate_longitudinal_region(
            region,
            base_long_bar="#5",
            base_long_count=2,
            extra_long_bar="#4",
            extra_long_count=2,
            transverse_spacing_mm=190.0,
        )

        self.assertFalse(base_only[0])
        self.assertGreaterEqual(base_only[2], 300.0)
        self.assertTrue(with_distribution_bars[0])
        self.assertEqual(with_distribution_bars[4], 300.0)

    def test_no4_satisfies_minimum_diameter_at_190_mm(self) -> None:
        region = _region(t_longitudinal_mm2=500.0)

        self.assertEqual(minimum_torsion_longitudinal_bar_diameter_mm(190.0), 10.0)
        accepted = _evaluate_longitudinal_region(
            region,
            base_long_bar="#5",
            base_long_count=4,
            extra_long_bar="#4",
            extra_long_count=2,
            transverse_spacing_mm=190.0,
        )
        too_small = _evaluate_longitudinal_region(
            region,
            base_long_bar="#3",
            base_long_count=4,
            extra_long_bar="#4",
            extra_long_count=2,
            transverse_spacing_mm=190.0,
        )

        self.assertTrue(accepted[0])
        self.assertFalse(too_small[0])
        self.assertIn("9.7.5.2", too_small[1])

    def test_optimizer_catalog_contains_conditional_minimum_for_every_region_and_base(self) -> None:
        regions = [_region(region_id) for region_id in ("R1", "R2", "R3")]
        outcome = optimize_span_coupled(
            regions,
            _optimization(),
            span_length_mm=3000.0,
            top_n=20,
        )

        for region in regions:
            options = outcome.alternatives_by_region[("S1", region.region_id)]
            by_base = {}
            for option in options:
                key = (option.base_long_bar, option.base_long_count)
                by_base.setdefault(key, []).append(option)

            no4 = min(by_base[("#4", 4)], key=lambda item: item.longitudinal_weight_kg_per_m)
            no5 = min(by_base[("#5", 4)], key=lambda item: item.longitudinal_weight_kg_per_m)
            self.assertEqual((no4.extra_long_bar, no4.extra_long_count), ("#4", 2))
            self.assertIsNone(no5.extra_long_bar)
            self.assertIsNone(no5.extra_long_count)

    def test_preview_base_change_uses_recalculated_non_stale_region_options(self) -> None:
        regions = [_region(region_id) for region_id in ("R1", "R2", "R3")]
        outcome = optimize_span_coupled(
            regions,
            _optimization(),
            span_length_mm=3000.0,
            top_n=20,
        )
        region_rows = []
        for region in regions:
            results = outcome.alternatives_by_region[("S1", region.region_id)]
            region_rows.append(
                {
                    "region_id": region.region_id,
                    "length_mm": region.region_length_mm,
                    "longitudinal_mode": "span_coupled",
                    "options": [_option_row(result, index) for index, result in enumerate(results, 1)],
                }
            )

        base_options = _build_span_longitudinal_base_options(region_rows)
        base_values = {item["base_label"]: item["value"] for item in base_options}
        self.assertIn("4 x #4", base_values)
        self.assertIn("4 x #5", base_values)

        for region_row in region_rows:
            by_base = _build_region_additional_options_by_base(region_row, base_options)
            self.assertEqual(by_base[base_values["4 x #4"]][0]["label"], "2 x #4")
            self.assertEqual(by_base[base_values["4 x #5"]][0]["label"], "no se requiere")

        sets = _build_span_longitudinal_option_sets(region_rows, base_options)
        no5_set = next(item for item in sets if item["base_label"] == "4 x #5")
        self.assertTrue(all(item["additional_label"] == "no se requiere" for item in no5_set["regions"]))

    def test_inactive_torsion_keeps_effective_longitudinal_reinforcement_zero(self) -> None:
        inactive = _region(t_longitudinal_mm2=0.0)
        outcome = optimize_span_coupled(
            [inactive],
            _optimization(),
            span_length_mm=1000.0,
            top_n=10,
        )
        result = outcome.results[0]

        self.assertEqual(result.long_count, 0)
        self.assertIsNone(result.long_bar)
        self.assertEqual(result.long_provided_mm2_override, 0.0)
        self.assertEqual(result.longitudinal_arrangement_label, "no se requiere")

    def test_preview_checks_minimum_diameter_against_selected_transverse_spacing(self) -> None:
        longitudinal_rows = [
            {
                "option": 1,
                "base_long_bar": "#4",
                "base_long_count": 4,
                "extra_long_bar": "",
                "extra_long_count": 0,
                "weight_total_kg": 1.0,
                "weight_longitudinal_kg": 1.0,
            }
        ]
        transverse_options = [
            {"label": "1E #3 @ 190 mm", "spacing_mm": 190.0, "weight_kg": 1.0},
            {"label": "1E #3 @ 330 mm", "spacing_mm": 330.0, "weight_kg": 0.8},
        ]

        expanded = _expand_span_coupled_options(
            longitudinal_rows=longitudinal_rows,
            transverse_options=transverse_options,
        )

        self.assertEqual([item["transverse_label"] for item in expanded], ["1E #3 @ 190 mm"])

        rejected = _expand_span_coupled_options(
            longitudinal_rows=longitudinal_rows,
            transverse_options=[
                {"label": "1E #3 @ 330 mm", "spacing_mm": 330.0, "weight_kg": 0.8}
            ],
        )
        self.assertEqual(rejected, [])

    def test_engine_optimizes_each_span_independently(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source_case = json.loads(
            (root / "examples" / "case_0001" / "case.json").read_text(encoding="utf-8")
        )
        source_case["inputs"]["seismic_excel"] = str(
            (root / "examples" / "case_0001" / "sismo.xlsx").resolve()
        )
        source_case["inputs"]["gravity_excel"] = str(
            (root / "examples" / "case_0001" / "gravedad.xlsx").resolve()
        )
        first_span = source_case["beams"][0]["spans"][0]
        second_span = json.loads(json.dumps(first_span))
        second_span["id"] = "B1.2"
        source_case["beams"][0]["spans"] = [first_span, second_span]
        source_case["optimization"]["longitudinal_mode"] = "span_coupled"

        observed_span_ids: list[set[str]] = []

        def capture(demands, optimization, **kwargs):
            observed_span_ids.append({demand.span_id for demand in demands})
            return SpanOptimizationOutcome(
                results=[],
                alternatives_by_region={},
                method="audit_stub",
                evaluated_candidates=0,
                feasible_candidates=0,
                failure_counts={},
            )

        runtime_root = root / ".tmp_test_runtime"
        runtime_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runtime_root) as temp_dir:
            temp = Path(temp_dir)
            case_path = temp / "case.json"
            case_path.write_text(json.dumps(source_case), encoding="utf-8")
            with patch("rc_shear_torsion.engine.optimize_span_coupled", side_effect=capture):
                run_case(case_path, temp / "results")

        self.assertEqual(len(observed_span_ids), 2)
        self.assertEqual(observed_span_ids, [{"B1.1"}, {"B1.2"}])


if __name__ == "__main__":
    unittest.main()
