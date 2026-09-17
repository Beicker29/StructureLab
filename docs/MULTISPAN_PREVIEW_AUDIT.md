# Corrección pre-Fase 4: alternativas en vigas multivano

## Alcance y estado inicial

Se diagnosticó primero, sin editar producción, y luego se corrigió únicamente
propagación, agrupación, preview, render y restauración de selección. No se
cambió ingeniería ni se avanzó a Fase 4.

Rama `main`. Había cambios locales de la limpieza anterior en arquitectura,
servicios, imports y motor, además de archivos nuevos sin seguimiento. Se
preservaron íntegramente; no deben atribuirse a esta corrección los cambios
preexistentes de `design.py`, `models.py`, `span_coupled.py` o `results_model.py`.
No commit, push, reset ni descarte.

Caso real localizado: job `26d78edf38a94171ab85288cb505cd76`, viga B1,
S1 de 8400 mm y S2 de 8300 mm, R1/R2/R3 en ambos. Coincide con el peso
óptimo 419,50 kg y el seleccionado 237,72 kg de la solicitud.
Los archivos de este job se usaron solo para lectura; no fueron reescritos.

## Diagnóstico anterior a la corrección

| Capa | Evidencia anterior |
| --- | --- |
| Motor | 2 vanos; 3 resultados regionales en S1 y 3 en S2 |
| Canónico | 6 identidades `(B1, span_id, region_id)`, sin pérdida |
| `optimized_results.xlsx` | 3 filas S1 y 3 filas S2 |
| `reinforcement_schedule.xlsx`, `por_region` | 63 filas S1 y 63 filas S2, 3 regiones por vano |
| Mismo XLSX, `por_vano` | 1 fila S1 y 1 fila S2 |
| Mismo XLSX, `transversales` | 30 filas S1 y 30 filas S2 |
| Servicio preview | 2 vanos y 6 regiones; catálogo de bases: S1=10, S2=0 |
| GET `/v1/jobs/{id}/preview` | 2 vanos, confirmado con TestClient |
| Entrada JavaScript | 2 vanos |
| DOM de `renderRegionOptions` | Solo `Vano S1`, 3 regiones |
| Payload de guardado JavaScript | 6 regiones, aunque solo 3 se mostraban |

Para observar el motor se volvió a ejecutar el caso con sus entradas reales,
interceptando los escritores en memoria para no cambiar los artefactos del job.
La conversión canónica se aplicó a los resultados capturados.

### Causa raíz exacta

1. El resultado longitudinal torsional de S2/R2 es explícitamente nulo:
   `base_longitudinal_label="no se requiere"`, cantidad nula y peso cero.
   Sus extremos sí tienen bases longitudinales torsionales.
2. `_build_span_longitudinal_base_options` intersectaba las etiquetas de base
   de **todas** las regiones, como si debieran tener la misma etiqueta regional.
   La intersección de etiquetas activas con `{"no se requiere"}` era vacía.
3. Por ello S2 llegaba al JSON, pero sin catálogo de bases ni conjuntos
   longitudinales. También quedaban sin opciones sus adicionales por base.
4. En `renderRegionOptions`, `if(!spanBaseOptions.length)return` descartaba
   completamente el vano antes de crear su bloque DOM.
5. El resumen sumaba pesos seleccionados solo de los estados renderizados,
   pero usaba como óptimo el total backend de ambos vanos.

**S2 no se perdía en el motor ni en XLSX: su catálogo se vaciaba en el preview y
su bloque desaparecía en el retorno temprano del renderer.**

### Auditoría de las hipótesis solicitadas

- A/B/C/D/I: no hay selección del primer vano ni `break` del bucle de vanos.
  Los `next` revisados eligen opciones específicas, no un único vano.
- E/F/G: motor y reportes usan identidad viga/vano/región; el preview y las
  selecciones usan vano/región dentro de la viga mostrada. Se detectó además
  que los lectores XLSX no filtraban viga antes de formar esas claves; ahora
  filtran por la viga del preview, evitando colisiones B1/S1/R1–B2/S1/R1.
