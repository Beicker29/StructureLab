from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from rc_shear_torsion.design import (
    DemandScenario,
    RegionDemand,
    build_region_demands,
    evaluate_candidate,
    locate_region,
    optimize_region_exhaustive,
    optimize_region_ga,
)
from rc_shear_torsion.io import EtabsFrameData, EtabsStationRow
from rc_shear_torsion.models import CaseConfig, OptimizationConfig, SpanConfig, load_case_config


REPO_ROOT = Path(__file__).resolve().parents[1]


def _station(
    station: float,
    *,
    v_req: float,
    t_req: float,
    l_req: float,
) -> EtabsStationRow:
    return EtabsStationRow(
        story="L1",
        label="B1",
        unique_name="190",
        design_sect="B300x600",
        station=station,
        as_top=0.0,
        as_bot=0.0,
        v_rebar_req=v_req,
        t_lng_req=l_req,
        t_trn_req=t_req,
    )


def _single_region_span() -> SpanConfig:
    return SpanConfig.model_validate(
        {
            "id": "S1",
            "seismic": "190",
            "gravity": "190",
            "regions": [
                {
                    "id": "R1",
                    "from": 0.0,
                    "to": 1.0,
                    "type": "NC",
                    "d_mm": 500.0,
                    "db_bar": "#5",
                    "min_branches": 2,
                    "width_mm": 300.0,
                    "height_mm": 600.0,
                }
            ],
        }
    )


class Phase0CharacterizationTests(unittest.TestCase):
    def test_existing_case_json_loads_with_legacy_defaults(self) -> None:
        config = load_case_config(REPO_ROOT / "examples" / "case_0001" / "case.json")

        self.assertEqual(config.case_name, "case_0001")
        self.assertEqual(config.optimization.longitudinal_mode, "legacy_region_independent")
        self.assertIsNone(config.beams[0].spans[0].clear_length_mm)

    def test_case_config_round_trip_preserves_region_aliases(self) -> None:
        original = load_case_config(REPO_ROOT / "examples" / "case_0001" / "case.json")

        serialized = original.model_dump(mode="json", by_alias=True)
        restored = CaseConfig.model_validate(serialized)

        self.assertIn("from", serialized["beams"][0]["spans"][0]["regions"][0])
        self.assertNotIn("from_", serialized["beams"][0]["spans"][0]["regions"][0])
        self.assertEqual(restored, original)

    def test_region_assignment_uses_half_open_boundaries_and_includes_final_endpoint(self) -> None:
        span = SpanConfig.model_validate(
            {
                "id": "S1",
                "seismic": "190",
                "gravity": "190",
                "regions": [
                    {"id": "R1", "from": 0.0, "to": 0.5, "type": "C"},
                    {"id": "R2", "from": 0.5, "to": 1.0, "type": "NC"},
                ],
            }
        )

        self.assertEqual(locate_region(span.regions, 0.0).id, "R1")
        self.assertEqual(locate_region(span.regions, 0.499999).id, "R1")
        self.assertEqual(locate_region(span.regions, 0.5).id, "R2")
        self.assertEqual(locate_region(span.regions, 1.0).id, "R2")

    def test_region_demand_preserves_physical_scenarios_without_artificial_envelope(self) -> None:
        seismic_rows = (
            _station(0.0, v_req=900.0, t_req=80.0, l_req=400.0),
            _station(1500.0, v_req=650.0, t_req=240.0, l_req=500.0),
            _station(3000.0, v_req=700.0, t_req=150.0, l_req=620.0),
        )

        demands, errors = build_region_demands(
            beam_id="B1",
            beam_detailing="DMO",
            beam_cover_side_mm=40.0,
            beam_cover_top_mm=40.0,
            beam_cover_bottom_mm=40.0,
            beam_fc_mpa=28.0,
            beam_fy_mpa=420.0,
            span=_single_region_span(),
            seismic_frame=EtabsFrameData(unique_name="190", stations=seismic_rows),
            gravity_frame=EtabsFrameData(unique_name="190", stations=tuple()),
        )

        self.assertEqual(errors, [])
        physical_vectors = {
            (
                scenario.v_rebar_mm2_per_m,
                scenario.t_transverse_mm2_per_m,
                scenario.t_longitudinal_mm2,
            )
            for scenario in demands[0].scenarios
        }
        self.assertEqual(
            physical_vectors,
            {(900.0, 80.0, 400.0), (650.0, 240.0, 500.0), (700.0, 150.0, 620.0)},
        )
        self.assertNotIn((900.0, 240.0, 620.0), physical_vectors)

    def test_regional_ga_and_exhaustive_search_use_the_same_candidate_evaluator(self) -> None:
        region = RegionDemand(
            beam_id="B1",
            span_id="S1",
            region_id="R1",
            region_type="NC",
            beam_detailing="DES",
            d_mm=None,
            db_bar=None,
            min_branches=None,
            width_mm=None,
            height_mm=None,
            cover_side_mm=None,
            cover_top_mm=None,
            cover_bottom_mm=None,
            scenarios=(
                DemandScenario(
                    source="SEISMIC",
                    station_mm=0.0,
                    x_relative=0.0,
                    region_id="R1",
                    v_rebar_mm2_per_m=100.0,
                    t_transverse_mm2_per_m=0.0,
                    t_longitudinal_mm2=0.0,
                    torsion_state="INACTIVE",
                    source_row=1,
                ),
            ),
            region_length_mm=1000.0,
        )
        optimization = OptimizationConfig.model_validate(
            {
                "enabled": True,
                "objective": "min_weight",
                "variables": {
                    "E_bars": ["#3"],
                    "G_bars": ["#3"],
                    "G_counts": [0],
                    "stirrup_spacing_mm": [100],
                    "longitudinal_bars": ["#4"],
                    "longitudinal_bar_counts": [2],
                },
                "genetic_algorithm": {
                    "population_size": 4,
                    "generations": 1,
                    "crossover_rate": 0.0,
                    "mutation_rate": 0.0,
                    "elite_count": 1,
                },
            }
        )

        with patch("rc_shear_torsion.design.evaluate_candidate", wraps=evaluate_candidate) as exhaustive_evaluator:
            exhaustive = optimize_region_exhaustive(region, optimization.variables)
        with patch("rc_shear_torsion.design.evaluate_candidate", wraps=evaluate_candidate) as ga_evaluator:
            genetic = optimize_region_ga(region, optimization)

        self.assertGreater(exhaustive_evaluator.call_count, 0)
        self.assertGreater(ga_evaluator.call_count, 0)
        self.assertEqual(genetic.selected, exhaustive.selected)


if __name__ == "__main__":
    unittest.main()
