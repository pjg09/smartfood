# SmartFood — Sprint Backlog del Sprint 2

## [S0] Bloque de control del documento

### [S0.1] Metadatos

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-SPRINT2 |
| titulo | Sprint Backlog del Sprint 2 — Billetera digital e identificación por tarjeta en el POS |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./backlog-historias-de-usuario.md` (`[S5]`, Sprint 2); `./decisiones-de-alcance.md`; `./decisiones-tecnicas.md`; `./smartfood.md` (`S11`, `S12`); `corpus:guia-de-scrum-2020.md` (`ART-2`, `COM-2`, `COM-3`) |
| tipo_documento | Sprint Backlog (`ART-2` de la Guía de Scrum) |
| sprint | 2 de 5 |
| semanas | 8 – 9 |
| hito | **Avance 1 · semana 10** (`EVA-3`, 20 % de la nota) |
| historias | 14 (`HU-06`, `HU-08`, `HU-07`, `HU-52`, `HU-27`, `HU-15`, `HU-16`, `HU-17`, `HU-58`, `HU-54`, `HU-21`, `HU-22`, `HU-19`, `HU-53`) — **`HU-17` no cierra aquí**: le falta un criterio que depende del Sprint 3, ver `[S4]` y `ANEXO A` |
| tareas | 37 (`TT-57` … `TT-93`) |
| stack | Django + PostgreSQL + HTMX (`DT-2`, `DT-3` de `./decisiones-tecnicas.md`) |
| idioma | es-CO |
| version | 1.0 |

### [S0.2] Instrucciones de lectura para el agente

1. Documento **derivado**: no reexpresa ningún original y no lleva texto verbatim.
2. Es el **Sprint Backlog** en el sentido de `ART-2` de la Guía de Scrum: el Objetivo del Sprint, las historias seleccionadas y **el plan para entregarlas**.
3. **Ninguna tarea introduce alcance nuevo.** Cada una se deriva de una historia de `./backlog-historias-de-usuario.md` o es trabajo de habilitación sin el cual esas historias no pueden construirse.
4. **La serie `TT-` continúa la del Sprint 1**, que terminó en `TT-56`. No se reinicia: un `TT-nn` identifica una tarea del proyecto, no una tarea de un sprint, y reiniciar la numeración haría ambiguo cualquier `TT-23`.
5. Los responsables salen de la matriz `[S12]` de `./smartfood.md`. Es la previsión de Sprint Planning (`EVT-1`), no una asignación rígida.
6. **La columna `Estado` marca el avance.** `☑` es finalizada —integrada en `main`—, `☐` es pendiente. El estado se lleva **también** en `./plan-de-pull-requests-sprint-2.md`, que agrupa estas tareas en Pull Requests; si hay discrepancia, manda ese documento.
7. Los identificadores `[TT-nn]` son estables y citables.

### [S0.3] Mapa de secciones

| ID | Sección | Contenido |
|---|---|---|
| S1 | Objetivo del Sprint | `COM-2` |
| S2 | Definición de Terminado | Puntero a `./definicion-de-terminado.md` (`COM-3`) |
| S3 | Tareas de habilitación | `TT-57` … `TT-58`, sin historia asociada |
| S4 | Tareas por historia | `TT-59` … `TT-90` |
| S5 | Tareas de gestión del Sprint | `TT-91` … `TT-93` |
| S6 | Reparto por responsable | Carga de cada integrante |
| ANEXO A | Riesgos del sprint | Lo que puede salir mal y qué hacer |
| ANEXO B | Nota de procedencia | Cómo se derivó |
| ANEXO C | Verificación del orden de construcción | Grafo de dependencias |

---

## [S1] Objetivo del Sprint `[COM-2]`

> Que un cajero identifique a un estudiante con su tarjeta, vea quién es y cuánto tiene, y le cobre un producto descontando a la vez el saldo de su billetera y las existencias del inventario, sin que ninguna venta pueda dejar el saldo en negativo.

Al cerrar el Sprint 2 **el sistema vende**. Es el corazón del prototipo y lo que se demuestra en el **Avance 1** de la semana 10 (`EVA-3`).

Lo que **no** entra: las restricciones alimentarias y el límite diario son del Sprint 3. Aquí la venta se rechaza por saldo, no por alérgeno.

---

## [S2] Definición de Terminado `[COM-3]`

La misma de todo el semestre: `./definicion-de-terminado.md`. No se relaja.

> ⏸ **`DoD-4` sigue suspendido** mientras el entorno desplegado esté congelado (`[S2]` de `./despliegue.md`). Cada tarea declara su verificación local. **Si el entorno se restaura durante este sprint, `DoD-4` vuelve a aplicar** y hay que demostrar en él lo cerrado desde entonces — y el Avance 1 de la semana 10 es exactamente el momento en que hará falta.

---

## [S3] Tareas de habilitación

El punto de venta es una **interfaz nueva** (`INT-2`). No existía nada de ella al cerrar el Sprint 1: las tres bases de plantilla construidas cubren acudiente, acceso y páginas públicas, y `INT-3` lo resuelve el admin.

| ID | Tarea | Responsable | Habilita | Estado |
|---|---|---|---|---|
| `TT-57` | Layout del punto de venta: pantalla completa, sin navegación, foco permanente y operación por teclado (`INT-2`, `DT-16`) | Carlos | `HU-15`, `HU-16`, `HU-17` | ☑ |
| `TT-58` | Ruta del punto de venta y su control de acceso: solo el rol cajero (`S11`, `DT-11`) | Pedro | Todo `[S4]` a partir de `HU-15` | ☑ |

> **`TT-57` y `TT-58` no cierran ninguna historia**, igual que las nueve de habilitación del Sprint 1. Se declaran aquí para que no queden invisibles en la planeación.

---

## [S4] Tareas por historia

**El orden en que están escritas es el orden en que se pueden desarrollar.** Cada tarea va después de todo lo que la bloquea; el `ANEXO C` lo verifica.

### `[HU-06]` Recarga de la billetera

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-59` | App `billetera`: modelos de billetera y de movimiento, **sin columna de saldo** (`DT-4`) | Pedro | ☑ |
| `TT-60` | Servicio de recarga que asienta un movimiento dentro de una transacción | Pedro | ☑ |
| `TT-61` | Pantalla de recarga en la interfaz del acudiente | Carlos | ☑ |

