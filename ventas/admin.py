"""`INT-3` para las ventas: **los reportes de la operación, solo consulta**
(`TT-168`, `HU-35`; `TT-176`, `HU-56`).

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

**Son dos reportes y no uno**, aunque salgan de la misma app y de la misma
jornada: el de ventas responde «cuánto se vendió» y el de cierres, «cuánto de
eso llegó al cajón». Lo que los cose es un enlace — cada cierre lleva al
listado de ventas en efectivo del día que explica su cifra (`INVD-5`).

── NADIE ESCRIBE AQUÍ, Y NO ES QUE NO SE CONCEDA ───────────────────────────
Una venta es un asiento y un cierre también: no se editan ni se borran
(`INV-2`, `INV-3`, `INVD-5`). La venta se registra en el punto de venta con su
transacción, y el cierre en el punto de venta con el efectivo esperado
calculado en ese momento, o no existen. Aquí se niegan las tres escrituras
**y además** `ventas` entra en `APPS_SIN_ESCRITURA_PARA_NINGUN_ROL`, así que el
permiso tampoco existe en ningún grupo. Dos sitios, como en el resto de
`INT-3`.
─────────────────────────────────────────────────────────────────────────────
"""

from urllib.parse import urlencode

from django.contrib import admin
from django.db.models import F
from django.urls import reverse
from django.utils.html import format_html

from billetera.templatetags.dinero import dinero
from reportes.selectors import (
    CONSULTAN_LOS_REPORTES_DE_LA_CAFETERIA,
    resumen_de_cierres,
    resumen_de_ventas,
)
from ventas.models import CierreDeCaja, LineaVenta, MedioDePago, Venta
from ventas.selectors import DIFERENCIA_DEL_CIERRE


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


class ResultadoDelCuadre(admin.SimpleListFilter):
    """Cuadró, sobró o faltó — **el filtro que la historia pide** (`TT-176`).

    El «para qué» de `HU-56` es **detectar un patrón de descuadres** en lugar de
    enterarse suelto cada día, y eso empieza por poder quedarse con los que no
    cuadraron.

    Es un `SimpleListFilter` y no un `list_filter` sobre un campo porque lo que
    distingue las tres clases **no es una columna**: es el signo de
    `efectivo_contado − base − efectivo_esperado`. La misma resta que hace
    `CierreDeCaja.diferencia` en Python y `DIFERENCIA_DEL_CIERRE` en SQL.
    """

    title = "resultado del cuadre"
    parameter_name = "cuadre"

    def lookups(self, request, model_admin):
        return [
            ("cuadra", "Sin diferencia"),
            ("sobrante", "Con sobrante"),
            ("faltante", "Con faltante"),
        ]

    def queryset(self, request, queryset):
        esperado_mas_base = F("base") + F("efectivo_esperado")
        if self.value() == "cuadra":
            return queryset.filter(efectivo_contado=esperado_mas_base)
        if self.value() == "sobrante":
            return queryset.filter(efectivo_contado__gt=esperado_mas_base)
        if self.value() == "faltante":
            return queryset.filter(efectivo_contado__lt=esperado_mas_base)
        return queryset


class CajeroQueCuadro(admin.SimpleListFilter):
    """Quién contó el dinero, **por su nombre** (`TT-176`).

    ── UN `list_filter` SOBRE LA CLAVE AJENA ENSEÑA EL `__str__` ───────────
    El de `Usuario` es «correo (rol)», así que un `list_filter = ["cajero"]`
    pone el correo de cada cajero en la barra lateral, en una pantalla que se
    cuida de no enseñarlo en ninguna columna. Es la misma trampa que `TT-168`
    pagó con `Estudiante.__str__` y el documento del menor, por otra puerta: el
    filtro, no la ficha.

    No basta con arreglar la columna: la barra lateral la pinta el admin por su
    cuenta, y el `__str__` es lo único que mira.
    ─────────────────────────────────────────────────────────────────────────

    Filtrar por cajero es lo que permite ver si los descuadres se concentran en
    una persona o están repartidos, que es el «para qué» de `HU-56`.
    """

    title = "cajero"
    parameter_name = "cajero"

    def lookups(self, request, model_admin):
        """Solo los que tienen algún cierre: una lista de todo el personal
        ofrecería filtros que no devuelven nada."""
        cajeros = (
            CierreDeCaja.objects.order_by("cajero__nombre")
            .values_list("cajero_id", "cajero__nombre")
            .distinct()
        )
        return list(cajeros)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(cajero_id=self.value())
        return queryset


