"""Vistas de los reportes.

Solo HTTP: parsear la petición, delegar en un selector y renderizar. **Cero
lógica de negocio** (`DT-15`): quién puede ver el consumo de un estudiante lo
decide `reportes.selectors`, y esta vista solo traduce su respuesta.
"""

import uuid
from datetime import date, timedelta
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from billetera.templatetags.dinero import dinero
from personas.models import Estudiante
from personas.selectors import estudiante_a_cargo
from reportes import reglas
from reportes.selectors import UMBRAL_DE_EXISTENCIAS_BAJAS
from reportes.selectors import panel_de_la_cafeteria as selectores_del_panel
from reportes.selectors import (
    CLASES_DE_OPERACION,
    OPERACIONES_MAXIMAS,
    agregados_nutricionales,
    alertas_de_frecuencia,
    auditoria,
    historial_de_consumo,
    ORDENES_DE_LOS_CIERRES,
    RESULTADOS_DEL_CUADRE,
    cierre_de_la_cafeteria,
    reporte_de_cierres,
    reporte_de_ventas,
    resumen_de_auditoria,
    resumen_de_gasto,
    venta_de_la_cafeteria,
    ventas_del_dia,
    ventas_registradas,
)
from ventas.models import MedioDePago


@login_required
@require_http_methods(["GET"])
def consumo_del_estudiante(request, estudiante_id):
    """El historial de consumo de un estudiante a cargo (`TT-156`, `HU-30`).

    **Una página entera, no un fragmento** (`DT-16`): se llega desde la ficha
    del panel y se lee de arriba abajo. No hay nada que intercambiar.

    ── SE AUTORIZA DOS VECES, Y LAS DOS HACEN FALTA ────────────────────────
    `estudiante_a_cargo` resuelve la fila y, al hacerlo, decide: un estudiante
    ajeno no se distingue de uno inexistente —los dos son `404`— porque un `403`
    le confirmaría a un desconocido que ese estudiante existe. El selector
    vuelve a comprobarlo sobre la fila ya traída, y esa repetición no sobra: es
    la que protege el dato entre por donde entre (`DT-11`, `DT-15`).

    Un rol que no sea acudiente recibe `403` antes de que se mire ningún
    identificador, porque `estudiantes_a_cargo` rechaza el rol primero.
    ─────────────────────────────────────────────────────────────────────────
    """
    try:
        estudiante = estudiante_a_cargo(
            usuario=request.user, estudiante_id=estudiante_id
        )
    except Estudiante.DoesNotExist:
        raise Http404("Ese estudiante no está a tu cargo.") from None

    compras = historial_de_consumo(actor=request.user, estudiante=estudiante)

    return render(
        request,
        "reportes/historial-de-consumo.html",
        {
            "estudiante": estudiante,
            "compras": compras,
            # `TT-160`, `HU-31`. Las alertas van en la misma pantalla que el
            # historial **a propósito**: cada una dice su umbral, y con las
            # compras debajo el acudiente puede contar los días y comprobarla.
            # En otra pantalla habría que creérsela.
            "alertas": alertas_de_frecuencia(
                actor=request.user, estudiante=estudiante
            ),
            # `TT-164`, `HU-32`. La comparación con la referencia sanitaria, en
            # la misma ventana que las alertas: dos periodos distintos en la
            # misma pantalla serían dos pantallas.
            "aporte": agregados_nutricionales(
                actor=request.user, estudiante=estudiante
            ),
            # `TT-166`, `HU-33`. El gasto frente a lo recargado, en la misma
            # ventana. **Ojo: sus fechas son las de los movimientos**, no las
            # del consumo — el dinero de una reserva sale al reservar.
            "gasto": resumen_de_gasto(actor=request.user, estudiante=estudiante),
            # La ventana y el umbral se pasan para que la pantalla los diga sin
            # tenerlos escritos a mano: son una decisión de análisis (`TT-158`)
            # y viven en un solo sitio. Una plantilla con el «14» tecleado se
            # queda mintiendo el día que la regla cambie.
            "ventana_de_frecuencia": reglas.DIAS_DE_LA_VENTANA,
            "umbral_de_frecuencia": reglas.UMBRAL_FRECUENCIA_ALTA,
        },
    )


#: El atajo con el que abre la auditoría cuando nadie pide un periodo: una
#: semana. Es lo que se revisa cuando algo no cuadró «esta semana», que es como
#: se pregunta, y sin ventana la primera visita se traería el libro entero para
#: enseñar las quinientas últimas. Los otros dos reportes abren en treinta.
ATAJO_DE_LA_AUDITORIA = "7"


