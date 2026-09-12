"""`TT-77`. La fotografía del estudiante en la vista de cobro (`HU-58`, `DEC-8`).

Los tres criterios de `HU-58`, y cuál se prueba dónde:

1. **La fotografía aparece en la vista de cobro**, junto al saldo, el consumo del
   día y las restricciones. Se prueba aquí, por las dos vías de identificación.
2. **Si el estudiante no tiene fotografía, la venta procede igual.** Que no sea
   obligatoria no se prueba mirando el campo: se prueba comprobando que sin ella
   la pantalla sigue trayendo todo lo demás. Y se prueba además lo que el segundo
   criterio implica y no dice — que el hueco **se vea**.
3. **Es un control preventivo.** Eso no es código: es la razón por la que el dato
   está en esta pantalla y no en un informe. Lo que sí se puede vigilar es que la
   URL de la fotografía de un menor **no sea adivinable** (`ALC-OUT-08`), y de eso
   se ocupa `personas/tests_fotografia.py` sobre el almacenamiento.

La distinción que conviene no perder: **un avatar genérico no sirve como hueco.**
Si al estudiante sin fotografía se le dibujara la silueta de siempre, el cajero
leería que la comprobación se hizo y salió bien. El hueco dice que no se puede
comprobar, que es lo que de verdad pasa.

Las pruebas usan almacenamiento en memoria, no MinIO: lo que se comprueba es la
pantalla, y el bucket ya tiene sus pruebas en `personas/`.
"""

from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from personas.services import guardar_fotografia

# El alias `privado` en memoria. Cada prueba parte de cero.
EN_MEMORIA = {
    **settings.STORAGES,
    "privado": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
}


def avatar():
    """Un avatar generado. **Nunca una persona real** (`INVD-6`, `ALC-OUT-07`)."""
    buffer = BytesIO()
    Image.new("RGB", (320, 320), (40, 120, 200)).save(buffer, format="JPEG")
    return SimpleUploadedFile("avatar.jpg", buffer.getvalue(), content_type="image/jpeg")


def estudiante(documento="1001234501"):
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente{documento}@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
    )
    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"43{documento}"
    )
    return Estudiante.objects.create(
        nombre="Ana Sofía Restrepo Ruiz",
        documento=documento,
        acudiente=acudiente,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )


@override_settings(STORAGES=EN_MEMORIA)
class LaFotografiaApareceAlCobrarTest(TestCase):
    """Primer criterio de `HU-58`."""

    def setUp(self):
        self.estudiante = estudiante()
        self.institucion = Usuario.objects.crear_usuario(
            email="institucion@example.com", rol=Rol.INSTITUCION, nombre="Colegio"
        )
        self.client.force_login(
            Usuario.objects.crear_usuario(
                email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
            )
        )
        self.url = reverse("identificacion-en-el-punto-de-venta")

    def _con_fotografia(self):
        guardar_fotografia(
            actor=self.institucion, estudiante=self.estudiante, archivo=avatar()
        )
        self.estudiante.refresh_from_db()

    def _por_tarjeta(self):
        return self.client.get(
            self.url, {"codigo": self.estudiante.codigo_tarjeta}
        ).content.decode()

    def test_el_escaneo_trae_la_fotografia(self):
        self._con_fotografia()

        cuerpo = self._por_tarjeta()

        self.assertIn(self.estudiante.url_de_la_foto, cuerpo)

    def test_esta_junto_a_las_cifras_de_cobro_y_no_en_otra_pantalla(self):
        """Primer criterio, literal: «aparece en la vista de cobro (`HU-17`),
        **junto** al saldo, el consumo del día y las restricciones».

        El control es preventivo y sirve en el instante del cobro: una fotografía
        que hubiera que ir a buscar a otra pantalla no lo sería.
        """
        self._con_fotografia()

        cuerpo = self._por_tarjeta()

        self.assertIn("Saldo", cuerpo)
        self.assertIn("Consumo de hoy", cuerpo)
        self.assertIn("Restricciones", cuerpo)
        self.assertIn(self.estudiante.url_de_la_foto, cuerpo)

    def test_por_documento_sale_la_misma_fotografia(self):
        """`HU-16`, primer criterio: **el mismo resultado** por las dos vías.

        Quien olvida la tarjeta no puede acabar en una venta sin el control que
        la otra vía sí aplica.
        """
        self._con_fotografia()

        por_documento = self.client.get(
            self.url, {"documento": self.estudiante.documento}
        ).content.decode()

        self.assertEqual(self._por_tarjeta(), por_documento)

    def test_la_url_no_es_adivinable(self):
        """`ALC-OUT-08`, Ley 1581 de 2012, y `DT-18`.

        La dirección de la fotografía de un menor no puede deducirse de su
        documento ni de su identificador. Lo que sirve la plantilla es lo que
        firma el almacenamiento privado, y aquí se comprueba que por ahí no se
        cuela ninguno de los dos.
        """
        self._con_fotografia()

        cuerpo = self._por_tarjeta()
        inicio = cuerpo.index("<img src=") + len('<img src="')
        url = cuerpo[inicio : cuerpo.index('"', inicio)]

        self.assertNotIn(self.estudiante.documento, url)
        self.assertNotIn(str(self.estudiante.id), url)

    def test_el_estudiante_de_baja_tambien_se_ve(self):
        """`INVD-2` no esconde la cara: se identifica igual y no se le vende.

        Y aquí importa más que nunca — una tarjeta de alguien que ya no está en
        el colegio es justo la que más probablemente esté en manos de otro.
        """
        from personas.services import dar_de_baja

        self._con_fotografia()
        dar_de_baja(actor=self.institucion, estudiante=self.estudiante)

        cuerpo = self._por_tarjeta()

        self.assertIn(self.estudiante.url_de_la_foto, cuerpo)
        self.assertIn("No se le puede vender", cuerpo)


@override_settings(STORAGES=EN_MEMORIA)
class SinFotografiaLaVentaProcedeIgualTest(TestCase):
    """Segundo criterio de `HU-58`, y lo que ese criterio implica.

    «La venta procede igual» tiene dos mitades. Una es que no se rompa nada, y se
    comprueba haciendo la identificación sin fotografía. La otra es que el cajero
    **sepa** que no la hay: el control preventivo no está disponible para ese
    estudiante, y silenciarlo sería peor que no tenerlo — quien ve una silueta
    genérica cree que miró la foto.
    """

    def setUp(self):
        self.estudiante = estudiante()
        self.client.force_login(
            Usuario.objects.crear_usuario(
                email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
            )
        )
        self.url = reverse("identificacion-en-el-punto-de-venta")
        self.cuerpo = self.client.get(
            self.url, {"codigo": self.estudiante.codigo_tarjeta}
        ).content.decode()

    def test_sin_fotografia_la_identificacion_funciona_entera(self):
        self.assertFalse(self.estudiante.tiene_foto)
        self.assertIn("Ana Sofía Restrepo Ruiz", self.cuerpo)
        self.assertIn("Saldo", self.cuerpo)
        self.assertIn("Consumo de hoy", self.cuerpo)

    def test_no_se_pinta_ninguna_imagen_rota(self):
        """Sin fotografía no hay `<img>`: una etiqueta con el `src` vacío pide la
        página a sí misma y deja un icono de imagen rota donde debería estar la
        cara."""
        self.assertNotIn("<img", self.cuerpo)

    def test_el_hueco_se_ve_y_dice_lo_que_falta(self):
        """El marcador es visible, no un `alt` ni un `title` que nadie lee."""
        self.assertIn("Sin foto", self.cuerpo)

    def test_el_hueco_no_es_un_avatar_generico(self):
        """La diferencia entre «no se pudo comprobar» y «se comprobó».

        El borde discontinuo es lo que distingue el hueco de un retrato: es la
        misma señal que el resto de los huecos del punto de venta (`[S2.4]`).
        """
        self.assertIn("border-dashed", self.cuerpo)
