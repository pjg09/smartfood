"""`INT-3` es el admin de Django (`DT-2`): no lleva plantillas propias.

`TT-45`. Aquí quedan **las categorías y los alérgenos**: listas cortas que se
tocan pocas veces al año y que el admin resuelve bien.

**Los productos ya no están** (`DEC-25`, `DT-50`). Se crean, se editan y se
retiran en `/inventario/`, junto a sus existencias y su libro: eran tres
entradas del menú para tocar lo mismo. Las reglas no se movieron —siguen en
`catalogo.services`— y tampoco la que importa aquí: **el alérgeno se declara
en el producto, no se copia**, y no existe en ninguna parte una lista de
«productos bloqueados» que alguien pudiera llenar a mano (`INV-5`).
"""

from django.contrib import admin

from catalogo.models import Alergeno, Categoria
from cuentas.models import Rol


class SoloLaAdministracionDeLaCafeteria:
    """`[S11]` y tercer criterio de `HU-26`, en las dos pantallas.

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
