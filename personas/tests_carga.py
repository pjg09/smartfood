"""`TT-21` … `TT-24`. Carga masiva de estudiantes y acudientes (`HU-01`)."""

from django.core import mail
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import IntegrityError
from django.test import TestCase

from cuentas.models import Rol, Usuario
from cuentas.services import sincronizar_grupos_y_permisos
from personas.carga import ArchivoIlegible, leer
from personas.models import Acudiente, Estudiante
from personas.services import cargar_estudiantes_y_acudientes, dar_de_alta_la_institucion

ENCABEZADO = (
    "documento_estudiante,nombre_estudiante,"
    "documento_acudiente,nombre_acudiente,correo_acudiente\n"
)

# Marta tiene dos hijos matriculados: aparece en dos filas (`ALC-IN-04`).
ARCHIVO = ENCABEZADO + (
    "1001234501,Ana Sofía Restrepo Ruiz,43512345,Marta Ruiz Ochoa,marta.ruiz@example.com\n"
    "1001234502,Tomás Restrepo Ruiz,43512345,Marta Ruiz Ochoa,marta.ruiz@example.com\n"
    "1001234503,Julián Ospina Vélez,71234567,Andrés Ospina Mesa,andres.ospina@example.com\n"
)


def archivo(contenido=ARCHIVO, nombre="estudiantes.csv"):
    return SimpleUploadedFile(nombre, contenido.encode("utf-8"), content_type="text/csv")


class LectorTest(TestCase):
    """`TT-23`, la mitad que solo lee."""

    def test_lee_las_filas_y_recorta_espacios(self):
        filas = leer(archivo(ENCABEZADO + "  1001 ,  Ana  ,43512345, Marta ,  M@example.com \n"))
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0].documento_estudiante, "1001")
        self.assertEqual(filas[0].nombre_estudiante, "Ana")
        self.assertEqual(filas[0].correo_acudiente, "M@example.com")

    def test_la_primera_fila_de_datos_es_la_numero_dos(self):
        """El número tiene que coincidir con lo que el usuario ve en su editor."""
        filas = leer(archivo())
        self.assertEqual([f.numero for f in filas], [2, 3, 4])

    def test_tolera_el_bom_que_antepone_excel(self):
        filas = leer(("﻿" + ARCHIVO).encode("utf-8"))
        self.assertEqual(len(filas), 3)

    def test_las_columnas_se_identifican_por_nombre_no_por_posicion(self):
        invertido = (
            "correo_acudiente,nombre_acudiente,documento_acudiente,"
            "nombre_estudiante,documento_estudiante\n"
            "marta.ruiz@example.com,Marta Ruiz Ochoa,43512345,Ana Sofía,1001234501\n"
        )
        filas = leer(archivo(invertido))
        self.assertEqual(filas[0].documento_estudiante, "1001234501")

    def test_rechaza_un_archivo_al_que_le_falta_una_columna(self):
        sin_correo = "documento_estudiante,nombre_estudiante\n1001,Ana\n"
        with self.assertRaises(ArchivoIlegible) as ctx:
            leer(archivo(sin_correo))
        self.assertIn("correo_acudiente", str(ctx.exception))

    def test_rechaza_el_archivo_vacio_y_el_que_solo_trae_encabezado(self):
        for contenido in ("", ENCABEZADO):
            with self.subTest(contenido=contenido[:20]):
                with self.assertRaises(ArchivoIlegible):
                    leer(archivo(contenido))

    def test_rechaza_una_codificacion_que_no_es_utf8(self):
        with self.assertRaises(ArchivoIlegible):
            leer((ENCABEZADO + "1001,Ana Sofía,435,Marta,m@example.com\n").encode("latin-1"))


