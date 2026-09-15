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
  - refuerzo longitudinal adicional por region.

Si no se envia el campo, se mantiene compatibilidad con `legacy_region_independent`.

El acero longitudinal calculado por este flujo corresponde exclusivamente a
torsion. Una region sin escenarios `ACTIVE` reporta area, barra y cantidad
longitudinal torsional nulas, incluso cuando siga requiriendo refuerzo
transversal por cortante o detallado sismico.

## Dominio dinamico de espaciamientos

Cuando `optimization.variables.stirrup_spacing_mm` se omite, el motor genera
los candidatos de cada region desde `stirrup_spacing_min_mm` (70 mm por
defecto), con incremento `stirrup_spacing_step_mm` (10 mm por defecto), hasta
el mayor multiplo del incremento que no exceda `s_max_real`. Este ultimo es el
menor entre los limites ACI evaluados, el limite de demanda del esquema de
barras y `stirrup_spacing_project_max_mm` si se configuro explicitamente.

No existe un maximo global de espaciamiento. El antiguo catalogo implicito
70..200 mm se reconoce como entrada heredada y se sustituye por el dominio
dinamico. Una lista distinta en `stirrup_spacing_mm` se conserva como catalogo
discreto explicito por compatibilidad.

## Procedencia de la altura efectiva

Los casos construidos desde el formulario calculan `d_mm` como
`height_mm * d_ratio`. Si el vano no define una razon propia, se usa
`d_ratio_default=0.9` y se conserva `d_source=DEFAULT_RATIO` junto con
`d_ratio=0.9`. Por tanto, ese valor es una aproximacion y no una geometria
exacta obtenida del arreglo de refuerzo. Un `d_mm` regional suministrado
explicitamente se identifica con `d_source=EXPLICIT`; una razon propia del
vano, con `d_source=SPAN_RATIO`. Los casos JSON heredados pueden no tener
procedencia porque los campos nuevos son opcionales.

El diametro longitudinal y la condicion de refuerzo a compresion no modifican
`d`. El modulo no calcula `d` a partir del recubrimiento, diametro del estribo
o diametro/disposicion de barras longitudinales.

## Datos longitudinales para detallado de ties

Cada vano admite `longitudinal_bar_diameter_mm` y
`compression_rebar_required` (por defecto `false`). El diametro representa una
barra longitudinal individual, igual para el refuerzo superior e inferior, y
solo aporta contexto a las reglas de detallado y a los limites sismicos que
dependen de `db`. No es refuerzo longitudinal disenado por StructureLab y se
mantiene separado del refuerzo longitudinal requerido por torsion.

`compression_rebar_required=true` significa exclusivamente que el refuerzo
longitudinal se contabiliza como refuerzo a compresion requerido por diseno.
Activa las verificaciones de ACI 318M-25 9.7.6.4.2 y 9.7.6.4.3. No significa
solo que existan barras superiores o barras en la cara comprimida.

Las barras longitudinales agrupadas quedan fuera del alcance y el contrato
fija `longitudinal_bars_bundled=false`. ACI 9.7.6.4.4 y la comprobacion
geometrica remitida por 18.6.4.2 a 25.7.2.3 permanecen `NOT_EVALUATED` cuando
aplican, porque el modulo no conoce la cantidad ni la posicion transversal de
las barras, crossties o distancias libres.

### Seleccion de resultados (API)

Endpoint: `POST /v1/jobs/{job_id}/selection`

- `selections`: contrato legacy por region.
- `span_selections` (opcional): seleccion longitudinal por vano para `span_coupled`.

Compatibilidad: ambos pueden coexistir; el backend mantiene el contrato previo.
