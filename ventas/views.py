"""Vistas del punto de venta (`INT-2`).

Solo HTTP: parsear la petición, delegar en un servicio o un selector, y
renderizar. **Cero lógica de negocio** (`DT-15`).

Una vista HTMX devuelve **un fragmento, nunca una página** (`DT-16`).
"""

import uuid
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from billetera.selectors import saldo_de
from billetera.templatetags.dinero import dinero
from cuentas.models import Rol
from personas.models import Estudiante
from personas.selectors import (
    estudiante_a_cargo,
    identificar_por_codigo_de_tarjeta,
    identificar_por_documento,
)
from personas.services import EstudianteNoOperativo
from ventas import carrito as carrito_de_la_venta
from ventas.carrito import devuelta as devuelta_de_la_venta
from ventas.carrito import leer_dinero
from ventas.selectors import (
    catalogo_de_venta,
    catalogo_para_reservar,
    informacion_de_cobro,
    informacion_del_cierre,
    lineas_del_carrito,
    pedido_de,
    pedidos_de,
    FILTROS_DE_PEDIDOS,
    pedido_de_la_cafeteria,
    pedidos_de_la_cafeteria,
    pedidos_pendientes_de,
    resumen_de_la_reserva,
    tablero_de_reservas,
)
from ventas.models import EstadoDelPedido, MedioDePago, PedidoAnticipado
from ventas.services import (
    CierreRechazado,
    VentaRechazada,
    cancelar_pedido,
    cerrar_caja,
    entregar,
    registrar_venta,
    reservar,
    total_de,
)


def _solo_el_cajero(usuario):
    """`[S11]`: registrar ventas es de `USR-3` y de nadie más.

    Se escribe una vez y la usan las dos vistas del punto de venta: con la
    comprobación repetida, la segunda que se añada se olvidará.
    """
    if usuario.rol != Rol.CAJERO:
        raise PermissionDenied(
            "El punto de venta es exclusivo del rol cajero: [S11] no concede "
            "registrar ventas a ningún otro rol."
        )


@login_required
@require_http_methods(["GET"])
def punto_de_venta(request):
    """La pantalla del punto de venta (`TT-57`, `TT-58`, `INT-2`).

    **Solo el cajero.** `[S11]` concede «registrar ventas en el punto de venta»
    a `USR-3` y a nadie más: ni la administración de la cafetería ni la
    institución cobran. Cualquier otro rol recibe `403`, también con la sesión
    abierta y aunque llegue escribiendo la URL.

    La comprobación está aquí y **no en la plantilla**. `DT-11` es explícito: el
    control de acceso es de la capa de datos, no del layout. Esconder el enlace
    dejaría la pantalla accesible a quien conozca la ruta, que es justo la clase
    de puerta trasera que `INV-4` no admite.

Esta vista **no cierra ninguna historia**: es el sitio donde ocurren las
    demás. Identificar al estudiante es `HU-15` y `HU-16`, ver su saldo y sus
    restricciones es `HU-17`, y la venta en sí es `HU-21` — las cuatro están
    construidas y viven aquí dentro.
    """
    _solo_el_cajero(request.user)

    return render(
        request,
        "ventas/punto-de-venta.html",
        {"productos": _catalogo_con_la_venta(request), **_contexto_del_ticket(request)},
    )


def _catalogo_con_la_venta(request, solo=None):
    """El catálogo con `en_la_venta` en cada producto: cuántas unidades lleva la
    venta en curso (`DT-57`). Es lo que decide si la tarjeta ofrece «Añadir» o
    «− n +».

    Con `solo`, el producto de ese identificador y nada más, o `None`: es la
    tarjeta que se repinta fuera de banda tras tocar el carrito.
    """
    carrito = carrito_de_la_venta.leer(request.session)
    productos = catalogo_de_venta()
    for producto in productos:
        producto.en_la_venta = carrito.get(str(producto.id), 0)
    if solo is not None:
        return next((p for p in productos if str(p.id) == str(solo)), None)
    return productos


@login_required
@require_http_methods(["GET"])
def identificacion(request):
    """El estudiante de la tarjeta escaneada (`TT-71`, `HU-15`).

    **Devuelve un fragmento, nunca una página** (`DT-16`): lo pide el campo de
    escaneo del punto de venta cada vez que el lector envía Enter, y lo que cambia
    es una zona de la pantalla, no la pantalla.

    Los dos resultados —lo encontró o no— son el **mismo fragmento**, no dos
    rutas. Quien escanea no sabe de antemano cuál va a ser, y partirlo obligaría
    al campo a decidir a dónde pedir antes de saber qué hay.

    **Y las dos vías de entrada también son la misma ruta** (`TT-73`, `HU-16`).
    Con `codigo` viene del lector; con `documento`, de quien no trae la tarjeta.
    Eso no contradice `DT-16` —que prohíbe un endpoint que devuelva a veces una
    cosa y a veces otra—: aquí lo que cambia es por dónde se preguntó, no lo que
    se responde. Es literalmente el primer criterio de `HU-16`, «la búsqueda por
    documento es una alternativa al escaneo, **con el mismo resultado**»: con dos
    vistas, ese «mismo» dependería de que nadie las dejara divergir.

    **Y trae la información de cobro** (`TT-75`, `HU-17`): identificar al
    estudiante y mostrar su saldo son el mismo momento —el primer criterio de la
    historia dice «al identificar al estudiante se muestran los tres datos»—, así
    que son la misma petición. Partirlo en dos obligaría al campo de escaneo a
    encadenar una segunda llamada por cada tarjeta, que es tiempo que la caja no
    tiene.

    Quién puede ver ese saldo lo decide `informacion_de_cobro`, no esta vista: la
    regla de `[S11]` —el cajero lo ve **solo al cobrar**— vive en el selector
    (`DT-15`). Aquí solo se llama cuando hay a quién cobrarle.

    Lo que se dice además es **si el estudiante puede comprar**: identificar a
    alguien de baja y callarlo dejaría al cajero montando una venta que va a
    fallar al final (`INVD-2`).
    """
    _solo_el_cajero(request.user)

    codigo = request.GET.get("codigo", "").strip()
    documento = request.GET.get("documento", "").strip()

    estudiante = None
    try:
        if documento:
            estudiante = identificar_por_documento(documento)
        elif codigo:
            estudiante = identificar_por_codigo_de_tarjeta(codigo)
    except Estudiante.DoesNotExist:
        estudiante = None

    # `TT-81`. Quién es el cliente lo recuerda el servidor, no un campo oculto:
    # entre escanear y cobrar puede haber otro escaneo, y manda el último.
    carrito_de_la_venta.fijar_estudiante(request.session, estudiante)

    return render(
        request,
        "ventas/partials/estudiante-identificado.html",
        _contexto_del_estudiante(
            request, estudiante, codigo=codigo, documento=documento
        ),
    )


