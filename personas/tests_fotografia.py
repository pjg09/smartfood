"""`TT-51` y `TT-52`. Fotografía del estudiante (`HU-57`).

Se apoya en lo que `TT-50` y `TT-55` dejaron montado: el almacenamiento privado
(`DT-18`, `DT-21`) y la canalización que re-codifica y retira el EXIF (`DT-20`).
Lo que se prueba aquí es lo que este PR añade y, sobre todo, **el segundo
criterio de la historia**: que la fotografía no sea obligatoria y su ausencia no
impida ninguna operación. Eso no se prueba mirando el campo, se prueba haciendo
las operaciones sin ella.

Las pruebas usan un almacenamiento en memoria en lugar de MinIO: son de este PR,
no del bucket, y `TT-50` ya tiene las suyas. Lo que sí se comprueba contra los
ajustes reales es que el almacenamiento `privado` firma las URL y que la firma
caduca pronto — la fotografía de un menor no puede quedar en una URL adivinable
ni en una que siga sirviendo meses después (`DEC-8`, `ALC-OUT-08`).
"""

from io import BytesIO

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from config.imagenes import ImagenInvalida, tiene_exif
from cuentas.models import Rol
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from personas.models import Acudiente, Estudiante
from personas.services import (
    crear_estudiante,
    dar_de_alta_la_institucion,
    dar_de_baja,
    guardar_fotografia,
    quitar_fotografia,
    reasignar_codigo_de_tarjeta,
)

CLAVE = "clave-de-prueba-2026"

# Almacenamiento en memoria para el alias `privado`. Cada prueba parte de cero.
EN_MEMORIA = {
    **settings.STORAGES,
    "privado": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
}


def imagen(formato="JPEG", tamano=(320, 240), color=(40, 120, 200), **guardar):
    """Un avatar generado. **Nunca una persona real** (`INVD-6`, `ALC-OUT-07`)."""
    buffer = BytesIO()
    Image.new("RGB", tamano, color).save(buffer, format=formato, **guardar)
    return buffer.getvalue()


def archivo(datos=None, nombre="avatar.jpg", tipo="image/jpeg"):
    return SimpleUploadedFile(nombre, datos or imagen(), content_type=tipo)


@override_settings(STORAGES=EN_MEMORIA)
class BaseDeFotografia(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo=CLAVE,
            )
        self.actor = institucion.usuario

        cuenta = crear_cuenta(
            email="marta.ruiz@example.com",
            rol=Rol.ACUDIENTE,
            nombre="Marta Ruiz Ochoa",
            enviar_invitacion=False,
        )
        self.acudiente = Acudiente.objects.create(
            usuario=cuenta, nombre="Marta Ruiz Ochoa", documento="43512345"
        )
        self.estudiante = crear_estudiante(
            actor=self.actor,
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001234501",
            acudiente=self.acudiente,
        )

    def subir(self, datos=None, estudiante=None):
        with self.captureOnCommitCallbacks(execute=True):
            return guardar_fotografia(
                actor=self.actor,
                estudiante=estudiante or self.estudiante,
                archivo=archivo(datos),
            )


# --- Primer criterio: se carga y se actualiza desde la vista de `HU-44` -----


