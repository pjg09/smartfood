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
from restricciones.selectors import (
    RestriccionesVigentes,
    identificadores_de_alergenos_bloqueados,
    identificadores_de_productos_bloqueados,
    limite_diario_de,
    restricciones_vigentes,
)

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
            "El saldo de un estudiante solo se le muestra al cajero, al cobrar."
        )
    if not actor.is_active:
        raise PermissionDenied(
            "Tu cuenta está desactivada. Pide a la institución educativa que la reactive."
        )

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
        # por su propia puerta: el acudiente en `INT-1`, la cafetería en `INT-3`
        # (`TT-111`, `estudiantes_con_sus_restricciones`) y la institución en la
        # ficha del padrón (`DT-43`, `DEC-21`).
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


def sin_pedidos_cancelados(consulta, *, venta="venta__"):
    """La misma consulta sin lo que pertenece a un pedido cancelado (`DT-48`).

    **Un pedido cancelado no es una venta ni un consumo** (`DEC-24`): se cobró
    y se devolvió, y el estudiante no recibió nada. Esta es la única definición
    de esa regla, y la aplican el cupo del día, el reporte de ventas, el panel
    de la cafetería, la frecuencia y los agregados. Dos copias de un `exclude`
    acaban discrepando en la tercera pantalla.

    `venta` es el camino desde el modelo de la consulta hasta la venta:
    `"venta__"` para las líneas y los movimientos de billetera, `""` para las
    propias ventas.

    `exclude` sobre un uno a uno inverso **conserva las ventas sin pedido** —las
    del mostrador—: Django lo traduce a un `NOT IN` sobre los pedidos
    cancelados, no a un `JOIN` que las dejaría fuera por tener el lado nulo.
    """
    from ventas.models import EstadoDelPedido

    return consulta.exclude(
        **{f"{venta}pedido_anticipado__estado": EstadoDelPedido.CANCELADO}
    )


def catalogo_para_reservar(estudiante):
    """Lo que hoy se puede reservar para **este** estudiante (`TT-145`, `DEC-24`).

    **Sin existencias, y no es un olvido**: la reserva es un encargo que la
    cafetería prepara a partir de la cola, no un apartado de lo que hay en la
    vitrina (`DT-47`). Ni las enseña ni las comprueba.

    Cada producto lleva lo que la tarjeta necesita para decir **antes** de
    añadirlo que no se va a poder: `bloqueado` si su acudiente lo bloqueó
    (`HU-10`) y `contiene_bloqueados` con los nombres de los alérgenos
    bloqueados que declara (`HU-11`). **Es aviso, no autorización**: quien
    rechaza es `reservar`, que cruza las restricciones dentro del bloqueo y en
    el momento de cobrar (`INV-5`, `DT-7`). Aquí no se guarda ninguna lista:
    se cruza al pintar, con dos consultas para todo el catálogo.

    `alergenos_declarados` sirve también al filtro «Sin …» de la pantalla.
    Ordenado por categoría y nombre, como la carta que es.
    """
    productos = list(
        productos_en_el_catalogo()
        .prefetch_related("alergenos")
        .order_by("categoria__nombre", "nombre")
    )
    productos_bloqueados = identificadores_de_productos_bloqueados(estudiante)
    alergenos_bloqueados = identificadores_de_alergenos_bloqueados(estudiante)

    for producto in productos:
        producto.alergenos_declarados = list(producto.alergenos.all())
        producto.bloqueado = producto.id in productos_bloqueados
        producto.contiene_bloqueados = [
            alergeno.nombre
            for alergeno in producto.alergenos_declarados
            if alergeno.id in alergenos_bloqueados
        ]
        producto.se_puede_reservar = not (
            producto.bloqueado or producto.contiene_bloqueados
        )
    return productos