- H: el parser no eliminaba S2 del XLSX. La eliminación lógica afectaba al
  catálogo de bases, después de leer las filas.
- J: no se reutiliza un mismo bloque DOM entre vanos. Se crean `details`
  independientes, pero antes S2 no llegaba a crearlos.
- K: el catálogo del motor existe para ambos vanos; el derivado del preview
  quedaba vacío solo en S2.
- L: no se cambiaron filtros de factibilidad ni catálogos del optimizador.
  El defecto era la intersección de etiquetas de presentación.

## Corrección y estructura posterior

Antes:

```text
preview.spans = [S1(R1,R2,R3), S2(R1,R2,R3)]
bases/sets: S1=10/10, S2=0/0
DOM: [S1]
selected total: suma de S1
```

Después:

```text
preview.spans = [S1(R1,R2,R3), S2(R1,R2,R3)]
bases/sets: S1=10/10, S2=10/10
DOM: [S1, S2]
selected total: suma de S1 + suma de S2
```

- Los resultados regionales explícitamente nulos no restringen la etiqueta de
  base del vano. Aportan sus propias opciones originales, con acero/peso cero,
  a cada conjunto compatible. Esto reconoce datos de resultados, no decide
  aplicabilidad normativa ni extiende acero torsional hacia otra región.
- Los conjuntos y adicionales transportan `base_longitudinal_label` regional.
  Así, S2/R2 sigue diciendo «no se requiere», aunque el control del vano tenga
  una base necesaria para otras regiones.
- Datos longitudinales faltantes no se confunden con resultados nulos: la
  compatibilidad exige etiquetas explícitas, peso cero y ausencia de cantidades.
- Se mantiene el orden del caso, no un orden lexicográfico de IDs.
- Si un catálogo está incompleto, el vano permanece visible y el resumen
  seleccionado/diferencia se muestra `n/d`; se bloquea el guardado desde la UI.
- `saved_selection` restaura las filas de `selection_applied.json` en su vano
  y región. La clave de caché incluye la modificación del archivo de selección.
  `default_selection` sigue representando el óptimo, no se sustituye por lo guardado.
- La elección personalizada de base y de adicional se conserva al reconstruir
  controles. La selección transversal válida mantiene su prioridad previa.

## Pesos antes/después del caso real

Valores iniciales, sin modificaciones manuales de alternativas:

| Magnitud | Antes | Después |
| --- | ---: | ---: |
| `optimal_weight`, viga completa | 419,496719 kg | 419,496719 kg |
| `selected_weight`, mostrado como viga completa | 237,719821 kg | 419,496719 kg |
| Aporte de S1 seleccionado | 237,719821 kg | 237,719821 kg |
| Aporte de S2 incluido en el resumen seleccionado | Omitido | 181,776898 kg |
| `delta_percent` mostrado | −43,33 % | 0,00 % |
| Vanos motor / preview / DOM | 2 / 2 / 1 | 2 / 2 / 2 |
| Regiones DOM por vano | S1=3; S2 ausente | S1=3; S2=3 |

No cambió la fórmula de peso ni la fórmula porcentual: ahora las magnitudes
comparadas incluyen los mismos vanos. Una comparación serializada de las seis
regiones del caso real confirma que `options` y `transverse_options` son
idénticos antes/después, incluido su orden y pesos. El óptimo también es idéntico.

## Archivos modificados en esta tarea

- `app/services/job_preview_service.py`: asociación base de vano/resultado
  regional nulo; etiquetas regionales; lectura de selección y caché; filtro de
  identidad de viga al leer artefactos.
- `app/ui/static/ui.js`: render sin omisión silenciosa, integridad del resumen,
  uso de la etiqueta regional y restauración de selecciones personalizadas.
- `tests/test_multispan_preview.py`: fixtures de resultados distinguibles y
  pruebas de integración, endpoint, persistencia y renderer.
- `README.md`: comportamiento multivano y contrato aditivo `saved_selection`.
- Este informe.

## Pruebas y verificación

