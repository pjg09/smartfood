"""Generación de imágenes ficticias (`TT-08`, `DT-14`).

**Sostiene `INVD-6`: ninguna fotografía del prototipo corresponde a una persona
real.** La forma más segura de garantizarlo no es elegir bien de dónde se
descargan las imágenes: es **no descargar ninguna**. Aquí se dibujan desde cero
con figuras geométricas, así que no hay ningún camino por el que la cara de una
persona entre en el sistema.

Tampoco se usan servicios de «caras generadas»: son personas sintéticas pero
plausibles, y una foto que **parece** una persona real acaba tratándose como
tal. Estos avatares no se pueden confundir con una fotografía.

Vive en `config/` porque lo usan `personas` (avatar del estudiante) y `catalogo`
(imagen del producto) por igual, y ninguna de las dos lo posee.

**Es determinista.** El mismo texto produce siempre el mismo dibujo, así que
sembrar dos veces no cambia las caras y una captura de pantalla de ayer sigue
pareciéndose a lo que hay hoy.
"""

import hashlib
from io import BytesIO

from PIL import Image, ImageDraw

LADO = 480

# Paleta sobria y con contraste suficiente sobre fondo claro. No es decoración:
# un avatar que no se distingue del de al lado no sirve para lo que existe, que
# es reconocer a alguien de un vistazo (`HU-58`).
COLORES = [
    (198, 40, 40), (216, 67, 21), (245, 124, 0), (249, 168, 37),
    (85, 139, 47), (0, 121, 107), (2, 119, 189), (48, 63, 159),
    (81, 45, 168), (123, 31, 162), (173, 20, 87), (66, 66, 66),
]


def _semilla(texto):
    """Bytes estables a partir de un texto. No es criptografía: es reparto."""
    return hashlib.sha256(texto.encode("utf-8")).digest()


def avatar(texto, lado=LADO):
    """Un identicón simétrico, en PNG. Determinista para el mismo texto.

    Cinco columnas espejadas sobre una rejilla, que es la forma clásica: se
    reconoce de un vistazo y **no se parece a una cara**, que es justo lo que
    `INVD-6` necesita.
    """
    datos = _semilla(texto)
    color = COLORES[datos[0] % len(COLORES)]
    fondo = (245, 245, 245)

    celdas = 5
    # El tamaño de celda se redondea hacia abajo, así que la rejilla no ocupa
    # todo el ancho disponible. El margen se recalcula con el sobrante para que
    # quede **centrada**: si no, el dibujo sale desplazado y deja de ser
    # simétrico píxel a píxel.
    tamano = (lado - 2 * (lado // 10)) // celdas
    margen = (lado - celdas * tamano) // 2

    imagen = Image.new("RGB", (lado, lado), fondo)
    lienzo = ImageDraw.Draw(imagen)

    for columna in range(3):
        for fila in range(celdas):
            if not datos[1 + columna * celdas + fila] % 2:
                continue
            for x in {columna, celdas - 1 - columna}:
                izquierda = margen + x * tamano
                arriba = margen + fila * tamano
                lienzo.rectangle(
                    [izquierda, arriba, izquierda + tamano, arriba + tamano],
                    fill=color,
                )

    salida = BytesIO()
    imagen.save(salida, format="PNG")
    salida.seek(0)
    return salida


def bodegon(texto, lado=LADO):
    """Una imagen ficticia de producto: bandas de color sobre un fondo.

    No pretende parecerse a comida y no debe: `ALC-OUT-07` pide datos ficticios,
    y una fotografía de empanada descargada de internet tiene dueño. Sirve para
    lo que la imagen sirve en `INT-2` —distinguir un producto de otro de un
    vistazo (`HU-59`)— sin traer nada de fuera.
    """
    datos = _semilla(texto)
    principal = COLORES[datos[0] % len(COLORES)]
    secundario = COLORES[datos[1] % len(COLORES)]

    imagen = Image.new("RGB", (lado, lado), (250, 250, 250))
    lienzo = ImageDraw.Draw(imagen)

    lienzo.ellipse(
        [lado // 8, lado // 8, lado - lado // 8, lado - lado // 8], fill=principal
    )
    for banda in range(4):
        arriba = lado // 3 + banda * (lado // 12)
        if datos[2 + banda] % 2:
            lienzo.rectangle([0, arriba, lado, arriba + lado // 24], fill=secundario)

    salida = BytesIO()
    imagen.save(salida, format="PNG")
    salida.seek(0)
    return salida
