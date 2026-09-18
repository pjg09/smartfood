"""Lecturas del punto de venta (`DT-15`).

**Toda lectura no trivial pasa por aquí.** Como los servicios, estos selectores
no conocen `request`: reciben el actor como argumento y devuelven datos, nunca
respuestas HTTP.
"""

from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import PermissionDenied

from billetera.selectors import consumo_del_dia, saldo_de
from catalogo.selectors import productos_en_el_catalogo
from cuentas.models import Rol
from inventario.selectors import existencias_por_producto
from restricciones.selectors import RestriccionesVigentes, restricciones_vigentes


@dataclass(frozen=True)
class InformacionDeCobro:
    """Lo que el cajero ve del estudiante para decidir si cobra (`HU-17`).

    **Los tres datos que pide el primer criterio**: saldo, consumo del día y
    restricciones vigentes. El tercero faltaba desde el Sprint 2 —las
    restricciones no existían— y es lo que dejaba `HU-17` abierta; `TT-109` lo
    completa.

    Es un objeto y no tres valores sueltos porque se leen juntos o no se leen:
    «tiene $3.000» sin «y lleva $12.000 gastados hoy» es media respuesta, y
    cualquiera de las dos sin «y el maní está bloqueado» sigue siéndolo.

    `restricciones` llega como el objeto compuesto de `TT-106`, no desarmado en
    tres campos: así el día que haya una cuarta restricción se añade en un solo
    sitio y esta pantalla la hereda.
    """

    saldo: Decimal
    consumo_del_dia: Decimal
    restricciones: RestriccionesVigentes

    @property
    def cupo_restante(self):
        """Lo que le queda del límite diario hoy, o `None` si no tiene límite.

        Se calcula aquí y no en la plantilla por dos motivos. Uno: una plantilla
        de Django no resta. Dos, y es el que importa: el cajero necesita **la
        cifra que decide**, no dos que tenga que restar de cabeza con una fila
        delante.

        Puede ser negativa si el consumo del día ya pasó el cupo. No se recorta a
        cero: que esté en `-$500` dice algo —que el cupo se superó antes de que
        `HU-20` lo hiciera cumplir— y taparlo sería inventar que cuadra.
        """
        if self.restricciones.limite is None:
            return None
        return self.restricciones.limite.monto - self.consumo_del_dia


