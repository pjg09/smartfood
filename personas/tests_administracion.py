"""`TT-33` y `TT-34`. Administración de estudiantes por la institución (`HU-44`).

Los tres criterios de `HU-44`, y cada uno probado dos veces: en el servicio,
que es donde vive la regla, y a través del admin, que es la vista real por la
que la institución va a entrar (`INT-3`, `DT-2`).

**No es duplicar.** Que el servicio autorice bien no dice nada de si el admin lo
llama; y que el admin guarde no dice nada de si pasó por el servicio. La segunda
es la que importa aquí: un `ModelAdmin` guarda por su cuenta salvo que se le
diga lo contrario, y un estudiante guardado por su cuenta nace **sin código de
tarjeta**. `HU-43` se rompería en silencio y ninguna prueba de `PR-15` lo vería.
"""

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from cuentas.permisos import PERMISOS_POR_ROL
from cuentas.services import sincronizar_grupos_y_permisos
from personas.codigo import ALFABETO, LONGITUD
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

    def test_el_admin_matricula_pasando_por_el_servicio(self):
        """La prueba que impide que `HU-43` se rompa por la puerta de atrás.

        Si `save_model` no delegara, el estudiante se guardaría con
        `codigo_tarjeta` vacío y la base lo rechazaría —o peor, lo aceptaría si
        algún día alguien relaja la restricción—. Que salga con un código bien
        formado es la prueba de que pasó por `crear_estudiante`.
        """
        self.client.force_login(self.actor)

        respuesta = self.client.post(
            reverse("admin:personas_estudiante_add"),
            {
                "nombre": "Ana Sofía Restrepo Ruiz",
                "documento": "1001234501",
                "acudiente": str(self.acudiente.pk),
            },
        )
        self.assertEqual(respuesta.status_code, 302, "el alta debería redirigir al listado")

        estudiante = Estudiante.objects.get(documento="1001234501")
        self.assertEqual(len(estudiante.codigo_tarjeta), LONGITUD)
        self.assertTrue(set(estudiante.codigo_tarjeta) <= set(ALFABETO))

    def test_el_formulario_del_admin_no_ofrece_el_codigo_de_tarjeta(self):
        """Primer criterio de `HU-14`: lo genera el sistema, no una persona."""
        self.client.force_login(self.actor)

        cuerpo = self.client.get(reverse("admin:personas_estudiante_add")).content.decode()
        self.assertNotIn('name="codigo_tarjeta"', cuerpo)


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

    def test_el_admin_edita_pasando_por_el_servicio(self):
        estudiante = self.matricular()
        codigo = estudiante.codigo_tarjeta
        self.client.force_login(self.actor)

        respuesta = self.client.post(
            reverse("admin:personas_estudiante_change", args=[estudiante.pk]),
            {
                "nombre": "Ana Sofía Restrepo Mejía",
                "documento": "1001234501",
                "acudiente": str(self.otro_acudiente.pk),
            },
        )
        self.assertEqual(respuesta.status_code, 302)

        estudiante.refresh_from_db()
        self.assertEqual(estudiante.nombre, "Ana Sofía Restrepo Mejía")
        self.assertEqual(estudiante.acudiente, self.otro_acudiente)
        self.assertEqual(estudiante.codigo_tarjeta, codigo, "la edición no reasigna la tarjeta")


# --- Listado y búsqueda -----------------------------------------------------


