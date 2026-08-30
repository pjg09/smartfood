"""Escrituras del dominio de usuarios, roles, invitaciones y sesión.

**Toda escritura pasa por aquí** (`DT-15`). Reglas que no se negocian:

1. Una vista nunca escribe directamente: llama a una función de este módulo.
2. Cada función abre su propia `transaction.atomic()`.
3. Estas funciones **no saben de HTTP**: no reciben `request`, no devuelven
   `HttpResponse` y no leen `request.user` —el usuario se pasa como argumento—.

Funciones, no clases.
"""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from config.correo import enviar_correo
from cuentas.models import Rol, Usuario


def construir_enlace_de_invitacion(usuario):
    """Devuelve la URL absoluta con la que el titular define su contraseña.

    Reutiliza el generador de tokens de Django en lugar de inventar uno. No es
    pereza: `CLAUDE.md` descarta explícitamente construir autenticación propia,
    y este generador ya invalida el token en cuanto la contraseña cambia y
    caduca solo (`PASSWORD_RESET_TIMEOUT`). `TT-18` revisa ambas propiedades;
    aquí se usan, no se dan por decididas.
    """
    ruta = reverse(
        "definir-contrasena",
        kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(usuario.pk)),
            "token": default_token_generator.make_token(usuario),
        },
    )
    return f"{settings.URL_BASE.rstrip('/')}{ruta}"


def invitar(usuario):
    """Manda al titular la invitación con la que definirá su contraseña.

    No escribe nada, pero vive entre los servicios porque es el efecto que
    acompaña a toda alta de cuenta (`HU-39`, `HU-41`, `HU-03`) y las vistas no
    deben construirlo por su cuenta.

    El envío se difiere hasta que la transacción confirme (`config/correo.py`):
    invitar a alguien cuya alta se revirtió es mandarle un enlace a una cuenta
    que no existe.
    """
    enviar_correo(
        destinatario=usuario.email,
        asunto="Te damos acceso a SmartFood",
        plantilla="correo/invitacion",
        contexto={
            "nombre": usuario.nombre or usuario.email,
            "rol": usuario.get_rol_display(),
            "enlace": construir_enlace_de_invitacion(usuario),
            "dias_de_validez": settings.PASSWORD_RESET_TIMEOUT // (60 * 60 * 24),
        },
    )


@transaction.atomic
def crear_cuenta(*, email, rol, nombre="", accede_a_administracion=False,
                 contrasena_de_desarrollo=None):
    """Crea una cuenta **sin contraseña utilizable** y la invita.

    `INV-6` e `INVD-1`: ninguna cuenta nace de un autorregistro, y quien la crea
    no llega a conocer nunca la clave del titular (`DEC-3`).

    `contrasena_de_desarrollo` es la **única excepción**, y está acotada por
    `DEC-10`: fija una clave conocida y **no envía invitación**. Existe solo para
    la cuenta institucional del prototipo, que nadie va a activar por correo
    porque su dirección no es de nadie. Su nombre es largo a propósito: quien lo
    escriba tiene que saber lo que está haciendo.

    **No lo uses para cuentas de acudiente ni de personal.** Ahí la invitación
    es el mecanismo, y `HU-41` exige que quien crea la cuenta no conozca la
    clave.
    """
    usuario = Usuario.objects.crear_usuario(
        email=email,
        rol=rol,
        nombre=nombre,
        is_staff=accede_a_administracion,
    )

    if contrasena_de_desarrollo:
        usuario.set_password(contrasena_de_desarrollo)
        usuario.save(update_fields=["password"])
        return usuario

    invitar(usuario)
    return usuario


@transaction.atomic
def reenviar_invitacion(usuario):
    """Vuelve a mandar la invitación a quien todavía no definió su contraseña."""
    if usuario.tiene_contrasena_definida:
        raise ValueError("Esa cuenta ya tiene contraseña: no procede una invitación.")
    invitar(usuario)


__all__ = ["Rol", "crear_cuenta", "invitar", "reenviar_invitacion", "construir_enlace_de_invitacion"]
