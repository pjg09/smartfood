"""`TT-28` y `TT-29`. El acudiente entra y ve a los suyos (`HU-03`, `HU-04`).

Dos historias contiguas y del mismo asunto. Los criterios que se ejercitan aquí,
uno por uno:

`HU-03` — Invitación por correo y definición de contraseña
  1. El sistema genera la invitación **automáticamente** tras la carga.
  2. Se **genera** una invitación por cada acudiente cargado; su entrega por
     correo queda fuera del prototipo (`DEC-9`).
  3. El acudiente define su propia contraseña con esa invitación, y la que
     genera la carga **es utilizable**: se demuestra de extremo a extremo.

`HU-04` — Acudiente con varios estudiantes a cargo
  1. Una cuenta de acudiente puede tener varios estudiantes vinculados.
  2. El saldo, el límite diario y las restricciones son **por estudiante**, no
     por acudiente.
"""

import re

from django.core import mail
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from cuentas.services import generar_invitacion, sincronizar_grupos_y_permisos
from personas.models import Acudiente, Estudiante
from personas.selectors import estudiante_a_cargo, estudiantes_a_cargo
from personas.services import cargar_estudiantes_y_acudientes, dar_de_alta_la_institucion

ENCABEZADO = (
    "documento_estudiante,nombre_estudiante,"
    "documento_acudiente,nombre_acudiente,correo_acudiente\n"
)

# Marta tiene dos hijos matriculados y aparece en dos filas: es el caso de
# `HU-04` (`ALC-IN-04`). Andrés tiene uno.
ARCHIVO = ENCABEZADO + (
    "1001234501,Ana Sofía Restrepo Ruiz,43512345,Marta Ruiz Ochoa,marta.ruiz@example.com\n"
    "1001234502,Tomás Restrepo Ruiz,43512345,Marta Ruiz Ochoa,marta.ruiz@example.com\n"
    "1001234503,Julián Ospina Vélez,71234567,Andrés Ospina Mesa,andres.ospina@example.com\n"
)

CLAVE_DE_LA_INSTITUCION = "clave-de-prueba-2026"
CLAVE_DEL_ACUDIENTE = "la-que-eligio-marta-2026"


def archivo(contenido=ARCHIVO, nombre="estudiantes.csv"):
    return SimpleUploadedFile(nombre, contenido.encode("utf-8"), content_type="text/csv")


class BaseDeCarga(TestCase):
    """Una institución sembrada y el archivo de arriba ya cargado."""

    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo=CLAVE_DE_LA_INSTITUCION,
            )
        self.institucion = institucion.usuario

    def cargar(self, contenido=ARCHIVO, **extra):
        with self.captureOnCommitCallbacks(execute=True):
            return cargar_estudiantes_y_acudientes(
                actor=self.institucion, archivo=archivo(contenido), **extra
            )


# --- `HU-03` ---------------------------------------------------------------


