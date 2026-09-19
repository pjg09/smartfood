# SmartFood — Plan de Pull Requests del Sprint 5

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-PR-SPRINT5 |
| plan anterior | `./plan-de-pull-requests-sprint-4.md` — cerrado, documento de archivo |
| titulo | Agrupación de las 33 tareas del Sprint 5 en Pull Requests, y estado de cada tarea |
| documentos_fuente | `./sprint-5-backlog.md` (`[S4]`, `[S5]`, `[S6]`, `ANEXO C`); `./convenciones-de-git.md` (`[S1]`); `./definicion-de-terminado.md` |
| tipo_documento | Documento derivado de planificación. **No es un artefacto de Scrum** |
| sprint | **5 de 5 — el último** · semanas 14 – 15 · **Entrega final · semana 16** (`EVA-5`, 30 %) |
| tareas cubiertas | 33 de 33 (`TT-155` … `TT-187`) |
| pull requests | 13 (`PR-01` … `PR-13`) |
| idioma | es-CO |
| version | 1.0 |

### [S0.1] Qué es este documento y qué no es

`main` está protegida: nada entra por `push` directo (`[S1]` de `./convenciones-de-git.md`).
Este documento responde a una sola pregunta operativa: **¿hasta dónde desarrollo antes de
parar, abrir un PR y seguir?**

**No reordena ni modifica ninguna tarea.** El orden de `./sprint-5-backlog.md` es el orden
de construcción verificado en su `ANEXO C`. Lo único que este documento añade son **cortes**.

> **Este es el único sitio donde vive el estado de las tareas.** El sprint backlog es el
> plan y no se toca; el tablero de `TT-185` es la vista de la Daily. Si hay discrepancia,
> manda este documento.

> **Hay un plan por sprint y se conservan todos.** Los de los Sprints 1 a 4 están en
> `./plan-de-pull-requests-sprint-1.md` … `-4`, cerrados.

---

## [S1] La regla de corte

Todo PR es un **bloque contiguo** del orden del sprint backlog. Sin huecos, sin saltos,
sin adelantar tareas.

> El `ANEXO C` verifica que el orden de las 33 tareas es un orden topológico del grafo de
> dependencias: **ninguna tarea aparece antes de algo que la bloquea**. Si cada PR es un
> bloque contiguo de ese orden, toda dependencia de cualquier tarea de `PR-k` está, o en
> `PR-k`, o en un PR anterior. **Nunca en uno posterior.**

Consecuencia práctica: **integrar los PR en orden numérico no puede romperse.**

Los cortes se eligieron con tres criterios, en este orden:

1. **Un PR cierra algo demostrable.** Este sprint desemboca en la entrega final.
2. **Un PR se revisa de una sentada.** Entre 1 y 4 tareas. Ninguno pasa de 4.
3. **Un PR no mezcla asuntos.** Los reportes del acudiente no viajan con los de la cafetería.

> **Hay una excepción deliberada al criterio 3, y es `PR-02`.** Junta dos historias —`HU-31`
> y `HU-34`— porque `INV-9` no admite que se separen. Ver su aviso.

---

## [S2] Cómo se marca una tarea como finalizada

1. Se cumplen los criterios de la Definición de Terminado que aplican al PR. **Los seis
   están vigentes** desde que `DoD-4` se reescribió en el Sprint 4.
2. El PR se integra en `main` por revisión cruzada, nunca por `push` directo.
3. Se marca `☑` **en los dos documentos**: aquí y en `./sprint-5-backlog.md`.
4. Si el PR cierra una historia, se marca también en la tabla `[S4]` de
   `./backlog-historias-de-usuario.md`.

---

## [S3] Avance del Sprint 5

| | Tareas | Pull Requests |
|---|---|---|
| **Finalizadas** | **3** de 33 | **1** de 13 |
| Pendientes | 30 | 12 |

| Responsable | Finalizadas | Total |
|---|---|---|
| Pedro | 1 | 11 |
| Carlos | 1 | 10 |
| Alejandro | 1 | 6 |
| Naomi | 0 | 6 |

### [S3.1] Estado de los 13 Pull Requests

