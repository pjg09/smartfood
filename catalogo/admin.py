"""`INT-3` es el admin de Django (`DT-2`): no lleva plantillas propias.

`TT-45`. La gestión del catálogo vive aquí, pero **ni el alta ni la edición las
hace el formulario generado**: las hacen `catalogo.services`. Es `DT-15`
aplicado al admin, que también es una vista.

**El alérgeno se declara, no se copia.** El formulario del producto ofrece los
alérgenos como una selección múltiple sobre la tabla de relación (`DT-7`); no
existe en ninguna parte una lista de «productos bloqueados» que alguien pudiera
llenar a mano. Esa ausencia es `INV-5`.
"""

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import PermissionDenied
from django.utils.html import format_html

from catalogo.models import Alergeno, Categoria, Producto, ProductoAlergeno
from catalogo.services import (
    crear_producto,
    declarar_alergenos,
    devolver_al_catalogo,
    editar_producto,
    guardar_imagen,
    quitar_imagen,
    retirar_del_catalogo,
)
from config.imagenes import ImagenInvalida
from cuentas.models import Rol

# Los campos nutricionales, en el orden del etiquetado (`TT-44`).
CAMPOS_NUTRICIONALES = [
    "porcion",
    "energia_kcal",
    "proteinas_g",
    "carbohidratos_g",
    "azucares_g",
    "grasas_totales_g",
    "grasas_saturadas_g",
    "sodio_mg",
]


class ProductoForm(forms.ModelForm):
    """El formulario del producto, con sus alérgenos declarados.

    **El campo es propio y no del modelo.** Se llama distinto que el
    `ManyToMany` a propósito: la comprobación del admin mira el modelo y no el
    formulario, y con el mismo nombre rechaza el `fieldset` aunque el campo sea
    nuestro.

    La razón de fondo es de diseño, no de Django. `alergenos` pasa por una tabla intermedia (`ProductoAlergeno`,
    `DT-7`), y Django no deja editar un `ManyToMany` con `through` desde un
    formulario generado — con razón: escribiría la relación por su cuenta. Aquí
    el formulario **recoge** la selección y quien la escribe es
    `declarar_alergenos` (`DT-15`).
    """

    alergenos_declarados = forms.ModelMultipleChoiceField(
        queryset=Alergeno.objects.all(),
        required=False,
        label="alérgenos declarados",
        widget=FilteredSelectMultiple("alérgenos", is_stacked=False),
        help_text=(
            "Lo que este producto contiene. No es una lista de bloqueos: el "
            "bloqueo lo configura el acudiente sobre el alérgeno (HU-11, INV-5)."
        ),
    )

    # `TT-54`, `HU-59`. Como en la fotografía del estudiante: el modelo guarda
    # la clave (`DT-18`) y el fichero pasa por la canalización antes de
    # almacenarse (`DT-20`), así que el campo es del formulario y no del modelo.
    imagen = forms.ImageField(
        label="Imagen del producto",
        required=False,
        help_text=(
            "Opcional: un producto sin imagen se vende igual. Se re-codifica "
            "antes de guardarla, y la sirve la aplicación con caché larga."
        ),
    )
    quitar_imagen = forms.BooleanField(
        label="Quitar la imagen actual", required=False
    )

    class Meta:
        model = Producto
        fields = ["nombre", "precio", "categoria", "activo", *CAMPOS_NUTRICIONALES]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["alergenos_declarados"].initial = self.instance.alergenos.all()


class SoloLaAdministracionDeLaCafeteria:
    """`[S11]` y tercer criterio de `HU-26`, en las tres pantallas.

    No basta con el permiso de Django: se comprueba también el rol, igual que en
    `personas`. Un permiso se puede conceder por error; que la comprobación esté
    en dos sitios es deliberado.
    """

    def _es_la_administracion(self, request):
        usuario = request.user
        return usuario.is_authenticated and usuario.rol == Rol.ADMINISTRADOR

    def has_add_permission(self, request):
        return self._es_la_administracion(request) and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return self._es_la_administracion(request) and super().has_change_permission(
            request, obj
        )

    def has_view_permission(self, request, obj=None):
        return self._es_la_administracion(request) and super().has_view_permission(
            request, obj
        )