@dataclass(frozen=True)
class ResumenDeLaReserva:
    """El ticket de una reserva todavía sin enviar (`DEC-24`).

    **Lo calcula el servidor a cada cambio de cantidad**, y no el navegador: el
    dinero se escribe en un solo sitio (`billetera/templatetags/dinero.py`), y
    una suma en JavaScript sería el segundo. Tampoco hay carrito en sesión: las
    cantidades viajan en la propia petición, así que no queda estado a medias.

    `saldo_despues` puede ser negativo, y eso es exactamente lo que la pantalla
    tiene que decir antes de que el cobro lo rechace (`INV-1`). Lo mismo
    `supera_el_cupo` con el límite diario (`HU-20`): **es aviso**, quien rechaza
    es `reservar`.
    """

    lineas: tuple
    total: Decimal
    kcal: int
    lineas_sin_kcal: int
    saldo: Decimal
    saldo_despues: Decimal
    cupo_restante: object
    supera_el_cupo: bool

    @property
    def alcanza(self):
        return self.saldo_despues >= 0

    @property
    def faltan(self):
        """Cuánto le falta al saldo, en positivo, o cero si alcanza."""
        return max(-self.saldo_despues, Decimal("0.00"))


def resumen_de_la_reserva(estudiante, cantidades):
    """`ResumenDeLaReserva` de `{id_de_producto: unidades}`.

    Solo cuenta productos del catálogo: un identificador que no es de ninguno
    —o de uno retirado— se ignora, igual que en `lineas_del_carrito`. Las
    calorías son las que el producto declara hoy (`energia_kcal`); las de un
    producto sin ese dato no se inventan, se cuentan aparte para decirlo.
    """
    productos = {
        p.id: p
        for p in productos_en_el_catalogo().filter(id__in=list(cantidades))
    }
    lineas = []
    total = Decimal("0.00")
    kcal = 0
    sin_kcal = 0
    for producto_id, cantidad in cantidades.items():
        producto = productos.get(producto_id)
        if producto is None or cantidad <= 0:
            continue
        importe = producto.precio * cantidad
        total += importe
        if producto.energia_kcal is None:
            sin_kcal += 1
            kcal_linea = None
        else:
            kcal_linea = producto.energia_kcal * cantidad
            kcal += kcal_linea
        lineas.append(
            {"producto": producto, "cantidad": cantidad, "importe": importe, "kcal": kcal_linea}
        )
    lineas.sort(key=lambda linea: linea["producto"].nombre)

    saldo = saldo_de(estudiante)
    limite = limite_diario_de(estudiante)
    cupo_restante = None
    if limite is not None:
        cupo_restante = max(limite.monto - consumo_del_dia(estudiante), Decimal("0.00"))

    return ResumenDeLaReserva(
        lineas=tuple(lineas),
        total=total,
        kcal=kcal,
        lineas_sin_kcal=sin_kcal,
        saldo=saldo,
        saldo_despues=saldo - total,
        cupo_restante=cupo_restante,
        supera_el_cupo=cupo_restante is not None and total > cupo_restante,
    )


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


def pedidos_de(estudiante):
    """Todos los pedidos anticipados de un estudiante (`HU-65`, `DEC-24`).

    Por recoger, entregados y cancelados, **del más reciente al más antiguo**:
    esto sí es un historial, al revés que la cola de la cafetería. Con las
    líneas y quién canceló ya traídos, porque la pantalla enseña lo que lleva
    cada uno y, del cancelado, quién y por qué.

    **No autoriza a nadie**, como `pedidos_pendientes_de`: quien la llama ya
    pasó por `estudiante_a_cargo`, que es donde vive la regla de que los
    pedidos de un estudiante solo los ve su acudiente (`DT-11`).

    Devuelve una lista, y cada pedido con su `numero`, sus `kcal` y su `total`
    —lo que se cobró y, si se canceló, lo que se devolvió—, calculados sobre las
    líneas ya traídas: sin consulta por pedido (`_completar_el_pedido`).
    """
    from ventas.models import PedidoAnticipado

    pedidos = list(
        PedidoAnticipado.objects.filter(venta__estudiante=estudiante)
        .select_related("venta", "cancelado_por")
        .prefetch_related("venta__lineas__producto")
        .order_by("-creado_en")
    )
    for numero, pedido in zip(range(len(pedidos), 0, -1), pedidos):
        _completar_el_pedido(pedido, numero)
    return pedidos