class LaCargaGeneraUnaInvitacionPorAcudienteTest(BaseDeCarga):
    """`TT-28`. Primer y segundo criterio de `HU-03`, con `DEC-9`."""

    def test_se_genera_una_invitacion_por_cada_acudiente_cargado(self):
        """Dos acudientes en tres filas: dos invitaciones, no tres."""
        resultado = self.cargar()

        self.assertEqual(resultado.acudientes_creados, 2)
        self.assertEqual(resultado.invitaciones_generadas, 2)

    def test_la_generacion_es_automatica_al_completarse_la_carga(self):
        """Primer criterio: nadie tiene que pedirlas después, una a una."""
        resultado = self.cargar()

        self.assertEqual(
            resultado.invitaciones_generadas,
            Acudiente.objects.count(),
            "toda cuenta de acudiente creada por la carga sale de ella invitable",
        )

    def test_no_se_entrega_ningun_correo(self):
        """`DEC-9`: se genera, no se entrega.

        Las direcciones cargadas son ficticias (`ALC-OUT-07`) y cada rebote
        degrada la reputación del remitente hasta perder la cuenta de correo.
        """
        mail.outbox.clear()
        self.cargar()
        self.assertEqual(mail.outbox, [])

    def test_un_acudiente_reutilizado_no_recibe_otra_invitacion(self):
        """Su cuenta ya existía, y ya se invitó cuando se creó.

        Regenerarla al cargar un segundo archivo sería devolverle validez a un
        enlace que su titular pudo haber dejado atrás.
        """
        self.cargar()

        segundo = ENCABEZADO + (
            "1001234504,Mateo Restrepo Ruiz,43512345,Marta Ruiz Ochoa,marta.ruiz@example.com\n"
        )
        resultado = self.cargar(segundo)

        self.assertEqual(resultado.acudientes_reutilizados, 1)
        self.assertEqual(resultado.acudientes_creados, 0)
        self.assertEqual(resultado.invitaciones_generadas, 0)

    def test_con_contrasena_asignada_no_hay_invitacion_que_generar(self):
        """`DEC-11`: por ese camino la cuenta nace ya activada."""
        resultado = self.cargar(contrasena_de_desarrollo="clave-de-carga-2026")

        self.assertEqual(resultado.acudientes_creados, 2)
        self.assertEqual(resultado.invitaciones_generadas, 0)

    def test_una_cuenta_que_ya_definio_su_contrasena_no_admite_invitacion(self):
        usuario = Usuario.objects.crear_usuario(
            email="ya.entro@example.com", rol=Rol.ACUDIENTE
        )
        usuario.set_password(CLAVE_DEL_ACUDIENTE)
        usuario.save(update_fields=["password"])

        with self.assertRaises(ValueError):
            generar_invitacion(usuario)


class LaInvitacionDeLaCargaEsUtilizableTest(BaseDeCarga):
    """`TT-28`. Tercer criterio de `HU-03`, de extremo a extremo.

    Es la demostración que pide `DEC-9`: tomar el enlace de un acudiente
    cargado, definir la contraseña con él y entrar. Sin este recorrido, «se
    genera la invitación» sería un contador sin respaldo.
    """

    def setUp(self):
        super().setUp()
        self.cargar()
        self.acudiente = Usuario.objects.get(email="marta.ruiz@example.com")

    def test_el_acudiente_define_su_contrasena_y_entra(self):
        self.assertFalse(self.acudiente.tiene_contrasena_definida)

        enlace = generar_invitacion(self.acudiente)
        ruta = re.sub(r"^https?://[^/]+", "", enlace)

        # `PasswordResetConfirmView` cambia el token de la URL por uno interno y
        # redirige: hay que seguir la redirección antes de enviar el formulario.
        respuesta = self.client.get(ruta, follow=True)
        self.assertEqual(respuesta.status_code, 200)

        respuesta = self.client.post(
            respuesta.request["PATH_INFO"],
            {
                "new_password1": CLAVE_DEL_ACUDIENTE,
                "new_password2": CLAVE_DEL_ACUDIENTE,
            },
        )
        self.assertEqual(respuesta.status_code, 302)

        self.acudiente.refresh_from_db()
        self.assertTrue(self.acudiente.tiene_contrasena_definida)

        # Y con esa contraseña entra por la pantalla de acceso (`TT-56`).
        respuesta = self.client.post(
            reverse("acceso"),
            {"username": self.acudiente.email, "password": CLAVE_DEL_ACUDIENTE},
        )
        self.assertRedirects(respuesta, reverse("inicio"))

    def test_el_enlace_deja_de_valer_en_cuanto_se_usa(self):
        """`TT-18` ya lo probó; aquí se comprueba sobre el enlace de la carga."""
        enlace = generar_invitacion(self.acudiente)
        ruta = re.sub(r"^https?://[^/]+", "", enlace)

        respuesta = self.client.get(ruta, follow=True)
        self.client.post(
            respuesta.request["PATH_INFO"],
            {
                "new_password1": CLAVE_DEL_ACUDIENTE,
                "new_password2": CLAVE_DEL_ACUDIENTE,
            },
        )

        respuesta = self.client.get(ruta, follow=True)
        self.assertContains(respuesta, "Este enlace ya no sirve")


