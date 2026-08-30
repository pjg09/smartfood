"""Rutas del proyecto.

**No hay rutas de registro y no las habrá** (`INV-6`, `INVD-1`, `DT-10`): las
cuentas se crean por seed o por invitación. Si alguna vez aparece aquí una ruta
de alta pública, es un error, no una funcionalidad.
"""

from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

from config.salud import salud

# `INT-3` no lleva plantillas propias: lo cubre el admin generado (`DT-2`). Lo
# único que necesita es hablar en español y no llamarse «Django» (TT-05).
admin.site.site_header = "SmartFood · Administración"
admin.site.site_title = "SmartFood"
admin.site.index_title = "Gestión de la cafetería"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("salud/", salud, name="salud"),
    # Provisional: la sustituye la pantalla de acceso de `TT-11` (`PR-08`).
    path("", TemplateView.as_view(template_name="inicio.html"), name="inicio"),
]
