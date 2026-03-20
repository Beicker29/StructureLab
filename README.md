# ShearTors_RC

API y motor de calculo para diseno/optimizacion de refuerzo de vigas de concreto reforzado por cortante y torsion, usando exportes de ETABS.

## Que hace el proyecto

- Lee un `case.json` con configuracion de vigas/vanos/regiones.
- Carga dos archivos Excel ETABS (sismico y gravedad).
- Calcula demanda por region y optimiza refuerzo transversal/longitudinal.
- Genera reportes:
  - `design_results.xlsx`
  - `summary.xlsx`
  - `optimized_results.xlsx`
  - `reinforcement_schedule.xlsx`
  - `run_log.txt`

El motor de negocio sigue en `src/rc_shear_torsion/` y puede ejecutarse por CLI o por API FastAPI.

## Estructura principal

```text
ShearTors_RC/
|-- app/
|   |-- main.py
|   |-- core/
|   |-- dependencies/
|   |-- models/
|   |-- routers/
|   |-- schemas/
|   `-- services/
|-- src/rc_shear_torsion/
|-- cases/
|-- requirements.txt
|-- render.yaml
`-- pyproject.toml
```

## Requisitos

- Python `3.12.x`

## Ejecucion local

### 1) Instalar dependencias

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

Swagger UI:

- `http://127.0.0.1:10000/docs`

### 3) Ejecutar por CLI (compatibilidad)

```powershell
python -m rc_shear_torsion.run cases/case_0001/case.json --out results/
```

## Variables de entorno

- `APP_ENV` (default: `production`)
- `APP_STORAGE_DIR` (default: `storage`)
- `APP_API_KEY` (opcional, si se define exige header `X-API-Key` en `/v1/jobs*`)
- `APP_MAX_UPLOAD_MB` (default: `25`)
- `APP_LOG_LEVEL` (default: `INFO`)

## Endpoints API

### GET `/`

Healthcheck del servicio.

### POST `/v1/jobs`

Crea trabajo asincrono con `multipart/form-data`:

- `case_json` (`.json`)
- `seismic_excel` (`.xlsx`)
- `gravity_excel` (`.xlsx`)

Respuesta `202`:

- `job_id`
- `status_url`
- `download_url`

### GET `/v1/jobs/{job_id}`

Consulta estado (`queued`, `running`, `completed`, `failed`), timestamps y artefactos.

### GET `/v1/jobs/{job_id}/download`

Descarga ZIP con reportes al estar `completed`.

## Ejemplos curl

### Crear job

```bash
curl -X POST "http://127.0.0.1:10000/v1/jobs" \
  -F "case_json=@cases/case_0001/case.json;type=application/json" \
  -F "seismic_excel=@cases/case_0001/sismo.xlsx" \
  -F "gravity_excel=@cases/case_0001/gravedad.xlsx"
```

Con API key:

```bash
curl -X POST "http://127.0.0.1:10000/v1/jobs" \
  -H "X-API-Key: TU_API_KEY" \
  -F "case_json=@cases/case_0001/case.json;type=application/json" \
  -F "seismic_excel=@cases/case_0001/sismo.xlsx" \
  -F "gravity_excel=@cases/case_0001/gravedad.xlsx"
```

### Consultar estado

```bash
curl "http://127.0.0.1:10000/v1/jobs/<job_id>"
```

### Descargar resultados

```bash
curl -L "http://127.0.0.1:10000/v1/jobs/<job_id>/download" -o reports.zip
```

## Despliegue en Render

Este repo ya incluye `render.yaml` listo para Blueprint deploy.

### Pasos

1. Sube cambios a GitHub.
2. En Render, crea un **Blueprint** apuntando al repo.
3. Render leera `render.yaml` y configurara:
   - Build: `pip install -r requirements.txt && pip install .`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
   - Disco persistente en `/var/data` (para `storage`).
4. Si deseas proteger API, define `APP_API_KEY` en Render.
5. Despliega y prueba:
   - `GET /`
   - `GET /docs`
   - flujo de `POST /v1/jobs` -> `GET /v1/jobs/{id}` -> `GET /download`.

## Notas tecnicas

- La logica de negocio no se reescribio; se encapsulo para ser llamada desde servicios API.
- El procesamiento se ejecuta asincronamente por `job_id` para reducir riesgo de timeout en web.
- El estado se persiste por archivos JSON en `APP_STORAGE_DIR/jobs/<job_id>/job.json`.
