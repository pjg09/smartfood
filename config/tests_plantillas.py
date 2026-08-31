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