class CargaYReemplazoTest(BaseDeFotografia):
    def test_el_estudiante_nace_sin_fotografia(self):
        self.assertFalse(self.estudiante.tiene_foto)
        self.assertEqual(self.estudiante.foto_clave, "")
        self.assertIsNone(self.estudiante.url_de_la_foto)

    def test_guardar_deja_la_clave_en_la_base_y_el_binario_fuera(self):
        """`DT-18`: la base guarda la clave del objeto, nunca el binario."""
        self.subir()
        self.estudiante.refresh_from_db()

        self.assertTrue(self.estudiante.tiene_foto)
        self.assertTrue(self.estudiante.foto_clave.endswith(".webp"))
        self.assertLess(
            len(self.estudiante.foto_clave), 200, "eso no es una clave, es un binario"
        )
        self.assertTrue(storages["privado"].exists(self.estudiante.foto_clave))

    def test_lo_almacenado_es_la_imagen_re_codificada(self):
        """`DT-20`. No se guarda el fichero que subieron: se guarda uno nuevo."""
        self.subir()
        self.estudiante.refresh_from_db()

        with storages["privado"].open(self.estudiante.foto_clave) as guardada:
            datos = guardada.read()

        with Image.open(BytesIO(datos)) as salida:
            self.assertEqual(salida.format, "WEBP")

    def test_el_exif_no_llega_al_almacenamiento(self):
        """La fotografía de un menor tomada con un móvil lleva dentro el GPS.

        `TT-55` ya prueba que la canalización lo retira; esto comprueba que la
        fotografía del estudiante **pasa por ella** y no se guarda en crudo.
        """
        con_exif = imagen(exif=Image.Exif().tobytes())
        self.subir(con_exif)
        self.estudiante.refresh_from_db()

        with storages["privado"].open(self.estudiante.foto_clave) as guardada:
            self.assertFalse(tiene_exif(guardada.read()))

    def test_reemplazar_cambia_la_clave_y_borra_la_anterior(self):
        """No se guarda historial de fotografías, y es deliberado.

        Ninguna historia lo pide, y conservar retratos de menores que ya nadie
        usa es lo que `ALC-OUT-08` desaconseja.
        """
        self.subir()
        self.estudiante.refresh_from_db()
        primera = self.estudiante.foto_clave

        self.subir(imagen(color=(10, 200, 90)))
        self.estudiante.refresh_from_db()

        self.assertNotEqual(self.estudiante.foto_clave, primera)
        self.assertFalse(storages["privado"].exists(primera), "quedó huérfana")
        self.assertTrue(storages["privado"].exists(self.estudiante.foto_clave))

    def test_quitarla_la_borra_del_almacenamiento(self):
        """Que no sea obligatoria significa que se pueda quitar."""
        self.subir()
        self.estudiante.refresh_from_db()
        clave = self.estudiante.foto_clave

        with self.captureOnCommitCallbacks(execute=True):
            quitar_fotografia(actor=self.actor, estudiante=self.estudiante)
        self.estudiante.refresh_from_db()

        self.assertFalse(self.estudiante.tiene_foto)
        self.assertFalse(storages["privado"].exists(clave))

    def test_quitarla_dos_veces_no_falla(self):
        quitar_fotografia(actor=self.actor, estudiante=self.estudiante)
        quitar_fotografia(actor=self.actor, estudiante=self.estudiante)
        self.assertFalse(self.estudiante.tiene_foto)

    def test_un_fichero_que_no_es_imagen_se_rechaza(self):
        """Se valida por contenido, no por el nombre ni por el tipo declarado."""
        disfrazado = SimpleUploadedFile(
            "avatar.jpg", b"<?php system($_GET[0]); ?>", content_type="image/jpeg"
        )
        with self.assertRaises(ImagenInvalida):
            guardar_fotografia(
                actor=self.actor, estudiante=self.estudiante, archivo=disfrazado
            )

        self.estudiante.refresh_from_db()
        self.assertFalse(self.estudiante.tiene_foto)


# --- La fotografía se sirve firmada y caduca pronto -------------------------


class LaFotografiaNoQuedaEnUnaUrlAdivinableTest(BaseDeFotografia):
    def test_la_url_se_construye_desde_la_clave(self):
        self.subir()
        self.estudiante.refresh_from_db()

        url = self.estudiante.url_de_la_foto
        self.assertIsNotNone(url)
        self.assertIn(self.estudiante.foto_clave.rsplit("/", 1)[-1], url)

    def test_sin_fotografia_no_hay_url(self):
        self.assertIsNone(self.estudiante.url_de_la_foto)


