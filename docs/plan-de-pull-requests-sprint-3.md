# SmartFood — Plan de Pull Requests del Sprint 3

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-PR-SPRINT3 |
| plan anterior | `./plan-de-pull-requests-sprint-2.md` — cerrado, documento de archivo |
| titulo | Agrupación de las 37 tareas del Sprint 3 en Pull Requests, y estado de cada tarea |
| documentos_fuente | `./sprint-3-backlog.md` (`[S4]`, `[S5]`, `ANEXO C`); `./convenciones-de-git.md` (`[S1]`); `./definicion-de-terminado.md` |
| tipo_documento | Documento derivado de planificación. **No es un artefacto de Scrum** |
| sprint | 3 de 5 · semanas 10 – 11 |
| tareas cubiertas | 37 de 37 (`TT-94` … `TT-130`) |
| pull requests | 14 (`PR-01` … `PR-14`) |
| idioma | es-CO |
| version | 1.1 |

### [S0.1] Qué es este documento y qué no es

`main` está protegida: nada entra por `push` directo (`[S1]` de `./convenciones-de-git.md`).
Este documento responde a una sola pregunta operativa: **¿hasta dónde desarrollo antes de
parar, abrir un PR y seguir?**

**No reordena ni modifica ninguna tarea.** El orden de `./sprint-3-backlog.md` es el orden
de construcción verificado en su `ANEXO C`, y aquí se respeta carácter por carácter. Lo
único que este documento añade son **cortes**.

> **Este es el único sitio donde vive el estado de las tareas.** El sprint backlog es el
> plan y no se toca; el tablero de `TT-128` es la vista de la Daily. Si hay discrepancia,
> manda este documento.

> **Hay un plan por sprint y se conservan todos.** Los del Sprint 1 y 2 están en
> `./plan-de-pull-requests-sprint-1.md` y `./plan-de-pull-requests-sprint-2.md`, cerrados.

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
   enseñar en la Sprint Review.
2. **Un PR se revisa de una sentada.** Entre 1 y 4 tareas. Ninguno pasa de 4.
3. **Un PR no mezcla asuntos.** Las restricciones no viajan con el estado del estudiante
   aunque ambos acaben rechazando ventas.

---

## [S2] Cómo se marca una tarea como finalizada

1. Se cumplen los criterios de la Definición de Terminado que aplican al PR
   (`./definicion-de-terminado.md`). Consultar el estado de `DoD-4` antes del primer PR.
2. El PR se integra en `main` por revisión cruzada, nunca por `push` directo.
3. Se marca `☑` **en los dos documentos**: aquí, en `[S3.1]` y en la tabla del PR, y en
   `./sprint-3-backlog.md`.
4. Si el PR cierra una historia, se marca también en la tabla `[S4]` de
   `./backlog-historias-de-usuario.md`.

> ⚠ **Dos PR de este sprint cierran dos historias cada uno.**
>
> - **`PR-06`**: además de `HU-13`, salda `HU-17`, que el Sprint 2 dejó abierta.
> - **`PR-09`**: además de `HU-20`, salda `HU-09`, que `PR-01` dejó con su tercer
>   criterio pendiente —evaluar el límite contra el consumo del día en cada venta es
>   `TT-116`—.
>
> Son cuatro marcas en el backlog de historias, no dos.

---

## [S3] Avance del Sprint 3

| | Tareas | Pull Requests |
|---|---|---|
| **Finalizadas** | **3** de 37 | **1** de 14 |
| Pendientes | 34 | 13 |

| Responsable | Finalizadas | Total |
|---|---|---|
| Pedro | 2 | 16 |
| Carlos | 1 | 11 |
| Alejandro | 0 | 7 |
| Naomi | 0 | 3 |

### [S3.1] Estado de los 14 Pull Requests

