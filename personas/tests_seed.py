"""`TT-08`. El generador de datos ficticios, donde queda terminado.

Es la única tarea del sprint que crece por partes: su esqueleto es de `PR-08` y
aquí siembra ya las tres cosas que el prototipo necesita —cuentas, familias y
catálogo—, que es el criterio con el que el plan la da por terminada.

Lo que estas pruebas fijan es lo que no se puede comprobar mirando la salida del
comando: que **todo lo que produce es ficticio** (`ALC-OUT-07`, `INVD-6`,
`DoD-6`) y que **se puede ejecutar dos veces**, que es lo que ocurre en cada
despliegue.
"""

from io import BytesIO

from django.conf import settings
from django.core.files.storage import storages
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from catalogo.models import Alergeno, Categoria, Producto
from cuentas.models import Rol, Usuario
from personas.models import Acudiente, Estudiante

EN_MEMORIA = {
    **settings.STORAGES,
    "privado": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "publico": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
}


@override_settings(STORAGES=EN_MEMORIA)
class BaseSembrada(TestCase):
    ESTUDIANTES = 8

    def sembrar(self, **extra):
        with self.captureOnCommitCallbacks(execute=True):
            call_command(
                "sembrar",
                contrasena_de_desarrollo="clave-de-prueba-2026",
                estudiantes=self.ESTUDIANTES,
                verbosity=0,
                **extra,
            )

    def setUp(self):
        self.sembrar()


class SiembraLasTresPartesTest(BaseSembrada):
    """Cuentas, familias y catálogo: el criterio con el que `TT-08` termina."""

    def test_la_institucion_y_el_personal_de_la_cafeteria(self):
        self.assertEqual(Usuario.objects.filter(rol=Rol.INSTITUCION).count(), 1)
        self.assertEqual(Usuario.objects.filter(rol=Rol.CAJERO).count(), 1)
        self.assertEqual(Usuario.objects.filter(rol=Rol.ADMINISTRADOR).count(), 1)

    def test_acudientes_con_sus_estudiantes(self):
        self.assertEqual(Estudiante.objects.count(), self.ESTUDIANTES)
        self.assertGreater(Acudiente.objects.count(), 0)

    def test_al_menos_un_acudiente_tiene_dos_estudiantes(self):
        """Sin este caso, la pantalla del acudiente nunca enseña su selector.

        Es lo que `HU-04` describe, y lo que hay que poder demostrar.
        """
        con_dos = [a for a in Acudiente.objects.all() if a.estudiantes.count() >= 2]
        self.assertTrue(con_dos, "ningún acudiente con más de un estudiante (HU-04)")

    def test_el_catalogo_entero(self):
        self.assertGreater(Categoria.objects.count(), 0)
        self.assertGreater(Alergeno.objects.count(), 0)
        self.assertGreater(Producto.objects.count(), 0)

    def test_los_productos_declaran_alergenos_por_la_relacion(self):
        """`INV-5`: la declaración es una fila, no una lista copiada."""
        con_alergenos = [p for p in Producto.objects.all() if p.alergenos.exists()]
        self.assertTrue(con_alergenos)

    def test_los_productos_traen_informacion_nutricional(self):
        """`TT-44`. Sin ella, los reportes del Sprint 4 no tienen qué agregar."""
        declaran = [
            p for p in Producto.objects.all() if p.declara_informacion_nutricional
        ]
        self.assertGreaterEqual(len(declaran), Producto.objects.count() - 1)

    def test_cada_estudiante_sale_con_su_codigo_de_tarjeta(self):
        codigos = list(Estudiante.objects.values_list("codigo_tarjeta", flat=True))
        self.assertEqual(len(set(codigos)), len(codigos))
        self.assertTrue(all(codigos))


