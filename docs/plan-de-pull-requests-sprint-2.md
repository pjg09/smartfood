# SmartFood — Plan de Pull Requests del Sprint 2

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-PR-SPRINT2 |
| plan anterior | `./plan-de-pull-requests-sprint-1.md` — cerrado, documento de archivo |
| titulo | Agrupación de las 37 tareas del Sprint 2 en Pull Requests, y estado de cada tarea |
| documentos_fuente | `./sprint-2-backlog.md` (`[S3]`, `[S4]`, `[S5]`, `ANEXO C`); `./convenciones-de-git.md` (`[S1]`); `./definicion-de-terminado.md` |
| tipo_documento | Documento derivado de planificación. **No es un artefacto de Scrum** |
| sprint | 2 de 5 · semanas 8 – 9 · **Avance 1 · semana 10** (`EVA-3`) |
| tareas cubiertas | 37 de 37 (`TT-57` … `TT-93`) |
| pull requests | 16 (`PR-01` … `PR-16`) |
| idioma | es-CO |
| version | 1.1 |

### [S0.1] Qué es este documento y qué no es

`main` está protegida: nada entra por `push` directo (`[S1]` de `./convenciones-de-git.md`).
Este documento responde a una sola pregunta operativa: **¿hasta dónde desarrollo antes de
parar, abrir un PR y seguir?**

**No reordena ni modifica ninguna tarea.** El orden de `./sprint-2-backlog.md` es el orden
de construcción verificado en su `ANEXO C`, y aquí se respeta carácter por carácter. Lo
único que este documento añade son **cortes**.

> **Este es el único sitio donde vive el estado de las tareas.** El sprint backlog es el
> plan y no se toca; el tablero de `TT-91` es la vista de la Daily. Si hay discrepancia,
> manda este documento.

> **Hay un plan por sprint y se conservan todos.** El del Sprint 1 está en
> `./plan-de-pull-requests-sprint-1.md`, cerrado con sus 25 PR y sus 56 tareas. Este
> documento no lo sustituye.

---

## [S1] La regla de corte

Todo PR es un **bloque contiguo** del orden del sprint backlog. Sin huecos, sin saltos,
sin adelantar tareas.

De ahí sale la única propiedad que importa, y es demostrable:

> El `ANEXO C` verifica que el orden de las 37 tareas es un orden topológico del grafo de
> dependencias: **ninguna tarea aparece antes de algo que la bloquea**. Si cada PR es un
> bloque contiguo de ese orden, entonces toda dependencia de cualquier tarea de `PR-k`
> está, o en `PR-k`, o en un PR anterior. **Nunca en uno posterior.**

Consecuencia práctica: **integrar los PR en orden numérico no puede romperse.** Al abrir
`PR-k`, `main` ya contiene todo lo que sus tareas necesitan.

Los cortes se eligieron con tres criterios, en este orden:

1. **Un PR cierra algo demostrable.** Un PR que deja una historia a medias no se puede
   enseñar en la Sprint Review ni en el Avance 1.
2. **Un PR se revisa de una sentada.** Entre 1 y 4 tareas. Ninguno pasa de 4.
3. **Un PR no mezcla asuntos.** La billetera no viaja con el inventario aunque sean
   contiguos: son dos libros de movimientos independientes.

---

## [S2] Cómo se marca una tarea como finalizada

> ⏸ **`DoD-4` sigue suspendido** y con él la verificación en el entorno desplegado. Una
> tarea se marca finalizada con los otros cinco criterios más la verificación local
> declarada. Ver `[S5]` de `./definicion-de-terminado.md`.
>
> **Si el entorno se restaura durante este sprint, `DoD-4` vuelve a aplicar.** El Avance 1
> de la semana 10 es exactamente cuando hará falta: ver la advertencia 4 de `[S6]`.

1. Se cumplen los criterios de la Definición de Terminado que aplican al PR.
2. El PR se integra en `main` por revisión cruzada, nunca por `push` directo.
3. Se marca `☑` **en los dos documentos**: aquí, en `[S3.1]` y en la tabla del PR, y en
   `./sprint-2-backlog.md`.
4. Si el PR cierra una historia, se marca también en la tabla `[S4]` de
   `./backlog-historias-de-usuario.md`.

---

## [S3] Avance del Sprint 2

| | Tareas | Pull Requests |
|---|---|---|
| **Finalizadas** | **16** de 37 | **7** de 16 |
| Pendientes | 21 | 9 |

