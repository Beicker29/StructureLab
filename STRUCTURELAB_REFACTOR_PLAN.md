# StructureLab - Plan rector de refactorizacion y correccion ingenieril

## 1. Proposito del documento

Este documento es el contrato tecnico para reorganizar StructureLab y corregir su flujo de calculo sin perder trazabilidad ni introducir cambios normativos silenciosos.

Debe utilizarse como fuente de verdad durante la implementacion. Cada fase debe ejecutarse, probarse y revisarse antes de iniciar la siguiente.

El objetivo funcional de StructureLab es:

1. Leer demandas de diseno exportadas por ETABS para vigas de concreto reforzado.
2. Conservar las demandas de cada fuente y estacion como escenarios fisicamente existentes.
3. Proponer, mediante busqueda exhaustiva o algoritmo genetico, un esquema de refuerzo transversal por cortante y torsion y refuerzo longitudinal por torsion.
4. Verificar separadamente los requisitos de detallado aplicables del ACI 318-25.
5. Entregar resultados auditables que indiquen demanda, capacidad, regla controlante, estacion controlante y procedencia de cada dato.

## 2. Alcance y limites

### Incluido

- Importacion de `VRebar`, `TTrnRebar` y `TLngRebar` desde ETABS.
- Escenarios separados de sismo y gravedad.
- Diseno por regiones dentro de cada vano.
- Refuerzo transversal por cortante y torsion.
- Refuerzo longitudinal requerido exclusivamente por torsion.
- Detallado ACI 318-25 para DMI, DMO y DES dentro del alcance anterior.
- Activacion regional de soporte lateral para refuerzo longitudinal a compresion requerido.
- Optimizacion por peso y trazabilidad de las verificaciones.

### Excluido por ahora

- Diseno del refuerzo longitudinal por flexion.
- Calculo de resistencia a flexion.
- Rediseno de las demandas producidas por ETABS.
- Prolongacion del refuerzo torsional fuera de la region mediante el criterio `bt+d`.
- Extension automatica de una condicion torsional hacia regiones vecinas.
- Declarar cumplimiento de reglas que requieran datos no disponibles.

La exclusion temporal de `bt+d` debe quedar documentada como una limitacion conocida. No debe aplicarse ni utilizarse para modificar regiones en esta etapa.

## 3. Principios obligatorios

### 3.1 Escenarios fisicamente existentes

Nunca se deben combinar maximos independientes de estaciones distintas.

Es incorrecto construir:

```text
[max(VRebar), max(TTrnRebar), max(TLngRebar)]
```

si los tres valores no pertenecen a la misma fuente y estacion.

La unidad atomica de demanda sera:

```text
DemandScenario = fuente + estacion + VRebar + TTrnRebar + TLngRebar
```

Cada candidato de refuerzo de una region debe cumplir todos los escenarios contenidos en esa region.

### 3.2 Separacion entre calculo y detallado

El sistema debe producir tres estados independientes:

- `demand_status`: cumplimiento de las demandas ETABS.
- `detailing_status`: cumplimiento de reglas de detallado aplicables.
- `overall_status`: combinacion de los anteriores.

Una configuracion puede satisfacer la demanda y fallar detallado. Los dos resultados no deben mezclarse en una sola expresion o mensaje.

### 3.3 Reglas puras y explicables

Cada regla debe:

- recibir datos explicitos;
- evitar dependencias con la interfaz, archivos o estado global;
- devolver un resultado estructurado;
- identificar la seccion normativa;
- indicar por que aplica o no aplica;
- informar requerido, suministrado, margen y unidad;
- ser comprobable mediante una prueba unitaria independiente.

### 3.4 DRY sin ocultar la ingenieria

DRY significa centralizar formulas, constantes, unidades, catalogos y decisiones de aplicabilidad. No significa crear abstracciones genericas que escondan las ecuaciones o dificulten su auditoria.

Cada formula normativa debe existir en un solo lugar.

### 3.5 Compatibilidad controlada

Los casos JSON anteriores deben continuar cargando cuando sea tecnicamente posible. Los campos nuevos opcionales deben tener valores predeterminados seguros y explicitos.

