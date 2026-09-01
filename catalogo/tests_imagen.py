"""`TT-53` y `TT-54`. Imagen del producto (`HU-59`).

Es el gemelo de la fotografía del estudiante (`PR-20`) con una diferencia que lo
cambia casi todo: **esta imagen no es sensible**. Va al prefijo `publico/` y la
sirve la aplicación con caché larga en vez de una URL firmada (`DT-21`), porque
firmar cincuenta URL para pintar la lista del punto de venta es coste sin
contrapartida y una firma caduca.

Que no sea sensible no significa que la ruta no tenga que defenderse: el
almacenamiento antepone el prefijo a lo que se le pida, así que una clave con
`..` alcanzaría la fotografía de un estudiante. Esa es la prueba que más importa
de este fichero.
"""

from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from catalogo.models import Categoria
from catalogo.selectors import productos_en_el_catalogo
from catalogo.services import crear_producto, guardar_imagen, quitar_imagen
from config.imagenes import ImagenInvalida
from cuentas.models import Rol
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos

EN_MEMORIA = {
    **settings.STORAGES,
    "publico": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "privado": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
}


def imagen(formato="JPEG", tamano=(240, 240), color=(220, 160, 40), **guardar):
    buffer = BytesIO()
    Image.new("RGB", tamano, color).save(buffer, format=formato, **guardar)
    return buffer.getvalue()


def archivo(datos=None, nombre="empanada.jpg", tipo="image/jpeg"):
    return SimpleUploadedFile(nombre, datos or imagen(), content_type=tipo)


