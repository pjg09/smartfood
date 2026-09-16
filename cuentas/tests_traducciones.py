"""El admin, entero en español.

Django 6.1 estrenó o renombró cuatro cadenas del admin y su catálogo `es`
todavía las devuelve en inglés, así que en una pantalla por lo demás en español
aparecían «Run», «- Select an option -» y «Search». Tres se arreglan con el
catálogo propio de `locale/`; la cuarta, el `alt` del icono de la lupa, está
escrita a pelo en la plantilla de Django y obligó a sustituirla.

**Estas pruebas vigilan las dos cosas que se rompen solas:**

1. Que las traducciones sigan aplicándose. Un `LOCALE_PATHS` mal puesto, o un
   `.mo` sin recompilar tras tocar el `.po`, y las cadenas vuelven al inglés sin
   que nada falle.
2. Que la plantilla copiada no se quede vieja. Está anclada a Django 6.1: si la
   suya cambia, la nuestra sigue sirviendo el marcado antiguo **en silencio**.
"""

from pathlib import Path

import django
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import gettext

from cuentas.models import Rol, Usuario
from cuentas.services import sincronizar_grupos_y_permisos
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from personas.services import dar_de_alta_la_institucion

PLANTILLA_DE_DJANGO = (
    Path(django.__file__).parent
    / "contrib/admin/templates/admin/search_form.html"
)
NUESTRA_PLANTILLA = Path(__file__).resolve().parent.parent / (
    "templates/admin/search_form.html"
)


class ElCatalogoPropioTraduceLoQueDjangoNoTest(TestCase):
    """Se comprueba la traducción, no el fichero: lo que importa es lo que sale."""

    def test_las_cuatro_cadenas_estan_en_espanol(self):
        esperado = {
            "- Select an option -": "- Seleccione una opción -",
            "Run": "Ejecutar",
            "Search": "Buscar",
            "Search %(name)s": "Buscar %(name)s",
        }
        for original, traduccion in esperado.items():
            with self.subTest(cadena=original):
                self.assertEqual(gettext(original), traduccion)

    def test_no_se_traduce_nada_que_django_ya_traduzca(self):
        """El catálogo propio es un parche, no una traducción del admin.

        Si crece, es señal de que alguien empezó a traducir por su cuenta lo que
        Django ya trae — y eso se queda desincronizado a la primera versión.
        """
        catalogo = (
            Path(__file__).resolve().parent.parent
            / "locale/es/LC_MESSAGES/django.po"
        ).read_text()

        # Sin contar la cabecera, que es un `msgid ""` vacío obligatorio.
        entradas = [
            linea
            for linea in catalogo.splitlines()
            if linea.startswith("msgid ") and linea != 'msgid ""'
        ]

        self.assertEqual(len(entradas), 4, f"el parche creció: {entradas}")


class ElAdminSeVeEnteroEnEspanolTest(TestCase):
    """Contra la pantalla, que es donde se nota."""

    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo="clave-de-prueba-2026",
            )
        self.client.force_login(institucion.usuario)

        # **Hace falta al menos un estudiante.** El admin solo dibuja la barra de
        # acciones —el desplegable y su botón— cuando el listado tiene filas, así
        # que sobre un padrón vacío no habría nada que traducir y la prueba
        # pasaría sin comprobar nada.
        acudiente = Usuario.objects.crear_usuario(
            email="acudiente@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
        )
        ficha = Acudiente.objects.create(
            usuario=acudiente, nombre="Marta Ruiz Ochoa", documento="4310012345"
        )
        Estudiante.objects.create(
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001234501",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )

    def test_el_listado_no_tiene_ninguna_de_las_cuatro_en_ingles(self):
        cuerpo = self.client.get(
            reverse("admin:personas_estudiante_changelist")
        ).content.decode()

        for ingles in ["Select an option", ">Run<", 'value="Search"', 'alt="Search"']:
            with self.subTest(cadena=ingles):
                self.assertNotIn(ingles, cuerpo)

    def test_y_sí_tiene_las_traducidas(self):
        cuerpo = self.client.get(
            reverse("admin:personas_estudiante_changelist")
        ).content.decode()

        for espanol in ["Seleccione una opción", ">Ejecutar<", 'value="Buscar"']:
            with self.subTest(cadena=espanol):
                self.assertIn(espanol, cuerpo)


class LaPlantillaCopiadaSigueAlDiaTest(TestCase):
    """`DT-2` dice que no sustituimos plantillas de Django, y aquí se sustituye una.

    Se acepta por una palabra —el nombre accesible del buscador— y con esta
    prueba como condición: **la copia queda anclada a la versión de Django**, y si
    la suya cambia, la nuestra serviría el marcado antiguo sin que nada falle.

    Al subir de versión: se vuelve a copiar la de Django, se aplica el mismo
    cambio, y si para entonces ya la tradujeron, nuestro fichero se borra.
    """

    def test_solo_cambia_el_alt_del_icono(self):
        de_django = PLANTILLA_DE_DJANGO.read_text()
        nuestra = NUESTRA_PLANTILLA.read_text()
        # Se descarta nuestro comentario de cabecera, que Django no tiene.
        nuestra = nuestra.split("{% endcomment %}\n", 1)[1]

        esperada = de_django.replace(
            'alt="Search"', "alt=\"{% translate 'Search' %}\""
        )

        self.assertEqual(
            nuestra,
            esperada,
            "La plantilla de Django cambió: vuelve a copiarla, aplica el mismo "
            "cambio del `alt`, y si ya la tradujeron, borra la nuestra.",
        )