No se deben mantener dos motores de calculo divergentes para conservar compatibilidad. La compatibilidad debe resolverse en la frontera de entrada mediante normalizacion o migracion.

## 4. Hallazgos confirmados en la implementacion actual

### `src/rc_shear_torsion/design.py`

- Contiene modelos, catalogos de barras, ensamblaje de demandas, formulas, detallado, evaluacion de candidatos y conversion de resultados.
- `build_region_demands()` calcula maximos independientes de `VRebar`, `TTrnRebar` y `TLngRebar`.
- `check_region_rule()` mezcla reglas de cortante, sismo, torsion y ties.
- Aplica limites `16db` y `48db` sin una condicion explicita de refuerzo longitudinal a compresion requerido.
- Aplica `Ph/8` en DES-C sin comprobar primero si la torsion esta activa.
- La rama DMO-C utiliza 150 mm donde la regla DMO indicada para esa rama es 300 mm.
- El tipo `beam_detailing` solo contempla DMO y DES.

### `src/rc_shear_torsion/models.py`

- `BeamConfig.detailing` solo admite DMO y DES.
- `RegionConfig` mezcla geometria, clasificacion normativa y parametros de detallado.
- `db_bar` es ambiguo: no distingue entre la menor y la mayor barra longitudinal encerrada.
- No existe un campo regional para indicar refuerzo longitudinal a compresion requerido.

### `app/domain/case_payload.py`

- Genera regiones C/NC y sus datos geometricos.
- No transporta la nueva condicion regional de refuerzo a compresion.
- La construccion del payload debera mantenerse separada de las formulas ACI.

### Interfaz

- El formulario y el editor avanzado de vanos todavia no permiten definir la aplicabilidad regional de ties.
- La interfaz no debe decidir reglas normativas; solamente debe capturar datos y mostrar las decisiones calculadas por el dominio.

## 5. Arquitectura objetivo

```text
src/rc_shear_torsion/
  application/
    run_case.py
    design_region.py
    optimize_span.py

  domain/
    models/
      demand.py
      geometry.py
      reinforcement.py
      results.py
    services/
      region_assignment.py
      candidate_evaluation.py
      governing_checks.py
    catalogs/
      reinforcing_bars.py
    units.py
    tolerances.py
    errors.py

  etabs/
    reader.py
    normalization.py
    validation.py

  codes/
    aci318_25/
      common.py
      shear.py
      torsion.py
      seismic.py
      ties.py
      applicability.py

  optimization/
    exhaustive.py
    genetic.py
    objectives.py

  reporting/
    excel.py
    audit.py
    summaries.py
```

La migracion puede ser gradual. No se debe mover todo en un solo cambio. Primero se introducen las nuevas piezas con pruebas; despues se elimina el codigo reemplazado.

## 6. Modelo de dominio propuesto

### 6.1 Demanda por estacion

```text
DemandScenario
  source: SEISMIC | GRAVITY
  station_mm: float
  x_relative: float
  region_id: str
  v_rebar_mm2_per_m: float
  t_transverse_mm2_per_m: float
  t_longitudinal_mm2: float
  torsion_state: ACTIVE | INACTIVE | INCONSISTENT
```

No se permite el valor `MIXED` como fuente de un escenario. `MIXED` puede aparecer solamente en un resumen que indique que diferentes escenarios controlan verificaciones diferentes.

### 6.2 Demanda regional

```text
RegionDemand
  beam_id
  span_id
  region_id
  scenarios: tuple[DemandScenario, ...]
  geometry
  detailing_context
```

`RegionDemand` no debe almacenar un vector sintetico de maximos independientes.

### 6.3 Contexto de detallado regional

```text
DetailingContext
  seismic_system: DMI | DMO | DES
  seismic_zone: CONFINED | NON_CONFINED
  compression_rebar_required: bool
  smallest_enclosed_longitudinal_bar
  largest_enclosed_longitudinal_bar
  longitudinal_bars_bundled: bool
  longitudinal_steel_grade_mpa
  nominal_max_aggregate_size_mm
```

El campo historico `db_bar` puede aceptarse como alias de compatibilidad, pero internamente no debe utilizarse para dos significados diferentes.

### 6.4 Resultado de una regla

