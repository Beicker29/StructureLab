# Revisión y simplificación de StructureLab

Fecha: 2026-09-17. Alcance: limpieza incremental sin ampliar funcionalidad ni modificar criterios de ingeniería. No se ejecutaron commit, push ni operaciones de descarte.

## A. Estado inicial y diagnóstico

### Línea base

- Rama: `main`, asociada a `origin/main`; árbol de trabajo inicialmente limpio.
- Commit de referencia: `f8b0ac8efebb497cc1a2e6469a13659bf3f0f6d6`.
- 62 archivos Python; 17 167 líneas físicas; 15 434 líneas no vacías y no iniciadas por comentario.
- 185 pruebas descubiertas y aprobadas con `unittest` en 176,927 s.
- Python 3.12 y entorno existente `.venv`. No se instalaron dependencias.
- No había configuración ni instalación de pytest, ruff, black, mypy o coverage. No existe una línea base de lint, tipado o cobertura que pueda declararse libre de errores.

Se consultaron `AGENTS.md`, `STRUCTURELAB_REFACTOR_PLAN.md`, `ARCHITECTURE.md`, contratos, pruebas, README y configuración de empaquetado/despliegue. La revisión incluyó inventario AST de todos los archivos Python, búsqueda de consumidores y revisión dirigida de módulos, UI, configuración y pruebas. No constituye una demostración formal de ausencia de código muerto ni una auditoría normativa nueva. Archivos generados, almacenamiento de jobs, entornos virtuales y temporales no se trataron como código fuente descartable.

### Estructura y dependencias relevantes

- `app/routers` publica transporte HTTP; `app/services` coordina casos, jobs, preview y reportes; `app/domain` normaliza importaciones y formularios.
- `models` y `domain` validan contratos del motor. `io` conserva procedencia de filas ETABS.
- `engine` coordina `design`, `span_coupled`, `optimization` y `report`.
- `codes/aci318_25` contiene verificaciones normativas; `ranking` y `tolerances` son implementaciones compartidas existentes que se conservaron.
- `app/ui` presenta y construye entradas. `scripts/smoke_api.py` y el workflow de Render siguen siendo consumidores activos.
- El paquete raíz `rc_shear_torsion` conecta con `src`; `run.py` conserva la entrada CLI documentada. No son archivos abandonados.

Focos iniciales de complejidad: endpoint de selección de 454 líneas; `evaluate_candidate` de 370; `parse_span_layout_json` de 287; `validate_case_rules` de 264; `optimize_span_coupled` de 297; `_build_span_preview` de 275; `write_reinforcement_schedule` de 237. El tamaño indica candidatos de revisión, no autoriza a alterar sus reglas.

### Hallazgos de los 20 aspectos solicitados

