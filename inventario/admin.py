"""`INT-3` para el inventario (`TT-69`, `HU-27`).

El admin de Django es la interfaz de la administración de la cafetería (`DT-2`),
así que el registro del ingreso vive aquí y no en una plantilla propia.

**El admin es una vista, y una vista nunca escribe directamente** (`DT-15`):
`save_model` delega en el servicio, que es donde están las reglas.
"""

from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied, ValidationError

from cuentas.models import Rol
from inventario.models import Merma, MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_por_producto
from inventario.services import ingresar_mercancia, registrar_merma


class SoloLaAdministracionDeLaCafeteria:
    """`[S11]`, igual que en `catalogo`.

    No basta con el permiso de Django: se comprueba también el rol. Un permiso se
    puede conceder por error; que la comprobación esté en dos sitios es
    deliberado.
    """

    def _es_la_administracion(self, request):
        usuario = request.user
        return usuario.is_authenticated and usuario.rol == Rol.ADMINISTRADOR

    def has_add_permission(self, request):
        return self._es_la_administracion(request) and super().has_add_permission(request)

    def has_view_permission(self, request, obj=None):
        return self._es_la_administracion(request) and super().has_view_permission(
            request, obj
        )


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(SoloLaAdministracionDeLaCafeteria, admin.ModelAdmin):
    """El libro del inventario: se lee y se le añaden asientos. Nada más.

    **Ni editar ni borrar**, y no es una restricción de permisos que se pueda
    ajustar: un asiento corregido a posteriori deja unas existencias que ya no
    explican lo que pasó, y `INV-3` dice justo lo contrario. Un error se corrige
    con otro movimiento —una merma con su motivo—, que es como se corrige un
    libro.
    """

    list_display = ["creado_en", "producto", "tipo", "cantidad", "motivo"]
    list_filter = ["tipo", "producto__categoria"]
    search_fields = ["producto__nombre", "motivo"]
    ordering = ["-creado_en"]
    readonly_fields = ["id", "creado_en"]

    def get_fields(self, request, obj=None):
        """En el alta solo se ofrece lo que el ajuste manual necesita.

        Se decide aquí y no borrando campos del formulario: el admin arma sus
        secciones desde `base_fields`, antes de que exista instancia, y un
        `del self.fields[...]` revienta al renderizar.
        """
        if obj is None:
            return ["producto", "cantidad", "motivo"]
        return ["id", "producto", "tipo", "cantidad", "motivo", "creado_en"]

    def has_change_permission(self, request, obj=None):
        """Ver sí, editar no. Un asiento no se reescribe (`INV-3`)."""
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        """Delega en el servicio, siempre (`DT-15`).

        **Solo ingresos desde aquí.** La venta la asienta el punto de venta
        (`TT-80`) y la merma tiene su propia entrada (`Merma`, `TT-139`):
        ofrecer los tres tipos en este formulario sería dejar que alguien
        descuente existencias a mano saltándose la venta, que es exactamente lo
        que `INV-3` no admite.
        """
        try:
            movimiento = ingresar_mercancia(
                actor=request.user,
                producto=form.cleaned_data["producto"],
                cantidad=form.cleaned_data["cantidad"],
                motivo=form.cleaned_data.get("motivo", ""),
            )
        except ValidationError as error:
            raise PermissionDenied("; ".join(error.messages)) from error
        except PermissionDenied:
            raise

        obj.pk = movimiento.pk
        obj.tipo = movimiento.tipo
        obj.creado_en = movimiento.creado_en


class MermaForm(forms.ModelForm):
    """El formulario de la merma: dos campos, y los dos obligatorios.

    **`cantidad` se pregunta en positivo** —«unidades perdidas»— y el servicio la
    asienta en negativo. Pedirla con signo invita a escribir «3» donde iba «-3», y
    ese error no falla: **sumaría existencias que nadie ingresó**.

    **`motivo` se declara `required=True` aquí aunque el modelo lo tenga
    `blank=True`.** El campo del modelo admite vacío porque un ingreso y una venta
    no lo llevan; en este formulario no hay más tipo que la merma, así que el
    campo es obligatorio. Es la capa de arriba de `INV-8`: la `CheckConstraint` es
    la que lo impone de verdad (`DT-5`), y `TT-140` lo comprueba sin pasar por
    aquí.
    """

    class Meta:
        model = Merma
        fields = ["producto", "cantidad", "motivo"]

    cantidad = forms.IntegerField(
        label="unidades perdidas",
        min_value=1,
        help_text="En positivo: cuántas unidades se dan de baja.",
    )
    motivo = forms.CharField(
        label="motivo",
        max_length=200,
        required=True,
        help_text="Obligatorio (INV-8). Rotura, caducidad, descuadre…",
    )