def _contexto_del_estudiante(request, estudiante, **extra):
    """Lo que necesita el panel del estudiante, en un solo sitio (`TT-150`).

    Lo arman dos vistas —la identificación y la entrega— y repetirlo es como una
    de las dos acaba enseñando un pedido que la otra ya entregó. Mismo motivo
    que `_contexto_del_ticket`.
    """
    return {
        "estudiante": estudiante,
        "cobro": (
            informacion_de_cobro(actor=request.user, estudiante=estudiante)
            if estudiante is not None
            else None
        ),
        # `HU-25`. Lo que este estudiante tiene reservado y sin recoger. Va con
        # la identificación y no en una segunda petición: es otro viaje por
        # tarjeta, y `INT-2` no lo tiene.
        "pedidos": (
            pedidos_pendientes_de(estudiante) if estudiante is not None else []
        ),
        **extra,
    }


def _estudiante_de_la_venta(request):
    """El estudiante al que se le está cobrando, o `None` si es genérica.

    Se resuelve contra la base en cada petición en lugar de guardar el objeto:
    entre escanear y cobrar puede haberse dado de baja, y lo que manda es el
    estado de ahora. Si el identificador guardado ya no existe, se trata como si
    no hubiera cliente — no como un error, porque no lo es para quien está en la
    caja.
    """
    identificador = carrito_de_la_venta.estudiante_id(request.session)
    if not identificador:
        return None
    return Estudiante.objects.filter(pk=identificador).first()


def _contexto_del_ticket(request, **extra):
    """Lo que necesita el fragmento del ticket, en un solo sitio.

    Lo arman tres vistas —la pantalla, el carrito y el cobro— y la
    identificación por añadidura. Repetirlo en cada una es como una de ellas
    acaba enseñando un total que no corresponde a sus líneas.
    """
    estudiante = _estudiante_de_la_venta(request)
    lineas, total = lineas_del_carrito(carrito_de_la_venta.leer(request.session))
    return {"estudiante": estudiante, "lineas": lineas, "total": total, **extra}


@login_required
@require_http_methods(["POST"])
def carrito(request):
    """Añade, descuenta o quita un renglón de la venta en curso (`TT-81`).

    **`POST` y no `GET`**: cambia el estado de la sesión, y un `GET` que cambia
    algo es un enlace que el navegador puede reproducir solo.

    Devuelve el **fragmento del ticket** y, fuera de banda, **la tarjeta del
    producto tocado** (`DT-57`): su «Añadir» o «− n +» cambia con el ticket. El
    catálogo entero no se repinta —sus existencias no cambian hasta que se
    cobre—, salvo al vaciar, que cambia todas las tarjetas a la vez.

    No comprueba existencias: montar el carrito no es cobrar. La cifra que decide
    se lee dentro del bloqueo, al confirmar (`DT-6`); avisar antes sería una
    promesa que otra caja puede romper entre este toque y el siguiente.
    """
    _solo_el_cajero(request.user)

    accion = request.POST.get("accion", "anadir")
    producto_id = request.POST.get("producto", "")

    if accion == "vaciar":
        carrito_de_la_venta.vaciar(request.session)
    elif accion == "quitar":
        carrito_de_la_venta.quitar(request.session, producto_id)
    elif accion == "descontar":
        carrito_de_la_venta.anadir(request.session, producto_id, -1)
    else:
        carrito_de_la_venta.anadir(request.session, producto_id, 1)

    # `DT-57`. La tarjeta del producto tocado cambia con el ticket —«Añadir» o
    # «− n +»—, así que viaja fuera de banda. Solo esa: el catálogo entero
    # costaría el doble de bytes en cada toque. Al vaciar, todas.
    if accion == "vaciar":
        fuera_de_banda = {"oob_catalogo": True, "productos": _catalogo_con_la_venta(request)}
    else:
        fuera_de_banda = {"oob_tarjeta": _catalogo_con_la_venta(request, solo=producto_id)}

    return render(
        request, "ventas/partials/ticket.html",
        _contexto_del_ticket(request, **fuera_de_banda),
    )


def _medio_de_la_confirmacion(estudiante, pedido):
    """El medio que se va a cobrar: con estudiante, siempre la billetera
    (`HU-54`); sin él, el elegido, o efectivo. La regla la impone la base
    (`venta_medio_de_pago_segun_el_cliente`); esto solo dice lo que va a pasar."""
    if estudiante is not None:
        return MedioDePago.BILLETERA
    if pedido in (MedioDePago.EFECTIVO, MedioDePago.TRANSFERENCIA):
        return pedido
    return MedioDePago.EFECTIVO


@login_required
@require_http_methods(["GET"])
def confirmacion_del_cobro(request):
    """La primera modal del cobro: qué se va a cobrar, a quién y cómo (`DT-57`).

    **No escribe nada.** Cerrarla es no cobrar. En efectivo lleva «Dinero
    recibido», que solo sirve para calcular la devuelta y no se guarda.
    """
    _solo_el_cajero(request.user)
    contexto = _contexto_del_ticket(request)
    medio = _medio_de_la_confirmacion(contexto["estudiante"], request.GET.get("medio_pago"))
    return render(request, "ventas/partials/confirmacion-del-cobro.html", {
        **contexto,
        "medio": medio,
        "etiqueta_del_medio": MedioDePago(medio).label,
        "en_efectivo": medio == MedioDePago.EFECTIVO,
    })


@login_required
@require_http_methods(["GET"])
def devuelta_del_cobro(request):
    """La devuelta mientras se escribe el dinero recibido (`DT-57`).

    La calcula el servidor, a cada tecla, contra el total de la venta en curso:
    el dinero se formatea en un solo sitio, y en JavaScript sería el segundo.
    """
    _solo_el_cajero(request.user)
    _, total = lineas_del_carrito(carrito_de_la_venta.leer(request.session))
    sobra, falta = devuelta_de_la_venta(total, leer_dinero(request.GET.get("recibido")))
    return render(request, "ventas/partials/devuelta.html", {"devuelta": sobra, "faltan": falta})


