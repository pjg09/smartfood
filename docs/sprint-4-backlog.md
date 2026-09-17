# SmartFood — Sprint Backlog del Sprint 4

## [S0] Bloque de control del documento

### [S0.1] Metadatos

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-SPRINT4 |
| titulo | Sprint Backlog del Sprint 4 — Inventario trazable y pedidos anticipados |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./backlog-historias-de-usuario.md` (`[S5]`, Sprint 4); `./decisiones-de-alcance.md` (`DEC-15`); `./decisiones-tecnicas.md` (`DT-31`); `./despliegue.md`; `./smartfood.md` (`S11`, `S12`); `corpus:guia-de-scrum-2020.md` (`ART-2`, `COM-2`, `COM-3`) |
| tipo_documento | Sprint Backlog (`ART-2` de la Guía de Scrum) |
| sprint | 4 de 5 |
| semanas | 12 – 13 |
| hito | **Avance 2 · semana 14** (`EVA-4`, 20 % de la nota), al cerrar este sprint |
| historias | 5 (`HU-28`, `HU-29`, `HU-23`, `HU-24`, `HU-25`) |
| tareas | 18 (`TT-137` … `TT-154`) |
| stack | Django + PostgreSQL + HTMX (`DT-2`, `DT-3` de `./decisiones-tecnicas.md`) |
| idioma | es-CO |
| version | 1.0 |

### [S0.2] Instrucciones de lectura para el agente

1. Documento **derivado**: no reexpresa ningún original y no lleva texto verbatim.
2. Es el **Sprint Backlog** en el sentido de `ART-2` de la Guía de Scrum: el Objetivo del Sprint, las historias seleccionadas y **el plan para entregarlas**.
3. **Ninguna tarea introduce alcance nuevo.** Cada una se deriva de una historia de `./backlog-historias-de-usuario.md`, o es habilitación declarada como tal.
4. **La serie `TT-` continúa**: los sprints anteriores terminaron en `TT-56`, `TT-93` y `TT-136`. No se reinicia.
5. Los responsables salen de la matriz `[S12]` de `./smartfood.md`. Es la previsión de Sprint Planning (`EVT-1`), no una asignación rígida.
6. **La columna `Estado` marca el avance.** `☑` es finalizada —integrada en `main`—, `☐` es pendiente. El estado se lleva **también** en `./plan-de-pull-requests-sprint-4.md`; si hay discrepancia, manda ese documento.
7. Los identificadores `[TT-nn]` son estables y citables.

### [S0.3] Mapa de secciones

| ID | Sección | Contenido |
|---|---|---|
| S1 | Objetivo del Sprint | `COM-2` |
| S2 | Definición de Terminado | Puntero a `./definicion-de-terminado.md` (`COM-3`) |
| S3 | Tareas de habilitación | `TT-137`, y por qué existe |
| S4 | Tareas por historia | `TT-138` … `TT-151` |
| S5 | Tareas de gestión del Sprint | `TT-152` … `TT-154` |
| S6 | Reparto por responsable | Carga de cada integrante |
| ANEXO A | Riesgos del sprint, y qué hacer con la holgura | Es el sprint más ligero de los cinco |
| ANEXO B | Nota de procedencia | Cómo se derivó |
| ANEXO C | Verificación del orden de construcción | Grafo de dependencias |

---

## [S1] Objetivo del Sprint `[COM-2]`

> Que las existencias de cualquier producto puedan explicarse movimiento a movimiento —incluida la merma, que siempre lleva motivo— y que un acudiente pueda reservar y pagar por adelantado lo que su hijo recogerá en la cafetería.

Cierra `TST-4`, **el último de los cuatro escenarios críticos** que `ENT-05` exige. Con `TST-1` y `TST-2` del Sprint 3 y `TST-3` del Sprint 2, al acabar este sprint el plan de pruebas está completo.

Es además el sprint que desemboca en el **Avance 2** de la semana 14, que vale el 20 % de la nota.

---

## [S2] Definición de Terminado `[COM-3]`

La misma de todo el semestre: `./definicion-de-terminado.md`. No se relaja.

> ✅ **`DoD-4` volvió a estar vigente el 2026-09-17**, con otra redacción: pide demostrar ejecutándolo, con la salida real del comando. Lo restableció `TT-137`, retirando el entorno desplegado en vez de restaurarlo (`DEC-15`).

---

## [S3] Tareas de habilitación

| ID | Tarea | Responsable | Habilita | Estado |
|---|---|---|---|---|
| `TT-137` | Restaurar el entorno desplegado y levantar la suspensión de `DoD-4` (`ENT-01`) | Pedro | Todo lo cerrado desde el 2026-08-30, y el Avance 2 | ☑ |

> **Cerrada el 2026-09-17, con la decisión contraria a la que preveía.** La tarea era
> restaurar el entorno; lo que se hizo fue **retirarlo**, y `TT-137` se da por terminada
> porque el asunto que abría quedó resuelto. La decisión es `DEC-15` de
> `./decisiones-de-alcance.md`, con su consecuencia técnica en `DT-31` de
> `./decisiones-tecnicas.md`.
>
> **La planeación describió mal el obstáculo, y conviene que quede dicho.** Esta caja
> presentaba el impedimento como «una restricción de ventana horaria, **no de dinero**».
> No lo era: `[S1]` de `./despliegue.md` registraba desde agosto que el plan gratuito no
> sostiene el entorno por dos fallos —la base gestionada se duerme y el proveedor prohíbe
> desactivarlo, y `/app/staticfiles/` no existe en ejecución—, y que la única salida
> técnica era pagar. La ventana horaria era la tercera restricción, no la primera. El dato
> estaba registrado y la planeación no lo leyó.
>
> Los tres hechos que hacían entrar la tarea siguen siendo ciertos, y los tres se
> resolvieron de una vez:
>
> 1. **`ENT-01` llevaba sin cumplirse desde agosto.** `DEC-15` le retira la condición de
>    estar desplegado; lo que queda del entregable —los flujos de extremo a extremo con
>    datos ficticios— sí se cumple, y se demuestra en local.
> 2. **`DoD-4` estaba suspendido.** Vuelve a estar vigente, pidiendo la salida real del
>    comando. Lo cerrado en los Sprints 2 y 3 ya se declaraba así, de modo que **no hay
>    nada que revisar hacia atrás**.
> 3. **El Avance 2 es la semana 14.** Se demuestra desde un portátil del equipo. Es la
>    decisión que el `ANEXO A` pedía tomar «con tiempo, no la víspera»: se toma tres
>    semanas antes.
>
> **La holgura del sprint no se gastó aquí.** Esta tarea costó una decisión y la
> documentación que la registra, no las dos semanas que preveía restaurar un entorno. El
> `ANEXO A` proponía tres usos para el margen; con el primero resuelto así, quedan los
> otros dos.

---

## [S4] Tareas por historia

**El orden en que están escritas es el orden en que se pueden desarrollar.** El `ANEXO C` lo verifica.

> **Buena parte de `HU-28` y `HU-29` ya está construida.** El Sprint 2 levantó el libro de movimientos con `TT-67`, y con él vinieron el tipo `MERMA`, la `CheckConstraint` de motivo obligatorio, el primitivo `asentar` y los selectores `existencias_de` e `historial_de`. Lo que falta de estas dos historias es **el servicio de cara al usuario, la pantalla y la prueba**, no el modelo. Las tareas de abajo reflejan eso y no vuelven a pedir lo que ya existe.

### `[HU-28]` Registro de merma con motivo obligatorio

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-138` | Servicio de registro de merma, sobre el primitivo `asentar` que ya existe | Pedro | ☐ |
| `TT-139` | Registro de merma desde la interfaz administrativa | Carlos | ☐ |
| `TT-140` | Caso de prueba: una merma sin motivo la rechaza **la base de datos**, no el formulario (`INV-8`) | Alejandro | ☐ |