| PR | Tareas | Qué cierra | Estado |
|---|---|---|---|
| `PR-01` | `TT-155`–`TT-157` | `HU-30` · app `reportes` | ☑ |
| `PR-02` | `TT-158`–`TT-161` | `HU-31` **y `HU-34`** · **`INV-9`** | ☐ |
| `PR-03` | `TT-162`–`TT-164` | `HU-32` | ☐ |
| `PR-04` | `TT-165`–`TT-166` | `HU-33` | ☐ |
| `PR-05` | `TT-167`–`TT-168` | `HU-35` | ☐ |
| `PR-06` | `TT-169`–`TT-170` | `HU-36` | ☐ |
| `PR-07` | `TT-171`–`TT-174` | `HU-55` · `INVD-5` | ☐ |
| `PR-08` | `TT-175`–`TT-176` | `HU-56` | ☐ |
| `PR-09` | `TT-177`–`TT-178` | `HU-37` · **las 61 historias terminadas** | ☐ |
| `PR-10` | `TT-179`–`TT-180` | `ENT-05` y el resto de `ENT-03` | ☐ |
| `PR-11` | `TT-181`–`TT-182` | `ENT-04` | ☐ |
| `PR-12` | `TT-183`–`TT-184` | `ENT-06` y `ENT-07` | ☐ |
| `PR-13` | `TT-185`–`TT-187` | Gestión y cierre del proyecto | ☐ |

---

## [S4] Los 13 Pull Requests

### Reportes del acudiente — `PR-01` … `PR-04`

#### `PR-01` — `HU-30` Historial de consumo

| | |
|---|---|
| Título del PR | `feat(reportes): mostrar al acudiente el historial de consumo` |
| Rama | `feat/TT-155-historial-de-consumo` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-30` |
| Invariantes | consume `DT-8`; `S11` en el control de acceso |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-155` | App `reportes` y selector del historial de consumo | Pedro | ☑ |
| `TT-156` | Pantalla del historial en la interfaz del acudiente | Carlos | ☑ |
| `TT-157` | Caso de prueba: el acudiente solo ve a sus estudiantes | Alejandro | ☑ |

Crea la app `reportes`, que `DT-15` declaró desde el principio: **no es una desviación** y no
necesita un `DT-` nuevo, a diferencia de `restricciones` en el Sprint 3.

> **Lee la instantánea, no el producto.** El historial muestra la información nutricional
> **registrada al momento de cada venta** (`TT-84`, `DT-8`). Leer el producto actual rompe
> `HU-22` retroactivamente: editar un precio reescribiría el pasado.

> ✅ **Integrado.** La app `reportes` entra **sin modelos y sin migraciones**: un reporte es
> una lectura de hechos que ya están escritos en `ventas`, `billetera` e `inventario`, y una
> tabla propia de «consumo» sería la segunda fuente de verdad que `DT-19` evita. Con ella
> están las ocho apps del proyecto: no queda ninguna por crear.
>
> El aviso de arriba se comprueba **por los dos caminos por los que se rompe**: el selector,
> que podría leer el producto, y la plantilla, que podría pintarlo aunque el selector traiga
> la línea congelada. Los dos tienen prueba, y las dos fallan al introducir la violación a
> propósito.

---

#### `PR-02` — `HU-31` **y** `HU-34` Alertas con su aviso

