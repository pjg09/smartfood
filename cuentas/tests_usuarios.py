"""`DT-45`. `/usuarios/`: el personal de la cafetería, con la composición del padrón.

Sustituye, para la institución, al listado de usuarios del admin. Lo que se vigila:

1. **Solo la institución**, y la regla en el selector (`DT-11`).
2. **Solo personal**: ni acudientes ni la propia institución.
3. **El alta dispara la invitación y nadie conoce la contraseña** (`HU-40`, `HU-41`),
   y solo crea cajeros o administradores.
4. **Desactivar, reactivar y reenviar** pasan por sus servicios (`HU-41`, `HU-42`),
   y una cuenta que no es de personal no se alcanza.
"""

from django.core import mail
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from cuentas.services import (
    crear_cuenta,
    reenviar_invitacion_de_personal,
    sincronizar_grupos_y_permisos,
)
from personas.services import dar_de_alta_la_institucion

CLAVE = "clave-de-prueba-2026"


class BaseDeUsuarios(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo=CLAVE,
            )
        self.actor = institucion.usuario
        self.cajero = self.cuenta("cajero@example.com", Rol.CAJERO, "Luis Cajero", activa=True)
        self.admin_cafeteria = self.cuenta(
            "admin@example.com", Rol.ADMINISTRADOR, "Rosa Administración", activa=False
        )
        self.acudiente = self.cuenta("marta@example.com", Rol.ACUDIENTE, "Marta Ruiz", activa=True)
        self.client.force_login(self.actor)

    def cuenta(self, email, rol, nombre, activa):
        usuario = crear_cuenta(
            email=email, rol=rol, nombre=nombre, enviar_invitacion=False,
            accede_a_administracion=(rol == Rol.ADMINISTRADOR),
        )
        if activa:
            usuario.set_password(CLAVE)
            usuario.save(update_fields=["password"])
        return usuario

    def tabla(self, **parametros):
        return self.client.get(reverse("usuarios-tabla"), parametros)

    def crear(self, **datos):
        base = {"email": "nuevo@example.com", "nombre": "Ana Nueva", "rol": Rol.CAJERO}
        base.update(datos)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse("alta-de-personal"), base)


class SoloLaInstitucionTest(BaseDeUsuarios):
    def test_la_institucion_entra(self):
        self.assertEqual(self.client.get(reverse("usuarios")).status_code, 200)

    def test_ningun_otro_rol(self):
        for usuario in [self.cajero, self.admin_cafeteria, self.acudiente]:
            with self.subTest(rol=usuario.rol):
                self.client.force_login(usuario)
                for ruta in ["usuarios", "usuarios-tabla", "alta-de-personal"]:
                    self.assertEqual(self.client.get(reverse(ruta)).status_code, 403)

    def test_sin_sesion_va_a_la_pantalla_de_acceso(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("usuarios")).status_code, 302)

    def test_otro_rol_no_crea_ni_desactiva(self):
        self.admin_cafeteria.is_active = True
        self.admin_cafeteria.save(update_fields=["is_active"])
        self.client.force_login(self.admin_cafeteria)

        alta = self.crear()
        baja = self.client.post(reverse("desactivacion-de-personal", args=[self.cajero.pk]))

        self.assertEqual(alta.status_code, 403)
        self.assertEqual(baja.status_code, 403)
        self.assertFalse(Usuario.objects.filter(email="nuevo@example.com").exists())
        self.cajero.refresh_from_db()
        self.assertTrue(self.cajero.is_active)

    def test_ningun_otro_rol_reactiva_ni_reenvia(self):
        self.admin_cafeteria.is_active = False
        self.admin_cafeteria.save(update_fields=["is_active"])
        for usuario in [self.cajero, self.acudiente]:
            for ruta in ["reactivacion-de-personal", "invitacion-de-personal"]:
                with self.subTest(rol=usuario.rol, ruta=ruta):
                    self.client.force_login(usuario)
                    respuesta = self.client.post(reverse(ruta, args=[self.admin_cafeteria.pk]))
                    self.assertEqual(respuesta.status_code, 403)
        self.admin_cafeteria.refresh_from_db()
        self.assertFalse(self.admin_cafeteria.is_active)

    def test_esta_en_su_menu_en_lugar_del_admin(self):
        pagina = self.client.get(reverse("padron")).content.decode()
        self.assertIn(f'href="{reverse("usuarios")}"', pagina)
        self.assertNotIn(reverse("admin:cuentas_usuario_changelist"), pagina)


