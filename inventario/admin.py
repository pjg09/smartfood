"""El reporte de movimientos de inventario (`TT-170`, `HU-36`), en `INT-3`.

**Es lo único del inventario que queda en el admin, y es de solo lectura**
(`DEC-25`, `DT-50`). Registrar un ingreso o una merma y consultar el libro de un
producto se hacen en `/inventario/`, junto al producto; aquí queda el libro
entero con su navegación por fechas y el consolidado del periodo, que es lo que
el admin da hecho y una pantalla propia tendría que reconstruir.
"""

from django.contrib import admin

from cuentas.models import Rol
from inventario.models import MovimientoInventario
from reportes.selectors import resumen_de_movimientos


class SoloLaAdministracionDeLaCafeteria:
    """`[S11]`, igual que en `catalogo`.

    No basta con el permiso de Django: se comprueba también el rol. Un permiso se
    puede conceder por error; que la comprobación esté en dos sitios es
    deliberado.
    """

    def _es_la_administracion(self, request):
        usuario = request.user
        return usuario.is_authenticated and usuario.rol == Rol.ADMINISTRADOR

    def has_view_permission(self, request, obj=None):
        return self._es_la_administracion(request) and super().has_view_permission(
            request, obj
        )


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(SoloLaAdministracionDeLaCafeteria, admin.ModelAdmin):
    """El libro del inventario: se lee y **se consolida**. Nada más.

    **Ni añadir, ni editar, ni borrar.** Un asiento corregido a posteriori deja
    unas existencias que ya no explican lo que pasó, y `INV-3` dice justo lo
    contrario: un error se corrige con otro movimiento. Y añadir ya no es de
    aquí: el ingreso y la merma se registran en `/inventario/` (`DT-50`), con el
    producto delante. Dos sitios para registrar lo mismo acabarían pidiendo
    cosas distintas.

    ── EL REPORTE DE `HU-36` ES ESTA PANTALLA, CON SU CONSOLIDADO ───────────
    El «para qué» de la historia es **revisar entradas, ventas y mermas en un
    solo lugar**, y el libro ya las tiene las tres: son tres clases de asiento
    de la misma tabla, no tres informes. Lo que lo hace reporte es acotar un
    periodo —`date_hierarchy`— y decir **cuánto suma lo que se está mirando**,
    que es lo que `TT-170` añade.
    ─────────────────────────────────────────────────────────────────────────
    """

    list_display = ["creado_en", "producto", "tipo", "cantidad", "motivo", "registrado_por"]
    list_filter = ["tipo", "producto__categoria"]
    search_fields = ["producto__nombre", "motivo"]
    # `TT-170`, `HU-36`. Sin navegación por fechas, «los movimientos de la
    # semana pasada» no se pueden acotar y el consolidado solo podría hablar del
    # libro entero.
    date_hierarchy = "creado_en"
    ordering = ["-creado_en"]
    fields = ["id", "producto", "tipo", "cantidad", "motivo", "venta", "registrado_por", "creado_en"]
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("producto", "registrado_por")

    def has_add_permission(self, request):
        """Se registra en `/inventario/` (`DT-50`), no aquí."""
        return False

    def has_change_permission(self, request, obj=None):
        """Ver sí, editar no. Un asiento no se reescribe (`INV-3`)."""
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        """`TT-170`. El consolidado del listado ya filtrado (`HU-36`).

        Mismo mecanismo que el reporte de ventas (`TT-168`): se llama a
        `super()` primero y se lee `cl.queryset` de la respuesta, que es el
        `QuerySet` con la fecha, los filtros y la búsqueda aplicados.
        Calcularlo por nuestra cuenta daría un resumen de otro conjunto **sin
        que nada fallara**, que es la peor clase de error de un reporte.

        `context_data` no existe si el admin devolvió una redirección —lo hace
        cuando un filtro de la URL no es válido—, así que se comprueba antes de
        tocarlo.
        """
        # El título por defecto es «Seleccione movimiento de inventario para
        # ver», que describe lo que se hace con una tabla y no lo que es esta
        # pantalla. Aquí no se selecciona nada: se revisa un libro.
        extra_context = {
            "title": "Movimientos de inventario",
            **(extra_context or {}),
        }

        respuesta = super().changelist_view(request, extra_context)

        listado = getattr(respuesta, "context_data", {}).get("cl")
        if listado is not None:
            respuesta.context_data["resumen"] = resumen_de_movimientos(
                listado.queryset
            )

        return respuesta