@login_required
@require_http_methods(["GET"])
def auditoria_de_la_operacion(request):
    """El reporte de auditoría (`TT-178`, `HU-37`, `ALC-IN-22`, `DT-56`).

    **Una pantalla propia**, como los reportes de ventas y de cierres a los que
    enlaza: abrir una venta o un cierre desde la línea de tiempo ya no salta de
    un armazón a otro, porque se abren en la modal de esta misma pantalla.

    El periodo es el de los otros reportes, con siete días por defecto: una
    auditoría se consulta acotada —«qué pasó el martes»—. **Las cifras por clase
    son del periodo entero** y la línea de tiempo, de la clase elegida: las
    cifras son la navegación, y no se vacían al pulsar una.

    El rol lo exige el selector, antes de leer nada.
    """
    desde, hasta, atajo, aviso = periodo_pedido(
        request.GET, timezone.localdate(), por_defecto=ATAJO_DE_LA_AUDITORIA
    )
    clase = request.GET.get("clase")
    if clase not in dict(CLASES_DE_OPERACION):
        clase = None

    todas, hubo_mas_en_todas = auditoria(actor=request.user, desde=desde, hasta=hasta)
    if clase:
        operaciones, hubo_mas = auditoria(
            actor=request.user, desde=desde, hasta=hasta, clases={clase}
        )
    else:
        operaciones, hubo_mas = todas, hubo_mas_en_todas

    resumen = resumen_de_auditoria(todas)
    periodo = (
        {"periodo": atajo} if atajo else
        {k: v.isoformat() for k, v in (("desde", desde), ("hasta", hasta)) if v}
    )

    return render(request, "reportes/auditoria.html", {
        "desde": desde,
        "hasta": hasta,
        "atajos": ATAJOS_DEL_PERIODO,
        "atajo": atajo,
        "personalizado": atajo is None,
        "aviso": aviso,
        "clase": clase,
        "etiqueta_de_la_clase": dict(CLASES_DE_OPERACION).get(clase),
        "clases": tuple(
            (valor, etiqueta, cuantas)
            for (valor, etiqueta), (_, cuantas) in zip(CLASES_DE_OPERACION, resumen.por_clase)
        ),
        "resumen": resumen,
        "operaciones": operaciones,
        "por_dia": _por_dia(operaciones),
        "hubo_mas": hubo_mas,
        "cifras_recortadas": hubo_mas_en_todas,
        "limite": OPERACIONES_MAXIMAS,
        # Las cifras por clase enlazan conservando el periodo; las fechas se
        # envían conservando la clase.
        "periodo_en_la_url": urlencode(periodo),
    })


def _por_dia(operaciones):
    """`((día, [operaciones]), …)`, del más reciente al más antiguo. Se agrupa
    aquí y no en la plantilla: `{% regroup %}` agruparía por la fecha en UTC
    si alguien le pasara el instante sin convertir."""
    grupos = {}
    for operacion in operaciones:
        grupos.setdefault(timezone.localdate(operacion.cuando), []).append(operacion)
    return tuple(grupos.items())


@login_required
@require_http_methods(["GET"])
def panel_de_la_cafeteria(request):
    """La pantalla de aterrizaje de `USR-4` (`DEC-16`).

    **Es el índice del rol, no un reporte más.** Los cuatro reportes responden
    «qué pasó en este periodo, con estos filtros»; esta responde «cómo va hoy y
    qué conviene mirar», que es otra pregunta y se hace todos los días. Por eso
    no tiene filtros: cada bloque enlaza al reporte que sí los tiene.

    **Vive en el armazón de la aplicación, no en el del admin** (`DT-53`): es la
    pantalla más diaria del rol, y todo lo que la administración escribe ya vive
    fuera. Los reportes a los que enlaza sí siguen en el admin.

    El rol lo exige el selector, antes de leer nada (`[S11]`).
    """
    panel = selectores_del_panel(actor=request.user)

    return render(
        request,
        "reportes/panel-de-la-cafeteria.html",
        {
            "panel": panel,
            "umbral": UMBRAL_DE_EXISTENCIAS_BAJAS,
            # Presentación: el rótulo y la marca de cada grupo del aviso (`DEC-25`).
            "grupos_de_existencias": (
                ("Agotados", panel.agotados, "agotados"),
                ("Quedan pocas", panel.quedan_pocas, "quedan-pocas"),
            ),
            "tarjetas": _tarjetas_de_la_jornada(panel),
            "mas_vendidos": panel.mas_vendidos,
        },
    )


