"""La institución tiene lo que la matriz declara, y nada más (`UX-6` de `TT-35`).

La cuenta institucional era **superusuario de Django**. El argumento era que es
el actor con más permisos del prototipo, y era cierto; el problema es lo que esa
bandera significa: un superusuario tiene **todos** los permisos por definición,
se declaren o no en `[S11]`.

Entre esos permisos estaba el de editar los grupos, y los grupos **son** la
matriz: es con ellos como `DT-11` sostiene `INV-4` —«las restricciones
alimentarias no las desactiva la cafetería»—. Quien edita un grupo puede
concederle al cajero la escritura sobre las restricciones el día que ese modelo
exista.

Dos puertas, no una. Quitar la bandera no habría servido de nada mientras el
formulario de usuario siguiera ofreciendo `is_superuser`, `groups` y
`user_permissions`: la institución se la habría devuelto con dos clics. Estas
pruebas cierran las dos, y la última clase comprueba lo que de verdad importa
después de cerrarlas — **que la institución sigue pudiendo hacer su trabajo**.
"""

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from cuentas.admin import UsuarioAdmin
from cuentas.models import Rol, Usuario
from cuentas.permisos import PERMISOS_POR_ROL, nombre_del_grupo
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from personas.services import dar_de_alta_la_institucion

CLAVE = "clave-de-prueba-2026"


class BaseInstitucional(TestCase):
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


class LaInstitucionNoEsSuperusuarioTest(BaseInstitucional):
    def test_la_cuenta_nace_sin_la_bandera(self):
        self.assertFalse(self.actor.is_superuser)

    def test_pero_sigue_entrando_al_admin(self):
        """`INT-3` es el admin (`DT-2`) y es por donde la institución opera."""
        self.assertTrue(self.actor.is_staff)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)

    def test_sus_permisos_son_exactamente_los_de_la_matriz(self):
        """Antes esta comprobación no significaba nada para `USR-5`.

        `test_ningun_rol_tiene_permisos_de_mas` compara los permisos del
        **grupo**. A un superusuario los permisos no le aplican, así que aquella
        prueba pasaba sobre un actor al que no vigilaba. Esta mira los permisos
        efectivos de la cuenta.
        """
        declarados = {
            f"{etiqueta.split('.')[0]}.{accion}_{etiqueta.split('.')[1]}"
            for etiqueta, acciones in PERMISOS_POR_ROL[Rol.INSTITUCION].items()
            for accion in acciones
        }
        self.assertEqual(self.actor.get_all_permissions(), declarados)

    def test_esta_en_el_grupo_de_su_rol(self):
        self.assertEqual(
            list(self.actor.groups.values_list("name", flat=True)),
            [nombre_del_grupo(Rol.INSTITUCION)],
        )


class NadieEditaLaMatrizDesdeLaPantallaTest(BaseInstitucional):
    """La puerta que `UX-6` encontró abierta."""

    def test_no_alcanza_el_admin_de_grupos(self):
        for ruta in ["admin:auth_group_changelist", "admin:auth_group_add"]:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(reverse(ruta)).status_code, 403)

    def test_los_grupos_no_aparecen_en_el_indice_del_admin(self):
        """Un modelo al que no se puede entrar tampoco se ofrece."""
        cuerpo = self.client.get(reverse("admin:index")).content.decode()

        self.assertNotIn("/admin/auth/group/", cuerpo)
        self.assertIn("/admin/personas/estudiante/", cuerpo)

    def test_no_alcanza_el_admin_de_permisos_sueltos(self):
        respuesta = self.client.get("/admin/auth/permission/")
        self.assertIn(respuesta.status_code, (403, 404))


