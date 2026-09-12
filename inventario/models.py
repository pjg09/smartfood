"""Modelos del inventario (`TT-67`, `HU-27`, `DT-5`).

Aquí van la estructura y las invariantes que la base de datos puede imponer:
`CheckConstraint` y `UniqueConstraint`. **Sin lógica de negocio** (`DT-15`).

═══════════════════════════════════════════════════════════════════════════
**NO EXISTE UNA COLUMNA `existencias`.** Es el mismo razonamiento que sostiene
la billetera (`DT-4`), aplicado a `INV-3`: las existencias de un producto **son**
la suma de los movimientos de su historial, no un contador que se actualiza.

Así `INV-3` —«las existencias se explican siempre desde el historial»— y su
prueba `TST-4` son ciertas por construcción. Con un contador al lado habría dos
fuentes de verdad, y una venta a medio asentar las dejaría divergir sin forma de
saber cuál miente.
═══════════════════════════════════════════════════════════════════════════

**Unidades vendibles, no insumos** (`HU-27`, `ALC-OUT-11`, `ALC-OUT-12`). Una
empanada es una unidad de inventario; la harina y el aceite con que se hizo, no.
Un producto preparado en la cafetería entra como existencia por el mismo ajuste
manual que la mercancía comprada, sin descomponerlo en una receta. Por eso la
cantidad es un entero: media empanada no se vende.

La clave primaria es UUIDv7 generado en la aplicación (`DT-17`).
"""

import uuid

from django.db import models


class TipoDeMovimientoDeInventario(models.TextChoices):
    """Los tres tipos de `[S2]`.

    `VENTA` no tiene todavía quién lo asiente —es `HU-21` y el servicio de
    `TT-80`—, y `MERMA` lo ejercita `HU-28` en el Sprint 4. Se declaran desde
    ahora porque el libro se define entero o no explica las existencias, y
    porque la restricción de `INV-8` **es más barata puesta con el modelo que
    añadida después sobre datos ya escritos**.
    """

    INGRESO = "ingreso", "Ingreso"
    VENTA = "venta", "Venta"
    MERMA = "merma", "Merma"


class MovimientoInventario(models.Model):
    """Un asiento del libro. **Nunca se edita ni se borra** (`INV-3`).

    ── LA CANTIDAD LLEVA SIGNO ─────────────────────────────────────────────
    Un ingreso suma y una venta o una merma restan, y eso va **en la propia
    cantidad**. Las existencias son literalmente `SUM(cantidad)`: una operación
    que la base sabe hacer y que no puede equivocarse de criterio.

    La alternativa —cantidad siempre positiva y el signo deducido del tipo—
    obliga a un `CASE` en cada consulta, y basta con que un tipo nuevo se olvide
    ahí para que las existencias empiecen a mentir sin que nada falle. Es la
    misma decisión que el monto de la billetera, y por el mismo motivo.
    ─────────────────────────────────────────────────────────────────────────

    ── EL MOTIVO ES OBLIGATORIO EN TODA DISMINUCIÓN MANUAL ─────────────────
    `INV-8`. Una merma es la única forma de que desaparezcan existencias sin que
    haya una venta que lo explique: sin motivo, el inventario tendría un agujero
    y ninguna manera de saber si fue rotura, caducidad o un descuadre. Lo impone
    una `CheckConstraint`, **no una validación de formulario** (`DT-5`): un
    formulario protege un camino; la restricción, todos.

    La venta no lo exige porque su motivo **es** la venta: la línea que la
    origina dice qué se vendió, a quién y cuándo (`TT-78`).
    ─────────────────────────────────────────────────────────────────────────

    ── Y AHORA LA SEÑALA (`TT-78`) ─────────────────────────────────────────
    La clave ajena a `Venta` es la que `TT-67` dejó prometida. Es lo que convierte
    la frase de arriba en algo comprobable: el motivo de una salida por venta **es**
    la venta, y con la referencia puesta se puede ir a mirarla en lugar de
    suponerla. `INV-3` pide que las existencias se expliquen desde el historial, y
    una salida de tres unidades sin decir de qué venta no las explica.

    Dos restricciones lo sostienen: el movimiento de venta apunta a la suya, y el
    ingreso y la merma **no** apuntan a ninguna — los dos son manuales y su
    explicación es el motivo, no una compra que no existió.

    `PROTECT`: borrar una venta que ya movió existencias dejaría el movimiento
    sin lo que lo explica.
    ─────────────────────────────────────────────────────────────────────────
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    producto = models.ForeignKey(
        "catalogo.Producto",
        on_delete=models.PROTECT,
        related_name="movimientos_de_inventario",
        verbose_name="producto",
    )
    tipo = models.CharField(
        "tipo", max_length=20, choices=TipoDeMovimientoDeInventario.choices
    )
    # Entero: el inventario opera sobre unidades vendibles (`HU-27`). Con signo:
    # ver la nota de arriba.
    cantidad = models.IntegerField("cantidad")
    # `blank=True` y `default=""`, nunca `null`: dos formas de decir «no hay
    # motivo» son dos formas de que la restricción de `INV-8` se pueda esquivar.
    motivo = models.CharField("motivo", max_length=200, blank=True, default="")
    # `null=True`: un ingreso y una merma no salen de ninguna venta. Qué tipos la
    # exigen y cuáles la prohíben lo dicen las restricciones de abajo.
    venta = models.ForeignKey(
        "ventas.Venta",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_de_inventario",
        verbose_name="venta",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario"
        ordering = ["-creado_en"]
        indexes = [
            # Las existencias se calculan sumando los movimientos de un producto,
            # y esa es la consulta que hará el punto de venta en cada cobro.
            models.Index(fields=["producto", "creado_en"], name="movimiento_por_producto"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(cantidad=0),
                name="movimiento_inventario_cantidad_distinta_de_cero",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(tipo=TipoDeMovimientoDeInventario.INGRESO, cantidad__gt=0)
                    | models.Q(tipo=TipoDeMovimientoDeInventario.VENTA, cantidad__lt=0)
                    | models.Q(tipo=TipoDeMovimientoDeInventario.MERMA, cantidad__lt=0)
                ),
                name="movimiento_inventario_signo_segun_tipo",
            ),
            # `INV-8`. La merma es la disminución manual: sin motivo no entra.
            models.CheckConstraint(
                condition=(
                    ~models.Q(tipo=TipoDeMovimientoDeInventario.MERMA)
                    | ~models.Q(motivo="")
                ),
                name="movimiento_inventario_merma_con_motivo",
            ),
            # `TT-78`. El motivo de una salida por venta **es** la venta, y aquí
            # se obliga a que se pueda ir a mirarla (`INV-3`).
            models.CheckConstraint(
                condition=(
                    ~models.Q(tipo=TipoDeMovimientoDeInventario.VENTA)
                    | models.Q(venta__isnull=False)
                ),
                name="movimiento_inventario_de_venta_con_su_venta",
            ),
            # El ingreso y la merma son manuales: los explica su motivo, no una
            # compra. Referenciar una venta desde ellos sería inventarla.
            models.CheckConstraint(
                condition=(
                    ~models.Q(
                        tipo__in=[
                            TipoDeMovimientoDeInventario.INGRESO,
                            TipoDeMovimientoDeInventario.MERMA,
                        ]
                    )
                    | models.Q(venta__isnull=True)
                ),
                name="movimiento_inventario_manual_sin_venta",
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.cantidad} · {self.producto}"