class SoloElPersonalTest(BaseDeUsuarios):
    def test_ni_acudientes_ni_la_institucion(self):
        respuesta = self.tabla()
        self.assertEqual(
            set(respuesta.context["personal"]), {self.cajero, self.admin_cafeteria}
        )
        cuerpo = respuesta.content.decode()
        self.assertNotIn("marta@example.com", cuerpo)
        self.assertNotIn("institucion@example.com", cuerpo)
        # Contraprueba: los correos del personal sí están.
        self.assertIn("cajero@example.com", cuerpo)

    def test_las_desactivadas_salen_con_su_estado(self):
        self.admin_cafeteria.is_active = False
        self.admin_cafeteria.save(update_fields=["is_active"])
        cuerpo = self.tabla().content.decode()
        # Dos: la tabla de escritorio y la ficha de móvil.
        self.assertEqual(cuerpo.count("data-usuario-desactivado\n"), 2)

    def test_la_busqueda_cruza_nombre_y_correo_y_el_total_no_depende_de_ella(self):
        for termino in ["rosa", "admin@"]:
            with self.subTest(termino=termino):
                respuesta = self.tabla(busqueda=termino)
                self.assertEqual(list(respuesta.context["personal"]), [self.admin_cafeteria])
                self.assertEqual(respuesta.context["total"], 2)

    def test_la_pagina_es_una_pagina_y_la_tabla_un_fragmento(self):
        pagina = self.client.get(reverse("usuarios"))
        self.assertTemplateUsed(pagina, "base-aplicacion.html")
        self.assertIn("data-modal-ficha", pagina.content.decode())
        self.assertNotIn("<html", self.tabla().content.decode())


class ElAltaTest(BaseDeUsuarios):
    def test_el_formulario_es_un_fragmento_sin_contrasena(self):
        cuerpo = self.client.get(reverse("alta-de-personal")).content.decode()
        self.assertIn("data-alta-de-personal", cuerpo)
        self.assertNotIn("<html", cuerpo)
        self.assertNotIn('type="password"', cuerpo)
        # Contraprueba: la búsqueda encuentra los campos que sí están.
        self.assertIn('type="email"', cuerpo)

    def test_crea_la_cuenta_e_invita(self):
        respuesta = self.crear(rol=Rol.ADMINISTRADOR)

        nuevo = Usuario.objects.get(email="nuevo@example.com")
        self.assertEqual(nuevo.rol, Rol.ADMINISTRADOR)
        self.assertEqual(nuevo.nombre, "Ana Nueva")
        self.assertFalse(nuevo.has_usable_password())
        self.assertEqual([m.to for m in mail.outbox], [["nuevo@example.com"]])
        self.assertEqual(respuesta["HX-Trigger"], "personal-cambiado")
        self.assertIn("data-usuario-creado", respuesta.content.decode())

    def test_el_cajero_no_entra_al_admin_y_la_administracion_si(self):
        """Lo decide el servicio (`crear_cuenta_de_personal`), no la pantalla."""
        self.crear(email="caja@example.com", rol=Rol.CAJERO)
        self.crear(email="adm@example.com", rol=Rol.ADMINISTRADOR)
        self.assertFalse(Usuario.objects.get(email="caja@example.com").is_staff)
        self.assertTrue(Usuario.objects.get(email="adm@example.com").is_staff)

    def test_solo_roles_de_personal(self):
        for rol in [Rol.ACUDIENTE, Rol.INSTITUCION]:
            with self.subTest(rol=rol):
                respuesta = self.crear(rol=rol)
                self.assertEqual(respuesta.status_code, 200)
                self.assertFalse(Usuario.objects.filter(email="nuevo@example.com").exists())
        self.assertEqual(mail.outbox, [])

    def test_un_correo_repetido_sin_distinguir_mayusculas(self):
        respuesta = self.crear(email="CAJERO@example.com")
        self.assertIn("data-error-del-servidor", respuesta.content.decode())
        self.assertEqual(Usuario.objects.filter(email__iexact="cajero@example.com").count(), 1)
        self.assertEqual(mail.outbox, [])

    def test_sin_nombre_no_se_crea(self):
        self.crear(nombre="")
        self.assertFalse(Usuario.objects.filter(email="nuevo@example.com").exists())


