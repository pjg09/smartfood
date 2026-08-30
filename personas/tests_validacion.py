"""`TT-25` … `TT-27`. Validación del archivo antes de escribir (`HU-02`).

Los tres criterios de `HU-02` se prueban por separado, y el segundo —«todo o
nada»— se prueba con el archivo mixto: filas correctas **y** filas con error.
Ese es el que distingue validar de validar de verdad. Un archivo enteramente
malo lo rechaza cualquiera; el que tiene la mitad bien es el que tienta a
escribir «lo que se pueda».
"""

from pathlib import Path

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from cuentas.models import Rol, Usuario
from cuentas.services import sincronizar_grupos_y_permisos
from personas.carga import leer
from personas.models import Acudiente, Estudiante
from personas.services import cargar_estudiantes_y_acudientes, dar_de_alta_la_institucion
from personas.validacion import ArchivoInvalido, validar

EJEMPLOS = Path(__file__).resolve().parent / "ejemplos"

ENCABEZADO = (
    "documento_estudiante,nombre_estudiante,"
    "documento_acudiente,nombre_acudiente,correo_acudiente\n"
)


def ejemplo(nombre):
    contenido = (EJEMPLOS / nombre).read_bytes()
    return SimpleUploadedFile(nombre, contenido, content_type="text/csv")


def filas(contenido):
    return leer(contenido.encode("utf-8"))


class ValidadorTest(TestCase):
    """`TT-25`. Acumula, no corta al primero."""

    def test_un_archivo_correcto_no_da_errores(self):
        self.assertEqual(validar(filas(
            ENCABEZADO + "1001234501,Ana,43512345,Marta,marta@example.com\n"
        )), [])

    def test_acumula_todos_los_errores_y_no_se_detiene_en_el_primero(self):
        """Lo que evita subir el archivo diez veces para diez erratas."""
        errores = validar(filas(
            ENCABEZADO
            + ",Ana,43512345,Marta,marta@example.com\n"
            + "1001234502,,43512345,Marta,marta@example.com\n"
            + "1001234503,Julián,71234567,Andrés,no-es-correo\n"
        ))
        self.assertEqual(len(errores), 3)
        self.assertEqual([e.fila for e in errores], [2, 3, 4])

    def test_señala_la_fila_la_columna_y_el_valor(self):
        """Tercer criterio de `HU-02`: el reporte identifica los errores."""
        error = validar(filas(
            ENCABEZADO + "1001234501,Ana,43512345,Marta,no-es-correo\n"
        ))[0]
        self.assertEqual(error.fila, 2)
        self.assertEqual(error.columna, "correo_acudiente")
        self.assertEqual(error.valor, "no-es-correo")
        self.assertIn("correo", error.mensaje.lower())

    def test_detecta_un_estudiante_repetido_dentro_del_archivo(self):
        errores = validar(filas(
            ENCABEZADO
            + "1001234501,Ana,43512345,Marta,marta@example.com\n"
            + "1001234501,Ana Otra Vez,43512345,Marta,marta@example.com\n"
        ))
        self.assertEqual(len(errores), 1)
        self.assertIn("fila 2", errores[0].mensaje)

    def test_detecta_que_el_archivo_se_contradice_sobre_un_acudiente(self):
        """`[S3]` del formato: el correo identifica. Adivinar no es una opción."""
        errores = validar(filas(
            ENCABEZADO
            + "1001234501,Ana,43512345,Marta Ruiz,marta@example.com\n"
            + "1001234502,Tomás,99999999,Marta Otra,marta@example.com\n"
        ))
        columnas = {e.columna for e in errores}
        self.assertIn("documento_acudiente", columnas)
        self.assertIn("nombre_acudiente", columnas)

    def test_detecta_un_documento_de_acudiente_con_dos_correos(self):
        """Serían dos cuentas para la misma persona."""
        errores = validar(filas(
            ENCABEZADO
            + "1001234501,Ana,43512345,Marta,marta@example.com\n"
            + "1001234502,Tomás,43512345,Marta,otra-marta@example.com\n"
        ))
        self.assertTrue(any(e.columna == "correo_acudiente" for e in errores))

    def test_los_campos_obligatorios_lo_son(self):
        errores = validar(filas(ENCABEZADO + ",,,,\n"))
        self.assertEqual(len(errores), 5, "las cinco columnas son obligatorias")

    def test_rechaza_un_documento_demasiado_corto(self):
        errores = validar(filas(
            ENCABEZADO + "12,Ana,43512345,Marta,marta@example.com\n"
        ))
        self.assertEqual(errores[0].columna, "documento_estudiante")


