"""Vistas de los reportes.

Solo HTTP: parsear la petición, delegar en un selector y renderizar. **Cero
lógica de negocio** (`DT-15`): quién puede ver el consumo de un estudiante lo
decide `reportes.selectors`, y esta vista solo traduce su respuesta.
"""

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from personas.models import Estudiante
from personas.selectors import estudiante_a_cargo
from reportes import reglas
from reportes.selectors import (
    agregados_nutricionales,
    alertas_de_frecuencia,
    historial_de_consumo,
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
            # La ventana y el umbral se pasan para que la pantalla los diga sin
            # tenerlos escritos a mano: son una decisión de análisis (`TT-158`)
            # y viven en un solo sitio. Una plantilla con el «14» tecleado se
            # queda mintiendo el día que la regla cambie.
            "ventana_de_frecuencia": reglas.DIAS_DE_LA_VENTANA,
            "umbral_de_frecuencia": reglas.UMBRAL_FRECUENCIA_ALTA,
        },
    )
