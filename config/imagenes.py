"""Canalización de subida de imágenes (`TT-55`, `DT-20`).

Vive en `config/` porque la usan `personas` (fotografía del estudiante, `HU-57`)
y `catalogo` (imagen del producto, `HU-59`) por igual, y ninguna la posee.

**Ningún fichero subido por un usuario se guarda tal cual.** Se decodifica y se
vuelve a codificar desde cero. Eso hace tres cosas a la vez:

1. **Valida por contenido, no por nombre.** La extensión y el `Content-Type` los
   elige quien sube el fichero: no son evidencia de nada. Aquí lo único que
   cuenta es si un decodificador de imágenes consigue abrirlo.
2. **Neutraliza los ficheros políglotos.** Un fichero puede ser a la vez un GIF
   válido y un script válido. Al reconstruir la imagen a partir de sus píxeles,
   lo que no era píxel desaparece.
3. **Retira el EXIF.** La fotografía de un menor tomada con un teléfono lleva
   dentro, por defecto, la ubicación GPS donde se tomó. Guardarla sería añadir
   un dato personal que nadie pidió (`ALC-OUT-08`, Ley 1581 de 2012).
"""

import uuid
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

# Formatos que aceptamos a la ENTRADA. La salida es siempre WEBP.
FORMATOS_ACEPTADOS = {"JPEG", "PNG", "WEBP", "GIF", "BMP"}

FORMATO_SALIDA = "WEBP"
EXTENSION_SALIDA = "webp"
TIPO_SALIDA = "image/webp"

# Una imagen de pocos kilobytes puede declarar unas dimensiones enormes y agotar
# la memoria al descomprimirla. Pillow lo llama «decompression bomb».
Image.MAX_IMAGE_PIXELS = 50_000_000


class ImagenInvalida(ValidationError):
    """El fichero no es una imagen que podamos aceptar."""


def procesar_imagen(archivo, *, lado_maximo=None, calidad=None):
    """Devuelve `(ContentFile, nombre)` con la imagen ya saneada.

    Lanza `ImagenInvalida` si el fichero no es una imagen procesable. El
    llamante —un servicio (`DT-15`)— decide qué hacer con el error; esta función
    no sabe de HTTP.
    """
    lado_maximo = lado_maximo or settings.IMAGEN_LADO_MAXIMO
    calidad = calidad or settings.IMAGEN_CALIDAD

    datos = archivo.read() if hasattr(archivo, "read") else bytes(archivo)

    limite = settings.IMAGEN_TAMANO_MAXIMO_BYTES
    if len(datos) > limite:
        raise ImagenInvalida(
            f"La imagen pesa más de {limite // (1024 * 1024)} MB."
        )
    if not datos:
        raise ImagenInvalida("El archivo está vacío.")

    # Primera pasada: comprobar que la estructura del fichero es coherente.
    # `verify()` deja la imagen inutilizable, así que después hay que reabrirla.
    try:
        with Image.open(BytesIO(datos)) as sonda:
            formato = sonda.format
            sonda.verify()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ImagenInvalida("El archivo no es una imagen válida.") from error

    if formato not in FORMATOS_ACEPTADOS:
        aceptados = ", ".join(sorted(FORMATOS_ACEPTADOS))
        raise ImagenInvalida(
            f"Formato «{formato}» no aceptado. Se admiten: {aceptados}."
        )

    try:
        with Image.open(BytesIO(datos)) as imagen:
            # Aplicar la orientación del EXIF ANTES de retirarlo. Las fotos
            # tomadas con un teléfono suelen venir «de pie» solo gracias a esa
            # etiqueta: si se borra sin aplicarla, salen giradas.
            imagen = ImageOps.exif_transpose(imagen)

            # WEBP no admite paleta ni escala de grises con transparencia; se
            # normaliza a RGB, o RGBA si de verdad hay canal alfa que conservar.
            if imagen.mode in ("RGBA", "LA", "PA"):
                imagen = imagen.convert("RGBA")
            else:
                imagen = imagen.convert("RGB")

            imagen.thumbnail((lado_maximo, lado_maximo), Image.LANCZOS)

            salida = BytesIO()
            # `save` sobre una imagen reconstruida no arrastra los metadatos del
            # original: el EXIF se queda fuera porque nunca se copia.
            imagen.save(salida, format=FORMATO_SALIDA, quality=calidad, method=6)
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise ImagenInvalida("No se pudo procesar la imagen.") from error

    salida.seek(0)

    # El nombre lo genera el servidor. El que venía del cliente no se usa: es
    # entrada del usuario y no aporta nada (`INV-7` razona igual sobre los
    # códigos no adivinables).
    nombre = f"{uuid.uuid4().hex}.{EXTENSION_SALIDA}"
    return ContentFile(salida.read(), name=nombre), nombre


def tiene_exif(datos):
    """Utilidad para las pruebas: ¿estos bytes llevan metadatos EXIF?"""
    with Image.open(BytesIO(datos)) as imagen:
        exif = imagen.getexif()
        return bool(exif)