@login_required
@require_http_methods(["POST"])
def cobrar(request):
    """Confirma la venta (`TT-80`, `TT-81`, `HU-21`).

    **Se llama desde la primera modal** (`DT-57`): el botón del ticket ya no
    cobra, abre la confirmación. Responde la segunda modal —«Venta registrada»—
    o, si se rechaza, la modal con el motivo; y en los dos casos arrastra el
    ticket fuera de banda.

    La vista no decide nada: junta lo que hay en la sesión y llama al servicio,
    que es quien bloquea, valida y escribe dentro de una sola transacción
    (`DT-6`). Si el servicio rechaza, aquí solo se traduce el motivo a algo que
    el cajero pueda leer — **la venta no se ha escrito**, porque la transacción
    del servicio se deshizo entera.

    Devuelve el fragmento del ticket en sus dos estados —cobrada o rechazada—,
    que es la misma zona de la pantalla y por tanto el mismo fragmento. Cuando
    cobra, arrastra fuera de banda el panel del estudiante y el catálogo: la
    venta terminó, así que el cliente se olvida y las existencias ya son otras.
    """
    _solo_el_cajero(request.user)

    estudiante = _estudiante_de_la_venta(request)
    lineas = {
        producto_id: int(cantidad)
        for producto_id, cantidad in carrito_de_la_venta.leer(request.session).items()
    }

    try:
        venta = registrar_venta(
            actor=request.user,
            lineas=lineas,
            estudiante=estudiante,
            medio_pago=request.POST.get("medio_pago") or None,
        )
    except (VentaRechazada, EstudianteNoOperativo) as rechazo:
        # `TT-132`. Además del texto va la **etiqueta** del motivo, que la
        # plantilla pone en el bloque de rechazo. El texto es para el cajero; la
        # etiqueta es para que una prueba pueda exigir cuál se enseñó sin buscar
        # una frase dentro de otra — que es lo que se rompe en cuanto alguien
        # reescribe el mensaje.
        #
        # `TT-126` resolvió la etiqueta de `INVD-2` **por otro camino**: no
        # dándosela a `EstudianteNoOperativo` —que es de `personas` y no sabe de
        # tickets— sino traduciéndola en el servicio a `EstudianteNoPuedeComprar`,
        # que sí es una `VentaRechazada` y sí la trae. Así la regla se queda en
        # `personas` y la etiqueta, donde se pinta.
        #
        # Por eso `EstudianteNoOperativo` ya no llega hasta aquí por ningún
        # camino de venta: se sigue capturando como red, porque un camino nuevo
        # que olvide traducirla enseñaría un `500` en la caja en vez de un
        # rechazo con su motivo.
        # `DT-57`. La modal dice por qué no se cobró, y el ticket de detrás
        # también, para que siga a la vista al cerrarla. El carrito no se toca.
        return render(
            request,
            "ventas/partials/cobro-rechazado.html",
            _contexto_del_ticket(
                request,
                rechazo=" ".join(rechazo.messages)
                if hasattr(rechazo, "messages")
                else str(rechazo),
                motivo=getattr(rechazo, "motivo", "rechazo"),
                oob_ticket=True,
            ),
        )

    carrito_de_la_venta.vaciar(request.session)
    total_cobrado = total_de(venta)
    # La devuelta, contra **lo que se cobró de verdad** y no contra el total
    # estimado de la primera modal: el precio puede haber cambiado entre las dos.
    # El dinero recibido no se guarda (`DT-57`).
    sobra, falta = (
        devuelta_de_la_venta(total_cobrado, leer_dinero(request.POST.get("recibido")))
        if venta.medio_pago == MedioDePago.EFECTIVO
        else (None, None)
    )

    return render(
        request,
        "ventas/partials/venta-registrada.html",
        {
            **_contexto_del_ticket(request),
            "cobrada": venta,
            "renglones": list(venta.lineas.select_related("producto")),
            "total_cobrado": total_cobrado,
            "devuelta": sobra,
            "faltan": falta,
            "productos": _catalogo_con_la_venta(request),
            "oob_ticket": True,
            "oob_estudiante": True,
            "oob_catalogo": True,
        },
    )


@login_required
@require_http_methods(["POST"])
def cliente_generico(request):
    """Saca al estudiante de la venta en curso (`TT-89`, `HU-53`).

    **No enciende ningún modo: apaga la identificación.** Una venta a cliente
    genérico **es** una venta sin estudiante (`DEC-1`), y eso ya es un estado del
    modelo —`Venta.es_generica`—, no uno nuevo. Inventar aquí un interruptor de
    «modo genérico» crearía un tercer estado que la base no tiene, y tarde o
    temprano alguien lo encontraría encendido con un estudiante identificado.

    Existe porque sin ella no había vuelta atrás: identificado un estudiante por
    error, el siguiente cliente era un docente y la única salida era pasar una
    tarjeta que no fuera de nadie o recargar la página.

    `POST` porque cambia el estado de la sesión. Devuelve la columna del
    estudiante en su estado vacío y arrastra el medio de pago, que con cliente
    genérico vuelve a ser efectivo o transferencia (`HU-54`).
    """
    _solo_el_cajero(request.user)

    carrito_de_la_venta.fijar_estudiante(request.session, None)

    return render(request, "ventas/partials/cliente-generico.html")


def _cantidades_de(datos):
    """`{id_de_producto: unidades}` a partir de los campos `cantidad-<id>`.

    Trabajo de HTTP, así que vive aquí: el servicio y el selector reciben las
    cantidades ya limpias (`DT-15`). Lo que no es un entero o no es positivo se
    ignora al pintar el ticket; al reservar, `_cantidades_o_error` lo rechaza.
    """
    cantidades = {}
    for clave, crudo in datos.items():
        if not clave.startswith("cantidad-"):
            continue
        try:
            producto_id = uuid.UUID(clave.removeprefix("cantidad-"))
            cuantas = int((crudo or "").strip() or 0)
        except ValueError:
            continue
        if cuantas > 0:
            cantidades[producto_id] = cuantas
    return cantidades