class TodoLoQueSiembraEsFicticioTest(BaseSembrada):
    """`ALC-OUT-07` y `DoD-6`. No es una preferencia: es la Ley 1581 de 2012."""

    def test_ningun_correo_sale_de_example_com(self):
        """La RFC 2606 lo reserva: ningún correo dirigido ahí llega a nadie."""
        ajenos = Usuario.objects.exclude(email__endswith="@example.com")
        self.assertEqual(list(ajenos), [])

    def test_ningun_documento_se_parece_a_uno_real(self):
        """Secuencias inventadas, no cédulas."""
        for estudiante in Estudiante.objects.all():
            self.assertTrue(estudiante.documento.startswith("10"))
            self.assertEqual(len(estudiante.documento), 10)

    def test_cada_estudiante_tiene_avatar_y_es_generado(self):
        """`INVD-6`. Y pasó por la canalización, como cualquier otra imagen."""
        for estudiante in Estudiante.objects.all():
            with self.subTest(estudiante=estudiante.nombre):
                self.assertTrue(estudiante.tiene_foto)
                with storages["privado"].open(estudiante.foto_clave) as guardada:
                    with Image.open(BytesIO(guardada.read())) as imagen:
                        self.assertEqual(imagen.format, "WEBP")

    def test_las_fotografias_van_al_privado_y_no_al_publico(self):
        """La de un menor no se sirve por una URL adivinable (`DT-18`)."""
        for estudiante in Estudiante.objects.all():
            with self.subTest(estudiante=estudiante.nombre):
                self.assertTrue(storages["privado"].exists(estudiante.foto_clave))
                self.assertFalse(storages["publico"].exists(estudiante.foto_clave))

    def test_cada_producto_tiene_imagen_y_va_al_publico(self):
        for producto in Producto.objects.all():
            with self.subTest(producto=producto.nombre):
                self.assertTrue(producto.tiene_imagen)
                self.assertTrue(storages["publico"].exists(producto.imagen_clave))


class SePuedeEjecutarDosVecesTest(BaseSembrada):
    """Es lo que ocurre en cada despliegue y al levantar el entorno."""

    def _censo(self):
        return (
            Usuario.objects.count(),
            Acudiente.objects.count(),
            Estudiante.objects.count(),
            Producto.objects.count(),
            Categoria.objects.count(),
            Alergeno.objects.count(),
        )

    def test_no_duplica_nada(self):
        antes = self._censo()
        self.sembrar()
        self.assertEqual(self._censo(), antes)

    def test_no_vuelve_a_subir_las_imagenes(self):
        """Volver a subirlas dejaría un objeto huérfano por despliegue."""
        fotos = dict(Estudiante.objects.values_list("documento", "foto_clave"))
        imagenes = dict(Producto.objects.values_list("nombre", "imagen_clave"))

        self.sembrar()

        self.assertEqual(
            dict(Estudiante.objects.values_list("documento", "foto_clave")), fotos
        )
        self.assertEqual(
            dict(Producto.objects.values_list("nombre", "imagen_clave")), imagenes
        )

    def test_los_codigos_de_tarjeta_no_cambian(self):
        """Sembrar de nuevo no invalida las tarjetas ya impresas (`INVD-4`)."""
        antes = dict(Estudiante.objects.values_list("documento", "codigo_tarjeta"))
        self.sembrar()
        self.assertEqual(
            dict(Estudiante.objects.values_list("documento", "codigo_tarjeta")), antes
        )


class SembrarSinImagenesTest(TestCase):
    """La opción rápida, para cuando solo hacen falta los datos."""

    @override_settings(STORAGES=EN_MEMORIA)
    def test_no_genera_ninguna(self):
        with self.captureOnCommitCallbacks(execute=True):
            call_command(
                "sembrar",
                contrasena_de_desarrollo="clave-de-prueba-2026",
                estudiantes=4,
                sin_imagenes=True,
                verbosity=0,
            )

        self.assertEqual(Estudiante.objects.count(), 4)
        self.assertEqual(Estudiante.objects.exclude(foto_clave="").count(), 0)
        self.assertEqual(Producto.objects.exclude(imagen_clave="").count(), 0)


class SembrarSoloLaInstitucionTest(TestCase):
    """Sin `--estudiantes` el comando hace lo que hacía antes de `TT-08`."""

    def test_no_siembra_ni_familias_ni_catalogo(self):
        with self.captureOnCommitCallbacks(execute=True):
            call_command(
                "sembrar", contrasena_de_desarrollo="clave", verbosity=0
            )

        self.assertEqual(Usuario.objects.count(), 1)
        self.assertEqual(Estudiante.objects.count(), 0)
        self.assertEqual(Producto.objects.count(), 0)
