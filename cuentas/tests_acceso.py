"""`TT-56`. Pantalla de acceso al sistema (`DEC-12`).

Trabajo de habilitación, no una historia: **ninguna de las 59 historias pide un
inicio de sesión**. La única mención en todo el backlog es un criterio de
`HU-42` —«una cuenta desactivada no puede iniciar sesión»— que *presupone* que
el acceso existe. Para `USR-3`, `USR-4` y `USR-5` lo resolvía el admin de Django
(`INT-3`, `DT-2`); para `USR-2` no había nada, y `TT-29` lo necesita.

Lo que estas pruebas fijan:

1. El acudiente entra por una pantalla propia y llega a su interfaz (`INT-1`).
2. El acudiente **no** puede entrar por el admin, que es lo que había antes.
3. Abrir el acceso **no abre un camino de alta**: `INV-6` e `INVD-1` intactas.
4. Una cuenta desactivada no entra por la pantalla nueva (`HU-42`).
"""

from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from cuentas.services import desactivar_cuenta, sincronizar_grupos_y_permisos
from personas.services import dar_de_alta_la_institucion

CLAVE = "clave-de-prueba-2026"


def acudiente_con_clave(email="acudiente@example.com"):
    """Un acudiente que ya definió su contraseña, como tras usar la invitación."""
    usuario = Usuario.objects.crear_usuario(
        email=email, rol=Rol.ACUDIENTE, nombre="Marta Ruiz Ochoa"
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
    return usuario


class PantallaDeAccesoTest(TestCase):
    def setUp(self):
        self.usuario = acudiente_con_clave()

    def test_la_pantalla_de_acceso_existe_y_se_sirve(self):
        respuesta = self.client.get(reverse("acceso"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "cuentas/acceso.html")

    def test_el_acudiente_entra_con_su_correo_y_su_contrasena(self):
        respuesta = self.client.post(
            reverse("acceso"),
            {"username": "acudiente@example.com", "password": CLAVE},
        )
        self.assertRedirects(respuesta, reverse("inicio"))
        self.assertEqual(self.client.session["_auth_user_id"], str(self.usuario.pk))

    def test_una_contrasena_equivocada_no_entra(self):
        respuesta = self.client.post(
            reverse("acceso"),
            {"username": "acudiente@example.com", "password": "no-es-esta"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_quien_no_definio_su_contrasena_no_entra(self):
        """La cuenta recién cargada existe, pero su clave no es utilizable."""
        Usuario.objects.crear_usuario(email="sin.clave@example.com", rol=Rol.ACUDIENTE)

        respuesta = self.client.post(
            reverse("acceso"), {"username": "sin.clave@example.com", "password": CLAVE}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_salir_cierra_la_sesion(self):
        self.client.force_login(self.usuario)
        self.client.post(reverse("salir"))
        self.assertNotIn("_auth_user_id", self.client.session)


class ElAdminNoSirveDeAccesoAlAcudienteTest(TestCase):
    """El motivo de que `TT-56` exista, escrito como prueba.

    `LOGIN_URL` apuntaba a `/admin/login/`, y ese formulario exige `is_staff`.
    El acudiente no accede a la administración porque `INT-1` no es el admin
    (`DT-2`): sin pantalla propia se le mandaba a una puerta que iba a
    rechazarlo siempre.
    """

    def test_el_acudiente_no_tiene_acceso_a_la_administracion(self):
        usuario = acudiente_con_clave()
        self.assertFalse(usuario.is_staff)

        entro = self.client.post(
            "/admin/login/",
            {"username": usuario.email, "password": CLAVE, "next": "/admin/"},
            follow=True,
        )
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(entro.status_code, 200)

    def test_una_vista_protegida_manda_a_la_pantalla_de_acceso(self):
        """Y no al admin, que es adonde mandaba antes."""
        respuesta = self.client.get(reverse("mis-estudiantes"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(
            respuesta.url.startswith(reverse("acceso")),
            f"un anónimo debería ir a {reverse('acceso')}, y fue a {respuesta.url}",
        )


class AbrirElAccesoNoAbreUnRegistroTest(TestCase):
    """`INV-6`, `INVD-1`. La pantalla nueva no es un camino de alta (`DT-10`).

    `TT-14` ya recorre el mapa de URL entero buscando rutas de registro y esa
    prueba sigue pasando con `acceso/` y `salir/` dentro. Aquí se fija lo que
    aquella no puede ver: que la pantalla no acepta un alta encubierta.
    """

    def test_la_pantalla_de_acceso_no_crea_la_cuenta_que_no_existe(self):
        antes = Usuario.objects.count()

        self.client.post(
            reverse("acceso"),
            {"username": "nadie@example.com", "password": CLAVE},
        )

        self.assertEqual(Usuario.objects.count(), antes)
        self.assertFalse(Usuario.objects.filter(email="nadie@example.com").exists())

    def test_la_pantalla_no_ofrece_ningun_enlace_de_registro(self):
        cuerpo = self.client.get(reverse("acceso")).content.decode()
        for palabra in ["registro", "registrarse", "signup", "crear cuenta"]:
            self.assertNotIn(palabra, cuerpo.lower(), f"«{palabra}» no puede aparecer")


class UnaCuentaDesactivadaNoEntraTest(TestCase):
    """`HU-42`, primer criterio, ahora sobre la pantalla que sí usa `USR-2`.

    `TT-19` lo probó contra `client.login`. Que el backend rechace no implica
    que la pantalla rechace: son dos afirmaciones distintas y la que el usuario
    vive es esta.
    """

    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo=CLAVE,
            )
        self.actor = institucion.usuario

        self.cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, is_staff=True
        )
        self.cajero.set_password(CLAVE)
        self.cajero.save(update_fields=["password"])

    def test_la_pantalla_de_acceso_rechaza_a_la_cuenta_desactivada(self):
        desactivar_cuenta(actor=self.actor, usuario=self.cajero)

        respuesta = self.client.post(
            reverse("acceso"), {"username": "cajero@example.com", "password": CLAVE}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
