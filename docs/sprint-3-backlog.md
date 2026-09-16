# SmartFood — Sprint Backlog del Sprint 3

## [S0] Bloque de control del documento

### [S0.1] Metadatos

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-SPRINT3 |
| titulo | Sprint Backlog del Sprint 3 — Control parental: restricciones, alérgenos, límite de gasto |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./backlog-historias-de-usuario.md` (`[S5]`, Sprint 3); `./decisiones-de-alcance.md`; `./decisiones-tecnicas.md`; `./smartfood.md` (`S11`, `S12`); `corpus:guia-de-scrum-2020.md` (`ART-2`, `COM-2`, `COM-3`) |
| tipo_documento | Sprint Backlog (`ART-2` de la Guía de Scrum) |
| sprint | 3 de 5 |
| semanas | 10 – 11 |
| hito | ninguno propio. El **Avance 2** (`EVA-4`) cae en la semana 14, al cerrar el Sprint 4 |
| historias | 13 (`HU-09`, `HU-10`, `HU-11`, `HU-12`, `HU-13`, `HU-38`, `HU-18`, `HU-20`, `HU-47`, `HU-48`, `HU-49`, `HU-50`, `HU-60`) **más el cierre de `HU-17`**, que el Sprint 2 dejó abierta. `HU-60` se añadió durante el sprint (`ANEXO A`, punto 5) |
| tareas | 40 (`TT-94` … `TT-133`) |
| stack | Django + PostgreSQL + HTMX (`DT-2`, `DT-3` de `./decisiones-tecnicas.md`) |
| idioma | es-CO |
| version | 1.0 |

### [S0.2] Instrucciones de lectura para el agente

1. Documento **derivado**: no reexpresa ningún original y no lleva texto verbatim.
2. Es el **Sprint Backlog** en el sentido de `ART-2` de la Guía de Scrum: el Objetivo del Sprint, las historias seleccionadas y **el plan para entregarlas**.
3. **Ninguna tarea introduce alcance nuevo.** Cada una se deriva de una historia de `./backlog-historias-de-usuario.md`.
4. **La serie `TT-` continúa**: el Sprint 1 terminó en `TT-56` y el Sprint 2 en `TT-93`. No se reinicia — un `TT-nn` identifica una tarea del proyecto, no de un sprint.
5. Los responsables salen de la matriz `[S12]` de `./smartfood.md`. Es la previsión de Sprint Planning (`EVT-1`), no una asignación rígida.
6. **La columna `Estado` marca el avance.** `☑` es finalizada —integrada en `main`—, `☐` es pendiente. El estado se lleva **también** en `./plan-de-pull-requests-sprint-3.md`; si hay discrepancia, manda ese documento.
7. Los identificadores `[TT-nn]` son estables y citables.

### [S0.3] Mapa de secciones

| ID | Sección | Contenido |
|---|---|---|
| S1 | Objetivo del Sprint | `COM-2` |
| S2 | Definición de Terminado | Puntero a `./definicion-de-terminado.md` (`COM-3`) |
| S3 | Tareas de habilitación | **Ninguna.** Se explica por qué |
| S4 | Tareas por historia | `TT-94` … `TT-127`, `TT-131` … `TT-133` |
| S5 | Tareas de gestión del Sprint | `TT-128` … `TT-130` |
| S6 | Reparto por responsable | Carga de cada integrante |
| ANEXO A | Riesgos del sprint | Lo que puede salir mal y qué hacer |
| ANEXO B | Nota de procedencia | Cómo se derivó |
| ANEXO C | Verificación del orden de construcción | Grafo de dependencias |

---

## [S1] Objetivo del Sprint `[COM-2]`

> Que el acudiente decida qué y cuánto puede consumir su hijo —límite diario, productos bloqueados y alérgenos bloqueados— y que el punto de venta lo haga cumplir sin que nadie de la cafetería pueda saltárselo.

El Sprint 2 construyó la venta. Este sprint construye **los límites de la venta**, que es la razón de ser del proyecto: `OBJ-E5` y la ruptura `RUP-1` del anteproyecto.

Cierra además los **dos escenarios críticos** que faltaban de `ENT-05`: `TST-1` (rechazo por alérgeno) y la mitad pendiente de `TST-2` (rechazo por límite diario).

---

## [S2] Definición de Terminado `[COM-3]`

La misma de todo el semestre: `./definicion-de-terminado.md`. No se relaja.

Consultar el estado de `DoD-4` —demostración en el entorno desplegado— en `[S5]` de ese documento antes de cerrar el primer PR del sprint.

---

## [S3] Tareas de habilitación

**Ninguna.** Es el primer sprint que no las necesita.

El Sprint 1 tuvo nueve —repositorio, entorno, despliegue, correo, buckets— y el Sprint 2 tuvo dos, porque el punto de venta era una interfaz nueva. Aquí las tres interfaces ya existen, el modelo de datos está asentado y la transacción de venta está construida: todo lo que este sprint hace es **añadir reglas a lo que ya funciona**.

> **Una decisión que este sprint tendrá que tomar y registrar.** Las restricciones no encajan en ninguna de las siete apps que `DT-15` declaró: pertenecen al estudiante pero referencian el catálogo, así que meterlas en `personas` acopla ese dominio con `catalogo` y meterlas en `catalogo` lo acopla al revés. Este plan asume una app nueva, `restricciones`, que depende de ambas. **Es una desviación de `DT-15` y hay que registrarla con un `DT-` propio** en el PR que la cree, no darla por supuesta.

---

## [S4] Tareas por historia

**El orden en que están escritas es el orden en que se pueden desarrollar.** Cada tarea va después de todo lo que la bloquea; el `ANEXO C` lo verifica.

### `[HU-09]` Límite diario de gasto

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-94` | App `restricciones` y modelo de límite diario por estudiante | Pedro | ☑ |
| `TT-95` | Servicio para fijar y modificar el límite, **solo por el acudiente** (`S11`) | Pedro | ☑ |
| `TT-96` | Pantalla del límite diario en la interfaz del acudiente | Carlos | ☑ |