class ElFormularioDeUsuarioNoConcedePrivilegiosTest(BaseInstitucional):
    """La segunda puerta: `is_superuser`, `groups` y `user_permissions`.

    Sin esto, quitar la bandera es cosmético: la institución se la devuelve
    editando su propia cuenta.
    """

    def setUp(self):
        super().setUp()
        # Por el servicio, para que quede en el grupo de su rol: es lo que estas
        # pruebas comprueban que sobrevive.
        self.cajero = crear_cuenta(
            email="cajero@example.com",
            rol=Rol.CAJERO,
            nombre="Cajero",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )

    def _ficha(self, usuario):
        return self.client.get(
            reverse("admin:cuentas_usuario_change", args=[usuario.pk])
        ).content.decode()

    def test_la_ficha_no_ofrece_los_campos_de_privilegio(self):
        cuerpo = self._ficha(self.cajero)

        for campo in ["is_superuser", "groups", "user_permissions", "rol", "is_staff"]:
            with self.subTest(campo=campo):
                self.assertNotIn(f'name="{campo}"', cuerpo)

    def test_pero_si_los_deja_ver(self):
        """Se ocultan del formulario, no de la vista: saber en qué grupo está
        una cuenta es parte de administrarla."""
        cuerpo = self._ficha(self.cajero)
        self.assertIn("rol:cajero", cuerpo)

    def test_un_intento_de_escalar_no_escala(self):
        """El caso que importa: mandar los campos aunque no estén en el formulario."""
        institucional = Group.objects.get(name=nombre_del_grupo(Rol.INSTITUCION))

        respuesta = self.client.post(
            reverse("admin:cuentas_usuario_change", args=[self.cajero.pk]),
            {
                "email": "cajero@example.com",
                "nombre": "Cajero",
                # Nada de esto está en el formulario. Se manda igual.
                "is_superuser": "on",
                "is_staff": "on",
                "rol": Rol.INSTITUCION,
                "groups": [str(institucional.pk)],
            },
        )
        self.assertEqual(respuesta.status_code, 302)

        self.cajero.refresh_from_db()
        self.assertFalse(self.cajero.is_superuser)
        self.assertEqual(self.cajero.rol, Rol.CAJERO)
        self.assertEqual(
            list(self.cajero.groups.values_list("name", flat=True)),
            [nombre_del_grupo(Rol.CAJERO)],
        )

    def test_la_institucion_no_se_devuelve_el_superusuario(self):
        self.client.post(
            reverse("admin:cuentas_usuario_change", args=[self.actor.pk]),
            {
                "email": self.actor.email,
                "nombre": self.actor.nombre,
                "is_superuser": "on",
            },
        )

        self.actor.refresh_from_db()
        self.assertFalse(self.actor.is_superuser)

    def test_la_institucion_no_se_deja_fuera_editando_la_casilla(self):
        """`HU-42` tiene un servicio con reglas, y una de ellas es esta.

        `desactivar_cuenta` se niega a que la institución se desactive a sí
        misma, porque después nadie podría reactivarla. La casilla del
        formulario no aplicaba esa regla.
        """
        self.client.post(
            reverse("admin:cuentas_usuario_change", args=[self.actor.pk]),
            {"email": self.actor.email, "nombre": self.actor.nombre},  # sin is_active
        )

        self.actor.refresh_from_db()
        self.assertTrue(self.actor.is_active, "la institución se quedó fuera del sistema")

    def test_el_alta_no_arrastra_los_campos_de_solo_lectura(self):
        """En el alta el formulario es `AltaDePersonalForm`: tres campos."""
        cuerpo = self.client.get(reverse("admin:cuentas_usuario_add")).content.decode()

        self.assertIn('name="email"', cuerpo)
        self.assertIn('name="rol"', cuerpo)
        self.assertNotIn('name="is_superuser"', cuerpo)
        self.assertNotIn("Creado en:", cuerpo)

    def test_la_lista_de_campos_bloqueados_esta_completa(self):
        """Si algún día aparece un campo de privilegio nuevo, que falle aquí."""
        del_modelo = {c.name for c in Usuario._meta.get_fields()}
        bloqueados = set(UsuarioAdmin.DERIVADOS_DEL_ROL) | set(
            UsuarioAdmin.CON_SERVICIO_PROPIO
        )

        privilegio = {"is_superuser", "groups", "user_permissions", "is_staff"}
        self.assertTrue(privilegio <= del_modelo)
        self.assertTrue(privilegio <= bloqueados)


class LaInstitucionSigueHaciendoSuTrabajoTest(BaseInstitucional):
    """Lo que de verdad hay que comprobar tras quitarle privilegios.

    Un candado que además cierra la puerta de casa no es una mejora. Estas son
    las cuatro cosas que `USR-5` hace hoy en el sistema.
    """

    def test_lista_y_da_de_alta_cuentas_de_personal(self):
        self.assertEqual(
            self.client.get(reverse("admin:cuentas_usuario_changelist")).status_code, 200
        )

        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(
                reverse("admin:cuentas_usuario_add"),
                {"email": "cajera@example.com", "nombre": "Cajera", "rol": Rol.CAJERO},
            )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Usuario.objects.filter(email="cajera@example.com").exists())

    def test_administra_estudiantes(self):
        self.assertEqual(
            self.client.get(reverse("admin:personas_estudiante_changelist")).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("admin:personas_estudiante_add")).status_code, 200
        )

    def test_consulta_acudientes(self):
        self.assertEqual(
            self.client.get(reverse("admin:personas_acudiente_changelist")).status_code,
            200,
        )

    def test_alcanza_la_pantalla_de_carga_masiva(self):
        self.assertEqual(
            self.client.get(reverse("carga-de-estudiantes")).status_code, 200
        )
