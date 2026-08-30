"""Envío de correo del sistema (`TT-06`).

Vive en `config/` porque es infraestructura, no dominio: lo usan `cuentas` y
`personas` por igual, y ninguna de las dos lo posee.

**La razón de que exista este módulo y no se llame a `send_mail` directamente**
es la regla de abajo. Sin ella, cada camino de escritura que mande un correo
tiene que acordarse de aplicarla, y el fallo solo aparece cuando algo va mal.
"""

import logging

from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string

registro = logging.getLogger(__name__)


def enviar_correo(*, destinatario, asunto, plantilla, contexto):
    """Encola un correo para enviarlo **cuando la transacción confirme**.

    `transaction.on_commit` no es un detalle: los servicios escriben dentro de
    `transaction.atomic()` (`DT-15`), y un correo enviado dentro de la
    transacción sale aunque esta acabe deshaciéndose. En `HU-03` eso significa
    invitar a un acudiente cuya carga se revirtió: recibe un enlace para
    activar una cuenta que no existe. El correo no se puede «deshacer».

    Fuera de una transacción, `on_commit` ejecuta de inmediato, así que llamar a
    esta función desde cualquier sitio es seguro.

    La plantilla se busca en dos versiones: `<plantilla>.txt` obligatoria y
    `<plantilla>.html` opcional. El texto plano no es cortesía — hay clientes
    de correo que no muestran HTML, y una invitación que no se lee es una
    cuenta que no se activa.
    """
    cuerpo_texto = render_to_string(f"{plantilla}.txt", contexto)

    try:
        cuerpo_html = render_to_string(f"{plantilla}.html", contexto)
    except Exception:  # noqa: BLE001 — la versión HTML es opcional
        cuerpo_html = None

    def _enviar():
        mensaje = EmailMultiAlternatives(
            subject=asunto,
            body=cuerpo_texto,
            to=[destinatario],
        )
        if cuerpo_html:
            mensaje.attach_alternative(cuerpo_html, "text/html")

        # Un fallo de correo no puede tumbar la operación que ya se confirmó:
        # la cuenta quedó creada. Se registra para poder reenviar la invitación.
        enviados = mensaje.send(fail_silently=True)
        if not enviados:
            registro.error(
                "No se pudo enviar el correo «%s» a %s", asunto, destinatario
            )

    transaction.on_commit(_enviar)
