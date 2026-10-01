"""`HU-62`. Recuperación de la contraseña olvidada (`DEC-19`).

Los criterios, uno por uno:

  1. Desde la pantalla de acceso se pide el enlace escribiendo el correo.
  2. La respuesta es la misma exista o no una cuenta con ese correo.
  3. El enlace llega al correo del titular, es de un solo uso y caduca.
  4. Solo lo reciben las cuentas activas que ya definieron su contraseña.
  5. Con el enlace se elige la contraseña nueva y se entra con ella; la anterior
     deja de servir.

Casi todo lo decide Django —`PasswordResetForm` y `PasswordResetConfirmView`—, y
precisamente por eso hay prueba: lo que aquí se afirma es que **lo que Django
decide es lo que `DEC-19` pide**, y que una actualización que lo cambie se note.
"""

import re
from datetime import datetime, timedelta
from unittest import mock

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from cuentas.models import Rol, Usuario
from cuentas.services import (
    construir_enlace_de_recuperacion,
    desactivar_cuenta,
    sincronizar_grupos_y_permisos,
)
from personas.services import dar_de_alta_la_institucion

CLAVE_VIEJA = "la-de-siempre-2026"
CLAVE_NUEVA = "una-nueva-y-larga-2026"


class BaseDeRecuperacion(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        self.titular = Usuario.objects.crear_usuario(
            email="marta.ruiz@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
        )
        self.titular.set_password(CLAVE_VIEJA)
        self.titular.save(update_fields=["password"])
        mail.outbox.clear()

    def pedir(self, correo):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse("recuperar-contrasena"), {"email": correo})

    def enlace_del_correo(self):
        (correo,) = mail.outbox
        return re.search(r"https?://\S+/recuperar/\S+/", correo.body).group(0)

    def elegir(self, enlace, clave=CLAVE_NUEVA):
        ruta = re.sub(r"^https?://[^/]+", "", enlace)
        # `PasswordResetConfirmView` cambia el token de la URL por uno de sesión
        # y redirige: hay que seguir la redirección antes de enviar.
        respuesta = self.client.get(ruta, follow=True)
        return self.client.post(
            respuesta.request["PATH_INFO"],
            {"new_password1": clave, "new_password2": clave},
        )


