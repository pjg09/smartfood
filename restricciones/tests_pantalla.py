"""`DEC-17`. La consulta de restricciones con el sistema visual (`HU-38`).

Sustituye al proxy del admin de `TT-112`. Lo que se fija:

1. **Quién entra**: la administración de la cafetería. La institución también
   consulta restricciones (`[S11]`, `HU-38`), pero en la ficha del padrón: esta
   pantalla no le servía y se le quitó (`DEC-21`). La regla vive en el
   selector, no en la vista ni en el menú.
2. **Que no escriba nada.** `INV-4` es explícito: las restricciones son del
   acudiente y la cafetería no las desactiva. Una acción aquí sería la
   invariante rota en la interfaz.
3. **Que el buscador no ofrezca el documento del menor.** El admin buscaba por
   documento exacto; esta pantalla la abre también la cafetería.
"""

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from restricciones.selectors import estudiantes_con_sus_restricciones

CLAVE = "clave-de-prueba-2026"


def cuenta(rol):
    sincronizar_grupos_y_permisos()
    usuario = crear_cuenta(
        email=f"{rol}-restr@example.com",
        rol=rol,
        nombre=f"Cuenta {rol}",
        accede_a_administracion=rol in (Rol.INSTITUCION, Rol.ADMINISTRADOR),
        enviar_invitacion=False,
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
    return usuario


def estudiante(nombre="Ana Ruiz", documento="1000000001"):
    titular = crear_cuenta(
        email=f"acu-{documento}@example.com",
        rol=Rol.ACUDIENTE,
        nombre="Acudiente",
        enviar_invitacion=False,
    )
    # El documento del acudiente es único: se deriva del del estudiante entero,
    # no de sus seis primeras cifras, que dos estudiantes comparten.
    acudiente = Acudiente.objects.create(
        usuario=titular, nombre="Acudiente", documento=f"43{documento}"
    )
    return Estudiante.objects.create(
        nombre=nombre,
        documento=documento,
        acudiente=acudiente,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )


class QuienConsultaLasRestriccionesTest(TestCase):
    def test_la_cafeteria_sí(self):
        self.assertEqual(
            list(estudiantes_con_sus_restricciones(actor=cuenta(Rol.ADMINISTRADOR))), []
        )

    def test_la_institucion_no_entra_por_esta_puerta(self):
        """`DEC-21`. Las consulta en la ficha de cada estudiante, desde el padrón."""
        with self.assertRaises(PermissionDenied):
            estudiantes_con_sus_restricciones(actor=cuenta(Rol.INSTITUCION))

    def test_el_acudiente_no_entra_por_esta_puerta(self):
        """Las consulta en `INT-1`, sobre los suyos, no en la lista del colegio."""
        with self.assertRaises(PermissionDenied):
            estudiantes_con_sus_restricciones(actor=cuenta(Rol.ACUDIENTE))


class LaPantallaDeRestriccionesTest(TestCase):
    def setUp(self):
        self.actor = cuenta(Rol.ADMINISTRADOR)
        self.ana = estudiante()
        self.client.force_login(self.actor)

    def test_la_pagina_es_una_pagina_y_la_tabla_un_fragmento(self):
        pagina = self.client.get(reverse("restricciones-de-estudiantes"))
        fragmento = self.client.get(reverse("restricciones-tabla"))

        self.assertTemplateUsed(pagina, "restricciones/restricciones.html")
        self.assertTemplateUsed(pagina, "base-aplicacion.html")
        self.assertTemplateUsed(
            fragmento, "restricciones/partials/restricciones-tabla.html"
        )
        self.assertNotContains(fragmento, "<!doctype html>")

    def test_la_tabla_no_ofrece_ninguna_accion(self):
        """`INV-4` dicho en la interfaz. Sobre el fragmento, no sobre la página."""
        tabla = self.client.get(reverse("restricciones-tabla")).content.decode()

        self.assertNotIn("<form", tabla)
        self.assertNotIn("/change/", tabla)
        self.assertIn("data-fila-de-restricciones", tabla)

    def test_la_tabla_no_enseña_el_documento_del_menor(self):
        """Esta pantalla la abre también la cafetería (`[S11]`)."""
        tabla = self.client.get(reverse("restricciones-tabla")).content.decode()

        self.assertIn(self.ana.nombre, tabla)
        self.assertNotIn(self.ana.documento, tabla)

    def test_la_busqueda_filtra_por_nombre(self):
        estudiante(nombre="Otro Estudiante", documento="1000000002")

        tabla = self.client.get(
            reverse("restricciones-tabla"), {"busqueda": "Ana"}
        ).content.decode()

        self.assertIn("Ana Ruiz", tabla)
        self.assertNotIn("Otro Estudiante", tabla)


class LaInstitucionYaNoTieneEstaPantallaTest(TestCase):
    """`DEC-21`. Ni en el menú ni por la URL, y la consulta sigue en el padrón."""

    def setUp(self):
        self.institucion = cuenta(Rol.INSTITUCION)
        self.ana = estudiante()

    def test_la_url_responde_403(self):
        self.client.force_login(self.institucion)
        for ruta in ["restricciones-de-estudiantes", "restricciones-tabla"]:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(reverse(ruta)).status_code, 403)

    def test_contraprueba_la_cafeteria_si_entra(self):
        self.client.force_login(cuenta(Rol.ADMINISTRADOR))
        self.assertEqual(self.client.get(reverse("restricciones-de-estudiantes")).status_code, 200)

    def test_no_esta_en_su_menu(self):
        self.client.force_login(self.institucion)
        padron = self.client.get(reverse("padron")).content.decode()
        self.assertNotIn(f'href="{reverse("restricciones-de-estudiantes")}"', padron)
        # Contraprueba: la búsqueda encuentra una entrada del menú que sí está.
        self.assertIn(f'href="{reverse("acudientes")}"', padron)

    def test_sigue_consultandolas_en_la_ficha_del_padron(self):
        """`HU-38` para la institución, por su otro camino (`DT-43`)."""
        self.client.force_login(self.institucion)
        ficha = self.client.get(reverse("consulta-del-estudiante", args=[self.ana.pk]))
        self.assertEqual(ficha.status_code, 200)
        self.assertIn("data-consulta-restricciones", ficha.content.decode())
