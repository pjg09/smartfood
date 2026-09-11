"""Lecturas de la billetera (`DT-15`).

Como los servicios, estos selectores no conocen `request`: reciben lo que
necesitan como argumentos y devuelven datos, nunca respuestas HTTP.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from billetera.models import MovimientoBilletera, TipoDeMovimiento


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


def consumo_del_dia(estudiante, dia=None):
    """Lo que el estudiante lleva gastado hoy, como cifra **positiva**.

    Es la segunda mitad de la información de cobro (`TT-74`, `HU-17`): el saldo
    dice cuánto hay, y esto dice cuánto se ha ido ya en la jornada. El cajero
    necesita las dos para saber, antes de montar la venta, si va a poder
    cobrarla.

    **Sale del mismo libro que el saldo** (`INV-2`, `DT-4`). No hay contador de
    consumo diario que alguien tenga que acordarse de poner a cero cada
    medianoche: es la suma de los movimientos de venta del día, y por eso no
    puede discrepar del historial que `HU-07` enseña. El día que exista el
    servicio de venta (`TT-80`, `PR-12`), esta función empieza a devolver cifras
    distintas de cero **sin tocarla**.

    ── DEVUELVE POSITIVO AUNQUE LOS MOVIMIENTOS SEAN NEGATIVOS ─────────────
    En el libro una venta resta, así que su monto es negativo (`INV-2`). Pero
    «lleva gastados $8.000» no es una cifra negativa: es cuánto salió. Se invierte
    el signo aquí, una sola vez, en lugar de dejar que cada pantalla decida si
    pone un menos delante — que es como la misma cifra acaba leyéndose de dos
    maneras.
    ─────────────────────────────────────────────────────────────────────────

    **Solo cuenta `VENTA`.** Una recarga no es consumo, y una devolución tampoco
    lo descuenta: devolver dinero no deshace que ese día se compró. Si `HU-20`
    —el límite diario, del Sprint 3— decide que una devolución sí libera cupo,
    esa decisión se toma allí, con su historia delante; adelantarla aquí sería
    inventar una regla que ningún criterio pide.

    El filtro es un **rango de fechas y hora**, no `creado_en__date`. Los dos
    devuelven lo mismo, pero `__date` envuelve la columna en una función y deja
    fuera el índice `movimiento_por_billetera`, que es `(billetera, creado_en)`.
    Esta consulta se hace en la caja, con cola delante.

    `dia` es una fecha local —`settings.TIME_ZONE` es `America/Bogota`— y por
    defecto es hoy. Existe para las pruebas y para quien un día consulte el
    consumo de otra jornada; el punto de venta siempre pregunta por hoy.
    """
    if dia is None:
        dia = timezone.localdate()

    # Los límites de la jornada **en la zona horaria del colegio**, no en UTC:
    # una venta de las 19:00 de Bogotá es de las 00:00 UTC del día siguiente, y
    # partir el día por UTC movería el almuerzo de media tarde al día que no es.
    comienzo = timezone.make_aware(datetime.combine(dia, time.min))
    siguiente = comienzo + timedelta(days=1)

    total = MovimientoBilletera.objects.filter(
        billetera__estudiante=estudiante,
        tipo=TipoDeMovimiento.VENTA,
        creado_en__gte=comienzo,
        creado_en__lt=siguiente,
    ).aggregate(total=Sum("monto"))["total"]

    return -total if total is not None else Decimal("0.00")
