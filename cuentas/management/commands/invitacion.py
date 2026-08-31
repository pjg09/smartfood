"""`manage.py invitacion <correo>` — imprime el enlace de invitación de una cuenta.

`DEC-9` dice que la carga masiva **genera** las invitaciones pero no las
entrega, y que `HU-03` se demuestra «tomando el enlace de un acudiente cargado y
definiendo la contraseña con él». Este comando es ese «tomar».

**Por qué un comando y no una pantalla.** El enlace es una credencial: quien lo
tiene puede fijar la contraseña de esa cuenta. Listarlos en el resultado de la
carga dejaría a la institución con la llave de todas las cuentas de acudiente, y
eso contradice de hecho `DEC-3` e `INVD-1`, cuyo valor es que quien crea la
cuenta **no llega a conocer la clave del titular**. Desde la terminal, sacar un
enlace es un acto deliberado, uno a uno y sobre una cuenta concreta.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from cuentas.models import Usuario
from cuentas.services import generar_invitacion


class Command(BaseCommand):
    help = (
        "Imprime el enlace de invitación de una cuenta que todavía no definió su "
        "contraseña (DEC-9, HU-03)."
    )

    def add_arguments(self, parser):
        parser.add_argument("correo", help="Correo de la cuenta.")

    def handle(self, *args, **opciones):
        correo = opciones["correo"]

        usuario = Usuario.objects.filter(email__iexact=correo).first()
        if usuario is None:
            raise CommandError(
                f"No hay ninguna cuenta con el correo «{correo}». "
                "Las cuentas nacen de un alta institucional, no de un registro (INV-6)."
            )

        if not usuario.is_active:
            raise CommandError(
                f"La cuenta «{usuario.email}» está desactivada y no puede activarse "
                "por invitación (HU-42)."
            )

        try:
            enlace = generar_invitacion(usuario)
        except ValueError as error:
            raise CommandError(str(error)) from error

        dias = settings.PASSWORD_RESET_TIMEOUT // (60 * 60 * 24)
        self.stdout.write(f"Cuenta:  {usuario.email} ({usuario.get_rol_display()})")
        self.stdout.write(f"Enlace:  {enlace}")
        self.stdout.write(
            self.style.WARNING(
                "Es una credencial de un solo uso: caduca, y deja de valer en cuanto "
                f"el titular define su contraseña. Vive {dias} días "
                "(DJANGO_CADUCIDAD_INVITACION)."
            )
        )
