"""Results-boundary fixtures: these weights are synthetic, not design calculations."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services import job_preview_service as preview_service
from app.services.selection_service import resolve_selected_options
from app.schemas.jobs import JobSelectionSaveRequest

ROOT = Path(__file__).resolve().parents[1]


def multispan_fixture(span_ids=("S1", "S2"), *, mixed=True):
    case = {"beams": [{"beam_id": "B1", "spans": []}]}
    optimized, schedule, transverse = {}, {}, {}
    for si, span_id in enumerate(span_ids):
        span = {"id": span_id, "clear_length_mm": 3000, "regions": []}
        case["beams"][0]["spans"].append(span)
        for ri in range(3):
            region_id = f"R{ri + 1}"
            span["regions"].append({"id": region_id, "type": "NC", "from": ri / 3, "to": (ri + 1) / 3})
            key = (span_id, region_id)
            spacing = (si % 2 + 1) * 100 + (ri + 1) * 10
            inactive = mixed and si == 1 and ri == 1
            bar = "#5" if si == 0 else "#6"
            total = (30, 40, 30)[ri] if si == 0 else 50
            long_weight = 0 if inactive else 10
            rows = []
            for option, count in ((1, 4), (2, 6)):
                base = "no se requiere" if inactive else f"{count} x {bar}"
                extra = "no se requiere" if inactive or ri != 0 else "2 x #4"
                weight = 0 if inactive else long_weight + (option - 1) * 5
                rows.append({
                    "option": option, "length_mm": 1000, "spacing_mm": spacing,
                    "transverse_label": f"1E #3 @ {spacing} mm",
                    "longitudinal_label": base if extra == "no se requiere" else f"{base} + {extra}",
                    "base_longitudinal_label": base, "additional_longitudinal_label": extra,
                    "base_long_bar": None if inactive else bar, "base_long_count": 0 if inactive else count,
                    "extra_long_bar": "#4" if extra != "no se requiere" else None,
                    "extra_long_count": 2 if extra != "no se requiere" else 0,
                    "weight_base_kg": weight - (2 if extra != "no se requiere" else 0),
                    "weight_additional_kg": 2 if extra != "no se requiere" else 0,
                    "weight_longitudinal_kg": weight, "weight_transverse_kg": total - long_weight,
                    "weight_total_kg": total - long_weight + weight,
                })
            schedule[key] = rows
            optimized[key] = dict(rows[0], longitudinal_mode="span_coupled")
            transverse[key] = [
                {"label": f"1E #3 @ {spacing + delta} mm", "spacing_mm": spacing + delta,
                 "weight_kg": total - long_weight + delta / 5, "stirrup_count": 10,
                 "stirrup_unit_weight_kg": (total - long_weight + delta / 5) / 10}
                for delta in (0, 10)
            ]
    return case, optimized, schedule, transverse


@contextmanager
def preview_fixture(span_ids=("S1", "S2"), *, mixed=True):
    case, optimized, schedule, transverse = multispan_fixture(span_ids, mixed=mixed)
    job_id = "multispan_" + uuid4().hex
    output = ROOT / ".tmp_test_runtime" / job_id
    output.mkdir(parents=True)
    meta = {"job_id": job_id, "status": "completed", "artifacts": {},
            "paths": {"job_dir": str(output)}, "output_dir": str(output)}
    def save_meta(value):
        meta.update(value)
    try:
        with (
            patch.object(preview_service, "get_job", side_effect=lambda _: meta),
            patch.object(preview_service, "get_job_case_payload", return_value=case),
            patch.object(preview_service, "_read_optimized_regions", return_value=deepcopy(optimized)),
            patch.object(preview_service, "_read_schedule_rows", return_value=deepcopy(schedule)),
            patch.object(preview_service, "_read_transverse_options", return_value=deepcopy(transverse)),
            patch("app.services.job_service._load_job", side_effect=lambda _: dict(meta)),
            patch("app.services.job_service._save_job", side_effect=save_meta),
        ):
            yield job_id, meta
    finally:
        preview_service._PREVIEW_CACHE.pop(job_id, None)
        shutil.rmtree(output, ignore_errors=True)


def render_in_browser(payload, actions=""):
    """Execute the actual renderer in an isolated headless browser/real DOM."""
    browser = os.environ.get("STRUCTURELAB_TEST_BROWSER") or shutil.which("chromium") or shutil.which("google-chrome")
    if not browser and Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe").exists():
        browser = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not browser:
        raise unittest.SkipTest("Set STRUCTURELAB_TEST_BROWSER to an installed Chromium/Edge executable")
    source = (ROOT / "app/ui/static/ui.js").read_text(encoding="utf-8")
    functions = source[source.index("function fmtKg("):source.index("function renderSummary(")]
    setup = """
