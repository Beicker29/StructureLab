"""Behavior captured before the repository cleanup (September 2026)."""
from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import patch

from starlette.requests import Request

from app.routers.jobs import save_job_selection_endpoint
from app.schemas.jobs import JobSelectionSaveRequest
from app.services.job_preview_service import _build_transverse_component_options
from rc_shear_torsion.design import optimize_region_exhaustive, optimize_region_ga
from tests.test_transverse_ranking import _ga_config, _region, _variables


class RefactoringContractTests(unittest.TestCase):
    def test_existing_catalog_import_paths_and_mass_results_remain_available(self) -> None:
        from rc_shear_torsion.design import (
            BAR_AREAS_MM2, BAR_MASS_KG_PER_M, bar_mass_kg_per_m, longitudinal_mass_kg_per_m,
        )
        from rc_shear_torsion.models import ALLOWED_BAR_LABELS, BAR_DIAMETERS_MM

        self.assertEqual(BAR_DIAMETERS_MM["#6"], 19.1)
        self.assertEqual(BAR_AREAS_MM2["#6"], 284.0)
        self.assertEqual(BAR_MASS_KG_PER_M["#6"], 2.235)
        self.assertEqual(bar_mass_kg_per_m("#6", 2), 4.47)
        self.assertEqual(longitudinal_mass_kg_per_m(284.0), 284.0 * 1000.0 * 7.85e-6)
        self.assertEqual(bar_mass_kg_per_m(None), 0.0)
        self.assertEqual(bar_mass_kg_per_m("unknown"), 0.0)
        self.assertEqual(bar_mass_kg_per_m("#6", 0), 0.0)
        self.assertNotIn("#14", ALLOWED_BAR_LABELS)
        self.assertIn("#14", BAR_DIAMETERS_MM)

    def test_empty_search_domains_keep_failure_details_and_counts(self) -> None:
        for missing_branches in (True, False):
            region = replace(_region(), beam_detailing="DMO", region_type="C", min_branches=4 if missing_branches else 2)
            variables = _variables()
            if not missing_branches:
                variables = variables.model_copy(update={"stirrup_spacing_project_max_mm": 50})
            outcomes = (
                optimize_region_exhaustive(region, variables),
                optimize_region_ga(region, _ga_config(variables)),
            )
            with self.subTest(missing_branches=missing_branches):
                self.assertEqual(outcomes[0].selected, outcomes[1].selected)
                self.assertEqual([o.method for o in outcomes], ["exhaustive", "genetic"])
                for outcome in outcomes:
                    self.assertEqual((outcome.evaluated_candidates, outcome.feasible_candidates), (0, 0))
                    self.assertEqual(outcome.failure_counts, {"input_fail": 1})
                    self.assertEqual(outcome.selected.failure_mode, "input_fail")
                    self.assertIn("No G_counts" if missing_branches else "No spacing candidate", outcome.selected.message)

    def test_preview_deduplicates_by_unrounded_weight_and_keeps_first_exact_tie(self) -> None:
        rows = [
            {"transverse_label": "1E #3 @ 110 mm", "weight_transverse_kg": 3.031},
            {"transverse_label": "1E #3 @ 130 mm", "weight_transverse_kg": 3.032},
            {"transverse_label": "1E #3 @ 110 mm", "weight_transverse_kg": 3.03, "stirrup_count": 4},
            {"transverse_label": "1E #3 @ 110 mm", "weight_transverse_kg": 3.03, "stirrup_count": 5},
            {"transverse_label": "unknown"},
        ]
        result = _build_transverse_component_options(rows)
        self.assertEqual([item["label"] for item in result], ["1E #3 @ 110 mm", "1E #3 @ 130 mm", "unknown"])
        self.assertEqual(result[0]["stirrup_count"], 4)
        self.assertEqual(result[0]["weight_kg"], 3.03)
        self.assertEqual(result[1]["spacing_mm"], 130.0)
        self.assertIsNone(result[2]["weight_kg"])
        self.assertEqual(_build_transverse_component_options(rows, max_items=0), result[:1])

    def test_preview_count_and_unit_weight_override_explicit_weight(self) -> None:
        result = _build_transverse_component_options([
            {"transverse_label": "1E #3 @ 130 mm", "stirrup_count": 4,
             "stirrup_unit_weight_kg": 0.75, "weight_transverse_kg": 99.0},
        ])
        self.assertEqual(result[0]["weight_kg"], 3.0)

    def test_selection_uses_exact_combination_weights_and_preserves_manual_choice(self) -> None:
        preview = {"spans": [{"span_id": "S1", "regions": [{"region_id": "R1", "options": [
            {"option": 1, "transverse_label": "T130", "longitudinal_label": "L",
             "weight_total_kg": 7.0, "weight_transverse_kg": 3.0, "weight_longitudinal_kg": 4.0},
            {"option": 2, "transverse_label": "T110", "longitudinal_label": "L",
             "weight_total_kg": 8.0, "weight_transverse_kg": 4.0, "weight_longitudinal_kg": 4.0},
        ]}]}]}
        payload = JobSelectionSaveRequest.model_validate({"selections": [
            {"span_id": "S1", "region_id": "R1", "option": 2},
        ]})
        request = Request({"type": "http", "scheme": "http", "server": ("testserver", 80), "path": "/", "headers": []})
        with (
            patch("app.routers.jobs.build_job_preview_payload", return_value=preview),
            patch("app.routers.jobs.save_selected_options_report", return_value={
                "artifact_name": "comparison.xlsx", "saved_regions": 1,
            }) as save,
        ):
            response = save_job_selection_endpoint("job", payload, request)
        row = save.call_args.kwargs["resolved_rows"][0]
        self.assertEqual((row["best_option"], row["selected_option"]), (1, 2))
        self.assertEqual(row["selected_transverse_label"], "T110")
        self.assertEqual(row["selected_weight_kg"], 8.0)
        self.assertEqual(row["difference_kg"], 1.0)
        self.assertEqual(row["difference_pct"], (1.0 / 7.0) * 100.0)
        self.assertEqual(response.artifact_url, "http://testserver/v1/jobs/job/artifacts/comparison.xlsx")
