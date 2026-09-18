"""Vistas del punto de venta (`INT-2`).

Solo HTTP: parsear la petición, delegar en un servicio o un selector, y
renderizar. **Cero lógica de negocio** (`DT-15`).

Una vista HTMX devuelve **un fragmento, nunca una página** (`DT-16`).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from billetera.selectors import saldo_de
from cuentas.models import Rol
from personas.models import Estudiante
from personas.selectors import (
    estudiante_a_cargo,
    identificar_por_codigo_de_tarjeta,
    identificar_por_documento,
)
from personas.services import EstudianteNoOperativo
from ventas import carrito as carrito_de_la_venta
from ventas.selectors import (
    catalogo_de_venta,
    catalogo_para_reservar,
    informacion_de_cobro,
    lineas_del_carrito,
    pedidos_pendientes_de,
    reservas_pendientes,
)
from ventas.services import VentaRechazada, registrar_venta, reservar, total_de


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
        {"productos": catalogo_de_venta(), **_contexto_del_ticket(request)},
    )


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

    cobro = (
        informacion_de_cobro(actor=request.user, estudiante=estudiante)
        if estudiante is not None
        else None
    )

    # `TT-81`. Quién es el cliente lo recuerda el servidor, no un campo oculto:
    # entre escanear y cobrar puede haber otro escaneo, y manda el último.
    carrito_de_la_venta.fijar_estudiante(request.session, estudiante)

    return render(
        request,
        "ventas/partials/estudiante-identificado.html",
        {
            "estudiante": estudiante,
            "cobro": cobro,
            "codigo": codigo,
            "documento": documento,
        },
    )


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

    Devuelve el **fragmento del ticket** y nada más: lo que cambia al tocar el
    carrito es la columna del ticket (`DT-16`). El catálogo no se repinta —sus
    existencias no cambian hasta que se cobre—, y repintarlo costaría el doble de
    bytes en cada toque.

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

    return render(
        request, "ventas/partials/ticket.html", _contexto_del_ticket(request)
    )


@login_required
@require_http_methods(["POST"])
def cobrar(request):
    """Confirma la venta (`TT-80`, `TT-81`, `HU-21`).

    **Sin diálogo de confirmación** (`INT-2`, `DT-16`): un modal roba el foco, y
    el foco es del lector. El botón cobra.

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
        # `EstudianteNoOperativo` no es una `VentaRechazada` y no trae etiqueta:
        # viene de `personas` y es `INVD-2`. La suya llega con `TT-126`.
        return render(
            request,
            "ventas/partials/ticket.html",
            _contexto_del_ticket(
                request,
                rechazo=" ".join(rechazo.messages)
                if hasattr(rechazo, "messages")
                else str(rechazo),
                motivo=getattr(rechazo, "motivo", "rechazo"),
            ),
        )

    carrito_de_la_venta.vaciar(request.session)

    return render(
        request,
        "ventas/partials/ticket.html",
        {
            **_contexto_del_ticket(request),
            "cobrada": venta,
            "total_cobrado": total_de(venta),
            "productos": catalogo_de_venta(),
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


@login_required
@require_http_methods(["GET", "POST"])
def reserva(request, estudiante_id):
    """Pantalla de reserva anticipada de un estudiante a cargo (`TT-145`, `HU-23`).

    Tercer criterio de la historia: **se gestiona desde la aplicación del
    acudiente** (`INT-1`), así que vive aquí y no en el admin.

    **La autorización la hace el selector**, no un `if` de esta vista: un
    estudiante que no está a cargo de quien pregunta es un 404, igual que uno
    que no existe. Los dos casos se responden igual a propósito — distinguirlos
    confirmaría a un desconocido que ese estudiante existe. Es el mismo patrón
    que la recarga (`TT-61`).

    El servicio vuelve a comprobar quién reserva, y esa repetición no sobra: la
    vista corta antes para no enseñar un formulario que va a fallar, y el
    servicio corta siempre, entre por donde entre (`DT-15`).

    ── NO HAY CARRITO EN SESIÓN, Y NO ES UN OLVIDO ────────────────────────
    El punto de venta lo tiene (`DT-26`) porque el cajero monta la venta gesto a
    gesto con una fila delante. Aquí no hay fila: el acudiente rellena las
    cantidades que quiere y envía una vez. Un carrito de servidor añadiría
    estado que nadie necesita y una segunda forma de que la reserva quede a
    medias.
    ─────────────────────────────────────────────────────────────────────────
    """
    try:
        estudiante = estudiante_a_cargo(usuario=request.user, estudiante_id=estudiante_id)
    except Estudiante.DoesNotExist:
        raise Http404("Ese estudiante no está a tu cargo.") from None

    productos = catalogo_para_reservar()
    error = None
    cantidades = {}

    if request.method == "POST":
        # Las cantidades llegan como `cantidad-<id>`. Se parsean aquí —es
        # trabajo de HTTP— y el servicio recibe `{id: entero}` ya limpio, que es
        # lo que sabe validar (`DT-15`).
        for producto in productos:
            crudo = (request.POST.get(f"cantidad-{producto.id}") or "").strip()
            if not crudo:
                continue
            try:
                cuantas = int(crudo)
            except ValueError:
                error = "Las cantidades se escriben en números enteros."
                break
            if cuantas > 0:
                cantidades[producto.id] = cuantas

        if error is None:
            try:
                pedido = reservar(
                    actor=request.user, estudiante=estudiante, lineas=cantidades
                )
            except (VentaRechazada, EstudianteNoOperativo) as rechazo:
                # Se devuelve `200` con el motivo dentro de la pantalla, no un
                # `400`: el estado de la petición y lo que hay que enseñar son
                # dos preguntas distintas, y es el precedente del repositorio.
                error = "; ".join(rechazo.messages) if hasattr(rechazo, "messages") else str(rechazo)
            else:
                messages.success(
                    request,
                    f"Reserva pagada: {estudiante.nombre} la recoge en la "
                    f"cafetería con su tarjeta.",
                )
                return redirect("reserva", estudiante_id=estudiante.id)

    # Lo que se escribió se devuelve escrito. Se adjunta al producto, como las
    # disponibles: una plantilla no sabe indexar un diccionario por una clave
    # que sale de una variable, y quien acaba de ver un rechazo no debería tener
    # que teclear otra vez lo que ya tecleó.
    for producto in productos:
        producto.cantidad_pedida = cantidades.get(producto.id, "")

    return render(
        request,
        "ventas/reserva.html",
        {
            "estudiante": estudiante,
            "productos": productos,
            "saldo": saldo_de(estudiante),
            "pendientes": pedidos_pendientes_de(estudiante),
            "error": error,
        },
    )


@login_required
@require_http_methods(["GET"])
def reservas(request):
    """La cola de reservas pendientes del personal de la cafetería (`TT-148`).

    `HU-24`, y su único criterio: **las reservas pendientes son consultables
    desde la cafetería**. Para tenerlas preparadas antes de que lleguen los
    estudiantes, que es el «para qué» de la historia.

    **La autorización la hace el selector**, no un `if` de esta vista: es el
    único camino por el que la cola llega a una pantalla, y así la regla se
    aplica entre por donde entre (`DT-15`, `DT-11`).

    ── POR QUÉ NO ESTÁ DENTRO DEL PUNTO DE VENTA ──────────────────────────
    `INT-2` es una pantalla de tres columnas sin scroll, dimensionada para cobrar
    en 1024 × 600 con una fila delante. Una lista que crece con el día no cabe
    ahí sin quitarle sitio a lo que se pulsa en cada venta.

    Y no hace falta que esté: se consulta **antes** del descanso, no durante.
    Durante, lo que el cajero necesita es el pedido del estudiante que tiene
    delante, y eso llega al identificar — es `HU-25`.
    ─────────────────────────────────────────────────────────────────────────
    """
    pendientes = reservas_pendientes(actor=request.user)

    return render(
        request,
        "ventas/reservas-pendientes.html",
        {
            "pendientes": pendientes,
            "cuantas": pendientes.count(),
        },
    )
