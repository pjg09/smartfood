"""Vistas del punto de venta (`INT-2`).

Solo HTTP: parsear la petición, delegar en un servicio o un selector, y
renderizar. **Cero lógica de negocio** (`DT-15`).

Una vista HTMX devuelve **un fragmento, nunca una página** (`DT-16`).
"""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from cuentas.models import Rol
from personas.models import Estudiante
from personas.selectors import (
    identificar_por_codigo_de_tarjeta,
    identificar_por_documento,
)
from personas.services import EstudianteNoOperativo
from ventas import carrito as carrito_de_la_venta
from ventas.selectors import (
    catalogo_de_venta,
    informacion_de_cobro,
    lineas_del_carrito,
)
from ventas.services import VentaRechazada, registrar_venta, total_de


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

    Todavía no hay nada que cobrar: identificar al estudiante es `HU-15` y
    `HU-16`, ver su saldo y sus restricciones es `HU-17`, y la venta en sí es
    `HU-21`. Esta vista habilita las tres —el sitio donde ocurren— y por eso no
    cierra ninguna historia.
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
        return render(
            request,
            "ventas/partials/ticket.html",
            _contexto_del_ticket(request, rechazo=" ".join(rechazo.messages)
                                 if hasattr(rechazo, "messages") else str(rechazo)),
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
