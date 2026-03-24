from __future__ import annotations

import argparse
import io
import time
from pathlib import Path
from zipfile import ZipFile

import httpx

EXPECTED_REPORTS = {
    "design_results.xlsx",
    "summary.xlsx",
    "optimized_results.xlsx",
    "reinforcement_schedule.xlsx",
    "run_log.txt",
}


def _headers(api_key: str | None) -> dict[str, str]:
    if not api_key:
        return {}
    return {"X-API-Key": api_key}


def _wait_terminal_status(
    client: httpx.Client,
    *,
    base_url: str,
    job_id: str,
    timeout_seconds: float,
    headers: dict[str, str],
) -> dict:
    deadline = time.time() + timeout_seconds
    last_payload: dict | None = None
    while time.time() < deadline:
        response = client.get(f"{base_url}/v1/jobs/{job_id}", headers=headers)
        response.raise_for_status()
        payload = response.json()
        last_payload = payload
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.5)
    raise RuntimeError(f"Job {job_id} no termino a tiempo. Ultimo estado: {last_payload}")


def run_smoke(
    *,
    base_url: str,
    case_json: Path,
    seismic_excel: Path,
    gravity_excel: Path,
    api_key: str | None,
    timeout_seconds: float,
) -> None:
    base_url = base_url.rstrip("/")
    headers = _headers(api_key)
    timeout = httpx.Timeout(60.0)
    with httpx.Client(timeout=timeout) as client:
        health = client.get(f"{base_url}/", headers=headers)
        health.raise_for_status()
        health_payload = health.json()
        if health_payload.get("status") != "ok":
            raise RuntimeError(f"Healthcheck inesperado: {health_payload}")
        print("Healthcheck OK")

        with (
            case_json.open("rb") as case_stream,
            seismic_excel.open("rb") as seismic_stream,
            gravity_excel.open("rb") as gravity_stream,
        ):
            files = {
                "case_json": ("case.json", case_stream, "application/json"),
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
            }
            create_response = client.post(f"{base_url}/v1/jobs", files=files, headers=headers)
        create_response.raise_for_status()
        if create_response.status_code != 202:
            raise RuntimeError(f"Status inesperado al crear job: {create_response.status_code}")
        job_id = create_response.json()["job_id"]
        print(f"Job creado: {job_id}")

        final_status = _wait_terminal_status(
            client,
            base_url=base_url,
            job_id=job_id,
            timeout_seconds=timeout_seconds,
            headers=headers,
        )
        if final_status["status"] != "completed":
            raise RuntimeError(f"Job fallo en smoke: {final_status}")
        print("Job completado")

        download_response = client.get(f"{base_url}/v1/jobs/{job_id}/download", headers=headers)
        download_response.raise_for_status()
        if download_response.status_code != 200:
            raise RuntimeError(f"Status inesperado en descarga: {download_response.status_code}")
        with ZipFile(io.BytesIO(download_response.content)) as zip_file:
            names = set(zip_file.namelist())
        missing = sorted(EXPECTED_REPORTS - names)
        if missing:
            raise RuntimeError(f"Faltan artefactos en ZIP: {missing}")
        print("Descarga ZIP OK")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="smoke_api")
    parser.add_argument("--base-url", required=True, help="Base URL de la API")
    parser.add_argument(
        "--case-json",
        default="examples/case_0001/case.json",
        help="Ruta a case.json",
    )
    parser.add_argument(
        "--seismic-excel",
        default="examples/case_0001/sismo.xlsx",
        help="Ruta al Excel sismico",
    )
    parser.add_argument(
        "--gravity-excel",
        default="examples/case_0001/gravedad.xlsx",
        help="Ruta al Excel de gravedad",
    )
    parser.add_argument("--api-key", default=None, help="API key opcional")
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    run_smoke(
        base_url=args.base_url,
        case_json=Path(args.case_json),
        seismic_excel=Path(args.seismic_excel),
        gravity_excel=Path(args.gravity_excel),
        api_key=args.api_key,
        timeout_seconds=args.timeout_seconds,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