def _cantidades_o_error(datos):
    """Como `_cantidades_de`, pero un valor que no es un entero es un error."""
    for clave, crudo in datos.items():
        if clave.startswith("cantidad-") and (crudo or "").strip():
            try:
                int(crudo.strip())
            except ValueError:
                return {}, "Las cantidades se escriben en números enteros."
    return _cantidades_de(datos), None


def _estudiante_del_acudiente(request, estudiante_id):
    try:
        return estudiante_a_cargo(usuario=request.user, estudiante_id=estudiante_id)
    except Estudiante.DoesNotExist:
        raise Http404("Ese estudiante no está a tu cargo.") from None


@login_required
@require_http_methods(["GET", "POST"])
def reserva(request, estudiante_id):
    """Pantalla de reserva anticipada de un estudiante a cargo (`TT-145`, `HU-23`).

    Tercer criterio de la historia: **se gestiona desde la aplicación del
    acudiente** (`INT-1`), así que vive aquí y no en el admin.

    **Una sola pantalla para reservar y para ver los pedidos** (`DEC-24`):
    arriba los filtros, debajo el catálogo con su ticket, y al final los pedidos
    del estudiante, que se abren en una modal donde se cancelan (`HU-65`,
    `HU-66`). Dos pantallas con el mismo dato acaban diciendo cosas distintas.

    **La autorización la hace el selector**, no un `if` de esta vista: un
    estudiante que no está a cargo de quien pregunta es un 404, igual que uno
    que no existe. El servicio vuelve a comprobar quién reserva (`DT-15`).

    ── NO HAY CARRITO EN SESIÓN, Y NO ES UN OLVIDO ────────────────────────
    El punto de venta lo tiene (`DT-26`) porque el cajero monta la venta gesto a
    gesto con una fila delante. Aquí las cantidades viven en el propio
    formulario: los botones «+» y «−» cambian un entero en el navegador, el
    ticket se pide al servidor con esas cantidades (`ticket_de_la_reserva`), y
    se envía una vez. Ningún estado queda a medias en el servidor.
    ─────────────────────────────────────────────────────────────────────────
    """
    estudiante = _estudiante_del_acudiente(request, estudiante_id)

    productos = catalogo_para_reservar(estudiante)
    error = None
    cantidades = {}

    if request.method == "POST":
        cantidades, error = _cantidades_o_error(request.POST)
        if error is None:
            try:
                reservar(actor=request.user, estudiante=estudiante, lineas=cantidades)
            except (VentaRechazada, EstudianteNoOperativo) as rechazo:
                # `200` con el motivo dentro de la pantalla, no un `400`: el
                # estado de la petición y lo que hay que enseñar son dos
                # preguntas distintas, y es el precedente del repositorio.
                error = "; ".join(rechazo.messages) if hasattr(rechazo, "messages") else str(rechazo)
            else:
                messages.success(
                    request,
                    f"Reserva pagada: {estudiante.nombre} la recoge en la "
                    f"cafetería con su tarjeta.",
                )
                return redirect("reserva", estudiante_id=estudiante.id)

    # Lo que se escribió se devuelve escrito, también tras un rechazo: se
    # adjunta al producto porque una plantilla no sabe indexar un diccionario
    # por una clave que sale de una variable.
    for producto in productos:
        producto.cantidad_pedida = cantidades.get(producto.id, 0)

    return render(
        request,
        "ventas/reserva.html",
        {
            "estudiante": estudiante,
            "productos": productos,
            "categorias": sorted(
                {p.categoria for p in productos}, key=lambda categoria: categoria.nombre
            ),
            "alergenos": sorted(
                {a for p in productos for a in p.alergenos_declarados},
                key=lambda alergeno: alergeno.nombre,
            ),
            "resumen": resumen_de_la_reserva(estudiante, cantidades),
            "pedidos": pedidos_de(estudiante),
            "error": error,
        },
    )


@login_required
@require_http_methods(["GET"])
def ticket_de_la_reserva(request, estudiante_id):
    """El ticket de la reserva para unas cantidades (`DEC-24`).

    **Un fragmento, nunca una página** (`DT-16`): lo pide la pantalla a cada
    «+» o «−», con las cantidades del formulario en la consulta. `GET` porque no
    escribe nada: calcula un resumen y lo devuelve. Las cifras las formatea el
    servidor, que es el único sitio donde se escribe el dinero.
    """
    estudiante = _estudiante_del_acudiente(request, estudiante_id)
    return render(
        request,
        "ventas/partials/ticket-de-la-reserva.html",
        {
            "estudiante": estudiante,
            "resumen": resumen_de_la_reserva(estudiante, _cantidades_de(request.GET)),
        },
    )


@login_required
@require_http_methods(["GET"])
def detalle_del_producto(request, estudiante_id, producto_id):
    """La ficha nutricional de un producto, para la modal (`DEC-24`).

    Con lo que ese estudiante tiene bloqueado, porque es lo que el acudiente
    viene a mirar: si puede llevarlo y qué declara. La abren la reserva y los
    productos bloqueados (`HU-10`), y es la misma en las dos. Fragmento
    (`DT-16`).
    """
    estudiante = _estudiante_del_acudiente(request, estudiante_id)
    producto = next(
        (p for p in catalogo_para_reservar(estudiante) if p.id == producto_id), None
    )
    if producto is None:
        raise Http404("Ese producto no está en el catálogo.")
    return render(
        request,
        "ventas/partials/detalle-del-producto.html",
        {"estudiante": estudiante, "producto": producto},
    )


@login_required
@require_http_methods(["GET"])
def pedidos_del_estudiante(request, estudiante_id):
    """La lista de pedidos del estudiante, como fragmento (`HU-65`, `DEC-24`).

    Vive dentro de la pantalla de reserva, y esta ruta es la que la repinta
    cuando un pedido se cancela: la modal responde con `HX-Trigger:
    pedidos-cambiado` y la lista se vuelve a pedir (`DT-40`). La autorización
    la hace `estudiante_a_cargo`: uno ajeno es un 404.
    """
    estudiante = _estudiante_del_acudiente(request, estudiante_id)
    return render(
        request,
        "ventas/partials/pedidos-del-estudiante.html",
        {"estudiante": estudiante, "pedidos": pedidos_de(estudiante)},
    )


