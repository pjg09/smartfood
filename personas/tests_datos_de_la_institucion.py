"""`DEC-22`. La institución ya no edita sus datos en el admin.

No lo usaba nadie: su nombre lo pone el seed (`HU-39`). Se retiraron la entrada
del menú, el permiso y el registro en el admin; lo que se vigila es que no
vuelvan por ninguno de los tres sitios.
"""

from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from cuentas.services import sincronizar_grupos_y_permisos
from personas.models import Institucion
from personas.services import dar_de_alta_la_institucion

CLAVE = "clave-de-prueba-2026"


class LaInstitucionYaNoSeEditaEnElAdminTest(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            self.institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo=CLAVE,
            )
        self.actor = self.institucion.usuario
        self.client.force_login(self.actor)

    def test_el_admin_ya_no_la_registra(self):
        with self.assertRaises(NoReverseMatch):
            reverse("admin:personas_institucion_changelist")
        self.assertEqual(self.client.get("/admin/personas/institucion/").status_code, 404)
        # Contraprueba: el admin sigue respondiendo a esta cuenta en lo que sí es suyo.
        self.assertEqual(self.client.get("/admin/personas/acudiente/").status_code, 200)

    def test_ni_permiso_ni_entrada_en_el_menu(self):
        self.assertFalse(self.actor.has_perm("personas.change_institucion"))
        self.assertFalse(self.actor.has_perm("personas.view_institucion"))
        padron = self.client.get(reverse("padron")).content.decode()
        self.assertNotIn("/admin/personas/institucion/", padron)
        self.assertIn(f'href="{reverse("usuarios")}"', padron)

    def test_su_nombre_sigue_en_la_cabecera(self):
        """Lo que se retiró es editarlo, no enseñarlo."""
        self.assertIn(
            Institucion.objects.get().nombre,
            self.client.get(reverse("padron")).content.decode(),
        )
