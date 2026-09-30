"""`DEC-17`. La consulta de restricciones con el sistema visual (`HU-38`).

Sustituye al proxy del admin de `TT-112`. Lo que se fija:

1. **Quién entra**: la institución y la administración de la cafetería, que es
   lo que `[S11]` concede. La regla vive en el selector, no en la vista.
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
    def test_la_institucion_y_la_cafeteria_sí(self):
        for rol in (Rol.INSTITUCION, Rol.ADMINISTRADOR):
            with self.subTest(rol=rol):
                self.assertEqual(
                    list(estudiantes_con_sus_restricciones(actor=cuenta(rol))), []
                )

    def test_el_acudiente_no_entra_por_esta_puerta(self):
        """Las consulta en `INT-1`, sobre los suyos, no en la lista del colegio."""
        with self.assertRaises(PermissionDenied):
            estudiantes_con_sus_restricciones(actor=cuenta(Rol.ACUDIENTE))


class LaPantallaDeRestriccionesTest(TestCase):
    def setUp(self):
        self.actor = cuenta(Rol.INSTITUCION)
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
