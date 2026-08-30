"""Rutas del proyecto.

**No hay rutas de registro y no las habrá** (`INV-6`, `INVD-1`, `DT-10`): las
cuentas se crean por seed o por invitación. Si alguna vez aparece aquí una ruta
de alta pública, es un error, no una funcionalidad.
"""

from django.contrib import admin
from django.urls import path

from config.salud import salud

urlpatterns = [
    path("admin/", admin.site.urls),
    path("salud/", salud, name="salud"),
]