`TT-59` es la tarea más determinante del sprint. **No existe una columna `saldo`**: el saldo es la suma de los movimientos (`DT-4`), y de ahí sale `INV-2` por construcción. Si aparece una columna que se actualiza, `HU-08` deja de cumplirse y hay que rehacer el modelo.

El pago de la recarga es **simulado** (`ALC-OUT-01`, `ALC-OUT-02`): no hay pasarela ni dinero real.

### `[HU-08]` Saldo reconstruible desde el historial

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-62` | Selector que calcula el saldo como suma del historial de movimientos (`INV-2`) | Pedro | ☑ |
| `TT-63` | Caso de prueba `TST-3`: el saldo mostrado coincide **exactamente** con la suma del historial | Alejandro | ☑ |

`TST-3` es uno de los cuatro escenarios críticos que `ENT-05` exige demostrar. Con `DT-4` se cumple por construcción, pero la prueba tiene que existir igual: es lo que detecta que alguien introdujo un atajo.

### `[HU-07]` Consulta de saldo por el acudiente

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-64` | Saldo y últimos movimientos en la ficha del estudiante, en la interfaz del acudiente | Carlos | ☑ |

Solo el acudiente ve el saldo como consulta libre. El cajero lo ve **solo al cobrar** (`S11`), que es `HU-17`.

### `[HU-52]` Saldo congelado y consultable tras la baja

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-65` | El estado `baja` impide recargar y comprar, y conserva el saldo consultable (`INVD-2`) | Pedro | ☑ |
| `TT-66` | Caso de prueba: estudiante de baja, saldo visible y sin operaciones posibles | Alejandro | ☑ |

Cierra la historia que el Sprint 1 dejó a medias: `HU-51` construyó la baja lógica, pero sin billetera no había saldo que congelar. La devolución del dinero queda **fuera del sistema**.

### `[HU-27]` Ingreso de mercancía por ajuste manual

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-67` | App `inventario`: modelo de movimiento como libro, **sin columna de existencias**, con motivo obligatorio por restricción de base de datos (`DT-5`, `INV-8`) | Pedro | ☑ |
| `TT-68` | Servicio de ingreso de mercancía por ajuste manual | Pedro | ☑ |
| `TT-69` | Registro del ingreso desde la interfaz administrativa, con las existencias calculadas | Carlos | ☑ |

Mismo criterio que `TT-59`: las existencias son la suma del historial (`DT-5`), no una columna. La restricción de motivo obligatorio se crea aquí aunque `INV-8` lo ejercite `HU-28`, en el Sprint 4: **es más barato ponerla con el modelo que añadirla sobre datos ya escritos**.

El inventario opera sobre **unidades vendibles**. Nada de insumos, recetas ni costo de producción (`ALC-OUT-11`, `ALC-OUT-12`, `ALC-OUT-13`).

