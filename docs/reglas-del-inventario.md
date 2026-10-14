# SmartFood — Las reglas del inventario

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-REGLAS-INVENTARIO |
| titulo | Qué mueve las existencias, con qué signo, quién lo firma y qué nunca se escribe a mano |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./smartfood.md` (`ALC-IN-16`, `ALC-IN-18`, `ALC-IN-19`, `INV-3`, `INV-8`, `S11`); `./decisiones-de-alcance.md` (`DEC-24`, `DEC-25`); `./decisiones-tecnicas.md` (`DT-5`, `DT-6`, `DT-35`, `DT-47`, `DT-50`, `DT-51`); `./backlog-historias-de-usuario.md` (`HU-21`, `HU-25`, `HU-26` … `HU-29`, `HU-36`, `HU-69`); `inventario/models.py`, `inventario/services.py`, `inventario/selectors.py` |
| tipo_documento | Documento operativo. **No es un artefacto de Scrum ni un entregable** |
| creado | 2026-10-14, al reunir el inventario en `/inventario/` (`DEC-25`) |
| idioma | es-CO |
| version | 1.0 |

### [S0.1] Qué responde este documento

**De dónde sale la cifra de existencias de un producto, qué la mueve y qué no puede moverla.**

Es el cuarto de la serie, después de `./reglas-de-la-venta.md`, `./reglas-del-pedido-anticipado.md`
y `./reglas-del-cierre-de-caja.md`, y existe por lo mismo: las reglas del libro de inventario
estaban repartidas entre docstrings, cinco decisiones técnicas y las restricciones del modelo,
y **varias no salen de ninguna historia**. La que más importa —que una entrega puede dejar el
libro en negativo y no es un fallo— es la que antes se toma por un error.

> **El código manda.** Este documento describe `inventario/models.py`, `inventario/services.py`
> e `inventario/selectors.py`; si algún día discrepan, el equivocado es este. Lo que aquí se
> fija son **las razones**.

---

## [S1] Las existencias son una suma, no una columna

**No existe una columna `existencias`** (`DT-5`, `INV-3`). Las existencias de un producto son
la suma de los movimientos de su libro, `MovimientoInventario`, y la única definición es
`existencias_de` en `inventario/selectors.py`. Con un contador al lado habría dos fuentes de
verdad, y una venta a medio asentar las dejaría divergir sin forma de saber cuál miente.

**La cantidad lleva signo**: un ingreso suma, una venta o una merma restan, y eso va en la
propia cantidad. Así las existencias son literalmente `SUM(cantidad)`; con la cantidad siempre
positiva y el signo deducido del tipo, un tipo nuevo olvidado en un `CASE` haría mentir a las
existencias sin que nada fallara.

**Un asiento no se edita ni se borra.** Corregido a posteriori, dejaría unas existencias que ya
no explican lo que pasó. Un error se corrige con otro movimiento —una merma con su motivo, o
el ingreso que faltaba—, que es como se corrige un libro.

---

## [S2] Los tres tipos de movimiento

| Tipo | Signo | Lo asienta | Lo explica | Lo impone la base |
|---|---|---|---|---|
| **Ingreso** | `+` | `ingresar_mercancia` — la administración (`HU-27`) | Su motivo | `movimiento_inventario_signo_segun_tipo`, `movimiento_inventario_manual_sin_venta` |
| **Merma** | `−` | `registrar_merma` — la administración (`HU-28`) | Su motivo, **obligatorio** (`INV-8`) | `movimiento_inventario_merma_con_motivo`, con `\S`: tres espacios no son un motivo |
| **Venta** | `−` | `registrar_venta` al cobrar (`HU-21`) y `entregar` al entregar un pedido (`HU-25`) | La venta que lo origina | `movimiento_inventario_de_venta_con_su_venta`, `movimiento_inventario_una_salida_por_venta_y_producto` |

**`asentar` es el único punto de escritura del libro** (`TT-67`). Los servicios de arriba
deciden quién puede; `asentar` comprueba la forma —el signo, la venta, el motivo, quién— venga
de donde venga, y la base lo vuelve a imponer con sus restricciones (`DT-15`).

**No hay un «ajuste» con signo libre** (`DEC-25`, `DT-50`). La única disminución manual es la
merma: un tercer tipo que pudiera restar sin ser merma abriría un camino por el que `INV-8` no
pasa.

---

## [S3] Ingreso y merma se escriben en positivo

Quien registra cuenta unidades: «llegaron 30», «se dañaron 3». **Los dos servicios reciben la
cantidad en positivo y el tipo pone el signo.** Pedir «-3» invita a escribir «3» donde iba
«-3», y ese error no falla: sumaría existencias que nadie ingresó. La pantalla lo refuerza: el
campo de unidades solo admite dígitos (`[S2.11]` de `./sistema-visual.md`).

**El motivo es obligatorio en los dos en la pantalla**, y en la base solo en la merma. La base
lo exige donde lo pide `INV-8` —toda disminución manual—; la pantalla, donde lo pide `HU-29`
—todo movimiento queda asentado con su motivo— (`DEC-25`). Un script que llame a
`ingresar_mercancia` sin motivo sigue funcionando.

**Un producto preparado en la cafetería entra como ingreso**, igual que uno comprado: treinta
empanadas son treinta unidades vendibles, sin receta ni insumos (`HU-27`, `ALC-OUT-11`,
`ALC-OUT-12`).

---

## [S4] La merma no deja el libro en negativo; la entrega sí puede

**La merma se rechaza si dejaría las existencias por debajo de cero.** No lo pide `HU-28`; se
aplica por el mismo razonamiento con el que la venta rechaza por existencias insuficientes
(`[S4]` de `./reglas-de-la-venta.md`). Si de verdad había más de lo que dice el libro, falta un
ingreso que nadie registró, y ese ingreso también tiene una explicación: primero el ingreso,
después la merma.

**Se comprueba dentro del bloqueo** (`DT-6`): `select_for_update` sobre el producto y, solo
después, leer las existencias. Dos mermas simultáneas que leyeran antes de bloquear pasarían
las dos.

**La entrega de un pedido no se rechaza por existencias** (`DT-35`). El pedido ya está cobrado:
rechazarlo dejaría al estudiante sin lo suyo y con el dinero pagado. Así que **el libro puede
quedar en negativo, y no es un fallo**: dice que salió mercancía que el inventario no tenía
registrada. Desde que la reserva es un encargo y no aparta existencias (`DT-47`, `DEC-24`),
**registrar el ingreso de lo preparado antes de entregar es parte del trabajo** de la
cafetería.

**Un pedido no se entrega dos veces**: la `UniqueConstraint` de una salida por venta y producto
lo impide aunque alguien se salte el servicio.

---

## [S5] Quién firma cada asiento

**`registrado_por` guarda quién hizo el asiento** (`HU-69`, `DT-50`): la administración en un
ingreso o una merma, el cajero en una venta o una entrega. `asentar` lo exige, sin valor por
defecto.

**Lo escrito antes del 2026-10-14 no tiene quién**, y no se le inventa. La columna admite nulo
solo por esas filas: una `CheckConstraint` no podría validarse sobre ellas sin atribuirles un
autor. Al enseñarlas, el historial de un producto toma el cajero de la venta o quien entregó
el pedido (`PedidoAnticipado.entregado_por`) —**nunca el acudiente que reservó**, que no movió
nada del inventario—, y un ingreso o una merma antiguos dicen «sin registrar». La auditoría
hace lo mismo y cuenta cuántos quedan sin quién.

---

## [S6] Lo que enseña la pantalla, y por qué

`/inventario/` (`DEC-25`) lee el libro; no guarda nada propio.

| Cifra | Qué cuenta | Por qué así |
|---|---|---|
| **Productos** | Los que están en el catálogo | Lo retirado no se vende |
| **Agotados** | Existencias **cero o menos** | Menos de cero pasa (`[S4]`), y es lo que más urge reponer |
| **Quedan pocas** | De 1 a `UMBRAL_DE_EXISTENCIAS_BAJAS` (10) | Un agotado no cuenta dos veces. **El umbral es una ayuda de pantalla**, no una regla: nada se bloquea al cruzarlo y nadie lo configura. Vive en `inventario/selectors.py` y lo usa también el panel |
| **Valor del inventario** | Existencias por precio de venta, **sin restar los negativos** | Un descuadre no es mercancía que valga menos que nada |

**El historial de un producto suma por un camino distinto que el total.** El total es un `SUM`
de PostgreSQL; la suma de las líneas se cuenta en Python al pintar. Si divergieran, la modal lo
dice en rojo: es `TST-4` puesto donde lo ve un humano (`HU-29`).

**El reporte de movimientos** con sus totales por periodo (`HU-36`) sigue en el admin, de solo
lectura: se registra en `/inventario/`, con el producto delante.

---

## [S7] Retirar no es borrar

**Un producto que ya se movió no puede desaparecer**: el libro lo referencia, y sin él las
existencias dejan de explicarse (`INV-3`). Lo que existe es **retirarlo del catálogo** (`HU-26`):
deja de venderse y de ofrecerse, y su historial, sus ventas y los bloqueos que le pusieron los
acudientes se conservan. **Un retirado también se merma** —lo que queda en la estantería se
daña igual— y se devuelve al catálogo cuando se quiera.

**Una categoría solo se elimina vacía**, contando los productos retirados (`DT-51`): la garantía
es el `PROTECT` de `Producto.categoria`, y los productos no se reasignan solos.

---

## [S8] Quién puede

`[S11]`: «gestionar catálogo, precios e inventario» es de la **administración de la
cafetería**. Ingresar, mermar, crear, editar y retirar productos se lo exigen los servicios, y
leer `/inventario/` se lo exigen los selectores, **antes** de buscar el producto: un `404` no
puede contarle a otro rol qué existe. El cajero mueve el inventario solo vendiendo y
entregando; la institución y el acudiente, nunca.

---

## [ANEXO A] Las reglas que ninguna historia dice

| Regla | Dónde se decidió |
|---|---|
| La merma no deja el libro en negativo | `inventario/services.py`, por el razonamiento de `[S4]` de `./reglas-de-la-venta.md` |
| La entrega sí puede dejarlo, y no es un fallo | `DT-35` |
| La reserva no aparta existencias | `DT-47`, `DEC-24` |
| Ingreso y merma se escriben en positivo | `HU-28` para la merma; `DT-50` para la pantalla |
| No hay ajuste con signo libre | `DEC-25`, `DT-50` |
| El motivo del ingreso es obligatorio en la pantalla | `DEC-25`, por `HU-29` |
| Lo antiguo no se atribuye a nadie | `HU-69`, `DT-50` |
| Agotado es cero o menos; el valor no resta negativos | `DT-50` |