| Aspecto | Evidencia y decisión |
| --- | --- |
| 1. Código muerto | Se retiraron fallbacks de selección inalcanzables después de la normalización y validación. No se encontraron funciones privadas inequívocamente abandonadas mediante búsqueda de referencias. |
| 2. Funciones/clases duplicadas | Los dos `decode` locales de búsqueda repetían el mismo cuerpo. Eliminados al compartir preparación y evaluación. No se eliminaron clases públicas. |
| 3. Lógica repetida | Preparación GA/exhaustiva, deduplicación transversal y filtros longitudinales ahora tienen una implementación cada uno. |
| 4. Helpers excesivamente específicos | Los dos productores de opciones transversales comparten ranking después de normalizar. Se conservaron parsers específicos de fuente: sus defaults y conversiones no son equivalentes. |
| 5. Wrappers/adaptadores | CLI, puente de paquete y entradas públicas de optimización son contratos activos. Se mantuvieron, aunque deleguen. |
| 6. Abstracciones sin valor | No se añadió framework, repositorio genérico ni jerarquía de estrategias. Los nuevos módulos agrupan responsabilidades concretas. |
| 7. Funciones largas | Endpoint de selección reducido a 17 líneas; resolución separada en preparación regional, preparación por vano, validación y selección. Las funciones normativas largas se dejaron intactas. |
| 8. Indirección excesiva | Se eliminaron los `decode` locales, usados una vez por implementación. Se conservaron helpers con nombre significativo y APIs públicas. |
| 9. Imports no utilizados | Eliminados imports de selección que dejaron de usarse en el router. Reexportaciones de catálogos son intencionales. `EtabsStationRow` en `design` se conserva por posible consumo externo, aunque no tenga uso local. |
| 10. Constantes/configuración obsoleta | Catálogos dispersos reunidos en `reinforcement`; valores sin cambios. El catálogo de espaciado legacy es consumido por normalización, no es obsoleto eliminable. |
| 11. Archivos sin función | No se confirmó ningún archivo fuente abandonado. Fixtures, referencias normativas, scripts y archivos de inicialización se conservaron. |
| 12. Legacy reemplazado | El modo regional independiente y los aliases siguen formando parte del contrato. No se confundieron con código muerto. |
| 13. Implementaciones paralelas | Eliminada la preparación paralela GA/exhaustiva; se conserva la diferencia entre algoritmos y el motor acoplado. El conteo de estribos para objetivo y reporte exige revisión independiente (G1). |
| 14. Conversiones repetitivas | Catálogo y conversiones de masa dejan de requerir importar el módulo de diseño completo. Conversiones de entrada con políticas diferentes permanecen separadas. |
| 15. Validaciones repetidas | Se preservan fronteras Pydantic, importación y dominio: producen errores y garantías diferentes. La validación de selecciones fue extraída sin cambiar precedencia ni mensajes. |
| 16. Manejo de errores repetitivo | Los errores de selección conservan códigos, mensajes y HTTP 422. No se agregó un capturador genérico ni se suprimieron excepciones. |
| 17. Estructuras innecesariamente complejas | Se eliminó `_sort_weight` temporal en las dos rutas transversales; se usan los valores normalizados. Los diccionarios de preview siguen siendo un contrato, no se rediseñaron. |
| 18. Dependencias simplificables | Ingestión, payload, preview, resultados y diseño acoplado consumen directamente el catálogo. El router delega resolución al servicio sin I/O. |
| 19. APIs internas inconsistentes | Se detectaron parsers con diferentes políticas para nulos, inválidos y positivos; no se unificaron perdiendo esas diferencias. Las firmas públicas se conservaron. |
| 20. Reutilización existente | Se reutilizan `SearchHooks`, los algoritmos de `optimization`, el evaluador de candidatos y `transverse_alternative_rank_key`. No se duplican fórmulas ACI. |

## B. Cambios realizados por módulo

### Motor y optimización

- `src/rc_shear_torsion/design.py`: `_optimize_region_search` comparte validación de dominios, valores longitudinales por defecto, evaluación, hooks y conversión de resultados. `optimize_region_exhaustive` y `optimize_region_ga` conservan firmas y comportamiento.
- El cache sigue aplicándose únicamente a GA. Se conservan semilla 42, orden de dominios, contadores, criterios de ranking y búsquedas subyacentes. No cambian `evaluate_candidate`, reglas ACI, estados, controlling, torsión ni fórmulas.
- `src/rc_shear_torsion/reinforcement.py` (nuevo): agrupa diámetros, áreas, masas tabuladas, etiquetas admitidas, densidad y las dos funciones existentes de masa. Se trasladaron sin cambiar valores ni orden de operaciones.
- `models.py` conserva reexportaciones históricas; `design.py` conserva los símbolos públicos trasladados. `results_model.py` y `span_coupled.py` solo ajustan imports del catálogo.

### Aplicación