def _pedido_del_estudiante(estudiante, pedido_id):
    try:
        return pedido_de(estudiante, pedido_id)
    except PedidoAnticipado.DoesNotExist:
        raise Http404("Ese pedido no existe.") from None


@login_required
@require_http_methods(["GET"])
def detalle_del_pedido(request, estudiante_id, pedido_id):
    """El detalle de un pedido en la modal, con su cancelación si procede.

    `HU-65` y `HU-66`. Fragmento (`DT-16`). El pedido se busca **dentro** del
    estudiante a cargo: uno de otro estudiante es un 404 aunque exista.
    """
    estudiante = _estudiante_del_acudiente(request, estudiante_id)
    return render(
        request,
        "ventas/partials/detalle-del-pedido.html",
        {"estudiante": estudiante, "pedido": _pedido_del_estudiante(estudiante, pedido_id)},
    )


@login_required
@require_http_methods(["POST"])
def cancelacion_por_el_acudiente(request, estudiante_id, pedido_id):
    """El acudiente cancela un pedido desde su modal (`HU-66`, `DT-48`).

    **Devuelve la misma modal**, con el error o ya cancelada (`DT-16`): lo que
    quedara fuera del fragmento no se intercambiaría. Si se canceló, la
    respuesta lleva `HX-Trigger: pedidos-cambiado`, y la lista y el ticket —que
    enseña el saldo— se vuelven a pedir solos (`DT-40`).

    Quién puede lo decide el servicio; un rechazo vuelve en `200` con su motivo
    dentro, porque HTMX no intercambia lo que llega en `4xx`.
    """
    estudiante = _estudiante_del_acudiente(request, estudiante_id)
    pedido = _pedido_del_estudiante(estudiante, pedido_id)

    error = None
    motivo = request.POST.get("motivo", "")
    try:
        cancelar_pedido(actor=request.user, pedido=pedido, motivo=motivo)
    except ValidationError as rechazo:
        error = " ".join(rechazo.messages)

    respuesta = render(
        request,
        "ventas/partials/detalle-del-pedido.html",
        {
            "estudiante": estudiante,
            "pedido": _pedido_del_estudiante(estudiante, pedido_id),
            "error": error,
            "motivo": motivo if error else "",
            "recien_cancelado": error is None,
        },
    )
    if error is None:
        respuesta["HX-Trigger"] = "pedidos-cambiado"
    return respuesta


def _pedido_en_la_cafeteria(request, pedido_id):
    """El pedido para la modal de la cafetería, o un 404 (`HU-68`).

    Quién lo puede abrir lo decide el selector: el cajero solo uno por recoger.
    """
    try:
        return pedido_de_la_cafeteria(actor=request.user, pedido_id=pedido_id)
    except PedidoAnticipado.DoesNotExist:
        raise Http404("Ese pedido no existe.")


@login_required
@require_http_methods(["GET"])
def detalle_del_pedido_en_la_cafeteria(request, pedido_id):
    """El detalle de un pedido en la modal de `/reservas/` (`HU-68`, `DT-49`).

    Fragmento (`DT-16`): **la misma plantilla que la modal del acudiente**, con
    lo que cambia según quién mira —quién canceló, a dónde va el formulario—.
    Dos modales del mismo pedido acabarían enseñando cosas distintas.
    """
    pedido = _pedido_en_la_cafeteria(request, pedido_id)
    return render(
        request,
        "ventas/partials/detalle-del-pedido.html",
        {"pedido": pedido, "estudiante": pedido.venta.estudiante, "para_la_cafeteria": True},
    )


@login_required
@require_http_methods(["POST"])
def cancelacion_por_la_cafeteria(request, pedido_id):
    """El cajero o la administración cancelan un pedido desde la modal (`HU-67`).

    **Devuelve la misma modal**, con el error o ya cancelada, como la del
    acudiente (`DT-49`, que corrige a `DT-48` en esto). Si se canceló, la
    respuesta lleva `HX-Trigger: pedidos-cambiado` y el tablero de detrás se
    vuelve a pedir: cambian la lista, las cifras y lo que falta por entregar.

    El rol se comprueba en el selector **y** en el servicio, como en el punto de
    venta: el primero para responder `403` antes de enseñar un pedido ajeno, el
    segundo para que la regla valga entre por donde entre (`DT-15`). Un rechazo
    vuelve en `200` con su motivo dentro, porque HTMX no intercambia un `4xx`.
    """
    pedido = _pedido_en_la_cafeteria(request, pedido_id)

    error = None
    motivo = request.POST.get("motivo", "")
    try:
        cancelar_pedido(actor=request.user, pedido=pedido, motivo=motivo)
    except ValidationError as rechazo:
        error = " ".join(rechazo.messages)
    # El estado nuevo —o el que otro dejó mientras la modal estaba abierta—.
    # Las líneas y el número ya venían, y no cambian.
    pedido.refresh_from_db()

    respuesta = render(
        request,
        "ventas/partials/detalle-del-pedido.html",
        {
            "pedido": pedido,
            "estudiante": pedido.venta.estudiante,
            "para_la_cafeteria": True,
            "error": error,
            "motivo": motivo if error else "",
            "recien_cancelado": error is None,
        },
    )
    if error is None:
        respuesta["HX-Trigger"] = "pedidos-cambiado"
    return respuesta


