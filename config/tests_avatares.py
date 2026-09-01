"""`TT-08`. Las imágenes ficticias se dibujan, no se descargan (`INVD-6`).

`INVD-6` dice que **ninguna fotografía del prototipo corresponde a una persona
real**. Es una regla de operación, y la forma de garantizarla no es elegir bien
de dónde se descargan las imágenes: es que no haya ningún camino por el que una
imagen de fuera entre en el sistema.
"""

import inspect
from io import BytesIO

from django.test import SimpleTestCase
from PIL import Image

from config import avatares
from config.avatares import avatar, bodegon


class SeDibujanYNoSeDescarganTest(SimpleTestCase):
    def test_el_modulo_no_sabe_hablar_por_la_red(self):
        """La prueba estructural de `INVD-6`.

        Si mañana alguien «mejora» los avatares trayéndolos de un servicio de
        caras generadas, esto falla. Son personas sintéticas pero plausibles, y
        una foto que **parece** una persona real acaba tratándose como tal.
        """
        fuente = inspect.getsource(avatares)

        for red in ["requests", "urllib", "httpx", "socket", "http.client", "urlopen"]:
            with self.subTest(red=red):
                self.assertNotIn(red, fuente)

    def test_produce_una_imagen_de_verdad(self):
        with Image.open(BytesIO(avatar("1001234501").read())) as imagen:
            self.assertEqual(imagen.format, "PNG")
            self.assertEqual(imagen.size, (480, 480))

    def test_es_determinista(self):
        """Sembrar dos veces no cambia las caras."""
        self.assertEqual(
            avatar("1001234501").getvalue(), avatar("1001234501").getvalue()
        )

    def test_dos_personas_distintas_no_comparten_avatar(self):
        distintos = {avatar(f"10012345{n:02d}").getvalue() for n in range(30)}
        self.assertEqual(len(distintos), 30)

    def test_el_avatar_es_simetrico_y_no_una_cara(self):
        """Un identicón: se reconoce de un vistazo y no se confunde con una foto."""
        with Image.open(BytesIO(avatar("1001234501").read())) as imagen:
            pixeles = imagen.load()
            ancho, alto = imagen.size
            for y in range(0, alto, 40):
                for x in range(0, ancho // 2, 40):
                    self.assertEqual(pixeles[x, y], pixeles[ancho - 1 - x, y])

    def test_el_bodegon_tambien_se_dibuja(self):
        with Image.open(BytesIO(bodegon("Empanada de carne").read())) as imagen:
            self.assertEqual(imagen.format, "PNG")

    def test_dos_productos_distintos_no_comparten_imagen(self):
        self.assertNotEqual(
            bodegon("Empanada de carne").getvalue(), bodegon("Jugo de mora").getvalue()
        )