class LosAjustesDelAlmacenamientoPrivadoTest(TestCase):
    """Contra los ajustes reales, no contra el almacenamiento de las pruebas.

    Es la mitad de `HU-57` que no se puede comprobar con un almacenamiento en
    memoria, y es la que protege a un menor: la fotografía se sirve **firmada** y
    la firma **caduca pronto** (`DEC-8`, `ALC-OUT-08`, `DT-18`).
    """

    def test_el_alias_privado_firma_las_url(self):
        opciones = settings.STORAGES["privado"]["OPTIONS"]
        self.assertTrue(opciones["querystring_auth"])

    def test_la_firma_caduca_en_minutos_y_no_en_meses(self):
        caducidad = settings.STORAGES["privado"]["OPTIONS"]["querystring_expire"]
        self.assertLessEqual(caducidad, 15 * 60, "una firma que dura horas no es corta")

    def test_va_al_prefijo_privado_y_no_al_publico(self):
        self.assertEqual(settings.STORAGES["privado"]["OPTIONS"]["location"], "privado")

    def test_las_imagenes_de_producto_no_comparten_prefijo(self):
        self.assertNotEqual(
            settings.STORAGES["privado"]["OPTIONS"]["location"],
            settings.STORAGES["publico"]["OPTIONS"]["location"],
        )


# --- Segundo criterio: NO es obligatoria -----------------------------------


