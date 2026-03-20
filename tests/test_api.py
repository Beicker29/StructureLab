from __future__ import annotations

import io
import json
import os
import time
import unittest
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
        cls.case_json = cls.repo_root / "cases" / "case_0001" / "case.json"
        cls.seismic_excel = cls.repo_root / "cases" / "case_0001" / "sismo.xlsx"
        cls.gravity_excel = cls.repo_root / "cases" / "case_0001" / "gravedad.xlsx"

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
        self.assertIn("Diseno", response.text)
        self.assertIn("Importar ETABS", response.text)
        self.assertIn("Resultados", response.text)
        self.assertIn("Reportes", response.text)
        self.assertIn("beam-elevation-container", response.text)
        self.assertIn("Crear y ejecutar job", response.text)

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
                "support_right_mm": 250,
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
        self.assertEqual(spans[0]["support_right_mm"], 250)

        final_status = self._wait_terminal_status(job_id)
        self.assertEqual(final_status["status"], "completed", final_status)

        preview_response = self.client.get(f"/v1/jobs/{job_id}/preview")
        self.assertEqual(preview_response.status_code, 200, preview_response.text)
        preview_payload = preview_response.json()
        self.assertEqual(len(preview_payload.get("spans", [])), 2)
        self.assertEqual(preview_payload["spans"][0]["support_right_mm"], 250)

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
