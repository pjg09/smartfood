"""Vistas de institución educativa, estudiantes y acudientes.

Solo HTTP: parsear la petición, delegar en un servicio o un selector, y
renderizar. **Cero lógica de negocio** (`DT-15`).

Una vista HTMX devuelve **un fragmento, nunca una página** (`DT-16`).
"""

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from billetera.selectors import historial_de, saldo_de
from cuentas.models import Rol
from personas.carga import ArchivoIlegible
from personas.models import Estudiante, Institucion
from personas.selectors import (
    cuentas_sin_activar,
    estudiante_a_cargo,
    estudiante_para_la_institucion,
    estudiantes_a_cargo,
    padron,
)
from personas.services import cargar_estudiantes_y_acudientes
from personas.tarjeta import ancho_mm, svg_del_codigo
from personas.validacion import ArchivoInvalido
from restricciones.selectors import limite_diario_de, productos_bloqueados_de


class ArchivoDeCargaForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo de estudiantes",
        help_text="CSV en UTF-8, con las cinco columnas del formato acordado.",
    )


@login_required
@require_http_methods(["GET", "POST"])
def carga_de_estudiantes(request):
    """Pantalla de carga masiva (`TT-24`, `HU-01`).

    La vista **no decide quién puede cargar**: se lo pregunta al servicio, que
    es donde vive la regla (`DT-15`). Aquí solo se corta antes para no enseñar
    un formulario que va a fallar.
    """
    if request.user.rol != Rol.INSTITUCION:
        raise PermissionDenied(
            "Cargar estudiantes es función exclusiva de la institución educativa."
        )

    contexto = {
        "form": ArchivoDeCargaForm(),
        "resultado": None,
        "error": None,
        "errores": None,
    }

    if request.method == "POST":
        form = ArchivoDeCargaForm(request.POST, request.FILES)
        contexto["form"] = form

        if form.is_valid():
            try:
                contexto["resultado"] = cargar_estudiantes_y_acudientes(
                    actor=request.user,
                    archivo=form.cleaned_data["archivo"],
                )
            except ArchivoIlegible as error:
                # El archivo que ni siquiera se puede leer como CSV.
                contexto["error"] = str(error)
            except ArchivoInvalido as error:
                # `HU-02`, tercer criterio: el reporte identifica los errores
                # encontrados. Van todos, no el primero.
                contexto["errores"] = error.errores

    return render(request, "personas/carga-de-estudiantes.html", contexto)


# Cuántos movimientos se enseñan bajo el saldo (`TT-64`, `HU-07`).
#
# Cinco, y no «el historial»: lo que la historia pide es saber **si hace falta
# recargar**, y para eso basta con ver lo último que pasó. Un extracto completo
# en la misma pantalla empuja el resto del panel fuera de la vista en un
# teléfono, que es desde donde entra el acudiente (`INT-1`).
ULTIMOS_MOVIMIENTOS = 5


def _contexto_del_estudiante(estudiante):
    """Lo que la ficha de un estudiante necesita, venga de la página o del fragmento.

    **La misma función para los dos caminos**, a propósito: la página y el
    fragmento HTMX pintan la misma plantilla (`DT-16`), y armar el contexto dos
    veces es cómo acaban enseñando cosas distintas.

    El saldo lo calcula `billetera`, sumando el historial (`INV-2`). Aquí es
    donde se juntan los dos dominios, y es el sitio correcto: **una vista
    compone**. La dependencia entre modelos sigue yendo en un solo sentido —
    `billetera` conoce a `personas` y no al revés.

    `TT-96` añade el límite diario por la misma puerta y con el mismo argumento:
    `restricciones` conoce a `personas`, y es la vista la que junta las dos
    lecturas para pintar la ficha. Puede ser `None`, y ese caso no es un hueco:
    significa que el acudiente no fijó cupo, que es distinto de un cupo de cero
    (`restricciones.models.LimiteDiario`).

    `TT-99` añade el recuento de productos bloqueados. Es un `count()` y no la
    lista: la tarjeta solo dice cuántos hay, y traerlos todos para contarlos
    sería pedirle a la base un trabajo que la pantalla no usa.
    """
    return {
        "seleccionado": estudiante,
        "saldo": saldo_de(estudiante) if estudiante is not None else None,
        "limite": limite_diario_de(estudiante) if estudiante is not None else None,
        "productos_bloqueados": (
            productos_bloqueados_de(estudiante).count() if estudiante is not None else 0
        ),
        "movimientos": (
            historial_de(estudiante, limite=ULTIMOS_MOVIMIENTOS)
            if estudiante is not None
            else []
        ),
    }


@login_required
@require_http_methods(["GET"])
def panel_del_acudiente(request):
    """La página del acudiente con sus estudiantes a cargo (`TT-29`, `HU-04`).

    `INT-1`, y es como entra `USR-2`. Entrar es de `TT-56`: sin pantalla de
    acceso propia esta vista no tenía forma de alcanzarse, porque el formulario
    del admin exige `is_staff` y el acudiente no lo es (`DEC-12`).

    Quién puede verla lo decide el selector, que es donde vive la regla
    (`DT-15`): aquí solo se renderiza lo que devuelve.
    """
    estudiantes = estudiantes_a_cargo(usuario=request.user)

    # El primero queda seleccionado: con un solo hijo, el selector sobra y la
    # pantalla ya muestra lo que el acudiente venía a ver.
    seleccionado = estudiantes.first()

    return render(
        request,
        "personas/mis-estudiantes.html",
        {"estudiantes": estudiantes, **_contexto_del_estudiante(seleccionado)},
    )