@admin.register(Merma)
class MermaAdmin(SoloLaAdministracionDeLaCafeteria, admin.ModelAdmin):
    """`INT-3` para la merma (`TT-139`, `HU-28`).

    Se lee y se le añaden asientos, como el libro entero. **Ni editar ni
    borrar**: los permisos no existen (`Merma.Meta`) y además se niegan aquí, que
    son los dos sitios con los que `INT-3` sostiene esto en el resto del admin.
    """

    form = MermaForm
    list_display = ["creado_en", "producto", "unidades_perdidas", "motivo"]
    list_filter = ["producto__categoria"]
    search_fields = ["producto__nombre", "motivo"]
    ordering = ["-creado_en"]
    readonly_fields = ["id", "creado_en"]

    def get_queryset(self, request):
        """Solo mermas.

        Sin esto, la entrada «Mermas» listaría el libro entero —ingresos y ventas
        incluidos—, porque un proxy comparte la tabla con su modelo base.
        """
        return (
            super()
            .get_queryset(request)
            .filter(tipo=TipoDeMovimientoDeInventario.MERMA)
            .select_related("producto")
        )

    @admin.display(description="unidades perdidas", ordering="cantidad")
    def unidades_perdidas(self, obj):
        """En positivo, como se preguntaron.

        El libro las guarda en negativo porque restan (`MovimientoInventario`), y
        esa es la cifra correcta ahí. En una lista que se titula «Mermas», «-3»
        obliga a traducir mentalmente cada fila.
        """
        return abs(obj.cantidad)

    def get_fields(self, request, obj=None):
        """En el alta, lo que la merma necesita; en la ficha, lo que pasó.

        Se decide aquí y no borrando campos del formulario: el admin arma sus
        secciones desde `base_fields`, antes de que exista instancia, y un
        `del self.fields[...]` revienta al renderizar.
        """
        if obj is None:
            return ["producto", "cantidad", "motivo"]
        return ["id", "producto", "cantidad", "motivo", "creado_en"]

    def has_change_permission(self, request, obj=None):
        """Ver sí, editar no. Un asiento no se reescribe (`INV-3`)."""
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        """Delega en el servicio, siempre (`DT-15`).

        El servicio es quien aplica `INV-8`, quien pone el signo y quien
        comprueba —dentro del bloqueo— que la merma no deja existencias
        negativas. Este método no repite ninguna de las tres: las traduce a lo
        que el admin sabe enseñar.

        `PermissionDenied` es lo que el admin pinta como un error del que se
        puede volver; una `ValidationError` sin traducir sale como un 500.
        """
        try:
            movimiento = registrar_merma(
                actor=request.user,
                producto=form.cleaned_data["producto"],
                cantidad=form.cleaned_data["cantidad"],
                motivo=form.cleaned_data["motivo"],
            )
        except ValidationError as error:
            raise PermissionDenied("; ".join(error.messages)) from error
        except PermissionDenied:
            raise

        obj.pk = movimiento.pk
        obj.tipo = movimiento.tipo
        # El movimiento guardado lleva la cantidad **con su signo**. Sin esta
        # línea, el mensaje de «se añadió» y la ficha a la que lleva enseñarían
        # la cifra que se tecleó y no la que quedó escrita.
        obj.cantidad = movimiento.cantidad
        obj.creado_en = movimiento.creado_en


class ExistenciasEnElCatalogo:
    """Mixin que añade la columna de existencias al listado de productos.

    **No hereda de `ModelAdmin`**, igual que el mixin de permisos: se mezcla con
    el `ModelAdmin` de `catalogo` y heredar de él dos veces complica el MRO sin
    aportar nada.

    Se calcula **al pintar el listado y en una sola consulta**
    (`existencias_por_producto`), no fila a fila: con un `existencias_de` por
    producto serían tantas consultas como filas, y el catálogo de un colegio no
    es corto.
    """

    def get_queryset(self, request):
        consulta = super().get_queryset(request)
        # Se guarda en el propio `ModelAdmin` porque `list_display` no recibe el
        # `request`: es el único sitio donde las dos cosas se encuentran.
        self._existencias = existencias_por_producto()
        return consulta

    @admin.display(description="existencias", ordering=None)
    def existencias(self, obj):
        """Las existencias **son** la suma de los movimientos (`INV-3`).

        Un producto sin movimientos da cero, y eso no es un caso especial: es la
        suma de una lista vacía. Se enseña «0» y no un hueco, porque un hueco se
        lee como «no se sabe».
        """
        return getattr(self, "_existencias", {}).get(obj.pk, 0)
