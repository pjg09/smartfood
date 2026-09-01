"""`TT-16` y `TT-17`. Alta de cuentas de personal (`HU-40`, `HU-41`)."""

from django.core import mail
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from cuentas.models import Rol, Usuario
from cuentas.services import (
    crear_cuenta_de_personal,
    sincronizar_grupos_y_permisos,
)
from personas.services import dar_de_alta_la_institucion


class AltaDePersonalTest(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            self.institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo="clave-de-prueba-2026",
            )
        self.actor = self.institucion.usuario
        mail.outbox.clear()

    def test_la_institucion_da_de_alta_a_un_cajero(self):
        with self.captureOnCommitCallbacks(execute=True):
            cajero = crear_cuenta_de_personal(
                actor=self.actor, email="cajero@example.com", rol=Rol.CAJERO
            )

        self.assertEqual(cajero.rol, Rol.CAJERO)
        self.assertTrue(cajero.is_staff, "el personal opera desde INT-3")
        self.assertEqual(len(mail.outbox), 1, "el alta dispara la invitación (HU-41)")
        self.assertIn("/invitacion/", mail.outbox[0].body)

    def test_quien_crea_la_cuenta_no_conoce_la_clave(self):
        """Tercer criterio de `HU-41`. La invariante del mecanismo entero."""
        with self.captureOnCommitCallbacks(execute=True):
            cajero = crear_cuenta_de_personal(
                actor=self.actor, email="cajero@example.com", rol=Rol.CAJERO
            )

        self.assertFalse(cajero.has_usable_password())
        # Y no hay ninguna contraseña en el correo que se envió.
        self.assertNotIn("contraseña:", mail.outbox[0].body.lower())

    def test_la_cuenta_queda_en_el_grupo_de_su_rol(self):
        with self.captureOnCommitCallbacks(execute=True):
            admin = crear_cuenta_de_personal(
                actor=self.actor, email="admin@example.com", rol=Rol.ADMINISTRADOR
            )

        self.assertEqual(
            [g.name for g in admin.groups.all()], ["rol:administrador"]
        )
        # `INV-4`: escribe su catálogo (`HU-26`) y nada más. Exigir cero escrituras
        # sería una foto del momento y no la invariante.
        escrituras = {p for p in admin.get_all_permissions()
                      if any(a in p for a in ("add_", "change_", "delete_"))}
        self.assertTrue(escrituras, "el catálogo es suyo")
        self.assertEqual(
            {p for p in escrituras if not p.startswith("catalogo.")}, set()
        )

    def test_solo_la_institucion_puede_dar_de_alta(self):
        """Primer criterio de `HU-40`."""
        for rol in (Rol.CAJERO, Rol.ADMINISTRADOR, Rol.ACUDIENTE):
            with self.subTest(rol=rol):
                impostor = Usuario.objects.crear_usuario(
                    email=f"{rol}@example.com", rol=rol
                )
                with self.assertRaises(PermissionDenied):
                    crear_cuenta_de_personal(
                        actor=impostor, email="cuela@example.com", rol=Rol.CAJERO
                    )

    def test_un_anonimo_no_puede_dar_de_alta(self):
        with self.assertRaises(PermissionDenied):
            crear_cuenta_de_personal(
                actor=None, email="cuela@example.com", rol=Rol.CAJERO
            )

    def test_una_institucion_desactivada_no_opera(self):
        """`HU-42`: una cuenta desactivada no puede operar."""
        self.actor.is_active = False
        self.actor.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            crear_cuenta_de_personal(
                actor=self.actor, email="cajero@example.com", rol=Rol.CAJERO
            )

    def test_no_se_dan_de_alta_acudientes_por_esta_via(self):
        """Las de acudiente nacen de la carga institucional (`HU-01`, `HU-03`)."""
        with self.assertRaises(ValueError):
            crear_cuenta_de_personal(
                actor=self.actor, email="acudiente@example.com", rol=Rol.ACUDIENTE
            )

    def test_no_se_dan_de_alta_instituciones_por_esta_via(self):
        with self.assertRaises(ValueError):
            crear_cuenta_de_personal(
                actor=self.actor, email="otra@example.com", rol=Rol.INSTITUCION
            )

    def test_nada_se_escribe_si_el_alta_falla(self):
        antes = Usuario.objects.count()
        with self.assertRaises(ValueError):
            crear_cuenta_de_personal(
                actor=self.actor, email="acudiente@example.com", rol=Rol.ACUDIENTE
            )
        self.assertEqual(Usuario.objects.count(), antes)
        self.assertEqual(len(mail.outbox), 0)


class VistaDeCuentasDePersonalTest(TestCase):
    """`TT-17`. El admin, que también es una vista y no escribe por su cuenta."""

    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo="clave-de-prueba-2026",
            )
        self.actor = institucion.usuario
        mail.outbox.clear()

    def test_la_institucion_ve_el_alta_de_cuentas(self):
        self.client.force_login(self.actor)
        self.assertEqual(self.client.get("/admin/cuentas/usuario/add/").status_code, 200)

    def test_el_personal_no_ve_el_alta_de_cuentas(self):
        """`HU-40`: solo la institución. Ni siquiera con `is_staff`."""
        cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, is_staff=True
        )
        cajero.set_password("clave-de-prueba-2026")
        cajero.save(update_fields=["password"])

        self.client.force_login(cajero)
        respuesta = self.client.get("/admin/cuentas/usuario/add/")
        self.assertEqual(respuesta.status_code, 403)

    def test_el_formulario_no_ofrece_contrasena(self):
        self.client.force_login(self.actor)
        contenido = self.client.get("/admin/cuentas/usuario/add/").content.decode()
        self.assertNotIn('name="password"', contenido)

    def test_el_formulario_solo_ofrece_roles_de_personal(self):
        self.client.force_login(self.actor)
        contenido = self.client.get("/admin/cuentas/usuario/add/").content.decode()
        self.assertIn('value="cajero"', contenido)
        self.assertIn('value="administrador"', contenido)
        self.assertNotIn('value="acudiente"', contenido)
        self.assertNotIn('value="institucion"', contenido)

    def test_dar_de_alta_desde_el_admin_dispara_la_invitacion(self):
        self.client.force_login(self.actor)
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(
                "/admin/cuentas/usuario/add/",
                {"email": "cajero@example.com", "nombre": "Cajero de Prueba", "rol": "cajero"},
            )

        self.assertEqual(respuesta.status_code, 302)
        cajero = Usuario.objects.get(email="cajero@example.com")
        self.assertFalse(cajero.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)
