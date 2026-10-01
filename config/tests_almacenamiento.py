"""Pruebas de la firma contra la dirección pública (`DT-37`).

Prefirmar es un cálculo local: ninguna de estas pruebas habla con el servidor S3. Lo que
fijan es **qué host queda dentro de la firma**, que es lo que decide si el
navegador puede abrir la fotografía de un estudiante.
"""

import pickle
from urllib.parse import parse_qs, urlsplit

from django.test import SimpleTestCase

from config.almacenamiento import AlmacenamientoS3

INTERNA = "http://seaweedfs:8333"
PUBLICA = "http://localhost:9000"


def _almacenamiento(**opciones):
    return AlmacenamientoS3(
        bucket_name="smartfood",
        endpoint_url=INTERNA,
        access_key="smartfood",
        secret_key="smartfood-local",
        region_name="auto",
        addressing_style="path",
        location="privado",
        querystring_expire=300,
        **opciones,
    )


class FirmaContraLaDireccionPublicaTest(SimpleTestCase):
    def test_con_direccion_publica_firma_contra_ella(self):
        url = _almacenamiento(endpoint_url_publico=PUBLICA).url("foto.webp")

        partes = urlsplit(url)
        self.assertEqual(f"{partes.scheme}://{partes.netloc}", PUBLICA)
        self.assertEqual(partes.path, "/smartfood/privado/foto.webp")

    def test_sigue_firmada_y_con_su_caducidad(self):
        """`custom_domain` también cambiaría el host, pero quitaría la firma:
        la fotografía de un menor no sale sin ella (`DEC-8`, `DT-18`)."""
        url = _almacenamiento(endpoint_url_publico=PUBLICA).url("foto.webp")

        consulta = parse_qs(urlsplit(url).query)
        self.assertIn("X-Amz-Signature", consulta)
        self.assertEqual(consulta["X-Amz-Expires"], ["300"])

    def test_sin_direccion_publica_se_comporta_como_s3storage(self):
        """La aplicación en el host y las pruebas no la definen."""
        url = _almacenamiento().url("foto.webp")

        self.assertTrue(url.startswith(f"{INTERNA}/smartfood/privado/foto.webp?"))

    def test_se_puede_serializar_despues_de_firmar(self):
        """Django copia los almacenamientos; un cliente de boto3 no se serializa."""
        almacenamiento = _almacenamiento(endpoint_url_publico=PUBLICA)
        almacenamiento.url("foto.webp")

        copia = pickle.loads(pickle.dumps(almacenamiento))

        self.assertTrue(copia.url("foto.webp").startswith(PUBLICA))

    def test_los_ajustes_usan_esta_clase_en_los_dos_alias(self):
        from django.conf import settings

        for alias in ("privado", "publico"):
            with self.subTest(alias=alias):
                self.assertEqual(
                    settings.STORAGES[alias]["BACKEND"],
                    "config.almacenamiento.AlmacenamientoS3",
                )
