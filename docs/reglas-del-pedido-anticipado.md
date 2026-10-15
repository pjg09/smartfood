# SmartFood — Las reglas del pedido anticipado

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-REGLAS-PEDIDO |
| titulo | Qué pasa al reservar, al consultar, al entregar y al cancelar, y por qué |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./smartfood.md` (`ALC-IN-10`, `FUN-5`, `ALC-OUT-01`); `./decisiones-de-alcance.md` (`INVD-2`, `INVD-7`, `DEC-24`); `./decisiones-tecnicas.md` (`DT-32` … `DT-35`, `DT-47`, `DT-48`, `DT-6`, `DT-8`, `DT-15`, `DT-24`); `./backlog-historias-de-usuario.md` (`HU-23` … `HU-25`, `HU-65` … `HU-67`); `./reglas-de-la-venta.md`; `ventas/services.py` |
| tipo_documento | Documento operativo. **No es un artefacto de Scrum ni un entregable** |
| creado | 2026-09-19, al cerrar el Sprint 4; la reserva como encargo y la cancelación, el 2026-10-13 (`DEC-24`) |
| idioma | es-CO |
| version | 2.0 |

### [S0.1] Qué responde este documento

**Qué ocurre exactamente en cada uno de los cuatro momentos de un pedido —reservar, consultar,
entregar, cancelar—, qué se mueve en cada uno y qué no.**

Es el gemelo de `./reglas-de-la-venta.md` para el otro flujo transaccional del sistema. Existe
por el mismo motivo: el pedido anticipado acumula **doce reglas que ninguna historia
menciona**, decididas en seis registros distintos. Las dos más fuertes —que un pedido no se
entrega dos veces y que no se devuelve dos veces— las impide la base de datos, no un `if`.

> **El código manda.** Este documento describe `ventas/services.py` y `ventas/selectors.py`;
> si algún día discrepan, el equivocado es este. Lo que aquí se fija son **las razones**, que
> el código no puede demostrar por sí solo.

---

## [S1] Los cuatro momentos, y qué mueve cada uno

| Momento | Quién | Saldo | Inventario | Estado |
|---|---|---|---|---|
| **Reservar** (`HU-23`) | El acudiente, desde `INT-1` | **Baja** | no se mira ni se toca | nace `pendiente` |
| **Consultar** (`HU-24`, `HU-65`) | La cafetería, la cola; el acudiente, sus pedidos | — | — | — |
| **Entregar** (`HU-25`) | El cajero, en `INT-2` | **no se toca** | **Baja** | pasa a `entregado` |
| **Cancelar** (`HU-66`, `HU-67`) | El acudiente, el cajero o la administración | **Sube** lo cobrado | no se toca | pasa a `cancelado` |

**Las casillas en negrita son la historia entera.** Se cobra al reservar, se descuenta al
entregar y se devuelve al cancelar, y ninguna de las tres cosas ocurre dos veces. **Un pedido
sale de `pendiente` una sola vez**: o se entrega o se cancela. Todo lo demás de este documento
explica cómo se sostiene eso.

**Una reserva es una `Venta`** con `origen = reserva` y sin cajero (`DT-32`). No hay otra
tabla que guarde lo que se pidió ni lo que costó: eso vive en la venta y sus `LineaVenta`,
como en cualquier otra venta. `PedidoAnticipado` añade **una sola cosa**: en qué acabó —la
entrega o la cancelación—, con quién, cuándo y, si se canceló, por qué.

---

## [S2] Reservar

### [S2.1] Valida por la misma función que el cobro, y eso no es negociable

`reservar` y `registrar_venta` llaman las dos a `_bloquear_y_validar`. **Cinco de las seis
comprobaciones** de `[S2]` de `./reglas-de-la-venta.md` —estudiante que no opera, alérgeno
bloqueado, producto bloqueado, cupo del día y saldo— se aplican por tanto a la reserva sin que
exista una segunda copia. La sexta, las existencias, es la que no se le aplica (`[S2.2]`).

> **`HU-23` no menciona ninguna de las seis.** Sus tres criterios hablan del estudiante, del
> pago y de dónde se gestiona. Con un flujo propio, un acudiente no podría comprarle a su hijo
> en la caja algo con un alérgeno bloqueado **pero sí reservárselo la noche anterior**, y el
> control parental entero tendría una puerta trasera.
>
> Era el riesgo marcado en rojo del Sprint 4. Lo sostienen `ventas/tests_reserva.py`, que
> ejercita las cinco sobre la reserva cobrando de verdad, y **una prueba estructural que exige
> que ninguno de los dos servicios las tenga escritas aparte**.

### [S2.2] Lo único que cambia: la reserva no mira la vitrina

| | Existencias |
|---|---|
| La venta del mostrador | `existencias_por_producto` — vende lo que hay |
| **La reserva** | **No las mira** — es un encargo |

`DEC-24`, `DT-47`. **La reserva es un encargo, no un apartado**: lo que el acudiente reserva
para mañana no tiene por qué estar hoy en la vitrina, y la cafetería lo prepara a partir de la
cola (`[S3]`). La pantalla no enseña existencias ni limita el campo de cantidad.

Es un argumento de `_bloquear_y_validar` **sin valor por defecto** —`existencias_de_los`—, y
la reserva pasa `None`: quien llama tiene que decir qué existencias mira, en vez de heredar sin
saberlo la respuesta de otro. **La caja sigue mirándolas**, y una prueba lo fija como
contraprueba: si la función dejara de mirarlas para todos, caería.

Lo que no se pueda preparar **se cancela** (`[S5]`), y el importe vuelve a la billetera.

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

**La cafetería, la cola.** `pedidos_de_la_cafeteria` con el filtro `por-recoger` devuelve lo
pagado y sin recoger, **del más antiguo al más reciente**. La administración ve además lo
entregado y lo cancelado, del más reciente al más antiguo (`HU-68`, `DT-49`): eso es un reporte
de ventas, y `[S11]` no se lo da al cajero. Encima de la lista, **lo que falta por entregar**,
sumado producto por producto: es lo que hay que tener preparado.

> **Al revés que todos los historiales del proyecto.** La billetera, el inventario y las
> restricciones se leen empezando por lo último. Esto **no es un historial: es una cola de
> trabajo**, y lo que el personal necesita saber es qué lleva más tiempo esperando.

**La consultan los dos roles de la cafetería**, `USR-3` y `USR-4`, porque `FUN-5` separa a
quien prepara de quien entrega. No comparten interfaz —el cajero no entra al admin y la
administración recibe `403` en el punto de venta—, y por eso la pantalla es una sola y vive
fuera del admin: es la segunda excepción declarada a `INT-3` (`DT-34`).

**No filtra por día y no esconde nada:**

- Una reserva de anteayer **sigue pendiente**. Ninguna historia dice hasta cuándo vale una, y
  no caducan solas (`DEC-24`): sigue ahí hasta que se entrega o alguien la cancela.
- El pedido de un estudiante que **no puede retirar** (`INVD-2`) también sigue, y se **marca**.
  Su salida es cancelarlo (`[S5.3]`).

**El acudiente, sus pedidos** (`HU-65`). `pedidos_de` devuelve los de un estudiante —por
recoger, entregados y cancelados—, **del más reciente al más antiguo**, porque eso sí es un
historial. No autoriza a nadie: la vista llega con el estudiante ya filtrado por
`estudiante_a_cargo`, que es donde vive la regla (`DT-11`). De un cancelado enseña cuándo, el
motivo y si lo canceló el propio acudiente o la cafetería.

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

`DT-35`. **El compromiso ya se adquirió y se cobró.** Si la cafetería lo preparó, se entrega
aunque el libro no lo tenga registrado; si no lo preparó, no se entrega: **se cancela**
(`[S5]`). Lo que no tiene sentido es que el sistema rechace entregar algo que el cajero tiene
en la mano. Un descuadre de inventario tiene salida —se explica y se corrige con un ingreso—.

> **Con la reserva como encargo (`DT-47`) esto deja de ser raro.** Lo que la cafetería prepara
> para una reserva tiene que entrar al libro como ingreso **antes** de entregarse; si no, la
> entrega lo deja en negativo. Es parte del trabajo de la cafetería, y no lo impide nada.

Si el libro queda en negativo, esa cifra **es información verdadera**: dice que salió
mercancía que el inventario no tenía registrada, que es el descuadre que `HU-29` existe para
auditar. La pantalla del historial lo enseña con la venta que lo originó.

### [S4.4] Lo que sí la rechaza

**Un estudiante desactivado o de baja no retira** (`INVD-2`). La regla no se reimplementa:
`comprobar_que_puede_operar` es la puerta única y la entrega la llama igual que el cobro.

**Un pedido cancelado no se entrega** (`PedidoCancelado`): el estudiante tendría el producto y
el dinero. Lo comprueba el servicio después de bloquear el pedido, y lo impide también la
restricción `pedido_estado_coherente`.

---

## [S5] Cancelar

`DEC-24`, `DT-48`. **Un solo servicio, `cancelar_pedido(actor, pedido, motivo)`, para los tres
roles que pueden**: el acudiente sobre los pedidos de sus estudiantes (`HU-66`), y el cajero
y la administración de la cafetería sobre cualquiera, desde la modal del pedido en `/reservas/`
(`HU-67`, `DT-49`). La institución
no: tiene el padrón, no la cafetería.

### [S5.1] Hace exactamente dos cosas

Cambia el estado —con quién, cuándo y el motivo— y asienta **una devolución** por el importe
íntegro de la venta, que apunta a ella (`INV-2`). El importe sale de las líneas congeladas
(`DT-8`): se devuelve lo que se cobró, no lo que el producto cuesta hoy. **No toca el
inventario**: la reserva no lo movió y no hay nada que reponer. **No borra nada**: la venta se
cobró y la devolución se asentó, y el libro tiene que poder explicar las dos.

### [S5.2] No se devuelve dos veces, y lo sostienen tres capas

Devolver dos veces es el gemelo de cobrar dos veces: el libro cuadraría con el doble y
**ninguna invariante lo notaría**.

| Capa | Qué aporta |
|---|---|
| `select_for_update(of=("self",))` sobre el pedido | Una cancelación y una entrega —o dos cancelaciones— no pueden leerlo las dos «pendiente» |
| `if bloqueado.esta_cancelado` | El mensaje que se lee |
| **`UniqueConstraint(venta)` para las devoluciones** | La garantía, también para el camino que alguien escriba mañana |

### [S5.3] Se cancela aunque el estudiante no opere

**Una devolución no es una recarga**: no entra dinero nuevo, se deshace un cobro. `INVD-7`
prohíbe las recargas al desactivado o dado de baja, y `billetera.services.asentar` solo llama a
esa puerta para la recarga y la venta. Es la salida del pedido pagado de quien no puede
retirarlo (`INVD-2`), que estaba abierta en el `ANEXO B` de `./decisiones-de-alcance.md`.

### [S5.4] El motivo, para todos y en la base

El servicio rechaza un motivo vacío con un mensaje; **la base lo impide** con
`pedido_estado_coherente`, que exige `\S` como la merma (`INV-8`, `TT-140`): tres espacios no
son un motivo. La misma restricción dice qué vale en cada estado: un pendiente no tiene entrega
ni cancelación, un entregado no está cancelado, y un cancelado no se entregó.

### [S5.5] Lo cancelado no es venta ni consumo

Se cobró y se devolvió, y el estudiante no recibió nada. La regla vive una vez, en
`ventas.selectors.sin_pedidos_cancelados`, y la aplican:

| Lectura | Efecto |
|---|---|
| El cupo del día (`consumo_del_dia`) | **Libera** lo que consumió al pagarse (`HU-66`) |
| El reporte de ventas (`/ventas/`) | No la cuenta; **su modal sí se abre**, con quién canceló y por qué, porque la auditoría enlaza con ella |
| El panel de la cafetería: últimas ventas y más vendidos | No la cuenta |
| La frecuencia y los agregados nutricionales | No la cuenta |

**Sí la enseñan**: el historial de consumo del acudiente —marcada «cancelada · importe
devuelto»—, su resumen de gasto —como gastado y devuelto, que es lo que pasó en la billetera—,
y la auditoría, con la venta en su línea y la cancelación en la suya.

---

## [S6] Las doce reglas que ninguna historia dice

Resumidas, porque es lo que hay que saber antes de tocar este flujo:

| | Regla | Dónde vive |
|---|---|---|
| 1 | La reserva valida por la misma función que el cobro | `_bloquear_y_validar` |
| 2 | La reserva **no** mira existencias: es un encargo | `existencias_de_los=None`, `DT-47` |
| 3 | Se cobra al reservar y **solo** al reservar | `reservar`, `DT-33` |
| 4 | Se descuenta inventario al entregar y **solo** al entregar | `entregar`, `DT-33` |
| 5 | La entrega **nunca** se rechaza por existencias | `DT-35` |
| 6 | Un pedido no se entrega dos veces — tres capas | `DT-15`, `[S4.2]` |
| 7 | La cola marca lo que no se puede retirar, no lo esconde | `[S3]` |
| 8 | Un pedido sale de `pendiente` una sola vez: o se entrega o se cancela | `pedido_estado_coherente` |
| 9 | Cancelar devuelve el importe una vez — tres capas | `cancelar_pedido`, `[S5.2]` |
| 10 | Toda cancelación lleva motivo, también la del acudiente | `pedido_estado_coherente`, `DT-48` |
| 11 | Se cancela aunque el estudiante no opere | `[S5.3]`, `DEC-24` |
| 12 | Lo cancelado no es venta ni consumo | `sin_pedidos_cancelados`, `[S5.5]` |

---

## [S7] Lo que este flujo deja abierto

Decisiones de alcance, no defectos. Ninguna historia las pide y el sistema no miente sobre
ellas.

| Punto | Dónde está registrado |
|---|---|
| Si las reservas caducan | `DEC-24`, «Lo que NO se decide aquí»: no caducan solas |
| Cancelar una parte de un pedido | `DEC-24`: se cancela entero |
| Avisar al acudiente cuando la cafetería cancela | `DEC-24`: lo ve en sus pedidos, con el motivo; no se le escribe |
| Que la caja **y la merma** pueden disponer de lo preparado para una reserva | `[S7]` de `./reglas-de-la-venta.md` |

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
| La cola marca lo que no puede retirarse | `TT-148` | `PR-07` | — |
| La reserva no mira existencias | — | — | `DEC-24`, `DT-47` |
| Cancelar con motivo y devolución, una vez | — | — | `DEC-24`, `DT-48` |
| Lo cancelado no es venta ni consumo | — | — | `DT-48` |

Las dos filas sin registro propio son consecuencia directa de `DT-15` —la regla vive en un
solo sitio; la invariante la impone la base— y no necesitaban una decisión nueva.
