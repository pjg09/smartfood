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
        for historia in ["HU-15", "HU-16", "HU-17", "HU-21"]:
            with self.subTest(historia=historia):
                self.assertIn(historia, self.cuerpo)

    def test_el_campo_de_identificacion_retiene_el_foco(self):
        """`TT-57`: la pistola escribe donde esté el foco.

        El atributo es el contrato entre la plantilla y `assets/js/interfaz.js`.
        `TT-71` colgará de este mismo campo la búsqueda al recibir Enter.
        """
        self.assertIn("data-foco-permanente", self.cuerpo)

    def test_no_lleva_navegacion(self):
        """`INT-2`: quien cobra no navega.

        Sin barra lateral y sin cajón: las dos cosas del armazón de `INT-1` que
        aquí serían sitios a los que llegar por error con cola delante. Lo único
        que sale de esta pantalla es cerrar sesión.
        """
        self.assertNotIn("data-alternar-barra", self.cuerpo)
        self.assertNotIn("data-cajon", self.cuerpo)
        self.assertIn(reverse("salir"), self.cuerpo)
