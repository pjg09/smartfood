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

    return render(request, "ventas/punto-de-venta.html")


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

    `HU-17` trae el saldo, el consumo del día y las restricciones (`PR-09`); aquí
    solo se identifica. Lo que sí se dice desde ahora es **si el estudiante puede
    comprar**: identificar a alguien de baja y callarlo dejaría al cajero
    montando una venta que va a fallar al final (`INVD-2`).
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

    return render(
        request,
        "ventas/partials/estudiante-identificado.html",
        {"estudiante": estudiante, "codigo": codigo, "documento": documento},
    )
