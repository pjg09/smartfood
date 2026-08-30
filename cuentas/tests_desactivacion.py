"""`TT-19` y `TT-20`. Desactivación y reactivación de cuentas (`HU-42`).

Los tres criterios de `HU-42` son afirmaciones distintas y aquí se prueban por
separado. La segunda —«ni operar»— es la que suele darse por supuesta: que
alguien no pueda **iniciar** sesión no dice nada de la sesión que ya tenía
abierta cuando lo desactivaron.
"""

from django.core.exceptions import PermissionDenied
from django.test import TestCase

from cuentas.models import Rol, Usuario
from cuentas.services import (
    desactivar_cuenta,
    reactivar_cuenta,
    sincronizar_grupos_y_permisos,
)
from personas.services import dar_de_alta_la_institucion


class DesactivacionDeCuentasTest(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo="clave-de-prueba-2026",
            )
        self.actor = institucion.usuario

        self.cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, is_staff=True
        )
        self.cajero.set_password("clave-del-cajero-2026")
        self.cajero.save(update_fields=["password"])

    # --- Primer criterio: no puede iniciar sesión ni operar ----------------

    def test_una_cuenta_desactivada_no_inicia_sesion(self):
        desactivar_cuenta(actor=self.actor, usuario=self.cajero)

        entro = self.client.login(
            username="cajero@example.com", password="clave-del-cajero-2026"
        )
        self.assertFalse(entro)

    def test_una_cuenta_desactivada_no_opera_con_la_sesion_ya_abierta(self):
        """«Ni operar» no es lo mismo que «ni iniciar sesión».

        Un cajero al que desactivan a media jornada tiene la sesión abierta. Si
        el sistema solo comprobara el acceso al entrar, seguiría cobrando hasta
        cerrar el navegador. Django resuelve la sesión a través del mismo
        backend que rechaza a los inactivos, así que deja de identificarlo en la
        siguiente petición — pero eso hay que comprobarlo, no suponerlo.
        """
        self.assertTrue(
            self.client.login(
                username="cajero@example.com", password="clave-del-cajero-2026"
            )
        )
        self.assertEqual(self.client.get("/admin/").status_code, 200)

        desactivar_cuenta(actor=self.actor, usuario=self.cajero)

        respuesta = self.client.get("/admin/")
        self.assertEqual(
            respuesta.status_code, 302,
            "la sesión abierta debe dejar de servir en cuanto se desactiva la cuenta",
        )

    # --- Segundo criterio: la institución puede reactivarla ----------------

    def test_la_institucion_reactiva_la_cuenta(self):
        desactivar_cuenta(actor=self.actor, usuario=self.cajero)
        reactivar_cuenta(actor=self.actor, usuario=self.cajero)

        self.cajero.refresh_from_db()
        self.assertTrue(self.cajero.is_active)
        self.assertTrue(
            self.client.login(
                username="cajero@example.com", password="clave-del-cajero-2026"
            )
        )

    def test_reactivar_no_pide_definir_la_contrasena_de_nuevo(self):
        """La contraseña sobrevive: la baja es lógica, no un borrado."""
        desactivar_cuenta(actor=self.actor, usuario=self.cajero)
        reactivar_cuenta(actor=self.actor, usuario=self.cajero)

        self.cajero.refresh_from_db()
        self.assertTrue(self.cajero.check_password("clave-del-cajero-2026"))

    # --- Tercer criterio: el historial se conserva -------------------------

    def test_desactivar_conserva_la_cuenta_y_sus_datos(self):
        creado_en = self.cajero.creado_en
        desactivar_cuenta(actor=self.actor, usuario=self.cajero)

        self.cajero.refresh_from_db()
        self.assertEqual(Usuario.objects.filter(pk=self.cajero.pk).count(), 1)
        self.assertEqual(self.cajero.email, "cajero@example.com")
        self.assertEqual(self.cajero.creado_en, creado_en)

    def test_el_admin_no_ofrece_borrar_cuentas(self):
        """Si se pudiera borrar, el historial de `HU-42` no se conservaría."""
        self.client.force_login(self.actor)
        respuesta = self.client.get(f"/admin/cuentas/usuario/{self.cajero.pk}/delete/")
        self.assertEqual(respuesta.status_code, 403)

    # --- Quién puede, y sobre quién ---------------------------------------

    def test_solo_la_institucion_desactiva(self):
        otro = Usuario.objects.crear_usuario(
            email="otro-cajero@example.com", rol=Rol.CAJERO
        )
        with self.assertRaises(PermissionDenied):
            desactivar_cuenta(actor=self.cajero, usuario=otro)

    def test_una_institucion_desactivada_no_desactiva_a_nadie(self):
        self.actor.is_active = False
        self.actor.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            desactivar_cuenta(actor=self.actor, usuario=self.cajero)

    def test_la_institucion_no_puede_desactivarse_a_si_misma(self):
        """Nadie podría reactivarla: el sistema quedaría sin quien lo administre."""
        with self.assertRaises((PermissionDenied, ValueError)):
            desactivar_cuenta(actor=self.actor, usuario=self.actor)

        self.actor.refresh_from_db()
        self.assertTrue(self.actor.is_active)

    def test_no_se_desactivan_acudientes_por_esta_via(self):
        """`HU-42` cubre al personal. La baja del estudiante es `HU-51`."""
        acudiente = Usuario.objects.crear_usuario(
            email="acudiente@example.com", rol=Rol.ACUDIENTE
        )
        with self.assertRaises(ValueError):
            desactivar_cuenta(actor=self.actor, usuario=acudiente)

    # --- TT-20: las acciones desde la vista de cuentas --------------------

    def test_la_accion_del_admin_desactiva(self):
        self.client.force_login(self.actor)
        respuesta = self.client.post(
            "/admin/cuentas/usuario/",
            {"action": "accion_desactivar", "_selected_action": [str(self.cajero.pk)]},
            follow=True,
        )

        self.assertEqual(respuesta.status_code, 200)
        self.cajero.refresh_from_db()
        self.assertFalse(self.cajero.is_active)

    def test_la_accion_del_admin_reactiva(self):
        desactivar_cuenta(actor=self.actor, usuario=self.cajero)

        self.client.force_login(self.actor)
        self.client.post(
            "/admin/cuentas/usuario/",
            {"action": "accion_reactivar", "_selected_action": [str(self.cajero.pk)]},
            follow=True,
        )

        self.cajero.refresh_from_db()
        self.assertTrue(self.cajero.is_active)

    def test_la_accion_del_admin_rechaza_lo_que_el_servicio_rechaza(self):
        """La vista no decide: delega. Si el servicio dice que no, es que no."""
        acudiente = Usuario.objects.crear_usuario(
            email="acudiente@example.com", rol=Rol.ACUDIENTE
        )
        self.client.force_login(self.actor)
        respuesta = self.client.post(
            "/admin/cuentas/usuario/",
            {"action": "accion_desactivar", "_selected_action": [str(acudiente.pk)]},
            follow=True,
        )

        acudiente.refresh_from_db()
        self.assertTrue(acudiente.is_active, "un acudiente no se desactiva por esta vía")
        self.assertContains(respuesta, "no es personal de la cafetería")

    def test_desactivar_dos_veces_no_falla(self):
        desactivar_cuenta(actor=self.actor, usuario=self.cajero)
        desactivar_cuenta(actor=self.actor, usuario=self.cajero)

        self.cajero.refresh_from_db()
        self.assertFalse(self.cajero.is_active)
