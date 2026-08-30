"""Pruebas del alta por seed y la invitación (`HU-39`, `TT-09` … `TT-12`).

Cubren dos invariantes que este PR empieza a sostener:

- `INV-6` / `INVD-1`: ninguna cuenta nace de un autorregistro. Aquí se
  comprueba la mitad que ya existe —toda cuenta nace sin contraseña utilizable—;
  la otra mitad, que no haya rutas de registro, la cierra `TT-14` en `PR-09`.
- `ALC-OUT-10`: el prototipo opera sobre **una** institución.
"""

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.db import transaction
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta
from personas.models import Institucion
from personas.services import dar_de_alta_la_institucion


class AltaDeCuentaTest(TestCase):
    def test_la_cuenta_nace_sin_contrasena_utilizable(self):
        """`INV-6`, `INVD-1`, `DEC-3`: quien crea la cuenta no conoce la clave."""
        with self.captureOnCommitCallbacks(execute=True):
            usuario = crear_cuenta(email="cajero@example.com", rol=Rol.CAJERO)

        self.assertFalse(usuario.has_usable_password())
        self.assertFalse(usuario.tiene_contrasena_definida)

    def test_el_alta_dispara_la_invitacion(self):
        with self.captureOnCommitCallbacks(execute=True):
            crear_cuenta(email="cajero@example.com", rol=Rol.CAJERO)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["cajero@example.com"])
        self.assertIn("/invitacion/", mail.outbox[0].body)

    def test_no_invita_si_el_alta_se_deshace(self):
        class FalloDelAlta(Exception):
            pass

        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(FalloDelAlta):
                with transaction.atomic():
                    crear_cuenta(email="cajero@example.com", rol=Rol.CAJERO)
                    raise FalloDelAlta

        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(Usuario.objects.filter(email="cajero@example.com").exists())


class SeedDeLaInstitucionTest(TestCase):
    DATOS = {"nombre": "Colegio de Prueba", "email": "institucion@example.com"}

    def test_el_seed_crea_la_institucion_y_dispara_su_invitacion(self):
        """Los dos primeros criterios de `HU-39`."""
        with self.captureOnCommitCallbacks(execute=True):
            institucion, creada = dar_de_alta_la_institucion(**self.DATOS)

        self.assertTrue(creada)
        self.assertEqual(institucion.usuario.rol, Rol.INSTITUCION)
        self.assertTrue(institucion.usuario.is_staff, "debe poder entrar a INT-3")
        self.assertFalse(institucion.usuario.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)

    def test_el_seed_es_idempotente_y_no_reenvia_el_correo(self):
        with self.captureOnCommitCallbacks(execute=True):
            dar_de_alta_la_institucion(**self.DATOS)
        mail.outbox.clear()

        with self.captureOnCommitCallbacks(execute=True):
            _, creada = dar_de_alta_la_institucion(**self.DATOS)

        self.assertFalse(creada)
        self.assertEqual(Institucion.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0, "una segunda pasada no debe invitar de nuevo")

    def test_la_base_impide_una_segunda_institucion(self):
        """`ALC-OUT-10`. Lo impone la base, no un `if` (`DT-15`)."""
        with self.captureOnCommitCallbacks(execute=True):
            dar_de_alta_la_institucion(**self.DATOS)

        otro = Usuario.objects.crear_usuario(email="otra@example.com", rol=Rol.INSTITUCION)
        with self.assertRaises(IntegrityError):
            Institucion.objects.create(nombre="Segundo Colegio", usuario=otro)


class ContrasenaDeDesarrolloTest(TestCase):
    """`DEC-10`. La excepción acotada, y sus límites."""

    DATOS = {"nombre": "Colegio de Prueba", "email": "institucion@example.com"}

    def test_fija_la_contrasena_y_no_envia_correo(self):
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                **self.DATOS, contrasena_de_desarrollo="clave-de-desarrollo-2026"
            )

        self.assertTrue(institucion.usuario.check_password("clave-de-desarrollo-2026"))
        self.assertEqual(len(mail.outbox), 0, "DEC-10: no se envía invitación por este camino")

    def test_sin_el_argumento_el_comportamiento_no_cambia(self):
        """`HU-39` sigue siendo demostrable tal como está escrita."""
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(**self.DATOS)

        self.assertFalse(institucion.usuario.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)

    def test_restablece_la_clave_de_una_institucion_ya_sembrada(self):
        with self.captureOnCommitCallbacks(execute=True):
            dar_de_alta_la_institucion(**self.DATOS, contrasena_de_desarrollo="primera")
        mail.outbox.clear()

        with self.captureOnCommitCallbacks(execute=True):
            institucion, creada = dar_de_alta_la_institucion(
                **self.DATOS, contrasena_de_desarrollo="segunda"
            )

        self.assertFalse(creada)
        self.assertTrue(institucion.usuario.check_password("segunda"))
        self.assertEqual(len(mail.outbox), 0)

    def test_el_generador_no_repite_contrasenas(self):
        from personas.management.commands.sembrar import generar_contrasena

        claves = {generar_contrasena() for _ in range(200)}
        self.assertEqual(len(claves), 200)
        self.assertTrue(all(len(c) >= 24 for c in claves))


class DefinirContrasenaTest(TestCase):
    def setUp(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba", email="institucion@example.com"
            )
        self.usuario = self.institucion.usuario

    def _url(self, usuario=None, token=None):
        usuario = usuario or self.usuario
        return "/invitacion/{}/{}/".format(
            urlsafe_base64_encode(force_bytes(usuario.pk)),
            token or default_token_generator.make_token(usuario),
        )

    def test_el_titular_define_su_propia_contrasena(self):
        """Tercer criterio de `HU-39`."""
        # Django redirige a una URL con el token en sesión antes de mostrar el
        # formulario; se sigue la redirección.
        respuesta = self.client.get(self._url(), follow=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["validlink"])

        respuesta = self.client.post(
            respuesta.redirect_chain[-1][0] if respuesta.redirect_chain else self._url(),
            {"new_password1": "cafeteria-2026-upb", "new_password2": "cafeteria-2026-upb"},
            follow=True,
        )
        self.assertEqual(respuesta.status_code, 200)

        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.tiene_contrasena_definida)
        self.assertTrue(self.usuario.check_password("cafeteria-2026-upb"))

    def test_el_enlace_deja_de_servir_tras_usarlo(self):
        url = self._url()
        respuesta = self.client.get(url, follow=True)
        destino = respuesta.redirect_chain[-1][0]
        self.client.post(
            destino,
            {"new_password1": "cafeteria-2026-upb", "new_password2": "cafeteria-2026-upb"},
        )

        # El mismo enlace, otra vez: el token ya no vale.
        respuesta = self.client.get(url, follow=True)
        self.assertFalse(respuesta.context["validlink"])

    def test_un_token_inventado_no_sirve(self):
        respuesta = self.client.get(self._url(token="no-es-un-token"), follow=True)
        self.assertFalse(respuesta.context["validlink"])