def _completar_el_pedido(pedido, numero):
    """Lo que la lista y la ficha de un pedido enseñan además de la venta.

    `numero` es su orden entre los pedidos del estudiante, empezando por el más
    antiguo: «Pedido #3» se lee mejor que un UUID, y no cambia nunca, porque un
    pedido no se borra (`INV-2`). `kcal` sale de la instantánea de cada línea
    (`DT-8`): lo que el producto declaraba al reservarse, no hoy.
    """
    from ventas.services import total_de

    lineas = list(pedido.venta.lineas.all())
    pedido.numero = numero
    pedido.total = total_de(pedido.venta)
    pedido.kcal = sum(
        linea.energia_kcal * linea.cantidad
        for linea in lineas
        if linea.energia_kcal is not None
    )
    return pedido


def pedido_de(estudiante, pedido_id):
    """Un pedido del estudiante, con su número, o `PedidoAnticipado.DoesNotExist`.

    Se busca **dentro** del estudiante: un pedido de otro no se alcanza ni
    sabiendo su identificador. Quien llama ya pasó por `estudiante_a_cargo`.
    """
    from ventas.models import PedidoAnticipado

    pedido = (
        PedidoAnticipado.objects.filter(venta__estudiante=estudiante)
        .select_related("venta__estudiante", "cancelado_por")
        .prefetch_related("venta__lineas__producto")
        .get(pk=pedido_id)
    )
    numero = PedidoAnticipado.objects.filter(
        venta__estudiante=estudiante, creado_en__lte=pedido.creado_en
    ).count()
    return _completar_el_pedido(pedido, numero)


