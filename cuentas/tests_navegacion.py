"""`DEC-16`. Dónde aterriza cada rol y qué es la portada.

Dos reglas que se sostienen entre sí:

1. **La portada es una sola y no cambia con quién mire.** Es la cara pública del
   producto, y quien tiene sesión no la ve: se le reparte a su panel.
2. **Quien entra aterriza en su trabajo**, no en una pantalla que le obliga a
   elegir a dónde ir. El reparto es `[S11]` leído como navegación.

Antes de esto, `LOGIN_REDIRECT_URL` era la portada y la portada se reescribía a
sí misma según la sesión: dos condicionales que decidían la navegación desde
dentro de una plantilla, donde nada los vigilaba.
"""

from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from django.test import Client

from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos

CLAVE = "clave-de-prueba-2026"

# Dónde tiene que acabar cada rol. **Es la tabla del documento**, y si alguien
# cambia el reparto sin cambiarla, esta prueba lo dice.
ATERRIZAJES = [
    (Rol.INSTITUCION, "/padron/"),
    (Rol.ADMINISTRADOR, "/admin/panel/"),
    (Rol.CAJERO, "/punto-de-venta/"),
    (Rol.ACUDIENTE, "/mis-estudiantes/"),
]


def _se_pregunta_quien_mira(plantilla):
    """Si la plantilla decide algo mirando quién tiene la sesión."""
    return "user.is_authenticated" in plantilla


def cuenta(rol):
    """Por el camino real: `[S11]` concede los permisos al grupo del rol.

    La administración necesita además `is_staff`, o `/admin/` la devuelve a su
    propia pantalla de acceso — que es exactamente el `302` que vio esta prueba
    la primera vez que se ejecutó.
    """
    sincronizar_grupos_y_permisos()
    usuario = crear_cuenta(
        email=f"{rol}@example.com",
        rol=rol,
        nombre=f"Cuenta {rol}",
        accede_a_administracion=rol in (Rol.INSTITUCION, Rol.ADMINISTRADOR),
        enviar_invitacion=False,
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
    return usuario


class CadaRolAterrizaEnLoSuyoTest(TestCase):
    def test_el_acceso_lleva_al_panel_de_cada_rol(self):
        for rol, destino in ATERRIZAJES:
            with self.subTest(rol=rol):
                cuenta(rol)
                # Un cliente por rol: `subTest` no ejecuta lo que venga después
                # de una aserción que falla, así que un `logout()` al final del
                # bloque no se llega a llamar y el rol siguiente heredaría la
                # sesión del anterior.
                cliente = Client()
                respuesta = cliente.post(
                    reverse("acceso"),
                    {"username": f"{rol}@example.com", "password": CLAVE},
                    follow=True,
                )

                # La cadena completa: acceso → /panel/ → la pantalla del rol.
                self.assertEqual(respuesta.redirect_chain[0][0], reverse("panel"))
                self.assertEqual(respuesta.redirect_chain[-1][0], destino)

    def test_el_reparto_no_es_para_anonimos(self):
        respuesta = self.client.get(reverse("panel"))

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("acceso"), respuesta.headers["Location"])