class CargaMasivaTest(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo="clave-de-prueba-2026",
            )
        self.actor = institucion.usuario
        mail.outbox.clear()

    # --- Criterios de aceptación de HU-01 ---------------------------------

    def test_acepta_el_archivo_y_crea_a_todos(self):
        with self.captureOnCommitCallbacks(execute=True):
            resultado = cargar_estudiantes_y_acudientes(actor=self.actor, archivo=archivo())

        self.assertEqual(resultado.filas_leidas, 3)
        self.assertEqual(resultado.estudiantes_creados, 3)
        self.assertEqual(Estudiante.objects.count(), 3)

    def test_solo_la_institucion_puede_cargar(self):
        """Segundo criterio: función exclusiva de la institución."""
        for rol in (Rol.CAJERO, Rol.ADMINISTRADOR, Rol.ACUDIENTE):
            with self.subTest(rol=rol):
                otro = Usuario.objects.crear_usuario(email=f"{rol}@example.com", rol=rol)
                with self.assertRaises(PermissionDenied):
                    cargar_estudiantes_y_acudientes(actor=otro, archivo=archivo())
        self.assertEqual(Estudiante.objects.count(), 0)

    def test_cada_estudiante_queda_vinculado_a_un_responsable(self):
        with self.captureOnCommitCallbacks(execute=True):
            cargar_estudiantes_y_acudientes(actor=self.actor, archivo=archivo())

        for estudiante in Estudiante.objects.all():
            self.assertIsNotNone(estudiante.acudiente)

    def test_un_acudiente_puede_quedar_a_cargo_de_varios_estudiantes(self):
        """Cuarto criterio, `ALC-IN-04`, `HU-04`. El correo agrupa."""
        with self.captureOnCommitCallbacks(execute=True):
            resultado = cargar_estudiantes_y_acudientes(actor=self.actor, archivo=archivo())

        self.assertEqual(resultado.acudientes_creados, 2, "tres filas, dos acudientes")
        marta = Acudiente.objects.get(usuario__email="marta.ruiz@example.com")
        self.assertEqual(marta.estudiantes.count(), 2)

    # --- Cómo nacen las cuentas -------------------------------------------

    def test_la_cuenta_del_acudiente_nace_sin_contrasena_utilizable(self):
        """`INV-6`, `INVD-1`."""
        with self.captureOnCommitCallbacks(execute=True):
            cargar_estudiantes_y_acudientes(actor=self.actor, archivo=archivo())

        for acudiente in Acudiente.objects.all():
            self.assertFalse(acudiente.usuario.has_usable_password())

    def test_la_carga_no_entrega_ningun_correo(self):
        """`DEC-9`: las direcciones son ficticias, un rebote quema la cuenta."""
        with self.captureOnCommitCallbacks(execute=True):
            cargar_estudiantes_y_acudientes(actor=self.actor, archivo=archivo())

        self.assertEqual(len(mail.outbox), 0)

    def test_con_contrasena_de_desarrollo_las_cuentas_quedan_utilizables(self):
        """`DEC-11`. Sigue sin enviar correo."""
        with self.captureOnCommitCallbacks(execute=True):
            cargar_estudiantes_y_acudientes(
                actor=self.actor, archivo=archivo(),
                contrasena_de_desarrollo="acudiente-2026",
            )

        marta = Acudiente.objects.get(usuario__email="marta.ruiz@example.com")
        self.assertTrue(marta.usuario.check_password("acudiente-2026"))
        self.assertEqual(len(mail.outbox), 0)

    def test_los_acudientes_quedan_en_su_grupo(self):
        with self.captureOnCommitCallbacks(execute=True):
            cargar_estudiantes_y_acudientes(actor=self.actor, archivo=archivo())

        marta = Acudiente.objects.get(usuario__email="marta.ruiz@example.com")
        self.assertEqual([g.name for g in marta.usuario.groups.all()], ["rol:acudiente"])

    # --- Todo o nada -------------------------------------------------------

    def test_si_una_fila_falla_no_se_escribe_ninguna(self):
        """La atomicidad que `HU-02` convierte en criterio (`TT-25`, `PR-13`)."""
        duplicado = ARCHIVO + (
            "1001234501,Ana Sofía Otra Vez,99999999,Otro Acudiente,otro@example.com\n"
        )
        with self.assertRaises(IntegrityError):
            with self.captureOnCommitCallbacks(execute=True):
                cargar_estudiantes_y_acudientes(actor=self.actor, archivo=archivo(duplicado))

        self.assertEqual(Estudiante.objects.count(), 0)
        self.assertEqual(Acudiente.objects.count(), 0)
        self.assertEqual(Usuario.objects.filter(rol=Rol.ACUDIENTE).count(), 0)

    def test_un_archivo_ilegible_no_escribe_nada(self):
        with self.assertRaises(ArchivoIlegible):
            cargar_estudiantes_y_acudientes(
                actor=self.actor, archivo=archivo("documento_estudiante\n1001\n")
            )
        self.assertEqual(Estudiante.objects.count(), 0)

    def test_una_segunda_carga_reutiliza_al_acudiente_existente(self):
        with self.captureOnCommitCallbacks(execute=True):
            cargar_estudiantes_y_acudientes(actor=self.actor, archivo=archivo())

        otra = ENCABEZADO + (
            "1001234599,Hermano Nuevo,43512345,Marta Ruiz Ochoa,marta.ruiz@example.com\n"
        )
        with self.captureOnCommitCallbacks(execute=True):
            resultado = cargar_estudiantes_y_acudientes(actor=self.actor, archivo=archivo(otra))

        self.assertEqual(resultado.acudientes_creados, 0)
        self.assertEqual(resultado.acudientes_reutilizados, 1)
        self.assertEqual(Acudiente.objects.count(), 2)


class PantallaDeCargaTest(TestCase):
    """`TT-24`."""

    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo="clave-de-prueba-2026",
            )
        self.actor = institucion.usuario

    def test_la_institucion_ve_la_pantalla(self):
        self.client.force_login(self.actor)
        respuesta = self.client.get("/carga/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Cargar estudiantes")

    def test_un_anonimo_no_la_ve(self):
        respuesta = self.client.get("/carga/")
        self.assertEqual(respuesta.status_code, 302)

    def test_el_personal_no_la_ve(self):
        cajero = Usuario.objects.crear_usuario(email="cajero@example.com", rol=Rol.CAJERO)
        self.client.force_login(cajero)
        self.assertEqual(self.client.get("/carga/").status_code, 403)

    def test_subir_el_archivo_carga_y_muestra_el_resultado(self):
        self.client.force_login(self.actor)
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post("/carga/", {"archivo": archivo()})

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Carga completada")
        self.assertEqual(Estudiante.objects.count(), 3)

    def test_un_archivo_ilegible_se_reporta_y_no_escribe(self):
        self.client.force_login(self.actor)
        respuesta = self.client.post(
            "/carga/", {"archivo": archivo("documento_estudiante\n1001\n")}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No se pudo leer el archivo")
        self.assertEqual(Estudiante.objects.count(), 0)
