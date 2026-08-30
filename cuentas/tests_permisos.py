"""`TT-15` y `TT-18`. La matriz `[S11]`, y el token de invitación.

La prueba que sostiene `INV-4` no es «el cajero no tiene tal permiso»: es
**«ningún rol tiene un permiso que la matriz no declare»**. Esa formulación
sobrevive a los modelos que aún no existen. Cuando en el Sprint 3 aparezca el
modelo de restricciones, si alguien concede escritura al cajero sin tocar la
matriz, esta prueba falla.
"""

from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.test import TestCase

from cuentas.models import Rol, Usuario
from cuentas.permisos import PERMISOS_POR_ROL, nombre_del_grupo
from cuentas.services import sincronizar_grupos_y_permisos


class MatrizDePermisosTest(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()

    def _permisos_de(self, rol):
        grupo = Group.objects.get(name=nombre_del_grupo(rol))
        return {
            f"{p.content_type.app_label}.{p.codename}" for p in grupo.permissions.all()
        }

    def _declarados(self, rol):
        esperados = set()
        for etiqueta, acciones in PERMISOS_POR_ROL[rol].items():
            app, modelo = etiqueta.split(".")
            for accion in acciones:
                esperados.add(f"{app}.{accion}_{modelo}")
        return esperados

    def test_existe_un_grupo_por_rol(self):
        for rol in Rol:
            self.assertTrue(
                Group.objects.filter(name=nombre_del_grupo(rol)).exists(),
                f"falta el grupo de {rol}",
            )

    def test_ningun_rol_tiene_permisos_de_mas(self):
        """`INV-4`, en la forma que sobrevive a los modelos futuros."""
        for rol in Rol:
            with self.subTest(rol=rol):
                self.assertEqual(
                    self._permisos_de(rol), self._declarados(rol),
                    f"Los permisos efectivos de «{rol}» no coinciden con la matriz "
                    "[S11]. Si el cambio es intencionado, actualiza cuentas/permisos.py; "
                    "conceder por fuera de la matriz rompe INV-4.",
                )

    def test_la_cafeteria_no_escribe_sobre_nada_todavia(self):
        """`INV-4` hoy: cajero y administrador no tienen NINGUNA escritura."""
        for rol in (Rol.CAJERO, Rol.ADMINISTRADOR):
            with self.subTest(rol=rol):
                escrituras = {
                    p for p in self._permisos_de(rol)
                    if any(a in p for a in ("add_", "change_", "delete_"))
                }
                self.assertEqual(escrituras, set())

    def test_solo_la_institucion_puede_crear_cuentas(self):
        """Primer criterio de `HU-40`, en la capa de datos."""
        for rol in Rol:
            with self.subTest(rol=rol):
                puede = "cuentas.add_usuario" in self._permisos_de(rol)
                self.assertEqual(puede, rol == Rol.INSTITUCION)

    def test_sincronizar_retira_lo_que_la_matriz_no_declara(self):
        """La poda. Sin ella, un permiso concedido a mano se queda para siempre."""
        from django.contrib.auth.models import Permission

        grupo = Group.objects.get(name=nombre_del_grupo(Rol.CAJERO))
        grupo.permissions.add(Permission.objects.get(codename="add_usuario"))
        self.assertIn("cuentas.add_usuario", self._permisos_de(Rol.CAJERO))

        sincronizar_grupos_y_permisos()
        self.assertNotIn("cuentas.add_usuario", self._permisos_de(Rol.CAJERO))

    def test_es_idempotente(self):
        antes = {rol: self._permisos_de(rol) for rol in Rol}
        sincronizar_grupos_y_permisos()
        sincronizar_grupos_y_permisos()
        self.assertEqual({rol: self._permisos_de(rol) for rol in Rol}, antes)


class TokenDeInvitacionTest(TestCase):
    """`TT-18`. Un solo uso y con caducidad."""

    def setUp(self):
        self.usuario = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO
        )

    def test_el_token_recien_hecho_vale(self):
        token = default_token_generator.make_token(self.usuario)
        self.assertTrue(default_token_generator.check_token(self.usuario, token))

    def test_definir_la_contrasena_invalida_el_token(self):
        """De un solo uso: el token se construye sobre el hash de la contraseña."""
        token = default_token_generator.make_token(self.usuario)
        self.usuario.set_password("cafeteria-2026-upb")
        self.usuario.save(update_fields=["password"])

        self.assertFalse(default_token_generator.check_token(self.usuario, token))

    def test_cambiar_el_correo_invalida_el_token(self):
        token = default_token_generator.make_token(self.usuario)
        self.usuario.email = "otro@example.com"
        self.usuario.save(update_fields=["email"])

        self.assertFalse(default_token_generator.check_token(self.usuario, token))

    def test_el_token_caduca(self):
        """Con caducidad. Se fabrica un token con fecha vieja."""
        class GeneradorConFecha(PasswordResetTokenGenerator):
            def __init__(self, cuando):
                super().__init__()
                self.cuando = cuando

            def _now(self):
                return self.cuando

        # Django compara con `datetime.now()` sin zona horaria: si se le pasa
        # una fecha con zona, revienta al restar.
        caducidad = timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
        viejo = GeneradorConFecha(datetime.now() - caducidad - timedelta(days=1))
        token = viejo.make_token(self.usuario)

        self.assertFalse(
            default_token_generator.check_token(self.usuario, token),
            "un token más viejo que PASSWORD_RESET_TIMEOUT debe estar caducado",
        )

    def test_la_caducidad_configurada_es_de_una_semana(self):
        self.assertEqual(settings.PASSWORD_RESET_TIMEOUT, 60 * 60 * 24 * 7)