class LaPortadaEsUnaSolaTest(TestCase):
    def test_sin_sesion_se_sirve_la_portada(self):
        respuesta = self.client.get(reverse("inicio"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "inicio.html")

    def test_con_sesion_no_se_ve_la_portada_sino_el_panel(self):
        cuenta(Rol.CAJERO)
        self.client.login(username=f"{Rol.CAJERO}@example.com", password=CLAVE)

        respuesta = self.client.get(reverse("inicio"), follow=True)

        self.assertEqual(respuesta.redirect_chain[0][0], reverse("panel"))
        self.assertEqual(respuesta.redirect_chain[-1][0], "/punto-de-venta/")

    PORTADA = ("inicio.html", "base-publica.html")

    def test_ninguna_plantilla_de_la_portada_se_pregunta_quien_mira(self):
        """La regla 1, fijada donde de verdad se rompería.

        Renderizar la portada no bastaría: sin sesión, un `{% if %}` que mira al
        usuario también pinta la rama pública y la prueba pasaría igual. Lo que
        no puede existir es la pregunta.
        """
        raiz = Path(settings.BASE_DIR) / "templates"
        culpables = [
            nombre
            for nombre in self.PORTADA
            if _se_pregunta_quien_mira((raiz / nombre).read_text())
        ]

        self.assertEqual(
            culpables,
            [],
            "la portada no cambia con la sesión (`DEC-16`): quien la tiene no "
            "llega a verla, así que el condicional solo puede dar problemas.",
        )

    def test_y_la_contraprueba_de_que_sabría_encontrarlo(self):
        """Que el criterio de arriba no pasa por no mirar.

        Se prueba contra el texto que tenía la portada antes de `DEC-16`, no
        contra otro fichero del repositorio: así la contraprueba sigue valiendo
        el día que ese otro fichero cambie por un motivo que no tiene que ver.
        """
        como_era = """
          {% if user.is_authenticated %}
            <a href="{% url 'mis-estudiantes' %}">Mis estudiantes</a>
          {% else %}
            <a href="{% url 'acceso' %}">Entrar</a>
          {% endif %}
        """

        self.assertTrue(_se_pregunta_quien_mira(como_era))


class LaBarraLlevaSoloADondeSePuedeEntrarTest(TestCase):
    """`DEC-16`. Cada rol es un dashboard, y su barra es lo que alcanza.

    **Esta es la prueba que hace que «un solo dashboard» signifique algo.** La
    barra no protege nada —`INV-4` se sostiene en la capa de datos, no
    escondiendo enlaces (`DT-11`)—, pero un enlace que lleva a un `403` es peor
    que no tenerlo: promete una pantalla y da un portazo.

    Se recorre el menú de cada rol, se pide cada entrada con una cuenta de ese
    rol y se exige `200`. Con las secciones del admin dentro de la barra, esto
    cubre de una vez que los permisos de `[S11]` y las entradas de la barra
    dicen lo mismo — que antes eran dos listas que nadie cruzaba.
    """

    def test_cada_entrada_del_menu_responde_a_su_rol(self):
        from django.urls import reverse as resolver

        from cuentas.templatetags.interfaz import MENU_POR_ROL

        for rol, entradas in MENU_POR_ROL.items():
            usuario = cuenta(rol)
            cliente = Client()
            cliente.force_login(usuario)

            for entrada in entradas:
                with self.subTest(rol=rol, entrada=entrada.etiqueta):
                    respuesta = cliente.get(resolver(entrada.ruta))

                    self.assertEqual(
                        respuesta.status_code,
                        200,
                        f"«{entrada.etiqueta}» está en la barra de {rol} y "
                        f"responde {respuesta.status_code}: o sobra del menú, o "
                        f"falta el permiso en [S11].",
                    )

    def test_ningun_menu_ofrece_la_portada(self):
        """`DEC-16`: quien tiene sesión no ve la portada, así que no se enlaza.

        Un «Inicio» en la barra llevaría a `/`, que redirige al panel del rol:
        una entrada que promete una pantalla y lleva a otra.
        """
        from cuentas.templatetags.interfaz import MENU_POR_ROL

        con_inicio = {
            rol: [e.etiqueta for e in entradas if e.ruta == "inicio"]
            for rol, entradas in MENU_POR_ROL.items()
        }

        self.assertEqual({rol: e for rol, e in con_inicio.items() if e}, {})


class ElAdminTraeElArmazonEnteroTest(TestCase):
    """Lo que se perdió al sustituir la cabecera del admin, y no puede repetirse.

    Al poner la cabecera de la aplicación en lugar de la suya, el admin se quedó
    **sin conmutador de tema**: el suyo vivía en `usertools`, dentro del bloque
    sustituido. La consecuencia no se veía en las pruebas ni en el código —la
    pantalla salía bien— pero quedaba clavada en lo que dijera el sistema
    operativo, sin forma de cambiarlo.

    Se afirma sobre los `data-*` del armazón y no sobre la copia: los rótulos
    cambian y estos atributos son lo que el script busca.
    """

    def setUp(self):
        self.client.force_login(cuenta(Rol.INSTITUCION))

    def _pantalla_del_admin(self):
        return self.client.get("/admin/cuentas/usuario/").content.decode()

    def test_una_pantalla_del_admin_trae_barra_cabecera_y_tema(self):
        cuerpo = self._pantalla_del_admin()

        self.assertIn("data-selector-de-tema", cuerpo)
        self.assertIn("data-alternar-barra", cuerpo)
        self.assertIn("data-modal-admin", cuerpo)

    def test_y_trae_las_entradas_del_rol_que_mira(self):
        """La barra del admin es la misma del resto, no una copia.

        Se comprueban las dos clases de entrada que conviven desde `DEC-17`:
        una pantalla propia —el padrón— y una que sigue dentro del admin. La de
        acudientes ya no vale como ejemplo: dejó de ser del admin.
        """
        from django.urls import reverse as resolver

        cuerpo = self._pantalla_del_admin()

        self.assertIn(resolver("padron"), cuerpo)
        self.assertIn(resolver("acudientes"), cuerpo)
        self.assertIn(resolver("admin:cuentas_usuario_changelist"), cuerpo)
