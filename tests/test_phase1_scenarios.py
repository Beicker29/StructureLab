from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook
from pydantic import ValidationError

from rc_shear_torsion.design import (
    DemandScenario,
    RegionDemand,
    build_region_demands,
    classify_torsion_state,
    evaluate_candidate,
)
from rc_shear_torsion.io import EtabsFrameData, EtabsStationRow, read_etabs_excel
from rc_shear_torsion.models import CaseConfig, SpanConfig
from rc_shear_torsion.tolerances import torsion_zero_tolerance


def _row(
    station: float,
    v: float,
    t_transverse: float,
    t_longitudinal: float,
    *,
    source_row: int | None = None,
) -> EtabsStationRow:
    return EtabsStationRow(
        story="L1",
        label="B1",
        unique_name="190",
        design_sect="B300x600",
        station=station,
        as_top=0.0,
        as_bot=0.0,
        v_rebar_req=v,
        t_lng_req=t_longitudinal,
        t_trn_req=t_transverse,
        source_row=source_row,
    )


def _scenario(
    station: float,
    v: float,
    t_transverse: float,
    t_longitudinal: float,
    *,
    source: str = "SEISMIC",
    region_id: str = "R1",
    source_row: int = 1,
) -> DemandScenario:
    return DemandScenario(
        source=source,  # type: ignore[arg-type]
        station_mm=station,
        x_relative=station / 3000.0,
        region_id=region_id,
        v_rebar_mm2_per_m=v,
        t_transverse_mm2_per_m=t_transverse,
        t_longitudinal_mm2=t_longitudinal,
        torsion_state=classify_torsion_state(t_transverse, t_longitudinal),
        source_row=source_row,
    )


def _region(*scenarios: DemandScenario, detailing: str = "DMI") -> RegionDemand:
    return RegionDemand(
        beam_id="B1",
        span_id="S1",
        region_id="R1",
        region_type="NC",
        beam_detailing=detailing,  # type: ignore[arg-type]
        d_mm=None,
        db_bar=None,
        min_branches=None,
        width_mm=None,
        height_mm=None,
        cover_side_mm=None,
        cover_top_mm=None,
        cover_bottom_mm=None,
        scenarios=tuple(scenarios),
        region_length_mm=1000.0,
    )


def _span() -> SpanConfig:
    return SpanConfig.model_validate(
        {
            "id": "S1",
            "seismic": "190",
            "gravity": "190",
            "regions": [
                {"id": "R1", "from": 0.0, "to": 0.5, "type": "NC"},
                {"id": "R2", "from": 0.5, "to": 1.0, "type": "NC"},
            ],
        }
    )


def _case_payload(*, detailing: str | None = None) -> dict[str, object]:
    beam: dict[str, object] = {
        "beam_id": "B1",
        "spans": [
            {
                "id": "S1",
                "seismic": "190",
                "gravity": "190",
                "regions": [{"id": "R1", "from": 0.0, "to": 1.0, "type": "NC"}],
            }
        ],
    }
    if detailing is not None:
        beam["detailing"] = detailing
    return {
        "case_name": "compatibility",
        "inputs": {"seismic_excel": "s.xlsx", "gravity_excel": "g.xlsx", "sheet_name": "data"},
        "units": {"rebar_per_length": "mm2/m"},
        "beams": [beam],
        "optimization": {
            "enabled": False,
            "objective": "min_weight",
            "variables": {
                "E_bars": ["#3"],
                "G_bars": ["#3"],
                "G_counts": [0],
                "stirrup_spacing_mm": [100],
                "longitudinal_bars": ["#5"],
                "longitudinal_bar_counts": [4],
            },
            "genetic_algorithm": {
                "population_size": 4,
                "generations": 1,
                "crossover_rate": 0.0,
                "mutation_rate": 0.0,
                "elite_count": 1,
            },
        },
    }


