"""`TT-70`, `TT-71`. Identificar al estudiante por su tarjeta (`HU-15`).

Los tres criterios de `HU-15`:

1. **El lector físico está integrado con el sistema.** El lector *es un teclado*:
   teclea el código y envía Enter. No hay driver ni SDK, así que «integrar» es
   que el campo dispare la búsqueda con esa tecla — lo que se comprueba aquí es
   la búsqueda; que el aparato teclee de verdad es `TT-72`.
2. **El escaneo identifica al estudiante** y trae su información de venta. Esa
   información es `HU-17` y llega desde `PR-09`: saldo y consumo del día, más el
   aviso de **si puede comprar**. Lo que se prueba aquí es que el escaneo la
   trae; que las cifras sean las correctas y que nadie más las vea es
   `ventas/tests_cobro.py`.
3. **Validación a escala reducida con tarjetas físicas.** Es `TT-72`, trabajo con
   una impresora y un lector de verdad: **no se puede automatizar**, y por eso
   esta historia no se cierra en este PR.

La decisión que conviene no perder: **un estudiante que no puede comprar se
identifica igual**. Filtrarlo aquí dejaría al cajero leyendo «esa tarjeta no es
de nadie», que es mentira.
"""

from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, EstadoDelEstudiante, Estudiante
from personas.selectors import identificar_por_codigo_de_tarjeta
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


class ElSelectorEncuentraPorCodigoTest(TestCase):
    """`TT-70`."""

    def setUp(self):
        self.estudiante = estudiante()

    def test_encuentra_al_estudiante_de_la_tarjeta(self):
        encontrado = identificar_por_codigo_de_tarjeta(self.estudiante.codigo_tarjeta)

        self.assertEqual(encontrado, self.estudiante)

    def test_normaliza_lo_que_llega_del_lector(self):
        """Un código correcto que no encuentra a nadie por un espacio es el peor
        fallo posible en una fila de veinte minutos."""
        codigo = self.estudiante.codigo_tarjeta

        for variante in [f" {codigo} ", f"{codigo}\n", codigo.lower()]:
            with self.subTest(variante=repr(variante)):
                self.assertEqual(identificar_por_codigo_de_tarjeta(variante), self.estudiante)

    def test_un_codigo_que_no_es_de_nadie_no_existe(self):
        with self.assertRaises(Estudiante.DoesNotExist):
            identificar_por_codigo_de_tarjeta("ZZZZZZZZZZZZZZ")

    def test_lo_que_ni_siquiera_tiene_forma_de_codigo_se_corta_antes(self):
        """`DT-9`, `INV-7`: la base tiene la misma regla en una `CheckConstraint`,
        así que ninguna fila puede tener otra forma y consultar sería un viaje
        seguro a cero resultados."""
        for basura in ["", "   ", "hola", "123", "I" * 14, self.estudiante.codigo_tarjeta + "X"]:
            with self.subTest(basura=repr(basura)):
                with self.assertRaises(Estudiante.DoesNotExist):
                    identificar_por_codigo_de_tarjeta(basura)

    def test_el_estudiante_de_baja_se_identifica_igual(self):
        """**La decisión de `TT-70`.** La tarjeta es correcta y el estudiante
        existe: lo que pasa es que no puede comprar. Decir «no es de nadie» sería
        mentir, y el cajero repetiría el escaneo tres veces."""
        institucion = Usuario.objects.crear_usuario(
            email="institucion@example.com", rol=Rol.INSTITUCION, nombre="Colegio"
        )
        dar_de_baja(actor=institucion, estudiante=self.estudiante)

        encontrado = identificar_por_codigo_de_tarjeta(self.estudiante.codigo_tarjeta)

        self.assertEqual(encontrado, self.estudiante)
        self.assertFalse(encontrado.puede_operar)


