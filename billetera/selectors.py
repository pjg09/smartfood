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

    **No autoriza a nadie, y es a propósito.** Un selector no sabe quién
    pregunta: quien llama decide si puede. En `INT-1` eso lo hace
    `estudiante_a_cargo`, que solo alcanza a los estudiantes propios (`DT-11`);
    en el punto de venta lo hará la identificación de `HU-15`. Meter aquí una
    comprobación de rol obligaría a pasar el actor a cada lectura interna —el
    servicio de venta consulta el saldo para decidir si alcanza (`INV-1`), y ahí
    no hay ningún acudiente— y acabaría en un `actor=None` que salta la regla.
    """
    total = MovimientoBilletera.objects.filter(billetera__estudiante=estudiante).aggregate(
        total=Sum("monto")
    )["total"]
    return total if total is not None else Decimal("0.00")


def historial_de(estudiante, limite=None):
    """Los movimientos de la billetera, del más reciente al más antiguo.

    **Es la otra mitad de `HU-08`**: `INV-2` no dice solo que el saldo salga de
    una suma, dice que se pueda **reconstruir**, y reconstruir exige poder leer
    los sumandos. Un saldo correcto que nadie puede desglosar no es trazabilidad,
    es el mismo número que había que creer, con otro origen.

    `limite` recorta para las pantallas que enseñan «los últimos movimientos»
    (`TT-64`, `PR-04`). **Sin él se devuelve el historial entero**, que es lo que
    `TST-3` compara contra el saldo: una comparación sobre una página del
    historial no probaría nada.

    Devuelve un `QuerySet` sin evaluar. El orden lo fija el modelo —`-creado_en`—
    y se repite aquí de forma explícita: quien lea esta función no tiene por qué
    ir al `Meta` a averiguar en qué orden llega un extracto.
    """
    movimientos = MovimientoBilletera.objects.filter(
        billetera__estudiante=estudiante
    ).order_by("-creado_en")

    return movimientos[:limite] if limite is not None else movimientos
