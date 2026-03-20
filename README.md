# ShearTors_RC

Backend Python para diseno y optimizacion de refuerzo de vigas de concreto reforzado por cortante y torsion usando resultados ETABS exportados a Excel.

## Estructura

```text
ShearTors_RC/
|-- pyproject.toml
|-- cases/
|-- results/
`-- src/
    `-- rc_shear_torsion/
        |-- run.py
        |-- io.py
        |-- models.py
        |-- design.py
        `-- report.py
```

## Requisito de Python

Este proyecto esta fijado a Python 3.12.x:

- `>=3.12,<3.13`

## Crear entorno virtual (Python 3.12)

```powershell
python3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install -e .
```

## Comando principal

```powershell
python -m rc_shear_torsion.run cases/case_0001/case.json --out results/
```

La ejecucion genera:

- `results/<case_name>/design_results.xlsx`
- `results/<case_name>/summary.xlsx`
- `results/<case_name>/optimized_results.xlsx`
- `results/<case_name>/reinforcement_schedule.xlsx` (top 5 alternativas por region para arreglo de estribos, cada una con su mejor refuerzo longitudinal y resumen por vano usando opcion 1)
- `results/<case_name>/run_log.txt`

En los reportes por region se incluye la columna `controlling_limit` (o `limite_controlante` en `por_region`) con el criterio que gobierna la separacion maxima de estribos (`d/4`, `d/2`, `16db`, `48dest`, `Ph/8`, etc.).

## Notas de implementacion

- `case.json` se valida con Pydantic.
- Barras permitidas en todo el flujo (`db_bar`, `E_bars`, `G_bars`, `longitudinal_bars`): `#2` a `#11`.
- Datos internos de calculo usan dataclasses.
- `VRebar` y `TTrnRebar` se convierten a base `mm2/m`.
- `TLngRebar` se trata como area puntual requerida por estacion (`mm2`) y se envuelve por region.
- `beam.detailing` admite `DES` y `DMO` (default: `DES`).
- Recubrimientos se definen por viga: `cover_side_mm`, `cover_top_mm`, `cover_bottom_mm`.
- Cada region define:
  - detallado DMO:
    - zona `C`: `d_mm`, `db_bar`, `min_branches`
    - zona `NC`: `d_mm`, `db_bar`
  - geometria para peso real: `width_mm`, `height_mm`
- Con optimizacion activa, la geometria por region es obligatoria.
- Para vigas `DMO`, las regiones `C` deben definir `d_mm`, `db_bar` y `min_branches` (con `min_branches >= 4`).
- Para vigas `DES`, las regiones `C` deben definir `d_mm` y `db_bar`.
- En vigas `DES` y region `C`, se verifica:
  - `s <= min(d/4, 6*db, 150, 16*db, 48*dest, Ph/8)`
- Para vigas `DMO` con regiones `NC`, la viga debe definir `fc_mpa` y `fy_mpa`.
- En vigas `DMO` y region `C`, se verifica:
  - `s <= min(d/4, 8*db, 150, 16*db, 48*dest, 24*dest)`
  - ramas minimas: `provided = 2 + G_count` y debe cumplir `provided >= min_branches`
- En vigas `DMO` y region `NC`, se verifica como restriccion dura:
  - `s <= min(d/4 o d/2 segun Vrebar*fy*d, 16*db, 48*dest, Ph/8 si TTrnRebar > 0)`
- Restriccion dura de optimizacion: si `G_counts` no incluye algun `G_count >= (min_branches - 2)` para una region `DMO` tipo `C`, el `case.json` se rechaza en validacion.
- Independencia de diseño:
  - la factibilidad de optimizacion se resuelve con restricciones de refuerzo transversal (torsion, cortante y detallado DMO).
  - el refuerzo longitudinal se selecciona en una etapa independiente usando el menor arreglo disponible que cumpla `TLngRebar_req`.
- Objetivo `min_weight`: minimiza peso total por region (kg/m), sumando:
  - transversal real (estribo + ganchos) usando longitudes por geometria de seccion y separacion `s`
  - longitudinal independiente: `Along = area(long_bar) * long_count`, convertido a kg/m
- Supuestos geometricos para el peso transversal:
  - longitud estribo exterior = perimetro a eje + 2 ganchos
  - longitud de cada gancho/ramal adicional = ancho a eje + 2 ganchos
  - longitudes de gancho fijas: `#3 = 110 mm`, `#4 = 120 mm`, `#5 = 140 mm`
  - para otras barras (si se usan), fallback = `10*phi`