`INV-8` ya está sostenida por una `CheckConstraint` desde `TT-67`. `TT-140` lo comprueba saltándose el formulario: si la prueba pasa llamando al ORM directamente, la invariante está donde debe.

El criterio de la historia dice «aplica a **toda** disminución manual, no solo a la merma». Hoy el único tipo manual que resta es la merma; si se añadiera otro, hereda la misma restricción.

### `[HU-29]` Existencias explicables desde el historial

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-141` | Vista del historial de movimientos de un producto, con su tipo y su motivo | Carlos | ☐ |
| `TT-142` | Caso de prueba `TST-4`: las existencias coinciden exactamente con la suma del historial tras ingreso, venta y merma | Alejandro | ☐ |

**No hay tarea de backend.** `existencias_de` e `historial_de` existen desde `TT-67`, y `INV-3` se cumple por construcción porque no hay columna de existencias (`DT-5`). Lo que falta es que un humano pueda **ver** esa explicación, que es lo que la historia pide, y la prueba que lo ejercita.

`TST-4` es el último escenario crítico de `ENT-05`. El fichero `inventario/tests_ingreso.py` ya lo anuncia: «`TST-4` la ejercitará en el Sprint 4 con la merma».

### `[HU-23]` Reserva y pago anticipado

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-143` | Modelo de pedido anticipado, con su estado y su vínculo a la venta | Pedro | ☐ |
| `TT-144` | Servicio de reserva que cobra **en el momento de reservar**, dentro de la transacción (`DT-6`) | Pedro | ☐ |
| `TT-145` | Pantalla de reserva en la interfaz del acudiente | Carlos | ☐ |
| `TT-146` | Caso de prueba: la reserva descuenta saldo al reservarse, **no** al entregarse | Alejandro | ☐ |