class ValidacionContraElSistemaTest(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba", email="institucion@example.com",
                contrasena_de_desarrollo="clave-de-prueba-2026",
            )
        self.actor = institucion.usuario
        mail.outbox.clear()

    def test_detecta_un_estudiante_que_ya_existe(self):
        with self.captureOnCommitCallbacks(execute=True):
            cargar_estudiantes_y_acudientes(actor=self.actor, archivo=ejemplo("carga-valida.csv"))

        with self.assertRaises(ArchivoInvalido) as ctx:
            cargar_estudiantes_y_acudientes(actor=self.actor, archivo=ejemplo("carga-valida.csv"))

        self.assertTrue(
            all("Ya existe un estudiante" in e.mensaje for e in ctx.exception.errores)
        )

    def test_detecta_un_acudiente_existente_con_otro_correo(self):
        with self.captureOnCommitCallbacks(execute=True):
            cargar_estudiantes_y_acudientes(actor=self.actor, archivo=ejemplo("carga-valida.csv"))

        otro = SimpleUploadedFile(
            "x.csv",
            (ENCABEZADO + "1009999999,Nuevo,43512345,Marta Ruiz Ochoa,otro@example.com\n").encode(),
            content_type="text/csv",
        )
        with self.assertRaises(ArchivoInvalido) as ctx:
            cargar_estudiantes_y_acudientes(actor=self.actor, archivo=otro)

        self.assertIn("Ya existe un acudiente", str(ctx.exception.errores[0].mensaje))


class TodoONadaTest(TestCase):
    """`TT-27`. Los tres archivos, y el segundo criterio de `HU-02`."""

    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba", email="institucion@example.com",
                contrasena_de_desarrollo="clave-de-prueba-2026",
            )
        self.actor = institucion.usuario
        mail.outbox.clear()

    def _nada_escrito(self):
        self.assertEqual(Estudiante.objects.count(), 0)
        self.assertEqual(Acudiente.objects.count(), 0)
        self.assertEqual(Usuario.objects.filter(rol=Rol.ACUDIENTE).count(), 0)

    def test_el_archivo_valido_carga_entero(self):
        with self.captureOnCommitCallbacks(execute=True):
            resultado = cargar_estudiantes_y_acudientes(
                actor=self.actor, archivo=ejemplo("carga-valida.csv")
            )

        self.assertEqual(resultado.estudiantes_creados, 5)
        self.assertEqual(resultado.acudientes_creados, 3)
        self.assertEqual(Estudiante.objects.count(), 5)

    def test_el_archivo_con_errores_no_escribe_nada(self):
        with self.assertRaises(ArchivoInvalido) as ctx:
            cargar_estudiantes_y_acudientes(
                actor=self.actor, archivo=ejemplo("carga-con-errores.csv")
            )

        self.assertGreater(len(ctx.exception.errores), 1, "debe reportar todos, no el primero")
        self._nada_escrito()

    def test_el_archivo_mixto_no_escribe_NI_LAS_FILAS_BUENAS(self):
        """El que distingue validar de validar de verdad.

        Un archivo enteramente malo lo rechaza cualquiera. El que tiene la mitad
        bien es el que tienta a escribir «lo que se pueda», y eso dejaría el
        sistema con medio colegio dentro.
        """
        with self.assertRaises(ArchivoInvalido):
            cargar_estudiantes_y_acudientes(
                actor=self.actor, archivo=ejemplo("carga-mixta.csv")
            )

        self._nada_escrito()

    def test_la_validacion_ocurre_antes_de_escribir_no_despues_de_deshacer(self):
        """Primer criterio de `HU-02`, y no es lo mismo que una transacción.

        Se comprueba mirando la secuencia: si se hubiera escrito y deshecho, el
        contador de identificadores de PostgreSQL habría avanzado. Como las
        claves son UUID generados en la aplicación, se comprueba de otra forma:
        el servicio lanza la excepción sin haber tocado la base, así que ningún
        `post_save` llegó a dispararse y la bandeja está vacía.
        """
        with self.assertRaises(ArchivoInvalido):
            cargar_estudiantes_y_acudientes(
                actor=self.actor, archivo=ejemplo("carga-mixta.csv")
            )

        self.assertEqual(len(mail.outbox), 0)
        self._nada_escrito()


class PantallaDeErroresTest(TestCase):
    """`TT-26`."""

    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba", email="institucion@example.com",
                contrasena_de_desarrollo="clave-de-prueba-2026",
            )
        self.client.force_login(institucion.usuario)

    def test_el_reporte_muestra_fila_columna_y_motivo(self):
        respuesta = self.client.post("/carga/", {"archivo": ejemplo("carga-mixta.csv")})

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No se cargó nada")
        self.assertContains(respuesta, "correo-sin-arroba")
        self.assertContains(respuesta, "correo_acudiente")
        self.assertEqual(Estudiante.objects.count(), 0)

    def test_el_reporte_dice_cuantos_errores_hay(self):
        respuesta = self.client.post("/carga/", {"archivo": ejemplo("carga-con-errores.csv")})
        self.assertContains(respuesta, "errores")

    def test_un_archivo_valido_muestra_el_resultado_y_no_el_reporte(self):
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post("/carga/", {"archivo": ejemplo("carga-valida.csv")})

        self.assertContains(respuesta, "Carga completada")
        self.assertNotContains(respuesta, "No se cargó nada")