- `app/services/job_preview_service.py`: `_rank_transverse_options` comparte deduplicación y ranking entre la lectura del reporte transversal y la construcción de opciones fallback. Mantiene peso sin redondear, primer elemento en empate exacto, ranking existente y límite de resultados. El parsing de cada fuente no se unificó.
- `app/services/selection_service.py` (nuevo): resolución pura contra un preview existente. Separa preparación, validación y selección; conserva selección regional/por vano, prioridades, combinaciones exactas y campos reportados. Elimina ramas inalcanzables y comparte los filtros de etiquetas longitudinales base/adicional.
- `app/routers/jobs.py`: mantiene endpoint, firma, transporte, generación de URL y llamada al servicio existente de persistencia. Delega solo la resolución.
- `app/domain/ingestion.py` y `case_payload.py`: consumen catálogo directamente; no cambian normalización ni validación.

### Pruebas y documentación

- `tests/test_refactoring_contracts.py` (nuevo): cinco pruebas de comportamiento/compatibilidad; ninguna prueba existente fue eliminada ni modificada.
- `ARCHITECTURE.md`: documenta responsabilidades compartidas y rutas de compatibilidad.
- Este informe registra decisiones, métricas y límites de la revisión.

## C. Código eliminado

- Archivos eliminados: ninguno.
- Clases eliminadas: ninguna.
- APIs públicas eliminadas: ninguna.
- Se eliminaron los dos helpers locales `decode`; la lectura de genes queda en el único evaluador local compartido.
- Se retiró una copia completa de preparación, hooks y ensamblado de resultados de búsqueda.
- Se retiró una copia del procesamiento transversal de ranking y deduplicación, así como sus diccionarios auxiliares de peso de ordenamiento.
- Se retiraron fallbacks de selección: mapas vacíos que ya habían sido poblados cuando había etiquetas; ramas para una combinación ausente después de lanzar error; pesos ausentes después de convertirlos obligatoriamente a float.
- Las funciones de masa fueron trasladadas, no eliminadas. No se retiró un motor legacy ni un adaptador público.

## D. Duplicación eliminada

Tres grupos de duplicación intervenidos quedaron con una sola implementación:

1. Preparación/evaluación/ensamblado de búsqueda regional GA y exhaustiva.
2. Deduplicación y ordenamiento de opciones transversales normalizadas.
3. Filtrado repetido por etiquetas longitudinales base y adicional.

La centralización del catálogo es una mejora de cohesión y dependencias, no una reducción de tablas duplicadas: cada tabla ya tenía sus propios valores. Esta distinción evita atribuirle una eliminación de duplicación inexistente.

## E. Métricas antes/después

| Métrica | Antes | Después | Cambio |
| --- | ---: | ---: | ---: |
| Archivos Python | 62 | 65 | +3 |
| LOC Python físicas, incluyendo pruebas | 17 167 | 17 145 | -22 |
| Líneas no vacías ni de comentario | 15 434 | 15 390 | -44 |
| LOC Python sin `tests/` | 11 035 | 10 912 | -123 |
| Líneas no vacías ni de comentario, sin `tests/` | 9 835 | 9 700 | -135 |
| Pruebas | 185 | 190 | +5 |
| Grupos de duplicación intervenidos | 3 | 0 | -3 |
| Líneas del endpoint de selección | 454 | 17 | -437 |
| Errores lint/type checking | No medidos | No medidos | Herramientas no configuradas |

Reducción LOC total: `(17167 - 17145) / 17167 × 100 = 0,128 %`.

Reducción LOC sin pruebas: `(11035 - 10912) / 11035 × 100 = 1,115 %`.

El endpoint más corto no significa 437 líneas netas eliminadas: gran parte se trasladó al servicio. Los dos módulos productivos nuevos mejoran responsabilidades; el tercero agrega 101 líneas de pruebas. No se compactaron expresiones para inflar la reducción.

### Método de medición

