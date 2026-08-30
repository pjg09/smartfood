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

from django.core.management.base import BaseCommand

from personas.services import dar_de_alta_la_institucion

# La institución de referencia del prototipo. El nombre es inventado y el
# dominio de correo es `example.edu.co`, reservado por la RFC 2606 justamente
# para esto: nunca corresponde a un buzón real.
INSTITUCION_NOMBRE = "Colegio San Bartolomé de Prueba"
INSTITUCION_EMAIL = "secretaria@example.edu.co"


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

    def handle(self, *args, **opciones):
        institucion, creada = dar_de_alta_la_institucion(
            nombre=opciones["nombre_institucion"],
            email=opciones["email_institucion"],
        )

        if creada:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Institución «{institucion.nombre}» creada. "
                    f"Invitación enviada a {institucion.usuario.email}."
                )
            )
        else:
            self.stdout.write(
                f"La institución «{institucion.nombre}» ya existía "
                f"({institucion.usuario.email}). No se reenvía la invitación."
            )