const statusModule={};const regionOptionsEl=document.getElementById('regions');
const selectionSaveMsg=document.createElement('div');const saveSelectionBtn=document.createElement('button');
let regionOptionSelections={};let spanLongSelections={};let currentJobId='test';
function syncBeamPreviewWithSelections(){}
"""
    inspect = """
const result={spans:[...document.querySelectorAll('.span-summary-title')].map(e=>e.textContent),
regions:[...document.querySelectorAll('.region-opt-span')].map(e=>e.querySelectorAll('.region-opt-transverse').length),
summary:document.querySelector('.region-opt-summary')?.textContent,
disabled:saveSelectionBtn.disabled,payload:buildSelectionPayload(payload)};
document.getElementById('result').textContent=JSON.stringify(result);
"""
    script = setup + functions + "const payload=" + json.dumps(payload) + ";try{renderRegionOptions(payload);" + actions + inspect
    script += "}catch(e){document.getElementById('result').textContent=JSON.stringify({error:e.stack});}"
    page = '<html><body><div id="regions"></div><pre id="result"></pre><script>' + script.replace("</script", "<\\/script") + '</script></body></html>'
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page.encode("utf-8"))
        def log_message(self, *args):
            pass
    server = HTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    profile = ROOT / ".tmp_test_runtime" / ("browser_" + uuid4().hex)
    try:
        completed = subprocess.run(
            [browser, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
             "--user-data-dir=" + str(profile), "--dump-dom", f"http://127.0.0.1:{server.server_port}"],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        marker = '<pre id="result">'
        if completed.returncode or marker not in completed.stdout:
            raise AssertionError(completed.stderr[-1500:])
        raw = completed.stdout.split(marker, 1)[1].split("</pre>", 1)[0]
        result = json.loads(html.unescape(raw))
        if "error" in result:
            raise AssertionError(result["error"])
        return result
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
        shutil.rmtree(profile, ignore_errors=True)


class MultispanPreviewTests(unittest.TestCase):
    def test_engine_canonical_artifacts_endpoint_renderer_selection_pipeline(self):
        from rc_shear_torsion import engine
        from rc_shear_torsion.io import EtabsFrameData, EtabsSourceData, EtabsStationRow
        from rc_shear_torsion.models import CaseConfig
        from rc_shear_torsion.results_model import to_canonical_region_results

        raw = json.loads((ROOT / "examples/case_0001/case.json").read_text())
        template = raw["beams"][0]["spans"][0]
        raw["beams"][0]["spans"] = [dict(deepcopy(template), id=s, seismic=s, gravity=s) for s in ("S1", "S2")]
        raw["optimization"]["longitudinal_mode"] = "span_coupled"
        raw["optimization"]["variables"].update(E_bars=["#3"], G_bars=["#3"], G_counts=[2],
                                                 stirrup_spacing_mm=[110, 120], longitudinal_bars=["#5", "#6"],
                                                 longitudinal_bar_counts=[4, 6])
        raw["optimization"]["genetic_algorithm"].update(population_size=10, generations=1, elite_count=1)
        config = CaseConfig.model_validate(raw)
        frames = {}
        for span_id in ("S1", "S2"):
            rows = []
            for station in (0, 1500, 3000):
                inactive = span_id == "S2" and station == 1500
                rows.append(EtabsStationRow("L1", "B1", span_id, "SEC", station, 0, 0, 100,
                                           0 if inactive else 200, 0 if inactive else 50))
            frames[span_id] = EtabsFrameData(span_id, tuple(rows))
        sources = {source: EtabsSourceData(source, frames, 6, 0, ()) for source in ("seismic", "gravity")}
        output = ROOT / ".tmp_test_runtime" / ("pipeline_" + uuid4().hex)
        job = "pipeline_" + uuid4().hex
        try:
            with (patch.object(engine, "load_case_config", return_value=config),
                  patch.object(engine, "load_etabs_sources", return_value=sources),
                  patch.object(engine, "write_optimized_results", wraps=engine.write_optimized_results) as write):
                result_dir = engine.run_case("fixture.json", output)
            results = write.call_args.args[1]
            self.assertTrue(all(r.status == "ok" for r in results))
            identities = {(r.beam_id, r.span_id, r.region_id) for r in to_canonical_region_results(results)}
            self.assertEqual(identities, {("B1", s, r) for s in ("S1", "S2") for r in ("R1", "R2", "R3")})
            meta = {"status": "completed", "artifacts": {p.name: str(p) for p in result_dir.glob("*.xlsx")}}
            with (patch.object(preview_service, "get_job", return_value=meta),
                  patch.object(preview_service, "get_job_case_payload", return_value=config.model_dump(by_alias=True))):
                response = TestClient(app).get(f"/v1/jobs/{job}/preview")
            self.assertEqual(response.status_code, 200, response.text)
            payload = response.json()
            rendered = render_in_browser(payload)
            self.assertEqual(rendered["spans"], ["Vano S1", "Vano S2"])
            self.assertEqual(rendered["regions"], [3, 3])
            selected = resolve_selected_options(payload, JobSelectionSaveRequest.model_validate(rendered["payload"]))
            self.assertEqual(len(selected), 6)
            self.assertAlmostEqual(sum(r["selected_weight_kg"] for r in selected), payload["optimal_beam_weight_kg"])
            zero = next(r for r in selected if (r["span_id"], r["region_id"]) == ("S2", "R2"))
            self.assertEqual(zero["selected_longitudinal_weight_kg"], 0)
        finally:
            preview_service._PREVIEW_CACHE.pop(job, None)
            shutil.rmtree(output, ignore_errors=True)

    def test_xlsx_parsers_scope_beam_span_and_region_identity(self):
        from tests.test_report import ReportTests
        from rc_shear_torsion.report import write_optimized_results, write_reinforcement_schedule
        from rc_shear_torsion.results_model import to_canonical_region_results

        with preview_fixture() as (_, meta):
            output = Path(meta["output_dir"])
            results = [ReportTests()._region_result(span_id=s, region_id=f"R{ri}", spacing_mm=si * 100 + ri * 10)
                       for si, s in enumerate(("S1", "S2"), 1) for ri in (1, 2, 3)]
            results += [replace(r, beam_id="B2", spacing_mm=70) for r in results]
            lengths = {(r.beam_id, r.span_id, r.region_id): 1000 for r in results}
            canonical = to_canonical_region_results(results)
            self.assertEqual(len({(r.beam_id, r.span_id, r.region_id) for r in canonical}), 12)
            optimized_path, schedule_path = output / "optimized.xlsx", output / "schedule.xlsx"
            write_optimized_results(optimized_path, results)
            write_reinforcement_schedule(schedule_path, results, lengths,
                                         transverse_alternatives={k: [r] for k, r in zip(lengths, results)})
            optimized = preview_service._read_optimized_regions(optimized_path, beam_id="B1")
            schedule = preview_service._read_schedule_rows(schedule_path, beam_id="B1")
            transverse = preview_service._read_transverse_options(schedule_path, beam_id="B1")
            for data in (optimized, schedule, transverse):
                self.assertEqual(len(data), 6)
                self.assertIn(("S1", "R1"), data)
                self.assertIn(("S2", "R1"), data)
            self.assertEqual(optimized[("S1", "R1")]["spacing_mm"], 110)
            self.assertEqual(optimized[("S2", "R1")]["spacing_mm"], 210)
            self.assertEqual(transverse[("S1", "R1")][0]["spacing_mm"], 110)
            self.assertEqual(transverse[("S2", "R1")][0]["spacing_mm"], 210)
            self.assertIn("210 mm", schedule[("S2", "R1")][0]["transverse_label"])

    def test_explicit_zero_results_do_not_turn_missing_data_into_compatibility(self):
        with preview_fixture() as (job, _):
            regions = preview_service.build_job_preview_payload(job)["spans"][1]["regions"]
        self.assertTrue(preview_service._has_only_zero_longitudinal_results(regions[1]))
        for row in regions[1]["options"]:
            row["weight_longitudinal_kg"] = None
        self.assertFalse(preview_service._has_only_zero_longitudinal_results(regions[1]))
        self.assertEqual(preview_service._build_span_longitudinal_base_options(regions), [])

    def test_wholly_zero_longitudinal_span_retains_zero_base_choice(self):
        with preview_fixture() as (job, _):
            region = preview_service.build_job_preview_payload(job)["spans"][1]["regions"][1]
        bases = preview_service._build_span_longitudinal_base_options([region])
        self.assertEqual(bases[0]["base_label"], "no se requiere")
        self.assertEqual(bases[0]["long_weight_kg"], 0)
        sets = preview_service._build_span_longitudinal_option_sets([region], bases)
        self.assertEqual(sets[0]["total_longitudinal_weight_kg"], 0)

    def test_endpoint_keeps_six_distinct_regions_and_separate_bases(self):
        with preview_fixture() as (job, _):
            response = TestClient(app).get(f"/v1/jobs/{job}/preview")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual([s["span_id"] for s in payload["spans"]], ["S1", "S2"])
        for si, span in enumerate(payload["spans"]):
            self.assertEqual([r["region_id"] for r in span["regions"]], ["R1", "R2", "R3"])
            self.assertEqual([r["transverse_options"][0]["spacing_mm"] for r in span["regions"]],
                             [110, 120, 130] if si == 0 else [210, 220, 230])
            self.assertTrue(span["longitudinal_base_options"])
            self.assertIn("#5" if si == 0 else "#6", span["longitudinal_base_options"][0]["base_label"])
            self.assertEqual(len(span["span_longitudinal_option_sets"][0]["regions"]), 3)
        inactive = payload["spans"][1]["regions"][1]
        self.assertTrue(all(o["weight_longitudinal_kg"] == 0 for o in inactive["options"]))
        self.assertTrue(all(o["base_longitudinal_label"] == "no se requiere" for o in inactive["options"]))
        self.assertAlmostEqual(payload["optimal_beam_weight_kg"], 250)

    def test_case_order_is_preserved_without_lexical_sorting(self):
        with preview_fixture(("S1", "S2", "S10")) as (job, _):
            payload = preview_service.build_job_preview_payload(job)
        self.assertEqual([s["span_id"] for s in payload["spans"]], ["S1", "S2", "S10"])

    def test_save_and_reload_preserves_choices_in_both_spans_and_totals(self):
        with preview_fixture() as (job, meta):
            client = TestClient(app)
            payload = client.get(f"/v1/jobs/{job}/preview").json()
            selections = []
            for span in payload["spans"]:
                for region in span["regions"]:
                    option = region["options"][0]
                    if (span["span_id"], region["region_id"]) in {("S1", "R1"), ("S2", "R2")}:
                        alternative = region["transverse_options"][1]["label"]
                        option = next(o for o in region["options"] if o["transverse_label"] == alternative)
                    selections.append({"span_id": span["span_id"], "region_id": region["region_id"],
                                       **{k: option[k] for k in ("transverse_label", "longitudinal_label", "base_longitudinal_label", "additional_longitudinal_label")}})
            response = client.post(f"/v1/jobs/{job}/selection", json={"selections": selections})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["saved_regions"], 6)
            saved = json.loads(Path(meta["artifacts"]["selection_applied.json"]).read_text())
            self.assertAlmostEqual(saved["totals"]["best_weight_kg"], 250)
            self.assertAlmostEqual(saved["totals"]["selected_weight_kg"], 254)
            reloaded = client.get(f"/v1/jobs/{job}/preview").json()
            actual = {(s["span_id"], r["region_id"]): r for s in reloaded["saved_selection"]["spans"] for r in s["regions"]}
            for expected in selections:
                self.assertEqual(actual[(expected["span_id"], expected["region_id"])]["transverse_label"], expected["transverse_label"])
            rendered = render_in_browser(reloaded)
            self.assertIn("254.00 kg", rendered["summary"])
            self.assertIn("1.60 %", rendered["summary"])

    def test_renderer_contains_both_spans_and_sums_100_plus_150(self):
        with preview_fixture() as (job, _):
            payload = preview_service.build_job_preview_payload(job)
        rendered = render_in_browser(payload)
        self.assertEqual(rendered["spans"], ["Vano S1", "Vano S2"])
        self.assertEqual(rendered["regions"], [3, 3])
        self.assertEqual(len(rendered["payload"]["selections"]), 6)
        self.assertEqual(rendered["summary"].count("250.00 kg"), 2)
        self.assertIn("0.00 %", rendered["summary"])
        self.assertFalse(rendered["disabled"])

    def test_renderer_keeps_single_span_and_more_than_two_spans(self):
        for ids in (("S1",), ("S1", "S2", "S10")):
            with self.subTest(ids=ids), preview_fixture(ids) as (job, _):
                result = render_in_browser(preview_service.build_job_preview_payload(job))
                self.assertEqual(result["spans"], ["Vano " + s for s in ids])
                self.assertEqual(result["regions"], [3] * len(ids))

    def test_changing_base_keeps_inactive_region_zero_and_other_span_unchanged(self):
        with preview_fixture() as (job, _):
            payload = preview_service.build_job_preview_payload(job)
        rendered = render_in_browser(payload, """
const base=document.querySelectorAll('.span-opt-longitudinal')[1];
base.selectedIndex=1;base.dispatchEvent(new Event('change'));
""")
        rows = resolve_selected_options(payload, JobSelectionSaveRequest.model_validate(rendered["payload"]))
        self.assertAlmostEqual(sum(r["selected_weight_kg"] for r in rows if r["span_id"] == "S1"), 100)
        inactive = next(r for r in rows if (r["span_id"], r["region_id"]) == ("S2", "R2"))
        self.assertEqual(inactive["selected_longitudinal_weight_kg"], 0)
        self.assertEqual(inactive["selected_base_longitudinal_label"], "no se requiere")

    def test_missing_catalog_is_visible_and_cannot_report_partial_beam_weight(self):
        with preview_fixture() as (job, _):
            payload = preview_service.build_job_preview_payload(job)
        payload["spans"][1]["longitudinal_base_options"] = []
        result = render_in_browser(payload)
        self.assertEqual(result["spans"], ["Vano S1", "Vano S2"])
        self.assertTrue(result["disabled"])
        self.assertIn("n/d", result["summary"])


if __name__ == "__main__":
    unittest.main()
