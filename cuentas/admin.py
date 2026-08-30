"""`INT-3` es el admin de Django (`DT-2`): no lleva plantillas propias."""

from django.contrib import admin

from cuentas.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ["email", "nombre", "rol", "is_active", "contrasena_definida"]
    list_filter = ["rol", "is_active", "is_staff"]
    search_fields = ["email", "nombre"]
    ordering = ["email"]
    # La contraseña nunca se edita desde aquí: la define el titular con su
    # invitación y nadie más llega a conocerla (`DEC-3`, `INVD-1`).
    exclude = ["password"]
    readonly_fields = ["id", "creado_en", "last_login"]

    @admin.display(boolean=True, description="contraseña definida")
    def contrasena_definida(self, obj):
        return obj.tiene_contrasena_definida
