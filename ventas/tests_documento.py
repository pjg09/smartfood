"""`TT-73`. Buscar al estudiante por documento (`HU-16`).

Los dos criterios:

1. **La búsqueda por documento es una alternativa al escaneo, con el mismo
   resultado.** «El mismo» se comprueba literalmente: se identifica al mismo
   estudiante por las dos vías y se compara **el fragmento servido**, no el
   objeto. Si una vía enseñara algo distinto —o dejara de avisar de que el
   estudiante está de baja—, esto falla.
2. **Las restricciones, el saldo y el límite se aplican igual que con tarjeta.**
   Los tres llegan con `HU-17` y `HU-21`; lo que hoy se puede comprobar es que
   las dos vías desembocan en la misma vista y el mismo fragmento, que es lo que
   hará imposible que diverjan cuando existan.
"""

from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from personas.selectors import identificar_por_documento
from personas.services import dar_de_baja


def estudiante(nombre="Ana Sofía Restrepo Ruiz", documento="1001234501"):
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente{documento}@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
    )
    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"43{documento[:6]}"
    )
    return Estudiante.objects.create(
        nombre=nombre,
        documento=documento,
        acudiente=acudiente,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )


class ElSelectorBuscaPorDocumentoTest(TestCase):
    def setUp(self):
        self.estudiante = estudiante()

    def test_encuentra_por_documento_exacto(self):
        self.assertEqual(
            identificar_por_documento(self.estudiante.documento), self.estudiante
        )

    def test_tolera_los_separadores_con_los_que_se_copia_una_cedula(self):
        for variante in ["1.001.234.501", " 1001234501 ", "1 001 234 501"]:
            with self.subTest(variante=variante):
                self.assertEqual(identificar_por_documento(variante), self.estudiante)

    def test_un_documento_con_separadores_de_verdad_se_busca_tal_cual_primero(self):
        """El campo admite texto, no solo dígitos (`./formato-de-carga.md`).

        Filtrar antes de buscar rompería a quien tenga un documento con puntos o
        guiones **de verdad**. Por eso la primera consulta es literal.
        """
        con_guion = estudiante(nombre="Luis Pérez", documento="CE-12345")

        self.assertEqual(identificar_por_documento("CE-12345"), con_guion)

    def test_no_hay_busqueda_parcial(self):
        """Buscar «100» y recibir treinta menores sería servirle el padrón a quien
        está en la caja, y `[S11]` no se lo da."""
        with self.assertRaises(Estudiante.DoesNotExist):
            identificar_por_documento("100")

    def test_un_documento_vacio_no_identifica_a_nadie(self):
        for vacio in ["", "   ", None]:
            with self.subTest(vacio=repr(vacio)):
                with self.assertRaises(Estudiante.DoesNotExist):
                    identificar_por_documento(vacio)


class LasDosViasDanElMismoResultadoTest(TestCase):
    """Primer criterio de `HU-16`, comprobado sobre el HTML servido."""

    def setUp(self):
        self.estudiante = estudiante()
        cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        self.client.force_login(cajero)
        self.url = reverse("identificacion-en-el-punto-de-venta")

    def _por_tarjeta(self):
        return self.client.get(
            self.url, {"codigo": self.estudiante.codigo_tarjeta}
        ).content.decode()

    def _por_documento(self):
        return self.client.get(
            self.url, {"documento": self.estudiante.documento}
        ).content.decode()

    def test_el_fragmento_es_identico_por_las_dos_vias(self):
        """No «equivalente»: idéntico. Es lo que hace imposible que diverjan."""
        self.assertEqual(self._por_tarjeta(), self._por_documento())

    def test_por_documento_tambien_avisa_de_que_no_puede_comprar(self):
        """Segundo criterio: el estado se aplica igual por las dos vías (`INVD-2`).

        Sin esto, quien olvida la tarjeta podría acabar en una venta que la vía
        del lector habría frenado.
        """
        institucion = Usuario.objects.crear_usuario(
            email="institucion@example.com", rol=Rol.INSTITUCION, nombre="Colegio"
        )
        dar_de_baja(actor=institucion, estudiante=self.estudiante)

        cuerpo = self._por_documento()

        self.assertIn("De baja", cuerpo)
        self.assertIn("No se le puede vender", cuerpo)
        self.assertEqual(self._por_tarjeta(), cuerpo)

    def test_por_documento_tampoco_ensena_el_saldo(self):
        """`[S11]`: el cajero lo ve **solo al cobrar**, venga por donde venga."""
        self.assertNotIn("Saldo", self._por_documento())

    def test_un_documento_desconocido_dice_que_hacer(self):
        cuerpo = self.client.get(self.url, {"documento": "9999999999"}).content.decode()

        self.assertIn("Ningún estudiante con ese documento", cuerpo)
        self.assertIn("9999999999", cuerpo)
        # Y remite a quien puede arreglarlo: el padrón es de la institución.
        self.assertIn("institución educativa", cuerpo)

    def test_solo_el_cajero_busca_por_documento(self):
        for rol in [Rol.ACUDIENTE, Rol.ADMINISTRADOR, Rol.INSTITUCION]:
            with self.subTest(rol=rol):
                actor = Usuario.objects.crear_usuario(
                    email=f"{rol}@example.com", rol=rol, nombre="Otro"
                )
                self.client.force_login(actor)
                respuesta = self.client.get(
                    self.url, {"documento": self.estudiante.documento}
                )
                self.assertEqual(respuesta.status_code, 403)


class ElCampoDeDocumentoEnLaPantallaTest(TestCase):
    def setUp(self):
        cajero = Usuario.objects.crear_usuario(
            email="cajero2@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        self.client.force_login(cajero)
        self.cuerpo = self.client.get(reverse("punto-de-venta")).content.decode()

    def test_hay_un_campo_de_documento_que_busca_con_enter(self):
        self.assertIn('id="documento"', self.cuerpo)
        self.assertIn("keyup[key=='Enter']", self.cuerpo)

    def test_pide_a_la_misma_ruta_que_el_escaneo(self):
        """Una sola ruta para las dos vías: es lo que hace que el resultado sea
        el mismo sin que nadie tenga que mantenerlo así."""
        self.assertEqual(
            self.cuerpo.count(reverse("identificacion-en-el-punto-de-venta")), 2
        )

    def test_el_foco_vuelve_al_lector_tras_buscar_por_documento(self):
        """Si se quedara en el documento, la siguiente tarjeta escaneada acabaría
        escrita ahí y buscaría un documento que no existe."""
        self.assertIn("data-vuelve-al-lector", self.cuerpo)
