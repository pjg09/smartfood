"""`INT-3` para el inventario (`TT-69`, `HU-27`).

El admin de Django es la interfaz de la administración de la cafetería (`DT-2`),
así que el registro del ingreso vive aquí y no en una plantilla propia.

**El admin es una vista, y una vista nunca escribe directamente** (`DT-15`):
`save_model` delega en el servicio, que es donde están las reglas.
"""

from django.contrib import admin
from django.core.exceptions import PermissionDenied, ValidationError

from cuentas.models import Rol
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_por_producto
from inventario.services import ingresar_mercancia


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
        (`TT-80`) y la merma es `HU-28`, del Sprint 4: ofrecer los tres tipos en
        este formulario sería dejar que alguien descuente existencias a mano
        saltándose la venta, que es exactamente lo que `INV-3` no admite.
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