class SePideDesdeLaPantallaDeAccesoTest(BaseDeRecuperacion):
    """Criterio 1."""

    def test_la_pantalla_de_acceso_enlaza_a_la_recuperacion(self):
        respuesta = self.client.get(reverse("acceso"))

        self.assertContains(respuesta, "data-enlace-recuperar")
        self.assertContains(respuesta, f'href="{reverse("recuperar-contrasena")}"')

    def test_la_pantalla_de_recuperacion_pide_el_correo(self):
        respuesta = self.client.get(reverse("recuperar-contrasena"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-formulario-de-recuperacion")
        self.assertIn("email", respuesta.context["form"].fields)

    def test_no_es_un_camino_de_alta(self):
        """`INV-6`, `INVD-1`: pedir un enlace para un correo sin cuenta no la crea."""
        self.pedir("nadie@example.com")

        self.assertFalse(Usuario.objects.filter(email="nadie@example.com").exists())


class LaRespuestaNoRevelaQuienTieneCuentaTest(BaseDeRecuperacion):
    """Criterio 2. Que un correo tenga cuenta es un dato de menores por
    asociación (`ALC-OUT-08`): quien lo tiene es acudiente de la institución."""

    def test_con_cuenta_y_sin_ella_se_llega_al_mismo_aviso(self):
        con_cuenta = self.pedir(self.titular.email)
        sin_cuenta = self.pedir("nadie@example.com")

        self.assertRedirects(con_cuenta, reverse("recuperacion-enviada"))
        self.assertRedirects(sin_cuenta, reverse("recuperacion-enviada"))

    def test_el_aviso_no_repite_el_correo(self):
        self.pedir(self.titular.email)
        respuesta = self.client.get(reverse("recuperacion-enviada"))

        self.assertContains(respuesta, "data-aviso-de-recuperacion")
        self.assertNotContains(respuesta, self.titular.email)

    def test_un_correo_mal_escrito_si_se_dice(self):
        """El único error que se pinta es el de forma, que no revela nada."""
        respuesta = self.pedir("esto-no-es-un-correo")

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["form"].errors)
        self.assertEqual(mail.outbox, [])


class ElEnlaceLlegaYEsDeUnSoloUsoTest(BaseDeRecuperacion):
    """Criterio 3."""

    def test_llega_un_correo_al_titular_con_el_enlace(self):
        self.pedir(self.titular.email)

        (correo,) = mail.outbox
        self.assertEqual(correo.to, [self.titular.email])
        self.assertIn("/recuperar/", correo.body)
        # Con su versión HTML, por la misma cáscara que la invitación.
        self.assertEqual(len(correo.alternatives), 1)

    def test_el_correo_no_distingue_mayusculas(self):
        self.pedir("MARTA.Ruiz@Example.com")

        self.assertEqual(len(mail.outbox), 1)

    def test_sale_al_confirmar_y_no_en_el_acto(self):
        """Va por `config/correo.py`, como la invitación: sin ejecutar los
        `on_commit`, la bandeja sigue vacía. Si alguien vuelve al `send_mail`
        de Django, que envía en el acto, esta prueba lo nota."""
        self.client.post(reverse("recuperar-contrasena"), {"email": self.titular.email})

        self.assertEqual(mail.outbox, [])

    def test_el_enlace_no_sirve_dos_veces(self):
        self.pedir(self.titular.email)
        enlace = self.enlace_del_correo()

        self.assertRedirects(self.elegir(enlace), reverse("contrasena-restablecida"))

        respuesta = self.client.get(re.sub(r"^https?://[^/]+", "", enlace), follow=True)
        self.assertContains(respuesta, "data-enlace-de-recuperacion-invalido")

    def test_el_enlace_caduca(self):
        """Pasada la caducidad (`PASSWORD_RESET_TIMEOUT`, siete días) no vale.

        Se adelanta el reloj del generador y no se pone la caducidad a cero:
        con cero, un token creado y comprobado en el mismo segundo sigue
        valiendo —Django compara con `>`— y la prueba no probaría nada."""
        enlace = construir_enlace_de_recuperacion(self.titular)
        ruta = re.sub(r"^https?://[^/]+", "", enlace)
        dentro_de_ocho_dias = datetime.now() + timedelta(days=8)

        with mock.patch.object(PasswordResetTokenGenerator, "_now", return_value=dentro_de_ocho_dias):
            respuesta = self.client.get(ruta, follow=True)

        self.assertContains(respuesta, "data-enlace-de-recuperacion-invalido")

    def test_contraprueba_antes_de_caducar_si_vale(self):
        enlace = construir_enlace_de_recuperacion(self.titular)
        ruta = re.sub(r"^https?://[^/]+", "", enlace)
        dentro_de_seis_dias = datetime.now() + timedelta(days=6)

        with mock.patch.object(PasswordResetTokenGenerator, "_now", return_value=dentro_de_seis_dias):
            respuesta = self.client.get(ruta, follow=True)

        self.assertNotContains(respuesta, "data-enlace-de-recuperacion-invalido")
        self.assertIn("form", respuesta.context)


class SoloCuentasActivasConContrasenaTest(BaseDeRecuperacion):
    """Criterio 4. La recuperación no es una segunda vía de activación."""

    def test_una_cuenta_sin_activar_no_recibe_nada(self):
        """La que todavía no usó su invitación sigue entrando por ella."""
        Usuario.objects.crear_usuario(email="sin.activar@example.com", rol=Rol.ACUDIENTE)

        respuesta = self.pedir("sin.activar@example.com")

        self.assertRedirects(respuesta, reverse("recuperacion-enviada"))
        self.assertEqual(mail.outbox, [])

    def test_una_cuenta_desactivada_no_recibe_nada(self):
        """`HU-42`: desactivada no opera, y tampoco se rehabilita por aquí."""
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo="clave-institucion-2026",
            )
        cajero = Usuario.objects.crear_usuario(email="cajero@example.com", rol=Rol.CAJERO)
        cajero.set_password(CLAVE_VIEJA)
        cajero.save(update_fields=["password"])
        desactivar_cuenta(actor=institucion.usuario, usuario=cajero)
        mail.outbox.clear()

        self.pedir(cajero.email)

        self.assertEqual(mail.outbox, [])

    def test_contraprueba_la_cuenta_activa_con_contrasena_si_recibe(self):
        """Sin esto, las dos de arriba pasarían también si nunca se enviara nada."""
        self.pedir(self.titular.email)

        self.assertEqual(len(mail.outbox), 1)


class SeEligeLaNuevaYLaViejaDejaDeServirTest(BaseDeRecuperacion):
    """Criterio 5."""

    def test_entra_con_la_nueva_y_no_con_la_vieja(self):
        self.pedir(self.titular.email)
        self.elegir(self.enlace_del_correo())

        self.titular.refresh_from_db()
        self.assertTrue(self.titular.check_password(CLAVE_NUEVA))
        self.assertFalse(self.titular.check_password(CLAVE_VIEJA))

        respuesta = self.client.post(
            reverse("acceso"), {"username": self.titular.email, "password": CLAVE_NUEVA}
        )
        self.assertRedirects(respuesta, reverse("panel"), target_status_code=302)

    def test_elegirla_no_abre_sesion_sola(self):
        """Se entra por `/login/` con la contraseña recién elegida."""
        self.pedir(self.titular.email)
        self.elegir(self.enlace_del_correo())

        self.assertNotIn("_auth_user_id", self.client.session)

    def test_un_enlace_de_recuperacion_no_vale_para_otra_cuenta(self):
        otra = Usuario.objects.crear_usuario(email="otra@example.com", rol=Rol.ACUDIENTE)
        otra.set_password(CLAVE_VIEJA)
        otra.save(update_fields=["password"])

        self.pedir(self.titular.email)
        token = self.enlace_del_correo().rstrip("/").rsplit("/", 1)[1]
        ajena = reverse(
            "restablecer-contrasena",
            kwargs={"uidb64": urlsafe_base64_encode(force_bytes(otra.pk)), "token": token},
        )

        respuesta = self.client.get(ajena, follow=True)
        self.assertContains(respuesta, "data-enlace-de-recuperacion-invalido")