| PR | Tareas | Qué cierra | Estado |
|---|---|---|---|
| `PR-01` | `TT-94`–`TT-96` | app `restricciones` (`DT-28`) · `HU-09` **salvo su tercer criterio** | ☑ |
| `PR-02` | `TT-97`–`TT-99` | `HU-10` | ☐ |
| `PR-03` | `TT-100`–`TT-103` | `HU-11` · **`INV-5`** | ☐ |
| `PR-04` | `TT-104`–`TT-105` | `HU-12` | ☐ |
| `PR-05` | `TT-106`–`TT-108` | Permisos de `HU-13` · **`INV-4`** | ☐ |
| `PR-06` | `TT-109`–`TT-110` | `HU-13` **y `HU-17`** | ☐ |
| `PR-07` | `TT-111`–`TT-112` | `HU-38` | ☐ |
| `PR-08` | `TT-113`–`TT-115` | `HU-18` · **`TST-1`** | ☐ |
| `PR-09` | `TT-116`–`TT-118` | `HU-20` **y `HU-09`** · **`TST-2`** | ☐ |
| `PR-10` | `TT-119`–`TT-120` | `HU-47` | ☐ |
| `PR-11` | `TT-121`–`TT-122` | `HU-48` | ☐ |
| `PR-12` | `TT-123`–`TT-124` | `HU-49` · `INVD-3` | ☐ |
| `PR-13` | `TT-125`–`TT-127` | `HU-50` · `INVD-2` | ☐ |
| `PR-14` | `TT-128`–`TT-130` | Gestión del sprint | ☐ |

---

## [S4] Los 14 Pull Requests

### Configuración del control parental — `PR-01` … `PR-04`

#### `PR-01` — `HU-09` Límite diario de gasto

| | |
|---|---|
| Título del PR | `feat(restricciones): fijar el límite diario de gasto del estudiante` |
| Rama | `feat/TT-94-limite-diario` |
| Responsables | Pedro y Carlos |
| Historia | `HU-09` — **no la cierra**: su tercer criterio es `TT-116`, en `PR-09` |
| Invariantes | ninguna directamente; habilita `HU-20` |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-94` | App `restricciones` y modelo de límite diario por estudiante | Pedro | ☑ |
| `TT-95` | Servicio para fijar y modificar el límite, solo por el acudiente | Pedro | ☑ |
| `TT-96` | Pantalla del límite diario en la interfaz del acudiente | Carlos | ☑ |

> **Este PR creó una app que `DT-15` no previó**, y la desviación quedó registrada como
> **`DT-28`** en `./decisiones-tecnicas.md`, como se hizo con `DT-24` … `DT-27` en el
> Sprint 2.

> ⚠ **`PR-01` no cierra `HU-09`, y el plan lo daba por hecho.** Cumple sus dos primeros
> criterios —el límite se define por estudiante, y solo su acudiente lo fija o lo
> modifica—, pero el tercero dice «el límite se evalúa contra el consumo del día en cada
> venta», que es la validación dentro del bloqueo de la transacción: `TT-116`, de `PR-09`.
> Es la misma frase que da sentido a `HU-20`. **`HU-09` se marca en
> `./backlog-historias-de-usuario.md` al integrar `PR-09`**, junto con `HU-20`, y hasta
> entonces queda declarada como abierta. Es el segundo caso del proyecto tras `HU-17`.

---

#### `PR-02` — `HU-10` Bloqueo de un producto puntual

| | |
|---|---|
| Título del PR | `feat(restricciones): bloquear un producto del catálogo` |
| Rama | `feat/TT-97-bloqueo-de-producto` |
| Responsables | Pedro y Carlos |
| Historia | `HU-10` |
| Invariantes | ninguna |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-97` | Modelo de restricción por producto, distinto del de alérgeno | Pedro | ☐ |
| `TT-98` | Servicio de bloqueo y desbloqueo de un producto | Pedro | ☐ |
| `TT-99` | Selección de productos a bloquear en la interfaz del acudiente | Carlos | ☐ |

Los dos tipos de restricción se modelan **por separado**. Unificarlos en una tabla con un
campo «tipo» invita a implementar el alérgeno como lista de productos, que es lo que
`INV-5` prohíbe y lo que `PR-03` tiene que evitar.

---

#### `PR-03` — `HU-11` Bloqueo por alérgeno

| | |
|---|---|
| Título del PR | `feat(restricciones): bloquear un alérgeno sobre la condición` |
| Rama | `feat/TT-100-bloqueo-por-alergeno` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-11` |
| Invariantes | **`INV-5`** |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-100` | Modelo de restricción por alérgeno, sobre la condición y no sobre una lista | Pedro | ☐ |
| `TT-101` | Servicio de bloqueo y desbloqueo de un alérgeno | Pedro | ☐ |
| `TT-102` | Selección de alérgenos a bloquear en la interfaz del acudiente | Carlos | ☐ |
| `TT-103` | Caso de prueba: producto creado **después** del bloqueo queda cubierto | Alejandro | ☐ |