### `[HU-15]` Identificación por escaneo de la tarjeta

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-70` | Selector de identificación por código de tarjeta, que respeta el estado del estudiante | Pedro | ☑ |
| `TT-71` | Campo de escaneo con foco permanente que dispara la búsqueda al recibir Enter (`DT-16`) | Carlos | ☑ |
| `TT-72` | Prueba de concepto con el lector físico y tarjetas impresas (`ENT-02`, `ALC-OUT-05`) | Alejandro | ☑ |

El lector **es un teclado**: teclea el código y envía Enter. No hay driver ni integración. `TT-71` es un campo con foco que se recupera al perderse.

`TT-72` cierra `ENT-02`, uno de los siete entregables del proyecto. Las tarjetas se imprimieron con lo que construyó `TT-37` en el Sprint 1. **Ejecutada el 2026-09-11**: el guion está en `./prueba-de-concepto-del-lector.md` y la evidencia, en `ENT-05`. Con ella `HU-15` queda cerrada.

### `[HU-16]` Identificación alternativa por documento

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-73` | Búsqueda por documento en el punto de venta, con el mismo resultado que el escaneo | Carlos | ☑ |

### `[HU-17]` Vista de cobro con saldo, consumo y restricciones

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-74` | Selector de la información de cobro: saldo y consumo del día del estudiante | Pedro | ☐ |
| `TT-75` | Panel del estudiante en el punto de venta | Carlos | ☐ |
| `TT-76` | Caso de prueba: el cajero ve el saldo **solo al cobrar**, no como consulta libre (`S11`) | Alejandro | ☐ |

> ⚠ **Esta historia no puede cerrarse en el Sprint 2.** Su tercer criterio de aceptación exige mostrar **las restricciones vigentes**, y las restricciones son `HU-09` … `HU-13`, del **Sprint 3**. El panel se construye aquí con saldo y consumo del día, y el bloque de restricciones lo añade `HU-13`, que declara depender de `HU-17`.
>
> Bajo `DoD-1` —«todos los criterios de aceptación se cumplen»— `HU-17` queda **abierta al cierre del sprint** y se marca terminada en el Sprint 3. No es un descuido de la planeación: es una consecuencia del reparto en cinco sprints, y vale más declararla que descubrirla al revisar. Ver `ANEXO A`.

### `[HU-58]` Fotografía visible al cobrar

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-77` | Fotografía del estudiante en el panel de cobro, con marcador visible cuando no la tiene | Carlos | ☐ |

Control **preventivo** de suplantación (`DEC-8`): el cajero ve a quién pertenece la tarjeta que le presentan. Si el estudiante no tiene fotografía, la venta procede igual.

### `[HU-54]` Medio de pago en toda venta

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-78` | App `ventas`: modelos de venta y línea de venta, con medio de pago y **estudiante opcional** (`DEC-1`) | Pedro | ☐ |
| `TT-79` | Selección del medio de pago en el punto de venta | Carlos | ☐ |

**Va antes que la venta a propósito.** El medio de pago es un campo del asiento; añadirlo después obliga a reescribir transacciones ya registradas, que es lo que `INV-2` prohíbe.

El **estudiante opcional** es lo que habilita `HU-53`: una venta sin estudiante es una venta a cliente genérico. La transferencia ocurre **fuera del sistema**; solo se deja constancia.

### `[HU-21]` Descuento simultáneo de saldo y existencias

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-80` | Servicio de venta: **una** transacción con bloqueo pesimista sobre la billetera y los productos (`DT-6`) | Pedro | ☐ |
| `TT-81` | Carrito y confirmación de la venta en el punto de venta, **sin diálogos de confirmación** (`DT-16`) | Carlos | ☐ |
| `TT-82` | Caso de prueba de concurrencia: dos ventas simultáneas sobre la misma billetera | Alejandro | ☐ |
| `TT-83` | Caso de prueba: saldo y existencias se descuentan en la misma operación, o ninguno (`INV-2`, `INV-3`) | Alejandro | ☐ |

**`TT-80` es la tarea de mayor riesgo del proyecto.** `DT-6` es explícito: se bloquea, **luego** se valida, **luego** se escribe. Validar fuera del bloqueo abre la ventana en la que dos cajeros cobran a la vez, ambos ven saldo suficiente e `INV-1` se rompe. Con 2 a 5 cajeros en una ventana de veinte a treinta minutos, esa concurrencia es real.

`TT-82` existe porque una prueba secuencial no detecta ese fallo.

