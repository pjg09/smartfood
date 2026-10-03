"""`TT-33` y `TT-34`. Administración de estudiantes por la institución (`HU-44`).

Los tres criterios de `HU-44`, probados en el servicio, que es donde vive la
regla. **La pantalla del admin que los llamaba se quitó**: lo que queda aquí de
ella es la prueba de que no ha vuelto.
"""

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from cuentas.permisos import PERMISOS_POR_ROL
from cuentas.services import sincronizar_grupos_y_permisos
from personas.codigo import LONGITUD
from personas.models import Acudiente, Estudiante
from personas.services import (
    CAMPOS_EDITABLES,
    crear_estudiante,
    dar_de_alta_la_institucion,
    editar_estudiante,
)

CLAVE = "clave-de-prueba-2026"


class BaseDeAdministracion(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo=CLAVE,
            )
        self.actor = institucion.usuario

        cuenta = Usuario.objects.crear_usuario(
            email="marta.ruiz@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz Ochoa"
        )
        self.acudiente = Acudiente.objects.create(
            usuario=cuenta, nombre="Marta Ruiz Ochoa", documento="43512345"
        )

        otra = Usuario.objects.crear_usuario(
            email="andres.ospina@example.com", rol=Rol.ACUDIENTE, nombre="Andrés Ospina"
        )
        self.otro_acudiente = Acudiente.objects.create(
            usuario=otra, nombre="Andrés Ospina Mesa", documento="71234567"
        )

    def matricular(self, documento="1001234501", nombre="Ana Sofía Restrepo Ruiz"):
        return crear_estudiante(
            actor=self.actor,
            nombre=nombre,
            documento=documento,
            acudiente=self.acudiente,
        )


# --- Primer criterio: matricular un estudiante individual -------------------


class AltaIndividualTest(BaseDeAdministracion):
    """«Permite matricular un estudiante individual, además de la carga masiva.»"""

    def test_el_servicio_matricula_y_asigna_el_codigo(self):
        estudiante = self.matricular()

        self.assertEqual(Estudiante.objects.count(), 1)
        self.assertEqual(estudiante.acudiente, self.acudiente)
        self.assertEqual(len(estudiante.codigo_tarjeta), LONGITUD)


# --- Segundo criterio: modificar los campos de uno ya cargado ---------------


class EdicionTest(BaseDeAdministracion):
    """«Permite modificar los campos de un estudiante ya cargado.»"""

    def test_el_servicio_cambia_los_campos_editables(self):
        estudiante = self.matricular()

        editar_estudiante(
            actor=self.actor,
            estudiante=estudiante,
            nombre="Ana Sofía Restrepo Mejía",
            acudiente=self.otro_acudiente,
        )

        estudiante.refresh_from_db()
        self.assertEqual(estudiante.nombre, "Ana Sofía Restrepo Mejía")
        self.assertEqual(estudiante.acudiente, self.otro_acudiente)

    def test_editar_no_toca_el_codigo_de_tarjeta(self):
        estudiante = self.matricular()
        codigo = estudiante.codigo_tarjeta

        editar_estudiante(actor=self.actor, estudiante=estudiante, nombre="Otro Nombre")

        estudiante.refresh_from_db()
        self.assertEqual(estudiante.codigo_tarjeta, codigo)

    def test_el_codigo_de_tarjeta_no_es_un_campo_editable(self):
        """Cambiarlo es reasignar la tarjeta, y eso es `HU-46` con `INVD-4`."""
        estudiante = self.matricular()

        with self.assertRaises(ValueError) as ctx:
            editar_estudiante(
                actor=self.actor,
                estudiante=estudiante,
                codigo_tarjeta="ZZZZZZZZZZZZZZ",
            )

        self.assertIn("HU-46", str(ctx.exception))
        self.assertNotIn("codigo_tarjeta", CAMPOS_EDITABLES)

    def test_un_campo_que_no_existe_es_un_error_explicito(self):
        estudiante = self.matricular()

        with self.assertRaises(ValueError):
            editar_estudiante(actor=self.actor, estudiante=estudiante, inventado="x")


# --- La pantalla del admin ya no existe ------------------------------------