`TT-94` creó la app que usan las tres historias de restricción, y la desviación de `DT-15` que anticipaba `[S3]` quedó registrada como **`DT-28`** en `./decisiones-tecnicas.md`.

> **`HU-09` no se cierra con estas tres tareas.** Sus dos primeros criterios sí —el límite es por estudiante y solo lo fija su acudiente—, pero el tercero, «se evalúa contra el consumo del día en cada venta», es `TT-116` (`PR-09`). La historia se marca al integrar ese PR, junto con `HU-20`.

El límite es **por estudiante**, no por acudiente: un acudiente con varios hijos fija uno distinto a cada uno.

### `[HU-10]` Bloqueo de un producto puntual

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-97` | Modelo de restricción por producto, **distinto** del de alérgeno | Pedro | ☑ |
| `TT-98` | Servicio de bloqueo y desbloqueo de un producto, solo por el acudiente | Pedro | ☑ |
| `TT-99` | Selección de productos a bloquear en la interfaz del acudiente | Carlos | ☑ |

Los dos tipos de restricción se modelan **por separado** y no se unifican en una tabla con un campo «tipo». `HU-10` es una lista; `HU-11` es una condición. Mezclarlos invita a implementar el alérgeno como lista de productos, que es justo lo que `INV-5` prohíbe.

### `[HU-11]` Bloqueo por alérgeno

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-100` | Modelo de restricción por alérgeno, **sobre la condición** y no sobre una lista de productos (`INV-5`) | Pedro | ☑ |
| `TT-101` | Servicio de bloqueo y desbloqueo de un alérgeno, solo por el acudiente | Pedro | ☑ |
| `TT-102` | Selección de alérgenos a bloquear en la interfaz del acudiente | Carlos | ☑ |
| `TT-103` | Caso de prueba: un producto creado **después** del bloqueo queda cubierto si declara ese alérgeno (`INV-5`) | Alejandro | ☑ |

> **La tarea más delicada del sprint es `TT-100`.** `INV-5` exige que el bloqueo se aplique sobre el alérgeno, de modo que cubra productos futuros. La comprobación en la venta es un cruce entre `restriccion_alergeno` y la tabla `ProductoAlergeno` que ya existe del Sprint 2. Si alguien materializa la lista de productos bloqueados —porque consulta más rápido—, `INV-5` se rompe y no se nota hasta que la cafetería añade un producto.
>
> `TT-103` existe exactamente para detectar eso: crea el producto **después** de la restricción.

La dependencia de esta historia es `HU-26` (administración del catálogo, Sprint 1), que es donde los productos declaran sus alérgenos. Su criterio de aceptación **ya cita `HU-26`**: ver `ANEXO A`, punto 4.

