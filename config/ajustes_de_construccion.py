"""Ajustes mínimos para descargar Tailwind al construir la imagen (`DT-37`).

El `Dockerfile` no copia el código —en `compose.yaml` llega montado—, así que
`django.setup()` con los ajustes de verdad fallaría importando las apps. Aquí
se toma la configuración de Tailwind de `config/settings.py`, que es donde vive
su versión, y se deja solo la app que la descarga. Así la versión sigue escrita
en un único sitio y la imagen no cambia cada vez que cambia el código.

No lo uses para nada más.
"""

from config.settings import *  # noqa: F403

INSTALLED_APPS = ["django_tailwind_cli"]

# Las comprobaciones del sistema, que corren antes de cualquier comando, buscan
# el `urls.py` de verdad, que importa las apps. Este módulo hace de URLconf vacío.
ROOT_URLCONF = __name__
urlpatterns = []