| Responsable | Finalizadas | Total |
|---|---|---|
| Pedro | 8 | 14 |
| Carlos | 6 | 11 |
| Alejandro | 2 | 9 |
| Naomi | 0 | 3 |

### [S3.1] Estado de los 16 Pull Requests

| PR | Tareas | Qué cierra | Estado |
|---|---|---|---|
| `PR-01` | `TT-57`–`TT-58` | Habilitación del punto de venta (`INT-2`) | ☑ |
| `PR-02` | `TT-59`–`TT-61` | `HU-06` · base de `INV-2` | ☑ |
| `PR-03` | `TT-62`–`TT-63` | `HU-08` · `INV-2`, `TST-3` | ☑ |
| `PR-04` | `TT-64` | `HU-07` | ☑ |
| `PR-05` | `TT-65`–`TT-66` | `HU-52` · `INVD-2` | ☑ |
| `PR-06` | `TT-67`–`TT-69` | `HU-27` · base de `INV-3` e `INV-8` | ☐ |
| `PR-07` | `TT-70`–`TT-72` | `HU-15` → `ENT-02` | ◐ software sí; falta `TT-72` |
| `PR-08` | `TT-73` | `HU-16` | ☑ |
| `PR-09` | `TT-74`–`TT-76` | `HU-17` **parcial**, ver aviso | ☐ |
| `PR-10` | `TT-77` | `HU-58` · `DEC-8` | ☐ |
| `PR-11` | `TT-78`–`TT-79` | `HU-54` · `DEC-1` | ☐ |
| `PR-12` | `TT-80`–`TT-83` | `HU-21` · `INV-2`, `INV-3` | ☐ |
| `PR-13` | `TT-84`–`TT-85` | `HU-22` · `DT-8` | ☐ |
| `PR-14` | `TT-86`–`TT-87` | `HU-19` · `INV-1`, `TST-2` | ☐ |
| `PR-15` | `TT-88`–`TT-90` | `HU-53` · cierra `VAC-1` | ☐ |
| `PR-16` | `TT-91`–`TT-93` | Gestión del sprint y Avance 1 | ☐ |

### [S3.2] Pull Requests fuera del plan

Los dieciséis de arriba salen del sprint backlog y **no se tocan**. Aquí se anota lo que
entró a `main` sin corresponder a ninguna tarea: sin esta lista, el documento que dice ser
el único sitio donde vive el estado estaría afirmando que en `main` no hay nada más.

Un PR de esta lista **no cierra ninguna historia y no mueve los contadores** de `[S3]`: si
lo hiciera, sería una tarea y le tocaría estar arriba.

| PR | Qué hizo | Por qué no es una tarea | Estado |
|---|---|---|---|
| `PR-X1` | Completar la adopción del sistema visual en todas las pantallas construidas (`DT-25`) | `DT-23` es del Sprint 1 y no dejó tarea abierta; esto es trabajo sobre lo ya entregado, no alcance nuevo | ☑ |

`PR-X1` toca las ocho pantallas existentes y la hoja de estilos, pero **ninguna regla de
negocio**: los servicios, los selectores y las invariantes quedan como estaban. Lo que sí
cambia de comportamiento visible está declarado en `DT-25` —el formato del dinero y las
pestañas del punto de venta— y lo cubren las pruebas de `billetera` y `ventas`.

---

## [S4] Los 16 Pull Requests

### Habilitación — `PR-01`

Corresponde a `[S3]` del sprint backlog. Ninguna historia del punto de venta se puede
construir antes de que esté integrado.

#### `PR-01` — Habilitación del punto de venta