### `[HU-12]` Retiro de una restricción

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-104` | Servicio de retiro que deja asiento auditable (`ALC-IN-19`) | Pedro | ☐ |
| `TT-105` | Acción de retirar en la interfaz del acudiente | Carlos | ☐ |

El retiro **se asienta**: es una acción sobre la seguridad alimentaria de un menor y tiene que poder reconstruirse quién la hizo y cuándo.

### `[HU-13]` Restricciones no desactivables por la cafetería · **cierra `HU-17`**

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-106` | Selector de las restricciones vigentes de un estudiante | Pedro | ☐ |
| `TT-107` | Permisos: ni cajero, ni administración de cafetería, ni institución escriben restricciones (`INV-4`, `DT-11`) | Pedro | ☐ |
| `TT-108` | Caso de prueba: los tres roles no tienen acción de escritura sobre restricciones (`INV-4`) | Alejandro | ☐ |
| `TT-109` | Bloque de restricciones vigentes en el panel de cobro — **cierra `HU-17`** | Carlos | ☐ |
| `TT-110` | Caso de prueba: `HU-17` completa — el panel muestra saldo, consumo del día y restricciones | Alejandro | ☐ |

> **Aquí se salda la deuda del Sprint 2.** `HU-17` quedó abierta porque su tercer criterio exige mostrar las restricciones vigentes y no existían. `TT-109` añade ese bloque al panel que ya construyó `TT-75`. **Al integrarse, `HU-17` se marca terminada** en `./backlog-historias-de-usuario.md`, además de `HU-13`.

`TT-107` es el corazón de `INV-4`: se aplica **en la capa de datos**, con permisos por modelo (`DT-11`). Ocultar el botón en la plantilla no es cumplir la invariante, es aparentarlo — y `TT-108` lo comprueba llamando al servicio con cada rol, no mirando la pantalla.

### `[HU-38]` Consulta de restricciones por los cuatro roles

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-111` | Consulta de restricciones habilitada a los cuatro roles, sobre el selector de `TT-106` (`S11`) | Pedro | ☐ |
| `TT-112` | Consulta de restricciones en la interfaz administrativa | Carlos | ☐ |

La matriz `[S11]` es explícita: los cuatro roles **consultan**, solo el acudiente **configura**. `HU-38` y `HU-13` son las dos caras de la misma fila.

### `[HU-18]` Venta rechazada por alérgeno bloqueado

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-113` | Validación del alérgeno **dentro** del bloqueo de la transacción de venta (`DT-6`) | Pedro | ☐ |
| `TT-114` | Motivo de rechazo por alérgeno, distinguible en el punto de venta | Carlos | ☐ |
| `TT-115` | Caso de prueba `TST-1`: venta rechazada por alérgeno bloqueado, sin vía para forzarla | Alejandro | ☐ |

**`TST-1` es el primero de los cuatro escenarios críticos de `ENT-05`** y el que da sentido al proyecto: un niño alérgico no puede comprar lo que le hace daño. La validación va **dentro** del bloqueo que ya monta `registrar_venta`, junto a las de saldo y existencias: fuera de él, dos ventas simultáneas podrían colarse.

El cajero **no tiene** forma de forzar la venta. No es un aviso que se pueda descartar.

### `[HU-20]` Venta rechazada por límite diario superado

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-116` | Validación del límite diario contra el consumo del día, dentro del bloqueo | Pedro | ☐ |
| `TT-117` | Motivo de rechazo por límite, **distinguible del de saldo** | Carlos | ☐ |
| `TT-118` | Caso de prueba `TST-2`: rechazo por cupo del día **aunque haya saldo** | Alejandro | ☐ |

Completa `TST-2`, cuya otra mitad —rechazo por saldo— cerró `HU-19` en el Sprint 2.

El caso que hay que probar es el contraintuitivo: **hay saldo de sobra y aun así la venta se rechaza**, porque el cupo del día está agotado. Si el mensaje dice «saldo insuficiente», el cajero le dará una explicación falsa al estudiante.

### `[HU-47]` Desactivación de un estudiante por la institución

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-119` | Transición a `desactivado` desde el padrón de la institución | Pedro | ☐ |
| `TT-120` | Acción de desactivar en la ficha del padrón | Carlos | ☐ |

