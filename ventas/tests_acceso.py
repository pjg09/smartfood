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
    cuesta una venta mal cobrada. `HU-17` trae el saldo, el consumo del día y las
    restricciones; hasta entonces, el hueco dice de quién es.
    """

    def setUp(self):
        self.client.force_login(usuario_con_rol(Rol.CAJERO, "cajero@example.com"))
        self.cuerpo = self.client.get(reverse("punto-de-venta")).content.decode()

    def test_declara_las_historias_que_llenaran_cada_hueco(self):
        """`HU-15` y `HU-16` ya no están en la lista, y por la mejor razón:
        **están construidas**. El escaneo es `TT-70` y `TT-71`; la búsqueda por
        documento, `TT-73`. Los dos campos buscan de verdad, así que sus huecos
        dejaron de ser huecos. Lo que queda por llenar es lo de abajo.

        `HU-16` sale de la lista en este mismo Pull Request: hasta ahora el aviso
        del hueco la citaba como pendiente aunque el campo ya existiera, que es
        la clase de texto que se queda viejo sin que nadie lo note.
        """
        for historia in ["HU-17", "HU-21"]:
            with self.subTest(historia=historia):
                self.assertIn(historia, self.cuerpo)

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
