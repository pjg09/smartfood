"""`INT-3` es el admin de Django (`DT-2`): no lleva plantillas propias.

`TT-34`. La administración de estudiantes vive aquí, pero **ni el alta ni la
edición las hace el formulario generado**: las hacen `personas.services`. Es
`DT-15` aplicado al admin, que también es una vista. Si el formulario guardara
por su cuenta, el estudiante nacería sin código de tarjeta (`HU-43`, `INV-7`).
"""

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied

from cuentas.models import Rol
from personas.models import Acudiente, Estudiante, Institucion
from personas.services import CAMPOS_EDITABLES, crear_estudiante, editar_estudiante


@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ["nombre", "usuario"]
    readonly_fields = ["id", "unica"]

    def has_add_permission(self, request):
        # El prototipo opera sobre UNA institución (`ALC-OUT-10`, `HU-39`), y la
        # crea el seed. La base lo impide igualmente; esto solo evita ofrecer un
        # botón que siempre falla.
        return not Institucion.objects.exists()


class EstudianteForm(forms.ModelForm):
    """Lo que la institución decide al matricular o al editar.

    El **código de tarjeta no aparece**, y no porque se haya olvidado: el campo
    es `editable=False` en el modelo, así que ningún formulario puede incluirlo.
    Primer criterio de `HU-14`: lo genera el sistema, no una persona.
    """

    class Meta:
        model = Estudiante
        fields = ["nombre", "documento", "acudiente"]


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    """`TT-34`, `HU-44`. Listado, búsqueda, alta individual y edición.

    `INT-3` es el admin de Django (`DT-2`), así que esta tarea se reduce a
    declarar el modelo (`ANEXO A` de `decisiones-tecnicas.md`). Lo que **no** se
    reduce es quién escribe: el alta y la edición pasan por `personas.services`,
    porque el admin es una vista y una vista nunca escribe directamente
    (`DT-15`). Si el formulario guardara por su cuenta, un estudiante nacería
    sin código de tarjeta y `HU-43` se rompería en silencio.
    """

    form = EstudianteForm
    list_display = ["nombre", "documento", "acudiente", "creado_en"]
    search_fields = ["nombre", "documento", "acudiente__nombre", "acudiente__documento"]
    ordering = ["nombre"]
    list_select_related = ["acudiente"]

    # `TT-35`. Con un colegio de verdad, un `<select>` con todos los acudientes
    # es una lista de cientos de nombres que hay que recorrer a ojo. El
    # autocompletado busca por nombre y por documento, que es como la institución
    # los identifica.
    autocomplete_fields = ["acudiente"]

    def get_readonly_fields(self, request, obj=None):
        """`TT-35`. En el alta no se enseñan campos que aún no tienen valor.

        El formulario de alta mostraba «Id:» y «Creado en:» vacíos, que no le
        dicen nada a quien está matriculando y compiten por su atención con los
        tres campos que sí tiene que llenar.
        """
        return ["id", "creado_en"] if obj is not None else []

    def _es_la_institucion(self, request):
        """`[S11]` y tercer criterio de `HU-44`.

        No basta con el permiso de Django: se comprueba también el rol, igual
        que en `UsuarioAdmin`. Un permiso se puede conceder por error; que la
        comprobación esté en dos sitios es deliberado.
        """
        usuario = request.user
        return usuario.is_authenticated and usuario.rol == Rol.INSTITUCION

    def has_add_permission(self, request):
        return self._es_la_institucion(request) and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return self._es_la_institucion(request) and super().has_change_permission(
            request, obj
        )

    def has_delete_permission(self, request, obj=None):
        """No se borran estudiantes.

        El que se va del colegio se da de **baja**, que es un estado distinto de
        «desactivado» y conserva íntegro su historial (`DT-12`, `DEC-7`,
        `HU-51`). Borrar la fila se llevaría por delante su billetera y sus
        compras, que es justo la trazabilidad que `OBJ-E2` pide del sistema.

        La baja llega en `PR-19`. Hasta entonces, un estudiante matriculado por
        error se corrige editándolo.
        """
        return False

    def save_model(self, request, obj, form, change):
        """Delega en el servicio, siempre. `DT-15`.

        El alta tiene que pasar por `crear_estudiante` porque ahí es donde se
        asigna el código de tarjeta (`HU-43`), y la edición por
        `editar_estudiante` porque ahí es donde se decide qué campos son
        editables — el código de tarjeta no lo es: se reasigna (`HU-46`).
        """
        try:
            if change:
                # `obj` ya trae los valores del formulario, así que la instancia
                # que se le pasa al servicio se relee de la base: sin eso, el
                # servicio no vería ningún cambio que comparar.
                editar_estudiante(
                    actor=request.user,
                    estudiante=Estudiante.objects.get(pk=obj.pk),
                    **{
                        campo: form.cleaned_data[campo]
                        for campo in CAMPOS_EDITABLES
                        if campo in form.cleaned_data
                    },
                )
                obj.refresh_from_db()
                return

            estudiante = crear_estudiante(
                actor=request.user,
                nombre=form.cleaned_data["nombre"],
                documento=form.cleaned_data["documento"],
                acudiente=form.cleaned_data["acudiente"],
            )
        except (PermissionDenied, ValueError) as error:
            raise PermissionDenied(str(error)) from error

        # Django espera que `obj` quede guardado; se sustituye por el creado.
        obj.pk = estudiante.pk
        obj.refresh_from_db()
        self.message_user(
            request,
            f"Estudiante matriculado. Su código de tarjeta se generó "
            f"automáticamente y no se puede escribir a mano (HU-43, INV-7).",
            messages.SUCCESS,
        )


@admin.register(Acudiente)
class AcudienteAdmin(admin.ModelAdmin):
    """Solo consulta (`TT-34`, `[S11]`).

    Existe por dos razones y ninguna es administrar acudientes. La primera es
    que el alta de un estudiante necesita elegir el suyo, y el autocompletado de
    `EstudianteAdmin` exige que el modelo esté registrado y sea buscable. La
    segunda es que «¿de quién es hijo este estudiante?» es una pregunta que la
    institución se hace a diario.

    **La cuenta del acudiente no se gestiona desde aquí.** Se da de alta con la
    carga (`HU-01`), se activa por invitación (`HU-03`) y se desactiva desde
    `cuentas.usuario` (`HU-42`). Por eso la matriz solo le concede `view`
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
