"""Lecturas del inventario (`DT-15`).

Como los servicios, estos selectores no conocen `request`: reciben lo que
necesitan como argumentos y devuelven datos, nunca respuestas HTTP.
"""

from django.db.models import Sum

from inventario.models import MovimientoInventario


def existencias_de(producto):
    """Las existencias de un producto: **la suma de sus movimientos** (`INV-3`).

    No lee ninguna columna `existencias`, porque no existe. Esta función es la
    única definición de «existencias» del sistema, y por eso vale la pena que sea
    una línea: cuanto menos haga, menos puede discrepar del historial.

    Un producto sin movimientos tiene cero. No es un caso especial: es la suma de
    una lista vacía.

    **No autoriza a nadie**, igual que `billetera.selectors.saldo_de`: un selector
    no sabe quién pregunta. El punto de venta lo consultará para decidir si hay
    stock (`HU-21`), y ahí quien opera es el cajero.
    """
    total = MovimientoInventario.objects.filter(producto=producto).aggregate(
        total=Sum("cantidad")
    )["total"]
    return total if total is not None else 0


def existencias_por_producto(productos=None):
    """`{id_de_producto: existencias}`, en **una sola consulta**.

    Lo pide el listado de la administración (`TT-69`): con `existencias_de` por
    fila serían tantas consultas como productos, y el catálogo del colegio no es
    corto. Los productos sin ningún movimiento no aparecen en el resultado, así
    que quien lo use debe leerlo con `.get(id, 0)` — el cero sigue sin ser un
    caso especial.
    """
    movimientos = MovimientoInventario.objects.all()
    if productos is not None:
        movimientos = movimientos.filter(producto__in=productos)

    return {
        fila["producto"]: fila["total"]
        for fila in movimientos.values("producto").annotate(total=Sum("cantidad"))
    }


def historial_de(producto, limite=None):
    """Los movimientos de un producto, del más reciente al más antiguo.

    **Es la otra mitad de `INV-3`**: la invariante dice que las existencias se
    **expliquen** desde el historial, y explicar exige poder leerlo. Un número
    correcto que nadie puede desglosar no explica nada.
    """
    movimientos = MovimientoInventario.objects.filter(producto=producto).order_by(
        "-creado_en"
    )
    return movimientos[:limite] if limite is not None else movimientos
