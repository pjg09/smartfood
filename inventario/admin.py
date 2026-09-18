"""`INT-3` para el inventario (`TT-69`, `HU-27`).

El admin de Django es la interfaz de la administración de la cafetería (`DT-2`),
así que el registro del ingreso vive aquí y no en una plantilla propia.

**El admin es una vista, y una vista nunca escribe directamente** (`DT-15`):
`save_model` delega en el servicio, que es donde están las reglas.
"""

from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from cuentas.models import Rol
from inventario.models import Merma, MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de, existencias_por_producto, historial_de
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
    """Mixin que añade al listado de productos las existencias y su explicación.

    **No hereda de `ModelAdmin`**, igual que el mixin de permisos: se mezcla con
    el `ModelAdmin` de `catalogo` y heredar de él dos veces complica el MRO sin
    aportar nada.

    Vive en `inventario` y no en `catalogo` aunque se cuelgue del admin del
    producto: las existencias son del libro de inventario, no un atributo del
    catálogo. Esa separación es la misma que `DT-5` sostiene en el modelo.
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

        **La cifra es un enlace a su explicación** (`TT-141`, `HU-29`). Es el
        gesto que la historia pide: quien ve un número que no cuadra pincha el
        número, no busca en un menú otra pantalla que quizá hable del mismo
        producto.
        """
        cuantas = getattr(self, "_existencias", {}).get(obj.pk, 0)
        return format_html(
            '<a href="{}" title="Ver de dónde sale esta cifra">{}</a>',
            reverse("admin:catalogo_producto_historial", args=[obj.pk]),
            cuantas,
        )

    def get_urls(self):
        """`TT-141`. La pantalla que explica una cifra de existencias.

        Va antes de las de Django: las suyas incluyen `<path:object_id>/change/`
        y una ruta propia declarada después nunca llegaría a resolverse.
        """
        propias = [
            path(
                "<path:object_id>/historial/",
                self.admin_site.admin_view(self.vista_historial),
                name="catalogo_producto_historial",
            ),
        ]
        return propias + super().get_urls()

    def vista_historial(self, request, object_id):
        """El desglose de una cifra de existencias (`HU-29`, `INV-3`).

        ── QUÉ HACE ESTA PANTALLA QUE NO HICIERA YA EL LISTADO ────────────────
        El listado de movimientos existe desde `TT-69` y se puede filtrar. Lo
        que no daba es lo que `HU-29` pide literalmente: **poder auditar un
        descuadre**. Para eso no basta ver los asientos; hace falta seguirlos
        hasta la cifra y encontrar en qué renglón se torció.

        Por eso la tabla lleva una columna de **existencias tras cada
        movimiento**, calculada aquí, en Python, recorriendo el historial de la
        más antigua a la más reciente. La cifra grande de arriba sale de
        `existencias_de`, que es un `SUM` de la base.

        **Las dos cifras salen de caminos distintos a propósito.** Si algún día
        divergieran, esta pantalla lo enseña sin que nadie tenga que buscarlo:
        el último renglón de la columna no coincidiría con el total. Es `TST-4`
        puesto donde lo ve un humano, y `TT-142` es el mismo escenario puesto
        donde lo ve la suite.

        **No se guarda ningún acumulado.** Se calcula al pintar y se tira. Un
        acumulado almacenado sería la segunda fuente de verdad que `DT-5`
        evita.
        ─────────────────────────────────────────────────────────────────────

        **Autoriza antes de leer nada**: la matriz `[S11]` da el inventario a la
        administración de la cafetería y a nadie más, y esta pantalla enseña el
        libro entero de un producto.
        """
        producto = self.get_object(request, object_id)
        if producto is None:
            raise Http404("Ese producto no está en el catálogo.")
        if not self.has_view_permission(request, producto):
            raise PermissionDenied(
                "Consultar el inventario es función de la administración de la "
                "cafetería ([S11])."
            )

        movimientos = list(
            historial_de(producto).select_related("venta")
        )

        # `historial_de` llega del más reciente al más antiguo, que es el orden
        # en que se lee un extracto. El acumulado necesita el contrario, así que
        # se recorre al revés y se vuelve a invertir para pintar.
        corridas = []
        acumulado = 0
        for movimiento in reversed(movimientos):
            acumulado += movimiento.cantidad
            corridas.append((movimiento, acumulado))
        corridas.reverse()

        return TemplateResponse(
            request,
            "admin/catalogo/producto/historial.html",
            {
                **self.admin_site.each_context(request),
                "title": f"Existencias de {producto.nombre}",
                "producto": producto,
                "existencias": existencias_de(producto),
                "corridas": corridas,
                "cuantos": len(movimientos),
                "volver": reverse("admin:catalogo_producto_changelist"),
                "ficha": reverse("admin:catalogo_producto_change", args=[producto.pk]),
            },
        )
