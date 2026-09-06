"""Modelos de la billetera del estudiante (`TT-59`, `HU-06`, `DT-4`).

Aquí van la estructura y las invariantes que la base de datos puede imponer:
`CheckConstraint` y `UniqueConstraint`. **Sin lógica de negocio** (`DT-15`).

═══════════════════════════════════════════════════════════════════════════
**NO EXISTE UNA COLUMNA `saldo`, Y ESA ES LA DECISIÓN ENTERA.**

`INV-2` exige que el saldo pueda reconstruirse siempre desde el historial de
movimientos, y `DT-4` dice cómo se sostiene: el saldo **es** la suma de los
movimientos, no un número guardado al lado que se actualiza con cada uno.

Así `INV-2` y su prueba `TST-3` son ciertas **por construcción** y no porque
alguien se acuerde de mantenerlas: no puede haber discrepancia entre el saldo
mostrado y el historial, porque son el mismo dato. Con una columna `saldo` habría
dos fuentes de verdad y una venta a medio asentar las dejaría divergir para
siempre, sin forma de saber cuál miente.

Si algún día el volumen exigiera desnormalizar, se haría **dentro de la misma
transacción** y como caché declarada, nunca como el dato bueno.
═══════════════════════════════════════════════════════════════════════════

La clave primaria es UUIDv7 generado en la aplicación (`DT-17`).
"""

import uuid

from django.db import models


class Billetera(models.Model):
    """La billetera de un estudiante. **Una por estudiante** (`HU-06`).

    Primer criterio de `HU-06`: la billetera es individual por estudiante, no de
    la cuenta del acudiente. Un acudiente con tres hijos tiene tres billeteras, y
    el saldo de uno no paga el almuerzo de otro. Lo impone la base con el
    `OneToOneField`, no una comprobación en el servicio.

    **Nace en la primera recarga**, no con el estudiante. Es lo que evita que
    `personas` tenga que importar de `billetera` —la dependencia natural va al
    revés— y no cambia lo que se ve: sin movimientos el saldo es cero, con fila o
    sin ella. `saldo_de()` trata los dos casos igual.

    `PROTECT` sobre el estudiante: dar de baja no borra: es un estado (`DT-12`,
    `HU-51`), y su saldo sigue siendo consultable (`HU-52`). Un borrado en
    cascada se llevaría por delante el historial que `INV-2` obliga a conservar.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    estudiante = models.OneToOneField(
        "personas.Estudiante",
        on_delete=models.PROTECT,
        related_name="billetera",
        verbose_name="estudiante",
    )
    creada_en = models.DateTimeField("creada en", auto_now_add=True)

    class Meta:
        verbose_name = "billetera"
        verbose_name_plural = "billeteras"

    def __str__(self):
        return f"Billetera de {self.estudiante.nombre}"


class TipoDeMovimiento(models.TextChoices):
    """Los tres tipos de `[S2]`, y cada uno tiene su signo obligado.

    `VENTA` y `DEVOLUCION` no tienen todavía quién los asiente —la venta es
    `HU-21` y el servicio de `TT-80`—, pero se declaran desde ahora: el libro de
    movimientos se define entero o no explica el saldo. Lo que falta es el
    servicio, no el concepto.
    """

    RECARGA = "recarga", "Recarga"
    VENTA = "venta", "Venta"
    DEVOLUCION = "devolucion", "Devolución"


class MovimientoBilletera(models.Model):
    """Un asiento del libro. **Nunca se edita ni se borra** (`INV-2`).

    ── EL MONTO LLEVA SIGNO ────────────────────────────────────────────────
    Una recarga suma y una venta resta, y eso va **en el propio monto**: la
    recarga es positiva y la venta negativa. Así el saldo es literalmente
    `SUM(monto)`, una sola operación que la base sabe hacer y que no puede
    equivocarse de criterio.

    La alternativa —monto siempre positivo y el signo deducido del tipo— obliga a
    un `CASE` en cada consulta de saldo, y basta con que un tipo nuevo se olvide
    en ese `CASE` para que el saldo empiece a mentir sin que nada falle.

    El signo no queda al criterio de quien escriba el servicio: lo impone una
    `CheckConstraint` por tipo. Un `if` se olvida en el siguiente camino de
    escritura; una restricción de la base, no (`DT-15`).
    ─────────────────────────────────────────────────────────────────────────

    **Sin `monto = 0`.** Un movimiento que no mueve nada no es un movimiento: es
    ruido en el historial que `INV-2` obliga a poder leer.

    La referencia a la venta que origina el movimiento llega con `TT-78`, cuando
    exista el modelo. Hasta entonces no se declara una clave ajena a una tabla
    que no existe.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    billetera = models.ForeignKey(
        Billetera,
        on_delete=models.PROTECT,
        related_name="movimientos",
        verbose_name="billetera",
    )
    tipo = models.CharField("tipo", max_length=20, choices=TipoDeMovimiento.choices)
    monto = models.DecimalField("monto", max_digits=10, decimal_places=2)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "movimiento de billetera"
        verbose_name_plural = "movimientos de billetera"
        # Del más reciente al más antiguo: es el orden en que se lee un extracto.
        ordering = ["-creado_en"]
        indexes = [
            # El saldo se calcula sumando los movimientos de una billetera, y esa
            # es la consulta más frecuente del sistema en cuanto exista la venta.
            models.Index(fields=["billetera", "creado_en"], name="movimiento_por_billetera"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(monto=0),
                name="movimiento_monto_distinto_de_cero",
            ),
            # El signo va atado al tipo, en la base. Recargar en negativo sería
            # robar saldo sin dejar un movimiento que lo parezca, y vender en
            # positivo sería regalarlo.
            models.CheckConstraint(
                condition=(
                    models.Q(tipo=TipoDeMovimiento.VENTA, monto__lt=0)
                    | models.Q(tipo=TipoDeMovimiento.RECARGA, monto__gt=0)
                    | models.Q(tipo=TipoDeMovimiento.DEVOLUCION, monto__gt=0)
                ),
                name="movimiento_signo_segun_tipo",
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.monto}"