> 🔴 **El PR de mayor riesgo del sprint.** `INV-5` exige que el bloqueo se aplique sobre el
> alérgeno, de modo que cubra productos futuros. La comprobación es un cruce con la tabla
> `ProductoAlergeno` que ya existe. **Si alguien materializa la lista de productos
> bloqueados —porque consulta más rápido— `INV-5` se rompe y no se nota hasta que la
> cafetería añade un producto nuevo.**
>
> `TT-103` es la red: crea el producto **después** de la restricción. Revisad `TT-100` con
> esa prueba delante.

---

#### `PR-04` — `HU-12` Retiro de una restricción

| | |
|---|---|
| Título del PR | `feat(restricciones): retirar una restricción dejando asiento` |
| Rama | `feat/TT-104-retiro-de-restriccion` |
| Responsables | Pedro y Carlos |
| Historia | `HU-12` |
| Invariantes | `ALC-IN-19`: el retiro se asienta |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-104` | Servicio de retiro que deja asiento auditable | Pedro | ☐ |
| `TT-105` | Acción de retirar en la interfaz del acudiente | Carlos | ☐ |

El retiro se asienta porque es una acción sobre la seguridad alimentaria de un menor:
tiene que poder reconstruirse quién la hizo y cuándo.

---

### Aplicación y consulta — `PR-05` … `PR-07`

#### `PR-05` — Permisos de `HU-13`

| | |
|---|---|
| Título del PR | `feat(restricciones): impedir que la cafetería toque las restricciones` |
| Rama | `feat/TT-106-permisos-de-restricciones` |
| Responsables | Pedro y Alejandro |
| Historia | `HU-13` — **no la cierra**, la cierra `PR-06` |
| Invariantes | **`INV-4`** |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-106` | Selector de las restricciones vigentes de un estudiante | Pedro | ☐ |
| `TT-107` | Permisos: ni cajero, ni administración, ni institución escriben restricciones | Pedro | ☐ |
| `TT-108` | Caso de prueba: los tres roles no tienen escritura sobre restricciones | Alejandro | ☐ |

`INV-4` se sostiene **en la capa de datos**, con permisos por modelo (`DT-11`). Ocultar el
botón en la plantilla no es cumplirla, es aparentarlo: `TT-108` llama al servicio con cada
rol, no mira la pantalla.

---

#### `PR-06` — `HU-13` y **`HU-17`**

| | |
|---|---|
| Título del PR | `feat(pos): mostrar las restricciones vigentes en el panel de cobro` |
| Rama | `feat/TT-109-restricciones-al-cobrar` |
| Responsables | Carlos y Alejandro |
| Historias | `HU-13` **y `HU-17`** |
| Invariantes | `INV-4` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-109` | Bloque de restricciones vigentes en el panel de cobro | Carlos | ☐ |
| `TT-110` | Caso de prueba: `HU-17` completa — saldo, consumo del día y restricciones | Alejandro | ☐ |

> ⚠ **Salda la deuda del Sprint 2.** `HU-17` quedó abierta porque su tercer criterio exige
> mostrar las restricciones vigentes y no existían. Este PR añade ese bloque al panel que
> construyó `TT-75`. **Al integrarlo hay que marcar DOS historias** en
> `./backlog-historias-de-usuario.md`: `HU-13` y `HU-17`. Es el error más fácil de cometer
> en todo el sprint.

El cajero **ve** las restricciones y no dispone de ninguna acción para desactivarlas. Lo
segundo ya lo garantiza `PR-05` en la capa de datos.

---

#### `PR-07` — `HU-38` Consulta por los cuatro roles

| | |
|---|---|
| Título del PR | `feat(restricciones): permitir consultar las restricciones a los cuatro roles` |
| Rama | `feat/TT-111-consulta-de-restricciones` |
| Responsables | Pedro y Carlos |
| Historia | `HU-38` |
| Invariantes | `INV-4`, matriz `S11` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-111` | Consulta habilitada a los cuatro roles, sobre el selector de `TT-106` | Pedro | ☐ |
| `TT-112` | Consulta de restricciones en la interfaz administrativa | Carlos | ☐ |

`HU-38` y `HU-13` son las dos caras de la misma fila de `S11`: los cuatro **consultan**,
solo el acudiente **configura**.

---

### Rechazos en la venta — `PR-08` … `PR-09`

#### `PR-08` — `HU-18` Venta rechazada por alérgeno

