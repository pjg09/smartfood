"""Vistas de institución educativa, estudiantes y acudientes.

Solo HTTP: parsear la petición, delegar en un servicio o un selector, y
renderizar. **Cero lógica de negocio** (`DT-15`).

Una vista HTMX devuelve **un fragmento, nunca una página** (`DT-16`).
"""

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from cuentas.models import Rol
from personas.carga import ArchivoIlegible
from personas.services import cargar_estudiantes_y_acudientes


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

    contexto = {"form": ArchivoDeCargaForm(), "resultado": None, "error": None}

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
                # `HU-02` construye el reporte de errores por fila (`TT-26`).
                # Esto solo cubre el archivo que ni siquiera se puede leer.
                contexto["error"] = str(error)

    return render(request, "personas/carga-de-estudiantes.html", contexto)