```text
RuleCheck
  rule_id
  code: ACI_318_25
  section
  status: PASS | FAIL | NOT_APPLICABLE | NOT_EVALUATED
  applicability_reason
  required_value
  provided_value
  margin
  unit
  source
  station
```

`NOT_EVALUATED` se utiliza cuando una regla podria aplicar, pero faltan datos. Nunca debe convertirse silenciosamente en `PASS`.

## 7. Asignacion de estaciones a regiones

Las regiones deben cubrir el intervalo `[0, 1]` sin vacios ni superposiciones.

- Regiones no finales: `[from, to)`.
- Ultima region: `[from, to]`.

Cada estacion debe pertenecer exactamente a una region.

Sismo y gravedad deben mantenerse como escenarios separados, incluso cuando compartan la misma coordenada.

## 8. Estado de torsion

Se debe usar una tolerancia unica y configurable `torsion_zero_tolerance`.

Por escenario:

```text
TTrn <= tol y TLng <= tol  -> INACTIVE
TTrn >  tol y TLng >  tol  -> ACTIVE
solo uno supera tol        -> INCONSISTENT
```

Reglas:

- `INACTIVE`: no aplicar requisitos especificos de torsion.
- `ACTIVE`: verificar demanda transversal y longitudinal de torsion y su detallado.
- `INCONSISTENT`: detener el diseno de la region con un error trazable de entrada.
- No extender la torsion hacia otra region.
- No usar `bt+d` en esta version.

Si una region contiene escenarios activos e inactivos, el candidato se verifica contra cada uno. El detallado torsional regional se activa si existe al menos un escenario activo.

## 9. Cumplimiento de demanda

Para cada candidato y cada escenario `i`:

```text
C_T  = At * 1000 / s
C_VT = (2*At + nG*AG) * 1000 / s
```

El candidato debe cumplir simultaneamente:

```text
TTrn_i <= C_T
VRebar_i + 2*TTrn_i <= C_VT
TLng_i <= Along_provided
```

La factibilidad regional es la interseccion de las factibilidades de todos los escenarios:

```text
candidate_is_feasible = all(check(candidate, scenario_i))
```

Despues de seleccionar el candidato se identifican las estaciones controlantes. Pueden existir estaciones distintas para torsion transversal, combinacion cortante-torsion y torsion longitudinal.

## 10. Cuantia minima transversal

Para vigas no preesforzadas, cuando sea aplicable:

```text
Av_min/s = max(
  0.062 * sqrt(fc') * bw / fyt,
  0.35 * bw / fyt
)
```

Con torsion activa:

```text
(Av + 2At)_min/s = max(
  0.062 * sqrt(fc') * bw / fyt,
  0.35 * bw / fyt
)
```

La aplicabilidad normativa del minimo por cortante depende de `Vu` y de las condiciones de ACI 318-25, no solamente de que `VRebar` sea positivo.

Si el repositorio no dispone de `Vu` o de un indicador confiable proveniente de ETABS, la regla debe devolver `NOT_EVALUATED`. No se debe afirmar una verificacion independiente que no puede realizarse.

Antes de implementar esta regla debe resolverse uno de estos contratos:

1. Importar `Vu` y calcular su aplicabilidad; o
2. Importar una bandera explicita de ETABS que indique que se requiere refuerzo minimo; o
3. Declarar que `VRebar` ya incluye los minimos de ETABS y reportarlo como verificacion externa, no independiente.

## 11. Limites de espaciamiento

Cada regla activa produce un limite superior independiente:

```text
s_max_final = min(limites_maximos_aplicables)
```

Ejemplos de familias:

- cortante;
- DMO o DES;
- torsion;
- ties, si aplican.

Las reglas `NOT_APPLICABLE` y `NOT_EVALUATED` no se introducen como cero dentro del minimo.

Si existe una separacion minima constructiva:

```text
s_min <= s_selected <= s_max_final
```

Si `s_min > s_max_final`, el candidato es inviable.

El resultado debe listar todos los limites calculados y marcar cual controlo.

## 12. Matriz de aplicabilidad

### DMI sin torsion

- Demanda de cortante por cada escenario.
- Cuantia minima por cortante cuando pueda comprobarse su aplicabilidad.
- Espaciamiento general por cortante.
- Sin reglas torsionales.
- Ties completos solo si `compression_rebar_required=true`.