| | |
|---|---|
| Título del PR | `feat(pos): levantar la interfaz del punto de venta y su acceso` |
| Rama | `feat/TT-57-punto-de-venta` |
| Responsables | Carlos y Pedro |
| Historia | ninguna — habilitación |
| Invariantes | `DT-11`: el control de acceso es de la capa de datos, no del layout |
| Estado | ☑ **Integrado en `main`** |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-57` | Layout del punto de venta: pantalla completa, sin navegación, foco permanente y operación por teclado | Carlos | ☑ |
| `TT-58` | Ruta del punto de venta y su control de acceso: solo el rol cajero | Pedro | ☑ |

**Qué habilita y cómo se comprueba:** que un usuario con rol cajero llegue a una pantalla
del punto de venta, y que cualquier otro rol reciba un 403. `DoD-1` exige declararlo
porque este PR no cierra ninguna historia.

`INT-2` pide operación rápida: veinte a treinta minutos para toda la demanda. El layout no
lleva navegación ni diálogos, y todo es alcanzable con teclado (`DT-16`).

---

### Historias — `PR-02` … `PR-15`

#### `PR-02` — `HU-06` Recarga de la billetera

| | |
|---|---|
| Título del PR | `feat(billetera): recargar la billetera del estudiante` |
| Rama | `feat/TT-59-recarga-de-billetera` |
| Responsables | Pedro y Carlos |
| Historia | `HU-06` |
| Invariantes | sienta la base de `INV-2` |
| Estado | ☑ **Integrado en `main`** |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-59` | App `billetera`: modelos de billetera y de movimiento, **sin columna de saldo** (`DT-4`) | Pedro | ☑ |
| `TT-60` | Servicio de recarga que asienta un movimiento dentro de una transacción | Pedro | ☑ |
| `TT-61` | Pantalla de recarga en la interfaz del acudiente | Carlos | ☑ |

> **El PR más determinante del sprint.** Si `TT-59` introduce una columna `saldo` que se
> actualiza, `INV-2` deja de cumplirse por construcción y `HU-08` pasa a depender de que
> nadie se equivoque. El saldo **es** la suma de los movimientos. En la revisión, esto es
> lo primero que hay que mirar.

El pago es **simulado** (`ALC-OUT-01`, `ALC-OUT-02`): ni pasarela ni dinero real.

---

#### `PR-03` — `HU-08` Saldo reconstruible desde el historial

| | |
|---|---|
| Título del PR | `feat(billetera): derivar el saldo del historial de movimientos` |
| Rama | `feat/TT-62-saldo-derivado` |
| Responsables | Pedro y Alejandro |
| Historia | `HU-08` |
| Invariantes | **`INV-2`** · escenario crítico **`TST-3`** |
| Estado | ☑ **Integrado en `main`** |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-62` | Selector que calcula el saldo como suma del historial | Pedro | ☑ |
| `TT-63` | Caso de prueba `TST-3`: el saldo mostrado coincide exactamente con la suma del historial | Alejandro | ☑ |

`TST-3` es uno de los cuatro escenarios que `ENT-05` exige. La prueba no sobra por ser
cierta por construcción: es lo que detecta que alguien metió un atajo.

---

#### `PR-04` — `HU-07` Consulta de saldo por el acudiente

| | |
|---|---|
| Título del PR | `feat(billetera): mostrar el saldo al acudiente` |
| Rama | `feat/TT-64-saldo-del-acudiente` |
| Responsables | Carlos |
| Historia | `HU-07` |
| Invariantes | ninguna directamente; consume `INV-2` |
| Estado | ☑ **Integrado en `main`** |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-64` | Saldo y últimos movimientos en la ficha del estudiante | Carlos | ☑ |

Solo el acudiente ve el saldo como consulta libre. El cajero lo verá **solo al cobrar**
(`S11`), y eso es `PR-09`.

---

#### `PR-05` — `HU-52` Saldo congelado tras la baja

| | |
|---|---|
| Título del PR | `feat(billetera): congelar el saldo del estudiante dado de baja` |
| Rama | `feat/TT-65-saldo-congelado` |
| Responsables | Pedro y Alejandro |
| Historia | `HU-52` |
| Invariantes | `INVD-2` · protege `INV-2` |
| Estado | ☑ **Integrado en `main`** |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-65` | El estado `baja` impide recargar y comprar, conservando el saldo consultable | Pedro | ☑ |
| `TT-66` | Caso de prueba: estudiante de baja, saldo visible y sin operaciones posibles | Alejandro | ☑ |

Cierra lo que el Sprint 1 dejó a medias: `HU-51` construyó la baja lógica, pero sin
billetera no había saldo que congelar. La devolución del dinero queda **fuera del sistema**.

---

#### `PR-06` — `HU-27` Ingreso de mercancía

| | |
|---|---|
| Título del PR | `feat(inventario): registrar el ingreso de mercancía por ajuste manual` |
| Rama | `feat/TT-67-ingreso-de-mercancia` |
| Responsables | Pedro y Carlos |
| Historia | `HU-27` |
| Invariantes | sienta la base de **`INV-3`** y crea la restricción de **`INV-8`** |
| Estado | ☑ **Integrado en `main`** |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-67` | App `inventario`: movimiento como libro, **sin columna de existencias**, con motivo obligatorio por restricción | Pedro | ☑ |
| `TT-68` | Servicio de ingreso por ajuste manual | Pedro | ☑ |
| `TT-69` | Registro del ingreso desde la interfaz administrativa, con existencias calculadas | Carlos | ☑ |

