"""`TT-57`, `TT-58`. La puerta del punto de venta (`INT-2`, `[S11]`, `DT-11`).

Trabajo de habilitación: **no cierra ninguna historia**. Lo que fija es quién
llega a la pantalla del punto de venta y quién no, que es la condición de la que
cuelgan todas las historias del sprint a partir de `HU-15`.

`[S11]` concede «registrar ventas en el punto de venta» a `USR-3` y **a nadie
más**. Que la administración de la cafetería reciba un `403` no es un olvido: es
la matriz. Y la comprobación vive en la vista y no en la plantilla, porque
`DT-11` es explícito —el control de acceso es de la capa de datos, no del
layout—: esconder el enlace deja la pantalla abierta a quien escriba la URL.
"""

from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario


def usuario_con_rol(rol, email):
    return Usuario.objects.crear_usuario(email=email, rol=rol, nombre="Persona de prueba")


class SoloElCajeroEntraAlPuntoDeVentaTest(TestCase):
    def test_el_cajero_llega_a_la_pantalla(self):
        self.client.force_login(usuario_con_rol(Rol.CAJERO, "cajero@example.com"))

        respuesta = self.client.get(reverse("punto-de-venta"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "ventas/punto-de-venta.html")

    def test_ningun_otro_rol_entra(self):
        """Incluida la administración de la cafetería: `[S11]` no le da la caja."""
        otros = [
            (Rol.ACUDIENTE, "acudiente@example.com"),
            (Rol.ADMINISTRADOR, "administracion@example.com"),
            (Rol.INSTITUCION, "institucion@example.com"),
        ]

        for rol, email in otros:
            with self.subTest(rol=rol):
                self.client.force_login(usuario_con_rol(rol, email))
                respuesta = self.client.get(reverse("punto-de-venta"))
                self.assertEqual(respuesta.status_code, 403)

    def test_sin_sesion_manda_a_la_pantalla_de_acceso(self):
        """No un `403`: quien no ha entrado todavía no tiene rol que rechazar."""
        respuesta = self.client.get(reverse("punto-de-venta"))

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("acceso"), respuesta.headers["Location"])

    def test_la_pantalla_no_se_escribe(self):
        """`POST` responde `405`.

        La venta se asienta en `HU-21` con su propio servicio y su propia ruta
        (`TT-80`). Esta vista solo pinta, y dejarla aceptar escrituras sería
        abrir la puerta antes de que exista la cerradura.
        """
        self.client.force_login(usuario_con_rol(Rol.CAJERO, "cajero@example.com"))

        respuesta = self.client.post(reverse("punto-de-venta"))

        self.assertEqual(respuesta.status_code, 405)


class ElPuntoDeVentaNoAdelantaNingunaHistoriaTest(TestCase):
    """La pantalla declara qué falta; no enseña cifras que todavía no existen.

    Un cero en el saldo se lee como un saldo de cero, y en la caja esa confusión
    cuesta una venta mal cobrada. La pantalla recién abierta **no tiene a quién
    cobrarle**, así que no escribe ninguna cifra: el saldo y el consumo del día
    llegan con el estudiante identificado (`HU-17`, `PR-09`), y el catálogo y el
    cobro siguen siendo huecos que dicen qué historia los llena.
    """

    def setUp(self):
        self.client.force_login(usuario_con_rol(Rol.CAJERO, "cajero@example.com"))
        self.cuerpo = self.client.get(reverse("punto-de-venta")).content.decode()

    def test_declara_las_historias_que_llenaran_cada_hueco(self):
        """La lista mengua a medida que las historias llegan, y eso es lo sano.

        `HU-15` y `HU-16` salieron cuando los dos campos empezaron a buscar de
        verdad (`TT-70`, `TT-71`, `TT-73`). `HU-17` sale en `PR-09`: la columna
        del estudiante ya enseña saldo y consumo del día, así que su hueco dejó
        de ser un hueco — el único que queda de esa historia es el bloque de
        restricciones, y vive en el fragmento, no en esta página.

        Queda el cobro. El día que un hueco cite una historia ya construida, este
        texto se ha quedado viejo sin que nadie lo note, y por eso se comprueba.
        """
        self.assertIn("HU-21", self.cuerpo)
        self.assertNotIn("HU-17", self.cuerpo)

    def test_los_huecos_no_son_botones_apagados(self):
        """Un hueco dice qué historia lo llena; no finge la acción que falta.

        Es la diferencia entre declarar y adelantar. Un «Cobrar» deshabilitado
        promete que un día hará algo y no dice cuándo ni de qué depende, y en una
        caja invita a pulsarlo esperando que reaccione. El bloque punteado con el
        identificador de la historia dice las dos cosas.
        """
        self.assertNotIn("disabled", self.cuerpo)

    def test_el_campo_de_identificacion_retiene_el_foco(self):
        """`TT-57`: la pistola escribe donde esté el foco.

        El atributo es el contrato entre la plantilla y `assets/js/interfaz.js`.
        `TT-71` colgará de este mismo campo la búsqueda al recibir Enter.
        """
        self.assertIn("data-foco-permanente", self.cuerpo)

    def test_la_barra_no_se_despliega_ni_hay_cajon(self):
        """`INT-2`: quien cobra no navega.

        La pantalla tiene una columna de iconos, pero **no es la barra de
        `INT-1`**: no se despliega —no hay botón que lo intente— y no tiene
        cajón de móvil. Las dos cosas que se descartan son las mismas de antes,
        y por el mismo motivo: los 280 px de las etiquetas salen de la zona
        donde el cajero pulsa, y un cajón es un sitio al que llegar por error
        con cola delante.

        Que la columna exista no reabre la navegación: su única entrada es esta
        misma pantalla. Sirve para situarse y para salir, que es justo lo que
        `INT-2` deja hacer.
        """
        self.assertNotIn("data-alternar-barra", self.cuerpo)
        self.assertNotIn("data-cajon", self.cuerpo)
        self.assertIn(reverse("salir"), self.cuerpo)