class ElEnlaceSeObtieneDeUnoEnUnoTest(BaseDeCarga):
    """`manage.py invitacion`. El enlace es una credencial (`DEC-3`)."""

    def setUp(self):
        super().setUp()
        self.cargar()

    def _invitacion(self, correo):
        from io import StringIO

        salida = StringIO()
        call_command("invitacion", correo, stdout=salida)
        return salida.getvalue()

    def test_imprime_el_enlace_del_acudiente_pedido(self):
        salida = self._invitacion("marta.ruiz@example.com")

        self.assertIn("marta.ruiz@example.com", salida)
        self.assertIn("/invitacion/", salida)

    def test_no_hay_enlace_para_una_cuenta_que_no_existe(self):
        with self.assertRaises(CommandError):
            self._invitacion("nadie@example.com")

    def test_el_resultado_de_la_carga_no_expone_ningun_enlace(self):
        """`DEC-3`: quien crea la cuenta no llega a conocer la clave.

        Listar los enlaces en la pantalla de la carga le daría a la institución
        la llave de todas las cuentas de acudiente.
        """
        resultado = self.cargar(
            ENCABEZADO
            + "1001234599,Otra Estudiante,99887766,Otro Acudiente,otro@example.com\n"
        )
        volcado = repr(resultado).lower()
        self.assertNotIn("http", volcado, "el resultado no lleva ningún enlace")
        self.assertNotIn("/invitacion/", volcado)
        # Lo que sí lleva es el recuento, que no es una credencial.
        self.assertIn("invitaciones_generadas=1", volcado)


# --- `HU-04` ---------------------------------------------------------------


class UnaCuentaConVariosEstudiantesTest(BaseDeCarga):
    """`TT-29`. Primer criterio de `HU-04`."""

    def setUp(self):
        super().setUp()
        self.cargar()
        self.marta = Usuario.objects.get(email="marta.ruiz@example.com")
        self.andres = Usuario.objects.get(email="andres.ospina@example.com")

    def test_una_sola_cuenta_tiene_varios_estudiantes_vinculados(self):
        estudiantes = estudiantes_a_cargo(usuario=self.marta)

        self.assertEqual(
            [e.nombre for e in estudiantes],
            ["Ana Sofía Restrepo Ruiz", "Tomás Restrepo Ruiz"],
        )
        self.assertEqual(Acudiente.objects.filter(usuario=self.marta).count(), 1)

    def test_cada_acudiente_ve_solo_a_los_suyos(self):
        self.assertEqual(estudiantes_a_cargo(usuario=self.andres).count(), 1)
        self.assertEqual(Estudiante.objects.count(), 3)

    def test_el_estudiante_ajeno_no_se_distingue_del_inexistente(self):
        """El filtro es la autorización, no un botón escondido (`DT-11`)."""
        ajeno = Estudiante.objects.get(documento="1001234503")

        with self.assertRaises(Estudiante.DoesNotExist):
            estudiante_a_cargo(usuario=self.marta, estudiante_id=ajeno.pk)

    def test_ningun_otro_rol_consulta_estudiantes_por_esta_via(self):
        cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, is_staff=True
        )
        with self.assertRaises(PermissionDenied):
            estudiantes_a_cargo(usuario=cajero)

    def test_una_cuenta_desactivada_no_consulta(self):
        """`HU-42`, y `INVD-1` no tiene nada que ver: es la cuenta, no el rol."""
        self.marta.is_active = False
        self.marta.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            estudiantes_a_cargo(usuario=self.marta)