Es la única historia del sprint que construye algo desde cero: no hay nada de pedidos anticipados en el código.

**El cobro ocurre al reservar** (`ALC-IN-10`, `FUN-5`), y por tanto pasa por la misma transacción con bloqueo que `registrar_venta`: se aplican las mismas reglas de saldo, límite diario, restricciones y estado del estudiante que construyeron los Sprints 2 y 3. Una reserva **es** una venta anticipada, no un apartado.

Pago simulado, como todo lo demás (`ALC-OUT-02`).

### `[HU-24]` Consulta de reservas pendientes

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-147` | Selector de reservas pendientes | Pedro | ☐ |
| `TT-148` | Consulta de reservas pendientes desde la cafetería | Carlos | ☐ |

### `[HU-25]` Registro de la entrega del pedido

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-149` | Servicio de entrega que **no vuelve a descontar saldo** ni admite entrega doble | Pedro | ☐ |
| `TT-150` | Registro de la entrega en el punto de venta | Carlos | ☐ |
| `TT-151` | Caso de prueba: entregar no descuenta saldo, y un pedido entregado no se entrega dos veces | Alejandro | ☐ |

> **El error a evitar es cobrar dos veces.** El pedido ya se pagó al reservarse; la entrega solo cambia su estado y descuenta existencias. Si la entrega reutiliza `registrar_venta` sin más, el estudiante paga dos veces y `INV-2` sigue cuadrando —el historial es consistente— pero el sistema está mal. La prueba de `TT-151` es lo que lo detecta.

---

## [S5] Tareas de gestión del Sprint

| ID | Tarea | Responsable | Origen | Estado |
|---|---|---|---|---|
| `TT-152` | Tablero Kanban del Sprint 4 con sus tareas y estado | Naomi | `CUR-3` | ☐ |
| `TT-153` | Registro de riesgos del Sprint 4 y seguimiento en las Daily | Naomi | `ENT-04` | ☐ |
| `TT-154` | Preparación de la Sprint Review, la Retrospective y **el Avance 2** (`EVA-4`) | Naomi | `EVT-3`, `EVT-4` | ☐ |

`TT-154` pesa: el Avance 2 vale el 20 % y es la segunda vez que el proyecto se enseña fuera del equipo.

---

## [S6] Reparto por responsable

| Integrante | Rol `[S12]` | Tareas | Cuáles |
|---|---|---|---|
| **Pedro** | Desarrollador backend | **7** | `TT-137`, `TT-138`, `TT-143`, `TT-144`, `TT-147`, `TT-149` |
| **Carlos** | Desarrollador frontend | **5** | `TT-139`, `TT-141`, `TT-145`, `TT-148`, `TT-150` |
| **Alejandro** | Analista de datos y UX | **4** | `TT-140`, `TT-142`, `TT-146`, `TT-151` |
| **Naomi** | Líder de proyecto | **3** | `TT-152`, `TT-153`, `TT-154` |

**Total: 18 tareas.** Menos de la mitad que en los Sprints 2 y 3, que tuvieron 37 cada uno.

---

## [ANEXO A] Riesgos del sprint, y qué hacer con la holgura

**1. Este sprint sobra tiempo, y eso es un riesgo en sí mismo.** 18 tareas en dos semanas frente a las 37 de los dos anteriores. El `ANEXO A` del Sprint 2 ya avisó de que el margen era deliberado, para «absorber el retraso acumulado antes del Avance 2». **No hay retraso que absorber**: los tres sprints cerraron completos. La holgura existe de verdad y hay que decidir en qué se gasta, porque si no se decide se gasta sola.

Tres usos, en el orden en que los recomendaría:

| Opción | Por qué |
|---|---|
| ~~**Restaurar el entorno desplegado** (`TT-137`)~~ | **Ya no consume holgura.** Se resolvió retirándolo, no restaurándolo: `DEC-15`. Quedan los otros dos usos |
| **Adelantar trabajo del Sprint 5** | Son 10 historias de reportes y el plan de pruebas; el Sprint 5 es el más cargado de los dos que quedan |
| **Reforzar lo que se enseña en el Avance 2** | Pulir los flujos que se van a demostrar antes que añadir funcionalidad nueva |

