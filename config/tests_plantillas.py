"""Que las anotaciones de las plantillas no salgan al navegador.

**Defecto encontrado al construir `TT-56`, corregido aquí.** Las plantillas de
este proyecto llevan comentarios largos que citan identificadores (`TT-05`,
`DT-16`, `INT-1`) y explican por qué cada cosa está donde está. Se escribieron
con la sintaxis `{# … #}`, que Django **solo reconoce dentro de una línea**: un
bloque de varias líneas no es un comentario, es texto, y viajaba entero dentro
del HTML servido.

No era cosmético. Iba en `templates/correo/invitacion.html`, es decir, dentro
del correo que `HU-41` y `HU-39` mandan a un buzón real, y ese es el correo que
se le enseña a la docente. La corrección es mecánica —`{% comment %}`— y esta
prueba impide que vuelva, que es lo que importa: la sintaxis equivocada no da
ningún error, solo funciona mal en silencio.
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase

RAIZ = Path(settings.BASE_DIR) / "templates"


def _comentarios_multilinea(texto):
    """Devuelve los bloques `{# … #}` que abarcan más de una línea."""
    encontrados, i = [], 0
    while True:
        ini = texto.find("{#", i)
        if ini == -1:
            return encontrados
        fin = texto.find("#}", ini)
        if fin == -1:
            return encontrados
        bloque = texto[ini : fin + 2]
        if "\n" in bloque:
            encontrados.append(bloque.splitlines()[0])
        i = fin + 2


class NingunComentarioSeSirveAlNavegadorTest(TestCase):
    def test_no_hay_comentarios_multilinea_con_la_sintaxis_de_una_linea(self):
        plantillas = sorted(RAIZ.rglob("*.html"))
        self.assertGreater(len(plantillas), 0, "no se encontró ninguna plantilla")

        culpables = {
            str(p.relative_to(RAIZ)): _comentarios_multilinea(p.read_text())
            for p in plantillas
        }
        culpables = {p: c for p, c in culpables.items() if c}

        self.assertEqual(
            culpables,
            {},
            "`{# … #}` solo comenta dentro de una línea: estos bloques se "
            "renderizan dentro del HTML servido. Usa `{% comment %}`.",
        )

    def test_la_portada_no_lleva_dentro_su_propia_anotacion(self):
        """La comprobación de arriba, vista desde el resultado."""
        cuerpo = self.client.get("/").content.decode()
        self.assertNotIn("TT-05", cuerpo)
        self.assertNotIn("DT-16", cuerpo)


class NingunaPlantillaEscribeUnColorSueltoTest(TestCase):
    """El sistema de diseño se sostiene solo si nada lo esquiva (`DT-23`).

    `estilos/fuente.css` es **el único fichero donde puede aparecer un color
    literal**. La regla no se cumple sola: escribir `bg-[#1a375c]` en una
    plantilla funciona, no da ningún aviso, y a la tercera pantalla la paleta
    vuelve a ser lo que cada quien tuviera a mano. Esta prueba es lo que lo
    impide.

    Dos excepciones, y las dos por el mismo motivo —no cargan la hoja de
    estilos, así que un token ahí no resolvería a nada—:

      · `correo/invitacion.html`: los clientes de correo descartan las
        variables CSS y las hojas externas.
      · `admin/base_site.html`: incluir Tailwind en el admin traería su
        `preflight` y desarmaría `INT-3` (`DT-2`).
    """

    EXCEPCIONES = {"correo/invitacion.html", "admin/base_site.html"}

    # `#abc` y `#aabbcc`, delimitados: así `href="#acceso"` o `#i-alerta` no
    # cuentan como color.
    HEXADECIMAL = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")

    # La paleta que Tailwind trae de fábrica. `--color-*: initial` la borra
    # entera, así que una clase de estas **no pinta nada**: el elemento se queda
    # sin color y no hay ningún error que lo delate. Es el fallo silencioso que
    # esta prueba existe para atrapar.
    PALETA_DE_FABRICA = re.compile(
        r"\b(?:bg|text|border|ring|from|to|via|fill|stroke|divide|outline|shadow)-"
        r"(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|"
        r"emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-"
        r"\d{2,3}\b"
    )

    def _plantillas(self):
        for ruta in sorted(RAIZ.rglob("*.html")):
            relativa = str(ruta.relative_to(RAIZ))
            if relativa not in self.EXCEPCIONES:
                yield relativa, ruta.read_text()

    def test_ninguna_plantilla_escribe_un_hexadecimal(self):
        culpables = {
            nombre: self.HEXADECIMAL.findall(texto)
            for nombre, texto in self._plantillas()
            if self.HEXADECIMAL.search(texto)
        }

        self.assertEqual(
            culpables,
            {},
            "los colores viven en `estilos/fuente.css`, con nombre de intención. "
            "Si hace falta uno que no está, lo que falta es el token.",
        )

    def test_ninguna_plantilla_usa_la_paleta_de_fabrica_de_tailwind(self):
        culpables = {
            nombre: self.PALETA_DE_FABRICA.findall(texto)
            for nombre, texto in self._plantillas()
            if self.PALETA_DE_FABRICA.search(texto)
        }

        self.assertEqual(
            culpables,
            {},
            "esas clases no existen en este proyecto (`--color-*: initial`): no "
            "pintan nada y no dan ningún error. Usa un alias de intención.",
        )
