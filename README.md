# Structure Lab

API (FastAPI) + motor de calculo para diseno/optimizacion de refuerzo en vigas RC por cortante y torsion usando exportes ETABS.

## Documentacion de arquitectura

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ENGINEERING_REPO_STANDARD.md](ENGINEERING_REPO_STANDARD.md)
- [ENGINEERING_REPO_TEMPLATE.md](ENGINEERING_REPO_TEMPLATE.md)

## Inicio rapido

### 1) Instalar

```powershell
python3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

### 2) Ejecutar API

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 10000
```

### 3) Usar

- UI: `http://127.0.0.1:10000/ui`
- Docs: `http://127.0.0.1:10000/docs`

## Flujo recomendado (usuario final)

1. Abrir `/ui`.
2. Cargar `seismic_excel` y `gravity_excel`.
3. (Opcional) Cargar `geometry_excel` para mapear `Width/Depth` por vano (`DesignSect` <-> `Name`).
4. (Opcional, por vano) Ajustar `L libre real (mm)` desde UI avanzada (`span_layout_json.clear_length_mm`).
   Regla actual del motor: `L_libre_modelo_mm = station_diff`.
   Si existe `clear_length_mm`, esa longitud se usa para calcular longitudes de region y conteo de estribos.
5. Crear job.
6. Revisar estado y descargar resultados.

## Fixture de ejemplo

- `examples/case_0001/` es el caso base para pruebas, smoke y ejemplos de uso.
- `storage/jobs/` es la salida real de la app web por cada job.

## Endpoints clave

- `GET /` -> healthcheck.
- `POST /v1/jobs` -> crea job desde `case_json + 2 excel`.
- `POST /v1/jobs/from-form` -> crea job desde formulario + archivos.
- `GET /v1/jobs/{job_id}` -> estado (`queued|running|completed|failed`).
- `GET /v1/jobs/{job_id}/case` -> case normalizado.
- `GET /v1/jobs/{job_id}/preview` -> datos para vista en alzado.
- `GET /v1/jobs/{job_id}/download` -> ZIP de reportes.
- `GET /v1/jobs/{job_id}/artifacts/{artifact_name}` -> artefacto puntual.

## Estructura de salida por job

Cada job se guarda en `APP_STORAGE_DIR/jobs/<job_id>/`:

- `input/` -> `case.json`, `seismic.xlsx`, `gravity.xlsx`
- `output/<case_name>/` -> reportes Excel + `run_log.txt`
- `job.json` -> estado, timestamps, rutas y metadatos

Esto es util para trazabilidad y para futuros pipelines de ML.

## Ejecutar por CLI (compatibilidad)

```powershell
python -m rc_shear_torsion.run examples/case_0001/case.json --out storage/cli_runs
```

## Variables de entorno

- `APP_ENV` (default: `production`)
- `APP_STORAGE_DIR` (default: `storage`; en Render Free usar `/tmp/storage`)
- `APP_API_KEY` (opcional, activa `X-API-Key` en `/v1/jobs*`)
- `APP_MAX_UPLOAD_MB` (default: `25`)
- `APP_LOG_LEVEL` (default: `INFO`)

## Deploy en Render

Repositorio listo con `render.yaml` (Blueprint):

- Build: `pip install -r requirements.txt && pip install .`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port 10000`

Nota Free tier:

- Sin disco persistente en Blueprint (`/tmp/storage` es efimero).

## Smoke test de deploy

Workflow: `.github/workflows/render-smoke.yml`

Script: `scripts/smoke_api.py`

## Ejemplo curl rapido

```bash
curl -X POST "http://127.0.0.1:10000/v1/jobs" \
  -F "case_json=@examples/case_0001/case.json;type=application/json" \
  -F "seismic_excel=@examples/case_0001/sismo.xlsx" \
  -F "gravity_excel=@examples/case_0001/gravedad.xlsx"
```

```bash
curl "http://127.0.0.1:10000/v1/jobs/<job_id>"
curl -L "http://127.0.0.1:10000/v1/jobs/<job_id>/download" -o reports.zip
```


## Modo longitudinal (GA acoplado por vano)

El sistema soporta dos modos en `optimization.longitudinal_mode`:

- `legacy_region_independent` (Dise?o independiente por regi?n (legacy), default): flujo historico por region.
- `span_coupled` (Dise?o acoplado por tramo): optimizacion acoplada por vano con:
  - refuerzo longitudinal base continuo por vano,
  - refuerzo longitudinal adicional por region,
  - chequeos deep-beam cuando `is_deep_beam=true`.

Si no se envia el campo, se mantiene compatibilidad con `legacy_region_independent`.

### Configuracion avanzada por vano

En `span_layout_json` cada vano acepta:

- `is_deep_beam` (opcional, default `false`).
- alias aceptado: `viga_alta`.

### Seleccion de resultados (API)

Endpoint: `POST /v1/jobs/{job_id}/selection`

- `selections`: contrato legacy por region.
- `span_selections` (opcional): seleccion longitudinal por vano para `span_coupled`.

Compatibilidad: ambos pueden coexistir; el backend mantiene el contrato previo.