Se apoya en `EstadoDelEstudiante`, que ya existe desde `HU-51` (Sprint 1). No hay modelo nuevo: hay una transición nueva.

### `[HU-48]` Desactivación de un estudiante por el acudiente

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-121` | Transición a `desactivado` por el acudiente, **sin acción de reactivar** (`INVD-3`) | Pedro | ☐ |
| `TT-122` | Acción de desactivar en la interfaz del acudiente | Carlos | ☐ |

Las dos vías cubren tiempos distintos (`DEC-5`): la institución bloquea de inmediato cuando la tarjeta se pierde en mitad de la jornada; el acudiente bloquea sin depender del horario de la secretaría.

### `[HU-49]` Reactivación exclusiva de la institución

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-123` | Reactivación permitida **solo** a la institución, con independencia de quién desactivó (`INVD-3`) | Pedro | ☐ |
| `TT-124` | Caso de prueba: el acudiente que desactivó **no** puede reactivar | Alejandro | ☐ |

La asimetría es deliberada y tiene un motivo de seguridad: el desbloqueo pasa siempre por una verificación presencial, y eso es lo que impide que quien encontró la tarjeta consiga que se reactive.

### `[HU-50]` Venta rechazada por estudiante desactivado

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-125` | Rechazo de venta y de retiro de pedido para estudiante desactivado o de baja (`INVD-2`) | Pedro | ☐ |
| `TT-126` | Motivo de rechazo por desactivación, **distinto** de los de saldo, alérgeno y límite | Carlos | ☐ |
| `TT-127` | Caso de prueba: desactivado no compra, pero **sí recibe recargas** | Alejandro | ☐ |

Al cerrar esta historia, la venta tiene **cinco motivos de rechazo distintos**: saldo (`HU-19`), alérgeno (`HU-18`), límite diario (`HU-20`), producto bloqueado (`HU-60`) y estudiante desactivado (`HU-50`). Que se distingan no es cosmética: el cajero tiene que poder decirle al estudiante qué pasa, y solo uno de los cinco se arregla recargando.

### `[HU-60]` Venta rechazada por producto bloqueado

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-131` | Validación del producto bloqueado **dentro** del bloqueo de la transacción (`DT-6`) | Pedro | ☑ |
| `TT-132` | Motivo de rechazo por producto bloqueado, distinguible en el punto de venta | Carlos | ☑ |
| `TT-133` | Caso de prueba: venta rechazada con saldo de sobra, **sin vía para forzarla** | Alejandro | ☑ |

> **Historia añadida durante el sprint, no prevista en la planeación.** Se detectó al construir `PR-02`: `ALC-IN-09` pide aplicar las restricciones en el momento de la venta, y la lista de `HU-10` no tenía quién la hiciera cumplir. Las cuatro historias de rechazo cubrían alérgeno, saldo, límite y desactivación. Está explicado en el `ANEXO A`, punto 5.

**Va la última de `[S4]` por número de tarea, no por orden de construcción.** Solo depende de `HU-10` (`TT-97`…`TT-99`) y de `HU-21` (Sprint 2), así que pudo construirse en cuanto la primera estuvo — no espera a `HU-18`. Colocarla aquí conserva las dos propiedades del documento: los `TT-` ascendentes y un orden topológico válido, porque todo lo que la bloquea está antes.

`TT-132` estrena el mecanismo que usarán `TT-114`, `TT-117` y `TT-126`: cada clase de rechazo lleva una etiqueta estable que llega hasta el HTML del ticket, de modo que una prueba pueda exigir **cuál** se enseñó sin buscar una frase dentro del mensaje.

---

## [S5] Tareas de gestión del Sprint

| ID | Tarea | Responsable | Origen | Estado |
|---|---|---|---|---|
| `TT-128` | Tablero Kanban del Sprint 3 con sus tareas y estado | Naomi | `CUR-3` | ☐ |
| `TT-129` | Registro de riesgos del Sprint 3 y seguimiento en las Daily | Naomi | `ENT-04` | ☐ |
| `TT-130` | Preparación de la Sprint Review y la Retrospective | Naomi | `EVT-3`, `EVT-4` | ☐ |

---

## [S6] Reparto por responsable