Mismo criterio que `PR-02`: las existencias son la suma del historial. La restricción de
motivo obligatorio se crea aquí aunque `INV-8` lo ejercite `HU-28` en el Sprint 4 —
**es más barato ponerla con el modelo que añadirla sobre datos ya escritos**.

Inventario sobre **unidades vendibles**: ni insumos, ni recetas, ni costo de producción.

---

#### `PR-07` — `HU-15` Identificación por escaneo

| | |
|---|---|
| Título del PR | `feat(pos): identificar al estudiante escaneando su tarjeta` |
| Rama | `feat/TT-70-identificacion-por-escaneo` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-15` |
| Invariantes | consume `INV-7`; cierra **`ENT-02`** |
| Estado | ◐ **Parcial**: `TT-70` y `TT-71` integrados; falta `TT-72` |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-70` | Selector de identificación por código de tarjeta, que respeta el estado del estudiante | Pedro | ☑ |
| `TT-71` | Campo de escaneo con foco permanente que dispara la búsqueda al recibir Enter | Carlos | ☑ |
| `TT-72` | Prueba de concepto con el lector físico y tarjetas impresas | Alejandro | ☐ |

El lector **es un teclado**: teclea el código y envía Enter. No hay driver ni SDK.

`TT-72` cierra `ENT-02`, uno de los siete entregables del proyecto, con las tarjetas que
imprime lo construido en `TT-37`. Es trabajo físico: hay que imprimirlas de verdad.

> **`PR-07` se integra con `TT-72` pendiente, y `HU-15` no se cierra con él.** El software
> está construido y probado —el escaneo identifica, normaliza y respeta el estado—, pero el
> tercer criterio de la historia es *validar a escala reducida con tarjetas físicas*, y eso
> exige una impresora y un lector. `DoD-1` no admite dar por terminada una historia cuyo
> criterio no se ha comprobado. El guion de la ejecución está en
> `./prueba-de-concepto-del-lector.md`; al ejecutarlo se marca `TT-72`, se cierra `HU-15` y
> este PR pasa a ☑.

---

#### `PR-08` — `HU-16` Identificación por documento

| | |
|---|---|
| Título del PR | `feat(pos): buscar al estudiante por documento` |
| Rama | `feat/TT-73-busqueda-por-documento` |
| Responsables | Carlos |
| Historia | `HU-16` |
| Invariantes | ninguna |
| Estado | ☑ **Integrado en `main`** |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-73` | Búsqueda por documento con el mismo resultado que el escaneo | Carlos | ☑ |

---

#### `PR-09` — `HU-17` Vista de cobro **(parcial)**

| | |
|---|---|
| Título del PR | `feat(pos): mostrar el panel del estudiante al cobrar` |
| Rama | `feat/TT-74-panel-de-cobro` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-17` — **no la cierra**, ver aviso |
| Invariantes | `S11`: el cajero ve el saldo solo al cobrar |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-74` | Selector de la información de cobro: saldo y consumo del día | Pedro | ☐ |
| `TT-75` | Panel del estudiante en el punto de venta | Carlos | ☐ |
| `TT-76` | Caso de prueba: el cajero ve el saldo solo al cobrar | Alejandro | ☐ |

> ⚠ **Este PR no cierra `HU-17`.** El tercer criterio de aceptación exige mostrar las
> **restricciones vigentes**, y las restricciones son `HU-09` … `HU-13`, del **Sprint 3**.
> El panel se construye aquí con saldo y consumo del día; el bloque de restricciones lo
> añade `HU-13`, que declara depender de `HU-17`.
>
> **No marques `HU-17` como terminada al cerrar el sprint.** `DoD-1` exige que se cumplan
> *todos* los criterios. Se marca en el Sprint 3.

---

#### `PR-10` — `HU-58` Fotografía visible al cobrar

| | |
|---|---|
| Título del PR | `feat(pos): mostrar la fotografía del estudiante al cobrar` |
| Rama | `feat/TT-77-fotografia-al-cobrar` |
| Responsables | Carlos |
| Historia | `HU-58` |
| Invariantes | `DEC-8`; complementa `DEC-5` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-77` | Fotografía en el panel de cobro, con marcador visible cuando no la tiene | Carlos | ☐ |

