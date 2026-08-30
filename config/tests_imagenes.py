"""Pruebas de la canalización de subida (`TT-55`, `DT-20`).

Cada afirmación que hace `config/imagenes.py` sobre lo que neutraliza tiene aquí
su prueba. Sin ellas, «retira el EXIF» y «neutraliza los políglotos» son
comentarios en un fichero, no propiedades del sistema.
"""

from io import BytesIO

from django.test import SimpleTestCase
from PIL import Image

from config.imagenes import ImagenInvalida, procesar_imagen, tiene_exif


def _imagen(formato="JPEG", tamano=(64, 48), color=(200, 30, 30), **guardar):
    buffer = BytesIO()
    Image.new("RGB", tamano, color).save(buffer, format=formato, **guardar)
    return buffer.getvalue()


class ProcesarImagenTest(SimpleTestCase):
    def test_acepta_una_imagen_normal_y_devuelve_webp(self):
        contenido, nombre = procesar_imagen(BytesIO(_imagen()))

        self.assertTrue(nombre.endswith(".webp"))
        with Image.open(BytesIO(contenido.read())) as salida:
            self.assertEqual(salida.format, "WEBP")

    def test_el_nombre_lo_genera_el_servidor(self):
        """El nombre que manda el cliente es entrada del usuario: no se usa."""
        archivo = BytesIO(_imagen())
        archivo.name = "../../etc/passwd.jpg"

        _, nombre = procesar_imagen(archivo)

        self.assertNotIn("passwd", nombre)
        self.assertNotIn("/", nombre)
        self.assertTrue(nombre.endswith(".webp"))

    def test_retira_el_exif(self):
        """DT-20. Una foto de móvil lleva dentro dónde se tomó."""
        # Un JPEG con EXIF real, incluida una etiqueta de GPS.
        exif = Image.Exif()
        exif[0x010F] = "SmartFood Test"      # Make
        exif[0x8825] = {1: "N", 2: (4.0, 42.0, 0.0)}  # GPSInfo
        buffer = BytesIO()
        Image.new("RGB", (64, 48), (10, 20, 30)).save(buffer, format="JPEG", exif=exif)
        con_exif = buffer.getvalue()

        self.assertTrue(tiene_exif(con_exif), "la imagen de partida debía traer EXIF")

        contenido, _ = procesar_imagen(BytesIO(con_exif))
        self.assertFalse(tiene_exif(contenido.read()), "el EXIF sobrevivió al procesado")

    def test_neutraliza_un_fichero_poliglota(self):
        """Un GIF válido con un script pegado detrás sale sin el script."""
        gif = _imagen(formato="GIF")
        poliglota = gif + b"<?php system($_GET['c']); ?>"

        contenido, _ = procesar_imagen(BytesIO(poliglota))
        salida = contenido.read()

        self.assertNotIn(b"<?php", salida)
        self.assertNotIn(b"system(", salida)

    def test_rechaza_lo_que_no_es_una_imagen(self):
        with self.assertRaises(ImagenInvalida):
            procesar_imagen(BytesIO(b"<?php system($_GET['c']); ?>"))

    def test_rechaza_un_ejecutable_con_extension_de_imagen(self):
        """La extensión la elige quien sube el fichero: no es evidencia."""
        archivo = BytesIO(b"MZ\x90\x00\x03" + b"\x00" * 200)
        archivo.name = "foto.jpg"

        with self.assertRaises(ImagenInvalida):
            procesar_imagen(archivo)

    def test_rechaza_el_archivo_vacio(self):
        with self.assertRaises(ImagenInvalida):
            procesar_imagen(BytesIO(b""))

    def test_rechaza_una_imagen_demasiado_pesada(self):
        with self.settings(IMAGEN_TAMANO_MAXIMO_BYTES=100):
            with self.assertRaises(ImagenInvalida):
                procesar_imagen(BytesIO(_imagen(tamano=(400, 400))))

    def test_reduce_la_imagen_al_lado_maximo(self):
        contenido, _ = procesar_imagen(BytesIO(_imagen(tamano=(3000, 1500))), lado_maximo=800)

        with Image.open(BytesIO(contenido.read())) as salida:
            self.assertLessEqual(max(salida.size), 800)
            # Conserva la proporción: 2:1 sigue siendo 2:1.
            self.assertEqual(round(salida.width / salida.height), 2)

    def test_conserva_la_transparencia(self):
        buffer = BytesIO()
        Image.new("RGBA", (32, 32), (0, 0, 0, 0)).save(buffer, format="PNG")

        contenido, _ = procesar_imagen(BytesIO(buffer.getvalue()))
        with Image.open(BytesIO(contenido.read())) as salida:
            self.assertEqual(salida.mode, "RGBA")