### DMI con torsion

- Todas las verificaciones de demanda por estacion.
- Minimo transversal combinado.
- Estribo cerrado y espaciamiento torsional.
- Refuerzo longitudinal exclusivamente por torsion.
- Ties completos solo si `compression_rebar_required=true`.

### DMO sin torsion

- Reglas de cortante y minimo aplicable.
- En regiones confinadas de extremo: reglas DMO, primer estribo y espaciamiento correspondiente.
- Fuera de ellas: limite DMO general.
- Sin `Ph/8` ni otras reglas torsionales.
- Ties completos solo si `compression_rebar_required=true`.

### DMO con torsion

- Superposicion de DMO, cortante y torsion.
- El menor espaciamiento maximo gobierna.
- Ties completos solo si `compression_rebar_required=true`.

### DES sin torsion

- Reglas de cortante y minimo aplicable.
- Reglas DES en zonas confinadas.
- Fuera de zonas confinadas: estribos y espaciamiento DES correspondientes.
- Soporte lateral de barras principales en zonas confinadas conforme a la remision especifica de ACI.
- No aplicar automaticamente `Ph/8`.

### DES con torsion

- Superposicion de DES, cortante y torsion.
- El menor espaciamiento maximo gobierna.
- Soporte lateral DES y detallado torsional se reportan como verificaciones distintas.

## 13. Politica de ties

No se debe representar la aplicabilidad mediante un unico booleano interno. Se recomienda:

```text
TieRuleScope =
  NONE
  LATERAL_SUPPORT_ONLY
  FULL
```

Regla de seleccion:

```text
si compression_rebar_required:
    scope = FULL
si no, si sistema == DES y zona == CONFINED:
    scope = LATERAL_SUPPORT_ONLY
en otro caso:
    scope = NONE
```

La torsion no activa por si sola los requisitos de ties.

Si se decide imponer ties completos en toda viga DES, debe implementarse como una politica de proyecto separada, por ejemplo `force_full_ties_in_des`, y reportarse como `PROJECT_REQUIREMENT`, no como exigencia automatica de ACI.

Para `FULL` deben estar disponibles como minimo:

- menor diametro longitudinal encerrado;
- mayor diametro longitudinal encerrado;
- existencia de paquetes de barras;
- diametro de cada componente transversal;
- dimensiones de la seccion;
- tamano nominal maximo del agregado si se verificara la separacion libre.

## 14. Separacion entre motor de esquema y codigo

### Motor de esquema

Responsable de:

- generar candidatos;
- calcular areas suministradas;
- calcular peso;
- verificar demandas ETABS por estacion;
- optimizar;
- identificar estaciones controlantes.

No debe conocer articulos ACI.

### Motor ACI 318-25

Responsable de:

- decidir aplicabilidad;
- calcular minimos y limites;
- verificar geometria y disposicion;
- producir `RuleCheck` auditables.

No debe conocer DEAP, poblaciones, mutaciones, archivos Excel, FastAPI ni HTML.

### Orquestador

Responsable de:

1. Obtener escenarios de la region.
2. Generar un candidato.
3. Evaluar demanda.
4. Evaluar detallado.
5. Combinar estados.
6. Entregar el resultado al optimizador.

## 15. Interfaz y contrato API

En el editor de cada region debe aparecer:

- Checkbox: `Refuerzo longitudinal a compresion requerido`.
- Si se activa:
  - menor barra longitudinal encerrada;
  - mayor barra longitudinal encerrada;
  - checkbox de barras agrupadas.

Comportamiento:

- DMI/DMO: checkbox editable.
- DES confinada: mostrar soporte lateral requerido por DES; permitir activar `FULL` si tambien existe refuerzo a compresion requerido.
- DES no confinada: comportamiento igual a DMI/DMO para ties completos.

La interfaz debe explicar que marcar el checkbox significa que las barras se contabilizan como refuerzo longitudinal a compresion requerido. No significa simplemente que existen barras en la cara comprimida.

El valor predeterminado para casos antiguos sera `false`.

## 16. Resultados y trazabilidad

Cada region debe reportar:

- numero de escenarios evaluados;
- lista de fuentes y estaciones;
- estado de torsion;
- esquema seleccionado;
- capacidad suministrada;
- estacion controlante por verificacion;
- todas las reglas de detallado evaluadas;
- regla controlante del espaciamiento;
- limites aplicables y no aplicables;
- campos faltantes que produjeron `NOT_EVALUATED`;
- peso transversal, peso longitudinal por torsion y peso total;
- metodo de optimizacion y semilla usada.

No debe existir un unico `governing_station` si verificaciones distintas estan controladas por estaciones distintas.

## 17. Estrategia de optimizacion

La busqueda exhaustiva y el algoritmo genetico deben utilizar exactamente la misma funcion de evaluacion.

La funcion objetivo no debe duplicar verificaciones normativas. Debe consumir el resultado comun del evaluador.

Orden recomendado:

1. Validaciones de entrada.
2. Factibilidad geometrica.
3. Cumplimiento de demanda para todos los escenarios.
4. Cumplimiento de detallado.
5. Calculo del objetivo.

El algoritmo genetico debe usar semilla configurable y reportarla para reproducibilidad.

Para casos pequenos, el resultado del GA debe compararse contra la busqueda exhaustiva.

## 18. Estrategia de pruebas

### Pruebas unitarias

- Asignacion unica de estaciones a regiones.
- Clasificacion de torsion con tolerancia.
- Capacidad transversal y longitudinal.
- Cada formula ACI por separado.
- Aplicabilidad DMI, DMO y DES.
- Alcances `NONE`, `LATERAL_SUPPORT_ONLY` y `FULL` para ties.
- Seleccion del menor limite maximo.
- Inviabilidad cuando el minimo constructivo supera el maximo permitido.

### Prueba obligatoria contra envolvente artificial

Con estaciones:

```text
(900, 80, 400)
(650, 240, 500)
(700, 150, 620)
```

se debe demostrar que nunca aparece el vector artificial:

```text
(900, 240, 620)
```

### Matriz minima de regresion

- DMI sin torsion.
- DMI con torsion.
- DMO sin torsion.
- DMO con torsion.
- DES sin torsion.
- DES con torsion.
- Cada caso anterior con demanda controlada por sismo.
- Cada caso anterior con demanda controlada por gravedad.
- Caso donde estaciones diferentes controlan verificaciones diferentes.
- Caso `TORSION_INCONSISTENT`.
- DMI/DMO con y sin refuerzo a compresion requerido.
- DES confinada y no confinada.

### Integracion

- JSON anterior sigue cargando.
- Formulario genera el payload correcto.
- API conserva contratos documentados o publica una migracion explicita.
- Reportes reproducen los `RuleCheck` sin reinterpretar formulas.
- GA y exhaustivo comparten evaluador.

## 19. Fases de implementacion

### Fase 0 - Linea base

- Leer instrucciones del repositorio.
- Registrar estado de Git.
- Ejecutar pruebas actuales.
- Crear pruebas de caracterizacion para los resultados vigentes que deban conservarse.

Puerta de salida: linea base reproducible y cambios existentes protegidos.

### Fase 1 - Escenarios por estacion

- Introducir `DemandScenario`.
- Eliminar envolventes independientes.
- Verificar candidatos contra todos los escenarios.
- Introducir estados de torsion.
- Agregar DMI al contrato.
- Agregar `compression_rebar_required=false` sin usarlo aun en formulas.

Puerta de salida: prueba de envolvente artificial, fuentes separadas y compatibilidad JSON.

### Fase 2 - Motor ACI modular

- Introducir `RuleCheck`.
- Separar cortante, torsion, sismo, ties y aplicabilidad.
- Corregir DMO-C.
- Evitar `Ph/8` sin torsion.
- Eliminar aplicacion indiscriminada de `16db` y `48db`.
- Mantener `check_region_rule()` solo como adaptador temporal y despues retirarlo.

Puerta de salida: matriz completa de reglas unitarias y ninguna formula ACI dentro del optimizador.

### Fase 3 - Modelo y UI de ties

- Incorporar datos longitudinales regionales necesarios.
- Agregar controles condicionales en la interfaz.
- Transportar los valores por API y constructor de casos.
- Mostrar claramente la aplicabilidad calculada.