Control **preventivo** de suplantación: la desactivación de `HU-47` y `HU-48` solo actúa
una vez reportada la pérdida; la fotografía actúa en el momento.

---

#### `PR-11` — `HU-54` Medio de pago en toda venta

| | |
|---|---|
| Título del PR | `feat(ventas): registrar el medio de pago de cada venta` |
| Rama | `feat/TT-78-medio-de-pago` |
| Responsables | Pedro y Carlos |
| Historia | `HU-54` |
| Invariantes | `DEC-1`; habilita `HU-53` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-78` | App `ventas`: modelos de venta y línea, con medio de pago y **estudiante opcional** | Pedro | ☐ |
| `TT-79` | Selección del medio de pago en el punto de venta | Carlos | ☐ |

> **Va antes que la venta a propósito.** El medio de pago es un campo del asiento; añadirlo
> después obliga a reescribir transacciones ya registradas, que es lo que `INV-2` prohíbe.

El **estudiante opcional** es lo que hace posible `PR-15`: una venta sin estudiante es una
venta a cliente genérico. La transferencia ocurre fuera del sistema; solo se deja constancia.

---

#### `PR-12` — `HU-21` Descuento simultáneo de saldo y existencias

| | |
|---|---|
| Título del PR | `feat(ventas): cobrar descontando saldo y existencias en una transacción` |
| Rama | `feat/TT-80-transaccion-de-venta` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-21` |
| Invariantes | **`INV-1`, `INV-2`, `INV-3` a la vez** |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-80` | Servicio de venta: **una** transacción con bloqueo pesimista sobre billetera y productos | Pedro | ☐ |
| `TT-81` | Carrito y confirmación de la venta, **sin diálogos de confirmación** | Carlos | ☐ |
| `TT-82` | Caso de prueba de concurrencia: dos ventas simultáneas sobre la misma billetera | Alejandro | ☐ |
| `TT-83` | Caso de prueba: saldo y existencias se descuentan en la misma operación, o ninguno | Alejandro | ☐ |

> 🔴 **El PR de mayor riesgo del proyecto.** `DT-6` es explícito: se bloquea, **luego** se
> valida, **luego** se escribe. Validar fuera del bloqueo abre la ventana en la que dos
> cajeros cobran a la vez, ambos ven saldo suficiente e `INV-1` se rompe. Con 2 a 5 cajeros
> en una ventana de veinte a treinta minutos, esa concurrencia no es teórica.
>
> **Revisión de los dos desarrolladores, no la cruzada de rigor.** Si falla, no falla una
> historia: falla el prototipo.

`TT-82` existe porque una prueba secuencial no detecta ese fallo.

---

#### `PR-13` — `HU-22` Información nutricional congelada

| | |
|---|---|
| Título del PR | `feat(ventas): congelar precio e información nutricional en la línea de venta` |
| Rama | `feat/TT-84-instantanea-nutricional` |
| Responsables | Pedro y Alejandro |
| Historia | `HU-22` |
| Invariantes | `DT-8`, `DT-19` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-84` | Instantánea del precio y de la información nutricional en la línea de venta | Pedro | ☐ |
| `TT-85` | Caso de prueba: editar un producto no altera las ventas ya asentadas | Alejandro | ☐ |

No es una desnormalización: «lo que el producto declara hoy» y «lo que declaraba al
venderse» son hechos distintos. Sostiene los reportes de consumo del Sprint 5.

---

#### `PR-14` — `HU-19` Venta rechazada por saldo insuficiente

