"""El admin, entero en español.

Hay **dos problemas distintos** y por eso hay dos catálogos propios:

1. **Lo que Django deja sin traducir.** Django 6.1 estrenó o renombró cinco
   cadenas del admin y sus catálogos españoles las devuelven en inglés, así que
   en una pantalla por lo demás en español aparecían «Run»,
   «- Select an option -», «Search» y «Filter by». Cuatro se arreglan con
   `locale/es/`; la quinta, el `alt` del icono de la lupa, está escrita a pelo en
   la plantilla de Django y obligó a sustituirla.
2. **Lo que Django traduce mal.** El catálogo `es_CO` capitaliza los doce meses,
   así que el formato de fecha de Colombia salía «19 de Septiembre de 2026» en
   mitad de una frase, y traduce «View %s» como «Vista %s», que es un sustantivo
   donde va un verbo. Eso se corrige en `locale/es_CO/`, **y tiene que ser ahí**:
   con `LANGUAGE_CODE = "es-co"` el catálogo que manda es el `es_CO` y el `es`
   solo es la reserva, así que una corrección escrita en `es` no ganaría.

**Estas pruebas vigilan las tres cosas que se rompen solas:**

1. Que las traducciones sigan aplicándose. Un `LOCALE_PATHS` mal puesto, o un
   `.mo` sin recompilar tras tocar el `.po`, y las cadenas vuelven al inglés sin
   que nada falle.
2. Que ninguno de los dos parches crezca hasta convertirse en una traducción
   propia del admin, que se desincronizaría a la primera versión.
3. Que la plantilla copiada no se quede vieja. Está anclada a Django 6.1: si la
   suya cambia, la nuestra sigue sirviendo el marcado antiguo **en silencio**.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import django
from django.test import TestCase
from django.urls import reverse
from django.utils import formats
from django.utils.dates import MONTHS
from django.utils.translation import gettext

from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from personas.services import dar_de_alta_la_institucion
from ventas.models import CierreDeCaja

PLANTILLA_DE_DJANGO = (
    Path(django.__file__).parent
    / "contrib/admin/templates/admin/search_form.html"
)
NUESTRA_PLANTILLA = Path(__file__).resolve().parent.parent / (
    "templates/admin/search_form.html"
)
RAIZ = Path(__file__).resolve().parent.parent
CATALOGO_ES = RAIZ / "locale/es/LC_MESSAGES/django.po"
CATALOGO_ES_CO = RAIZ / "locale/es_CO/LC_MESSAGES/django.po"


def entradas_de(catalogo):
    """Los `msgid` de un `.po`, sin la cabecera —que es un `msgid ""` vacío
    obligatorio—."""
    return [
        linea
        for linea in catalogo.read_text().splitlines()
        if linea.startswith("msgid ") and linea != 'msgid ""'
    ]


class ElCatalogoPropioTraduceLoQueDjangoNoTest(TestCase):
    """Se comprueba la traducción, no el fichero: lo que importa es lo que sale."""

    def test_las_cinco_cadenas_estan_en_espanol(self):
        esperado = {
            "- Select an option -": "- Seleccione una opción -",
            "Run": "Ejecutar",
            "Search": "Buscar",
            "Search %(name)s": "Buscar %(name)s",
            "Filter by %(field_name)s": "Filtrar por %(field_name)s",
        }
        for original, traduccion in esperado.items():
            with self.subTest(cadena=original):
                self.assertEqual(gettext(original), traduccion)

    def test_no_se_traduce_nada_que_django_ya_traduzca(self):
        """El catálogo propio es un parche, no una traducción del admin.

        Si crece, es señal de que alguien empezó a traducir por su cuenta lo que
        Django ya trae — y eso se queda desincronizado a la primera versión.
        """
        entradas = entradas_de(CATALOGO_ES)

        self.assertEqual(len(entradas), 5, f"el parche creció: {entradas}")


class ElCatalogoDeColombiaCorrigeLoQueDjangoTraduceMalTest(TestCase):
    """El otro parche, y el que **no podría vivir en `locale/es/`**.

    Con `LANGUAGE_CODE = "es-co"` el catálogo que manda es el `es_CO` y el `es`
    solo es la reserva: una corrección escrita en `es` la pisaría el catálogo de
    Django. Por eso hay dos ficheros y no uno, y por eso esta prueba comprueba
    **lo que sale**, no dónde está escrito.
    """

    def test_los_doce_meses_van_en_minuscula(self):
        """En español el nombre del mes va en minúscula. El catálogo `es` de
        Django lo hace bien; el `es_CO` los capitaliza los doce.

        Es la misma regla que `CLAUDE.md` fija para nuestras plantillas —donde se
        arregla con `|lower`—, aplicada a lo que pinta el admin, que era la única
        parte del producto que no la cumplía.
        """
        for numero, nombre in MONTHS.items():
            with self.subTest(mes=numero):
                self.assertEqual(str(nombre), str(nombre).lower())

    def test_la_fecha_del_admin_sale_en_minuscula(self):
        """Contra el formato de verdad, que es donde se veía el defecto.

        El `DATE_FORMAT` de `es_CO` escribe «día de MES de año», así que el mes
        va en mitad de la frase: comprobar solo la tabla `MONTHS` dejaría pasar
        un cambio de formato que volviera a capitalizarlo.
        """
        self.assertEqual(
            formats.date_format(date(2026, 9, 19), "DATE_FORMAT"),
            "19 de septiembre de 2026",
        )

    def test_el_titulo_de_una_ficha_de_solo_lectura_es_un_verbo(self):
        """«Vista cierre de caja» encabezaba la ficha del reporte de cierres.

        Es el título de cualquier ficha que no se puede editar: los tres
        reportes de la cafetería y las restricciones por estudiante.
        """
        self.assertEqual(gettext("View %s") % "cierre de caja", "Ver cierre de caja")

    def test_no_se_corrige_nada_que_ninguna_pantalla_imprima(self):
        """Los días de la semana vienen igual de capitalizados y **no se tocan**.

        Ninguna pantalla del proyecto los imprime, y cada entrada de más es una
        que hay que revisar al subir de versión de Django. Trece: los doce meses
        y el título de la ficha.
        """
        entradas = entradas_de(CATALOGO_ES_CO)

        self.assertEqual(len(entradas), 13, f"el parche creció: {entradas}")

    def test_lo_que_django_ya_traduce_bien_no_se_toca(self):
        """La contraprueba de los dos parches juntos: si alguien empezara a
        traducir el admin por su cuenta, esto sería lo primero que cambiaría."""
        for original, traduccion in (
            ("Home", "Inicio"),
            ("Save", "Grabar"),
            ("Delete", "Eliminar"),
        ):
            with self.subTest(cadena=original):
                self.assertEqual(gettext(original), traduccion)


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


class LosReportesConNavegacionPorFechasSeVenEnEspanolTest(TestCase):
    """Contra la pantalla donde se vieron los dos defectos.

    Los tres reportes de la cafetería son las únicas pantallas con
    `date_hierarchy`, así que son las únicas que imprimían «Filter by» y las
    únicas donde el mes capitalizado se leía en un enlace. Se comprueban sobre
    el de cierres, que los tiene los dos —el rótulo y los enlaces de día—.
    """

    def setUp(self):
        sincronizar_grupos_y_permisos()
        administracion = crear_cuenta(
            email="administracion-traducciones@example.com",
            rol=Rol.ADMINISTRADOR,
            nombre="Administración",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.client.force_login(administracion)
        cajero = Usuario.objects.crear_usuario(
            email="cajero-traducciones@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        # Un cierre de una jornada conocida: sin filas, el admin no dibuja los
        # enlaces de día y no habría mes que comprobar.
        CierreDeCaja.objects.create(
            fecha=date(2026, 9, 19),
            cajero=cajero,
            base=Decimal("50000"),
            efectivo_esperado=Decimal("10000"),
            efectivo_contado=Decimal("60000"),
        )
        self.cuerpo = self.client.get(
            reverse("admin:ventas_cierredecaja_changelist")
        ).content.decode()

    def test_el_rotulo_de_la_navegacion_por_fechas_esta_en_espanol(self):
        self.assertIn("Filtrar por jornada", self.cuerpo)
        self.assertNotIn("Filter by", self.cuerpo)

    def test_los_enlaces_de_fecha_llevan_el_mes_en_minuscula(self):
        self.assertIn("septiembre", self.cuerpo)
        self.assertNotIn("Septiembre", self.cuerpo)


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