def informacion_de_cobro(*, actor, estudiante):
    """Saldo y consumo del día del estudiante identificado (`TT-74`, `HU-17`).

    ── ESTA FUNCIÓN ES «SOLO AL COBRAR» ────────────────────────────────────
    `[S11]`, fila «Consultar saldo de un estudiante»: el acudiente lo consulta
    libremente y el cajero **solo al cobrar**. Esa distinción no se sostiene con
    un rótulo en una pantalla: se sostiene aquí, porque este es el único camino
    por el que el saldo de un estudiante llega al rol cajero, y exige el rol.

    `saldo_de` no autoriza a nadie a propósito —lo explica en su docstring: el
    servicio de venta también lo consulta, y ahí no hay ningún acudiente—. La
    autorización va en quien llama, y en el punto de venta ese quien es esta
    función. Un rol distinto del cajero recibe `PermissionDenied` aunque escriba
    la URL a mano (`DT-11`, `INV-4`).
    ─────────────────────────────────────────────────────────────────────────

    **Se responde también del estudiante que no puede comprar** (`INVD-2`), y no
    es una grieta en lo anterior: el saldo de un estudiante de baja sigue siendo
    consultable (`HU-52`), y el cajero acaba de identificarlo con una tarjeta que
    alguien le puso delante en la caja. Callar la cifra no lo protegería de nada
    y dejaría al cajero sin poder explicar por qué no se cobra.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Consultar el saldo para cobrar exige identificarse.")
    if actor.rol != Rol.CAJERO:
        raise PermissionDenied(
            "El saldo de un estudiante se le muestra al cajero solo al cobrar, "
            "y cobrar es del rol cajero (HU-17, [S11])."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")

    return InformacionDeCobro(
        saldo=saldo_de(estudiante),
        consumo_del_dia=consumo_del_dia(estudiante),
        # `TT-109`. Las restricciones entran por el mismo sitio que las dos
        # cifras y con el mismo control de acceso: este sigue siendo el único
        # camino por el que el rol cajero llega a los datos de un estudiante.
        #
        # `[S11]` concede **consultar** restricciones a los cuatro roles
        # (`HU-38`), así que exigir el cajero aquí no las protege — las protege
        # el saldo, que sí es «solo al cobrar». Los otros tres roles consultan
        # por su propia puerta: el acudiente en `INT-1` y la cafetería y la
        # institución en `INT-3` (`TT-111`, `estudiantes_con_sus_restricciones`).
        restricciones=restricciones_vigentes(estudiante),
    )


def catalogo_de_venta():
    """Lo que hoy se puede vender, con sus existencias (`TT-81`, `HU-21`).

    Los productos retirados no salen: siguen existiendo porque el historial los
    referencia, pero no se ofrecen (`HU-26`).

    **Las existencias llegan en una sola consulta**, no una por fila: el catálogo
    del colegio no es corto y esto se pinta en cada gesto del cajero. Un producto
    sin movimientos no aparece en el agregado, así que se lee con `.get(id, 0)` —
    el cero no es un caso especial, es la suma de una lista vacía (`INV-3`).

    **Lo que devuelve es informativo, no autorizante.** Que aquí figuren tres
    empanadas no significa que al confirmar sigan estando: entre este pintado y
    el cobro puede haber otra caja. La cifra que decide se lee **dentro** del
    bloqueo, en `registrar_venta` (`DT-6`).
    """
    productos = list(productos_en_el_catalogo().order_by("categoria__nombre", "nombre"))
    existencias = existencias_por_producto(productos)

    for producto in productos:
        producto.existencias = existencias.get(producto.id, 0)

    return productos


def lineas_del_carrito(carrito):
    """Los renglones de la venta en curso, listos para pintar.

    Recibe `{id_de_producto: cantidad}` tal como lo guarda `ventas.carrito` —con
    los identificadores en texto, que es como los devuelve la sesión— y resuelve
    los productos en **una** consulta.

    Devuelve `(lineas, total)`. Cada línea trae producto, cantidad e importe; el
    importe se calcula aquí y no en la plantilla porque una plantilla no
    multiplica, y desde luego no en JavaScript (`DT-25`).

    Un producto que ya no está en el catálogo **se cae del carrito en silencio**:
    la alternativa es pintar un renglón de algo que el cobro va a rechazar de
    todas formas. El cobro lo vuelve a comprobar, que es donde importa.
    """
    productos = {
        str(producto.id): producto
        for producto in productos_en_el_catalogo().filter(id__in=carrito)
    }

    lineas = []
    total = Decimal("0.00")
    for producto_id, cantidad in carrito.items():
        producto = productos.get(str(producto_id))
        if producto is None:
            continue
        importe = producto.precio * cantidad
        total += importe
        lineas.append({"producto": producto, "cantidad": cantidad, "importe": importe})

    lineas.sort(key=lambda linea: linea["producto"].nombre)
    return lineas, total


def unidades_reservadas_pendientes(productos=None):
    """`{id_de_producto: unidades}` apartadas por reservas sin entregar.

    `TT-144`, `HU-23`. Un pedido anticipado **cobra al reservarse pero no
    descuenta inventario hasta que se entrega** (`HU-25`), así que entre las dos
    cosas hay unidades pagadas que todavía están en el libro.

    ── POR QUÉ ESTA FUNCIÓN EXISTE ─────────────────────────────────────────
    Sin ella, dos reservas del último paquete pasarían las dos: las existencias
    dicen «queda 1» las dos veces, porque ninguna lo ha descontado. El acudiente
    que reservó segundo habría pagado por algo que no va a recibir.

    No es una columna ni una caché: se cuenta desde las líneas de las ventas de
    origen `reserva` cuyo pedido sigue pendiente. `INV-3` no se toca — las
    existencias siguen siendo la suma del historial, y esto es otra cifra que se
    lee al lado.
    ─────────────────────────────────────────────────────────────────────────

    Los productos sin nada reservado no aparecen en el resultado, así que quien
    lo use debe leerlo con `.get(id, 0)` — igual que `existencias_por_producto`.
    """
    from django.db.models import Sum

    from ventas.models import EstadoDelPedido, LineaVenta, OrigenDeLaVenta

    lineas = LineaVenta.objects.filter(
        venta__origen=OrigenDeLaVenta.RESERVA,
        venta__pedido_anticipado__estado=EstadoDelPedido.PENDIENTE,
    )
    if productos is not None:
        lineas = lineas.filter(producto__in=productos)

    return {
        fila["producto"]: fila["total"]
        for fila in lineas.values("producto").annotate(total=Sum("cantidad"))
    }


def existencias_sin_reservar(productos=None):
    """Lo que de verdad se puede comprometer: existencias menos lo apartado.

    `TT-144`. Es lo que mira la reserva en lugar de las existencias a secas, y
    la única diferencia entre validar una reserva y validar una venta del
    mostrador (`_bloquear_y_validar`).

    **La venta del mostrador sigue mirando las existencias reales**, y eso deja
    un hueco conocido: el cajero puede vender unidades que están apartadas para
    una reserva pagada. Está anotado en `[S6]` de `./docs/reglas-de-la-venta.md`
    y lo decide `HU-25`, que es quien tiene que saber qué hacer cuando llega el
    estudiante y no hay lo suyo. Cambiarlo aquí sería añadir una condición a la
    venta sin historia que la pida.
    """
    existencias = existencias_por_producto(productos)
    reservadas = unidades_reservadas_pendientes(productos)

    return {
        producto_id: cuantas - reservadas.get(producto_id, 0)
        for producto_id, cuantas in existencias.items()
    }


def catalogo_para_reservar():
    """Lo que hoy se puede reservar, con lo que queda **sin apartar** (`TT-145`).

    Gemelo de `catalogo_de_venta` con una diferencia: la cifra que acompaña a
    cada producto es `existencias_sin_reservar`, no las existencias a secas. Es
    la misma que valida `reservar`, así que la pantalla no ofrece lo que el
    servicio va a rechazar.

    **Lo que devuelve es informativo, no autorizante**, igual que en el punto de
    venta: entre este pintado y el envío del formulario puede haber otra reserva.
    La cifra que decide se lee **dentro** del bloqueo (`DT-6`).
    """
    productos = list(productos_en_el_catalogo().order_by("categoria__nombre", "nombre"))
    disponibles = existencias_sin_reservar(productos)

    for producto in productos:
        producto.disponibles = disponibles.get(producto.id, 0)

    return productos


def pedidos_pendientes_de(estudiante):
    """Las reservas de un estudiante que todavía no se han entregado.

    `TT-145`. La pantalla de reserva las enseña para que el acudiente no
    reserve dos veces lo mismo por no acordarse de la anterior — el mismo
    motivo por el que la recarga enseña las últimas recargas (`TT-61`).
    """
    from ventas.models import EstadoDelPedido, PedidoAnticipado

    return (
        PedidoAnticipado.objects.filter(
            venta__estudiante=estudiante, estado=EstadoDelPedido.PENDIENTE
        )
        .select_related("venta")
        .prefetch_related("venta__lineas__producto")
    )