def _contexto_del_tablero(request):
    """Lo que pintan la pantalla de pedidos y su tablero (`HU-68`, `HU-24`).

    El filtro llega en `?ver=`. **Sin él, cada rol abre lo suyo**: la
    administración, todos; el cajero, lo que está por recoger, que es lo único
    que ve (`[S11]`). Un filtro que no existe es un 404, no la pestaña por
    defecto: una URL mal escrita que enseña otra cosa es peor que un error.
    Uno que existe pero no le toca al rol lo rechaza el selector con `403`.
    """
    es_administracion = request.user.rol == Rol.ADMINISTRADOR
    filtro = request.GET.get("ver") or ("todos" if es_administracion else "por-recoger")
    if filtro not in FILTROS_DE_PEDIDOS:
        raise Http404("Ese filtro de pedidos no existe.")

    pedidos = pedidos_de_la_cafeteria(actor=request.user, filtro=filtro)
    tablero = tablero_de_reservas(actor=request.user)
    pantalla = reverse("reservas")

    return {
        "pedidos": pedidos,
        "tablero": tablero,
        "filtro": filtro,
        "es_administracion": es_administracion,
        # Lo que está por recoger, se enseñe o no la pestaña.
        "cuantas": tablero.por_recoger,
        "pestanas": [
            {"clave": clave, "rotulo": rotulo, "url": f"{pantalla}?ver={clave}"}
            for clave, rotulo in (
                ("todos", "Todos"),
                ("por-recoger", "Por recoger"),
                ("entregados", "Entregados"),
                ("cancelados", "Cancelados"),
            )
        ]
        if es_administracion
        else [],
        "titulo_de_la_lista": {
            "todos": "Todos los pedidos",
            "por-recoger": "Por recoger",
            "entregados": "Entregados",
            "cancelados": "Cancelados",
        }[filtro],
        "tablero_url": f"{reverse('tablero-de-reservas')}?ver={filtro}",
        # `INVD-2`. Si alguno por recoger no se puede entregar, la pantalla lo
        # explica una vez además de marcar la fila. Se calcula aquí para no
        # recorrer la lista dos veces en la plantilla.
        "hay_sin_salida": any(
            p.esta_pendiente and not p.venta.estudiante.puede_operar for p in pedidos
        ),
    }


@login_required
@require_http_methods(["GET"])
def reservas(request):
    """La pantalla de pedidos anticipados de la cafetería (`TT-148`, `HU-68`).

    `HU-24`: **las reservas pendientes son consultables desde la cafetería**,
    para tenerlas preparadas antes de que lleguen los estudiantes. `HU-68`
    añade, solo para la administración, el resto de los pedidos —entregados y
    cancelados— con un filtro por estado, y arriba las cifras y la suma de lo
    que falta por entregar.

    **La autorización la hacen los selectores**, no un `if` de esta vista: son
    el único camino por el que los pedidos llegan a una pantalla, y así la
    regla se aplica entre por donde entre (`DT-15`, `DT-11`).

    ── POR QUÉ NO ESTÁ DENTRO DEL PUNTO DE VENTA ──────────────────────────
    `INT-2` es una pantalla de tres columnas sin scroll, dimensionada para cobrar
    en 1024 × 600 con una fila delante. Una lista que crece con el día no cabe
    ahí sin quitarle sitio a lo que se pulsa en cada venta.

    Y no hace falta que esté: el pedido del estudiante que el cajero tiene
    delante llega al identificarlo — es `HU-25`. Lo que se busca por el nombre
    se entrega desde la vista del cajero de esta pantalla (`DT-58`).
    ─────────────────────────────────────────────────────────────────────────

    **El cajero ve otra pantalla en la misma ruta** (`DT-58`): «Entregas», con
    un buscador, la cola y un panel desde el que entrega o cancela. La ruta es
    la misma porque el dato es el mismo (`DT-34`); lo que cambia es para qué lo
    mira cada rol.
    """
    if request.user.rol == Rol.CAJERO:
        return render(request, "ventas/entregas.html", _contexto_de_la_cola(request))
    return render(request, "ventas/reservas-pendientes.html", _contexto_del_tablero(request))


@login_required
@require_http_methods(["GET"])
def tablero_de_reservas_fragmento(request):
    """El tablero de `/reservas/` sin la página: cifras, lo que falta y la lista.

    Fragmento (`DT-16`). Lo vuelve a pedir la propia pantalla cuando la modal
    cancela un pedido (`HX-Trigger: pedidos-cambiado`, `DT-40`), con el mismo
    filtro que se estaba mirando.
    """
    return render(
        request, "ventas/partials/tablero-de-reservas.html", _contexto_del_tablero(request)
    )


# ── Entregas: la vista del cajero de `/reservas/` (`DT-58`) ───────────────────
#
# Una cola con buscador, un panel con el pedido elegido y dos modales: la
# confirmación de la entrega y el motivo de la cancelación. **Las dos escrituras
# responden con el panel**, en cualquiera de sus estados, y la modal se cierra
# al recibirlo (`interfaz.js`). Todo es del cajero: la administración no entrega
# (`[S11]`) y cancela desde su propia modal (`DT-49`).
# ──────────────────────────────────────────────────────────────────────────────


def _contexto_de_la_cola(request):
    """La cola del cajero, filtrada por lo que haya en el buscador (`DT-58`).

    Lo que está por recoger, y debajo, plegado, lo que falta por entregar
    sumado, que es para lo que existe `HU-24`. **La suma no se filtra**: dice
    qué hay que tener preparado para todo el descanso, no para quien se busca.

    **`?ver=` se sigue respetando**, aunque la pantalla no tenga pestañas: un
    filtro que no existe es un `404`, y uno que no es suyo, el `403` del
    selector. Ignorarlo enseñaría la cola a quien escribió `?ver=entregados`
    como si se lo hubieran concedido.
    """
    _solo_el_cajero(request.user)
    filtro = request.GET.get("ver") or "por-recoger"
    if filtro not in FILTROS_DE_PEDIDOS:
        raise Http404("Ese filtro de pedidos no existe.")
    busqueda = request.GET.get("q", "").strip()
    pedidos = pedidos_de_la_cafeteria(actor=request.user, filtro=filtro, busqueda=busqueda)
    return {
        "pedidos": pedidos,
        "busqueda": busqueda,
        "tablero": tablero_de_reservas(actor=request.user),
        "hay_sin_salida": any(not p.venta.estudiante.puede_operar for p in pedidos),
    }


@login_required
@require_http_methods(["GET"])
def cola_de_entregas(request):
    """La cola del cajero sin la página (`DT-58`, `DT-16`).

    La pide el buscador a cada tecla y la propia pantalla cuando se entrega o se
    cancela un pedido (`HX-Trigger: pedidos-cambiado`), con lo que haya escrito.
    """
    return render(request, "ventas/partials/cola-de-entregas.html", _contexto_de_la_cola(request))


