"""El token CSRF de las peticiones de HTMX que no salen de un formulario.

**Defecto que vivió medio proyecto, corregido el 2026-09-21.** Los botones del
catálogo del punto de venta llevan `hx-post` y **no cuelgan de ningún
`<form>`** —es una rejilla de productos, no un formulario—, y de un formulario
es de donde HTMX saca el token. Así que añadir un producto al ticket respondía
`403` en el navegador **con las 1.489 pruebas de entonces en verde**.

Por qué ninguna lo cazó: el cliente de pruebas de Django **no aplica CSRF** a
menos que se le pida con `Client(enforce_csrf_checks=True)`. Sin esa bandera un
`hx-post` sin token pasa toda la suite y falla solo al pulsarlo.

El arreglo pone el token en `hx-headers` del `<body>` de `base.html`, del que
heredan los cuatro armazones, y estas pruebas son las que lo vigilan. Las tres
mitades importan:

1. La pantalla **entrega** el token en el atributo
   (`ElArmazonEntregaElTokenTest`).
2. La petición **no pasa sin él**, y sí con él, contra un cliente que de verdad
   comprueba CSRF (`UnHxPostSinTokenNoPasaTest`).
3. El catálogo **sigue sin formulario**, que es lo que hace imprescindible a las
   dos anteriores (`ElCatalogoNoCuelgaDeUnFormularioTest`).

Sin la 1 alguien borra el atributo y la 2 seguiría verde tomando el token de la
cookie. Sin la 3, el día que el catálogo se envuelva en un `<form>` nadie sabría
que estas pruebas dejaron de proteger lo que decían proteger.
"""

import json
import re
from pathlib import Path

from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from ventas.tests_carrito import producto

# El atributo tal como lo escribe `base.html`, con el token ya renderizado.
HX_HEADERS = re.compile(r"hx-headers='([^']*)'")

# `{% comment %}…{% endcomment %}`, para no confundir una explicación con
# una etiqueta.
COMENTARIO = re.compile(r"{%\s*comment\s*%}.*?{%\s*endcomment\s*%}", re.DOTALL)


def cajero(email="cajero@example.com"):
    return Usuario.objects.crear_usuario(email=email, rol=Rol.CAJERO, nombre="Cajero")


class ElArmazonEntregaElTokenTest(TestCase):
    """La pantalla trae el token en el atributo que HTMX lee."""

    def setUp(self):
        self.client.force_login(cajero())

    def test_el_body_del_punto_de_venta_declara_la_cabecera(self):
        cuerpo = self.client.get(reverse("punto-de-venta")).content.decode()

        encontrado = HX_HEADERS.search(cuerpo)
        self.assertIsNotNone(
            encontrado,
            "`base.html` debe declarar `hx-headers` en el `<body>`: sin él, un "
            "`hx-post` que no viva en un `<form>` sale sin token.",
        )

        cabeceras = json.loads(encontrado.group(1))
        self.assertIn("X-CSRFToken", cabeceras)
        self.assertNotEqual(cabeceras["X-CSRFToken"], "")
        # Es el token de esta respuesta, no una cadena cualquiera.
        self.assertNotIn("csrf_token", cabeceras["X-CSRFToken"])

    def test_tambien_lo_trae_una_pantalla_de_otro_armazon(self):
        """Los cuatro armazones cuelgan del mismo `<body>` (`DT-25`).

        El defecto se vio en el punto de venta, pero el padrón y las
        restricciones también publican `hx-post`. Si el atributo se moviera a
        la base del punto de venta, esta prueba lo diría.
        """
        # Sin sesión: con una abierta, `/login/` redirige al panel del rol y
        # la respuesta no trae cuerpo que mirar.
        cuerpo = Client().get(reverse("acceso")).content.decode()

        self.assertIsNotNone(HX_HEADERS.search(cuerpo))

    def test_no_hay_ningun_otro_body_que_esquive_el_atributo(self):
        """La garantía estructural, y la que no depende de qué pantalla se mire.

        Mientras el proyecto tenga **un solo** `<body>` y sea el de
        `base.html`, ninguna pantalla puede publicar un `hx-post` sin token.
        """
        raiz = Path(settings.BASE_DIR) / "templates"
        con_body = {}
        for ruta in sorted(raiz.rglob("*.html")):
            texto = ruta.read_text()
            # Sin lo comentado: `partials/iconos.html` nombra el `<body>` para
            # explicar dónde se incluye, y eso no es una etiqueta.
            if re.search(r"<body[\s>]", COMENTARIO.sub("", texto)):
                con_body[str(ruta.relative_to(raiz))] = texto

        self.assertEqual(list(con_body), ["base.html"])
        self.assertIn("hx-headers", con_body["base.html"])


class UnHxPostSinTokenNoPasaTest(TestCase):
    """La mitad que exige el defecto: un cliente que comprueba CSRF de verdad.

    `self.client` no sirve aquí — no aplica CSRF y por eso el `403` del
    navegador no salía en ninguna prueba.
    """

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(cajero())
        self.empanada = producto()
        self.carrito = reverse("carrito-del-punto-de-venta")
        # Cargar la pantalla primero, como el cajero: así el cliente queda con
        # la cookie CSRF puesta y lo único que falta luego es la cabecera, que
        # es exactamente el estado en el que el navegador recibía el `403`.
        self.token = self._token_de_la_pantalla()

    def _token_de_la_pantalla(self):
        """El token como lo toma HTMX: del atributo, no de la cookie."""
        cuerpo = self.client.get(reverse("punto-de-venta")).content.decode()
        encontrado = HX_HEADERS.search(cuerpo)
        self.assertIsNotNone(
            encontrado,
            "la pantalla no publica `hx-headers`: HTMX no tiene de dónde tomar "
            "el token y todo `hx-post` de fuera de un `<form>` saldrá sin él.",
        )
        return json.loads(encontrado.group(1))["X-CSRFToken"]

    def _anadir(self, **extra):
        return self.client.post(
            self.carrito,
            {"producto": str(self.empanada.id), "accion": "anadir"},
            **extra,
        )

    def test_sin_la_cabecera_django_lo_rechaza(self):
        # `assertLogs` además fija **por qué** es `403`: el cajero sí puede
        # tocar el carrito, así que un rechazo por rol pasaría esta prueba sin
        # tener nada que ver con el defecto. Y de paso el aviso de seguridad no
        # se cuela en la salida de la suite.
        with self.assertLogs("django.security.csrf", level="WARNING") as registro:
            respuesta = self._anadir()

        self.assertEqual(respuesta.status_code, 403)
        self.assertIn("CSRF token missing", registro.output[0])

    def test_con_la_cabecera_que_publica_el_armazon_pasa(self):
        respuesta = self._anadir(headers={"x-csrftoken": self.token})

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Empanada")


class ElCatalogoNoCuelgaDeUnFormularioTest(TestCase):
    """Por qué el token tiene que ir en la cabecera y no en un campo.

    HTMX incluye el token solo si el elemento vive dentro de un `<form>` que lo
    lleve. El catálogo del punto de venta es una rejilla de botones, así que
    `{% csrf_token %}` no tiene dónde ir.
    """

    CATALOGO = Path(settings.BASE_DIR) / "templates/ventas/partials/catalogo.html"

    def test_publica_hx_post_y_no_tiene_formulario(self):
        plantilla = self.CATALOGO.read_text()

        self.assertIn("hx-post", plantilla)
        self.assertNotIn(
            "<form",
            plantilla,
            "si el catálogo pasa a ser un formulario, esta prueba y sus "
            "hermanas dejan de estar vigilando el defecto que las trajo.",
        )