| | |
|---|---|
| Título del PR | `feat(reportes): alertar sobre la frecuencia de consumo, con su aviso` |
| Rama | `feat/TT-158-alertas-de-frecuencia` |
| Responsables | Alejandro, Pedro y Carlos |
| Historias | `HU-31` **y `HU-34`** |
| Invariantes | **`INV-9`** |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-158` | Definición de las reglas determinísticas de frecuencia, con sus umbrales | Alejandro | ☐ |
| `TT-159` | Motor que evalúa esas reglas sobre el historial | Pedro | ☐ |
| `TT-160` | Alertas en la pantalla del acudiente | Carlos | ☐ |
| `TT-161` | Aviso de carácter orientativo junto a las recomendaciones | Carlos | ☐ |

> ⚠ **`HU-34` va aquí y no en su propio PR, a propósito.** `INV-9` exige que el aviso esté
> desde **la primera recomendación publicada**, y `ALC-OUT-20` excluye «cualquier forma de
> valoración nutricional individualizada» por ser acto profesional del área de la salud.
> Separarlos publicaría alertas sin descargo durante el intervalo entre dos PR.
>
> Es el único sitio del proyecto con implicación legal directa sobre lo que se muestra.
> **Son dos marcas en el backlog de historias al integrar.**

`TT-158` no es implementación: es decidir los umbrales y poder justificarlos. **Nada de
modelos probabilísticos** — `OBJ-E3` exige reglas determinísticas.

---

#### `PR-03` — `HU-32` Comparación con valores de referencia

| | |
|---|---|
| Título del PR | `feat(reportes): comparar los agregados nutricionales con la referencia sanitaria` |
| Rama | `feat/TT-162-valores-de-referencia` |
| Responsables | Alejandro, Pedro y Carlos |
| Historia | `HU-32` |
| Invariantes | `INV-9` (ya cubierto por `PR-02`) |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-162` | Localizar y registrar los valores de la autoridad sanitaria colombiana, con su fuente | Alejandro | ☐ |
| `TT-163` | Cálculo determinístico de los agregados frente a esa referencia | Pedro | ☐ |
| `TT-164` | Comparación en la pantalla del acudiente | Carlos | ☐ |

> **`TT-162` es investigación, no código, y es la tarea con más riesgo de quedarse a
> medias.** La historia exige que la referencia sea «la publicada por la autoridad sanitaria
> colombiana»: hay que ir a la normativa del Ministerio de Salud, elegir la tabla y dejar la
> fuente registrada. Si en la sustentación preguntan de dónde salen esas cifras, esta tarea
> es la respuesta. **Si no se encuentran, hay que declarar qué se usó en su lugar**, no
> inventar una cifra.

---

#### `PR-04` — `HU-33` Resumen de gasto

| | |
|---|---|
| Título del PR | `feat(reportes): resumir el gasto frente al saldo recargado` |
| Rama | `feat/TT-165-resumen-de-gasto` |
| Responsables | Pedro y Carlos |
| Historia | `HU-33` |
| Invariantes | ninguna; consume `INV-2` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-165` | Selector del gasto frente al saldo recargado en un periodo | Pedro | ☐ |
| `TT-166` | Resumen de gasto en la pantalla del acudiente | Carlos | ☐ |

Sale entero del libro de movimientos: recargas contra ventas. No hay dato nuevo que capturar.

---

### Reportes de la cafetería — `PR-05` … `PR-09`

#### `PR-05` — `HU-35` Reporte de ventas

| | |
|---|---|
| Título del PR | `feat(reportes): informar de las ventas registradas` |
| Rama | `feat/TT-167-reporte-de-ventas` |
| Responsables | Pedro y Carlos |
| Historia | `HU-35` |
| Invariantes | `S11`: solo la administración |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-167` | Selector del reporte sobre las transacciones registradas | Pedro | ☐ |
| `TT-168` | Reporte de ventas en la interfaz administrativa | Carlos | ☐ |

«Sobre las transacciones registradas, **no sobre datos capturados aparte**». Incluye las
ventas genéricas de `HU-53` y distingue el medio de pago de `HU-54`.

---

#### `PR-06` — `HU-36` Reporte de movimientos de inventario

