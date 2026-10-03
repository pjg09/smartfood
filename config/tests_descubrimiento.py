"""Toda prueba escrita es una prueba que se ejecuta.

`manage.py test` se corre sin argumentos, en local y en el script de
comprobación desde cero (`[S5.3]` de docs/desarrollo.md): la suite no se enumera en ninguna parte, y una prueba nueva entra sola **si el
descubridor la encuentra**. Hay dos formas de que no la encuentre, y ninguna
avisa —la suite sale en verde con una prueba menos—:

1. **El fichero no casa con `test*.py`**, el patrón por defecto del ejecutor de
   Django. `pruebas_caja.py` o `caja_tests.py` no se importan nunca.
2. **La carpeta no es un paquete.** El descubrimiento de `unittest` solo baja a
   directorios con `__init__.py`: un `ventas/pruebas/tests_caja.py` sin él se
   salta entero.

Esto lo vigila con el código fuente, sin ejecutar nada.
"""

import ast
import fnmatch
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

RAIZ = Path(settings.BASE_DIR)
PATRON = "test*.py"  # el de `DiscoverRunner`; el proyecto no lo cambia
IGNORADOS = {".venv", ".git", "node_modules", "staticfiles", "migrations", "__pycache__"}
BASES_DE_PRUEBA = {"TestCase", "SimpleTestCase", "TransactionTestCase", "LiveServerTestCase"}


def _ficheros_del_proyecto():
    for fichero in RAIZ.rglob("*.py"):
        relativo = fichero.relative_to(RAIZ)
        if not IGNORADOS.intersection(relativo.parts):
            yield relativo


def _define_pruebas(ruta):
    """Si el fichero declara una clase que hereda de una base de pruebas."""
    arbol = ast.parse((RAIZ / ruta).read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ClassDef):
            for base in nodo.bases:
                nombre = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
                if nombre in BASES_DE_PRUEBA:
                    return True
    return False


def _con_pruebas():
    return [ruta for ruta in _ficheros_del_proyecto() if _define_pruebas(ruta)]


class DescubrimientoTest(SimpleTestCase):
    def test_la_busqueda_encuentra_las_pruebas_de_hoy(self):
        """Contraprueba: si la búsqueda no encontrara nada, las dos de abajo
        pasarían solas el día que dejaran de proteger."""
        encontrados = {str(ruta) for ruta in _con_pruebas()}

        self.assertIn("config/tests_descubrimiento.py", encontrados)
        self.assertIn("ventas/tests_venta.py", encontrados)
        self.assertGreater(len(encontrados), 50)

    def test_todo_fichero_con_pruebas_casa_con_el_patron(self):
        fuera = [str(r) for r in _con_pruebas() if not fnmatch.fnmatch(r.name, PATRON)]

        self.assertFalse(
            fuera,
            f"Estos ficheros declaran pruebas que nunca se ejecutan: {fuera}. "
            f"Renómbralos a `tests_<tema>.py`.",
        )

    def test_toda_carpeta_con_pruebas_es_un_paquete(self):
        sin_paquete = set()
        for ruta in _con_pruebas():
            for carpeta in list(ruta.parents)[:-1]:  # sin la raíz
                if not (RAIZ / carpeta / "__init__.py").is_file():
                    sin_paquete.add(str(carpeta))

        self.assertFalse(
            sin_paquete,
            f"Estas carpetas no tienen `__init__.py` y el descubridor no entra: "
            f"{sorted(sin_paquete)}",
        )