class ElAdminDeEstudiantesNoExisteTest(BaseDeAdministracion):
    """Se quitó la ruta `/admin/personas/estudiante/` y sus seis vecinas.

    Una prueba de ausencia: pasa sola el día que deja de proteger, así que se
    afirma por las dos vías por las que el admin podría volver —el registro y la
    URL— y no solo por una.
    """

    def setUp(self):
        super().setUp()
        self.client.force_login(self.actor)

    def test_el_modelo_no_esta_registrado_en_el_admin(self):
        from django.contrib import admin

        self.assertFalse(admin.site.is_registered(Estudiante))

    def test_la_ruta_no_responde(self):
        estudiante = self.matricular()
        for ruta in [
            "/admin/personas/estudiante/",
            "/admin/personas/estudiante/add/",
            f"/admin/personas/estudiante/{estudiante.pk}/change/",
        ]:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 404)

    def test_el_indice_del_admin_no_la_ofrece(self):
        cuerpo = self.client.get(reverse("admin:index")).content.decode()
        self.assertNotIn("/admin/personas/estudiante/", cuerpo)


# --- Tercer criterio: función exclusiva de la institución -------------------


class SoloLaInstitucionAdministraTest(BaseDeAdministracion):
    """«Es una función exclusiva de la institución educativa.»"""

    def _cuenta(self, rol, email):
        usuario = Usuario.objects.crear_usuario(email=email, rol=rol, is_staff=True)
        usuario.set_password(CLAVE)
        usuario.save(update_fields=["password"])
        return usuario

    def test_el_servicio_rechaza_a_cualquier_otro_rol(self):
        for rol in [Rol.CAJERO, Rol.ADMINISTRADOR, Rol.ACUDIENTE]:
            with self.subTest(rol=rol):
                otro = self._cuenta(rol, f"{rol}@example.com")
                with self.assertRaises(PermissionDenied):
                    crear_estudiante(
                        actor=otro,
                        nombre="Ana Sofía Restrepo Ruiz",
                        documento="1001234501",
                        acudiente=self.acudiente,
                    )

    def test_el_servicio_rechaza_la_edicion_de_cualquier_otro_rol(self):
        estudiante = self.matricular()
        cajero = self._cuenta(Rol.CAJERO, "cajero@example.com")

        with self.assertRaises(PermissionDenied):
            editar_estudiante(actor=cajero, estudiante=estudiante, nombre="Cambiado")

    def test_una_cuenta_desactivada_no_administra(self):
        self.actor.is_active = False
        self.actor.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            self.matricular()

    def test_la_matriz_no_le_da_estudiantes_a_nadie_mas(self):
        for rol in Rol:
            with self.subTest(rol=rol):
                tiene = "personas.estudiante" in PERMISOS_POR_ROL[rol]
                self.assertEqual(tiene, rol == Rol.INSTITUCION)


# --- Lo que la vista NO permite hacer ---------------------------------------


class NoSeBorranEstudiantesTest(BaseDeAdministracion):
    """El estudiante que se va se da de baja, no se borra (`DT-12`, `HU-51`).

    Borrar la fila se llevaría por delante su billetera y sus compras, que es la
    trazabilidad que `OBJ-E2` pide. Las claves ajenas van con `PROTECT` por lo
    mismo.
    """

    def test_la_matriz_no_concede_el_permiso_de_borrado(self):
        self.assertNotIn(
            "delete", PERMISOS_POR_ROL[Rol.INSTITUCION]["personas.estudiante"]
        )


# --- `TT-35`. Lo que el recorrido de experiencia de usuario cambió ----------


class ElAcudienteEsSoloConsultaTest(BaseDeAdministracion):
    """`[S11]`. La cuenta del acudiente no se gestiona desde `personas`."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.actor)

    def test_se_puede_consultar(self):
        respuesta = self.client.get(reverse("admin:personas_acudiente_changelist"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Marta Ruiz Ochoa")

    def test_no_se_puede_crear(self):
        """Los acudientes nacen de la carga institucional (`HU-01`, `INV-6`)."""
        respuesta = self.client.get(reverse("admin:personas_acudiente_add"))
        self.assertEqual(respuesta.status_code, 403)

    def test_no_se_puede_editar_ni_borrar(self):
        self.assertNotIn("change", PERMISOS_POR_ROL[Rol.INSTITUCION]["personas.acudiente"])
        self.assertNotIn("delete", PERMISOS_POR_ROL[Rol.INSTITUCION]["personas.acudiente"])

        respuesta = self.client.get(
            reverse("admin:personas_acudiente_delete", args=[self.acudiente.pk])
        )
        self.assertEqual(respuesta.status_code, 403)
