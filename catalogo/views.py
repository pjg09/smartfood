"""Vistas de productos, categorías y alérgenos.

Solo HTTP: parsear la petición, delegar en un servicio o un selector, y
renderizar. **Cero lógica de negocio** (`DT-15`).

Una vista HTMX devuelve **un fragmento, nunca una página** (`DT-16`). Si un
endpoint devuelve a veces una cosa y a veces la otra, se parte en dos.
"""

import re

from django.conf import settings
from django.core.files.storage import storages
from django.http import FileResponse, Http404
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_safe

from config.imagenes import TIPO_SALIDA

# La forma exacta de las claves que produce la canalización: 32 dígitos
# hexadecimales y la extensión de salida (`config/imagenes.py`).
#
# **No es una comprobación de estilo: es lo que impide salir del prefijo.** El
# almacenamiento antepone `publico/` a lo que se le pida, así que una clave como
# `../privado/loquesea.webp` alcanzaría la fotografía de un estudiante. Se acepta
# lo que la canalización genera y nada más.
CLAVE_VALIDA = re.compile(r"^[0-9a-f]{32}\.webp$")


@require_safe
@cache_control(public=True, max_age=settings.CACHE_IMAGEN_PRODUCTO, immutable=True)
def imagen_del_producto(request, clave):
    """Sirve una imagen del catálogo (`TT-53`, `HU-59`, `DT-21`).

    **La sirve la aplicación y no una URL firmada.** La imagen de un producto no
    es sensible, y firmar cincuenta URL para pintar la lista del punto de venta
    es coste sin contrapartida (`DT-18`). Además una firma caduca, y el punto de
    venta tendría que volver a pedir el catálogo entero cada pocos minutos solo
    para renovar enlaces.

    **Sin sesión, a propósito.** «Público» aquí significa *no sensible*
    (`DT-21`): es la fotografía de una empanada. Exigir sesión no protegería
    nada y rompería la caché del navegador, que es justo lo que `INT-2` necesita
    para no descargar el catálogo en cada pintado. Lo que sí es cierto es que la
    clave no se puede adivinar: la genera el servidor y son 128 bits.

    **Inmutable.** La ruta lleva la clave, no el identificador del producto: al
    reemplazar la imagen cambia la clave y con ella la URL, así que no hay nada
    que invalidar y el navegador puede quedársela un mes.
    """
    if not CLAVE_VALIDA.match(clave):
        raise Http404("Esa no es una clave de imagen.")

    almacenamiento = storages["publico"]
    if not almacenamiento.exists(clave):
        raise Http404("No hay ninguna imagen con esa clave.")

    return FileResponse(almacenamiento.open(clave), content_type=TIPO_SALIDA)