### `[HU-22]` Venta con información nutricional congelada

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-84` | Instantánea del precio y de la información nutricional en la línea de venta (`DT-8`) | Pedro | ☐ |
| `TT-85` | Caso de prueba: editar un producto no altera las ventas ya asentadas | Alejandro | ☐ |

No es una desnormalización: «lo que el producto declara hoy» y «lo que declaraba al venderse» son hechos distintos (`DT-19`). Sostiene los reportes de consumo del Sprint 5.

### `[HU-19]` Venta rechazada por saldo insuficiente

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-86` | Validación del saldo **dentro** del bloqueo; si no alcanza, la venta no se realiza (`INV-1`) | Pedro | ☐ |
| `TT-87` | Caso de prueba `TST-2`: venta rechazada por saldo insuficiente, y saldo nunca negativo | Alejandro | ☐ |

`TST-2` es escenario crítico de `ENT-05`. Su otra mitad —rechazo por límite diario— es `HU-20`, del Sprint 3.

### `[HU-53]` Venta a cliente genérico

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-88` | Venta sin estudiante: descuenta inventario, **no** toca ninguna billetera y no aplica restricciones (`DEC-1`) | Pedro | ☐ |
| `TT-89` | Modo de cliente genérico en el punto de venta | Carlos | ☐ |
| `TT-90` | Caso de prueba: la venta genérica descuenta inventario y no altera ninguna billetera | Alejandro | ☐ |

Cierra `VAC-1`, el hueco más serio que tenía el anteproyecto: `[S5]` declaraba `USR-6` y exigía registrar sus ventas, sin ningún `ALC-IN` que lo respaldara.

---

## [S5] Tareas de gestión del Sprint

| ID | Tarea | Responsable | Origen | Estado |
|---|---|---|---|---|
| `TT-91` | Tablero Kanban del Sprint 2 con sus tareas y estado | Naomi | `CUR-3` | ☐ |
| `TT-92` | Registro de riesgos del Sprint 2 y seguimiento en las Daily | Naomi | `ENT-04` | ☐ |
| `TT-93` | Preparación de la Sprint Review, la Retrospective y **el Avance 1** (`EVA-3`) | Naomi | `EVT-3`, `EVT-4` | ☐ |

`TT-93` pesa más que su equivalente del Sprint 1: el Avance 1 de la semana 10 vale el **20 %** de la nota y es la primera vez que el proyecto se enseña fuera del equipo.

---

## [S6] Reparto por responsable

| Integrante | Rol `[S12]` | Tareas | Cuáles |
|---|---|---|---|
| **Pedro** | Desarrollador backend | **14** | `TT-58`, `TT-59`, `TT-60`, `TT-62`, `TT-65`, `TT-67`, `TT-68`, `TT-70`, `TT-74`, `TT-78`, `TT-80`, `TT-84`, `TT-86`, `TT-88` |
| **Carlos** | Desarrollador frontend | **11** | `TT-57`, `TT-61`, `TT-64`, `TT-69`, `TT-71`, `TT-73`, `TT-75`, `TT-77`, `TT-79`, `TT-81`, `TT-89` |
| **Alejandro** | Analista de datos y UX | **9** | `TT-63`, `TT-66`, `TT-72`, `TT-76`, `TT-82`, `TT-83`, `TT-85`, `TT-87`, `TT-90` |
| **Naomi** | Líder de proyecto | **3** | `TT-91`, `TT-92`, `TT-93` |

**Total: 37 tareas.**

El reparto está mucho más equilibrado que el del Sprint 1, donde Pedro salió a 26 tareas. Aquí son 14, y Alejandro sube a 9 casi todas de pruebas: este sprint construye la lógica transaccional, que es justo donde las pruebas valen.

---

## [ANEXO A] Riesgos del sprint

**1. `HU-17` no puede cerrarse aquí.** Su criterio de mostrar restricciones necesita el Sprint 3. Declarado en `[S4]`. Al cierre del sprint quedará **13 de 14 historias terminadas**, y eso hay que decirlo en la Sprint Review en vez de forzar una marca de terminada que `DoD-1` no respalda.

**2. `TT-80` concentra el riesgo técnico del proyecto.** La transacción de venta sostiene `INV-1`, `INV-2` e `INV-3` a la vez. Si sale mal, no falla una historia: falla el prototipo. Merece revisión de los dos desarrolladores, no solo la cruzada de rigor.

**3. El Avance 1 cae en la semana 10, una semana después de cerrar el sprint.** No hay colchón. Si el sprint desborda, lo que se enseña el día del Avance es lo que haya en `main`.

**4. `DoD-4` sigue suspendido y el Avance 1 lo va a necesitar.** Enseñar el prototipo desde el portátil de alguien es posible pero frágil. Si el entorno desplegado no se restaura antes de la semana 10, decidid pronto **cómo** se demuestra, y no la víspera.

**5. Si el sprint desborda**, los candidatos a mover al Sprint 3 son `HU-52` (`TT-65`, `TT-66`) y `HU-16` (`TT-73`): son los dos únicos `Should` del sprint y **ninguna otra historia depende de ellos**. Sacarlos deja 34 tareas y 12 historias, sin tocar la ruta de la venta.

---

## [ANEXO B] Nota de procedencia

Documento producido por el equipo el 2026-09-06, al cerrar el Sprint 1.

Las 37 tareas se derivaron de las 14 historias del Sprint 2 de `[S5]` de `./backlog-historias-de-usuario.md`, descomponiendo cada una en el trabajo necesario para satisfacer sus criterios de aceptación. Las dos de habilitación y las tres de gestión no provienen de ninguna historia y se declaran como tales.

Los responsables salen de la matriz `[S12]` de `./smartfood.md`. La serie `TT-` continúa la del Sprint 1: este sprint va de `TT-57` a `TT-93`.

**Ninguna tarea introduce alcance.** No hay tarea que implemente algo que no esté en una historia, y no hay historia del Sprint 2 sin tareas.

---

## [ANEXO C] Verificación del orden de construcción

El orden de las 37 tareas se comprobó por script contra el grafo de dependencias:

| Comprobación | Resultado |
|---|---|
| Tareas colocadas | 37 de 37, ninguna repetida |
| Tareas situadas antes de algo que las bloquea | **0** |

**Se desarrolla de arriba abajo, sin excepciones.**

### Dependencias que cruzan de historia

| Tarea | Necesita | De |
|---|---|---|
| `TT-62` Selector de saldo | `TT-59` Modelos de billetera | `HU-06` |
| `TT-64` Saldo en la ficha | `TT-62` Selector de saldo | `HU-08` |
| `TT-65` Baja congela el saldo | `TT-59` Modelos de billetera | `HU-06` |
| `TT-71` Campo de escaneo | `TT-57`, `TT-58` Layout y ruta del POS | habilitación |
| `TT-73` Búsqueda por documento | `TT-70`, `TT-71` Identificación y campo | `HU-15` |
| `TT-74` Información de cobro | `TT-62` Selector de saldo | `HU-08` |
| `TT-75` Panel del estudiante | `TT-74`, `TT-71` | `HU-17`, `HU-15` |
| `TT-77` Fotografía al cobrar | `TT-75` Panel del estudiante | `HU-17` |
| `TT-78` Modelos de venta | `TT-59`, `TT-67` Libros de billetera e inventario | `HU-06`, `HU-27` |
| `TT-80` Servicio de venta | `TT-78`, `TT-60`, `TT-68`, `TT-62` | `HU-54`, `HU-06`, `HU-27`, `HU-08` |
| `TT-84` Instantánea nutricional | `TT-80` Servicio de venta | `HU-21` |
| `TT-86` Validación de saldo | `TT-80` Servicio de venta | `HU-21` |
| `TT-88` Venta genérica | `TT-80`, `TT-78` | `HU-21`, `HU-54` |

### Dependencias con el Sprint 1

Todo lo siguiente ya está en `main` y no bloquea nada:

| Necesita | Del Sprint 1 |
|---|---|
| `TT-59` Billetera por estudiante | `TT-21` Modelos de estudiante y acudiente |
| `TT-65` Estado de baja | `TT-41` Baja lógica |
| `TT-67` Movimientos de producto | `TT-43` Modelos del catálogo |
| `TT-70` Identificación por código | `TT-30`, `TT-32` Generación y asignación del código |
| `TT-72` Prueba con lector físico | `TT-37` Vista imprimible del código de barras |
| `TT-77` Fotografía al cobrar | `TT-51` Fotografía del estudiante |

### Trabajo en paralelo

**Ocho raíces**, sin dependencia alguna dentro del sprint, que pueden arrancarse el primer día: cinco técnicas —`TT-57` (layout del POS), `TT-58` (ruta y acceso), `TT-59` (modelos de billetera), `TT-67` (modelos de inventario) y `TT-70` (identificación por código)— más las tres de gestión.

`TT-59` y `TT-67` son las dos raíces de backend y no se tocan entre sí: son dos libros de movimientos independientes que solo se encuentran en `TT-80`.
