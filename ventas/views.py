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
    if request.user.rol != Rol.CAJERO:
        raise PermissionDenied(
            "El punto de venta es exclusivo del rol cajero: [S11] no concede "
            "registrar ventas a ningún otro rol."
        )

    return render(request, "ventas/punto-de-venta.html")
