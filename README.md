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
- UI para usuario final (sin editar `case.json`):
  - `http://127.0.0.1:10000/ui`

### 3) Ejecutar por CLI (compatibilidad)

```powershell
python -m rc_shear_torsion.run cases/case_0001/case.json --out results/
```

## Variables de entorno

- `APP_ENV` (default: `production`)
- `APP_STORAGE_DIR` (default: `storage`; en Render Free usar `/tmp/storage`)
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

### POST `/v1/jobs/from-form`

Crea trabajo asincrono desde formulario + 2 Excel (sin `case.json` manual).

Campos principales:

- Archivos: `seismic_excel`, `gravity_excel`
- Caso: `case_name`, `sheet_name`, `units_rebar_per_length`
- Viga: `beam_id`, `detailing`, recubrimientos, `fc_mpa`, `fy_mpa`
- Geometria/regiones base: `width_mm`, `height_mm`, `d_mm`, `db_bar`, `min_branches_c`, `min_branches_nc`, `region_c_ratio`
- Vanos:
  - `frame_names_csv` (opcional, lista de `UniqueName` comunes), o
  - `frame_pairs_json` (opcional, mapeo avanzado `seismic/gravity`)

Si no defines vanos manualmente, la API usa automaticamente la interseccion de `UniqueName` entre ambos Excel.

### GET `/v1/jobs/{job_id}`

Consulta estado (`queued`, `running`, `completed`, `failed`), timestamps y artefactos.

### GET `/v1/jobs/{job_id}/download`

Descarga ZIP con reportes al estar `completed`.

### GET `/v1/jobs/{job_id}/case`

Devuelve el `case.json` generado/normalizado para auditoria.

### Contrato de errores de dominio/aplicacion

Los errores propios de la API (uploads invalidos, dominio, job no encontrado/no listo) responden con:

```json
{
  "error": "codigo_estable",
  "message": "descripcion legible",
  "details": []
}
```

Para errores de reglas de negocio (`domain_validation_error`), `details` contiene lista de issues con:

- `code`
- `field`
- `message`
- `severity`
- `context` (opcional)

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

### Crear job desde formulario (sin case.json)

```bash
curl -X POST "http://127.0.0.1:10000/v1/jobs/from-form" \
  -F "case_name=case_web" \
  -F "sheet_name=Conc Bm Sum - ACI 318-08" \
  -F "detailing=DMO" \
  -F "units_rebar_per_length=mm2/m" \
  -F "beam_id=B1" \
  -F "cover_side_mm=40" \
  -F "cover_top_mm=40" \
  -F "cover_bottom_mm=40" \
  -F "fc_mpa=28" \
  -F "fy_mpa=420" \
  -F "width_mm=300" \
  -F "height_mm=600" \
  -F "d_mm=600" \
  -F "db_bar=#6" \
  -F "min_branches_c=4" \
  -F "min_branches_nc=2" \
  -F "region_c_ratio=0.2" \
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
   - Storage temporal en `/tmp/storage` (compatible con plan `free`).
4. Si deseas proteger API, define `APP_API_KEY` en Render.
5. Despliega y prueba:
   - `GET /`
   - `GET /docs`
   - `GET /ui`
   - flujo de `POST /v1/jobs` -> `GET /v1/jobs/{id}` -> `GET /download`.

### Nota sobre almacenamiento en Render Free

- El plan `free` no soporta `disk` en `render.yaml`, por eso el storage es efimero (`/tmp/storage`).
- Si necesitas persistencia entre reinicios, cambia a plan pago y agrega un disco montado (por ejemplo en `/var/data`) con `APP_STORAGE_DIR=/var/data/storage`.

## CI y smoke checks

- CI en GitHub Actions: `.github/workflows/ci.yml`
  - instala dependencias
  - corre `unittest`
  - levanta FastAPI local y ejecuta smoke end-to-end
- Smoke post-deploy (manual): `.github/workflows/render-smoke.yml`
  - usa `scripts/smoke_api.py` contra tu URL de Render
  - opcionalmente lee `RENDER_API_KEY` desde secrets

## Notas tecnicas

- La logica de negocio no se reescribio; se encapsulo para ser llamada desde servicios API.
- El procesamiento se ejecuta asincronamente por `job_id` para reducir riesgo de timeout en web.
- El estado se persiste por archivos JSON en `APP_STORAGE_DIR/jobs/<job_id>/job.json`.