class ElEscaneoEnElPuntoDeVentaTest(TestCase):
    """`TT-71`. La vista, que devuelve **un fragmento, nunca una página** (`DT-16`)."""

    def setUp(self):
        self.estudiante = estudiante()
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        self.client.force_login(self.cajero)
        self.url = reverse("identificacion-en-el-punto-de-venta")

    def test_el_escaneo_devuelve_al_estudiante(self):
        respuesta = self.client.get(self.url, {"codigo": self.estudiante.codigo_tarjeta})

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "ventas/partials/estudiante-identificado.html")
        self.assertIn("Ana Sofía Restrepo Ruiz", respuesta.content.decode())
        self.assertIn("1001234501", respuesta.content.decode())

    def test_devuelve_un_fragmento_y_no_una_pagina(self):
        """`DT-16`. Si devolviera la página entera, cada escaneo repintaría el
        punto de venta y el foco se perdería con él."""
        cuerpo = self.client.get(
            self.url, {"codigo": self.estudiante.codigo_tarjeta}
        ).content.decode()

        self.assertNotIn("<html", cuerpo)
        self.assertNotIn("<body", cuerpo)

    def test_el_escaneo_trae_tambien_la_informacion_de_venta(self):
        """Segundo criterio de `HU-15`: identifica **y trae su información de
        venta** (`HU-17`).

        Hasta `PR-09` esta prueba afirmaba lo contrario —que el fragmento no
        enseñaba el saldo—, y era cierto: `HU-17` no estaba construida. Lo que
        `[S11]` dice del cajero es «solo al cobrar», y escanear una tarjeta en la
        caja **es** cobrar; lo que ese «solo» excluye es la consulta libre, y eso
        lo vigila `ventas/tests_cobro.py`, que es donde puede vigilarse de verdad.
        """
        cuerpo = self.client.get(
            self.url, {"codigo": self.estudiante.codigo_tarjeta}
        ).content.decode()

        self.assertIn("Saldo", cuerpo)

    def test_una_tarjeta_desconocida_dice_que_hacer(self):
        """No «no existe» a secas: lo que el cajero necesita saber es qué hacer
        ahora, y se le enseña lo leído porque casi siempre falta un carácter."""
        cuerpo = self.client.get(self.url, {"codigo": "ZZZZZZZZZZZZZZ"}).content.decode()

        self.assertIn("no es de nadie", cuerpo)
        self.assertIn("ZZZZZZZZZZZZZZ", cuerpo)

    def test_sin_codigo_no_dice_nada(self):
        """El primer pintado de la pantalla, o un Enter en un campo vacío."""
        cuerpo = self.client.get(self.url, {"codigo": ""}).content.decode()

        self.assertNotIn("no es de nadie", cuerpo)

    def test_avisa_de_que_el_estudiante_de_baja_no_compra(self):
        """`INVD-2`, **antes** de montar una venta que iba a fallar al cobrar."""
        institucion = Usuario.objects.crear_usuario(
            email="institucion@example.com", rol=Rol.INSTITUCION, nombre="Colegio"
        )
        dar_de_baja(actor=institucion, estudiante=self.estudiante)

        cuerpo = self.client.get(
            self.url, {"codigo": self.estudiante.codigo_tarjeta}
        ).content.decode()

        self.assertIn("Ana Sofía Restrepo Ruiz", cuerpo)
        self.assertIn("De baja", cuerpo)
        self.assertIn("No se le puede vender", cuerpo)

    def test_avisa_del_desactivado(self):
        self.estudiante.estado = EstadoDelEstudiante.DESACTIVADO
        self.estudiante.save(update_fields=["estado"])

        cuerpo = self.client.get(
            self.url, {"codigo": self.estudiante.codigo_tarjeta}
        ).content.decode()

        self.assertIn("Desactivado", cuerpo)
        self.assertIn("No se le puede vender", cuerpo)

    def test_solo_el_cajero_escanea(self):
        """`[S11]`, igual que la pantalla de la que cuelga (`TT-58`)."""
        for rol in [Rol.ACUDIENTE, Rol.ADMINISTRADOR, Rol.INSTITUCION]:
            with self.subTest(rol=rol):
                actor = Usuario.objects.crear_usuario(
                    email=f"{rol}@example.com", rol=rol, nombre="Otro"
                )
                self.client.force_login(actor)
                respuesta = self.client.get(
                    self.url, {"codigo": self.estudiante.codigo_tarjeta}
                )
                self.assertEqual(respuesta.status_code, 403)

    def test_sin_sesion_no_se_escanea(self):
        self.client.logout()

        respuesta = self.client.get(self.url, {"codigo": self.estudiante.codigo_tarjeta})

        self.assertEqual(respuesta.status_code, 302)


class ElCampoDeEscaneoDisparaConEnterTest(TestCase):
    """`TT-71`. El contrato entre la plantilla y el lector.

    El lector **es un teclado**: no hay nada que probar del aparato desde aquí
    —eso es `TT-72`, con hardware—, pero sí que la pantalla está preparada para
    lo único que el aparato hace: teclear y pulsar Enter.
    """

    def setUp(self):
        cajero = Usuario.objects.crear_usuario(
            email="cajero2@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        self.client.force_login(cajero)
        self.cuerpo = self.client.get(reverse("punto-de-venta")).content.decode()

    def test_el_campo_busca_al_recibir_enter(self):
        self.assertIn("keyup[key=='Enter']", self.cuerpo)
        self.assertIn(reverse("identificacion-en-el-punto-de-venta"), self.cuerpo)

    def test_el_resultado_reemplaza_solo_su_zona(self):
        """No la pantalla: repintarla se llevaría por delante el foco."""
        self.assertIn('hx-target="#estudiante-identificado"', self.cuerpo)
        self.assertIn('id="estudiante-identificado"', self.cuerpo)

    def test_el_campo_conserva_el_foco_permanente(self):
        self.assertIn("data-foco-permanente", self.cuerpo)
