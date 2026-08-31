"""Rutas del proyecto.

**No hay rutas de registro y no las habrá** (`INV-6`, `INVD-1`, `DT-10`): las
cuentas se crean por seed o por invitación. Si alguna vez aparece aquí una ruta
de alta pública, es un error, no una funcionalidad.
"""

from django.contrib import admin
from django.contrib.auth import views as vistas_de_auth
from django.urls import path, reverse_lazy
from django.views.generic import TemplateView

from config.salud import salud
from personas.views import (
    carga_de_estudiantes,
    estudiante_seleccionado,
    panel_del_acudiente,
)

# `INT-3` no lleva plantillas propias: lo cubre el admin generado (`DT-2`). Lo
# único que necesita es hablar en español y no llamarse «Django» (TT-05).
admin.site.site_header = "SmartFood · Administración"
admin.site.site_title = "SmartFood"
admin.site.index_title = "Gestión de la cafetería"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("salud/", salud, name="salud"),
    # Acceso al sistema (`TT-56`, `DEC-12`). **No es un camino de alta**: aquí
    # solo entra quien ya tiene cuenta y ya definió su contraseña con la
    # invitación. `INV-6` e `INVD-1` no se tocan.
    #
    # Existe porque `/admin/login/` exige `is_staff` y el acudiente no lo es
    # (`INT-1` no es el admin): sin esta ruta, `USR-2` no tiene por dónde entrar.
    path(
        "acceso/",
        vistas_de_auth.LoginView.as_view(
            template_name="cuentas/acceso.html",
            redirect_authenticated_user=True,
        ),
        name="acceso",
    ),
    path("salir/", vistas_de_auth.LogoutView.as_view(), name="salir"),
    # Definición de contraseña a partir de la invitación (`TT-11`). La misma
    # pantalla sirve a los cuatro roles: el mecanismo de acceso es único
    # (`DEC-3`), y la reutilizan `HU-39`, `HU-41` y `HU-03`.
    #
    # Se apoya en las vistas de Django en lugar de escribir autenticación
    # propia, que `CLAUDE.md` descarta explícitamente. El token que usan ya se
    # invalida al cambiar la contraseña y caduca solo; `TT-18` lo revisa.
    path(
        "invitacion/<uidb64>/<token>/",
        vistas_de_auth.PasswordResetConfirmView.as_view(
            template_name="cuentas/definir-contrasena.html",
            success_url=reverse_lazy("contrasena-definida"),
        ),
        name="definir-contrasena",
    ),
    path(
        "invitacion/lista/",
        TemplateView.as_view(template_name="cuentas/contrasena-definida.html"),
        name="contrasena-definida",
    ),
    # Carga masiva de estudiantes y acudientes (`TT-24`, `HU-01`).
    path("carga/", carga_de_estudiantes, name="carga-de-estudiantes"),
    # Interfaz del acudiente (`TT-29`, `HU-04`, `INT-1`). La primera devuelve la
    # página; la segunda, el fragmento HTMX del estudiante elegido. Son dos
    # rutas y no una con dos comportamientos (`DT-16`).
    path("mis-estudiantes/", panel_del_acudiente, name="mis-estudiantes"),
    path(
        "mis-estudiantes/<uuid:estudiante_id>/",
        estudiante_seleccionado,
        name="estudiante-seleccionado",
    ),
    path("", TemplateView.as_view(template_name="inicio.html"), name="inicio"),
]
