"""`DEC-17`. La lista de acudientes con el sistema visual de la institución.

Sustituye a `/admin/personas/acudiente/`, que era la misma información dentro
de otra interfaz. Lo que se fija aquí:

1. **Quién entra.** `[S11]` da `view` sobre `personas.acudiente` solo a la
   institución, y la regla vive en el selector (`DT-11`), no en la vista.
2. **Que no escriba nada.** La matriz no le concede ni `add` ni `change`: una
   acción en esta pantalla sería prometer algo que la capa de datos rechaza.
3. **Que el buscador devuelva un fragmento y la página, una página** (`DT-16`).
"""

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from personas.selectors import acudientes_de_la_institucion, acudientes_sin_activar

CLAVE = "clave-de-prueba-2026"


def cuenta(rol, email=None):
    sincronizar_grupos_y_permisos()
    usuario = crear_cuenta(
        email=email or f"{rol}-acu@example.com",
        rol=rol,
        nombre=f"Cuenta {rol}",
        accede_a_administracion=rol in (Rol.INSTITUCION, Rol.ADMINISTRADOR),
        enviar_invitacion=False,
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
    return usuario


def acudiente(nombre="Marta Ruiz", documento="43000001", activa=True):
    usuario = crear_cuenta(
        email=f"{documento}@example.com",
        rol=Rol.ACUDIENTE,
        nombre=nombre,
        enviar_invitacion=False,
    )
    if activa:
        usuario.set_password(CLAVE)
        usuario.save(update_fields=["password"])
    return Acudiente.objects.create(usuario=usuario, nombre=nombre, documento=documento)


class SoloLaInstitucionVeLosAcudientesTest(TestCase):
    def test_los_otros_tres_roles_reciben_403(self):
        for rol in (Rol.CAJERO, Rol.ADMINISTRADOR, Rol.ACUDIENTE):
            with self.subTest(rol=rol):
                usuario = cuenta(rol, email=f"{rol}-x@example.com")

                with self.assertRaises(PermissionDenied):
                    acudientes_de_la_institucion(actor=usuario)

    def test_un_anonimo_tampoco(self):
        from django.contrib.auth.models import AnonymousUser

        with self.assertRaises(PermissionDenied):
            acudientes_de_la_institucion(actor=AnonymousUser())

    def test_la_institucion_los_ve(self):
        acudiente()

        self.assertEqual(
            len(list(acudientes_de_la_institucion(actor=cuenta(Rol.INSTITUCION)))), 1
        )


class LaListaDeAcudientesTest(TestCase):
    def setUp(self):
        self.actor = cuenta(Rol.INSTITUCION)
        self.marta = acudiente()
        self.sin_activar = acudiente("Jorge Ospina", "43000002", activa=False)
        self.client.force_login(self.actor)

    def test_cuenta_los_estudiantes_a_cargo_en_una_sola_consulta(self):
        for i in range(2):
            Estudiante.objects.create(
                nombre=f"Hijo {i}",
                documento=f"10000{i}",
                acudiente=self.marta,
                # La forma del código la impone la base (`INV-7`, `DT-9`): un
                # valor inventado revienta el `INSERT`, no una validación.
                codigo_tarjeta=generar_codigo_de_tarjeta(),
            )

        por_nombre = {a.nombre: a for a in acudientes_de_la_institucion(actor=self.actor)}

        self.assertEqual(por_nombre["Marta Ruiz"].cuantos, 2)
        self.assertEqual(por_nombre["Jorge Ospina"].cuantos, 0)

    def test_avisa_de_los_que_no_han_activado_su_cuenta(self):
        """Es el dato por el que secretaría abre esta pantalla (`DEC-9`)."""
        acudientes = list(acudientes_de_la_institucion(actor=self.actor))

        self.assertEqual(acudientes_sin_activar(acudientes), 1)

    def test_la_busqueda_cruza_nombre_documento_y_correo(self):
        for termino, esperado in [
            ("marta", "Marta Ruiz"),
            ("43000002", "Jorge Ospina"),
            ("43000001@example.com", "Marta Ruiz"),
        ]:
            with self.subTest(termino=termino):
                encontrados = list(
                    acudientes_de_la_institucion(actor=self.actor, busqueda=termino)
                )

                self.assertEqual([a.nombre for a in encontrados], [esperado])

    def test_la_pagina_es_una_pagina_y_la_tabla_un_fragmento(self):
        """`DT-16`: dos rutas, no un endpoint que a veces devuelve una cosa."""
        pagina = self.client.get(reverse("acudientes"))
        fragmento = self.client.get(reverse("acudientes-tabla"))

        self.assertTemplateUsed(pagina, "personas/acudientes.html")
        self.assertTemplateUsed(pagina, "base-aplicacion.html")
        self.assertTemplateUsed(fragmento, "personas/partials/acudientes-tabla.html")
        self.assertNotContains(fragmento, "<!doctype html>")

    def test_la_tabla_no_ofrece_ninguna_accion_que_escriba(self):
        """`[S11]` solo concede `view`, y la pantalla lo dice igual que la matriz.

        **Sobre el fragmento y no sobre la página**: la página trae el
        formulario de cerrar sesión de la barra, que no es una acción de esta
        pantalla y haría pasar la prueba por el motivo equivocado.

        Y sobre las URL, no sobre la copia: un `assertNotContains` de «Editar»
        se rompería en cuanto alguien mejore una frase.
        """
        tabla = self.client.get(reverse("acudientes-tabla")).content.decode()

        self.assertNotIn("/change/", tabla)
        self.assertNotIn("/add/", tabla)
        self.assertNotIn("<form", tabla)
        self.assertIn("data-fila-de-acudiente", tabla)