| | |
|---|---|
| Título del PR | `feat(ventas): rechazar la venta de un producto con alérgeno bloqueado` |
| Rama | `feat/TT-113-rechazo-por-alergeno` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-18` |
| Invariantes | `INV-4`, `INV-5` · escenario crítico **`TST-1`** |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-113` | Validación del alérgeno **dentro** del bloqueo de la transacción | Pedro | ☐ |
| `TT-114` | Motivo de rechazo por alérgeno, distinguible en el punto de venta | Carlos | ☐ |
| `TT-115` | Caso de prueba `TST-1`: venta rechazada, sin vía para forzarla | Alejandro | ☐ |

**`TST-1` es el escenario que da sentido al proyecto**: un niño alérgico no puede comprar
lo que le hace daño. La validación va dentro del bloqueo que ya monta `registrar_venta`,
junto a las de saldo y existencias.

El cajero **no tiene** forma de forzar la venta: no es un aviso descartable.

---

#### `PR-09` — `HU-20` Venta rechazada por límite diario

| | |
|---|---|
| Título del PR | `feat(ventas): rechazar la venta cuando se agotó el cupo del día` |
| Rama | `feat/TT-116-rechazo-por-limite` |
| Responsables | Pedro, Carlos y Alejandro |
| Historias | `HU-20` **y `HU-09`** |
| Invariantes | escenario crítico **`TST-2`**, mitad pendiente |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-116` | Validación del límite diario contra el consumo del día, dentro del bloqueo | Pedro | ☐ |
| `TT-117` | Motivo de rechazo por límite, distinguible del de saldo | Carlos | ☐ |
| `TT-118` | Caso de prueba `TST-2`: rechazo por cupo aunque haya saldo | Alejandro | ☐ |

> ⚠ **Salda también `HU-09`.** `PR-01` dejó el cupo configurable por estudiante y
> escribible solo por su acudiente, pero el tercer criterio de la historia —«el límite se
> evalúa contra el consumo del día en cada venta»— es exactamente lo que construye
> `TT-116`. **Al integrarlo hay que marcar DOS historias** en
> `./backlog-historias-de-usuario.md`: `HU-20` y `HU-09`.

Completa `TST-2`, cuya otra mitad cerró `HU-19` en el Sprint 2.

El caso a probar es el contraintuitivo: **hay saldo de sobra y la venta se rechaza igual**.
Si el mensaje dice «saldo insuficiente», el cajero le da al estudiante una explicación falsa.

---

### Estado del estudiante — `PR-10` … `PR-13`

#### `PR-10` — `HU-47` Desactivación por la institución

| | |
|---|---|
| Título del PR | `feat(personas): desactivar a un estudiante desde el padrón` |
| Rama | `feat/TT-119-desactivacion-institucion` |
| Responsables | Pedro y Carlos |
| Historia | `HU-47` |
| Invariantes | `INVD-2` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-119` | Transición a `desactivado` desde el padrón de la institución | Pedro | ☐ |
| `TT-120` | Acción de desactivar en la ficha del padrón | Carlos | ☐ |

No hay modelo nuevo: `EstadoDelEstudiante` existe desde `HU-51` (Sprint 1). Hay una
transición nueva.

---

#### `PR-11` — `HU-48` Desactivación por el acudiente

| | |
|---|---|
| Título del PR | `feat(personas): permitir al acudiente desactivar a su estudiante` |
| Rama | `feat/TT-121-desactivacion-acudiente` |
| Responsables | Pedro y Carlos |
| Historia | `HU-48` |
| Invariantes | `INVD-2`, `INVD-3` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-121` | Transición a `desactivado` por el acudiente, **sin acción de reactivar** | Pedro | ☐ |
| `TT-122` | Acción de desactivar en la interfaz del acudiente | Carlos | ☐ |

Las dos vías cubren tiempos distintos (`DEC-5`): la institución bloquea de inmediato en
mitad de la jornada; el acudiente bloquea sin depender del horario de la secretaría.

---

#### `PR-12` — `HU-49` Reactivación exclusiva de la institución

| | |
|---|---|
| Título del PR | `feat(personas): reservar la reactivación a la institución` |
| Rama | `feat/TT-123-reactivacion-exclusiva` |
| Responsables | Pedro y Alejandro |
| Historia | `HU-49` |
| Invariantes | **`INVD-3`** |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-123` | Reactivación solo por la institución, con independencia de quién desactivó | Pedro | ☐ |
| `TT-124` | Caso de prueba: el acudiente que desactivó no puede reactivar | Alejandro | ☐ |

La asimetría tiene un motivo de seguridad: el desbloqueo pasa por una verificación
presencial, y eso impide que quien encontró la tarjeta consiga que se reactive.

