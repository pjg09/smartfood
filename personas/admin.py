"""`INT-3` es el admin de Django (`DT-2`): no lleva plantillas propias.

**Los estudiantes ya no se administran aquí.** El alta individual, la edición,
la fotografía, la baja y la reasignación del código siguen en
`personas.services`, que es donde viven sus reglas (`DT-15`); lo que se quitó
es la pantalla del admin que los llamaba, y la sustituye la ficha del padrón
(`DT-40`).
"""

from django.contrib import admin

from personas.models import Acudiente

# **La institución ya no se edita aquí** (`DEC-22`): no lo usaba nadie. La crea
# el seed con su nombre (`HU-39`), y que haya una sola lo impone la base
# (`ALC-OUT-10`), no este registro.


@admin.register(Acudiente)
class AcudienteAdmin(admin.ModelAdmin):
    """Solo consulta (`TT-34`, `[S11]`).

    Existe para consultar, no para administrar acudientes: «¿de quién es hijo
    este estudiante?» es una pregunta que la institución se hace a diario.

    **La cuenta del acudiente no se gestiona desde aquí.** Se da de alta con la
    carga (`HU-01`), se activa por invitación (`HU-03`) y se desactiva y
    reactiva desde la ficha del estudiante en el padrón (`HU-63`). Por eso la matriz solo le concede `view`
    (`cuentas/permisos.py`), y estas tres negativas lo hacen visible en la
    interfaz además de en la capa de datos.
    """

    list_display = ["nombre", "documento", "email", "cuantos_estudiantes"]
    search_fields = ["nombre", "documento", "usuario__email"]
    ordering = ["nombre"]
    readonly_fields = ["id", "usuario", "nombre", "documento"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("usuario")

    @admin.display(description="estudiantes a cargo")
    def cuantos_estudiantes(self, obj):
        return obj.estudiantes.count()