@admin.register(Categoria)
class CategoriaAdmin(SoloLaAdministracionDeLaCafeteria, admin.ModelAdmin):
    list_display = ["nombre", "cuantos_productos"]
    search_fields = ["nombre"]
    ordering = ["nombre"]

    def has_delete_permission(self, request, obj=None):
        """Borrar una categoría dejaría sus productos sin agrupación, y las
        alertas de `HU-31` se calculan por categoría."""
        return False

    @admin.display(description="productos")
    def cuantos_productos(self, obj):
        return obj.productos.count()


@admin.register(Alergeno)
class AlergenoAdmin(SoloLaAdministracionDeLaCafeteria, admin.ModelAdmin):
    """El alérgeno es una condición. Aquí solo se le pone nombre.

    **No hay ni puede haber una pantalla donde se listen «los productos
    bloqueados» de un alérgeno.** Los productos que lo declaran son el resultado
    de una consulta —se muestran como cuenta, no como lista editable— y quien
    declara es el producto. Al revés sería una lista materializada, que es lo
    que `INV-5` prohíbe.
    """

    list_display = ["nombre", "cuantos_productos_lo_declaran"]
    search_fields = ["nombre"]
    ordering = ["nombre"]

    def has_delete_permission(self, request, obj=None):
        """Borrar un alérgeno borraría las declaraciones que lo mencionan, y con
        ellas el bloqueo que protege a un estudiante alérgico (`HU-11`)."""
        return False

    @admin.display(description="productos que lo declaran")
    def cuantos_productos_lo_declaran(self, obj):
        return obj.declaraciones.count()