@admin.register(CierreDeCaja)
class CierreDeCajaAdmin(admin.ModelAdmin):
    """El reporte de cierres de caja: el histórico, filtrable, con su
    consolidado arriba (`TT-176`, `HU-56`).

    ── EL TERCER CRITERIO NO SE CUMPLE ENSEÑANDO LA CIFRA ──────────────────
    «El efectivo esperado de un día se explica a partir de sus ventas en
    efectivo registradas» (`INVD-5`). Una columna con `$31.500` no explica
    nada: hay que creérsela.

    Por eso cada cierre trae **un enlace al reporte de ventas de esa jornada,
    ya filtrado por efectivo**. Es lo que convierte la invariante en algo que
    se comprueba en dos clics, y es el mismo razonamiento por el que la venta
    lleva su inline: un total que no se puede abrir no es auditable.
    ─────────────────────────────────────────────────────────────────────────

    **Nadie escribe un cierre desde aquí.** Un cuadre se registra en el punto
    de venta, con el efectivo esperado calculado en ese momento, o no existe
    (`INVD-5`). Las tres escrituras se niegan **y además** `ventas` está en
    `APPS_SIN_ESCRITURA_PARA_NINGUN_ROL`, así que el permiso tampoco existe en
    ningún grupo. Dos sitios, como en el resto de `INT-3`.

    **Y editar uno sería peor que registrarlo mal**: el esperado quedó
    congelado contra el dinero que alguien contó aquella tarde, y cambiarlo a
    posteriori reescribiría un descuadre ya explicado por escrito.
    """

    date_hierarchy = "fecha"
    # **Las cuatro cifras pasan por `dinero`**, ninguna cruda. El admin pinta un
    # `DecimalField` como el `Decimal` que es —«31500,00»— y la diferencia de al
    # lado sale formateada: **dos formatos de dinero en la misma fila**, que es
    # justo lo que el filtro existe para evitar. Es la misma trampa que
    # `LineaVentaInline` documenta con `precio_congelado`, y se vio en la
    # captura — la suite no la ve.
    list_display = [
        "fecha",
        "quien_cuadro",
        "esperado_de_la_jornada",
        "base_para_cambio",
        "contado_en_el_cajon",
        "diferencia_del_cierre",
        "motivo",
    ]
    list_filter = [ResultadoDelCuadre, CajeroQueCuadro]
    search_fields = ["motivo", "cajero__nombre", "cajero__email"]
    ordering = ["-fecha"]
    actions = None

    fields = [
        "fecha",
        "quien_cuadro",
        "esperado_de_la_jornada",
        "de_donde_sale_el_esperado",
        "base_para_cambio",
        "contado_en_el_cajon",
        "diferencia_del_cierre",
        "motivo",
        "creado_en",
    ]
    readonly_fields = fields

    def get_queryset(self, request):
        """Con el cajero traído y la diferencia anotada.

        La anotación es lo que permite **ordenar por la columna de diferencia**,
        que es la que se mira para encontrar el peor día del mes. Sin ella la
        columna existiría y no se podría ordenar, porque el orden lo hace la
        base y la propiedad del modelo vive en Python.
        """
        return (
            super()
            .get_queryset(request)
            .select_related("cajero")
            .annotate(diferencia_calculada=DIFERENCIA_DEL_CIERRE)
        )

    # --- Solo consulta ------------------------------------------------------

    def has_view_permission(self, request, obj=None):
        """El permiso de Django **y** el rol, como en el reporte de ventas.

        El cajero registra los cierres y **no** consulta el histórico: `[S11]`
        separa registrar de consolidar, y `HU-55` y `HU-56` son dos historias
        con dos actores distintos.
        """
        usuario = request.user
        return (
            usuario.is_authenticated
            and usuario.rol in CONSULTAN_LOS_REPORTES_DE_LA_CAFETERIA
            and super().has_view_permission(request, obj)
        )

    def has_add_permission(self, request):
        """Nunca. Un cierre se registra en el punto de venta, con el efectivo
        esperado calculado desde las ventas de esa jornada (`INVD-5`). Un alta
        por el admin escribiría la cifra a mano, que es lo que la invariante
        existe para impedir."""
        return False

    def has_change_permission(self, request, obj=None):
        """Nunca: el esperado quedó congelado contra el dinero que se contó."""
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # --- Lo que el listado enseña ------------------------------------------

    @admin.display(description="cajero", ordering="cajero__nombre")
    def quien_cuadro(self, obj):
        """El nombre de quien contó el dinero, y nada más.

        Un campo de relación se pinta con el `__str__` del modelo apuntado, y el
        de `Usuario` es «correo (rol)». El correo es una credencial de acceso y
        no hace falta para leer un cuadre; el rol es siempre el mismo — todos
        los cierres los firma un cajero.
        """
        return obj.cajero.nombre

    @admin.display(description="efectivo esperado", ordering="efectivo_esperado")
    def esperado_de_la_jornada(self, obj):
        """La suma de sus ventas en efectivo, formateada (`INVD-5`)."""
        return dinero(obj.efectivo_esperado)

    @admin.display(description="base para cambio", ordering="base")
    def base_para_cambio(self, obj):
        """Lo que había en el cajón y no salió de ninguna venta."""
        return dinero(obj.base)

    @admin.display(description="efectivo contado", ordering="efectivo_contado")
    def contado_en_el_cajon(self, obj):
        """Lo que el cajero contó, con la base incluida."""
        return dinero(obj.efectivo_contado)

    @admin.display(description="diferencia", ordering="diferencia_calculada")
    def diferencia_del_cierre(self, obj):
        """Lo que sobró o faltó, formateado donde se formatea el dinero.

        Sale de `obj.diferencia`, la propiedad del modelo: la anotación de
        `get_queryset` está para ordenar, no para que haya dos cifras. Si algún
        día dicen cosas distintas, es que alguien tocó una de las dos restas —
        y hay una prueba que lo caza.
        """
        return dinero(obj.diferencia)

    @admin.display(description="de dónde sale el esperado")
    def de_donde_sale_el_esperado(self, obj):
        """El enlace que hace comprobable `INVD-5` (`TT-176`).

        Lleva al reporte de ventas acotado a esa jornada y filtrado por
        efectivo: las mismas filas que el servicio sumó al cerrar. **Los
        parámetros son los del propio admin** —los de `date_hierarchy` y los del
        filtro de medio de pago—, no una ruta inventada: así el enlace sigue
        funcionando mientras el reporte de ventas exista, y deja de funcionar de
        forma visible si alguien le quita la navegación por fechas.
        """
        destino = reverse("admin:ventas_venta_changelist")
        consulta = urlencode(
            {
                "medio_pago__exact": MedioDePago.EFECTIVO,
                "creado_en__year": obj.fecha.year,
                "creado_en__month": obj.fecha.month,
                "creado_en__day": obj.fecha.day,
            }
        )
        return format_html(
            '<a href="{}?{}">Ver las ventas en efectivo de esa jornada</a>',
            destino,
            consulta,
        )

    # --- El consolidado del periodo que se está mirando ---------------------

    def changelist_view(self, request, extra_context=None):
        """`TT-176`. El consolidado del listado ya filtrado.

        Mismo mecanismo que los otros dos reportes: se llama a `super()` primero
        y se lee `cl.queryset` de la respuesta, que es el `QuerySet` con la
        fecha, los filtros y la búsqueda aplicados. Calcularlo por nuestra cuenta
        daría un resumen de otro conjunto **sin que nada fallara**.
        """
        # El título de fábrica es «Seleccione cierre de caja para ver», que
        # describe lo que se hace con una tabla y no lo que es esta pantalla.
        extra_context = {"title": "Reporte de cierres de caja", **(extra_context or {})}

        respuesta = super().changelist_view(request, extra_context)

        listado = getattr(respuesta, "context_data", {}).get("cl")
        if listado is not None:
            respuesta.context_data["resumen"] = resumen_de_cierres(listado.queryset)

        return respuesta
