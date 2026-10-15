"""`INT-3` para las ventas: **el reporte de cierres de caja, solo consulta**
(`TT-176`, `HU-56`).

`[S11]` concede «consultar reportes de ventas e inventario» a `USR-4` y a nadie
más. El de cierres vive aquí por el camino que `TT-141` abrió: el admin da el
listado, los filtros y la navegación por fechas, y lo que se añade es lo que el
admin no sabe hacer solo — **el consolidado del periodo que se está mirando**.

**El reporte de ventas ya no está aquí** (`DT-54`): es una pantalla propia,
`/ventas/`, con barras, tarjetas y una modal por día que el admin no carga. Lo
que lo cose con este reporte es un enlace — cada cierre lleva a las ventas en
efectivo del día que explican su cifra (`INVD-5`).

── NADIE ESCRIBE AQUÍ, Y NO ES QUE NO SE CONCEDA ───────────────────────────
Un cierre es un asiento: no se edita ni se borra (`INVD-5`). Se registra en el
punto de venta con el efectivo esperado calculado en ese momento, o no existe.
Aquí se niegan las tres escrituras **y además** `ventas` entra en
`APPS_SIN_ESCRITURA_PARA_NINGUN_ROL`, así que el permiso tampoco existe en
ningún grupo. Dos sitios, como en el resto de `INT-3`.
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
)
from ventas.models import CierreDeCaja, MedioDePago
from ventas.selectors import DIFERENCIA_DEL_CIERRE


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
    # justo lo que el filtro existe para evitar. Se vio en la captura — la
    # suite no la ve.
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
        """El enlace que hace comprobable `INVD-5` (`TT-176`, `DT-54`).

        Lleva al reporte de ventas con la modal de esa jornada abierta y
        filtrada por efectivo: las mismas ventas que el servicio sumó al
        cerrar. La ruta se resuelve por su nombre, así que renombrarla rompe
        aquí con `NoReverseMatch` en vez de dejar un enlace muerto.
        """
        destino = reverse("ventas-del-dia", args=[obj.fecha.isoformat()])
        consulta = urlencode({"medio": MedioDePago.EFECTIVO})
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