| | |
|---|---|
| Título del PR | `feat(reportes): informar de los movimientos de inventario` |
| Rama | `feat/TT-169-reporte-de-inventario` |
| Responsables | Pedro y Carlos |
| Historia | `HU-36` |
| Invariantes | consume `INV-3` e `INV-8` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-169` | Selector del reporte de movimientos, con su motivo | Pedro | ☐ |
| `TT-170` | Reporte de inventario en la interfaz administrativa | Carlos | ☐ |

Se apoya en `historial_de` (Sprint 2) y en la merma con motivo (Sprint 4).

---

#### `PR-07` — `HU-55` Cierre de caja diario

| | |
|---|---|
| Título del PR | `feat(ventas): cuadrar la caja contra las ventas registradas` |
| Rama | `feat/TT-171-cierre-de-caja` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-55` |
| Invariantes | **`INVD-5`** |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-171` | Modelo de cierre: fecha, cajero, base, efectivo contado, diferencia y motivo | Pedro | ☐ |
| `TT-172` | Servicio que calcula el efectivo esperado **desde las ventas registradas** | Pedro | ☐ |
| `TT-173` | Pantalla de cierre de caja en el punto de venta | Carlos | ☐ |
| `TT-174` | Caso de prueba: diferencia ≠ 0 exige motivo; transferencias fuera del cuadre | Alejandro | ☐ |

**El PR más denso del sprint** y el único que añade un modelo. Tres condiciones que se
pierden fácil:

- **El efectivo esperado se calcula, no se digita** (`INVD-5`).
- **Las transferencias quedan fuera del cuadre**: ese dinero nunca pasó por la caja (`DEC-1`).
- **Motivo obligatorio si la diferencia no es cero**, mismo criterio que `ALC-IN-18`.

> `PA-7` del anteproyecto describe lo que hace hoy la cafetería: cuadrar el efectivo contra
> **su estimación** de lo vendido. Este PR convierte esa estimación en ventas registradas.
> Es una ruptura del proceso actual, y conviene decirlo así en la sustentación.

---

#### `PR-08` — `HU-56` Reporte de cierres de caja

| | |
|---|---|
| Título del PR | `feat(reportes): informar de los cierres de caja registrados` |
| Rama | `feat/TT-175-reporte-de-cierres` |
| Responsables | Pedro y Carlos |
| Historia | `HU-56` |
| Invariantes | `INVD-5` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-175` | Selector de los cierres registrados | Pedro | ☐ |
| `TT-176` | Reporte de cierres en la interfaz administrativa | Carlos | ☐ |

---

#### `PR-09` — `HU-37` Reporte de auditoría · **cierra el backlog**

| | |
|---|---|
| Título del PR | `feat(reportes): consolidar la auditoría de la operación` |
| Rama | `feat/TT-177-reporte-de-auditoria` |
| Responsables | Pedro y Carlos |
| Historia | `HU-37` |
| Invariantes | cubre `ALC-IN-22` entero |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-177` | Selector que consolida ventas, movimientos de inventario y cierres | Pedro | ☐ |
| `TT-178` | Reporte de auditoría en la interfaz administrativa | Carlos | ☐ |

> 🏁 **Al integrar este PR, las 61 historias del proyecto están terminadas.** Es el último
> que toca el producto: de aquí en adelante el sprint es entrega, no desarrollo. Merece
> decirse en la Daily del día que ocurra.

---

### Cierre del proyecto — `PR-10` … `PR-12`

> **Estos tres PR no cierran historias: cierran entregables.** `[S9.3]` del anteproyecto
> declara siete, y tres de ellos —`ENT-05`, `ENT-06` y `ENT-07`— no son historias de usuario
> y ningún sprint los había planificado. Sin ellos no hay entrega, por mucho prototipo que
> haya. Ver `[S5]` del sprint backlog.

#### `PR-10` — `ENT-05` Plan de pruebas y `ENT-03` Arquitectura

| | |
|---|---|
| Título del PR | `docs(entrega): ejecutar el plan de pruebas y documentar la arquitectura` |
| Rama | `docs/TT-179-plan-de-pruebas` |
| Responsables | Alejandro y Pedro |
| Entregables | `ENT-05`, resto de `ENT-03` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-179` | Ejecución del plan de pruebas y evidencia de `TST-1` … `TST-4` | Alejandro | ☐ |
| `TT-180` | Diagrama de arquitectura | Pedro | ☐ |

**`TT-179` puede empezar el primer día del sprint.** Los cuatro escenarios críticos están
construidos desde el Sprint 4; lo que falta es **ejecutarlos y dejar evidencia**. No depende
de ninguna tarea de este sprint.

---

#### `PR-11` — `ENT-04` Artefactos de gestión

| | |
|---|---|
| Título del PR | `docs(entrega): completar los artefactos de gestión del proyecto` |
| Rama | `docs/TT-181-artefactos-de-gestion` |
| Responsables | Naomi y Alejandro |
| Entregable | `ENT-04` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-181` | Mapa de stakeholders y matriz de riesgos del proyecto | Naomi | ☐ |
| `TT-182` | Recorrido de experiencia de usuario e indicadores (KPI) | Alejandro | ☐ |

La matriz de riesgos **consolida los cinco registros de sprint**, no se escribe de cero.

---

#### `PR-12` — `ENT-06` Informe final y `ENT-07` Sustentación

| | |
|---|---|
| Título del PR | `docs(entrega): redactar el informe final y preparar la sustentación` |
| Rama | `docs/TT-183-informe-final` |
| Responsable | Naomi |
| Entregables | `ENT-06`, `ENT-07`, `EVA-5` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-183` | Informe técnico final: resultados, limitaciones y trabajo futuro | Naomi | ☐ |
| `TT-184` | Preparación de la sustentación y la demostración en vivo | Naomi | ☐ |