| Integrante | Rol `[S12]` | Tareas | Cuáles |
|---|---|---|---|
| **Pedro** | Desarrollador backend | **17** | `TT-94`, `TT-95`, `TT-97`, `TT-98`, `TT-100`, `TT-101`, `TT-104`, `TT-106`, `TT-107`, `TT-111`, `TT-113`, `TT-116`, `TT-119`, `TT-121`, `TT-123`, `TT-125`, `TT-131` |
| **Carlos** | Desarrollador frontend | **12** | `TT-96`, `TT-99`, `TT-102`, `TT-105`, `TT-109`, `TT-112`, `TT-114`, `TT-117`, `TT-120`, `TT-122`, `TT-126`, `TT-132` |
| **Alejandro** | Analista de datos y UX | **8** | `TT-103`, `TT-108`, `TT-110`, `TT-115`, `TT-118`, `TT-124`, `TT-127`, `TT-133` |
| **Naomi** | Líder de proyecto | **3** | `TT-128`, `TT-129`, `TT-130` |

**Total: 40 tareas.**

---

## [ANEXO A] Riesgos del sprint

**1. `INV-5` es fácil de romper sin enterarse.** Materializar la lista de productos bloqueados por estudiante es más rápido de consultar y parece equivalente. No lo es: los productos futuros dejan de estar cubiertos. `TT-103` es la red, pero la revisión de `TT-100` es la barrera.

**2. Las cuatro validaciones de venta comparten el mismo bloqueo.** `TT-113`, `TT-116` y `TT-125` añaden condiciones dentro de la transacción que `TT-80` construyó en el Sprint 2. Cada una es sencilla; el riesgo es el acumulado: tres PR seguidos tocando el mismo servicio transaccional. Revisad que el orden bloqueo → validación → escritura siga intacto después del tercero, no después de cada uno.

**3. `HU-17` arrastra desde el Sprint 2 y es fácil que se olvide.** No es una tarea: es una marca en otro documento. `TT-109` la cierra, y quien integre ese PR tiene que acordarse de marcarla en `./backlog-historias-de-usuario.md`. Está anotado en `[S4]` y en el plan de PR.

**4. Un defecto del backlog que conviene corregir.** El tercer criterio de `HU-11` decía «depende de que el catálogo declare alérgenos por producto (`HU-25`)», pero `HU-25` es «Registro de la entrega del pedido», del Sprint 4. La historia del catálogo es **`HU-26`**.

**Ya estaba resuelto al escribirse este aviso**, y se comprobó al construir `PR-03`: el mismo commit que planificó el sprint (`1294a69`) corrigió la referencia. El criterio cita `HU-26` desde entonces y no hace falta ningún PR. Se conserva el punto porque el aviso llegó a estar en pie y quien lo leyera iría a buscar un defecto que no existe.

**5. Ninguna historia rechaza una venta por producto bloqueado.** Encontrado al construir `TT-98` (`PR-02`). Hay cuatro historias de rechazo —`HU-18` alérgeno, `HU-19` saldo, `HU-20` límite diario y `HU-50` desactivado— y **ninguna para la lista de `HU-10`**. `HU-10` cierra con sus dos criterios cumplidos porque ninguno habla de la venta, pero `ALC-IN-09` sí: «aplicación de las restricciones **en el momento de la venta**». Tal como está, el acudiente bloquea la gaseosa y la caja se la cobra igual.

**Resuelto el 2026-09-16 con `HU-60`**, historia nueva —`TT-131` … `TT-133`, `PR-15`— en lugar de un criterio añadido a `HU-13`: el backlog tiene **una historia por motivo de rechazo**, la trazabilidad y el `DoD` funcionan por historia, y `ENT-05` organiza el plan de pruebas por escenario. La validación entró en el mismo bloqueo que tocarán `TT-113`, `TT-116` y `TT-125`, y va **la primera de las tres**: «está bloqueado» es el único motivo que no se arregla ni recargando ni reponiendo.

Que el punto llegó a estar abierto es información, y por eso se conserva: la planeación del sprint no lo vio, y lo que lo destapó fue construir la pantalla de `HU-10` y preguntarse qué pasaba al cobrar.

**6. Si el sprint desborda**, los candidatos a mover al Sprint 4 son `HU-12` (`TT-104`, `TT-105`) y `HU-38` (`TT-111`, `TT-112`): `HU-12` es el único `Should` del sprint y de `HU-38` no depende ninguna otra historia. Quedan 33 tareas. **No se pueden mover** `HU-18` ni `HU-20`: son los escenarios críticos `TST-1` y `TST-2` de `ENT-05`.