Dos regresiones fallaron antes de editar producción: catálogo de S2 vacío y
DOM con solo S1. Después pasan once pruebas nuevas:

1. Motor real con dos vanos → resultados canónicos → XLSX reales → endpoint →
   renderer → resolución de seis selecciones y suma completa.
2. Lectores XLSX con B1 y B2 compartiendo S1/S2 y R1/R2/R3: ninguna colisión.
3. Datos longitudinales faltantes no se tratan como cero compatible.
4. Vano completamente nulo conserva su opción de base/peso cero.
5. Endpoint: seis regiones, spacing 110/120/130 y 210/220/230, bases propias.
6. Orden del modelo S1/S2/S10 preservado.
7. Guardar cambios en S1/R1 y S2/R2, GET posterior y nuevo render: se conservan
   ambos. Óptimo sintético=250 kg, seleccionado=254 kg, diferencia=1,60 %.
8. DOM inicial: dos bloques, tres controles regionales en cada uno,
   óptimo=seleccionado=100+150=250 kg.
9. DOM con un vano y con tres vanos, sin hardcodear el caso de dos.
10. Cambio de base de S2: S1 no cambia; S2/R2 sigue con peso longitudinal cero.
11. Catálogo incompleto: vano visible, peso parcial no publicado y guardado deshabilitado.

Los tests de UI ejecutan las funciones reales del renderer en **Edge headless
y un DOM real**, con servidor loopback y perfil temporal aislados. Se omite
solo el dibujo SVG, fuera de esta prueba de alternativas. No es una búsqueda
de strings ni un DOM simulado. En sistemas sin Edge/Chromium se puede definir
`STRUCTURELAB_TEST_BROWSER`; en ausencia de navegador esas pruebas se omiten
explícitamente. En esta sesión se ejecutaron, no se omitieron.

La herramienta del navegador integrado no estaba disponible; se siguió la
alternativa de pruebas headless tras comprobar esa limitación. El sandbox
impedía arrancar Edge, por lo que las pruebas se ejecutaron con la autorización
de elevación del entorno, siempre con perfiles nuevos y sin usar el del usuario.

Comandos/resultados:

- `.\.venv\Scripts\python.exe -m unittest tests.test_multispan_preview -q`:
  11/11 aprobadas (11,145 s).
- `.\.venv\Scripts\python.exe -m unittest tests.test_pre_phase4_longitudinal_audit tests.test_transverse_ranking tests.test_refactoring_contracts -q`:
  21/21 aprobadas; incluye ranking transversal existente.
- `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`:
  201/201 aprobadas en 183,927 s; cero fallos, errores u omisiones.
- `.\.venv\Scripts\python.exe -m compileall -q app tests`: aprobado.
- `git diff --check`: aprobado al cierre documental.

## Compatibilidad, decisiones y límites

- No se modificaron fórmulas, ACI, DMI/DMO/DES, d/h, demandas ETABS,
  escenarios, capacidades, controlling, s_max_real, Lv/sL, pesos unitarios,
  ranking ni optimizadores. Ningún archivo `src/` se editó en esta tarea.
- GET/POST conservan rutas y campos existentes. Los nuevos campos de preview
  son aditivos; casos sin selección persistida devuelven `saved_selection=null`.
- Se mantiene el contrato previo de preview de **una viga** (`beam`), la primera
  del caso. No se añadió selector multiviga. Los artefactos con identidad de
  viga se filtran antes de agrupar sus vanos; XLSX antiguos sin esa columna
  conservan la compatibilidad de una viga.
- El resumen usa exclusivamente pesos de las opciones recibidas; JavaScript
  no reconstruye vanos ni calcula aplicabilidad torsional.
- Las pruebas no abren ni cambian la sesión del usuario. Para ver el cambio
  en un servidor ya iniciado sin recarga automática, reiniciar la API y recargar
  la página, eliminando así código/caché anterior; no hace falta recalcular el job.
- La forma de calcular el óptimo y las demás observaciones técnicas de la
  auditoría anterior quedan fuera de esta corrección.

No commit ni push.
