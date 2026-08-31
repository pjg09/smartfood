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

from cuentas.models import Rol
from personas.carga import ArchivoIlegible
from personas.models import Estudiante
from personas.selectors import estudiante_a_cargo, estudiantes_a_cargo
from personas.services import cargar_estudiantes_y_acudientes
from personas.validacion import ArchivoInvalido


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
        {"estudiantes": estudiantes, "seleccionado": seleccionado},
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
        {"seleccionado": estudiante},
    )