---

## [ANEXO B] Nota de procedencia

Documento producido por el equipo el 2026-09-15, al cerrar el Sprint 2.

Las 37 tareas se derivaron de las 12 historias del Sprint 3 de `[S5]` de `./backlog-historias-de-usuario.md`, más el cierre de `HU-17`, descomponiendo cada una en el trabajo necesario para satisfacer sus criterios de aceptación. Las tres de gestión no provienen de ninguna historia y se declaran como tales.

Los responsables salen de la matriz `[S12]` de `./smartfood.md`. La serie `TT-` continúa: este sprint va de `TT-94` a `TT-130`.

**Ninguna tarea introduce alcance.** No hay tarea que implemente algo que no esté en una historia, y no hay historia del Sprint 3 sin tareas.

---

## [ANEXO C] Verificación del orden de construcción

El orden de las 40 tareas se comprobó por script contra el grafo de dependencias:

| Comprobación | Resultado |
|---|---|
| Tareas colocadas | 40 de 40, ninguna repetida |
| Tareas situadas antes de algo que las bloquea | **0** |

**Se desarrolla de arriba abajo, sin excepciones.**

### Dependencias que cruzan de historia

| Tarea | Necesita | De |
|---|---|---|
| `TT-97` Modelo de producto bloqueado | `TT-94` App `restricciones` | `HU-09` |
| `TT-100` Modelo de alérgeno bloqueado | `TT-94` App `restricciones` | `HU-09` |
| `TT-104` Retiro de restricción | `TT-98`, `TT-101` Servicios de bloqueo | `HU-10`, `HU-11` |
| `TT-106` Selector de restricciones vigentes | `TT-95`, `TT-98`, `TT-101` | `HU-09`, `HU-10`, `HU-11` |
| `TT-107` Permisos de escritura | `TT-95`, `TT-98`, `TT-101` | `HU-09`, `HU-10`, `HU-11` |
| `TT-111` Consulta por los cuatro roles | `TT-106`, `TT-107` | `HU-13` |
| `TT-113` Validación de alérgeno en la venta | `TT-101`, `TT-106` | `HU-11`, `HU-13` |
| `TT-116` Validación del límite en la venta | `TT-95`, `TT-106` | `HU-09`, `HU-13` |
| `TT-126` Motivo de rechazo distinguible | `TT-113`, `TT-116`, `TT-125`, `TT-132` | `HU-18`, `HU-20`, `HU-50`, `HU-60` |
| `TT-131` Validación de producto bloqueado en la venta | `TT-98` Servicio de bloqueo | `HU-10` |
| `TT-132` Motivo de rechazo por producto bloqueado | `TT-131` | `HU-60` |

### Dependencias con sprints anteriores

Todo lo siguiente ya está en `main`:

| Necesita | De |
|---|---|
| `TT-94` Límite por estudiante | `TT-21` Modelos de estudiante (S1), `TT-59` Billetera (S2) |
| `TT-97`, `TT-100` Restricciones sobre el catálogo | `TT-43` Catálogo con alérgenos (S1) |
| `TT-109` Bloque en el panel de cobro | `TT-75` Panel del estudiante (S2) |
| `TT-113`, `TT-116`, `TT-125`, `TT-131` Validaciones | `TT-80` Transacción de venta (S2) |
| `TT-119`, `TT-121` Transiciones de estado | `TT-41` Estado del estudiante (S1), `TT-44` Padrón (S1) |

### Trabajo en paralelo

**Cinco raíces** sin dependencia dentro del sprint: `TT-94` (app y límite), `TT-119` (desactivación por la institución) y las tres de gestión.

`TT-131` … `TT-133` se añadieron después de la planeación y **no rompen el orden**: lo único que las bloquea dentro del sprint es `TT-98`, que va muy por delante. Van al final de `[S4]` para no romper los `TT-` ascendentes, y `TT-132` queda además antes que `TT-126`, que ahora lo necesita — el mecanismo de motivos lo estrena el primero que llegó.

`TT-94` y `TT-119` son dos frentes de backend que no se tocan: las restricciones y el estado del estudiante son cosas distintas y solo se encuentran en el punto de venta, al final. Pedro puede abrir los dos; Carlos tiene trabajo desde que `TT-95` esté.
