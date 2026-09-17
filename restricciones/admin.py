"""`INT-3` para las restricciones: **solo consulta** (`TT-112`, `HU-38`).

`[S11]` concede consultar las restricciones de un estudiante a los cuatro roles.
La administración de la cafetería y la institución trabajan en el admin (`DT-2`),
así que su consulta vive aquí.

**Lo único registrado es el proxy `RestriccionesDelEstudiante`.** Ni
`LimiteDiario`, ni `RestriccionProducto`, ni `RestriccionAlergeno`, ni el libro de
asientos: registrarlos abriría en `INT-3` una puerta a escribir lo que `INV-4`
reserva al acudiente. Ver el docstring de `restricciones/models.py`.
"""

from django.contrib import admin

from billetera.templatetags.dinero import dinero
from restricciones.models import RestriccionesDelEstudiante
from restricciones.selectors import (
    CONSULTAN_EN_LA_ADMINISTRACION,
    estudiantes_con_sus_restricciones,
    restricciones_precargadas,
)

# Lo que se enseña, en el orden en que se lee. **Ni el documento, ni el código de
# tarjeta, ni el acudiente, ni la fotografía, ni el saldo**: la cafetería consulta
# restricciones, no administra estudiantes (`[S11]`, `HU-44`). El código de
# tarjeta, además, es la credencial de acceso al saldo (`FUN-4`).
CAMPOS = ["nombre", "estado", "cupo_diario", "productos", "alergenos"]


@admin.register(RestriccionesDelEstudiante)
class RestriccionesDelEstudianteAdmin(admin.ModelAdmin):
    """El listado de estudiantes con sus tres restricciones, y la ficha de cada uno.

    **Se busca por el documento, pero no se enseña.** `=documento` es coincidencia
    exacta: sirve para distinguir a dos estudiantes con el mismo nombre teniendo
    el documento delante, y no sirve para recorrer documentos tecleando cifras
    sueltas, que es lo que haría una búsqueda por subcadena.

    Toda la escritura está negada aquí, además de no existir en la matriz: el
    proxy solo tiene permiso `view` (`default_permissions`). Dos sitios, como en
    el resto de `INT-3`.
    """

    list_display = CAMPOS
    list_filter = ["estado"]
    search_fields = ["nombre", "=documento"]
    ordering = ["nombre"]
    # Sin `delete_selected`: no hay nada que una acción masiva pueda hacer aquí.
    actions = None
    fieldsets = [
        (
            None,
            {
                "fields": CAMPOS,
                "description": (
                    "Solo consulta. Las restricciones las configura y las retira "
                    "el acudiente desde su panel; nadie más puede cambiarlas "
                    "(HU-13, INV-4). El alérgeno bloqueado cubre cualquier "
                    "producto que lo declare, también los que se añadan al "
                    "catálogo después (INV-5)."
                ),
            },
        )
    ]
    readonly_fields = CAMPOS

    def get_queryset(self, request):
        """El selector decide quién llega y trae las restricciones de una vez (`TT-111`)."""
        return estudiantes_con_sus_restricciones(actor=request.user)

    def has_view_permission(self, request, obj=None):
        """El permiso de Django **y** el rol, como en `catalogo` y `personas`.

        Un permiso se puede conceder por error; que la comprobación esté en dos
        sitios es deliberado.
        """
        usuario = request.user
        return (
            usuario.is_authenticated
            and usuario.rol in CONSULTAN_EN_LA_ADMINISTRACION
            and super().has_view_permission(request, obj)
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        """Nunca, ni para quien tenga el permiso: no existe (`INV-4`)."""
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="límite diario")
    def cupo_diario(self, obj):
        """«Sin límite» y no `$0`: son opuestos (`LimiteDiario`, `HU-61`)."""
        limite = restricciones_precargadas(obj).limite
        return dinero(limite.monto) if limite else "Sin límite"

    @admin.display(description="productos bloqueados")
    def productos(self, obj):
        """Los que el acudiente señaló uno a uno (`HU-10`)."""
        nombres = [r.producto.nombre for r in restricciones_precargadas(obj).productos]
        return ", ".join(nombres) if nombres else "Ninguno"

    @admin.display(description="alérgenos bloqueados")
    def alergenos(self, obj):
        """Las condiciones, no los productos que hoy las declaran (`HU-11`, `INV-5`)."""
        nombres = [r.alergeno.nombre for r in restricciones_precargadas(obj).alergenos]
        return ", ".join(nombres) if nombres else "Ninguno"