class LasAccionesDeCadaFilaTest(BaseDeUsuarios):
    def test_desactivar_y_reactivar(self):
        url = reverse("desactivacion-de-personal", args=[self.cajero.pk])
        respuesta = self.client.post(url, {"busqueda": "luis"})
        self.cajero.refresh_from_db()
        self.assertFalse(self.cajero.is_active)
        self.assertIn("data-usuario-desactivado-aviso", respuesta.content.decode())
        # La búsqueda que había puesta se conserva.
        self.assertEqual(respuesta.context["busqueda"], "luis")

        self.client.post(reverse("reactivacion-de-personal", args=[self.cajero.pk]))
        self.cajero.refresh_from_db()
        self.assertTrue(self.cajero.is_active)

    def test_reenviar_la_invitacion(self):
        self.admin_cafeteria.is_active = True
        self.admin_cafeteria.save(update_fields=["is_active"])
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(
                reverse("invitacion-de-personal", args=[self.admin_cafeteria.pk])
            )
        self.assertEqual([m.to for m in mail.outbox], [["admin@example.com"]])
        self.assertIn("data-invitacion-reenviada", respuesta.content.decode())

    def test_a_quien_ya_tiene_contrasena_se_le_niega_con_motivo(self):
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(reverse("invitacion-de-personal", args=[self.cajero.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("data-error-de-usuarios", respuesta.content.decode())
        self.assertEqual(mail.outbox, [])

    def test_ni_un_acudiente_ni_la_institucion_se_alcanzan(self):
        for usuario in [self.acudiente, self.actor]:
            for ruta in ["desactivacion-de-personal", "invitacion-de-personal"]:
                with self.subTest(usuario=usuario.rol, ruta=ruta):
                    respuesta = self.client.post(reverse(ruta, args=[usuario.pk]))
                    self.assertEqual(respuesta.status_code, 404)
        self.acudiente.refresh_from_db()
        self.actor.refresh_from_db()
        self.assertTrue(self.acudiente.is_active)
        self.assertTrue(self.actor.is_active)

    def test_solo_se_escribe_por_post(self):
        url = reverse("desactivacion-de-personal", args=[self.cajero.pk])
        self.assertEqual(self.client.get(url).status_code, 405)


class ElReenvioTienePuertaTest(BaseDeUsuarios):
    """`reenviar_invitacion` no recibía actor; el de `/usuarios/` sí (`DT-15`)."""

    def test_solo_la_institucion(self):
        with self.assertRaises(PermissionDenied):
            reenviar_invitacion_de_personal(actor=self.cajero, usuario=self.admin_cafeteria)

    def test_solo_sobre_personal(self):
        acudiente_sin_activar = self.cuenta(
            "jorge@example.com", Rol.ACUDIENTE, "Jorge", activa=False
        )
        with self.assertRaises(ValueError):
            reenviar_invitacion_de_personal(actor=self.actor, usuario=acudiente_sin_activar)

