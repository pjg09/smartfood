"""`INT-3` es el admin de Django (`DT-2`): no lleva plantillas propias.

`TT-17`. La gestión de cuentas de personal vive aquí, pero **el alta no la hace
el formulario generado**: la hace `cuentas.services.crear_cuenta_de_personal`.
Es `DT-15` aplicado al admin, que también es una vista: una vista nunca escribe
directamente. Si el formulario guardara por su cuenta, la cuenta nacería sin
invitación y con la contraseña vacía.
"""

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied

from cuentas.models import Rol, Usuario
from cuentas.services import (
    ROLES_DE_PERSONAL,
    crear_cuenta_de_personal,
    desactivar_cuenta,
    reactivar_cuenta,
    reenviar_invitacion,
)


class AltaDePersonalForm(forms.ModelForm):
    """Solo lo que la institución decide. La contraseña no aparece: la define el
    titular con su invitación, y nadie más llega a conocerla (`DEC-3`, `HU-41`)."""

    rol = forms.ChoiceField(
        choices=[(r.value, r.label) for r in Rol if r in ROLES_DE_PERSONAL],
        label="rol",
        help_text=(
            "Solo cajero o administrador. Las cuentas de acudiente nacen de la "
            "carga institucional (HU-01) más su invitación (HU-03)."
        ),
    )

    class Meta:
        model = Usuario
        fields = ["email", "nombre", "rol"]


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ["email", "nombre", "rol", "is_active", "contrasena_definida"]
    list_filter = ["rol", "is_active", "is_staff"]
    search_fields = ["email", "nombre"]
    ordering = ["email"]
    # La contraseña nunca se edita desde aquí: la define el titular con su
    # invitación y nadie más llega a conocerla (`DEC-3`, `INVD-1`).
    exclude = ["password"]
    actions = ["accion_desactivar", "accion_reactivar", "accion_reenviar_invitacion"]

    # Lo que este formulario **no** deja tocar, y por qué cada uno.
    #
    # Salió del recorrido de `TT-35`. Quitarle el superusuario a la institución
    # (`TT-10`) no habría servido de nada mientras este formulario siguiera
    # ofreciendo `is_superuser`, `groups` y `user_permissions`: la institución
    # podía devolvérselo con dos clics, o concederle al cajero la escritura
    # sobre las restricciones directamente sobre su cuenta. `INV-4` se sostiene
    # con permisos por rol en la capa de datos (`DT-11`), y eso exige que los
    # permisos **no** se concedan una a una desde una pantalla.
    #
    # Van como solo lectura y no ocultos a propósito: la institución tiene que
    # poder **ver** en qué grupo está una cuenta y si está activa. Lo que no
    # puede es cambiarlo desde aquí.
    DERIVADOS_DEL_ROL = ["rol", "is_staff", "groups", "user_permissions", "is_superuser"]

    # `is_active` tiene sus propias reglas y su propio servicio (`TT-19`,
    # `HU-42`): `desactivar_cuenta` se niega a que la institución se desactive a
    # sí misma, porque entonces nadie podría reactivarla. Editando la casilla a
    # mano esa regla no se aplica, y la institución se queda fuera del sistema
    # sin forma de volver a entrar. Se cambia con las acciones del listado.
    CON_SERVICIO_PROPIO = ["is_active"]

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs["form"] = AltaDePersonalForm
        return super().get_form(request, obj, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        """En el alta solo están los tres campos de `AltaDePersonalForm`."""
        if obj is None:
            return []
        return [
            "id", "creado_en", "last_login",
            *self.DERIVADOS_DEL_ROL,
            *self.CON_SERVICIO_PROPIO,
        ]

    def has_add_permission(self, request):
        """Solo la institución educativa. Primer criterio de `HU-40`.

        No basta con el permiso de Django: se comprueba también el rol, porque
        un permiso se puede conceder por error y `[S11]` es explícita en que solo
        `USR-5` da de alta cuentas.
        """
        usuario = request.user
        return (
            usuario.is_authenticated
            and usuario.rol == Rol.INSTITUCION
            and super().has_add_permission(request)
        )

    def save_model(self, request, obj, form, change):
        """El alta pasa por el servicio; la edición, no.

        `DT-15`: una vista nunca escribe directamente. El admin es una vista.
        """
        if change:
            return super().save_model(request, obj, form, change)

        try:
            usuario = crear_cuenta_de_personal(
                actor=request.user,
                email=form.cleaned_data["email"],
                rol=form.cleaned_data["rol"],
                nombre=form.cleaned_data.get("nombre", ""),
            )
        except (PermissionDenied, ValueError) as error:
            raise PermissionDenied(str(error)) from error

        # Django espera que `obj` quede guardado; se sustituye por el creado.
        obj.pk = usuario.pk
        obj.refresh_from_db()
        self.message_user(
            request,
            f"Cuenta creada. Se envió una invitación a {usuario.email}: "
            "define su contraseña desde ahí, nadie más la conocerá.",
            messages.SUCCESS,
        )

    def has_delete_permission(self, request, obj=None):
        """No se borran cuentas. `TT-19`, tercer criterio de `HU-42`.

        La historia exige que **el historial de operaciones de esa cuenta se
        conserve**: quién cobró qué venta sigue siendo cierto después de que esa
        persona deje de trabajar allí. Borrar la fila destruiría esa
        trazabilidad. El camino sancionado es desactivar, que es baja lógica.
        """
        return False

    def _aplicar(self, request, queryset, operacion, hecho, ya_estaba):
        """Recorre la selección aplicando un servicio y resume el resultado.

        El admin es una vista: delega, no escribe (`DT-15`).
        """
        aplicadas, sin_cambio, rechazadas = 0, 0, []
        for usuario in queryset:
            estaba = usuario.is_active
            try:
                operacion(actor=request.user, usuario=usuario)
            except (PermissionDenied, ValueError) as error:
                rechazadas.append(f"{usuario.email}: {error}")
                continue
            usuario.refresh_from_db()
            if usuario.is_active != estaba:
                aplicadas += 1
            else:
                sin_cambio += 1

        if aplicadas:
            self.message_user(request, f"{hecho}: {aplicadas}.", messages.SUCCESS)
        if sin_cambio:
            self.message_user(request, f"Sin cambios, {ya_estaba}: {sin_cambio}.", messages.INFO)
        for motivo in rechazadas:
            self.message_user(request, motivo, messages.ERROR)

    @admin.action(description="Desactivar la cuenta (revoca el acceso, conserva el historial)")
    def accion_desactivar(self, request, queryset):
        self._aplicar(request, queryset, desactivar_cuenta, "Cuentas desactivadas", "ya estaban desactivadas")

    @admin.action(description="Reactivar la cuenta")
    def accion_reactivar(self, request, queryset):
        self._aplicar(request, queryset, reactivar_cuenta, "Cuentas reactivadas", "ya estaban activas")

    @admin.action(description="Reenviar la invitación")
    def accion_reenviar_invitacion(self, request, queryset):
        reenviadas, omitidas = 0, 0
        for usuario in queryset:
            try:
                reenviar_invitacion(usuario)
                reenviadas += 1
            except ValueError:
                omitidas += 1

        if reenviadas:
            self.message_user(request, f"Invitaciones reenviadas: {reenviadas}.", messages.SUCCESS)
        if omitidas:
            self.message_user(
                request,
                f"Omitidas {omitidas}: ya tienen contraseña definida.",
                messages.WARNING,
            )

    @admin.display(boolean=True, description="contraseña definida")
    def contrasena_definida(self, obj):
        return obj.tiene_contrasena_definida