@admin.register(Producto)
class ProductoAdmin(SoloLaAdministracionDeLaCafeteria, admin.ModelAdmin):
    list_display = [
        "nombre", "categoria", "precio", "tiene_imagen",
        "alergenos_del_producto", "activo",
    ]
    list_filter = ["categoria", "activo", "alergenos"]
    search_fields = ["nombre", "categoria__nombre"]
    ordering = ["nombre"]
    form = ProductoForm
    readonly_fields = ["id", "creado_en", "imagen_actual"]
    actions = ["accion_retirar", "accion_devolver"]

    fieldsets = [
        (None, {"fields": ["nombre", "precio", "categoria", "activo"]}),
        (
            "Imagen",
            {
                "fields": ["imagen_actual", "imagen", "quitar_imagen"],
                "description": (
                    "Para que el cajero reconozca el producto de un vistazo y la "
                    "fila avance más rápido (HU-59, INT-2)."
                ),
            },
        ),
        (
            "Alérgenos declarados",
            {
                "fields": ["alergenos_declarados"],
                "description": (
                    "Lo que el producto <strong>contiene</strong>. El bloqueo lo "
                    "configura el acudiente sobre el alérgeno, no sobre este "
                    "producto (HU-11, INV-5): un producto que se agregue mañana "
                    "y declare lo mismo queda cubierto sin tocar nada."
                ),
            },
        ),
        (
            "Información nutricional",
            {
                "fields": CAMPOS_NUTRICIONALES,
                "description": (
                    "Por <strong>porción vendible</strong>, no por 100 g. Todo es "
                    "opcional: vacío significa «no declarado», que no es lo mismo "
                    "que cero. Ver docs/campos-nutricionales.md."
                ),
            },
        ),
        ("Trazabilidad", {"fields": ["id", "creado_en"], "classes": ["collapse"]}),
    ]

    def has_delete_permission(self, request, obj=None):
        """Un producto que ya se vendió no puede desaparecer.

        El historial de inventario lo referencia y sin él las existencias dejan
        de explicarse (`INV-3`). El camino sancionado es retirarlo del catálogo,
        que es un estado y no destruye nada.
        """
        return False

    def save_model(self, request, obj, form, change):
        """Delega en el servicio, siempre (`DT-15`)."""
        campos = {
            campo: form.cleaned_data[campo]
            for campo in ["nombre", "precio", "categoria", "activo", *CAMPOS_NUTRICIONALES]
            if campo in form.cleaned_data
        }
        try:
            if change:
                editar_producto(
                    actor=request.user,
                    producto=Producto.objects.get(pk=obj.pk),
                    **campos,
                )
                obj.refresh_from_db()
                self._aplicar_imagen(request, obj, form)
                return

            producto = crear_producto(actor=request.user, **campos)
        except (PermissionDenied, ValueError) as error:
            raise PermissionDenied(str(error)) from error

        obj.pk = producto.pk
        obj.refresh_from_db()
        self._aplicar_imagen(request, obj, form)

    def _aplicar_imagen(self, request, producto, form):
        """`TT-54`. Delega en el servicio, que es quien procesa y almacena.

        **Un fallo de la imagen no deshace el resto.** La imagen no es
        obligatoria (`HU-59`), así que un fichero que no se puede procesar es un
        aviso y no un error que tire el precio o los alérgenos que sí se
        guardaron.
        """
        imagen = form.cleaned_data.get("imagen")
        quitar = form.cleaned_data.get("quitar_imagen")

        if quitar and not imagen:
            quitar_imagen(actor=request.user, producto=producto)
            producto.refresh_from_db()
            self.message_user(request, "Imagen retirada.", messages.SUCCESS)
            return

        if not imagen:
            return

        try:
            guardar_imagen(actor=request.user, producto=producto, archivo=imagen)
        except ImagenInvalida as error:
            self.message_user(
                request,
                f"No se guardó la imagen: {'; '.join(error.messages)} El resto "
                "del producto sí se guardó: la imagen no es obligatoria (HU-59).",
                messages.WARNING,
            )
            return

        producto.refresh_from_db()
        self.message_user(request, "Imagen guardada.", messages.SUCCESS)

    def save_related(self, request, form, formsets, change):
        """Los alérgenos también pasan por el servicio.

        Django guardaría el `ManyToMany` por su cuenta aquí. Si se le dejara, la
        relación se escribiría sin pasar por `declarar_alergenos` y el único
        camino de escritura dejaría de ser único (`DT-15`).
        """
        declarar_alergenos(
            actor=request.user,
            producto=form.instance,
            alergenos=form.cleaned_data.get("alergenos_declarados", []),
        )

    @admin.display(description="imagen actual")
    def imagen_actual(self, obj):
        if not obj.tiene_imagen:
            return "Sin imagen. Un producto sin imagen se vende igual (HU-59)."
        return format_html(
            '<img src="{}" alt="Imagen de {}" style="max-height:180px;border-radius:6px">',
            obj.url_de_la_imagen,
            obj.nombre,
        )

    @admin.display(boolean=True, description="imagen")
    def tiene_imagen(self, obj):
        return obj.tiene_imagen

    @admin.display(description="alérgenos")
    def alergenos_del_producto(self, obj):
        nombres = [a.nombre for a in obj.alergenos.all()]
        return ", ".join(nombres) if nombres else "—"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("categoria").prefetch_related(
            "alergenos"
        )

    def _aplicar(self, request, queryset, operacion, hecho):
        aplicados = 0
        for producto in queryset:
            try:
                operacion(actor=request.user, producto=producto)
                aplicados += 1
            except PermissionDenied as error:
                self.message_user(request, f"{producto.nombre}: {error}", messages.ERROR)
        if aplicados:
            self.message_user(request, f"{hecho}: {aplicados}.", messages.SUCCESS)

    @admin.action(description="Retirar del catálogo (deja de ofrecerse, no se borra)")
    def accion_retirar(self, request, queryset):
        self._aplicar(request, queryset, retirar_del_catalogo, "Productos retirados")

    @admin.action(description="Devolver al catálogo")
    def accion_devolver(self, request, queryset):
        self._aplicar(request, queryset, devolver_al_catalogo, "Productos devueltos")
