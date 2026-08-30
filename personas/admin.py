"""`INT-3` es el admin de Django (`DT-2`): no lleva plantillas propias."""

from django.contrib import admin

from personas.models import Institucion


@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ["nombre", "usuario"]
    readonly_fields = ["id", "unica"]

    def has_add_permission(self, request):
        # El prototipo opera sobre UNA institución (`ALC-OUT-10`, `HU-39`), y la
        # crea el seed. La base lo impide igualmente; esto solo evita ofrecer un
        # botón que siempre falla.
        return not Institucion.objects.exists()
