"""`HU-64`, `DEC-23`. El alta de un solo acudiente, sin la carga masiva.

Lo que se vigila, criterio a criterio:

1. **Solo la institución**, y por el servicio (`DT-15`).
2. **La cuenta nace como en la carga**: sin contraseña utilizable y con su
   invitación al confirmar (`INV-6`, `INVD-1`, `HU-03`), con el correo en
   minúsculas y las mismas longitudes (`personas.validacion`).
3. **Ni correo ni documento repetidos**, y un fallo no deja nada a medias ni
   envía nada.
4. **Nace sin estudiantes, y el padrón ya lo puede elegir**: que una familia
   nueva entre sin archivo es la razón de la historia.
"""

from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from personas.models import Acudiente
from personas.services import crear_acudiente, dar_de_alta_la_institucion

CLAVE = "clave-de-prueba-2026"


class BaseDeAlta(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo=CLAVE,
            )
        self.actor = institucion.usuario
        self.client.force_login(self.actor)
        mail.outbox.clear()

    def crear(self, **datos):
        base = {"nombre": "Marta Ruiz Ochoa", "documento": "43512345", "email": "marta@example.com"}
        base.update(datos)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse("alta-de-acudiente"), base)


class SoloLaInstitucionTest(BaseDeAlta):
    def test_ningun_otro_rol(self):
        for rol in [Rol.CAJERO, Rol.ADMINISTRADOR, Rol.ACUDIENTE]:
            with self.subTest(rol=rol):
                otro = crear_cuenta(email=f"{rol}@example.com", rol=rol, enviar_invitacion=False)
                self.client.force_login(otro)
                self.assertEqual(self.client.get(reverse("alta-de-acudiente")).status_code, 403)
                self.assertEqual(self.crear().status_code, 403)
        self.assertFalse(Acudiente.objects.exists())

    def test_el_servicio_tiene_su_puerta(self):
        cajero = crear_cuenta(email="caja@example.com", rol=Rol.CAJERO, enviar_invitacion=False)
        with self.assertRaises(PermissionDenied):
            crear_acudiente(actor=cajero, nombre="X", documento="12345", email="x@example.com")

    def test_sin_sesion_va_a_la_pantalla_de_acceso(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("alta-de-acudiente")).status_code, 302)


class LaCuentaNaceComoEnLaCargaTest(BaseDeAlta):
    def test_crea_acudiente_y_cuenta_sin_contrasena_e_invita(self):
        respuesta = self.crear(email="Marta@Example.com")

        acudiente = Acudiente.objects.get()
        self.assertEqual(acudiente.nombre, "Marta Ruiz Ochoa")
        self.assertEqual(acudiente.documento, "43512345")
        self.assertEqual(acudiente.usuario.email, "marta@example.com")  # en minúsculas
        self.assertEqual(acudiente.usuario.rol, Rol.ACUDIENTE)
        self.assertFalse(acudiente.usuario.has_usable_password())
        self.assertFalse(acudiente.usuario.is_staff)
        self.assertEqual([m.to for m in mail.outbox], [["marta@example.com"]])
        self.assertEqual(respuesta["HX-Trigger"], "acudientes-cambiado")
        self.assertIn("data-acudiente-creado", respuesta.content.decode())

    def test_el_formulario_no_pide_contrasena(self):
        cuerpo = self.client.get(reverse("alta-de-acudiente")).content.decode()
        self.assertIn("data-alta-de-acudiente", cuerpo)
        self.assertNotIn("<html", cuerpo)
        self.assertNotIn('type="password"', cuerpo)
        # Contraprueba: la búsqueda encuentra los campos que sí están.
        self.assertIn('type="email"', cuerpo)

    def test_las_longitudes_de_la_carga(self):
        for campo, valor in [("documento", "1234"), ("documento", "1" * 21), ("nombre", "x" * 201)]:
            with self.subTest(campo=campo, largo=len(valor)):
                respuesta = self.crear(**{campo: valor})
                self.assertIn("data-error-del-servidor", respuesta.content.decode())
        self.assertFalse(Acudiente.objects.exists())
        self.assertEqual(mail.outbox, [])

    def test_el_servicio_aplica_las_longitudes_aunque_el_formulario_no_estuviera(self):
        with self.assertRaises(ValidationError) as error:
            crear_acudiente(actor=self.actor, nombre="Ana", documento="12", email="ana@example.com")
        self.assertIn("documento", error.exception.message_dict)


class NadaRepetidoNiAMediasTest(BaseDeAlta):
    def setUp(self):
        super().setUp()
        self.crear()
        mail.outbox.clear()

    def test_un_correo_que_ya_es_una_cuenta(self):
        respuesta = self.crear(documento="99999999", email="MARTA@example.com")
        self.assertIn("Ya hay una cuenta con ese correo", respuesta.content.decode())
        self.assertEqual(Acudiente.objects.count(), 1)
        self.assertEqual(mail.outbox, [])

    def test_un_documento_que_ya_es_de_otro_acudiente(self):
        respuesta = self.crear(email="otra@example.com")
        self.assertIn("Ya hay un acudiente con ese documento", respuesta.content.decode())
        self.assertEqual(Acudiente.objects.count(), 1)
        self.assertFalse(Usuario.objects.filter(email="otra@example.com").exists())
        self.assertEqual(mail.outbox, [])


class NaceSinEstudiantesYElPadronLoEligeTest(BaseDeAlta):
    def test_sale_en_la_lista_y_no_como_retirado(self):
        self.crear()
        tabla = self.client.get(reverse("acudientes-tabla")).content.decode()
        self.assertIn("Marta Ruiz Ochoa", tabla)
        self.assertNotIn("data-acudiente-retirado", tabla)

    def test_el_alta_del_padron_lo_encuentra(self):
        self.crear()
        respuesta = self.client.get(
            reverse("acudientes-para-matricular"), {"buscar_acudiente": "Marta"}
        )
        self.assertEqual([a.nombre for a in respuesta.context["acudientes"]], ["Marta Ruiz Ochoa"])

    def test_la_pantalla_trae_el_boton(self):
        pagina = self.client.get(reverse("acudientes")).content.decode()
        self.assertIn(f'hx-get="{reverse("alta-de-acudiente")}"', pagina)
        self.assertIn("acudientes-cambiado from:body", pagina)