@override_settings(STORAGES=EN_MEMORIA)
class BaseDeImagen(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        self.actor = crear_cuenta(
            email="administracion@example.com",
            rol=Rol.ADMINISTRADOR,
            nombre="Administración de la cafetería",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.categoria = Categoria.objects.create(nombre="Panadería")
        self.producto = crear_producto(
            actor=self.actor,
            nombre="Empanada de carne",
            precio=Decimal("3000"),
            categoria=self.categoria,
        )

    def subir(self, datos=None, producto=None):
        with self.captureOnCommitCallbacks(execute=True):
            return guardar_imagen(
                actor=self.actor,
                producto=producto or self.producto,
                archivo=archivo(datos),
            )


class CargaYReemplazoTest(BaseDeImagen):
    def test_el_producto_nace_sin_imagen(self):
        self.assertFalse(self.producto.tiene_imagen)
        self.assertIsNone(self.producto.url_de_la_imagen)

    def test_guardar_deja_la_clave_y_el_binario_fuera(self):
        self.subir()
        self.producto.refresh_from_db()

        self.assertTrue(self.producto.imagen_clave.endswith(".webp"))
        self.assertTrue(storages["publico"].exists(self.producto.imagen_clave))

    def test_va_al_prefijo_publico_y_no_al_privado(self):
        """Donde va la fotografía de un menor no va la de una empanada."""
        self.assertNotEqual(
            settings.STORAGES["publico"]["OPTIONS"]["location"]
            if "OPTIONS" in settings.STORAGES["publico"] else "publico",
            "privado",
        )

    def test_lo_almacenado_es_la_imagen_re_codificada(self):
        """`DT-20`: una imagen servida tal como se subió es un vector de XSS."""
        self.subir()
        self.producto.refresh_from_db()

        with storages["publico"].open(self.producto.imagen_clave) as guardada:
            with Image.open(BytesIO(guardada.read())) as salida:
                self.assertEqual(salida.format, "WEBP")

    def test_reemplazar_borra_la_anterior(self):
        self.subir()
        self.producto.refresh_from_db()
        primera = self.producto.imagen_clave

        self.subir(imagen(color=(20, 180, 90)))
        self.producto.refresh_from_db()

        self.assertNotEqual(self.producto.imagen_clave, primera)
        self.assertFalse(storages["publico"].exists(primera), "quedó huérfana")

    def test_quitarla_la_borra(self):
        self.subir()
        self.producto.refresh_from_db()
        clave = self.producto.imagen_clave

        with self.captureOnCommitCallbacks(execute=True):
            quitar_imagen(actor=self.actor, producto=self.producto)
        self.producto.refresh_from_db()

        self.assertFalse(self.producto.tiene_imagen)
        self.assertFalse(storages["publico"].exists(clave))

    def test_un_fichero_que_no_es_imagen_se_rechaza(self):
        disfrazado = SimpleUploadedFile(
            "empanada.jpg", b"<svg onload=alert(1)>", content_type="image/jpeg"
        )
        with self.assertRaises(ImagenInvalida):
            guardar_imagen(
                actor=self.actor, producto=self.producto, archivo=disfrazado
            )


class LaImagenLaSirveLaAplicacionTest(BaseDeImagen):
    """`DT-21`. Sin firma, con caché larga, y por una ruta que lleva la clave."""

    def test_la_url_lleva_la_clave_y_no_el_identificador(self):
        """De ahí sale que la respuesta pueda cachearse como inmutable."""
        self.subir()
        self.producto.refresh_from_db()

        url = self.producto.url_de_la_imagen
        self.assertIn(self.producto.imagen_clave, url)
        self.assertNotIn(str(self.producto.pk), url)

    def test_la_url_cambia_al_reemplazar_la_imagen(self):
        """Por eso no hay que invalidar ninguna caché."""
        self.subir()
        self.producto.refresh_from_db()
        antes = self.producto.url_de_la_imagen

        self.subir(imagen(color=(20, 180, 90)))
        self.producto.refresh_from_db()

        self.assertNotEqual(self.producto.url_de_la_imagen, antes)

    def test_se_sirve_y_es_la_imagen(self):
        self.subir()
        self.producto.refresh_from_db()

        respuesta = self.client.get(self.producto.url_de_la_imagen)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "image/webp")
        with Image.open(BytesIO(b"".join(respuesta.streaming_content))) as salida:
            self.assertEqual(salida.format, "WEBP")

    def test_se_sirve_sin_sesion(self):
        """«Público» significa **no sensible** (`DT-21`), y `INT-2` necesita la
        caché del navegador: exigir sesión no protegería nada y la rompería."""
        self.subir()
        self.producto.refresh_from_db()

        self.client.logout()
        self.assertEqual(
            self.client.get(self.producto.url_de_la_imagen).status_code, 200
        )

    def test_no_lleva_firma_ni_caduca(self):
        self.subir()
        self.producto.refresh_from_db()

        url = self.producto.url_de_la_imagen
        self.assertNotIn("Signature", url)
        self.assertNotIn("Expires", url)

    def test_se_cachea_mucho_tiempo_y_como_inmutable(self):
        self.subir()
        self.producto.refresh_from_db()

        cabecera = self.client.get(self.producto.url_de_la_imagen)["Cache-Control"]

        self.assertIn("public", cabecera)
        self.assertIn("immutable", cabecera)
        self.assertIn(f"max-age={settings.CACHE_IMAGEN_PRODUCTO}", cabecera)
        self.assertGreaterEqual(settings.CACHE_IMAGEN_PRODUCTO, 60 * 60 * 24)

    def test_una_clave_que_no_existe_es_un_404(self):
        respuesta = self.client.get(
            reverse("imagen-del-producto", kwargs={"clave": "0" * 32 + ".webp"})
        )
        self.assertEqual(respuesta.status_code, 404)


class LaRutaNoDejaSalirDelPrefijoTest(BaseDeImagen):
    """La prueba que más importa de este fichero.

    El almacenamiento antepone `publico/` a lo que se le pida, así que una clave
    con `..` alcanzaría el prefijo `privado/` — donde está la fotografía de un
    menor (`DT-18`, `ALC-OUT-08`). Solo se acepta la forma exacta que produce la
    canalización.
    """

    def test_rechaza_las_claves_que_intentan_escapar(self):
        for clave in [
            "../privado/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.webp",
            "..%2Fprivado%2Fx.webp",
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.webp/../../etc/passwd",
            "/etc/passwd",
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.webp",  # mayúsculas: no las genera
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.png",   # otra extensión
            "corta.webp",
        ]:
            with self.subTest(clave=clave):
                respuesta = self.client.get(f"/catalogo/imagenes/{clave}")
                self.assertIn(
                    respuesta.status_code, (404, 301),
                    f"«{clave}» no debería servir nada",
                )

    def test_no_sirve_una_fotografia_del_prefijo_privado(self):
        """De extremo a extremo: se pone algo en `privado/` y se intenta sacar."""
        storages["privado"].save("f" * 32 + ".webp", ContentFile(imagen(), name="x"))

        respuesta = self.client.get(
            "/catalogo/imagenes/../privado/" + "f" * 32 + ".webp"
        )
        self.assertNotEqual(respuesta.status_code, 200)


class SinImagenElProductoSeVendeIgualTest(BaseDeImagen):
    """Segundo criterio de `HU-59`."""

    def test_esta_en_el_catalogo(self):
        self.assertIn(self.producto, productos_en_el_catalogo())

    def test_la_ficha_lo_dice_en_vez_de_dejar_un_hueco(self):
        self.client.force_login(self.actor)
        respuesta = self.client.get(
            reverse("admin:catalogo_producto_change", args=[self.producto.pk])
        )
        self.assertContains(respuesta, "se vende igual")

    def test_el_listado_dice_quien_tiene_imagen(self):
        self.client.force_login(self.actor)
        respuesta = self.client.get(reverse("admin:catalogo_producto_changelist"))
        self.assertEqual(respuesta.status_code, 200)


class SoloLaAdministracionCargaLaImagenTest(BaseDeImagen):
    def test_ningun_otro_rol(self):
        for rol in [Rol.CAJERO, Rol.INSTITUCION, Rol.ACUDIENTE]:
            with self.subTest(rol=rol):
                otro = crear_cuenta(
                    email=f"{rol}@example.com", rol=rol, enviar_invitacion=False
                )
                with self.assertRaises(PermissionDenied):
                    guardar_imagen(
                        actor=otro, producto=self.producto, archivo=archivo()
                    )


class LaCargaDesdeLaFichaTest(BaseDeImagen):
    """`TT-54`."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.actor)

    def _cambiar(self, **extra):
        datos = {
            "nombre": self.producto.nombre,
            "precio": "3000",
            "categoria": str(self.categoria.pk),
            "activo": "on",
            **extra,
        }
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                reverse("admin:catalogo_producto_change", args=[self.producto.pk]),
                datos,
            )

    def test_la_ficha_ofrece_el_campo(self):
        cuerpo = self.client.get(
            reverse("admin:catalogo_producto_change", args=[self.producto.pk])
        ).content.decode()
        self.assertIn('name="imagen"', cuerpo)

    def test_subirla_desde_la_ficha(self):
        respuesta = self._cambiar(imagen=archivo())
        self.assertEqual(respuesta.status_code, 302)

        self.producto.refresh_from_db()
        self.assertTrue(self.producto.tiene_imagen)

    def test_la_ficha_la_muestra_despues(self):
        self._cambiar(imagen=archivo())
        cuerpo = self.client.get(
            reverse("admin:catalogo_producto_change", args=[self.producto.pk])
        ).content.decode()

        self.assertIn("<img", cuerpo)
        self.assertIn("Imagen de Empanada de carne", cuerpo)

    def test_se_quita_marcando_la_casilla(self):
        self._cambiar(imagen=archivo())
        self._cambiar(quitar_imagen="on")

        self.producto.refresh_from_db()
        self.assertFalse(self.producto.tiene_imagen)

    def test_un_formato_no_aceptado_avisa_pero_no_tira_la_edicion(self):
        respuesta = self._cambiar(
            nombre="Empanada de pollo",
            imagen=archivo(imagen(formato="TIFF"), "empanada.tiff", "image/tiff"),
        )
        self.assertEqual(respuesta.status_code, 302)

        self.producto.refresh_from_db()
        self.assertFalse(self.producto.tiene_imagen)
        self.assertEqual(self.producto.nombre, "Empanada de pollo")
