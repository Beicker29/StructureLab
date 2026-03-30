from __future__ import annotations

import io
import json
import os
import time
import unittest
from unittest.mock import patch
from pathlib import Path
import shutil
from zipfile import ZipFile

from fastapi.testclient import TestClient


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.storage_dir = cls.repo_root / ".tmp_api_storage"
        if cls.storage_dir.exists():
            shutil.rmtree(cls.storage_dir, ignore_errors=True)
        cls.storage_dir.mkdir(parents=True, exist_ok=True)

        os.environ["APP_STORAGE_DIR"] = str(cls.storage_dir)
        os.environ.pop("APP_API_KEY", None)

        from app.core.config import get_settings

        get_settings.cache_clear()
        from app.main import app

        cls.client = TestClient(app)
        cls.case_json = cls.repo_root / "examples" / "case_0001" / "case.json"
        cls.seismic_excel = cls.repo_root / "examples" / "case_0001" / "sismo.xlsx"
        cls.gravity_excel = cls.repo_root / "examples" / "case_0001" / "gravedad.xlsx"
        geometry_upper = cls.repo_root / "examples" / "case_0001" / "Geometria.xlsx"
        geometry_lower = cls.repo_root / "examples" / "case_0001" / "geometria.xlsx"
        cls.geometry_excel = geometry_upper if geometry_upper.exists() else geometry_lower

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.storage_dir, ignore_errors=True)

    def _create_job(self, case_content: bytes | None = None) -> str:
        if case_content is None:
            case_content = self.case_json.read_bytes()

        with (
            io.BytesIO(case_content) as case_stream,
            self.seismic_excel.open("rb") as seismic_stream,
            self.gravity_excel.open("rb") as gravity_stream,
        ):
            response = self.client.post(
                "/v1/jobs",
                files={
                    "case_json": ("case.json", case_stream, "application/json"),
                    "seismic_excel": ("sismo.xlsx", seismic_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                    "gravity_excel": ("gravedad.xlsx", gravity_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                },
            )

        self.assertEqual(response.status_code, 202, response.text)
        return response.json()["job_id"]

    def _wait_terminal_status(self, job_id: str, timeout_seconds: float = 120.0) -> dict:
        deadline = time.time() + timeout_seconds
        last_payload: dict | None = None
        while time.time() < deadline:
            response = self.client.get(f"/v1/jobs/{job_id}")
            self.assertEqual(response.status_code, 200, response.text)
            payload = response.json()
            last_payload = payload
            if payload["status"] in {"completed", "failed"}:
                return payload
            time.sleep(0.25)
        self.fail(f"El job {job_id} no termino a tiempo. Ultimo estado: {last_payload}")

    def _write_job_meta(self, job_id: str, status: str, artifacts: dict[str, str] | None = None) -> None:
        job_dir = self.storage_dir / "jobs" / job_id
        input_dir = job_dir / "input"
        output_root = job_dir / "output"
        input_dir.mkdir(parents=True, exist_ok=True)
        output_root.mkdir(parents=True, exist_ok=True)
        meta = {
            "job_id": job_id,
            "status": status,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "started_at": None,
            "finished_at": None,
            "error": None,
            "paths": {
                "job_dir": str(job_dir),
                "input_dir": str(input_dir),
                "output_root": str(output_root),
                "case_json": str(input_dir / "case.json"),
                "seismic_excel": str(input_dir / "seismic.xlsx"),
                "gravity_excel": str(input_dir / "gravity.xlsx"),
            },
            "output_dir": None,
            "artifacts": artifacts or {},
            "zip_path": None,
        }
        (job_dir / "job.json").write_text(json.dumps(meta), encoding="utf-8")

    def test_healthcheck(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("service", payload)

    def test_ui_page_available(self) -> None:
        response = self.client.get("/ui")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("Configuracion", response.text)
        self.assertIn("Entrada del modelo", response.text)
        self.assertIn("Resultados", response.text)
        self.assertIn("Reportes", response.text)
        self.assertIn("beam-elevation-container", response.text)
        self.assertIn("Crear y ejecutar job", response.text)
        self.assertIn("Refuerzo transversal", response.text)

    def test_ui_static_assets_available(self) -> None:
        css_response = self.client.get("/ui/static/ui.css")
        self.assertEqual(css_response.status_code, 200, css_response.text)
        self.assertIn("text/css", css_response.headers.get("content-type", ""))

        js_response = self.client.get("/ui/static/ui.js")
        self.assertEqual(js_response.status_code, 200, js_response.text)
        self.assertIn("javascript", js_response.headers.get("content-type", ""))

        payload_response = self.client.get("/ui/static/ui_payload.js")
        self.assertEqual(payload_response.status_code, 200, payload_response.text)
        self.assertIn("javascript", payload_response.headers.get("content-type", ""))

        status_response = self.client.get("/ui/static/ui_status.js")
        self.assertEqual(status_response.status_code, 200, status_response.text)
        self.assertIn("javascript", status_response.headers.get("content-type", ""))

        svg_response = self.client.get("/ui/static/ui_svg.js")
        self.assertEqual(svg_response.status_code, 200, svg_response.text)
        self.assertIn("javascript", svg_response.headers.get("content-type", ""))

    def test_job_flow_success_and_download(self) -> None:
        job_id = self._create_job()
        final_status = self._wait_terminal_status(job_id)
        self.assertEqual(final_status["status"], "completed", final_status)

        download_response = self.client.get(f"/v1/jobs/{job_id}/download")
        self.assertEqual(download_response.status_code, 200, download_response.text)
        self.assertEqual(download_response.headers.get("content-type"), "application/zip")

        with ZipFile(io.BytesIO(download_response.content)) as zip_file:
            names = set(zip_file.namelist())
        expected = {
            "design_results.xlsx",
            "summary.xlsx",
            "optimized_results.xlsx",
            "reinforcement_schedule.xlsx",
            "run_log.txt",
        }
        self.assertTrue(expected.issubset(names), names)

    def test_status_not_found(self) -> None:
        response = self.client.get("/v1/jobs/noexiste")
        self.assertEqual(response.status_code, 404, response.text)
        payload = response.json()
        self.assertEqual(payload["error"], "job_not_found")
        self.assertIn("message", payload)
        self.assertIn("details", payload)
        self.assertEqual(payload["details"], [])

    def test_job_create_and_status_response_contract_keys(self) -> None:
        with (
            io.BytesIO(self.case_json.read_bytes()) as case_stream,
            self.seismic_excel.open("rb") as seismic_stream,
            self.gravity_excel.open("rb") as gravity_stream,
        ):
            create_response = self.client.post(
                "/v1/jobs",
                files={
                    "case_json": ("case.json", case_stream, "application/json"),
                    "seismic_excel": ("sismo.xlsx", seismic_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                    "gravity_excel": ("gravedad.xlsx", gravity_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                },
            )
        self.assertEqual(create_response.status_code, 202, create_response.text)
        create_payload = create_response.json()
        expected_create_keys = {"job_id", "status", "status_url", "download_url", "created_at"}
        self.assertEqual(set(create_payload.keys()), expected_create_keys)
        job_id = create_payload["job_id"]

        create_response = self.client.get(f"/v1/jobs/{job_id}")
        self.assertEqual(create_response.status_code, 200, create_response.text)
        status_payload = create_response.json()

        expected_status_keys = {
            "job_id",
            "status",
            "created_at",
            "updated_at",
            "started_at",
            "finished_at",
            "error",
            "artifacts",
        }
        self.assertEqual(set(status_payload.keys()), expected_status_keys)
        self.assertEqual(status_payload["job_id"], job_id)

    def test_create_job_validation_error(self) -> None:
        response = self.client.post("/v1/jobs")
        self.assertEqual(response.status_code, 422, response.text)

    def test_create_job_from_form_and_case_endpoint(self) -> None:
        with (
            self.seismic_excel.open("rb") as seismic_stream,
            self.gravity_excel.open("rb") as gravity_stream,
        ):
            response = self.client.post(
                "/v1/jobs/from-form",
                data={
                    "case_name": "case_form_test",
                    "sheet_name": "Conc Bm Sum - ACI 318-08",
                    "detailing": "DMO",
                    "units_rebar_per_length": "mm2/m",
                    "beam_id": "BFORM",
                    "cover_side_mm": "40",
                    "cover_top_mm": "40",
                    "cover_bottom_mm": "40",
                    "fc_mpa": "28",
                    "fy_mpa": "420",
                    "width_mm": "300",
                    "height_mm": "600",
                    "d_mm": "600",
                    "db_bar": "#6",
                    "min_branches_c": "4",
                    "min_branches_nc": "2",
                    "region_c_ratio": "0.2",
                },
                files={
                    "seismic_excel": ("sismo.xlsx", seismic_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                    "gravity_excel": ("gravedad.xlsx", gravity_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                },
            )

        self.assertEqual(response.status_code, 202, response.text)
        payload = response.json()
        job_id = payload["job_id"]

        case_response = self.client.get(f"/v1/jobs/{job_id}/case")
        self.assertEqual(case_response.status_code, 200, case_response.text)
        case_payload = case_response.json()
        self.assertEqual(case_payload["inputs"]["seismic_excel"], "seismic.xlsx")
        self.assertEqual(case_payload["inputs"]["gravity_excel"], "gravity.xlsx")
        self.assertGreater(len(case_payload["beams"][0]["spans"]), 0)
        self.assertEqual(case_payload["optimization"]["longitudinal_mode"], "legacy_region_independent")

    def test_create_job_from_form_with_geometry_excel_maps_sections(self) -> None:
        with (
            self.seismic_excel.open("rb") as seismic_stream,
            self.gravity_excel.open("rb") as gravity_stream,
            self.geometry_excel.open("rb") as geometry_stream,
        ):
            response = self.client.post(
                "/v1/jobs/from-form",
                data={
                    "case_name": "case_form_geometry_mapping",
                    "sheet_name": "Conc Bm Sum - ACI 318-08",
                    "detailing": "DMO",
                    "units_rebar_per_length": "mm2/m",
                    "beam_id": "BFORM",
                    "cover_side_mm": "40",
                    "cover_top_mm": "40",
                    "cover_bottom_mm": "40",
                    "fc_mpa": "28",
                    "fy_mpa": "420",
                    "width_mm": "300",
                    "height_mm": "600",
                    "d_mm": "600",
                    "db_bar": "#6",
                    "min_branches_c": "4",
                    "min_branches_nc": "2",
                    "region_c_ratio": "0.2",
                    "frame_pairs_json": '[{"id":"S1","seismic":"190","gravity":"190"},{"id":"S2","seismic":"8","gravity":"8"}]',
                },
                files={
                    "seismic_excel": ("sismo.xlsx", seismic_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                    "gravity_excel": ("gravedad.xlsx", gravity_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                    "geometry_excel": ("geometria.xlsx", geometry_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                },
            )

        self.assertEqual(response.status_code, 202, response.text)
        job_id = response.json()["job_id"]

        case_response = self.client.get(f"/v1/jobs/{job_id}/case")
        self.assertEqual(case_response.status_code, 200, case_response.text)
        case_payload = case_response.json()
        spans = case_payload["beams"][0]["spans"]

        span_190 = next(span for span in spans if span.get("seismic") == "190")
        span_8 = next(span for span in spans if span.get("seismic") == "8")

        for region in span_190["regions"]:
            self.assertEqual(region["width_mm"], 700.0)
            self.assertEqual(region["height_mm"], 700.0)

        for region in span_8["regions"]:
            self.assertEqual(region["width_mm"], 500.0)
            self.assertEqual(region["height_mm"], 500.0)

    def test_create_job_from_form_domain_validation_error(self) -> None:
        with (
            self.seismic_excel.open("rb") as seismic_stream,
            self.gravity_excel.open("rb") as gravity_stream,
        ):
            response = self.client.post(
                "/v1/jobs/from-form",
                data={
                    "case_name": "case_bad_domain",
                    "sheet_name": "Conc Bm Sum - ACI 318-08",
                    "detailing": "DMO",
                    "units_rebar_per_length": "mm2/m",
                    "beam_id": "BDOM",
                    "cover_side_mm": "40",
                    "cover_top_mm": "40",
                    "cover_bottom_mm": "40",
                    "fc_mpa": "28",
                    "fy_mpa": "420",
                    "width_mm": "300",
                    "height_mm": "600",
                    "d_mm": "600",
                    "db_bar": "#6",
                    "min_branches_c": "3",
                    "min_branches_nc": "2",
                    "region_c_ratio": "0.2",
                    "optimization_overrides_json": '{"genetic_algorithm":{"population_size":3}}',
                },
                files={
                    "seismic_excel": ("sismo.xlsx", seismic_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                    "gravity_excel": ("gravedad.xlsx", gravity_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                },
            )
        self.assertEqual(response.status_code, 422, response.text)
        payload = response.json()
        self.assertEqual(payload["error"], "domain_validation_error")
        self.assertTrue(payload.get("details"))
        first = payload["details"][0]
        self.assertIn("code", first)
        self.assertIn("field", first)
        self.assertIn("message", first)
        self.assertIn("severity", first)
        self.assertTrue(
            any(detail.get("field") == "optimization.genetic_algorithm.population_size" for detail in payload["details"])
        )

    def test_job_preview_endpoint_returns_span_region_labels(self) -> None:
        job_id = self._create_job()
        final_status = self._wait_terminal_status(job_id)
        self.assertEqual(final_status["status"], "completed", final_status)

        response = self.client.get(f"/v1/jobs/{job_id}/preview")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["job_id"], job_id)
        self.assertIn("spans", payload)
        self.assertTrue(payload["spans"])
        first_span = payload["spans"][0]
        self.assertIn("regions", first_span)
        self.assertTrue(first_span["regions"])
        first_region = first_span["regions"][0]
        self.assertIn("transverse_label", first_region)
        self.assertIn("longitudinal_label", first_region)
        self.assertIn("options", first_region)
        self.assertIsInstance(first_region["options"], list)
        self.assertLessEqual(len(first_region["options"]), 10)
        self.assertIn("transverse_options", first_region)
        self.assertIn("longitudinal_options", first_region)
        self.assertIsInstance(first_region["transverse_options"], list)
        self.assertIsInstance(first_region["longitudinal_options"], list)
        self.assertGreaterEqual(len(first_region["transverse_options"]), 1)
        self.assertLessEqual(len(first_region["transverse_options"]), 10)
        self.assertLessEqual(len(first_region["longitudinal_options"]), 10)
        transverse_weights = [
            float(item["weight_kg"])
            for item in first_region["transverse_options"]
            if item.get("weight_kg") is not None
        ]
        self.assertEqual(transverse_weights, sorted(transverse_weights))
        if first_region["options"]:
            first_option = first_region["options"][0]
            self.assertIn("option", first_option)
            self.assertIn("weight_total_kg", first_option)
            self.assertIn("base_longitudinal_label", first_option)
            self.assertIn("additional_longitudinal_label", first_option)
        if first_region["transverse_options"]:
            first_transverse = first_region["transverse_options"][0]
            self.assertIn("label", first_transverse)
            self.assertIn("weight_kg", first_transverse)
            self.assertIn("stirrup_count", first_transverse)
            self.assertIn("stirrup_unit_weight_kg", first_transverse)
            for item in first_region["transverse_options"]:
                if item.get("stirrup_count") is not None and item.get("stirrup_unit_weight_kg") is not None:
                    expected_weight = float(item["stirrup_count"]) * float(item["stirrup_unit_weight_kg"])
                    self.assertAlmostEqual(float(item.get("weight_kg") or 0.0), expected_weight, places=2)
        if first_region["longitudinal_options"]:
            first_longitudinal = first_region["longitudinal_options"][0]
            self.assertIn("label", first_longitudinal)
            self.assertIn("weight_kg", first_longitudinal)


    def test_save_job_selection_generates_comparison_artifact(self) -> None:
        job_id = self._create_job()
        final_status = self._wait_terminal_status(job_id)
        self.assertEqual(final_status["status"], "completed", final_status)

        preview_response = self.client.get(f"/v1/jobs/{job_id}/preview")
        self.assertEqual(preview_response.status_code, 200, preview_response.text)
        preview = preview_response.json()

        first_span = preview["spans"][0]
        first_region = first_span["regions"][0]
        options = first_region.get("options", [])
        self.assertTrue(options)
        selected_row = options[1] if len(options) > 1 else options[0]

        save_response = self.client.post(
            f"/v1/jobs/{job_id}/selection",
            json={
                "selections": [
                    {
                        "span_id": first_span["span_id"],
                        "region_id": first_region["region_id"],
                        "transverse_label": selected_row["transverse_label"],
                        "longitudinal_label": selected_row["longitudinal_label"],
                    }
                ]
            },
        )
        self.assertEqual(save_response.status_code, 200, save_response.text)
        save_payload = save_response.json()
        self.assertEqual(save_payload["artifact_name"], "selected_reinforcement_comparison.xlsx")
        self.assertEqual(save_payload["job_id"], job_id)

        status_response = self.client.get(f"/v1/jobs/{job_id}")
        self.assertEqual(status_response.status_code, 200, status_response.text)
        status_payload = status_response.json()
        self.assertIn("selected_reinforcement_comparison.xlsx", status_payload["artifacts"])
        self.assertIn("selection_applied.json", status_payload["artifacts"])

        artifact_response = self.client.get(f"/v1/jobs/{job_id}/artifacts/selected_reinforcement_comparison.xlsx")
        self.assertEqual(artifact_response.status_code, 200, artifact_response.text)

        zip_response = self.client.get(f"/v1/jobs/{job_id}/download")
        self.assertEqual(zip_response.status_code, 200, zip_response.text)
        with ZipFile(io.BytesIO(zip_response.content)) as zip_file:
            names = set(zip_file.namelist())
        self.assertIn("selected_reinforcement_comparison.xlsx", names)
        self.assertIn("selection_applied.json", names)

    def test_save_job_selection_accepts_span_selections_compatibly(self) -> None:
        job_id = self._create_job()
        final_status = self._wait_terminal_status(job_id)
        self.assertEqual(final_status["status"], "completed", final_status)

        preview_response = self.client.get(f"/v1/jobs/{job_id}/preview")
        self.assertEqual(preview_response.status_code, 200, preview_response.text)
        preview = preview_response.json()

        selections: list[dict] = []
        spans = preview.get("spans", [])
        self.assertTrue(spans)
        for span in spans:
            span_id = span.get("span_id")
            regions = span.get("regions", [])
            for region in regions:
                options = region.get("options", [])
                if not options:
                    continue
                first = options[0]
                selections.append(
                    {
                        "span_id": span_id,
                        "region_id": region.get("region_id"),
                        "transverse_label": first.get("transverse_label"),
                        "longitudinal_label": first.get("longitudinal_label"),
                    }
                )

        self.assertTrue(selections)
        first_span_id = spans[0].get("span_id")
        self.assertTrue(first_span_id)

        save_response = self.client.post(
            f"/v1/jobs/{job_id}/selection",
            json={
                "selections": selections,
                "span_selections": [
                    {
                        "span_id": first_span_id,
                        "option": 1,
                    }
                ],
            },
        )
        self.assertEqual(save_response.status_code, 200, save_response.text)
        payload = save_response.json()
        self.assertEqual(payload["artifact_name"], "selected_reinforcement_comparison.xlsx")

    def test_save_job_selection_accepts_span_option_without_region_longitudinal(self) -> None:
        job_id = self._create_job()
        final_status = self._wait_terminal_status(job_id)
        self.assertEqual(final_status["status"], "completed", final_status)

        preview_response = self.client.get(f"/v1/jobs/{job_id}/preview")
        self.assertEqual(preview_response.status_code, 200, preview_response.text)
        preview = preview_response.json()

        spans = preview.get("spans", [])
        self.assertTrue(spans)
        first_span = spans[0]
        selections: list[dict] = []
        for region in first_span.get("regions", []):
            options = region.get("options", [])
            if not options:
                continue
            first = options[0]
            selections.append(
                {
                    "span_id": first_span["span_id"],
                    "region_id": region.get("region_id"),
                    "transverse_label": first.get("transverse_label"),
                }
            )

        self.assertTrue(selections)
        save_response = self.client.post(
            f"/v1/jobs/{job_id}/selection",
            json={
                "selections": selections,
                "span_selections": [
                    {
                        "span_id": first_span["span_id"],
                        "option": 1,
                    }
                ],
            },
        )
        self.assertEqual(save_response.status_code, 200, save_response.text)

    def test_save_job_selection_accepts_transverse_label_exposed_by_preview(self) -> None:
        preview_payload = {
            "job_id": "fake_job",
            "spans": [
                {
                    "span_id": "S1",
                    "regions": [
                        {
                            "region_id": "R3",
                            "options": [
                                {
                                    "option": 1,
                                    "transverse_label": "1E #3 @ 100 mm",
                                    "longitudinal_label": "4 x #4",
                                    "weight_total_kg": 10.0,
                                    "weight_transverse_kg": 4.0,
                                    "weight_longitudinal_kg": 6.0,
                                }
                            ],
                            "transverse_options": [
                                {
                                    "label": "1E #3 @ 100 mm",
                                    "weight_kg": 4.0,
                                    "stirrup_count": 9,
                                    "stirrup_unit_weight_kg": 0.45,
                                },
                                {
                                    "label": "1E #3 + 3G #3 @ 90 mm",
                                    "weight_kg": 3.8,
                                    "stirrup_count": 10,
                                    "stirrup_unit_weight_kg": 0.38,
                                },
                            ],
                            "longitudinal_options": [
                                {
                                    "label": "4 x #4",
                                    "weight_kg": 6.0,
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        with patch("app.routers.jobs.build_job_preview_payload", return_value=preview_payload), patch(
            "app.routers.jobs.save_selected_options_report",
            return_value={"artifact_name": "selected_reinforcement_comparison.xlsx", "saved_regions": 1},
        ):
            response = self.client.post(
                "/v1/jobs/fake_job/selection",
                json={
                    "selections": [
                        {
                            "span_id": "S1",
                            "region_id": "R3",
                            "transverse_label": "1E #3 + 3G #3 @ 90 mm",
                            "longitudinal_label": "4 x #4",
                        }
                    ]
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["artifact_name"], "selected_reinforcement_comparison.xlsx")

    def test_save_job_selection_rejects_invalid_span_option(self) -> None:
        job_id = self._create_job()
        final_status = self._wait_terminal_status(job_id)
        self.assertEqual(final_status["status"], "completed", final_status)

        preview_response = self.client.get(f"/v1/jobs/{job_id}/preview")
        self.assertEqual(preview_response.status_code, 200, preview_response.text)
        preview = preview_response.json()
        first_span = preview["spans"][0]

        save_response = self.client.post(
            f"/v1/jobs/{job_id}/selection",
            json={
                "selections": [],
                "span_selections": [
                    {
                        "span_id": first_span["span_id"],
                        "option": 999,
                    }
                ],
            },
        )
        self.assertEqual(save_response.status_code, 422, save_response.text)
        payload = save_response.json()
        self.assertEqual(payload["error"], "invalid_selection")

    def test_save_job_selection_rejects_invalid_option(self) -> None:
        job_id = self._create_job()
        final_status = self._wait_terminal_status(job_id)
        self.assertEqual(final_status["status"], "completed", final_status)

        preview_response = self.client.get(f"/v1/jobs/{job_id}/preview")
        self.assertEqual(preview_response.status_code, 200, preview_response.text)
        preview = preview_response.json()

        first_span = preview["spans"][0]
        first_region = first_span["regions"][0]

        save_response = self.client.post(
            f"/v1/jobs/{job_id}/selection",
            json={
                "selections": [
                    {
                        "span_id": first_span["span_id"],
                        "region_id": first_region["region_id"],
                        "option": 9999,
                    }
                ]
            },
        )
        self.assertEqual(save_response.status_code, 422, save_response.text)
        payload = save_response.json()
        self.assertEqual(payload["error"], "invalid_selection")

    def test_job_preview_endpoint_supports_multiple_spans_from_pairs(self) -> None:
        with (
            self.seismic_excel.open("rb") as seismic_stream,
            self.gravity_excel.open("rb") as gravity_stream,
        ):
            response = self.client.post(
                "/v1/jobs/from-form",
                data={
                    "case_name": "case_multi_span_preview",
                    "sheet_name": "Conc Bm Sum - ACI 318-08",
                    "detailing": "DMO",
                    "units_rebar_per_length": "mm2/m",
                    "beam_id": "B1",
                    "cover_side_mm": "40",
                    "cover_top_mm": "40",
                    "cover_bottom_mm": "40",
                    "fc_mpa": "28",
                    "fy_mpa": "420",
                    "width_mm": "300",
                    "height_mm": "600",
                    "d_mm": "600",
                    "db_bar": "#6",
                    "min_branches_c": "4",
                    "min_branches_nc": "2",
                    "region_c_ratio": "0.2",
                    "frame_pairs_json": '[{"id":"S1","seismic":"190","gravity":"190"},{"id":"S2","seismic":"8","gravity":"8"}]',
                },
                files={
                    "seismic_excel": ("sismo.xlsx", seismic_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                    "gravity_excel": ("gravedad.xlsx", gravity_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                },
            )

        self.assertEqual(response.status_code, 202, response.text)
        job_id = response.json()["job_id"]
        final_status = self._wait_terminal_status(job_id)
        self.assertEqual(final_status["status"], "completed", final_status)

        preview_response = self.client.get(f"/v1/jobs/{job_id}/preview")
        self.assertEqual(preview_response.status_code, 200, preview_response.text)
        preview_payload = preview_response.json()
        self.assertEqual(len(preview_payload.get("spans", [])), 2)

    def test_create_job_from_form_with_span_layout_json(self) -> None:
        span_layout = [
            {
                "id": "S1",
                "seismic": "190",
                "gravity": "190",
                "c_ratio_extremos": 0.2,
                "support_left_mm": 180,
                "support_right_mm": 250,
                "clear_length_mm": 5370,
                "is_deep_beam": True,
                "regions": [
                    {"id": "R1", "from": 0.0, "to": 0.2, "type": "C"},
                    {"id": "R2", "from": 0.2, "to": 0.8, "type": "NC"},
                    {"id": "R3", "from": 0.8, "to": 1.0, "type": "C"},
                ],
            },
            {
                "id": "S2",
                "seismic": "8",
                "gravity": "8",
                "c_ratio_extremos": 0.25,
                "support_left_mm": 200,
                "support_right_mm": 150,
                "is_deep_beam": False,
                "regions": [
                    {"id": "R1", "from": 0.0, "to": 0.25, "confinado": True},
                    {"id": "R2", "from": 0.25, "to": 0.75, "confinado": False},
                    {"id": "R3", "from": 0.75, "to": 1.0, "confinado": True},
                ],
            },
        ]
        with (
            self.seismic_excel.open("rb") as seismic_stream,
            self.gravity_excel.open("rb") as gravity_stream,
        ):
            response = self.client.post(
                "/v1/jobs/from-form",
                data={
                    "case_name": "case_span_layout",
                    "sheet_name": "Conc Bm Sum - ACI 318-08",
                    "detailing": "DMO",
                    "units_rebar_per_length": "mm2/m",
                    "beam_id": "B1",
                    "cover_side_mm": "40",
                    "cover_top_mm": "40",
                    "cover_bottom_mm": "40",
                    "fc_mpa": "28",
                    "fy_mpa": "420",
                    "width_mm": "300",
                    "height_mm": "600",
                    "d_mm": "600",
                    "db_bar": "#6",
                    "min_branches_c": "4",
                    "min_branches_nc": "2",
                    "region_c_ratio": "0.2",
                    "span_layout_json": json.dumps(span_layout),
                },
                files={
                    "seismic_excel": ("sismo.xlsx", seismic_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                    "gravity_excel": ("gravedad.xlsx", gravity_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                },
            )

        self.assertEqual(response.status_code, 202, response.text)
        job_id = response.json()["job_id"]

        case_response = self.client.get(f"/v1/jobs/{job_id}/case")
        self.assertEqual(case_response.status_code, 200, case_response.text)
        case_payload = case_response.json()
        spans = case_payload["beams"][0]["spans"]
        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[0]["id"], "S1")
        self.assertEqual(spans[1]["id"], "S2")
        self.assertEqual(spans[0]["support_left_mm"], 180)
        self.assertEqual(spans[0]["support_right_mm"], 250)
        self.assertEqual(spans[0]["clear_length_mm"], 5370)
        self.assertTrue(spans[0]["is_deep_beam"])
        self.assertFalse(spans[1]["is_deep_beam"])
        self.assertEqual(spans[1]["support_left_mm"], 250)
        self.assertEqual(spans[1]["support_right_mm"], 150)

        final_status = self._wait_terminal_status(job_id)
        self.assertEqual(final_status["status"], "completed", final_status)

        preview_response = self.client.get(f"/v1/jobs/{job_id}/preview")
        self.assertEqual(preview_response.status_code, 200, preview_response.text)
        preview_payload = preview_response.json()
        self.assertEqual(len(preview_payload.get("spans", [])), 2)
        self.assertEqual(preview_payload["spans"][0]["support_right_mm"], 250)
        self.assertEqual(preview_payload["spans"][0]["length_mm"], 5370)

    def test_create_job_from_form_accepts_longitudinal_mode_override(self) -> None:
        with (
            self.seismic_excel.open("rb") as seismic_stream,
            self.gravity_excel.open("rb") as gravity_stream,
        ):
            response = self.client.post(
                "/v1/jobs/from-form",
                data={
                    "case_name": "case_long_mode_override",
                    "sheet_name": "Conc Bm Sum - ACI 318-08",
                    "detailing": "DMO",
                    "units_rebar_per_length": "mm2/m",
                    "beam_id": "B1",
                    "cover_side_mm": "40",
                    "cover_top_mm": "40",
                    "cover_bottom_mm": "40",
                    "fc_mpa": "28",
                    "fy_mpa": "420",
                    "width_mm": "300",
                    "height_mm": "600",
                    "d_mm": "600",
                    "db_bar": "#6",
                    "min_branches_c": "4",
                    "min_branches_nc": "2",
                    "region_c_ratio": "0.2",
                    "optimization_overrides_json": json.dumps({
                        "longitudinal_mode": "span_coupled",
                        "variables": {
                            "longitudinal_bar_counts": [2, 4, 6, 8],
                        },
                    }),
                },
                files={
                    "seismic_excel": (
                        "sismo.xlsx",
                        seismic_stream,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ),
                    "gravity_excel": (
                        "gravedad.xlsx",
                        gravity_stream,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ),
                },
            )

        self.assertEqual(response.status_code, 202, response.text)
        job_id = response.json()["job_id"]

        case_response = self.client.get(f"/v1/jobs/{job_id}/case")
        self.assertEqual(case_response.status_code, 200, case_response.text)
        case_payload = case_response.json()
        self.assertEqual(case_payload["optimization"]["longitudinal_mode"], "span_coupled")

        final_status = self._wait_terminal_status(job_id)
        self.assertEqual(final_status["status"], "completed", final_status)

        preview_response = self.client.get(f"/v1/jobs/{job_id}/preview")
        self.assertEqual(preview_response.status_code, 200, preview_response.text)
        preview_payload = preview_response.json()
        spans = preview_payload.get("spans", [])
        self.assertTrue(spans)
        self.assertIn("span_option_choices", spans[0])
        self.assertIsInstance(spans[0]["span_option_choices"], list)

        first_span = spans[0]
        base_options = first_span.get("longitudinal_base_options", [])
        self.assertLessEqual(len(base_options), 10)
        if base_options:
            base_total_weights = [float(opt.get("total_weight_kg") or 0.0) for opt in base_options]
            self.assertEqual(base_total_weights, sorted(base_total_weights))
            base_labels = [str(opt.get("base_label") or "") for opt in base_options]
            self.assertEqual(len(base_labels), len(set(base_labels)))
            from rc_shear_torsion.design import BAR_AREAS_MM2, longitudinal_mass_kg_per_m
            import re

            span_length_m = float(first_span.get("length_mm") or 0.0) / 1000.0
            self.assertGreater(span_length_m, 0.0)
            for opt in base_options:
                label = str(opt.get("base_label") or "").strip().lower()
                reported = float(opt.get("long_weight_kg") or 0.0)
                if label == "no se requiere":
                    self.assertAlmostEqual(reported, 0.0, places=3)
                    continue
                match = re.match(r"^(\d+)\s*x\s*(#\d+)$", str(opt.get("base_label") or "").strip(), re.IGNORECASE)
                self.assertIsNotNone(match, msg=f"Formato base no esperado: {opt.get('base_label')}")
                count = int(match.group(1))
                bar = match.group(2).upper()
                expected = longitudinal_mass_kg_per_m(BAR_AREAS_MM2[bar] * count) * span_length_m
                self.assertAlmostEqual(reported, expected, places=2)
        span_long_sets = first_span.get("span_longitudinal_option_sets", [])
        self.assertLessEqual(len(span_long_sets), 10)
        if span_long_sets:
            set_weights = [float(item.get("total_longitudinal_weight_kg") or 0.0) for item in span_long_sets]
            self.assertEqual(set_weights, sorted(set_weights))
            default_set_value = first_span.get("default_longitudinal_option_set_value")
            self.assertTrue(any(str(item.get("value")) == str(default_set_value) for item in span_long_sets))
            for item in span_long_sets:
                regions_map = item.get("regions", [])
                self.assertIsInstance(regions_map, list)
                self.assertTrue(regions_map)
                self.assertTrue(all(str(region.get("region_id") or "").strip() for region in regions_map))

        regions = first_span.get("regions", [])
        self.assertTrue(regions)
        first_region = regions[0]
        transverse_options = first_region.get("transverse_options", [])
        self.assertLessEqual(len(transverse_options), 10)
        if transverse_options:
            trans_weights = [float(opt.get("weight_kg") or 0.0) for opt in transverse_options]
            self.assertEqual(trans_weights, sorted(trans_weights))

        additional_map = first_region.get("additional_options_by_base", {})
        for base in base_options:
            values = additional_map.get(base.get("value"), [])
            self.assertLessEqual(len(values), 10)
            if values:
                add_weights = [float(opt.get("weight_kg") or 0.0) for opt in values]
                self.assertEqual(add_weights, sorted(add_weights))
                add_labels = [str(opt.get("label") or "") for opt in values]
                self.assertEqual(len(add_labels), len(set(add_labels)))
                region_length_m = float(first_region.get("length_mm") or 0.0) / 1000.0
                self.assertGreater(region_length_m, 0.0)
                for opt in values:
                    label = str(opt.get("label") or "").strip().lower()
                    reported = float(opt.get("weight_kg") or 0.0)
                    if label == "no se requiere":
                        self.assertAlmostEqual(reported, 0.0, places=3)
                        continue
                    match = re.match(r"^(\d+)\s*x\s*(#\d+)$", str(opt.get("label") or "").strip(), re.IGNORECASE)
                    self.assertIsNotNone(match, msg=f"Formato adicional no esperado: {opt.get('label')}")
                    count = int(match.group(1))
                    bar = match.group(2).upper()
                    expected = longitudinal_mass_kg_per_m(BAR_AREAS_MM2[bar] * count) * region_length_m
                    self.assertAlmostEqual(reported, expected, places=2)
    def test_download_single_artifact_success(self) -> None:
        job_id = self._create_job()
        final_status = self._wait_terminal_status(job_id)
        self.assertEqual(final_status["status"], "completed", final_status)

        response = self.client.get(f"/v1/jobs/{job_id}/artifacts/design_results.xlsx")
        self.assertEqual(response.status_code, 200, response.text)
        disposition = response.headers.get("content-disposition", "")
        self.assertIn("design_results.xlsx", disposition)

    def test_download_single_artifact_not_found(self) -> None:
        job_id = self._create_job()
        final_status = self._wait_terminal_status(job_id)
        self.assertEqual(final_status["status"], "completed", final_status)

        response = self.client.get(f"/v1/jobs/{job_id}/artifacts/noexiste.xlsx")
        self.assertEqual(response.status_code, 404, response.text)
        payload = response.json()
        self.assertEqual(payload["error"], "job_artifact_not_found")

    def test_download_conflict_when_failed(self) -> None:
        invalid_case = b'{"case_name":"bad_case","inputs":{},"units":{"rebar_per_length":"mm2/m"},"beams":[],"optimization":{"enabled":true,"objective":"min_weight","variables":{"E_bars":["#3"],"G_bars":["#3"],"G_counts":[0],"stirrup_spacing_mm":[100],"longitudinal_bars":["#4"],"longitudinal_bar_counts":[2]},"genetic_algorithm":{"population_size":10,"generations":2,"crossover_rate":0.8,"mutation_rate":0.1,"elite_count":2}}}'
        job_id = self._create_job(case_content=invalid_case)
        final_status = self._wait_terminal_status(job_id)
        self.assertEqual(final_status["status"], "failed", final_status)
        self.assertTrue(final_status.get("error"))
        self.assertIsNotNone(final_status.get("finished_at"))

        download_response = self.client.get(f"/v1/jobs/{job_id}/download")
        self.assertEqual(download_response.status_code, 409, download_response.text)

    def test_download_conflict_when_job_is_queued(self) -> None:
        job_id = "queued_manual_job"
        self._write_job_meta(job_id=job_id, status="queued", artifacts={})
        response = self.client.get(f"/v1/jobs/{job_id}/download")
        self.assertEqual(response.status_code, 409, response.text)
        payload = response.json()
        self.assertEqual(payload["error"], "job_not_ready")
        self.assertIn("message", payload)
        self.assertIn("details", payload)
        self.assertEqual(payload["details"], [])

    def test_download_single_artifact_conflict_when_job_is_queued(self) -> None:
        job_id = "queued_manual_job_artifact"
        self._write_job_meta(job_id=job_id, status="queued", artifacts={})
        response = self.client.get(f"/v1/jobs/{job_id}/artifacts/design_results.xlsx")
        self.assertEqual(response.status_code, 409, response.text)
        payload = response.json()
        self.assertEqual(payload["error"], "job_not_ready")

    def test_openapi_error_response_schema_is_documented(self) -> None:
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()

        components = payload["components"]["schemas"]
        self.assertIn("ErrorResponse", components)
        self.assertIn("ErrorDetail", components)

        download_responses = payload["paths"]["/v1/jobs/{job_id}/download"]["get"]["responses"]
        self.assertIn("409", download_responses)
        schema_ref = download_responses["409"]["content"]["application/json"]["schema"]["$ref"]
        self.assertEqual(schema_ref, "#/components/schemas/ErrorResponse")


if __name__ == "__main__":
    unittest.main()