def _pedido_por_entregar(request, pedido_id):
    """El pedido elegido en la cola, o `None` si ya no está por recoger.

    **El rol primero, después el `404`**: que un pedido existe no se le cuenta a
    otro rol. Y **uno cerrado no es un error**: otra caja lo entregó o alguien lo
    canceló desde que la cola se pintó. Se responde que ya no está —sin enseñar
    cómo se cerró, que es el historial que el cajero no ve (`HU-68`)— y la cola
    se repinta.
    """
    _solo_el_cajero(request.user)
    estado = (
        PedidoAnticipado.objects.filter(pk=pedido_id).values_list("estado", flat=True).first()
    )
    if estado is None:
        raise Http404("Ese pedido no existe.")
    if estado != EstadoDelPedido.PENDIENTE:
        return None
    return pedido_de_la_cafeteria(actor=request.user, pedido_id=pedido_id)


def _panel(request, pedido, **extra):
    """El panel del pedido elegido, en cualquiera de sus estados (`DT-58`).

    **Un rechazo puede venir de que otra caja se adelantó**: entre leer el
    pedido y bloquearlo, alguien lo entregó o lo canceló. Entonces el pedido ya
    no se pinta —el panel volvería a ofrecer entregarlo— y queda el motivo.
    Siempre que el pedido sale de la cola, la cola se repinta.
    """
    if pedido is not None and extra.get("rechazo"):
        pedido.refresh_from_db(fields=["estado"])
        if not pedido.esta_pendiente:
            pedido = None
    contexto = {
        "pedido": pedido,
        "estudiante": pedido.venta.estudiante if pedido else None,
        "ya_no_esta": pedido is None,
    }
    contexto.update(extra)
    respuesta = render(request, "ventas/partials/panel-de-la-entrega.html", contexto)
    if pedido is None or extra.get("entregado") or extra.get("cancelado"):
        respuesta["HX-Trigger"] = "pedidos-cambiado"
    return respuesta


def _modal(request, plantilla, pedido):
    """Una de las dos modales de «Entregas»; si el pedido ya no está, lo dice."""
    respuesta = render(
        request,
        plantilla,
        {"pedido": pedido, "estudiante": pedido.venta.estudiante if pedido else None},
    )
    if pedido is None:
        respuesta["HX-Trigger"] = "pedidos-cambiado"
    return respuesta


@login_required
@require_http_methods(["GET"])
def resumen_del_pedido(request, pedido_id):
    """El panel con el pedido que se pulsó en la cola (`DT-58`)."""
    return _panel(request, _pedido_por_entregar(request, pedido_id))


@login_required
@require_http_methods(["GET"])
def confirmacion_de_la_entrega(request, pedido_id):
    """La modal que confirma a quién se entrega y qué (`DT-58`).

    **No escribe nada.** Lleva la fotografía porque aquí no hay tarjeta: el
    pedido se eligió de una lista, y la cara es lo único que dice que se entrega
    a quien lo reservó (`DEC-8`, `HU-58`).
    """
    return _modal(
        request,
        "ventas/partials/confirmacion-de-la-entrega.html",
        _pedido_por_entregar(request, pedido_id),
    )


@login_required
@require_http_methods(["POST"])
def entrega_en_el_panel(request, pedido_id):
    """Entrega el pedido confirmado en la modal y responde con el panel (`DT-58`).

    El mismo servicio que el punto de venta (`HU-25`): bloquea, comprueba el
    estado y que el estudiante pueda retirar (`INVD-2`), asienta las salidas y
    **no toca la billetera**. Un rechazo vuelve al panel en `200`, con el
    motivo: htmx no intercambia un `4xx`.
    """
    pedido = _pedido_por_entregar(request, pedido_id)
    if pedido is None:
        return _panel(request, None)
    try:
        entregar(actor=request.user, pedido=pedido)
    except (VentaRechazada, EstudianteNoOperativo) as rechazo:
        return _panel(request, pedido, rechazo=_motivo_del_rechazo(rechazo))
    return _panel(request, pedido, entregado=True)


@login_required
@require_http_methods(["GET"])
def confirmacion_de_la_cancelacion(request, pedido_id):
    """La modal que pide el motivo de la cancelación (`DT-58`, `HU-67`)."""
    return _modal(
        request,
        "ventas/partials/confirmacion-de-la-cancelacion.html",
        _pedido_por_entregar(request, pedido_id),
    )


@login_required
@require_http_methods(["POST"])
def cancelacion_en_el_panel(request, pedido_id):
    """Cancela con su motivo y devuelve el importe; responde con el panel.

    `cancelar_pedido` es el mismo servicio que el de la modal de la
    administración y el del acudiente (`HU-67`, `DEC-24`): el motivo es
    obligatorio allí, no aquí. La modal ya apaga el botón sin él; si llega
    vacío igualmente, el rechazo vuelve al panel como cualquier otro.
    """
    pedido = _pedido_por_entregar(request, pedido_id)
    if pedido is None:
        return _panel(request, None)
    try:
        cancelar_pedido(actor=request.user, pedido=pedido, motivo=request.POST.get("motivo", ""))
    except ValidationError as rechazo:
        return _panel(request, pedido, rechazo=_motivo_del_rechazo(rechazo))
    return _panel(request, pedido, cancelado=True)


def _motivo_del_rechazo(rechazo):
    """El texto de un rechazo del servicio, sea `ValidationError` o no."""
    return " ".join(rechazo.messages) if hasattr(rechazo, "messages") else str(rechazo)


