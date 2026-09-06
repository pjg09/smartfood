"""Lecturas de la billetera (`DT-15`).

Como los servicios, estos selectores no conocen `request`: reciben lo que
necesitan como argumentos y devuelven datos, nunca respuestas HTTP.
"""

from decimal import Decimal

from django.db.models import Sum

from billetera.models import MovimientoBilletera


def saldo_de(estudiante):
    """El saldo del estudiante: **la suma de sus movimientos** (`INV-2`, `DT-4`).

    No lee ninguna columna `saldo`, porque no existe. Esta función es la única
    definición de «saldo» del sistema, y por eso vale la pena que sea una línea:
    cuanto menos haga, menos puede discrepar del historial.

    Un estudiante sin billetera —o con billetera y sin movimientos— tiene saldo
    cero. Son el mismo hecho contado de dos maneras: la fila nace en la primera
    recarga (ver `billetera.models.Billetera`).

    La lectura completa de `HU-08` y su prueba `TST-3` son de `PR-03` (`TT-62`,
    `TT-63`); esto es lo que el servicio de recarga necesita para no adelantarlas.
    """
    total = MovimientoBilletera.objects.filter(billetera__estudiante=estudiante).aggregate(
        total=Sum("monto")
    )["total"]
    return total if total is not None else Decimal("0.00")