def _personal_de_la_cafeteria(actor):
    """La puerta de las lecturas de pedidos de la cafetería (`HU-24`, `HU-68`).

    El cajero y la administración, con la cuenta activa. Lo que cada uno ve
    dentro lo decide quien llama: el cajero solo lo que está por recoger.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Consultar las reservas exige identificarse.")
    if actor.rol not in (Rol.CAJERO, Rol.ADMINISTRADOR):
        raise PermissionDenied(
            "Las reservas pendientes solo las consulta el personal de la "
            "cafetería: el cajero y la administración."
        )
    if not actor.is_active:
        raise PermissionDenied(
            "Tu cuenta está desactivada. Pide a la institución educativa que la reactive."
        )


def _solo_la_administracion_ve_lo_cerrado(actor):
    """Lo entregado y lo cancelado es un reporte de ventas (`HU-68`, `[S11]`).

    `[S11]` le da a la administración «consultar reportes de ventas» y al cajero
    no: él prepara y entrega lo que está **por recoger** (`HU-24`, `HU-25`).
    Enseñarle el historial ampliaría la matriz sin una decisión que lo diga.
    """
    if actor.rol != Rol.ADMINISTRADOR:
        raise PermissionDenied(
            "Los pedidos entregados y cancelados solo los consulta la "
            "administración de la cafetería; el cajero ve lo que está por recoger."
        )


# Los filtros de la pantalla de pedidos de la cafetería (`HU-68`), en el orden de
# sus pestañas. La clave es lo que viaja en la URL —`?ver=entregados`— y el valor,
# el estado que filtra; `None` es «todos».
FILTROS_DE_PEDIDOS = {
    "todos": None,
    "por-recoger": "pendiente",
    "entregados": "entregado",
    "cancelados": "cancelado",
}


def _con_su_numero(consulta):
    """Anota a cada pedido su número **entre los de su estudiante**.

    Es el mismo «Pedido #3» que el acudiente ve en su pantalla (`HU-65`): si la
    cafetería numerara a todo el colegio seguido, la misma reserva tendría dos
    números y una llamada sobre «el pedido 3» no se entendería. Junto al nombre
    del estudiante, el número no es ambiguo.

    Es una subconsulta y no un `enumerate` en Python porque la lista llega
    **filtrada**: contar sobre lo que se enseña renumeraría al cambiar de
    pestaña.
    """
    from django.db.models import Count, OuterRef, Subquery

    from ventas.models import PedidoAnticipado

    anteriores = (
        PedidoAnticipado.objects.filter(
            venta__estudiante=OuterRef("venta__estudiante"),
            creado_en__lte=OuterRef("creado_en"),
        )
        .order_by()
        .values("venta__estudiante")
        .annotate(cuantos=Count("pk"))
        .values("cuantos")
    )
    return consulta.annotate(numero_del_estudiante=Subquery(anteriores))


def _del_estudiante_buscado(consulta, busqueda):
    """Estrecha los pedidos a los del estudiante buscado (`DT-58`).

    Lo que llega es lo que el cajero escribió **o lo que el lector tecleó**, y
    se prueba en ese orden: el código de una tarjeta, el documento y, si no es
    ninguno, una parte del nombre.

    **La tarjeta y el documento, exactos**: son los mismos selectores de la caja
    (`HU-15`, `HU-16`), con su normalización. Un documento parcial sería el
    listado de menores que `identificar_por_documento` se niega a dar. El nombre
    sí va por una parte —«Julián» encuentra a Julián Amariles—, y no descubre
    nada: los nombres ya están en la lista que se está filtrando.
    """
    from personas.models import Estudiante
    from personas.selectors import identificar_por_codigo_de_tarjeta, identificar_por_documento

    busqueda = (busqueda or "").strip()
    if not busqueda:
        return consulta
    for identificar in (identificar_por_codigo_de_tarjeta, identificar_por_documento):
        try:
            return consulta.filter(venta__estudiante=identificar(busqueda))
        except Estudiante.DoesNotExist:
            pass
    return consulta.filter(venta__estudiante__nombre__icontains=busqueda)


def pedidos_de_la_cafeteria(*, actor, filtro, busqueda=""):
    """Los pedidos de todo el colegio, filtrados por estado (`HU-68`, `HU-24`).

    `filtro` es una clave de `FILTROS_DE_PEDIDOS`. **El cajero solo pide
    `por-recoger`**; cualquier otro filtro es de la administración.

    ── EL ORDEN DEPENDE DEL FILTRO, Y ES A PROPÓSITO ──────────────────────
    Un historial se lee empezando por lo último, y por eso el de la billetera,
    el del inventario y el de restricciones llegan así; aquí, «todos»,
    «entregados» y «cancelados». **Lo que está por recoger no es un historial:
    es una cola de trabajo**, y va del más antiguo al más reciente. Lo que el
    personal necesita saber es qué lleva más tiempo esperando.
    ─────────────────────────────────────────────────────────────────────────

    ── QUIÉN PUEDE, Y POR QUÉ SON DOS ROLES ───────────────────────────────
    `HU-24` los nombra a los dos: `USR-3` y `USR-4`. `FUN-5` explica por qué —«el
    personal de la cafetería consulta las reservas pendientes y registra su
    entrega»—: quien prepara y quien entrega no tienen que ser la misma persona.
    La autorización vive aquí y no en la vista: es el único camino por el que
    los pedidos llegan a la pantalla de la cafetería, y exige el rol aunque
    alguien escriba la URL a mano (`DT-11`, `INV-4`).

    **El acudiente no entra por aquí.** Los suyos los ve en su pantalla de
    reserva, filtrados por su estudiante (`pedidos_de`).
    ─────────────────────────────────────────────────────────────────────────

    **No filtra por día.** Ninguna historia dice hasta cuándo vale una reserva, y
    las reservas no caducan solas (`DEC-24`). Una de anteayer sin recoger
    **sigue pendiente** hasta que se entrega o alguien la cancela.

    **Tampoco esconde los pedidos que hoy no se pueden entregar.** Un estudiante
    desactivado o de baja no retira (`INVD-2`), y su pedido sigue aquí para que
    la pantalla lo marque; su salida es cancelarlo, porque una devolución no es
    una recarga (`DEC-24`, `HU-67`).

    `busqueda` es el buscador de la vista del cajero (`DT-58`), y **solo
    estrecha la lista**: ver `_del_estudiante_buscado`.

    Cada pedido llega con `numero`, `total` y `kcal` (`_completar_el_pedido`),
    con las líneas, el estudiante y quién canceló ya traídos: la lista no hace
    una consulta por fila.
    """
    from ventas.models import PedidoAnticipado

    _personal_de_la_cafeteria(actor)
    if filtro not in FILTROS_DE_PEDIDOS:
        raise ValueError(f"No hay ningún filtro de pedidos llamado «{filtro}».")
    if filtro != "por-recoger":
        _solo_la_administracion_ve_lo_cerrado(actor)

    consulta = _con_su_numero(
        PedidoAnticipado.objects.select_related("venta__estudiante", "cancelado_por")
        .prefetch_related("venta__lineas__producto")
    )
    if FILTROS_DE_PEDIDOS[filtro] is not None:
        consulta = consulta.filter(estado=FILTROS_DE_PEDIDOS[filtro])
    consulta = _del_estudiante_buscado(consulta, busqueda)
    consulta = consulta.order_by("creado_en" if filtro == "por-recoger" else "-creado_en")

    return [_completar_el_pedido(pedido, pedido.numero_del_estudiante) for pedido in consulta]


def pedido_de_la_cafeteria(*, actor, pedido_id):
    """Un pedido cualquiera, para la modal de la cafetería (`HU-68`, `HU-67`).

    O `PedidoAnticipado.DoesNotExist`. **El cajero solo abre uno por recoger**:
    el detalle de uno entregado o cancelado es el mismo historial que la lista
    no le enseña, y no puede alcanzarse escribiendo la URL.
    """
    from ventas.models import PedidoAnticipado

    _personal_de_la_cafeteria(actor)
    pedido = (
        _con_su_numero(PedidoAnticipado.objects.all())
        .select_related("venta__estudiante", "cancelado_por", "entregado_por")
        .prefetch_related("venta__lineas__producto")
        .get(pk=pedido_id)
    )
    if not pedido.esta_pendiente:
        _solo_la_administracion_ve_lo_cerrado(actor)
    return _completar_el_pedido(pedido, pedido.numero_del_estudiante)


@dataclass(frozen=True)
class TableroDeReservas:
    """Las cifras de arriba de la pantalla de pedidos (`HU-68`).

    `pedidos` y `reservado` son `None` para el cajero: son historial —cuánto se
    ha pedido y cobrado desde siempre— y ese es de la administración (`[S11]`).
    """

    por_recoger: int
    falta_por_entregar: list
    pedidos: int | None
    reservado: Decimal | None


def tablero_de_reservas(*, actor):
    """Cuántos pedidos hay, cuántos esperan, cuánto se cobró y qué preparar.

    **`falta_por_entregar` es lo que `HU-24` existe para responder**: la suma,
    producto por producto, de lo que llevan los pedidos por recoger. Es lo que
    hay que tener listo, sin ir sumando fila por fila. Del más pedido al menos,
    con su `porcentaje` frente al primero para el medidor (`[S2.8]`).

    **`reservado` no cuenta lo cancelado**: ese importe volvió a la billetera
    (`DEC-24`), así que sumarlo diría que la cafetería cobró algo que devolvió.
    """
    from ventas.models import EstadoDelPedido, LineaVenta, PedidoAnticipado, Venta

    _personal_de_la_cafeteria(actor)

    filas = list(
        LineaVenta.objects.filter(venta__pedido_anticipado__estado=EstadoDelPedido.PENDIENTE)
        .values("producto", "producto__nombre")
        .annotate(unidades=Sum("cantidad"))
        .order_by("-unidades", "producto__nombre")
    )
    tope = filas[0]["unidades"] if filas else 0
    falta_por_entregar = [
        {
            "nombre": fila["producto__nombre"],
            "unidades": fila["unidades"],
            "porcentaje": round(100 * fila["unidades"] / tope),
        }
        for fila in filas
    ]
    por_recoger = PedidoAnticipado.objects.filter(estado=EstadoDelPedido.PENDIENTE).count()

    if actor.rol != Rol.ADMINISTRADOR:
        return TableroDeReservas(por_recoger, falta_por_entregar, None, None)

    reservado = Venta.objects.filter(
        pedido_anticipado__estado__in=(EstadoDelPedido.PENDIENTE, EstadoDelPedido.ENTREGADO)
    ).aggregate(total=Sum(IMPORTE_DE_LA_LINEA))["total"]
    return TableroDeReservas(
        por_recoger,
        falta_por_entregar,
        PedidoAnticipado.objects.count(),
        reservado or Decimal("0.00"),
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
            "Solo el cajero puede cuadrar la caja."
        )
    if not actor.is_active:
        raise PermissionDenied(
            "Tu cuenta está desactivada. Pide a la institución educativa que la reactive."
        )

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