@login_required
@require_http_methods(["GET"])
def estudiante_seleccionado(request, estudiante_id):
    """El fragmento del estudiante elegido en el selector (`TT-29`, `HU-04`).

    **Devuelve un fragmento, nunca una página** (`DT-16`): por eso es una ruta
    aparte de `panel_del_acudiente` y no la misma vista decidiendo según la
    cabecera de HTMX.

    Un estudiante que no está a cargo de quien pregunta es un 404, igual que uno
    que no existe: el selector no los distingue a propósito.
    """
    try:
        estudiante = estudiante_a_cargo(
            usuario=request.user, estudiante_id=estudiante_id
        )
    except Estudiante.DoesNotExist:
        raise Http404("Ese estudiante no está a tu cargo.") from None

    return render(
        request,
        "partials/estudiante-seleccionado.html",
        _contexto_del_estudiante(estudiante),
    )


@login_required
@require_http_methods(["GET"])
def tarjeta_del_estudiante(request, estudiante_id):
    """Vista imprimible de la tarjeta de un estudiante (`TT-37`, `HU-45`).

    Habilita `ENT-02`: lo que sale de aquí se imprime y se pasa por un lector en
    el Sprint 2. No es una pantalla de consulta con un adorno, es el insumo
    físico de la siguiente demostración.

    **El código de barras se genera en cada petición, a partir del campo del
    estudiante.** Nada se almacena ni se cachea, y eso es lo que sostiene el
    segundo criterio de `HU-45`: se muestra el código **vigente**. Una imagen
    guardada seguiría enseñando un código correcto después de que `HU-46` lo
    reasignara, y esa tarjeta impresa ya no abre ningún saldo (`INVD-4`).

    **Una tarjeta por página, a propósito.** `ALC-OUT-04` excluye la producción
    masiva; `ALC-OUT-05` pide «un número limitado de tarjetas» para la prueba de
    concepto. Se imprimen de una en una, que para un conjunto reducido es
    suficiente y deja la exclusión donde está.
    """
    try:
        estudiante = estudiante_para_la_institucion(
            actor=request.user, estudiante_id=estudiante_id
        )
    except Estudiante.DoesNotExist:
        raise Http404("No hay ningún estudiante con ese identificador.") from None

    return render(
        request,
        "personas/tarjeta.html",
        {
            "estudiante": estudiante,
            "institucion": Institucion.objects.first(),
            "codigo_de_barras": svg_del_codigo(estudiante.codigo_tarjeta),
            "ancho_impreso_mm": ancho_mm(estudiante.codigo_tarjeta),
        },
    )


@login_required
@require_http_methods(["GET"])
def padron_de_estudiantes(request):
    """El padrón de la institución (`DT-27`, `HU-44`).

    **Quién puede verlo lo decide el selector**, que es donde vive la regla
    (`DT-15`): aquí no se comprueba el rol dos veces. El `PermissionDenied` que
    lanza sale como `403`, también para quien escriba la URL a mano (`DT-11`).

    ── DEVUELVE PÁGINA O FRAGMENTO, Y SON DOS COSAS DISTINTAS ──────────────
    `DT-16` prohíbe que **un mismo endpoint** devuelva a veces una página y a
    veces un fragmento. Aquí no pasa eso: son **dos rutas** —`/padron/` y
    `/padron/tabla/`— apuntando a la misma función porque lo que cambia es el
    envoltorio, no lo que se responde. La lista es la misma consulta y el mismo
    contexto; repetirla en dos funciones sería garantizar que un día divergen.

    Lo dice `request.resolver_match.url_name`, no una cabecera de HTMX: una
    cabecera la pone el cliente y se puede falsear; la ruta la resuelve Django.
    ─────────────────────────────────────────────────────────────────────────

    El buscador **no es un formulario que se envíe**: cada tecla pide la tabla y
    reemplaza solo esa zona. Sin eso, secretaría teclea, pulsa Enter, espera a
    que repinte la página entera y pierde el foco del campo en cada intento.
    """
    busqueda = request.GET.get("busqueda", "")
    # La casilla solo llega cuando está marcada, que es como el navegador manda
    # los checkbox. Su ausencia significa «no», no «no lo sé».
    incluir_retirados = request.GET.get("retirados") == "1"

    estudiantes = list(
        padron(
            actor=request.user,
            busqueda=busqueda,
            incluir_retirados=incluir_retirados,
        )
    )

    contexto = {
        "estudiantes": estudiantes,
        "busqueda": busqueda,
        "incluir_retirados": incluir_retirados,
        "sin_activar": cuentas_sin_activar(estudiantes),
        # El total sin filtrar, para poder decir «8 de 20» y que quien busca sepa
        # que hay más. Con la búsqueda vacía las dos cifras coinciden y la frase
        # sigue leyéndose bien.
        "total": padron(
            actor=request.user, incluir_retirados=incluir_retirados
        ).count(),
    }

    if request.resolver_match.url_name == "padron-tabla":
        return render(request, "personas/partials/padron-tabla.html", contexto)

    return render(request, "personas/padron.html", contexto)