Puerta de salida: pruebas de formulario, payload, validacion y compatibilidad.

### Fase 4 - Resultados y reportes

- Separar estados de demanda, detallado y resultado global.
- Reportar todas las estaciones y controles.
- Incluir trazabilidad normativa.
- Actualizar Excel, vista previa y descarga.

Puerta de salida: un resultado puede reconstruirse desde sus datos y reglas reportadas.

### Fase 5 - Limpieza arquitectonica

- Descomponer `design.py`.
- Centralizar catalogos y unidades.
- Eliminar codigo reemplazado y adaptadores temporales.
- Resolver paquetes o rutas duplicadas.
- Actualizar `ARCHITECTURE.md`, README y ejemplos.

Puerta de salida: no quedan dos implementaciones de una misma regla.

### Fase 6 - Validacion ingenieril

- Crear casos manuales de referencia.
- Comparar con calculos independientes.
- Comparar GA contra exhaustivo.
- Registrar tolerancias y redondeos.
- Documentar limitaciones conocidas, incluida la exclusion temporal de `bt+d`.

Puerta de salida: resultados reproducibles y revisables por un ingeniero distinto del autor.

## 20. Reglas para ejecutar el plan con Codex

- Trabajar una fase por vez.
- No mezclar refactorizacion estructural con cambios de formulas sin pruebas especificas.
- Antes de editar, revisar `git status` y las instrucciones locales.
- No sobrescribir cambios ajenos.
- Se permite modificar, mover, fusionar o eliminar archivos y modulos que hayan quedado obsoletos o que contradigan la arquitectura objetivo. Antes de eliminarlos, buscar todas sus referencias, migrar los consumidores y ejecutar las pruebas correspondientes.
- No conservar codigo muerto, implementaciones duplicadas ni capas de compatibilidad sin una necesidad comprobada. Toda eliminacion debe informarse al finalizar la fase junto con su justificacion y efecto sobre compatibilidad.
- Ejecutar pruebas antes y despues de cada fase.
- No hacer commit salvo solicitud expresa.
- Cada fase debe terminar con:
  - archivos modificados;
  - decisiones tomadas;
  - pruebas agregadas;
  - comandos de verificacion;
  - resultados;
  - riesgos o pendientes.
- Si una regla normativa es ambigua, detener esa regla y solicitar decision. No inventar una interpretacion.
- Si faltan datos para una verificacion, devolver `NOT_EVALUATED` y declarar el dato faltante.

## 21. Decisiones que no deben cambiarse sin aprobacion

1. No construir envolventes independientes.
2. Verificar un candidato contra todas las estaciones de la region.
3. Mantener sismo y gravedad como escenarios separados.
4. No disenar refuerzo longitudinal por flexion.
5. El refuerzo longitudinal optimizado corresponde solamente a torsion.
6. No implementar `bt+d` en esta etapa.
7. No aplicar reglas torsionales cuando la torsion este inactiva.
8. No tratar una inconsistencia torsional como cero.
9. No aplicar ties completos solo porque existan barras en la cara comprimida.
10. DMI/DMO activan ties completos mediante `compression_rebar_required`.
11. DES confinada activa el soporte lateral exigido por su regla especifica; no se debe atribuir automaticamente todo §25.7.2 a toda la viga.
12. El menor limite maximo aplicable controla el espaciamiento.
13. Las reglas no evaluadas no cuentan como aprobadas.

## 22. Definicion de terminado

La reorganizacion se considera completa cuando:

- ningun resultado contiene un vector de demanda inexistente;
- todas las estaciones de una region se verifican con el esquema seleccionado;
- DMI, DMO y DES funcionan con y sin torsion;
- las reglas de ties se aplican solamente bajo su condicion correcta;
- el detallado esta desacoplado del cumplimiento de demanda;
- las formulas, unidades y tolerancias estan centralizadas;
- GA y busqueda exhaustiva utilizan el mismo evaluador;
- los resultados identifican reglas y estaciones controlantes;
- existe cobertura automatizada de la matriz de escenarios;
- la documentacion coincide con el comportamiento real;
- todas las pruebas pasan de forma reproducible.