class Phase1ScenarioTests(unittest.TestCase):
    def test_sources_with_different_stations_are_preserved_and_assigned_once(self) -> None:
        seismic = EtabsFrameData(
            unique_name="190",
            stations=(
                _row(0.0, 10.0, 2.0, 3.0, source_row=11),
                _row(500.0, 20.0, 4.0, 5.0, source_row=12),
                _row(1000.0, 30.0, 6.0, 7.0, source_row=13),
            ),
        )
        gravity = EtabsFrameData(
            unique_name="190",
            stations=(
                _row(250.0, 40.0, 8.0, 9.0, source_row=21),
                _row(750.0, 50.0, 10.0, 11.0, source_row=22),
            ),
        )

        demands, errors = build_region_demands(
            beam_id="B1",
            beam_detailing="DMI",
            beam_cover_side_mm=None,
            beam_cover_top_mm=None,
            beam_cover_bottom_mm=None,
            beam_fc_mpa=None,
            beam_fy_mpa=None,
            span=_span(),
            seismic_frame=seismic,
            gravity_frame=gravity,
        )

        self.assertEqual(errors, [])
        scenarios = [item for demand in demands for item in demand.scenarios]
        self.assertEqual(len(scenarios), 5)
        self.assertEqual(len({(item.source, item.source_row) for item in scenarios}), 5)
        self.assertEqual(
            {(item.source, item.station_mm, item.region_id) for item in scenarios},
            {
                ("SEISMIC", 0.0, "R1"),
                ("SEISMIC", 500.0, "R2"),
                ("SEISMIC", 1000.0, "R2"),
                ("GRAVITY", 250.0, "R1"),
                ("GRAVITY", 750.0, "R2"),
            },
        )
        gravity_first = next(item for item in scenarios if item.source_row == 21)
        self.assertEqual(
            (
                gravity_first.source,
                gravity_first.station_mm,
                gravity_first.v_rebar_mm2_per_m,
                gravity_first.t_transverse_mm2_per_m,
                gravity_first.t_longitudinal_mm2,
            ),
            ("GRAVITY", 250.0, 40.0, 8.0, 9.0),
        )

    def test_torsion_states_and_tolerance_boundary(self) -> None:
        tol = torsion_zero_tolerance
        self.assertEqual(classify_torsion_state(0.0, 0.0), "INACTIVE")
        self.assertEqual(classify_torsion_state(tol, tol), "INACTIVE")
        self.assertEqual(classify_torsion_state(tol * 2.0, tol * 2.0), "ACTIVE")
        self.assertEqual(classify_torsion_state(tol * 2.0, tol), "INCONSISTENT")
        self.assertEqual(classify_torsion_state(tol, tol * 2.0), "INCONSISTENT")

    def test_inconsistent_torsion_is_traceable_input_failure(self) -> None:
        inconsistent = _scenario(1500.0, 100.0, 10.0, 0.0, source_row=47)
        candidate = evaluate_candidate(
            _region(inconsistent),
            e_bar="#3",
            g_bar="#3",
            g_count=0,
            spacing_mm=100,
            long_bar="#5",
            long_count=4,
            check_longitudinal=True,
        )
        self.assertEqual(candidate.failure_mode, "input_fail")
        self.assertIn("station_mm=1500.0", candidate.message)
        self.assertIn("source_row=47", candidate.message)

    def test_candidate_checks_every_physical_scenario_without_synthetic_vector(self) -> None:
        scenarios = (
            _scenario(0.0, 900.0, 80.0, 400.0, source_row=1),
            _scenario(1500.0, 650.0, 240.0, 500.0, source_row=2),
            _scenario(3000.0, 700.0, 150.0, 620.0, source_row=3),
        )
        demand = _region(*scenarios)
        candidate = evaluate_candidate(
            demand,
            e_bar="#3",
            g_bar="#3",
            g_count=0,
            spacing_mm=120,
            long_bar="#5",
            long_count=4,
            check_longitudinal=True,
        )

        self.assertEqual(candidate.status, "ok")
        self.assertNotIn(
            (900.0, 240.0, 620.0),
            {
                (
                    item.v_rebar_mm2_per_m,
                    item.t_transverse_mm2_per_m,
                    item.t_longitudinal_mm2,
                )
                for item in demand.scenarios
            },
        )

        failing = evaluate_candidate(
            _region(*scenarios, _scenario(2000.0, 1100.0, 100.0, 500.0, source_row=4)),
            e_bar="#3",
            g_bar="#3",
            g_count=0,
            spacing_mm=120,
            long_bar="#5",
            long_count=4,
            check_longitudinal=True,
        )
        self.assertEqual(failing.status, "fail")
        self.assertEqual(failing.failure_mode, "shear_fail")
        self.assertIn("source_row=4", failing.message)

    def test_different_scenarios_control_each_check(self) -> None:
        demand = _region(
            _scenario(0.0, 0.0, 300.0, 100.0, source_row=1),
            _scenario(1500.0, 1000.0, 100.0, 200.0, source="GRAVITY", source_row=2),
            _scenario(3000.0, 0.0, 50.0, 600.0, source_row=3),
        )
        self.assertEqual(demand.governing_t_transverse_scenario.station_mm, 0.0)
        self.assertEqual(demand.governing_combined_scenario.station_mm, 1500.0)
        self.assertEqual(demand.governing_combined_scenario.source, "GRAVITY")
        self.assertEqual(demand.governing_longitudinal_scenario.station_mm, 3000.0)
        self.assertEqual(demand.governing_station, 1500.0)

    def test_duplicate_etabs_rows_are_not_component_enveloped(self) -> None:
        runtime_root = Path(__file__).resolve().parents[1] / ".tmp_test_runtime"
        runtime_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runtime_root) as temp_dir:
            path = Path(temp_dir) / "duplicates.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "data"
            sheet.append(
                [
                    "Story",
                    "Label",
                    "UniqueName",
                    "DesignSect",
                    "Station",
                    "AsTop",
                    "AsBot",
                    "VRebar",
                    "TLngRebar",
                    "TTrnRebar",
                ]
            )
            sheet.append(["L1", "B1", "190", "B", 0.0, 0.0, 0.0, 900.0, 400.0, 80.0])
            sheet.append(["L1", "B1", "190", "B", 0.0, 0.0, 0.0, 650.0, 500.0, 240.0])
            workbook.save(path)

            source = read_etabs_excel(
                source_name="seismic",
                excel_path=path,
                sheet_name="data",
                rebar_per_length_factor=1.0,
            )

        rows = source.by_unique_name["190"].stations
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            {(row.v_rebar_req, row.t_trn_req, row.t_lng_req) for row in rows},
            {(900.0, 80.0, 400.0), (650.0, 240.0, 500.0)},
        )
        self.assertEqual({row.source_row for row in rows}, {2, 3})
        self.assertTrue(any("semantics are ambiguous" in warning for warning in source.warnings))

    def test_old_contract_defaults_and_dmi_are_accepted(self) -> None:
        old_config = CaseConfig.model_validate(_case_payload())
        self.assertEqual(old_config.beams[0].detailing, "DES")
        self.assertFalse(old_config.compression_rebar_required)

        dmi_config = CaseConfig.model_validate(_case_payload(detailing="DMI"))
        self.assertEqual(dmi_config.beams[0].detailing, "DMI")
        self.assertFalse(dmi_config.compression_rebar_required)

        serialized = dmi_config.model_dump(mode="python")
        self.assertEqual(serialized["beams"][0]["detailing"], "DMI")
        self.assertEqual(
            CaseConfig.model_validate(serialized).beams[0].detailing,
            "DMI",
        )

    def test_unknown_detailing_system_remains_invalid(self) -> None:
        with self.assertRaises(ValidationError):
            CaseConfig.model_validate(_case_payload(detailing="XYZ"))


if __name__ == "__main__":
    unittest.main()
