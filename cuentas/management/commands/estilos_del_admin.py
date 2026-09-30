"""Compila la segunda hoja de estilos: la del admin (`DT-36`).

**Son dos hojas y no una**, y el motivo es el `preflight` de Tailwind: la
aplicación lo quiere —es su reset— y el admin no puede tenerlo, porque
desarmaría los estilos con los que Django pinta sus 89 pantallas. Las dos
comparten `estilos/tokens.css`, así que un color de la marca sigue estando
escrito una sola vez.

`manage.py tailwind build` solo conoce la hoja que declara
`TAILWIND_CLI_SRC_CSS`. Esta llama al mismo binario —el que aquel ya descargó—
con la otra entrada.
"""

import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

ENTRADA = "estilos/admin.css"
SALIDA = "assets/css/admin.css"


def binario():
    """El ejecutable que `django-tailwind-cli` dejó en `TAILWIND_CLI_PATH`.

    No se descarga aquí: si no está, es que nadie ha corrido todavía
    `tailwind build`, y el mensaje lo dice en vez de fallar con un `FileNotFound`
    sobre una ruta que no le dice nada a nadie.
    """
    candidatos = sorted(settings.TAILWIND_CLI_PATH.glob("tailwindcss-*"))
    if not candidatos:
        raise CommandError(
            "No está el binario de Tailwind. Ejecuta antes "
            "`manage.py tailwind build`, que es quien lo descarga."
        )
    return candidatos[-1]


class Command(BaseCommand):
    help = "Compila estilos/admin.css, la hoja del admin sin preflight (DT-36)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch",
            action="store_true",
            help="Se queda recompilando cuando cambie una plantilla del admin.",
        )
        parser.add_argument(
            "--minify",
            action="store_true",
            help="Minifica, como hace `tailwind build` con la hoja principal.",
        )

    def handle(self, *args, **opciones):
        self.verbosidad = opciones["verbosity"]
        orden = [
            str(binario()),
            "--input", str(settings.BASE_DIR / ENTRADA),
            "--output", str(settings.BASE_DIR / SALIDA),
        ]
        if opciones["watch"]:
            orden.append("--watch")
        if opciones["minify"]:
            orden.append("--minify")

        resultado = subprocess.run(orden, capture_output=not opciones["watch"])
        if resultado.returncode:
            raise CommandError(
                (resultado.stderr or b"").decode() or "Tailwind falló sin decir por qué."
            )
        if self.verbosidad:
            self.stdout.write(self.style.SUCCESS(f"Hoja del admin compilada en {SALIDA}."))
