"""Lecturas de los reportes (`TT-155`, `DT-15`).

**Toda lectura no trivial pasa por aquí.** Como los servicios, estos selectores
no conocen `request`: reciben el actor como argumento y devuelven datos, nunca
respuestas HTTP.

**Esta app no escribe nada**, y mientras siga así no tendrá `services.py`. Un
reporte consolida hechos que otro dominio ya asentó; si algún día uno de ellos
necesitara escribir, eso sería un hecho nuevo y no un reporte.
"""

from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db.models import (
    Case,
    Count,
    DateTimeField,
    DecimalField,
    ExpressionWrapper,
    F,
    Sum,
    When,
)
from django.db.models.functions import TruncDate
from django.utils import timezone

from cuentas.models import Rol
from reportes import reglas
from ventas.models import EstadoDelPedido, LineaVenta, OrigenDeLaVenta, Venta

# El importe de un renglón, calculado por la base: precio congelado por unidades
# (`DT-8`). Se declara aquí, una vez, porque lo usan las dos anotaciones y
# repetir la expresión es como acaban dando cifras distintas.
IMPORTE_DE_LA_LINEA = ExpressionWrapper(
    F("lineas__precio_unitario") * F("lineas__cantidad"),
    output_field=DecimalField(max_digits=12, decimal_places=2),
)

# **Cuándo se consumió un renglón**, que no siempre es cuándo se pagó (`[S2.3]`
# de `docs/reglas-de-frecuencia-de-consumo.md`). En el mostrador son el mismo
# momento; en una reserva, no: el acudiente puede pagar el domingo por la noche
# lo del lunes, y lo que la frecuencia mide es el lunes.
#
# `TruncDate` corta en la zona horaria del colegio —`America/Bogota`—, no en
# UTC: partir el día por UTC mandaría la compra de las 19:00 al día siguiente.
MOMENTO_DEL_CONSUMO = Case(
    When(
        venta__origen=OrigenDeLaVenta.RESERVA,
        then=F("venta__pedido_anticipado__entregado_en"),
    ),
    default=F("venta__creado_en"),
    output_field=DateTimeField(),
)
DIA_DEL_CONSUMO = TruncDate(MOMENTO_DEL_CONSUMO)


