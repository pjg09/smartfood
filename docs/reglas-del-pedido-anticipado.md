# SmartFood — Las reglas del pedido anticipado

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-REGLAS-PEDIDO |
| titulo | Qué pasa al reservar, al consultar y al entregar, y por qué |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./smartfood.md` (`ALC-IN-10`, `FUN-5`, `ALC-OUT-01`); `./decisiones-de-alcance.md` (`INVD-2`, `ANEXO B`); `./decisiones-tecnicas.md` (`DT-32` … `DT-35`, `DT-6`, `DT-8`, `DT-15`, `DT-24`); `./backlog-historias-de-usuario.md` (`HU-23`, `HU-24`, `HU-25`); `./reglas-de-la-venta.md`; `ventas/services.py` |
| tipo_documento | Documento operativo. **No es un artefacto de Scrum ni un entregable** |
| creado | 2026-09-19, al cerrar el Sprint 4 |
| idioma | es-CO |
| version | 1.0 |

### [S0.1] Qué responde este documento

**Qué ocurre exactamente en cada uno de los tres momentos de un pedido —reservar, consultar,
entregar—, qué se mueve en cada uno y qué no.**

Es el gemelo de `./reglas-de-la-venta.md` para el otro flujo transaccional del sistema. Existe
por el mismo motivo: el pedido anticipado acumula **siete reglas que ninguna historia
menciona**, decididas en cuatro registros distintos a lo largo de un sprint, y hasta ahora
repartidas entre nueve documentos. La más fuerte de todas —que un pedido no se entrega dos
veces, y que lo impide la base de datos— **no estaba escrita en ninguno**.

> **El código manda.** Este documento describe `ventas/services.py` y `ventas/selectors.py`;
> si algún día discrepan, el equivocado es este. Lo que aquí se fija son **las razones**, que
> el código no puede demostrar por sí solo.

---

## [S1] Los tres momentos, y qué mueve cada uno

| Momento | Quién | Saldo | Inventario | Estado |
|---|---|---|---|---|
| **Reservar** (`HU-23`) | El acudiente, desde `INT-1` | **Baja** | no se toca | nace `pendiente` |
| **Consultar** (`HU-24`) | Cajero y administración | — | — | — |
| **Entregar** (`HU-25`) | El cajero, en `INT-2` | **no se toca** | **Baja** | pasa a `entregado` |

**Las dos casillas en negrita son la historia entera.** Se cobra al reservar y se descuenta
al entregar, y ninguna de las dos cosas ocurre dos veces. Todo lo demás de este documento
explica cómo se sostiene eso.

**Una reserva es una `Venta`** con `origen = reserva` y sin cajero (`DT-32`). No hay otra
tabla que guarde lo que se pidió ni lo que costó: eso vive en la venta y sus `LineaVenta`,
como en cualquier otra venta. `PedidoAnticipado` añade **una sola cosa**: el estado de la
entrega.

---

## [S2] Reservar

### [S2.1] Valida por la misma función que el cobro, y eso no es negociable

`reservar` y `registrar_venta` llaman las dos a `_bloquear_y_validar`. Las **seis
comprobaciones** de `[S2]` de `./reglas-de-la-venta.md` —estudiante que no opera, alérgeno
bloqueado, producto bloqueado, existencias, cupo del día y saldo— se aplican por tanto a la
reserva sin que exista una segunda copia.

> **`HU-23` no menciona ninguna de las seis.** Sus tres criterios hablan del estudiante, del
> pago y de dónde se gestiona. Con un flujo propio, un acudiente no podría comprarle a su hijo
> en la caja algo con un alérgeno bloqueado **pero sí reservárselo la noche anterior**, y el
> control parental entero tendría una puerta trasera.
>
> Era el riesgo marcado en rojo del Sprint 4. Lo sostienen `ventas/tests_reserva.py`, que
> ejercita las seis sobre la reserva cobrando de verdad, y **una prueba estructural que exige
> que ninguno de los dos servicios las tenga escritas aparte**.

### [S2.2] Lo único que cambia: qué cuenta como disponible

| | Mira |
|---|---|
| La venta del mostrador | `existencias_por_producto` — las existencias reales |
| **La reserva** | **`existencias_sin_reservar`** — menos lo apartado por pedidos pendientes |

Es consecuencia de `DT-33`: como la reserva no descuenta inventario, las unidades siguen en el
libro. Sin restar lo apartado, **dos reservas del último paquete pasarían las dos** —las
existencias dicen «queda 1» las dos veces— y quien reservó segundo habría pagado por algo que
no va a recibir.

**`INV-3` no se toca**: no hay columna ni caché. Las existencias siguen siendo la suma del
historial, y esto es otra cifra que se lee al lado.

### [S2.3] El cobro va aquí, y solo aquí

El movimiento de billetera se asienta al reservar, por el único punto de asiento del libro
(`DT-24`). Es el segundo criterio de `HU-23` y lo que distingue una reserva de un apartado: un
apartado no cobra hasta que se recoge.

**El medio de pago no se pregunta**: hay estudiante, luego sale de su billetera (`HU-54`,
`DEC-1`). Una reserva en efectivo sería alguien poniendo billetes en una aplicación, que es lo
que `ALC-OUT-01` deja fuera.

**El precio se congela** (`DT-8`). Entre reservar y entregar puede pasar una noche, y lo que
se cobró no lo reescribe una edición del catálogo de mañana.

---

## [S3] Consultar

`reservas_pendientes` devuelve lo pagado y sin recoger, **del más antiguo al más reciente**.

> **Al revés que todos los historiales del proyecto.** La billetera, el inventario y las
> restricciones se leen empezando por lo último. Esto **no es un historial: es una cola de
> trabajo**, y lo que el personal necesita saber es qué lleva más tiempo esperando.

**La consultan los dos roles de la cafetería**, `USR-3` y `USR-4`, porque `FUN-5` separa a
quien prepara de quien entrega. No comparten interfaz —el cajero no entra al admin y la
administración recibe `403` en el punto de venta—, y por eso la pantalla es una sola y vive
fuera del admin: es la segunda excepción declarada a `INT-3` (`DT-34`).

**No filtra por día y no esconde nada:**

- Una reserva de anteayer **sigue pendiente**. Ninguna historia dice hasta cuándo vale una, y
  el sistema no sabe anularlas. Esconderla la dejaría pagada y olvidada.
- El pedido de un estudiante que **no puede retirar** (`INVD-2`) también sigue, y se **marca**.
  Está pagado y sin anular: quitarlo de la lista lo volvería invisible, y hay dinero de por
  medio. Qué hacer con él es un punto abierto del `ANEXO B` de `./decisiones-de-alcance.md`.

---

## [S4] Entregar

### [S4.1] El error a evitar es cobrar dos veces

`entregar` hace **exactamente dos cosas**: mueve el libro de inventario y cambia el estado. Ni
una más — y esa ausencia es el segundo criterio de `HU-25`.

> **Es el único fallo del sprint que ninguna invariante detecta.** Si la entrega reutilizara
> `registrar_venta`, el estudiante pagaría dos veces **y el sistema seguiría cuadrando**: el
> historial sería consistente, `INV-2` se cumpliría y las dos ventas existirían de verdad. No
> hay restricción de base que lo note.
>
> Lo único que lo nota es `ventas/tests_entrega.py`, comparando el saldo antes y después.
> **Con el cobro doble introducido a propósito, caen cinco pruebas.**

### [S4.2] No se entrega dos veces, y lo sostienen tres capas

| Capa | Qué aporta |
|---|---|
| `select_for_update(of=("self",))` sobre el pedido | Dos cajas no pueden leerlo las dos «pendiente» |
| `if not esta_pendiente` | El mensaje que el cajero lee |
| **`UniqueConstraint(venta, producto)`** para salidas por venta | La garantía, también para el camino que alguien escriba mañana |

Quitando el `if`, la entrega doble **sigue fallando** — con `IntegrityError`. Es `DT-15`
aplicado: la invariante que la base puede imponer, la impone la base.

> **`of=("self",)` no es cosmético.** `venta.estudiante` es opcional (`DEC-1`), así que
> `select_related` lo trae con un LEFT JOIN y PostgreSQL rechaza la consulta entera: «FOR
> UPDATE cannot be applied to the nullable side of an outer join».

### [S4.3] La entrega no se rechaza por falta de existencias

`DT-35`. **El compromiso ya se adquirió y se cobró.** Rechazarla dejaría al estudiante sin lo
suyo **y** con el dinero pagado, y el sistema no sabe devolver (`ALC-OUT-01`): el rechazo no
tendría salida. Un descuadre de inventario sí la tiene.

Si el libro queda en negativo, esa cifra **es información verdadera**: dice que salió
mercancía que el inventario no tenía registrada, que es el descuadre que `HU-29` existe para
auditar. La pantalla del historial lo enseña con la venta que lo originó.

### [S4.4] Lo que sí la rechaza

**Un estudiante desactivado o de baja no retira** (`INVD-2`). La regla no se reimplementa:
`comprobar_que_puede_operar` es la puerta única y la entrega la llama igual que el cobro.

---

## [S5] Las siete reglas que ninguna historia dice

Resumidas, porque es lo que hay que saber antes de tocar este flujo:

| | Regla | Dónde vive |
|---|---|---|
| 1 | La reserva valida por la misma función que el cobro | `_bloquear_y_validar` |
| 2 | La reserva mira lo disponible **sin** lo apartado | `existencias_sin_reservar` |
| 3 | Se cobra al reservar y **solo** al reservar | `reservar`, `DT-33` |
| 4 | Se descuenta inventario al entregar y **solo** al entregar | `entregar`, `DT-33` |
| 5 | La entrega **nunca** se rechaza por existencias | `DT-35` |
| 6 | Un pedido no se entrega dos veces — tres capas | `DT-15`, `[S4.2]` |
| 7 | La cola marca lo que no tiene salida, no lo esconde | `[S3]` |

---

## [S6] Lo que este flujo deja abierto

Tres decisiones de alcance, no defectos. Ninguna historia las pide y el sistema no miente
sobre ellas.

| Punto | Dónde está registrado |
|---|---|
| Qué hacer con un pedido pagado de quien no puede retirar | `ANEXO B` de `./decisiones-de-alcance.md` |
| Si las reservas caducan | `reservas_pendientes`, en su docstring |
| Que la caja **y la merma** pueden disponer de lo apartado | `[S7]` de `./reglas-de-la-venta.md` |

> **El tercero tiene dos salidas conocidas** y conviene no perderlas: restar lo reservado
> también en la caja —sería la séptima comprobación, y `[S6]` de `./reglas-de-la-venta.md`
> existe para que ninguna se añada sin que una historia la pida— o descontar el inventario al
> reservar, que es la alternativa que `DT-33` descartó y que **quita** comprobaciones en vez
> de añadirlas.

---

## [ANEXO A] De dónde salió cada regla

| Regla | Tarea | PR | Registro |
|---|---|---|---|
| La reserva como `Venta` con otro origen | `TT-143` | `PR-04` | `DT-32` |
| Cobra al reservar, inventario al entregar | `TT-144` | `PR-04` | `DT-33` |
| Valida por la función compartida | `TT-144` | `PR-04` | — |
| Pantalla compartida fuera del admin | `TT-148` | `PR-05` | `DT-34` |
| La entrega no se rechaza por existencias | `TT-149` | `PR-06` | `DT-35` |
| No se entrega dos veces, en la base | `TT-149` | `PR-06` | — |
| La cola marca lo que no tiene salida | `TT-148` | `PR-07` | — |

Las dos filas sin registro propio son consecuencia directa de `DT-15` —la regla vive en un
solo sitio; la invariante la impone la base— y no necesitaban una decisión nueva.