class SinFotografiaTodoSigueFuncionandoTest(BaseDeFotografia):
    """«Su ausencia no impide ninguna operación», y el plan pide demostrarlo.

    No se demuestra mirando que el campo admita vacío: se demuestra haciendo,
    sin fotografía, todo lo que el sistema sabe hacer con un estudiante.
    """

    def test_se_matricula_sin_fotografia(self):
        otro = crear_estudiante(
            actor=self.actor,
            nombre="Tomás Restrepo Ruiz",
            documento="1001234502",
            acudiente=self.acudiente,
        )
        self.assertFalse(otro.tiene_foto)

    def test_se_le_imprime_la_tarjeta(self):
        self.client.force_login(self.actor)
        respuesta = self.client.get(
            reverse("tarjeta-del-estudiante", args=[self.estudiante.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, self.estudiante.codigo_tarjeta)

    def test_se_le_reasigna_el_codigo(self):
        anterior, nuevo = reasignar_codigo_de_tarjeta(
            actor=self.actor, estudiante=self.estudiante
        )
        self.assertNotEqual(anterior, nuevo)

    def test_se_le_da_de_baja(self):
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.esta_de_baja)

    def test_el_acudiente_lo_ve_en_su_panel(self):
        self.client.force_login(self.acudiente.usuario)
        respuesta = self.client.get(reverse("mis-estudiantes"))
        self.assertContains(respuesta, "Ana Sofía Restrepo Ruiz")

    def test_la_ficha_del_admin_dice_que_no_la_tiene_en_vez_de_fallar(self):
        self.client.force_login(self.actor)
        respuesta = self.client.get(
            reverse("admin:personas_estudiante_change", args=[self.estudiante.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No es obligatoria")

    def test_la_carga_masiva_no_pide_fotografia(self):
        """El formato acordado no tiene columna para ella (`TT-22`)."""
        from personas.carga import COLUMNAS

        self.assertNotIn("foto", "".join(COLUMNAS))


# --- Quién puede cargarla ---------------------------------------------------


class SoloLaInstitucionCargaLaFotografiaTest(BaseDeFotografia):
    def test_ningun_otro_rol(self):
        for rol in [Rol.CAJERO, Rol.ADMINISTRADOR, Rol.ACUDIENTE]:
            with self.subTest(rol=rol):
                otro = crear_cuenta(
                    email=f"{rol}@example.com", rol=rol, enviar_invitacion=False
                )
                with self.assertRaises(PermissionDenied):
                    guardar_fotografia(
                        actor=otro, estudiante=self.estudiante, archivo=archivo()
                    )

    def test_ni_el_acudiente_para_su_propio_hijo(self):
        """`HU-57` es de `USR-5`: la carga la institución."""
        with self.assertRaises(PermissionDenied):
            guardar_fotografia(
                actor=self.acudiente.usuario,
                estudiante=self.estudiante,
                archivo=archivo(),
            )


# --- `TT-52`. Desde la ficha ------------------------------------------------


class LaCargaDesdeLaFichaTest(BaseDeFotografia):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.actor)

    def _cambiar(self, **extra):
        datos = {
            "nombre": self.estudiante.nombre,
            "documento": self.estudiante.documento,
            "acudiente": str(self.acudiente.pk),
            **extra,
        }
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                reverse("admin:personas_estudiante_change", args=[self.estudiante.pk]),
                datos,
            )

    def test_la_ficha_ofrece_el_campo(self):
        cuerpo = self.client.get(
            reverse("admin:personas_estudiante_change", args=[self.estudiante.pk])
        ).content.decode()
        self.assertIn('name="fotografia"', cuerpo)

    def test_subirla_desde_la_ficha_la_guarda(self):
        respuesta = self._cambiar(fotografia=archivo())
        self.assertEqual(respuesta.status_code, 302)

        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.tiene_foto)

    def test_la_ficha_la_muestra_despues(self):
        self._cambiar(fotografia=archivo())
        cuerpo = self.client.get(
            reverse("admin:personas_estudiante_change", args=[self.estudiante.pk])
        ).content.decode()

        self.assertIn("<img", cuerpo)
        self.assertIn("Fotografía de Ana Sofía Restrepo Ruiz", cuerpo)

    def test_se_quita_marcando_la_casilla(self):
        self._cambiar(fotografia=archivo())
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.tiene_foto)

        self._cambiar(quitar_fotografia="on")
        self.estudiante.refresh_from_db()
        self.assertFalse(self.estudiante.tiene_foto)

    def test_un_fichero_roto_lo_para_el_formulario(self):
        """Primera barrera: `ImageField` no lo reconoce y no se guarda nada."""
        respuesta = self._cambiar(
            nombre="Ana Sofía Restrepo Mejía",
            fotografia=SimpleUploadedFile(
                "avatar.jpg", imagen()[:120], content_type="image/jpeg"
            ),
        )

        self.assertEqual(respuesta.status_code, 200, "debería reenseñar el formulario")
        self.estudiante.refresh_from_db()
        self.assertFalse(self.estudiante.tiene_foto)
        self.assertEqual(self.estudiante.nombre, "Ana Sofía Restrepo Ruiz")

    def test_un_formato_no_aceptado_avisa_pero_no_tira_la_edicion(self):
        """Segunda barrera, y la que importa para el segundo criterio.

        Un TIFF es una imagen de verdad: el formulario lo acepta y es la
        canalización la que lo rechaza (`DT-20` fija los formatos de entrada).
        Como la fotografía **no es obligatoria**, ese fallo no puede llevarse por
        delante el resto de la edición.
        """
        respuesta = self._cambiar(
            nombre="Ana Sofía Restrepo Mejía",
            fotografia=archivo(imagen(formato="TIFF"), "avatar.tiff", "image/tiff"),
        )
        self.assertEqual(respuesta.status_code, 302)

        self.estudiante.refresh_from_db()
        self.assertFalse(self.estudiante.tiene_foto)
        self.assertEqual(
            self.estudiante.nombre,
            "Ana Sofía Restrepo Mejía",
            "el fallo de la fotografía se llevó por delante el cambio de nombre",
        )

    def test_el_listado_dice_quien_tiene_fotografia(self):
        respuesta = self.client.get(reverse("admin:personas_estudiante_changelist"))
        self.assertContains(respuesta, "foto")