---

#### `PR-13` — `HU-50` Venta rechazada por estudiante desactivado

| | |
|---|---|
| Título del PR | `feat(ventas): rechazar la venta a un estudiante desactivado` |
| Rama | `feat/TT-125-rechazo-por-desactivacion` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-50` |
| Invariantes | **`INVD-2`** |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-125` | Rechazo de venta y de retiro de pedido para desactivado o de baja | Pedro | ☐ |
| `TT-126` | Motivo de rechazo distinto de los de saldo, alérgeno y límite | Carlos | ☐ |
| `TT-127` | Caso de prueba: desactivado no compra pero **sí recibe recargas** | Alejandro | ☐ |

Al integrarse, la venta tiene **cuatro motivos de rechazo distintos**. Que se distingan no
es cosmética: el cajero tiene que poder decir qué pasa, y solo uno de los cuatro se
arregla recargando.

---

### Gestión — `PR-14`

#### `PR-14` — Gestión del sprint

| | |
|---|---|
| Título del PR | `docs(gestion): cerrar el Sprint 3` |
| Rama | `docs/TT-128-gestion-del-sprint-3` |
| Responsable | Naomi |
| Historia | ninguna — gestión |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-128` | Tablero Kanban del Sprint 3 | Naomi | ☐ |
| `TT-129` | Registro de riesgos del Sprint 3 | Naomi | ☐ |
| `TT-130` | Preparación de la Sprint Review y la Retrospective | Naomi | ☐ |

Va el último por número, no por fecha: las tres empiezan el primer día.

---

## [S5] Qué se puede solapar

| PR | Puede ir en paralelo con | Porque |
|---|---|---|
| `PR-10` … `PR-13` (estado, Pedro) | `PR-01` … `PR-04` (restricciones, Pedro) | `TT-119` no depende de nada del sprint; son dos frentes que solo se encuentran en `PR-13` |
| `PR-14` (gestión, Naomi) | cualquiera | `TT-128`–`TT-130` no dependen de nada |

**Cinco raíces** sin dependencia dentro del sprint: `TT-94`, `TT-119` y las tres de gestión.

Carlos no tiene raíces: su primera tarea, `TT-96`, necesita `TT-95`. En el arranque del
sprint tiene un hueco de un día o dos — buen momento para adelantar la corrección del
defecto de `HU-11` que señala el `ANEXO A` del sprint backlog.

**Regla al solapar:** ramifica siempre desde `main`, nunca desde la rama del otro.

---

## [S6] Advertencias sobre este plan

1. **`PR-09` cierra dos historias, y una de ellas es de `PR-01`.** `HU-20` y `HU-09`:
   `PR-01` dejó el cupo configurable pero su tercer criterio —evaluarlo contra el consumo
   del día en cada venta— es `TT-116`. Está anotado en `[S3.1]`, en el bloque de `PR-01` y
   en `[S4]` del backlog de historias.
2. **`PR-06` cierra dos historias.** `HU-13` y `HU-17`. Es la única vez en el proyecto que
   un PR salda una historia de un sprint anterior, y por eso es la marca más fácil de
   olvidar. Va anotada en `[S2]`, en `[S3.1]` y en el propio PR.
3. **`PR-03` es el de mayor riesgo.** `INV-5` se rompe con una decisión de modelado que
   parece una optimización. Revisadlo con `TT-103` delante.
4. **Tres PR seguidos tocan el mismo servicio transaccional.** `PR-08`, `PR-09` y `PR-13`
   añaden validaciones dentro del bloqueo que construyó `TT-80` en el Sprint 2. Cada una es
   sencilla; el riesgo es el acumulado. Comprobad que el orden bloqueo → validación →
   escritura sigue intacto **después del tercero**, no solo después de cada uno.
5. **Este sprint cierra `TST-1` y `TST-2`.** Dos de los cuatro escenarios críticos que
   `ENT-05` exige demostrar. `TST-3` cerró en el Sprint 2 y `TST-4` es del Sprint 4: al
   acabar el 4, el plan de pruebas está completo.
6. **Si el sprint desborda**, los candidatos a mover son `PR-04` (`HU-12`, el único
   `Should`) y `PR-07` (`HU-38`, del que no depende ninguna historia). Quedan 12 PR y 33
   tareas. **No se pueden mover** `PR-08` ni `PR-09`.
7. **Este plan no reordena nada.** Si alguien propone mover una tarea de PR, hay que
   comprobar el `ANEXO C` del sprint backlog antes.