def _tarjetas_de_la_jornada(panel):
    """Los cinco rótulos de la fila de arriba.

    Se arman en la vista porque son **presentación**: rótulo, frase de apoyo,
    icono y color de cada una. Las cifras vienen ya calculadas del selector;
    aquí no se suma nada.

    **Las clases van escritas enteras**, nunca como `bg-{{ serie }}`: Tailwind
    compila lo que encuentra escrito, y una clase armada en la plantilla no
    existe. Así se quedaron sin franja cuatro de las cinco. Este fichero está en
    las fuentes de `estilos/fuente.css` para que las encuentre.

    La franja y el icono usan `serie-*` y nunca un color de estado: es
    decoración, y el rojo y el ámbar significan otra cosa en este producto.

    **Sin enlace en cada tarjeta.** Cuatro de las cinco llevaban a la misma
    lista de ventas, que ya enlazan dos bloques más abajo: cuatro veces el mismo
    destino no es navegación, es ruido.
    """
    por_medio = dict((etiqueta, total) for etiqueta, _, total in panel.de_hoy.por_medio_de_pago)

    return (
        {
            "rotulo": "En caja hoy",
            "cifra": dinero(por_medio.get("Efectivo"), "COP"),
            "apoyo": "Cobrado en efectivo",
            "icono": "i-efectivo",
            "franja": "from-serie-1 to-serie-1/40",
            "insignia": "bg-serie-1/12 text-serie-1",
        },
        {
            "rotulo": "Transferencias hoy",
            "cifra": dinero(por_medio.get("Transferencia"), "COP"),
            "apoyo": "Cobrado en transferencia",
            "icono": "i-transferencia",
            "franja": "from-serie-2 to-serie-2/40",
            "insignia": "bg-serie-2/12 text-serie-2",
        },
        {
            "rotulo": "Con billetera hoy",
            "cifra": dinero(por_medio.get("Billetera"), "COP"),
            "apoyo": "Descontado del saldo de las familias",
            "icono": "i-saldo",
            "franja": "from-serie-3 to-serie-3/40",
            "insignia": "bg-serie-3/12 text-serie-3",
        },
        {
            "rotulo": "Ventas de hoy",
            "cifra": panel.de_hoy.cuantas,
            "apoyo": (
                f"Ticket medio de {dinero(panel.ticket_medio)}"
                if panel.ticket_medio is not None
                else "Todavía no se ha cobrado nada"
            ),
            "icono": "i-recibo",
            "franja": "from-serie-4 to-serie-4/40",
            "insignia": "bg-serie-4/12 text-serie-4",
        },
        {
            "rotulo": "Recargado hoy",
            "cifra": dinero(panel.recargado_hoy, "COP"),
            "apoyo": "Lo que las familias añadieron a las billeteras",
            "icono": "i-tendencia",
            "franja": "from-serie-5 to-serie-5/40",
            "insignia": "bg-serie-5/12 text-serie-5",
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# EL REPORTE DE VENTAS (`HU-35`, `DT-54`)
#
# Una pantalla propia, fuera del admin. **El periodo va en la URL**: los atajos
# son enlaces y las dos fechas, un formulario `GET`, así que se puede volver a
# un periodo y compartirlo. Cada modal tiene dos rutas (`DT-16`): la página con
# la modal ya abierta —a la que enlazan el cierre de caja y la auditoría— y el
# fragmento que la rellena.
# ──────────────────────────────────────────────────────────────────────────────

#: Los atajos del periodo, en el orden en que se pintan. `None` es «todo».
ATAJOS_DEL_PERIODO = (("7", "Últimos 7 días", 7), ("30", "Últimos 30 días", 30),
                      ("90", "Últimos 90 días", 90), ("todo", "Todo", None))
ATAJO_POR_DEFECTO = "30"


def _fecha(texto):
    try:
        return date.fromisoformat(texto) if texto else None
    except ValueError:
        return None


def periodo_pedido(parametros, hoy, por_defecto=ATAJO_POR_DEFECTO):
    """`(desde, hasta, atajo, aviso)` a partir de la URL.

    Dos fechas mandan sobre el atajo; una sola deja el otro extremo abierto. Una
    fecha que no se entiende se ignora. **Si llegan al revés, se intercambian y
    se dice**: devolver un periodo vacío se leería como «no hubo ventas».
    """
    desde, hasta = _fecha(parametros.get("desde")), _fecha(parametros.get("hasta"))
    if desde or hasta:
        aviso = ""
        if desde and hasta and desde > hasta:
            desde, hasta = hasta, desde
            aviso = "Las fechas estaban al revés: se muestra del más antiguo al más reciente."
        return desde, hasta, None, aviso

    atajo = parametros.get("periodo")
    dias = {clave: n for clave, _, n in ATAJOS_DEL_PERIODO}
    if atajo not in dias:
        atajo = por_defecto
    if dias[atajo] is None:
        return None, None, atajo, ""
    return hoy - timedelta(days=dias[atajo] - 1), hoy, atajo, ""


def _medio(texto):
    return texto if texto in MedioDePago.values else None


def _pantalla_de_ventas(request, *, desde, hasta, atajo, aviso="", abrir=None):
    return render(request, "reportes/ventas.html", {
        "reporte": reporte_de_ventas(actor=request.user, desde=desde, hasta=hasta),
        "atajos": ATAJOS_DEL_PERIODO,
        "atajo": atajo,
        "personalizado": atajo is None,
        "aviso": aviso,
        "abrir": abrir,
    })


@login_required
@require_http_methods(["GET"])
def ventas(request):
    """El reporte de ventas de un periodo (`HU-35`, `DT-54`)."""
    desde, hasta, atajo, aviso = periodo_pedido(request.GET, timezone.localdate())
    return _pantalla_de_ventas(request, desde=desde, hasta=hasta, atajo=atajo, aviso=aviso)


@login_required
@require_http_methods(["GET"])
def ventas_de_un_dia(request, fecha):
    """La pantalla acotada a ese día, con su modal abierta. Es donde aterriza
    «Ver las ventas en efectivo de esa jornada» del cierre de caja (`INVD-5`)."""
    # El rol antes que el `404`: una fecha mal escrita no le dice nada a otro rol.
    ventas_registradas(actor=request.user)
    dia = _fecha(fecha)
    if dia is None:
        raise Http404("Esa no es una fecha.")
    medio = _medio(request.GET.get("medio"))
    ficha = reverse("ventas-del-dia-ficha", args=[dia.isoformat()])
    if medio:
        ficha += f"?medio={medio}"
    return _pantalla_de_ventas(request, desde=dia, hasta=dia, atajo=None, abrir=ficha)


@login_required
@require_http_methods(["GET"])
def ficha_de_ventas_del_dia(request, fecha):
    """Las ventas de un día, en la modal: fragmento (`DT-16`)."""
    ventas_registradas(actor=request.user)
    dia = _fecha(fecha)
    if dia is None:
        raise Http404("Esa no es una fecha.")
    medio = _medio(request.GET.get("medio"))
    del_dia = ventas_del_dia(actor=request.user, fecha=dia, medio=medio)
    return render(request, "reportes/partials/ventas-del-dia.html", {
        "dia": dia,
        "medio": MedioDePago(medio).label if medio else None,
        "ventas": del_dia,
        # Las ventas ya vienen con su total anotado: sumarlas aquí no es lógica
        # de negocio, es el pie de lo que la modal enseña.
        "total": sum(v.total_cobrado for v in del_dia),
    })


@login_required
@require_http_methods(["GET"])
def venta(request, venta_id):
    """La pantalla acotada al día de esa venta, con su modal abierta. Es donde
    aterriza la auditoría (`DT-48`), también para un pedido cancelado."""
    encontrada = venta_de_la_cafeteria(actor=request.user, venta_id=venta_id)
    if encontrada is None:
        raise Http404("No hay ninguna venta con ese identificador.")
    dia = timezone.localdate(encontrada.creado_en)
    return _pantalla_de_ventas(
        request, desde=dia, hasta=dia, atajo=None,
        abrir=reverse("venta-ficha", args=[venta_id]),
    )


@login_required
@require_http_methods(["GET"])
def ficha_de_venta(request, venta_id):
    """Una venta, en la modal: fragmento (`DT-16`)."""
    encontrada = venta_de_la_cafeteria(actor=request.user, venta_id=venta_id)
    if encontrada is None:
        raise Http404("No hay ninguna venta con ese identificador.")
    return render(request, "reportes/partials/venta.html", {"venta": encontrada})


# ──────────────────────────────────────────────────────────────────────────────
# EL REPORTE DE CIERRES DE CAJA (`HU-56`, `DT-55`)
#
# El mismo periodo que las ventas, sobre la jornada cuadrada, y los filtros que
# tenía el admin. **Todo va en la URL**: el periodo, el resultado, el cajero, la
# búsqueda y el orden. Cada formulario lleva en campos ocultos lo que el otro
# decide, para que cambiar una cosa no borre la otra.
# ──────────────────────────────────────────────────────────────────────────────


def _filtros_de_cierres(parametros):
    """Los filtros de la URL, con lo que no se reconozca descartado."""
    resultado = parametros.get("resultado")
    if resultado not in dict(RESULTADOS_DEL_CUADRE):
        resultado = None
    orden = parametros.get("orden")
    if orden not in dict(ORDENES_DE_LOS_CIERRES):
        orden = "fecha"
    try:
        cajero = uuid.UUID(parametros.get("cajero", ""))
    except ValueError:
        cajero = None
    return {
        "resultado": resultado,
        "cajero": cajero,
        "busqueda": parametros.get("q", "").strip(),
        "orden": orden,
    }


def _pantalla_de_cierres(request, *, desde, hasta, atajo, aviso="", filtros=None, abrir=None):
    filtros = filtros or _filtros_de_cierres({})
    periodo = (
        {"periodo": atajo} if atajo else
        {k: v.isoformat() for k, v in (("desde", desde), ("hasta", hasta)) if v}
    )
    en_la_url = {
        k: v for k, v in (
            ("resultado", filtros["resultado"]),
            ("cajero", filtros["cajero"] and str(filtros["cajero"])),
            ("q", filtros["busqueda"]),
            ("orden", filtros["orden"] if filtros["orden"] != "fecha" else None),
        ) if v
    }
    return render(request, "reportes/cierres.html", {
        "reporte": reporte_de_cierres(actor=request.user, desde=desde, hasta=hasta, **filtros),
        "atajos": ATAJOS_DEL_PERIODO,
        "atajo": atajo,
        "personalizado": atajo is None,
        "aviso": aviso,
        "abrir": abrir,
        "filtros": filtros,
        "resultados": RESULTADOS_DEL_CUADRE,
        "ordenes": ORDENES_DE_LOS_CIERRES,
        # Lo que cada formulario reenvía en campos ocultos, y lo que los atajos
        # añaden a su enlace.
        "periodo_oculto": tuple(periodo.items()),
        "filtros_ocultos": tuple(en_la_url.items()),
        "filtros_en_la_url": urlencode(en_la_url),
        "hay_filtros": bool(en_la_url.keys() - {"orden"}),
    })


@login_required
@require_http_methods(["GET"])
def cierres(request):
    """El reporte de cierres de caja de un periodo (`HU-56`, `DT-55`)."""
    desde, hasta, atajo, aviso = periodo_pedido(request.GET, timezone.localdate())
    return _pantalla_de_cierres(
        request, desde=desde, hasta=hasta, atajo=atajo, aviso=aviso,
        filtros=_filtros_de_cierres(request.GET),
    )


@login_required
@require_http_methods(["GET"])
def cierre(request, cierre_id):
    """La pantalla acotada a la jornada de ese cierre, con su modal abierta. Es
    donde aterriza la auditoría."""
    encontrado = cierre_de_la_cafeteria(actor=request.user, cierre_id=cierre_id)
    if encontrado is None:
        raise Http404("No hay ningún cierre con ese identificador.")
    return _pantalla_de_cierres(
        request, desde=encontrado.fecha, hasta=encontrado.fecha, atajo=None,
        abrir=reverse("cierre-de-caja-ficha", args=[cierre_id]),
    )


@login_required
@require_http_methods(["GET"])
def ficha_de_cierre(request, cierre_id):
    """Un cierre, en la modal: fragmento (`DT-16`)."""
    encontrado = cierre_de_la_cafeteria(actor=request.user, cierre_id=cierre_id)
    if encontrado is None:
        raise Http404("No hay ningún cierre con ese identificador.")
    return render(request, "reportes/partials/cierre.html", {
        "cierre": encontrado,
        "ventas_en_efectivo": (
            f"{reverse('ventas-del-dia', args=[encontrado.fecha.isoformat()])}"
            f"?{urlencode({'medio': MedioDePago.EFECTIVO})}"
        ),
    })
