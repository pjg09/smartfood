"""`HU-63`, `DEC-20`. La institución corta y devuelve el acceso de un acudiente.

Los criterios de la historia, sobre el servicio, que es donde vive la regla
(`DT-15`). La ficha del padrón, que es por donde se llega, tiene las suyas en
`personas/tests_ficha.py`.

**Y lo que no debe cambiar**: la puerta de `HU-42` sigue siendo solo del
personal. Que esta exista no puede ensanchar aquella sin que nadie lo decida.
"""

from django.core import mail
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from cuentas.services import (
    desactivar_acudiente,
    desactivar_cuenta,
    reactivar_acudiente,
    sincronizar_grupos_y_permisos,
)
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from personas.services import comprobar_que_puede_operar, dar_de_alta_la_institucion

CLAVE = "clave-del-acudiente-2026"


class BaseDeAcceso(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo="clave-institucion-2026",
            )
        self.actor = institucion.usuario

        self.usuario = Usuario.objects.crear_usuario(
            email="marta.ruiz@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
        )
        self.usuario.set_password(CLAVE)
        self.usuario.save(update_fields=["password"])
        self.acudiente = Acudiente.objects.create(
            usuario=self.usuario, nombre="Marta Ruiz Ochoa", documento="43512345"
        )
        self.estudiante = Estudiante.objects.create(
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001234501",
            acudiente=self.acudiente,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        mail.outbox.clear()

    def entra(self):
        return self.client.login(username=self.usuario.email, password=CLAVE)


# --- Primer criterio: ni entra, ni opera, ni recupera la contraseña ---------


class UnaCuentaDesactivadaNoEntraTest(BaseDeAcceso):
    def test_no_inicia_sesion(self):
        desactivar_acudiente(actor=self.actor, usuario=self.usuario)
        self.assertFalse(self.entra())

    def test_contraprueba_activa_si_entra(self):
        """Sin esto, la anterior pasaría también con una contraseña mal puesta."""
        self.assertTrue(self.entra())

    def test_la_sesion_ya_abierta_deja_de_operar(self):
        self.assertTrue(self.entra())
        panel = reverse("mis-estudiantes")
        self.assertEqual(self.client.get(panel).status_code, 200)

        desactivar_acudiente(actor=self.actor, usuario=self.usuario)

        self.assertEqual(self.client.get(panel).status_code, 302)

    def test_no_recupera_la_contrasena(self):
        """`DEC-19`: las cuentas inactivas no reciben el enlace."""
        desactivar_acudiente(actor=self.actor, usuario=self.usuario)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("recuperar-contrasena"), {"email": self.usuario.email})
        self.assertEqual(mail.outbox, [])

    def test_contraprueba_activa_si_recupera(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("recuperar-contrasena"), {"email": self.usuario.email})
        self.assertEqual(len(mail.outbox), 1)


# --- Segundo criterio: la institución la reactiva, y nadie más toca nada ----


class LaInstitucionLaReactivaTest(BaseDeAcceso):
    def test_reactivar_le_devuelve_el_acceso_con_su_contrasena(self):
        desactivar_acudiente(actor=self.actor, usuario=self.usuario)
        reactivar_acudiente(actor=self.actor, usuario=self.usuario)
        self.assertTrue(self.entra())

    def test_las_dos_son_idempotentes(self):
        desactivar_acudiente(actor=self.actor, usuario=self.usuario)
        desactivar_acudiente(actor=self.actor, usuario=self.usuario)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_active)

        reactivar_acudiente(actor=self.actor, usuario=self.usuario)
        reactivar_acudiente(actor=self.actor, usuario=self.usuario)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.is_active)

    def test_ningun_otro_rol_desactiva_ni_reactiva(self):
        otros = [self.usuario] + [
            Usuario.objects.crear_usuario(email=f"{rol}@example.com", rol=rol)
            for rol in (Rol.CAJERO, Rol.ADMINISTRADOR)
        ]
        for actor in otros:
            for servicio in (desactivar_acudiente, reactivar_acudiente):
                with self.subTest(actor=actor.rol, servicio=servicio.__name__):
                    with self.assertRaises(PermissionDenied):
                        servicio(actor=actor, usuario=self.usuario)

        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.is_active)

    def test_ni_una_institucion_desactivada(self):
        self.actor.is_active = False
        self.actor.save(update_fields=["is_active"])
        with self.assertRaises(PermissionDenied):
            desactivar_acudiente(actor=self.actor, usuario=self.usuario)

    def test_el_acudiente_no_se_reactiva_a_si_mismo(self):
        desactivar_acudiente(actor=self.actor, usuario=self.usuario)
        with self.assertRaises(PermissionDenied):
            reactivar_acudiente(actor=self.usuario, usuario=self.usuario)


class LasDosPuertasNoSeMezclanTest(BaseDeAcceso):
    """Una puerta por historia: `HU-42` para el personal, `HU-63` para acudientes."""

    def test_esta_no_corta_al_personal(self):
        cajero = Usuario.objects.crear_usuario(email="cajero@example.com", rol=Rol.CAJERO)
        with self.assertRaises(ValueError):
            desactivar_acudiente(actor=self.actor, usuario=cajero)
        cajero.refresh_from_db()
        self.assertTrue(cajero.is_active)

    def test_ni_a_la_institucion(self):
        with self.assertRaises(ValueError):
            desactivar_acudiente(actor=self.actor, usuario=self.actor)
        self.actor.refresh_from_db()
        self.assertTrue(self.actor.is_active)

    def test_la_de_hu_42_sigue_sin_cortar_acudientes(self):
        with self.assertRaises(ValueError):
            desactivar_cuenta(actor=self.actor, usuario=self.usuario)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.is_active)


# --- Tercer criterio: sus estudiantes siguen, y nada se borra --------------


class SeCortaLaCuentaNoLosEstudiantesTest(BaseDeAcceso):
    def test_el_estudiante_sigue_pudiendo_comprar(self):
        desactivar_acudiente(actor=self.actor, usuario=self.usuario)
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.puede_operar)
        comprobar_que_puede_operar(self.estudiante)

    def test_no_se_borra_nada(self):
        desactivar_acudiente(actor=self.actor, usuario=self.usuario)
        self.assertTrue(Usuario.objects.filter(pk=self.usuario.pk).exists())
        self.assertTrue(Acudiente.objects.filter(pk=self.acudiente.pk).exists())
        self.assertTrue(Estudiante.objects.filter(pk=self.estudiante.pk).exists())
