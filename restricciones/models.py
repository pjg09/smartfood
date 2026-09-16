"""Modelos del control parental (`TT-94`, `HU-09`, `DT-28`).

Aquí van la estructura y las invariantes que la base de datos puede imponer:
`CheckConstraint` y `UniqueConstraint`. **Sin lógica de negocio** (`DT-15`).

═══════════════════════════════════════════════════════════════════════════
**ESTA APP ES UNA DESVIACIÓN DECLARADA DE `DT-15`, NO UN DESCUIDO.**

`DT-15` enumeró siete apps y `restricciones` no era ninguna de ellas. El
control parental no cabe en las que hay: pertenece al estudiante pero
referencia el catálogo, así que meterlo en `personas` acopla ese dominio con
`catalogo`, y meterlo en `catalogo` lo acopla al revés — y el catálogo es de la
cafetería, que es justamente quien `INV-4` deja fuera.

La decisión está registrada como `DT-28` en `docs/decisiones-tecnicas.md`. Sin
ese registro, dentro de dos meses nadie sabría si la app nació de una decisión o
de una tarde.
═══════════════════════════════════════════════════════════════════════════

**Ningún modelo de esta app se registra en el admin, y esa ausencia es la mitad
de `INV-4`.** La invariante dice que ni la cafetería ni la institución desactivan
las restricciones, y `DT-11` precisa cómo: con permisos en la capa de datos. El
acudiente no entra al admin —`INT-1` es su interfaz (`DT-2`)—, así que un
`admin.site.register` aquí no serviría a quien sí puede y abriría una puerta a
quien no. El control de quién escribe vive en `services.py`; los permisos de
`[S11]` los cierra `TT-107`.

La clave primaria es UUIDv7 generado en la aplicación (`DT-17`).
"""

import uuid

from django.db import models


class LimiteDiario(models.Model):
    """Cuánto puede gastar un estudiante en una jornada (`HU-09`, `ALC-IN-07`).

    ── ES POR ESTUDIANTE, Y LO IMPONE LA BASE ──────────────────────────────
    Primer criterio de `HU-09`. Un acudiente con tres hijos fija tres límites
    distintos, y el cupo de uno no es el del otro. Lo sostiene el
    `OneToOneField` sobre `Estudiante`, no una comprobación del servicio: colgar
    el límite de la cuenta del acudiente —que es la alternativa que parece más
    cómoda— haría imposible el criterio, y ningún `if` podría recuperarlo.
    ─────────────────────────────────────────────────────────────────────────

    ── NO HAY FILA = NO HAY LÍMITE ─────────────────────────────────────────
    La ausencia de límite se representa **sin fila**, nunca con `monto = 0`. Un
    cero es una cifra legítima —«no puede gastar nada»— y usarla para decir «no
    configuré nada» dejaría dos hechos opuestos escritos igual. Por eso el monto
    lleva `CheckConstraint(monto > 0)`: quien no quiere límite no guarda uno, y
    `HU-12` retira el suyo borrando la fila, no poniéndola a cero.
    ─────────────────────────────────────────────────────────────────────────

    **No guarda cuánto se lleva gastado hoy, y no es un olvido.** El consumo del
    día es la suma de los movimientos de venta de la jornada y ya lo calcula
    `billetera.selectors.consumo_del_dia` (`INV-2`, `DT-4`). Un contador aquí
    sería un segundo dato que alguien tendría que acordarse de poner a cero cada
    medianoche, y el día que discrepara del libro no habría forma de saber cuál
    de los dos miente. La comparación la hará `TT-116` en la venta, leyendo el
    historial.

    `PROTECT` sobre el estudiante: dar de baja no borra —es un estado (`DT-12`,
    `HU-51`)—, y una cascada se llevaría por delante la configuración que el
    acudiente hizo si algún día esa baja se revirtiera.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    estudiante = models.OneToOneField(
        "personas.Estudiante",
        on_delete=models.PROTECT,
        related_name="limite_diario",
        verbose_name="estudiante",
    )
    monto = models.DecimalField("monto", max_digits=10, decimal_places=2)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "límite diario"
        verbose_name_plural = "límites diarios"
        constraints = [
            # Un límite de cero o negativo no es un límite: es la ausencia de
            # uno escrita donde no toca. La regla la impone la base y no un `if`
            # del servicio, porque un `if` se olvida en el siguiente camino de
            # escritura y una restricción no (`DT-15`).
            models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name="limite_diario_monto_positivo",
            ),
        ]

    def __str__(self):
        return f"Límite diario de {self.estudiante.nombre}"