class ElSelectorDeEstudianteTest(BaseDeCarga):
    """`TT-29`. La interfaz: `INT-1`, y el fragmento HTMX (`DT-16`)."""

    def setUp(self):
        super().setUp()
        self.cargar()
        self.marta = Usuario.objects.get(email="marta.ruiz@example.com")
        self.andres = Usuario.objects.get(email="andres.ospina@example.com")

    def test_el_panel_lista_los_estudiantes_a_cargo(self):
        self.client.force_login(self.marta)
        respuesta = self.client.get(reverse("mis-estudiantes"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ana Sofía Restrepo Ruiz")
        self.assertContains(respuesta, "Tomás Restrepo Ruiz")
        self.assertNotContains(respuesta, "Julián Ospina Vélez")

    def test_con_un_solo_estudiante_no_se_dibuja_el_selector(self):
        self.client.force_login(self.andres)
        respuesta = self.client.get(reverse("mis-estudiantes"))

        self.assertContains(respuesta, "Julián Ospina Vélez")
        self.assertNotContains(respuesta, 'role="group"')

    def test_el_selector_devuelve_un_fragmento_y_no_una_pagina(self):
        """`DT-16`: una vista HTMX devuelve un fragmento, nunca una página."""
        self.client.force_login(self.marta)
        tomas = Estudiante.objects.get(documento="1001234502")

        respuesta = self.client.get(
            reverse("estudiante-seleccionado", args=[tomas.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Tomás Restrepo Ruiz")
        self.assertNotContains(respuesta, "<html")
        self.assertTemplateNotUsed(respuesta, "base.html")

    def test_el_fragmento_de_un_estudiante_ajeno_es_un_404(self):
        self.client.force_login(self.marta)
        ajeno = Estudiante.objects.get(documento="1001234503")

        respuesta = self.client.get(
            reverse("estudiante-seleccionado", args=[ajeno.pk])
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_un_anonimo_no_alcanza_el_panel(self):
        respuesta = self.client.get(reverse("mis-estudiantes"))
        self.assertEqual(respuesta.status_code, 302)


class LoQueEsPorEstudianteYNoPorAcudienteTest(BaseDeCarga):
    """`TT-29`. Segundo criterio de `HU-04`.

    «El saldo, el límite diario y las restricciones son **por estudiante**, no
    por acudiente.» Los tres modelos llegan en sprints posteriores —billetera en
    el 2 (`HU-06`, `HU-09`), restricciones en el 3 (`HU-10`, `HU-11`)—, así que
    hoy el criterio se ejercita en las dos formas en que ya se puede: que la
    cuenta del acudiente **no** tenga dónde guardarlos, y que la interfaz los
    presente colgando de un estudiante concreto.

    La primera es la que importa: si mañana alguien añade `saldo` a `Acudiente`,
    esta prueba falla antes de que el error llegue a la billetera.
    """

    CAMPOS_QUE_NO_SON_DEL_ACUDIENTE = ["saldo", "limite_diario", "restricciones"]

    def setUp(self):
        super().setUp()
        self.cargar()
        self.marta = Usuario.objects.get(email="marta.ruiz@example.com")

    def test_la_cuenta_del_acudiente_no_tiene_donde_guardarlos(self):
        campos = {c.name for c in Acudiente._meta.get_fields()}
        for campo in self.CAMPOS_QUE_NO_SON_DEL_ACUDIENTE:
            with self.subTest(campo=campo):
                self.assertNotIn(
                    campo, campos,
                    f"«{campo}» es por estudiante, no por acudiente (HU-04)",
                )

    def test_el_detalle_cuelga_del_estudiante_elegido(self):
        self.client.force_login(self.marta)
        tomas = Estudiante.objects.get(documento="1001234502")

        respuesta = self.client.get(
            reverse("estudiante-seleccionado", args=[tomas.pk])
        )
        cuerpo = respuesta.content.decode()

        for etiqueta in ["Saldo", "Límite diario", "Restricciones"]:
            with self.subTest(etiqueta=etiqueta):
                self.assertIn(etiqueta, cuerpo)
        self.assertIn("Tomás Restrepo Ruiz", cuerpo)
        self.assertNotIn("Ana Sofía Restrepo Ruiz", cuerpo)
