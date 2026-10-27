"""Lecturas del inventario (`DT-15`).

Como los servicios, estos selectores no conocen `request`: reciben lo que
necesitan como argumentos y devuelven datos, nunca respuestas HTTP.
"""

from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db.models import Sum

from cuentas.models import Rol
from inventario.models import MovimientoInventario

#: Con esto o menos, un producto «queda poco»: lo dicen la tarjeta y la píldora
#: de `/inventario/` y el aviso del panel (`DEC-16`, `DT-50`). **Es una ayuda de
#: pantalla, no una regla del negocio**: nada se bloquea al cruzarlo y nadie lo
#: configura. Vive aquí, junto al dato, para que cambiarlo sea una línea.
UMBRAL_DE_EXISTENCIAS_BAJAS = 10


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


# ──────────────────────────────────────────────────────────────────────────────
# LA PANTALLA DE INVENTARIO (`DEC-25`, `DT-50`)
# ──────────────────────────────────────────────────────────────────────────────


def _gestiona_el_inventario(actor):
    """`[S11]`: «gestionar catálogo, precios e inventario» es de `USR-4`.

    Lo mismo que exigen los servicios, preguntado **antes de leer**: la pantalla
    enseña precios, existencias y quién movió qué, y nada de eso es del cajero
    ni de la institución.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Consultar el inventario exige identificarse.")
    if actor.rol != Rol.ADMINISTRADOR:
        raise PermissionDenied(
            "El inventario solo lo gestiona la administración de la cafetería."
        )
    if not actor.is_active:
        raise PermissionDenied(
            "Tu cuenta está desactivada. Pide a la institución educativa que la reactive."
        )


@dataclass(frozen=True)
class TableroDelInventario:
    """Las cuatro cifras de arriba de `/inventario/`, sobre lo que está a la venta."""

    productos: int
    agotados: int
    quedan_pocas: int
    valor: Decimal


def tablero_del_inventario(*, actor):
    """Cuántos productos se venden, cuántos se acabaron, cuántos quedan pocos y
    cuánto vale lo que hay.

    **Solo lo que está en el catálogo**: lo retirado no se vende, y contarlo
    diría que falta reponer algo que ya no se ofrece.

    Agotado es **cero o menos**. Menos de cero pasa —la entrega no se rechaza
    por existencias (`DT-35`)— y es justo lo que más urge mirar. «Quedan pocas»
    son de una a `UMBRAL_DE_EXISTENCIAS_BAJAS`: un agotado no cuenta dos veces.

    **El valor no resta los negativos.** Es existencias por precio de venta,
    sumando solo lo que hay: un descuadre en negativo no es mercancía que valga
    menos que nada.
    """
    from catalogo.models import Producto

    _gestiona_el_inventario(actor)

    productos = list(Producto.objects.filter(activo=True).only("id", "precio"))
    existencias = existencias_por_producto(productos)
    cuantas = [existencias.get(p.id, 0) for p in productos]

    return TableroDelInventario(
        productos=len(productos),
        agotados=sum(1 for c in cuantas if c <= 0),
        quedan_pocas=sum(1 for c in cuantas if 0 < c <= UMBRAL_DE_EXISTENCIAS_BAJAS),
        valor=sum(
            (max(c, 0) * p.precio for p, c in zip(productos, cuantas)), Decimal("0.00")
        ),
    )


def productos_del_inventario(
    *, actor, nombre="", categoria=None, precio_minimo=None, precio_maximo=None,
    retirados=False,
):
    """Los productos de `/inventario/`, filtrados, con sus `existencias`.

    Del catálogo o, con `retirados`, los que se retiraron: se siguen pudiendo
    consultar, mermar y devolver al catálogo, porque su historial existe
    (`INV-3`). Por nombre, de la A a la Z, que es como se busca en una lista que
    se repasa entera.

    Las existencias se calculan **en una sola consulta** para todos
    (`existencias_por_producto`) y se cuelgan de cada producto: con
    `existencias_de` por fila serían tantas consultas como productos.
    """
    from catalogo.models import Producto

    _gestiona_el_inventario(actor)

    consulta = (
        Producto.objects.filter(activo=not retirados)
        .select_related("categoria")
        .prefetch_related("alergenos")
        .order_by("nombre")
    )
    if nombre:
        consulta = consulta.filter(nombre__icontains=nombre)
    if categoria is not None:
        consulta = consulta.filter(categoria=categoria)
    if precio_minimo is not None:
        consulta = consulta.filter(precio__gte=precio_minimo)
    if precio_maximo is not None:
        consulta = consulta.filter(precio__lte=precio_maximo)

    productos = list(consulta)
    existencias = existencias_por_producto(productos)
    for producto in productos:
        producto.existencias = existencias.get(producto.id, 0)
    return productos


def historial_del_producto(*, actor, producto):
    """El libro de un producto, del más reciente al más antiguo (`HU-29`).

    Cada movimiento llega con `responsable`: quién lo registró (`HU-69`). En los
    escritos antes de que el libro lo guardara, el de una venta sale de su
    cajero, y el de la entrega de un pedido, de quien lo entregó
    (`PedidoAnticipado.entregado_por`) — **no del acudiente que reservó**, que no
    movió nada del inventario. El de un ingreso o una merma de entonces se queda
    en `None`: no se le inventa un autor.
    """
    _gestiona_el_inventario(actor)

    movimientos = list(
        historial_de(producto).select_related(
            "registrado_por", "venta__cajero", "venta__pedido_anticipado__entregado_por"
        )
    )
    for movimiento in movimientos:
        movimiento.responsable = _responsable_de(movimiento)
    return movimientos


def _responsable_de(movimiento):
    if movimiento.registrado_por is not None:
        usuario = movimiento.registrado_por
        return usuario.nombre or usuario.email
    venta = movimiento.venta
    if venta is None:
        return None
    if venta.cajero is not None:
        return venta.cajero.nombre or venta.cajero.email
    pedido = getattr(venta, "pedido_anticipado", None)
    if pedido is not None and pedido.entregado_por is not None:
        return pedido.entregado_por.nombre or pedido.entregado_por.email
    return None
