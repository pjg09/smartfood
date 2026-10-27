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


# Un identificador del proyecto: `HU-26`, `INV-8`, `DEC-6`, `ALC-IN-18`, `[S11]`…
IDENTIFICADOR = re.compile(r"\b(HU|ALC-IN|ALC-OUT|DEC|DT|INVD|INV|TT|USR|INT|ENT|DoD)-\d+|\[S\d+(\.\d+)*\]")


def _texto_servido(texto):
    """La plantilla sin sus comentarios: lo que puede llegar al navegador."""
    for patron in (r"{% comment %}.*?{% endcomment %}", r"{#.*?#}", r"<!--.*?-->"):
        texto = re.sub(patron, lambda m: "\n" * m.group(0).count("\n"), texto, flags=re.S)
    return texto


class NingunaPlantillaEnsenaIdentificadoresTest(TestCase):
    """`DT-62`. Los identificadores son del equipo, no de quien usa la
    aplicación: «(HU-26)» en un estado vacío no le dice nada a un acudiente.
    Viven en los comentarios, que no se sirven."""

    def test_el_texto_servido_no_cita_identificadores(self):
        encontrados = []
        for plantilla in sorted(RAIZ.rglob("*.html")):
            servido = _texto_servido(plantilla.read_text(encoding="utf-8"))
            for numero, linea in enumerate(servido.splitlines(), 1):
                if IDENTIFICADOR.search(linea):
                    encontrados.append(f"{plantilla.relative_to(RAIZ)}:{numero}: {linea.strip()}")
        self.assertEqual(encontrados, [], "\n".join(encontrados))

    def test_la_deteccion_ve_un_identificador_fuera_de_un_comentario(self):
        """Contraprueba: el mismo texto, dentro y fuera de un comentario."""
        self.assertTrue(IDENTIFICADOR.search(_texto_servido("Lo trae (<strong>HU-26</strong>).")))
        self.assertFalse(IDENTIFICADOR.search(_texto_servido("{% comment %} HU-26 {% endcomment %}")))


class NingunaPlantillaEscribeUnColorSueltoTest(TestCase):
    """El sistema de diseño se sostiene solo si nada lo esquiva (`DT-23`).

    `estilos/fuente.css` es **el único fichero donde puede aparecer un color
    literal**. La regla no se cumple sola: escribir `bg-[#1a375c]` en una
    plantilla funciona, no da ningún aviso, y a la tercera pantalla la paleta
    vuelve a ser lo que cada quien tuviera a mano. Esta prueba es lo que lo
    impide.

    **Una sola excepción**, `correo/base.html`: los clientes de correo
    descartan las variables CSS y las hojas externas, así que un token ahí no
    resolvería a nada. Es la cáscara de los dos correos —invitación y
    recuperación (`HU-62`)—, y por eso los colores siguen en un solo fichero.

    `admin/base_site.html` **dejó de ser la segunda** (`DT-36`). Lo era porque
    el admin no podía cargar Tailwind —su `preflight` lo desarmaba—, así que
    llevaba los colores copiados a mano; ahora carga `estilos/admin.css`, que es
    Tailwind sin `preflight`, y los toma de `estilos/tokens.css` como todo lo
    demás.
    """

    EXCEPCIONES = {"correo/base.html"}

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
