"""`INT-3` para las ventas: **el reporte de la operación, solo consulta**
(`TT-168`, `HU-35`).

`[S11]` concede «consultar reportes de ventas e inventario» a `USR-4` y a nadie
más, y la administración de la cafetería trabaja en el admin (`DT-2`). Por eso
el reporte vive aquí y no en una pantalla propia: **no hace falta una tercera
excepción a `DT-2`**. Las dos que hay —el padrón (`DT-27`) y la cola de reservas
(`DT-34`)— existen porque las abre a diario alguien que no es administrador; el
reporte de ventas lo consulta justo quien vive en el admin.

Es el mismo camino que `TT-141` abrió para el historial de existencias: el admin
da el listado, los filtros y la navegación por fechas, y lo que se añade es lo
que el admin no sabe hacer solo — **el consolidado del periodo que se está
mirando**.

── NADIE ESCRIBE UNA VENTA DESDE AQUÍ, Y NO ES QUE NO SE CONCEDA ───────────
Una venta es un asiento: no se edita ni se borra (`INV-2`, `INV-3`). Se registra
en el punto de venta, con su transacción, o no existe. Aquí se niegan las tres
escrituras **y además** `ventas` entra en `APPS_SIN_ESCRITURA_PARA_NINGUN_ROL`,
así que el permiso tampoco existe en ningún grupo. Dos sitios, como en el resto
de `INT-3`.
─────────────────────────────────────────────────────────────────────────────
"""

from django.contrib import admin

from billetera.templatetags.dinero import dinero
from reportes.selectors import (
    CONSULTAN_LOS_REPORTES_DE_LA_CAFETERIA,
    resumen_de_ventas,
)
from ventas.models import LineaVenta, Venta


