"""Siembra los datos de arranque del prototipo.

Vive en `personas` porque la institución es lo primero que siembra, pero es
**transversal**: `TT-08` lo amplía con estudiantes, acudientes y catálogo a
medida que aparezcan sus modelos. Aquí está su esqueleto, como indica `[S4]` del
sprint backlog.

**Es idempotente.** Se ejecuta al levantar el entorno, después de un despliegue
y mientras se desarrolla: no puede duplicar filas ni reenviar invitaciones en
cada pasada.

Todo lo que siembra es ficticio (`ALC-OUT-07`, `DoD-6`).
"""

import secrets
import string

from django.core.management.base import BaseCommand

from personas.services import dar_de_alta_la_institucion

# Centinela: distingue «no se pidió contraseña» de «se pidió sin dar valor».
GENERAR = object()


def generar_contrasena(longitud=24):
    """Clave fuerte y aleatoria. No hay ninguna por defecto en el código.

    Una contraseña escrita en el repositorio es una contraseña filtrada: acaba
    en el historial de git para siempre y nadie se acuerda de cambiarla.
    """
    alfabeto = string.ascii_letters + string.digits + "-_"
    return "".join(secrets.choice(alfabeto) for _ in range(longitud))

# La institución de referencia del prototipo. El nombre es inventado y el
# dominio es `example.com`, que la RFC 2606 reserva y nadie puede registrar.
#
# Corrige lo que decía TT-10: allí se usaba `example.edu.co` afirmando que la
# RFC lo reservaba. No es cierto —la RFC reserva example.com/net/org y los TLD
# .test e .invalid—, y `example.edu.co` es un subdominio de `edu.co` que alguien
# podría registrar. Un correo dirigido ahí podría llegarle a un tercero.
INSTITUCION_NOMBRE = "Colegio San Bartolomé de Prueba"
INSTITUCION_EMAIL = "institucion@example.com"


class Command(BaseCommand):
    help = "Siembra la institución de referencia y dispara su invitación (HU-39, TT-10)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email-institucion",
            default=INSTITUCION_EMAIL,
            help=(
                "Correo de la cuenta institucional. Útil para dirigir la invitación "
                "a un buzón real al demostrar HU-39."
            ),
        )
        parser.add_argument(
            "--nombre-institucion",
            default=INSTITUCION_NOMBRE,
            help="Nombre de la institución de referencia.",
        )
        parser.add_argument(
            "--contrasena-de-desarrollo",
            nargs="?",
            const=GENERAR,
            default=None,
            metavar="CLAVE",
            help=(
                "DEC-10. Fija una contraseña conocida en la cuenta institucional y "
                "NO envía invitación. Sin valor, genera una fuerte y la imprime una "
                "sola vez. Solo para la cuenta institucional del prototipo: las de "
                "acudiente y personal se activan por correo (HU-41, HU-03)."
            ),
        )

    def handle(self, *args, **opciones):
        contrasena = opciones["contrasena_de_desarrollo"]
        if contrasena is GENERAR:
            contrasena = generar_contrasena()

        institucion, creada = dar_de_alta_la_institucion(
            nombre=opciones["nombre_institucion"],
            email=opciones["email_institucion"],
            contrasena_de_desarrollo=contrasena,
        )

        if creada:
            self.stdout.write(self.style.SUCCESS(f"Institución «{institucion.nombre}» creada."))
        else:
            self.stdout.write(f"La institución «{institucion.nombre}» ya existía.")

        if contrasena:
            self.stdout.write(f"  cuenta     : {institucion.usuario.email}")
            self.stdout.write(self.style.WARNING(f"  contraseña : {contrasena}"))
            self.stdout.write(
                "  Se muestra UNA vez y no se guarda en claro en ninguna parte. "
                "Anótala donde corresponda (docs/desarrollo.md)."
            )
            self.stdout.write("  No se envió invitación por correo (DEC-10).")
        elif creada:
            self.stdout.write(f"  Invitación enviada a {institucion.usuario.email}.")
        else:
            self.stdout.write("  No se reenvía la invitación.")
