"""Vistas de los reportes.

Solo HTTP: parsear la petición, delegar en un selector y renderizar. **Cero
lógica de negocio** (`DT-15`): quién puede ver el consumo de un estudiante lo
decide `reportes.selectors`, y esta vista solo traduce su respuesta.
"""

from datetime import timedelta

from django import forms
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from personas.models import Estudiante
from personas.selectors import estudiante_a_cargo
from reportes import reglas
from reportes.selectors import (
    OPERACIONES_MAXIMAS,
    agregados_nutricionales,
    alertas_de_frecuencia,
    auditoria,
    historial_de_consumo,
    resumen_de_auditoria,
    resumen_de_gasto,
)


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


#: Cuántos días atrás mira el reporte de auditoría cuando nadie pide un periodo.
#: Una semana: es lo que se revisa cuando algo no cuadró «esta semana», que es
#: como se pregunta. Sin ventana por defecto, la primera visita se traería el
#: libro entero para enseñar las quinientas últimas.
DIAS_DE_AUDITORIA_POR_DEFECTO = 7


class PeriodoDeAuditoriaForm(forms.Form):
    """Las dos fechas del reporte, y nada más.

    **Son fechas locales inclusivas**, como en los otros tres reportes. El
    formulario no valida que `desde` sea anterior a `hasta`: si se invierten no
    sale nada, la pantalla lo dice, y una regla más aquí sería una regla que el
    selector no tiene.
    """

    desde = forms.DateField(
        label="Desde", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    hasta = forms.DateField(
        label="Hasta", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )


@login_required
@require_http_methods(["GET"])
def auditoria_de_la_operacion(request):
    """El reporte de auditoría (`TT-178`, `HU-37`, `ALC-IN-22`).

    ── VIVE EN EL ADMIN, Y NO ES UNA TERCERA EXCEPCIÓN A `DT-2` ────────────
    Las dos excepciones declaradas —el padrón (`DT-27`) y la cola de reservas
    (`DT-34`)— son pantallas propias, con Tailwind y fuera del admin, porque las
    abre a diario alguien que no es administrador. Esta no: usa el armazón del
    admin, sus estilos y su barra, y quien la consulta ya vive ahí.

    **Lo que sí es distinto de los otros tres reportes es que no hay modelo.**
    Un `ModelAdmin` pinta el listado de *una* tabla, y la auditoría cruza
    cuatro. Por eso es una vista con su ruta, registrada **antes** de
    `admin.site.urls` en `config/urls.py`: así la URL queda `/admin/auditoria/`
    —que es donde alguien la buscaría— en vez de colgar de un modelo con el que
    no tiene que ver. Es el mismo camino que `TT-141` abrió para el historial de
    existencias, con la diferencia de que aquel sí tenía modelo del que colgar.
    ─────────────────────────────────────────────────────────────────────────

    **Se autoriza dos veces y las dos hacen falta.** `is_staff` decide si el
    armazón del admin tiene sentido para quien llama —sin él, Django lo mandaría
    a su propia pantalla de acceso—, y el selector decide si puede ver el dato.
    Un cajero tiene lo segundo en contra aunque tuviera lo primero.
    """
    if not request.user.is_staff:
        raise PermissionDenied(
            "El reporte de auditoría vive en la administración (INT-3)."
        )

    formulario = PeriodoDeAuditoriaForm(request.GET or None)
    formulario.is_valid()

    hoy = timezone.localdate()
    desde = formulario.cleaned_data.get("desde") if formulario.is_bound else None
    hasta = formulario.cleaned_data.get("hasta") if formulario.is_bound else None
    if desde is None and hasta is None:
        desde = hoy - timedelta(days=DIAS_DE_AUDITORIA_POR_DEFECTO - 1)
        hasta = hoy

    operaciones, hubo_mas = auditoria(actor=request.user, desde=desde, hasta=hasta)

    return render(
        request,
        "admin/reportes/auditoria.html",
        {
            # El contexto del admin: la barra, el selector de tema y las migas.
            # Sin él la pantalla se pintaría desnuda dentro de su propio armazón.
            **admin.site.each_context(request),
            "title": "Reporte de auditoría",
            "form": formulario,
            "desde": desde,
            "hasta": hasta,
            "operaciones": operaciones,
            "hubo_mas": hubo_mas,
            "limite": OPERACIONES_MAXIMAS,
            "resumen": resumen_de_auditoria(operaciones),
        },
    )