**2. La entrega de un pedido puede cobrar dos veces.** Ver el aviso de `HU-25`. Es el único error del sprint que deja la base de datos consistente y el comportamiento mal: `INV-2` cuadra porque el historial es correcto, pero el estudiante pagó dos veces.

**3. La reserva es una venta y hay que tratarla como tal.** `TT-144` debe pasar por la misma transacción con bloqueo que `registrar_venta`. Si se implementa como un flujo aparte, las cuatro reglas de rechazo que construyeron los Sprints 2 y 3 —saldo, límite, alérgeno, desactivación— no se aplicarían a las reservas, y habría una puerta trasera para saltarse el control parental entero.

**4. Las tres historias de pedidos anticipados son `Should`.** `HU-23`, `HU-24` y `HU-25` son las únicas del sprint que no son `Must`. Si algo se cae, se caen ellas; `HU-28` y `HU-29` no pueden, porque `HU-29` cierra `TST-4`.

---

## [ANEXO B] Nota de procedencia

Documento producido por el equipo el 2026-09-17, al cerrar el Sprint 3.

Las 18 tareas se derivaron de las 5 historias del Sprint 4 de `[S5]` de `./backlog-historias-de-usuario.md`, **contrastadas contra el código ya construido**: el Sprint 2 dejó hechos el libro de movimientos, el tipo `MERMA`, la restricción de motivo obligatorio y los selectores de existencias e historial, así que las tareas de `HU-28` y `HU-29` piden solo lo que falta. La de habilitación y las tres de gestión no provienen de ninguna historia y se declaran como tales.

La serie `TT-` continúa: este sprint va de `TT-137` a `TT-154`.

**Ninguna tarea introduce alcance.** No hay tarea que implemente algo que no esté en una historia, salvo `TT-137`, que es habilitación declarada y cuya incorporación el equipo debe confirmar en el Sprint Planning.

---

## [ANEXO C] Verificación del orden de construcción

| Comprobación | Resultado |
|---|---|
| Tareas colocadas | 18 de 18, ninguna repetida |
| Tareas situadas antes de algo que las bloquea | **0** |

**Se desarrolla de arriba abajo, sin excepciones.**

### Dependencias dentro del sprint

| Tarea | Necesita | De |
|---|---|---|
| `TT-139` Registro de merma en la interfaz | `TT-138` Servicio de merma | `HU-28` |
| `TT-140` Prueba de motivo obligatorio | `TT-138` Servicio de merma | `HU-28` |
| `TT-142` Prueba `TST-4` | `TT-138` Servicio de merma | `HU-28` |
| `TT-144` Servicio de reserva | `TT-143` Modelo de pedido | `HU-23` |
| `TT-145`, `TT-146` Pantalla y prueba de reserva | `TT-144` Servicio de reserva | `HU-23` |
| `TT-147` Selector de pendientes | `TT-143` Modelo de pedido | `HU-23` |
| `TT-148` Consulta en la cafetería | `TT-147` Selector | `HU-24` |
| `TT-149` Servicio de entrega | `TT-144` Servicio de reserva | `HU-23` |
| `TT-150`, `TT-151` Registro y prueba de entrega | `TT-149` Servicio de entrega | `HU-25` |

`TT-142` depende de `TT-138` aunque pertenezcan a historias distintas: `TST-4` exige ejercitar el historial **con una merma**, y la merma la registra `HU-28`.

### Dependencias con sprints anteriores

| Necesita | De |
|---|---|
| `TT-138` Servicio de merma | `TT-67` Libro de inventario con `MERMA` y `CheckConstraint` (S2) |
| `TT-141` Vista del historial | `TT-67` Selector `historial_de` (S2) |
| `TT-144` Cobro al reservar | `TT-80` Transacción de venta (S2); reglas de rechazo de los Sprints 2 y 3 |
| `TT-149` Entrega en el punto de venta | `TT-81` Carrito y confirmación (S2) |

### Trabajo en paralelo

**Siete raíces** sin dependencia dentro del sprint: cuatro técnicas —`TT-137` (entorno desplegado), `TT-138` (servicio de merma), `TT-141` (vista del historial) y `TT-143` (modelo de pedido)— más las tres de gestión.

`TT-138` y `TT-143` son dos frentes de backend que no se tocan: el inventario y los pedidos solo se encuentran en la entrega, al final. Carlos tiene trabajo desde que `TT-138` esté.