class LineaVentaInline(admin.TabularInline):
    """Qué se vendió en esa venta, con **los precios de entonces** (`DT-8`).

    Solo lectura, como todo lo demás. Está aquí porque una venta sin sus
    renglones no se puede auditar: «$12.000» no dice si fueron tres empanadas o
    un almuerzo, y el primer criterio de `HU-35` habla de construir el reporte
    sobre las transacciones registradas — que solo significa algo si se pueden
    abrir.

    **El precio sale de la línea y no del producto**: editar el catálogo no
    reescribe lo que se cobró. Si alguien cambia `precio_unitario` por
    `producto.precio`, el reporte de mayo empieza a decir lo que costaría hoy.
    """

    model = LineaVenta
    extra = 0
    can_delete = False
    # `precio_congelado` y no `precio_unitario` a secas: el campo crudo lo pinta
    # el admin como el `Decimal` que es —«2500,00»— y el importe de al lado sale
    # por `dinero` —«$5.000»—. **Dos formatos de dinero en la misma fila**, que
    # es justo lo que el filtro existe para evitar.
    fields = ["producto", "cantidad", "precio_congelado", "importe_del_renglon"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="precio unitario")
    def precio_congelado(self, obj):
        """Lo que costaba **una** unidad al venderse (`DT-8`).

        Sale de la línea y no del producto: editar el catálogo no reescribe lo
        que se cobró. Si alguien lo cambia por `obj.producto.precio`, el reporte
        de mayo empieza a decir lo que costaría hoy — y se ve bien.
        """
        return dinero(obj.precio_unitario)

    @admin.display(description="importe")
    def importe_del_renglon(self, obj):
        """La propiedad del modelo, formateada en el único sitio que formatea
        dinero (`billetera.templatetags.dinero`)."""
        return dinero(obj.importe)


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    """El reporte de ventas: el libro, filtrable, con su consolidado arriba.

    ── QUÉ APORTA SOBRE UN LISTADO CORRIENTE ───────────────────────────────
    `date_hierarchy` y los filtros los da el admin. Lo que `HU-35` pide y el
    admin no da es **cuánto suma lo que se está mirando**: el consolidado se
    calcula sobre el mismo `QuerySet` que pinta la tabla de abajo —el de
    `ChangeList`, ya filtrado—, no sobre una consulta propia.

    Es la diferencia entre un reporte y dos pantallas que se contradicen: si el
    resumen consultara por su cuenta, filtrar por «efectivo» dejaría arriba el
    total de todo y nadie lo notaría, porque las dos cifras seguirían siendo
    correctas cada una por su lado.
    ─────────────────────────────────────────────────────────────────────────

    **El estudiante se enseña por su nombre y nada más.** Ni documento, ni
    código de tarjeta: el código es la credencial de acceso al saldo (`FUN-4`,
    `INV-7`) y el documento es un dato personal de un menor que la cafetería no
    necesita para conocer su actividad comercial (Ley 1581, `ALC-OUT-08`). Es el
    mismo criterio con el que `RestriccionesDelEstudianteAdmin` los oculta.
    """

    date_hierarchy = "creado_en"
    # `medio_pago` y `origen` **por su nombre de campo**, no por
    # `get_…_display`: el admin ya pinta la etiqueta de un campo con `choices` y
    # usa su `verbose_name` como encabezado. Con el método, la columna se titula
    # «method» —Django no tiene de dónde sacarle un nombre— y salen dos columnas
    # llamadas igual. Se vio en la captura.
    list_display = [
        "creado_en",
        "cliente",
        "medio_pago",
        "origen",
        "cajero",
        "total_de_la_venta",
    ]
    list_filter = ["medio_pago", "origen", "creado_en"]
    # Búsqueda por el nombre del estudiante y por el correo de quien cobró. **Sin
    # documento ni código de tarjeta**, ni siquiera como criterio de búsqueda:
    # una búsqueda por subcadena sobre un documento es una forma de recorrerlos.
    search_fields = ["estudiante__nombre", "cajero__email"]
    ordering = ["-creado_en"]
    inlines = [LineaVentaInline]
    actions = None

    # ── LA FICHA NO PINTA LA CLAVE AJENA AL ESTUDIANTE, Y ESO ES `[S11]` ────
    # Un campo de relación se pinta con el `__str__` del modelo apuntado, y el
    # de `Estudiante` es «Nombre (documento)». Es la misma trampa que
    # `CLAUDE.md` documenta para los proxies del admin: la pantalla se cuida de
    # no enseñar el documento en ninguna columna del listado y lo enseñaba en la
    # ficha, en letra grande y enlazado.
    #
    # Se vio en la captura, no en las pruebas — la que había solo miraba el
    # listado. Por eso la ficha usa `cliente`, que dice el nombre y nada más.
    # ───────────────────────────────────────────────────────────────────────
    fields = ["creado_en", "cliente", "medio_pago", "origen", "cajero"]
    readonly_fields = fields

    def get_queryset(self, request):
        """Con el estudiante y el cajero traídos: sin esto son dos consultas por
        fila, y un reporte de ventas de un colegio no es corto."""
        return super().get_queryset(request).select_related("estudiante", "cajero")

    # --- Solo consulta ------------------------------------------------------

    def has_view_permission(self, request, obj=None):
        """El permiso de Django **y** el rol, como en `catalogo` y `personas`.

        Un permiso se puede conceder por error; que la comprobación esté en dos
        sitios es deliberado. El cajero registra las ventas y **no** consulta el
        consolidado: `[S11]` son dos filas distintas.
        """
        usuario = request.user
        return (
            usuario.is_authenticated
            and usuario.rol in CONSULTAN_LOS_REPORTES_DE_LA_CAFETERIA
            and super().has_view_permission(request, obj)
        )

    def has_add_permission(self, request):
        """Nunca. Una venta se registra en el punto de venta, con su transacción
        —que descuenta saldo y existencias a la vez (`INV-1`, `INV-2`, `INV-3`)—
        o no existe. Un alta por el admin escribiría la fila sin ninguno de los
        dos descuentos."""
        return False

    def has_change_permission(self, request, obj=None):
        """Nunca: un asiento no se edita (`INV-2`, `INV-3`)."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Nunca. Y aunque se intentara, las claves ajenas de los dos libros van
        con `PROTECT`: borrar la venta dejaría movimientos que ya no explican
        nada."""
        return False

    # --- Lo que el listado enseña ------------------------------------------

    @admin.display(description="cliente", ordering="estudiante__nombre")
    def cliente(self, obj):
        """El estudiante, o «cliente genérico» (`DEC-1`, `HU-53`).

        No es un hueco: una venta sin estudiante **es** una venta a `USR-6`, y
        dejarlo vacío se leería como un dato que falta.
        """
        return obj.estudiante.nombre if obj.estudiante_id else "Cliente genérico"

    @admin.display(description="total")
    def total_de_la_venta(self, obj):
        """Con los precios congelados de sus renglones (`DT-8`).

        Se calcula sobre las líneas ya traídas por el `prefetch` del inline en
        la ficha; en el listado son una consulta por fila, que es el precio de
        enseñar el total de cada venta y no solo el del periodo. Si el listado
        se hiciera lento, la salida es anotar el total en `get_queryset`, no
        guardar una columna `total` — eso es la segunda fuente de verdad que
        `DT-19` evita.
        """
        return dinero(sum(linea.importe for linea in obj.lineas.all()))

    # --- El consolidado del periodo que se está mirando ---------------------

    def changelist_view(self, request, extra_context=None):
        """`TT-168`. Añade el resumen al contexto **del listado ya filtrado**.

        Se llama a `super()` primero y se lee `cl.queryset` de la respuesta: es
        el `QuerySet` que el admin acaba de construir con la fecha, los filtros
        y la búsqueda aplicados. Calcularlo antes, o por nuestra cuenta, daría
        un resumen de otro conjunto.

        `response.context_data` no existe si algo devolvió una redirección —el
        admin lo hace cuando un filtro no es válido—, así que se comprueba
        antes de tocarlo. Sin esa guarda, un filtro mal escrito en la URL
        rompería la pantalla en vez de corregirse solo.
        """
        # El título por defecto de un listado de solo lectura es «Seleccione
        # venta para ver», que describe lo que se hace con una tabla y no lo que
        # es esta pantalla. `HU-35` pide un reporte, y quien entra por el menú
        # tiene que reconocerlo por el encabezado.
        extra_context = {"title": "Reporte de ventas", **(extra_context or {})}

        respuesta = super().changelist_view(request, extra_context)

        listado = getattr(respuesta, "context_data", {}).get("cl")
        if listado is not None:
            respuesta.context_data["resumen"] = resumen_de_ventas(listado.queryset)

        return respuesta
