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

    def has_add_permission(self, request):
        """No se crean cuentas desde aquí. `TT-13`, `INV-6`, `INVD-1`.

        El formulario de alta del admin no pasa por `cuentas.services`, así que
        crearía la cuenta **sin disparar la invitación** y con la contraseña
        vacía. El único camino de alta sancionado hoy es el seed (`HU-39`).

        `TT-16` construye el servicio de alta de personal y `TT-17` la vista que
        lo usa: entonces esto vuelve a abrirse, apoyado en el servicio.
        """
        return False

    @admin.display(boolean=True, description="contraseña definida")
    def contrasena_definida(self, obj):
        return obj.tiene_contrasena_definida