class ListadoYBusquedaTest(BaseDeAdministracion):
    """`TT-34`: listado y búsqueda. Con un colegio, el listado sin filtro no sirve."""

    def setUp(self):
        super().setUp()
        self.matricular(documento="1001234501", nombre="Ana Sofía Restrepo Ruiz")
        self.matricular(documento="1001234502", nombre="Tomás Restrepo Ruiz")
        crear_estudiante(
            actor=self.actor,
            nombre="Julián Ospina Vélez",
            documento="1001234503",
            acudiente=self.otro_acudiente,
        )
        self.client.force_login(self.actor)

    def test_el_listado_muestra_a_todos(self):
        respuesta = self.client.get(reverse("admin:personas_estudiante_changelist"))

        self.assertEqual(respuesta.status_code, 200)
        for nombre in ["Ana Sofía", "Tomás", "Julián"]:
            self.assertContains(respuesta, nombre)

    def test_busca_por_nombre(self):
        respuesta = self.client.get(
            reverse("admin:personas_estudiante_changelist"), {"q": "Julián"}
        )
        self.assertContains(respuesta, "Julián Ospina Vélez")
        self.assertNotContains(respuesta, "Tomás Restrepo Ruiz")

    def test_busca_por_documento(self):
        respuesta = self.client.get(
            reverse("admin:personas_estudiante_changelist"), {"q": "1001234502"}
        )
        self.assertContains(respuesta, "Tomás Restrepo Ruiz")
        self.assertNotContains(respuesta, "Julián Ospina Vélez")

    def test_busca_por_el_acudiente(self):
        """El caso real: «los hijos de Marta», no «el estudiante 1001234501»."""
        respuesta = self.client.get(
            reverse("admin:personas_estudiante_changelist"), {"q": "Marta"}
        )
        self.assertContains(respuesta, "Ana Sofía Restrepo Ruiz")
        self.assertContains(respuesta, "Tomás Restrepo Ruiz")
        self.assertNotContains(respuesta, "Julián Ospina Vélez")


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

    def test_el_personal_no_alcanza_el_alta_desde_el_admin(self):
        """En la capa de datos, no escondiendo el botón (`DT-11`)."""
        cajero = self._cuenta(Rol.CAJERO, "cajero@example.com")
        self.client.force_login(cajero)

        respuesta = self.client.get(reverse("admin:personas_estudiante_add"))
        self.assertEqual(respuesta.status_code, 403)

    def test_ni_aunque_alguien_le_conceda_el_permiso_de_django(self):
        """La comprobación está en dos sitios a propósito.

        Un permiso se puede conceder por error desde el admin de grupos. El rol
        no: `[S11]` dice que administrar estudiantes es de `USR-5`.
        """
        cajero = self._cuenta(Rol.CAJERO, "cajero@example.com")
        cajero.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="personas",
                codename__in=["add_estudiante", "change_estudiante", "view_estudiante"],
            )
        )
        self.client.force_login(cajero)

        self.assertEqual(
            self.client.get(reverse("admin:personas_estudiante_add")).status_code, 403
        )

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

    def test_ni_la_institucion_puede_borrar_desde_el_admin(self):
        estudiante = self.matricular()
        self.client.force_login(self.actor)

        respuesta = self.client.get(
            reverse("admin:personas_estudiante_delete", args=[estudiante.pk])
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(Estudiante.objects.filter(pk=estudiante.pk).exists())

    def test_la_matriz_no_concede_el_permiso_de_borrado(self):
        self.assertNotIn(
            "delete", PERMISOS_POR_ROL[Rol.INSTITUCION]["personas.estudiante"]
        )


# --- `TT-35`. Lo que el recorrido de experiencia de usuario cambió ----------


class HallazgosDelRecorridoTest(BaseDeAdministracion):
    """Las tres correcciones que salieron de recorrer la vista de verdad.

    Están probadas porque un ajuste de interfaz sin prueba se deshace solo en el
    siguiente cambio, y entonces el recorrido de `TT-35` queda como un documento
    que describe algo que ya no es cierto.
    """

    def test_el_alta_no_muestra_campos_que_todavia_no_tienen_valor(self):
        """«Id» y «Creado en» salían vacíos en el formulario de matrícula."""
        self.client.force_login(self.actor)
        cuerpo = self.client.get(reverse("admin:personas_estudiante_add")).content.decode()

        self.assertNotIn("Creado en:", cuerpo)
        self.assertIn("Documento:", cuerpo)

    def test_la_ficha_de_un_estudiante_si_los_muestra(self):
        estudiante = self.matricular()
        self.client.force_login(self.actor)

        cuerpo = self.client.get(
            reverse("admin:personas_estudiante_change", args=[estudiante.pk])
        ).content.decode()
        self.assertIn("Creado en:", cuerpo)

    def test_el_alta_no_ofrece_quitar_una_fotografia_que_no_existe(self):
        """`UX-1`, que se aplicó a «Id» y «Creado en» y faltaba aquí."""
        self.client.force_login(self.actor)
        cuerpo = self.client.get(reverse("admin:personas_estudiante_add")).content.decode()

        self.assertNotIn("Quitar la fotografía actual", cuerpo)
        self.assertIn('name="fotografia"', cuerpo)

    def test_la_ficha_si_lo_ofrece(self):
        estudiante = self.matricular()
        self.client.force_login(self.actor)
        cuerpo = self.client.get(
            reverse("admin:personas_estudiante_change", args=[estudiante.pk])
        ).content.decode()

        self.assertIn("Quitar la fotografía actual", cuerpo)

    def test_el_acudiente_se_elige_buscando_y_no_de_una_lista_entera(self):
        """Con un colegio real, el `<select>` es una lista de cientos."""
        self.client.force_login(self.actor)
        cuerpo = self.client.get(reverse("admin:personas_estudiante_add")).content.decode()

        self.assertIn("admin-autocomplete", cuerpo)

        respuesta = self.client.get(
            reverse("admin:autocomplete"),
            {
                "app_label": "personas",
                "model_name": "estudiante",
                "field_name": "acudiente",
                "term": "Marta",
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Marta Ruiz Ochoa", respuesta.json()["results"][0]["text"])


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
