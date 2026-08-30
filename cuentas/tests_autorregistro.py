"""`TT-14`. Intento de autorregistro desde cada una de las tres interfaces.

`HU-05` dice que **no existe ningún camino de autorregistro en ninguna de las
tres interfaces**, y `INV-6` e `INVD-1` lo elevan a invariante: toda cuenta nace
de un alta hecha por otro actor más una invitación por correo.

Probar esto tiene una dificultad propia: **no se puede comprobar la ausencia de
algo probando las URL que se nos ocurran**. Por eso la prueba principal no
adivina rutas, sino que **recorre el mapa de URL completo del proyecto** y exige
que ninguna sea de registro. Así cubre también las interfaces que aún no
existen: cuando `INT-2` se construya en el Sprint 2, esta prueba ya la vigila.
"""

from django.contrib.auth.hashers import is_password_usable
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import get_resolver

from cuentas.models import Rol, Usuario

# Cómo se llamaría una ruta de registro si alguien la añadiera, en español o en
# inglés. La lista es deliberadamente amplia.
PALABRAS_DE_REGISTRO = [
    "registro", "registrar", "registrarse", "register", "signup", "sign-up",
    "sign_up", "crear-cuenta", "crear_cuenta", "nueva-cuenta", "alta-usuario",
    "join", "inscribir",
]


def _todas_las_rutas():
    def recorrer(resolver, prefijo=""):
        for patron in resolver.url_patterns:
            if hasattr(patron, "url_patterns"):
                yield from recorrer(patron, prefijo + str(patron.pattern))
            else:
                yield prefijo + str(patron.pattern)

    return sorted(set(recorrer(get_resolver())))


class NoHayCaminoDeAutorregistroTest(TestCase):
    """`INV-6`, `INVD-1`. Cubre `INT-1`, `INT-2` e `INT-3`."""

    def test_ninguna_ruta_del_proyecto_es_de_registro(self):
        """La prueba que de verdad importa: no adivina, inspecciona el mapa."""
        rutas = _todas_las_rutas()
        self.assertGreater(len(rutas), 0, "el mapa de URL no puede estar vacío")

        culpables = [
            ruta for ruta in rutas
            if any(palabra in ruta.lower() for palabra in PALABRAS_DE_REGISTRO)
        ]
        self.assertEqual(
            culpables, [],
            f"Aparecieron rutas que parecen de autorregistro: {culpables}. "
            "INV-6 e INVD-1 lo prohíben: las rutas de registro no existen (DT-10).",
        )

    def test_int_1_el_acudiente_no_puede_registrarse(self):
        """Interfaz del acudiente, web adaptable a móvil."""
        for ruta in ["/registro/", "/registrarse/", "/signup/", "/crear-cuenta/"]:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 404)
                self.assertEqual(
                    self.client.post(ruta, {"email": "cuela@example.com"}).status_code, 404
                )

    def test_int_2_el_punto_de_venta_no_puede_registrar_cuentas(self):
        """Punto de venta. Todavía no existe (Sprint 2), y ya está vigilado."""
        for ruta in ["/pos/registro/", "/venta/registro/", "/caja/crear-cuenta/"]:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 404)

    def test_int_3_nadie_se_da_de_alta_a_si_mismo(self):
        """`INT-3` es el admin de Django (`DT-2`).

        Desde `TT-17` el alta de cuentas **sí existe** aquí, pero eso no es
        autorregistro: la hace la institución educativa sobre otra persona, y
        pasa por `cuentas.services` para que dispare la invitación (`HU-40`).
        Autorregistrarse sería crear la cuenta propia, y para eso hay que estar
        dentro; para estar dentro hace falta una cuenta.

        Lo que esta prueba fija es que **nadie del personal** —aun teniendo
        acceso a la administración— puede dar de alta cuentas.
        """
        cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, is_staff=True,
        )
        cajero.set_password("clave-de-prueba-2026")
        cajero.save(update_fields=["password"])
        self.client.force_login(cajero)

        respuesta = self.client.get("/admin/cuentas/usuario/add/")
        self.assertEqual(
            respuesta.status_code, 403,
            "solo la institución educativa da de alta cuentas (HU-40, [S11])",
        )

    def test_un_anonimo_no_alcanza_el_admin(self):
        respuesta = self.client.get("/admin/cuentas/usuario/add/")
        self.assertIn(respuesta.status_code, (302, 403))


class LaCuentaNaceSinContrasenaUtilizableTest(TestCase):
    """`TT-13`. La segunda mitad de `HU-05`, en todos los caminos de escritura."""

    def test_el_manager_no_deja_contrasena_utilizable(self):
        usuario = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO
        )
        self.assertFalse(usuario.has_usable_password())
        self.assertFalse(usuario.tiene_contrasena_definida)

    def test_la_base_rechaza_una_contrasena_vacia(self):
        """El agujero que cierra `TT-13`.

        Un `Usuario` construido sin pasar por el manager queda con `password=""`,
        y Django considera **usable** una contraseña vacía. Esa cuenta reportaría
        tener contraseña definida y nunca podría ser invitada de nuevo.

        Lo impide la base y no un `if` (`DT-15`): un `if` cubre el camino que hoy
        conocemos; la restricción cubre los que aún no existen.
        """
        self.assertTrue(
            is_password_usable(""),
            "si Django dejara de considerar usable la cadena vacía, esta "
            "restricción se podría revisar",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Usuario.objects.create(email="colado@example.com", rol=Rol.CAJERO)

    def test_ninguna_cuenta_existente_tiene_la_contrasena_vacia(self):
        self.assertFalse(Usuario.objects.filter(password="").exists())