> **`TT-183` es el que más fácil se queda corto, y el que no se escribe en un fin de semana.**
> `ENT-06` pide «resultados, **limitaciones identificadas** y trabajo futuro». Las
> limitaciones ya están escritas y dispersas: los `ANEXO B` de `./decisiones-de-alcance.md` y
> `./decisiones-tecnicas.md` llevan cinco sprints acumulando puntos abiertos, y `DEC-15`
> documenta que el prototipo no se despliega. **Se redacta recogiéndolos, no inventándolos.**

---

### Gestión — `PR-13`

#### `PR-13` — Cierre del sprint y del proyecto

| | |
|---|---|
| Título del PR | `docs(gestion): cerrar el Sprint 5 y el proyecto` |
| Rama | `docs/TT-185-gestion-del-sprint-5` |
| Responsable | Naomi |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-185` | Tablero Kanban del Sprint 5 | Naomi | ☐ |
| `TT-186` | Registro de riesgos del Sprint 5 | Naomi | ☐ |
| `TT-187` | Sprint Review y Retrospective **finales** del proyecto | Naomi | ☐ |

`TT-186` alimenta `TT-181`: la matriz de riesgos del proyecto es la consolidación de los
cinco registros, no un documento nuevo.

---

## [S5] Qué se puede solapar

Es el sprint con **más frentes independientes** de los cinco.

| PR | Puede ir en paralelo con | Porque |
|---|---|---|
| `PR-05`, `PR-06`, `PR-07` (cafetería) | `PR-01` … `PR-04` (acudiente) | Dos familias de reportes que solo se encuentran en `PR-09` |
| `PR-10` (`ENT-05`, Alejandro y Pedro) | cualquiera | `TT-179` no depende de nada del sprint |
| `PR-11` (`ENT-04`, Naomi y Alejandro) | cualquiera | `TT-181` y `TT-182` no dependen de nada |
| `PR-13` (gestión, Naomi) | cualquiera | — |

**Trece raíces** sin dependencia dentro del sprint: `TT-155`, `TT-158`, `TT-162`, `TT-167`,
`TT-169`, `TT-171`, `TT-179`, `TT-180`, `TT-181`, `TT-182` y las tres de gestión.

**Regla al solapar:** ramifica siempre desde `main`, nunca desde la rama del otro.

---

## [S6] Advertencias sobre este plan

1. **Es el último sprint: lo que falle aquí no se recupera.** No hay sprint siguiente. Si
   algo tiene que caerse, que sean los `Should` de reportes —`PR-04`, `PR-06`, `PR-08`— y
   **nunca** `PR-10`, `PR-11` ni `PR-12`: sin `ENT-05` y `ENT-06` no hay entrega.
2. **El cierre del proyecto no puede empezar en la semana 15.** `PR-10` y `PR-11` no
   dependen de nada y deberían abrirse en la **primera** semana. El informe final (`PR-12`)
   sí depende de los dos, y por eso es el único que queda forzosamente para el final.
3. **`PR-02` cierra dos historias.** `HU-31` y `HU-34`. Es la segunda vez en el proyecto que
   un PR cierra dos —la primera fue `PR-06` del Sprint 3—, y aquí no es por arrastre sino
   porque `INV-9` prohíbe separarlas.
4. **`PR-09` es el último PR de producto del proyecto.** Al integrarse, las 61 historias
   están terminadas. Lo que viene después es entrega.
5. **`TT-162` puede no tener respuesta limpia.** Si los valores de referencia no existen en
   la forma que `HU-32` asume, hay que declarar qué se usó en su lugar. No inventar cifras.
6. **Este plan no reordena nada.** Si alguien propone mover una tarea de PR, hay que
   comprobar el `ANEXO C` del sprint backlog antes.
