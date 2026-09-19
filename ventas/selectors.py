"""Lecturas del punto de venta (`DT-15`).

**Toda lectura no trivial pasa por aquí.** Como los servicios, estos selectores
no conocen `request`: reciben el actor como argumento y devuelven datos, nunca
respuestas HTTP.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.utils import timezone

from billetera.selectors import consumo_del_dia, saldo_de
from catalogo.selectors import productos_en_el_catalogo
from cuentas.models import Rol
from inventario.selectors import existencias_por_producto
from restricciones.selectors import RestriccionesVigentes, restricciones_vigentes

# El importe de un renglón, calculado por la base: precio congelado por unidades
# (`DT-8`). Se declara **una vez y aquí**, que es de donde es el renglón, porque
# lo usan el historial del acudiente, el reporte de ventas de la cafetería y el
# efectivo esperado del cierre. Repetir la expresión es como acaban dando cifras
# distintas (`DT-19`).
#
# Se atraviesa **desde la venta** —`lineas__…`—, así que sirve tal cual en
# cualquier `QuerySet` de `Venta`.
IMPORTE_DE_LA_LINEA = ExpressionWrapper(
    F("lineas__precio_unitario") * F("lineas__cantidad"),
    output_field=DecimalField(max_digits=12, decimal_places=2),
)

# La diferencia de un cierre de caja, **calculada por la base** (`TT-175`).
#
# ── ES EL GEMELO EN SQL DE `CierreDeCaja.diferencia`, Y ESO HAY QUE VIGILARLO ─
# La propiedad del modelo resta en Python y sirve para una fila; esta expresión
# resta en Postgres y sirve para agregar, filtrar y ordenar un listado entero.
# Son dos escrituras de la misma regla, que es justo lo que `DT-19` evita — y
# aquí no hay salida: sumar en Python obligaría a traerse todos los cierres.
#
# Lo que se hace en su lugar es **fijar que coinciden**: hay una prueba que
# compara las dos sobre las mismas filas y falla si alguien toca una sola. Si un
# día hace falta una tercera forma de restar esto, la respuesta no es escribirla,
# es preguntarse por qué.
DIFERENCIA_DEL_CIERRE = ExpressionWrapper(
    F("efectivo_contado") - F("base") - F("efectivo_esperado"),
    output_field=DecimalField(max_digits=12, decimal_places=2),
)


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


def reservas_pendientes(*, actor):
    """Las reservas pagadas que nadie ha recogido todavía (`TT-147`, `HU-24`).

    Devuelve los `PedidoAnticipado` en estado `pendiente`, del más antiguo al más
    reciente, con el estudiante y las líneas ya traídos.

    ── EL ORDEN ES DEL MÁS ANTIGUO AL MÁS RECIENTE, Y ES AL REVÉS QUE TODO ─
    Un historial se lee empezando por lo último, y por eso el de la billetera,
    el del inventario y el de restricciones llegan así. **Esto no es un
    historial: es una cola de trabajo.** Lo que el personal necesita saber es
    qué lleva más tiempo esperando, no qué acaba de entrar.
    ─────────────────────────────────────────────────────────────────────────

    ── QUIÉN PUEDE, Y POR QUÉ SON DOS ROLES ───────────────────────────────
    `HU-24` los nombra a los dos: `USR-3` y `USR-4`. `FUN-5` explica por qué —«el
    personal de la cafetería consulta las reservas pendientes y registra su
    entrega»—: quien prepara y quien entrega no tienen que ser la misma persona.

    La autorización vive aquí y no en la vista, como en `informacion_de_cobro`:
    este es el único camino por el que la cola de reservas llega a una pantalla,
    y exige el rol aunque alguien escriba la URL a mano (`DT-11`, `INV-4`).

    **El acudiente no entra por aquí.** Las suyas las ve en su pantalla de
    reserva, filtradas por su estudiante (`pedidos_pendientes_de`). Esta función
    devuelve las de todo el colegio, que no es asunto suyo.
    ─────────────────────────────────────────────────────────────────────────

    **No filtra por día.** Ninguna historia dice hasta cuándo vale una reserva, y
    el sistema no sabe anularlas (`EstadoDelPedido` tiene dos estados y ninguno
    es «caducado»). Una reserva de anteayer sin recoger **sigue pendiente**, y
    esconderla la dejaría pagada y olvidada. Si algún día se decide que caducan,
    eso es una decisión de alcance con su historia, no un `filter` aquí.

    **Tampoco esconde los pedidos que hoy no se pueden entregar.** Un estudiante
    desactivado o de baja no retira (`INVD-2`), y su pedido sigue aquí: está
    pagado y sin anular, así que quitarlo lo volvería invisible — justo lo que no
    conviene con dinero de por medio. La pantalla lo **marca** en vez de
    esconderlo, preguntándole al estudiante que viene en `select_related`.

    Que un pedido así **no tiene salida hoy** es un punto abierto declarado en el
    `ANEXO B` de `./docs/decisiones-de-alcance.md` —no se decidió si se devuelve
    el saldo, si queda pendiente o si se anula—. Esto lo hace visible en vez de
    resolverlo por su cuenta.
    """
    from cuentas.models import Rol
    from ventas.models import EstadoDelPedido, PedidoAnticipado

    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Consultar las reservas exige identificarse.")
    if actor.rol not in (Rol.CAJERO, Rol.ADMINISTRADOR):
        raise PermissionDenied(
            "Consultar las reservas pendientes es del personal de la cafetería "
            "—cajero y administración— y de ningún otro rol ([S11], HU-24)."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")

    return (
        PedidoAnticipado.objects.filter(estado=EstadoDelPedido.PENDIENTE)
        # `venta__estudiante` no es adorno: la pantalla pregunta a cada
        # estudiante si puede retirar (`INVD-2`), y sin traerlo aquí serían
        # tantas consultas como reservas.
        .select_related("venta", "venta__estudiante")
        .prefetch_related("venta__lineas__producto")
        .order_by("creado_en")
    )


def efectivo_esperado_de(fecha):
    """Lo que la caja debería tener de una jornada: sus ventas en efectivo.

    `TT-172`, `HU-55`, `INVD-5`. Es **la** cifra de la historia, y sale del
    libro de ventas tal cual: no hay tabla de recaudo que alguien tenga que
    mantener al día, igual que no hay columna `saldo` ni columna `existencias`
    (`DT-4`, `DT-5`).

    ── QUÉ ENTRA Y QUÉ NO ──────────────────────────────────────────────────
    Entra `MedioDePago.EFECTIVO` y nada más.

    · **La transferencia queda fuera** (`DEC-6`, `DEC-1`): va de la app bancaria
      del cliente a la cuenta de la cafetería y **ese dinero nunca pasó por el
      cajón**. Sumarla haría que todo cierre diera un faltante igual a lo
      transferido, y el motivo obligatorio de `HU-55` se llenaría de «faltan las
      transferencias» hasta dejar de significar nada.
    · **La billetera también** (`HU-54`): la compra de un estudiante descuenta
      saldo, no billetes. El dinero entró el día de la recarga y ni siquiera
      entonces fue efectivo — la recarga es simulada (`ALC-OUT-01`).

    Las **reservas** no necesitan regla propia y por eso no la tienen: son
    siempre de un estudiante, así que son siempre de billetera (`DT-32`,
    `venta_medio_de_pago_segun_el_cliente`) y el filtro por efectivo las deja
    fuera solo.
    ─────────────────────────────────────────────────────────────────────────

    **No autoriza a nadie**, como `saldo_de` y por el mismo motivo: la llaman el
    servicio de cierre —que ya exigió el rol— y el selector de la pantalla. La
    autorización va en quien llama.

    Devuelve `Decimal("0.00")` cuando no hubo ninguna venta en efectivo. Aquí sí
    es un cero de verdad y no un hueco: la caja tenía que tener cero, y el
    cajero cuenta lo mismo con ventas que sin ellas.
    """
    from ventas.models import MedioDePago, Venta

    # Rango sobre la columna y no `creado_en__date`, por lo mismo que en
    # `ventas_registradas`: `__date` envuelve la columna en una función y deja
    # fuera el índice `venta_por_fecha`.
    inicio = timezone.make_aware(datetime.combine(fecha, time.min))
    fin = timezone.make_aware(datetime.combine(fecha + timedelta(days=1), time.min))

    total = (
        Venta.objects.filter(
            medio_pago=MedioDePago.EFECTIVO, creado_en__gte=inicio, creado_en__lt=fin
        ).aggregate(total=Sum(IMPORTE_DE_LA_LINEA))
    )["total"]

    return total or Decimal("0.00")


@dataclass(frozen=True)
class InformacionDelCierre:
    """Lo que el cajero ve antes de contar el dinero (`TT-173`, `HU-55`).

    `cierre` es el de la jornada si ya se cerró, y `None` si no. Se trae junto
    con el esperado y no en una consulta aparte porque la pantalla hace **una**
    pregunta —«¿cómo va la caja de hoy?»— y las dos mitades de la respuesta se
    leen juntas: ofrecer el formulario de un cierre ya hecho sería invitar a un
    error que la base va a rechazar (`cierre_de_caja_uno_por_jornada`).
    """

    fecha: object
    efectivo_esperado: Decimal
    ventas_en_efectivo: int
    cierre: object

    @property
    def ya_esta_cerrada(self):
        return self.cierre is not None


def informacion_del_cierre(*, actor, fecha=None):
    """El esperado de la jornada y su cierre, si ya lo hay (`TT-173`, `HU-55`).

    ── LA AUTORIZACIÓN VIVE AQUÍ, COMO EN `informacion_de_cobro` ───────────
    Este es el único camino por el que el recaudo en efectivo del día llega a
    una pantalla, así que exige el rol aunque alguien escriba la URL a mano
    (`DT-11`, `INV-4`). `efectivo_esperado_de` no autoriza a propósito: el
    servicio de cierre también lo consulta, y ahí el rol ya se comprobó.

    **Cerrar la caja es del cajero.** `HU-55` es de `USR-3` y `DEC-6` la
    describe como lo que hace quien cuenta el dinero al terminar la jornada. La
    administración no cuadra la caja: **consulta** los cierres, que es `HU-56` y
    es otra pantalla.
    ─────────────────────────────────────────────────────────────────────────

    `fecha` se recibe y no se lee del reloj, por lo que `CLAUDE.md` deja escrito
    de las pruebas de ventana: un selector que mira `timezone.now()` falla solo
    una madrugada y nadie sabe por qué. Quien no la pasa obtiene la jornada de
    hoy en la zona local, que es lo que hace la vista.
    """
    from cuentas.models import Rol
    from ventas.models import CierreDeCaja, MedioDePago, Venta

    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Cerrar la caja exige identificarse.")
    if actor.rol != Rol.CAJERO:
        raise PermissionDenied(
            "Cuadrar la caja es del rol cajero, y de ningún otro (HU-55, DEC-6)."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")

    if fecha is None:
        fecha = timezone.localdate()

    inicio = timezone.make_aware(datetime.combine(fecha, time.min))
    fin = timezone.make_aware(datetime.combine(fecha + timedelta(days=1), time.min))

    return InformacionDelCierre(
        fecha=fecha,
        efectivo_esperado=efectivo_esperado_de(fecha),
        # Cuántas ventas componen esa cifra. Es lo que convierte el esperado en
        # algo que se puede comprobar en vez de creer: `INVD-5` pide que se
        # **explique** desde las ventas registradas, y «$84.000 de 12 ventas en
        # efectivo» invita a ir a mirarlas.
        ventas_en_efectivo=Venta.objects.filter(
            medio_pago=MedioDePago.EFECTIVO, creado_en__gte=inicio, creado_en__lt=fin
        ).count(),
        cierre=CierreDeCaja.objects.filter(fecha=fecha).select_related("cajero").first(),
    )
