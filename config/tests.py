"""Pruebas de la infraestructura del proyecto (`TT-06`).

No cubren dominio: cubren `config/`. La única regla que se comprueba aquí es la
que da sentido a `config/correo.py` —el correo espera a que la transacción
confirme— porque es una garantía que se rompe en silencio: si falla, nadie ve
un error, simplemente se invita a alguien cuya cuenta no llegó a existir.
"""

from django.core import mail
from django.db import transaction
from django.test import TestCase, override_settings

from config.correo import enviar_correo

PLANTILLAS_DE_PRUEBA = {
    "correo/prueba.txt": "Hola {{ nombre }}, esto es una prueba.",
}

CONFIGURACION_DE_PLANTILLAS = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "OPTIONS": {
            "loaders": [
                ("django.template.loaders.locmem.Loader", PLANTILLAS_DE_PRUEBA),
            ],
        },
    },
]


@override_settings(TEMPLATES=CONFIGURACION_DE_PLANTILLAS)
class EnviarCorreoTest(TestCase):
    def _enviar(self):
        enviar_correo(
            destinatario="acudiente@ejemplo.test",
            asunto="Invitación a SmartFood",
            plantilla="correo/prueba",
            contexto={"nombre": "Acudiente de prueba"},
        )

    def test_no_envia_nada_hasta_que_la_transaccion_confirma(self):
        """Dentro de una transacción abierta, el correo todavía no ha salido."""
        with transaction.atomic():
            self._enviar()
            self.assertEqual(len(mail.outbox), 0)

    def test_envia_cuando_la_transaccion_confirma(self):
        with self.captureOnCommitCallbacks(execute=True):
            self._enviar()

        self.assertEqual(len(mail.outbox), 1)
        mensaje = mail.outbox[0]
        self.assertEqual(mensaje.to, ["acudiente@ejemplo.test"])
        self.assertEqual(mensaje.subject, "Invitación a SmartFood")
        self.assertIn("Acudiente de prueba", mensaje.body)

    def test_no_envia_nada_si_la_transaccion_se_deshace(self):
        """La razón de ser de `config/correo.py`.

        Una carga masiva que falla a mitad (`HU-02`) no puede haber invitado ya
        a los acudientes de las filas que se revirtieron: recibirían un enlace
        para activar una cuenta inexistente, y un correo no se deshace.
        """
        class FalloDeLaCarga(Exception):
            pass

        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    self._enviar()
                    raise FalloDeLaCarga
            except FalloDeLaCarga:
                pass

        self.assertEqual(len(mail.outbox), 0)