Se contaron `.py` en `app`, `src`, `tests`, `scripts` y `rc_shear_torsion`, excluyendo cachés. La línea base se obtuvo del commit indicado mediante `git ls-files`/`git show`; el resultado incluye los nuevos archivos, aunque aún no estén en Git. LOC corresponde a `len(text.splitlines())`; la aproximación efectiva excluye líneas vacías y aquellas cuyo `lstrip()` empieza con `#`, pero incluye docstrings y continuaciones: no es SLOC lógica. Las pruebas se cuentan por funciones AST `test_*` y se confirman con `unittest`. El tamaño de funciones utiliza `end_lineno - lineno + 1`, sin decoradores. La métrica de duplicación es manual y limitada a los tres grupos intervenidos, no una puntuación global de un detector de clones.

## F. Validación y compatibilidad

### Pruebas agregadas

Las primeras cuatro se ejecutaron contra la implementación original antes de cambiar producción:

1. Dominios de búsqueda vacíos: mismos errores, método, contadores y candidato fallido para GA y exhaustiva.
2. Preview: deduplicación por peso no redondeado, primer registro en empate exacto, orden, faltantes y límite mínimo.
3. Preview: conteo por peso unitario mantiene precedencia sobre peso explícito.
4. Selección HTTP: conserva elección manual, combinación exacta, pesos, diferencia porcentual y URL del artefacto.

Se agregó además una comprobación de imports públicos históricos, valores de catálogo y resultados de masa para barra conocida, desconocida y cantidad cero.

### Ejecuciones

- Línea base: `python -m unittest discover -s tests -v`: 185/185 aprobadas.
- Verificaciones incrementales después de cada grupo: 65 pruebas del motor; 22 de preview/reportes; 10 de selección/contratos; 76 de catálogos, ingestión y detallado. Todas aprobadas.
- Suite final: `python -m unittest discover -s tests -v`: 190/190 aprobadas en 176,555 s; cero fallos y cero errores.
- `python -m compileall -q app src scripts tests rc_shear_torsion`: aprobado.
- `git diff --check`: aprobado al cierre.
- Archivos nuevos: comprobación adicional de espacios finales y salto de línea final, aprobada.
- Comparación AST contra la línea base: sin cambios en `evaluate_candidate`, `spacing_domain_for_region`, `failed_candidate`, `stirrup_count_in_region`, `stirrup_set_unit_weight_kg` y `make_failed_region_result`.
- No se ejecutaron lint, type checker o cobertura: no están configurados/instalados. Compilar y revisar AST no sustituye esas herramientas.

Los comandos Python se ejecutaron con `.\.venv\Scripts\python.exe`. Git no está en PATH en esta sesión; se utilizó el ejecutable de GitHub Desktop (`app-3.6.5/resources/app/git/cmd/git.exe`). No se alteró la configuración del entorno.

### Comparación diferencial adicional

- Se capturaron antes de editar 12 salidas deterministas: producto de DMI/DMO/DES, C/NC y torsión activa/inactiva, utilizando los fixtures de `test_transverse_ranking`. Cada salida incluye búsqueda exhaustiva, GA, alternativas regionales, diseño acoplado y resultado fallido, serializados completos con `dataclasses.asdict`. Después de los cambios coinciden los 12 SHA-256 del JSON normalizado, incluidos estados y trazabilidad. Es una caracterización del software, no una validación normativa de esos resultados.
- Se compararon en memoria 600 solicitudes de selección con el endpoint obtenido mediante `git show` de la línea base: 60 previews generados con semilla 42, dos vanos/dos regiones/cinco opciones, y diez variantes de solicitud. Incluye selección predeterminada, regional, por vano, filtros base/adicional, opción inexistente, vano/región inexistente y duplicados. Coinciden exactamente las filas o los campos completos de `AppError`.
- Las comparaciones diferenciales fueron verificaciones de auditoría, no pruebas hash permanentes que conviertan posibles bugs antiguos en contratos correctos.