@login_required
@require_http_methods(["POST"])
def entrega(request):
    """Registra la entrega de un pedido anticipado (`TT-150`, `HU-25`).

    Primer criterio de la historia: **se registra en el punto de venta**. Es el
    camino rápido de los dos: la tarjeta escaneada ya dijo quién es. El otro es
    el panel de «Entregas» (`DT-58`), para el pedido que se busca por el nombre.

    **Sin diálogo de confirmación** (`INT-2`): un modal roba el foco y el foco es
    del lector. El cobro sí lleva dos (`DT-57`), por la devuelta; la entrega no
    cobra nada y no tiene qué calcular. La de «Entregas» sí confirma, porque allí
    no hay tarjeta y la fotografía es el único control.

    Devuelve el panel del estudiante en sus dos estados —entregado o rechazado—,
    que es la misma zona de la pantalla y por tanto el mismo fragmento. Arrastra
    el catálogo fuera de banda porque la entrega acaba de mover existencias, y
    esas son las que el cajero va a leer en la siguiente venta.

    La vista no decide nada: llama al servicio, que es quien bloquea, comprueba
    el estado y escribe dentro de una sola transacción. Si rechaza, **no se
    escribió nada** — la transacción se deshizo entera.
    """
    _solo_el_cajero(request.user)

    pedido = PedidoAnticipado.objects.filter(
        pk=request.POST.get("pedido") or None
    ).select_related("venta__estudiante").first()

    # **El estudiante sale del pedido, no de la sesión.** Se entrega a quien
    # reservó, y el panel tiene que seguir enseñando a esa persona: si viniera
    # de la sesión y el cajero hubiera escaneado otra tarjeta entre medias, el
    # fragmento volvería con alguien que no es el del pedido. Solo se cae a la
    # sesión cuando el pedido no existe y no hay a quién enseñar.
    estudiante = (
        pedido.venta.estudiante if pedido is not None else _estudiante_de_la_venta(request)
    )

    if pedido is None:
        return render(
            request,
            "ventas/partials/estudiante-identificado.html",
            _contexto_del_estudiante(
                request, estudiante, rechazo_de_entrega="Ese pedido ya no existe."
            ),
        )

    try:
        entregado = entregar(actor=request.user, pedido=pedido)
    except (VentaRechazada, EstudianteNoOperativo) as rechazo:
        # `200` con el motivo dentro del fragmento, no `400`: htmx no
        # intercambia lo que llega en `4xx`, y la pantalla se quedaría igual sin
        # decirle al cajero por qué no pasó nada.
        return render(
            request,
            "ventas/partials/estudiante-identificado.html",
            _contexto_del_estudiante(
                request,
                estudiante,
                rechazo_de_entrega=" ".join(rechazo.messages)
                if hasattr(rechazo, "messages")
                else str(rechazo),
            ),
        )

    return render(
        request,
        "ventas/partials/estudiante-identificado.html",
        _contexto_del_estudiante(
            request,
            estudiante,
            entregado=entregado,
            productos=catalogo_de_venta(),
            oob_catalogo=True,
        ),
    )


class CierreDeCajaForm(forms.Form):
    """Lo que el cajero cuenta: la base y el efectivo del cajón (`TT-173`).

    ═══════════════════════════════════════════════════════════════════════
    **NO HAY CAMPO PARA EL EFECTIVO ESPERADO, Y ESA AUSENCIA ES `INVD-5`.**

    La pantalla lo **enseña** —es la cifra contra la que se cuenta— y no lo
    **pide**. Un campo aquí, aunque llegara relleno, sería una casilla que se
    puede editar antes de enviar, y entonces el sistema volvería a cuadrar
    contra una estimación como en `PA-7`.
    ═══════════════════════════════════════════════════════════════════════

    `motivo` es opcional **en el formulario** y obligatorio cuando la caja no
    cuadra. La regla no puede vivir aquí porque depende de una cifra que el
    formulario no conoce: la decide el servicio y la garantiza
    `cierre_de_caja_diferencia_con_motivo` (`DT-15`).
    """

    base = forms.DecimalField(
        label="Base para dar cambio",
        min_value=Decimal("0"),
        decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal"}),
        help_text="El dinero que había en el cajón y no salió de ninguna venta.",
    )
    efectivo_contado = forms.DecimalField(
        label="Efectivo contado",
        min_value=Decimal("0"),
        decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal"}),
        help_text="Todo lo que hay en el cajón, con la base incluida.",
    )
    motivo = forms.CharField(
        label="Motivo de la diferencia",
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Faltó un billete de $10.000…"}),
        help_text="Obligatorio solo si la caja no cuadra.",
    )


@login_required
@require_http_methods(["GET", "POST"])
def cierre_de_caja(request):
    """La pantalla de cierre de caja de la jornada (`TT-173`, `HU-55`).

    **Solo el cajero.** Cuadrar la caja es de `USR-3` (`DEC-6`), y la
    autorización la hace el selector, no un `if` de esta vista: es el único
    camino por el que el recaudo en efectivo del día llega a una pantalla, y
    responde `PermissionDenied` aunque alguien escriba la URL (`DT-11`).

    ── VIVE EN EL ARMAZÓN DE LA APLICACIÓN, NO EN EL DE LA CAJA ────────────
    `base-punto-de-venta.html` es una pantalla completa de tres zonas, sin
    scroll y con el foco atado al lector: está hecha para cobrar con una fila
    delante. El cierre es lo contrario —se hace una vez, al final, sin nadie
    esperando y con billetes en la mano—, y meterlo en esa rejilla obligaría a
    inventarle una cuarta zona a un armazón que tiene tres por una razón.

    Es el mismo camino que `TT-148` tomó con la cola de reservas, y por eso la
    entrada está en los dos menús del cajero: en la barra del punto de venta,
    para llegar desde la caja, y en la de la aplicación, para volver.
    ─────────────────────────────────────────────────────────────────────────

    **No es una vista HTMX**: cerrar la caja escribe y termina en una
    redirección, para que recargar el navegador no intente cuadrar dos veces
    (`DT-16`). Que la segunda vez fallaría por `cierre_de_caja_uno_por_jornada`
    no es motivo para dejar la trampa puesta.
    """
    informacion = informacion_del_cierre(actor=request.user)

    formulario = CierreDeCajaForm(request.POST or None)

    if request.method == "POST" and formulario.is_valid():
        try:
            cierre = cerrar_caja(
                actor=request.user,
                base=formulario.cleaned_data["base"],
                efectivo_contado=formulario.cleaned_data["efectivo_contado"],
                motivo=formulario.cleaned_data["motivo"],
            )
        except CierreRechazado as error:
            # El motivo que falta no es culpa de un campo concreto —depende de
            # las tres cifras a la vez—, así que se cuelga del formulario y no
            # de `motivo`. Igual que en la recarga. **`messages`, no `str()`**:
            # el `str` de un `ValidationError` es la lista de Python, con sus
            # corchetes y sus comillas, y eso es lo que llegaba a la pantalla.
            formulario.add_error(None, " ".join(error.messages))
        else:
            messages.success(
                request,
                f"Caja cuadrada. {'Sin diferencia' if cierre.cuadra else 'Con diferencia'}: "
                f"{dinero(cierre.diferencia)}.",
            )
            return redirect("cierre-de-caja")

    return render(
        request,
        "ventas/cierre-de-caja.html",
        {"informacion": informacion, "form": formulario},
    )