| | |
|---|---|
| Título del PR | `feat(ventas): rechazar la venta cuando el saldo no alcanza` |
| Rama | `feat/TT-86-rechazo-por-saldo` |
| Responsables | Pedro y Alejandro |
| Historia | `HU-19` |
| Invariantes | **`INV-1`** · escenario crítico **`TST-2`** |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-86` | Validación del saldo **dentro** del bloqueo; si no alcanza, la venta no se realiza | Pedro | ☐ |
| `TT-87` | Caso de prueba `TST-2`: venta rechazada, y saldo nunca negativo | Alejandro | ☐ |

`TST-2` es escenario crítico de `ENT-05`. Su otra mitad —rechazo por límite diario— es
`HU-20`, del Sprint 3.

---

#### `PR-15` — `HU-53` Venta a cliente genérico

| | |
|---|---|
| Título del PR | `feat(ventas): registrar la venta a un cliente sin vínculo estudiantil` |
| Rama | `feat/TT-88-venta-generica` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-53` |
| Invariantes | `DEC-1`; cierra **`VAC-1`** |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-88` | Venta sin estudiante: descuenta inventario, **no** toca billetera, sin restricciones | Pedro | ☐ |
| `TT-89` | Modo de cliente genérico en el punto de venta | Carlos | ☐ |
| `TT-90` | Caso de prueba: descuenta inventario y no altera ninguna billetera | Alejandro | ☐ |

Cierra el hueco más serio que tenía el anteproyecto: `[S5]` declaraba `USR-6` y exigía
registrar sus ventas, sin ningún `ALC-IN` que lo respaldara.

---

### Gestión — `PR-16`

#### `PR-16` — Gestión del sprint y Avance 1

| | |
|---|---|
| Título del PR | `docs(gestion): cerrar el Sprint 2 y preparar el Avance 1` |
| Rama | `docs/TT-91-gestion-del-sprint-2` |
| Responsables | Naomi |
| Historia | ninguna — gestión |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-91` | Tablero Kanban del Sprint 2 | Naomi | ☐ |
| `TT-92` | Registro de riesgos del Sprint 2 | Naomi | ☐ |
| `TT-93` | Preparación de la Sprint Review, la Retrospective y el **Avance 1** | Naomi | ☐ |

`TT-91` y `TT-92` no esperan al final: el tablero se abre el primer día. Lo que se integra
al cierre es su resultado.

---

## [S5] Qué se puede solapar

El orden de integración es estricto, pero **el trabajo no es una fila india.** Estos PR no
dependen entre sí y pueden estar abiertos a la vez:

| PR | Puede ir en paralelo con | Porque |
|---|---|---|
| `PR-02` (billetera, Pedro) | `PR-06` (inventario, Pedro) | Dos libros independientes; solo se encuentran en `TT-80` |
| `PR-06` (inventario) | `PR-07` (identificación) | `TT-67` y `TT-70` no se tocan |
| `PR-16` (gestión, Naomi) | cualquiera | `TT-91`–`TT-93` no dependen de nada |

Y hay tareas **raíz** —sin dependencias— trabajables desde el primer día aunque su PR se
integre más tarde: `TT-57`, `TT-58`, `TT-59`, `TT-67` y `TT-70`, más las tres de gestión.
**Ocho raíces**, frente a las siete del Sprint 1.

**Regla al solapar:** ramifica siempre desde `main`, nunca desde la rama del otro. Si tu PR
necesita algo del PR de al lado, no es paralelo: espera a que se integre.

---

## [S6] Advertencias sobre este plan

1. **16 PR en dos semanas, frente a los 24 del Sprint 1.** Ritmo más sostenible, pero los
   PR son más densos: `PR-12` concentra la lógica transaccional entera. No confundir menos
   PR con menos trabajo.
2. **`PR-12` no se revisa como los demás.** Sostiene `INV-1`, `INV-2` e `INV-3` a la vez.
   Pide revisión de los dos desarrolladores y lectura línea a línea del orden
   bloqueo → validación → escritura.
3. **`PR-09` no cierra su historia y eso es correcto.** `HU-17` necesita las restricciones
   del Sprint 3. Al cerrar el sprint quedarán **13 de 14 historias terminadas**, y hay que
   decirlo así en la Sprint Review en vez de forzar una marca que `DoD-1` no respalda.
4. **El Avance 1 cae la semana 10, una semana después de cerrar el sprint, y `DoD-4` sigue
   suspendido.** Si el entorno desplegado no se restaura antes, hay que decidir **cómo** se
   demuestra el prototipo —y decidirlo en la primera Daily del sprint, no la víspera—.
   Enseñarlo desde el portátil de alguien es posible, pero es una decisión, no un accidente.
5. **Si el sprint desborda**, los candidatos a mover al Sprint 3 son `PR-05` (`HU-52`) y
   `PR-08` (`HU-16`): son los dos únicos `Should` y **ninguna otra historia depende de
   ellos**. Quedan 14 PR y 34 tareas, sin tocar la ruta de la venta.
6. **Este plan no reordena nada.** Si alguien propone mover una tarea de PR, hay que
   comprobar el `ANEXO C` del sprint backlog antes: el orden es un orden topológico
   verificado, y romperlo introduce un bloqueo que no se ve hasta que alguien está a mitad
   de la tarea.