Se mantienen rutas HTTP, contratos JSON, campos, hojas de Excel, CLI, defaults, modos longitudinales, d/h por vano y configuración longitudinal global. No se modificaron archivos de reglas ACI, evaluadores normativos, algoritmo genético, unidades ni límites. La verificación es local; no se ejecutó smoke contra Render ni validación visual en navegador.

## G. Riesgos y pendientes reales

### G1. Posible bug: conteos distintos entre objetivo y reporte

- Archivos/funciones: `design.stirrup_count_in_region` y `report._stirrup_count_for_reporting`.
- Actual: el objetivo usa `floor(L/s)+1`; el reporte descuenta offsets de apoyo y usa `ceil` cuando una región cubre todo el vano. Por ejemplo, L=400 mm y s=130 mm produce 4 en el primero y 4 en vano completo; con s=100 mm produce 5 y 4, respectivamente.
- Sospecha/impacto: objetivos y pesos mostrados pueden corresponder a cantidades distintas; un ranking puede no reflejar el peso constructivo reportado.
- Recomendación: acordar primero el contrato de colocación/conteo por región y borde; caracterizar objetivos y reportes juntos. No unificar durante esta limpieza: cambiaría resultados y requiere decisión técnica.

### G2. Posible bug: pérdida de estado en resultado fallido

- Archivo/función: `design.make_failed_region_result`.
- Actual: construye `failed_candidate` y luego reconstruye `Candidate` sin copiar estados estructurados. Una llamada diagnóstica con `region_detail_fail` confirma `status=fail`, pero `detailing_status=NOT_EVALUATED` y `overall_status=NOT_EVALUATED`; pierde los estados FAIL generados por `failed_candidate`.
- Impacto: inconsistencia de trazabilidad entre fallo global y estados detallados.
- Recomendación: revisar consumidores y estados esperados en una corrección separada, con regresión específica. No reemplazar mecánicamente la reconstrucción por `replace`: eso modificaría las salidas actuales.

### G3. Deuda técnica: ciclo de vida de workbooks

- Ubicación: `io.read_etabs_excel`, `_open_etabs_sheet_with_required_columns` de ingestión y lectores `_read_optimized_regions`/`_read_schedule_rows` del preview.
- Actual: cierre solo al final del camino exitoso en el primer caso; otros lectores no garantizan cierre explícito. Algunas salidas tempranas o errores dejan el recurso abierto.
- Impacto: retención de recursos y posibles archivos bloqueados en Windows.
- Recomendación: definir ownership y cierre con pruebas de éxito/error. No agregar `try/except` que oculte fallos. No se cambió la gestión de recursos en esta intervención.

### G4. Posible mejora arquitectónica: funciones que aún mezclan demasiados pasos

- Ubicación: `_build_span_preview`, `parse_span_layout_json`, `validate_case_rules`, `optimize_span_coupled`, `write_reinforcement_schedule` y funciones compactadas de `app/ui/static/ui.js`.
- Recomendación: extraer responsabilidades por contrato con pruebas específicas en cambios posteriores. La validación y el ensamblado de reglas no se separaron mecánicamente para evitar alterar orden, mensajes y aplicabilidad. El servicio de selección aún emplea diccionarios amplios; introducir modelos tipados requeriría evaluar coerciones y defaults.

### G5. Posible código legacy / posible ruptura futura de compatibilidad

- Candidatos: reexportación incidental de `EtabsStationRow` en `design`, `to_canonical_region_results` sin consumidor interno identificado, adaptador raíz de paquete y modo `legacy_region_independent`.
- No equivalen a código eliminable. CLI, usuarios externos o casos anteriores pueden depender de ellos; el modo legacy tiene uso explícito y permanece soportado.
- Recomendación: inventariar consumidores externos y acordar una política de deprecación antes de retirar símbolos o modos. Las reexportaciones del catálogo agregadas en esta tarea son compatibilidad deliberada, no duplicación de implementación.

No se corrigió ninguno de los posibles bugs técnicos dentro de esta refactorización ni se avanzó a una fase funcional adicional.