def _solo_su_acudiente(actor, estudiante):
    """`[S11]`: el consumo de un estudiante lo consulta **su** acudiente.

    La fila «Consultar reportes de consumo de su hijo» de `[S11]` concede a
    `USR-2` y **a ningún otro rol**: ni la cafetería, ni la institución. Es el
    segundo criterio de `HU-30` y la comprobación vive en la capa de datos, no
    en un enlace que no se dibuja (`DT-11`, `INV-4`) — quien escriba la URL a
    mano recibe lo mismo.

    **Que sean suyos es la mitad que se olvida**, y aquí más que en ninguna otra
    puerta: lo que hay detrás es el registro de lo que un menor come y a qué hora
    está en la cafetería. Un acudiente identificado es un actor legítimo; leer el
    consumo del hijo de otro no lo es. Por eso se comprueba el vínculo, no el
    rol.

    Se mira `estudiante.acudiente.usuario_id` y no se vuelve a consultar la lista
    de estudiantes a cargo: es la misma condición que `personas.selectors`
    filtra, resuelta sobre una fila que la vista ya trajo.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Consultar el consumo exige identificarse.")
    if actor.rol != Rol.ACUDIENTE:
        raise PermissionDenied(
            "El historial de consumo de un estudiante es de su acudiente, y de "
            "ningún otro rol (HU-30, [S11])."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")
    if estudiante is None or estudiante.acudiente.usuario_id != actor.id:
        raise PermissionDenied(
            "Solo se consulta el consumo de los estudiantes a cargo de quien "
            "pregunta."
        )


def historial_de_consumo(*, actor, estudiante):
    """Las compras de un estudiante, de la más reciente a la más antigua.

    `TT-155`, `HU-30`, `ALC-IN-20`. Devuelve un `QuerySet` de `Venta` con sus
    líneas ya traídas: cada una lleva **lo que el producto declaraba al
    venderse**, no lo que declara hoy.

    ── LEE LA INSTANTÁNEA, NUNCA EL PRODUCTO ───────────────────────────────
    El precio y los nutrientes salen de `LineaVenta`, que los copió al asentar
    la venta (`TT-84`, `DT-8`). El producto se trae **solo por el nombre**, que
    no se copia porque la clave ajena va con `PROTECT` y siempre se puede leer.

    Si alguien sustituye aquí un campo de la línea por el del producto, editar
    un precio reescribiría lo que costó el mes pasado y corregir una ficha
    nutricional cambiaría lo que un niño comió: el historial dejaría de ser un
    historial para ser una proyección del catálogo de hoy sobre el pasado, y
    `HU-22` quedaría rota hacia atrás sin que nada fallara.
    ─────────────────────────────────────────────────────────────────────────

    ── LAS RESERVAS ENTRAN, Y LA PANTALLA DICE EN QUÉ ESTADO ESTÁN ─────────
    Una reserva **es una venta** (`DT-32`): está pagada, tiene sus líneas y su
    instantánea. Esconder las que todavía no se han entregado dejaría fuera del
    historial dinero que ya salió de la billetera. Por eso se traen todas y
    `pedido_anticipado` viene resuelto, para que la pantalla pueda distinguir lo
    consumido de lo que está esperando en el mostrador.
    ─────────────────────────────────────────────────────────────────────────

    **Las ventas a cliente genérico no aparecen y no hay que excluirlas**
    (`DEC-1`, `HU-53`): no tienen estudiante, así que el filtro no las alcanza.
    Ese es justamente el motivo por el que la venta genérica no tiene historial
    de nadie.

    `total` y `unidades` se anotan en la base. `total` es la misma suma que
    `ventas.services.total_de` —precio congelado por unidades—, calculada aquí
    por SQL porque esta pantalla lista muchas ventas y aquella recorre las
    líneas de una sola. `reportes/tests_historial.py` compara las dos cifras
    para que no puedan separarse en silencio.

    **Sin límite ni paginación**, y es deliberado: `HU-30` pide el historial, no
    su última página. Recortarlo por comodidad dejaría al acudiente creyendo que
    eso es todo lo que su hijo compró.
    """
    _solo_su_acudiente(actor, estudiante)

    return (
        Venta.objects.filter(estudiante=estudiante)
        # `pedido_anticipado` es un uno a uno inverso: entra en el
        # `select_related` y ahorra una consulta por reserva al pintar su estado.
        .select_related("pedido_anticipado")
        .prefetch_related("lineas__producto")
        .annotate(total=Sum(IMPORTE_DE_LA_LINEA), unidades=Sum("lineas__cantidad"))
        # El orden lo fija el modelo —`-creado_en`— y se repite aquí de forma
        # explícita, como en `billetera.selectors.historial_de`: quien lea esta
        # función no tiene por qué ir al `Meta` a averiguar cómo llega un
        # historial.
        .order_by("-creado_en")
    )


def dias_de_consumo_por_categoria(*, actor, estudiante, hoy=None):
    """`{categoría: días distintos con consumo}` en la ventana de la regla.

    `TT-159`, `HU-31`. Es lo único que la base tiene que contar para que
    `reportes.reglas` decida: **días distintos, no unidades ni importe**
    (`[S2.1]`). Dos empanadas el mismo martes son un día de `Almuerzo`.

    ── QUÉ ENTRA, Y POR QUÉ NO ES LO MISMO QUE EN EL HISTORIAL ─────────────
    El historial de `HU-30` enseña **todas** las compras, reservas sin recoger
    incluidas. Aquí no: una reserva pagada que sigue en el mostrador todavía no
    se ha consumido, y contarla diría que el estudiante comió algo que no ha
    recogido (`[S2.3]`).

    No es una contradicción entre las dos lecturas: un historial responde «qué
    se ha comprado» y esta regla responde «con qué frecuencia se ha consumido».
    ─────────────────────────────────────────────────────────────────────────

    ── LA CATEGORÍA SE LEE DEL PRODUCTO, Y ES LA ÚNICA CIFRA QUE NO ES DT-8 ─
    `TT-84` congeló en la línea el precio y los nutrientes, **no la categoría**:
    no hay nada que congelar. Si la cafetería mueve un producto de `Panadería` a
    `Almuerzo`, la pregunta «¿cada cuánto come de esto?» se responde con la
    clasificación vigente. Está razonado en `[S2.4]`.
    ─────────────────────────────────────────────────────────────────────────

    `hoy` existe para las pruebas y para poder mirar otra jornada; por defecto
    es hoy en la zona horaria del colegio. La ventana lo **incluye**, así que
    son `DIAS_DE_LA_VENTANA` días contando el de hoy.

    **`alias()` y no `annotate()` para el día**, y esa distinción no es de
    estilo: lo que se anota antes de un `values()` entra en el `GROUP BY`, y el
    recuento saldría agrupado por categoría **y por día** —una fila por día, con
    un uno en cada una—. `alias()` deja filtrar por la expresión sin
    seleccionarla. El fallo sería silencioso: cifras bien formadas, todas a uno.
    """
    _solo_su_acudiente(actor, estudiante)

    if hoy is None:
        hoy = timezone.localdate()
    desde = hoy - timedelta(days=reglas.DIAS_DE_LA_VENTANA - 1)

    recuento = (
        LineaVenta.objects.filter(venta__estudiante=estudiante)
        # La reserva sin entregar no cuenta. Se excluye por el estado del pedido
        # y no dejando que su fecha nula se caiga del rango: la regla dice «lo
        # que todavía no se ha recogido no se ha consumido», y eso merece
        # leerse en el código tal cual, no deducirse de cómo compara un nulo.
        .exclude(
            venta__origen=OrigenDeLaVenta.RESERVA,
            venta__pedido_anticipado__estado=EstadoDelPedido.PENDIENTE,
        )
        .alias(dia=DIA_DEL_CONSUMO)
        .filter(dia__gte=desde, dia__lte=hoy)
        .values("producto__categoria__nombre")
        .annotate(dias=Count(DIA_DEL_CONSUMO, distinct=True))
    )

    return {fila["producto__categoria__nombre"]: fila["dias"] for fila in recuento}


def alertas_de_frecuencia(*, actor, estudiante, hoy=None):
    """Las alertas de frecuencia de un estudiante (`TT-159`, `HU-31`).

    Junta las dos mitades: la base cuenta los días y `reportes.reglas` decide si
    alguno pasa de un umbral. **El veredicto no se calcula aquí a propósito** —
    los umbrales son una decisión de análisis (`TT-158`, `[S12]`) y viven en un
    módulo puro que se puede leer y probar sin sembrar catorce días de ventas.

    Devuelve una lista, ya ordenada, que puede estar vacía: **lo normal es que no
    haya ninguna alerta**, y eso no es un hueco ni un error. Por debajo del
    umbral no se publica nada, ni siquiera un «va bien» — decirlo sería la
    valoración nutricional que `ALC-OUT-20` excluye.

    **Quien las pinte se lleva el aviso de `INV-9` con ellas**: en la plantilla
    son el mismo fragmento (`TT-161`, `[S5]`). Esta función no lo sabe ni tiene
    por qué, pero quien añada una segunda pantalla que la llame, sí.
    """
    return reglas.evaluar(
        dias_de_consumo_por_categoria(actor=actor, estudiante=estudiante, hoy=hoy)
    )
