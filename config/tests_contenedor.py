"""El `compose.yaml` y el `Dockerfile` no se quedan atrás (`DT-37`).

El stack tiene que levantar con `docker compose up` en cualquier máquina, y lo
que lo rompe casi nunca es tocar esos dos ficheros: es tocar **otro** —una
variable obligatoria nueva en los ajustes, un comando renombrado, la versión de
Python— y no acordarse de ellos. Estas pruebas vigilan esa deriva sin Docker,
con la suite de siempre. Lo que solo se ve levantando el stack de verdad lo
vigila el flujo `integracion-continua` de la CI.
"""

import ast
import re
from pathlib import Path

from django.conf import settings
from django.core.management import get_commands, load_command_class
from django.test import SimpleTestCase

RAIZ = Path(settings.BASE_DIR)


def _texto(nombre):
    return (RAIZ / nombre).read_text(encoding="utf-8")


def _entorno_de_la_aplicacion():
    """Las variables del bloque `x-aplicacion` de `compose.yaml`: las que ven
    `app` y `estilos`. Sin PyYAML —no es dependencia del proyecto— y sin
    necesidad: el bloque es plano."""
    compose = _texto("compose.yaml")
    bloque = re.search(r"^x-aplicacion:.*?(?=^\S)", compose, re.S | re.M)
    assert bloque, "compose.yaml ya no tiene el bloque x-aplicacion"
    entorno = re.search(r"^  environment:\n(.*?)(?=^  \S|\Z)", bloque.group(0), re.S | re.M)
    assert entorno, "el bloque x-aplicacion ya no tiene environment"
    return dict(re.findall(r"^    ([A-Z0-9_]+): *(.*)$", entorno.group(1), re.M))


def _variables_obligatorias_de_los_ajustes():
    """Las que `config/settings.py` lee con `env(…)` sin `default=`."""
    arbol = ast.parse(_texto("config/settings.py"))
    con_esquema = set()   # las declaradas en `environ.Env(X=(tipo, defecto))`
    obligatorias = set()
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        funcion = nodo.func
        if isinstance(funcion, ast.Attribute) and funcion.attr == "Env":
            con_esquema |= {k.arg for k in nodo.keywords}
            continue
        es_env = (isinstance(funcion, ast.Name) and funcion.id == "env") or (
            isinstance(funcion, ast.Attribute)
            and isinstance(funcion.value, ast.Name)
            and funcion.value.id == "env"
        )
        if not es_env or not nodo.args or not isinstance(nodo.args[0], ast.Constant):
            continue
        if not any(k.arg == "default" for k in nodo.keywords):
            obligatorias.add(nodo.args[0].value)
    return obligatorias - con_esquema


class ComposeAlDiaTest(SimpleTestCase):
    def test_la_deteccion_encuentra_las_obligatorias_de_hoy(self):
        """Contraprueba: si el análisis no encontrara nada, la prueba de abajo
        pasaría sola el día que dejara de proteger."""
        self.assertLessEqual(
            {"DJANGO_SECRET_KEY", "DATABASE_URL"}, _variables_obligatorias_de_los_ajustes()
        )
        self.assertNotIn("S3_BUCKET", _variables_obligatorias_de_los_ajustes())

    def test_toda_variable_obligatoria_esta_en_el_compose(self):
        """Sin ella, Django no arranca dentro del contenedor —y en el host sí,
        porque ahí la pone `.env`, que es por lo que nadie lo notaría—."""
        faltan = _variables_obligatorias_de_los_ajustes() - set(_entorno_de_la_aplicacion())
        self.assertFalse(
            faltan,
            f"config/settings.py exige {sorted(faltan)} y compose.yaml no las da "
            "en x-aplicacion.environment",
        )

    def test_los_servicios_se_alcanzan_por_la_red_de_compose(self):
        """Dentro del contenedor, `localhost` es el propio contenedor."""
        entorno = _entorno_de_la_aplicacion()
        for variable in ("DATABASE_URL", "S3_ENDPOINT_URL"):
            with self.subTest(variable=variable):
                self.assertNotRegex(entorno[variable], r"localhost|127\.0\.0\.1")
        # La única que va a localhost es la que usa el navegador.
        self.assertIn("localhost", entorno["S3_ENDPOINT_URL_PUBLICO"])

    def test_sin_conexiones_persistentes_bajo_runserver(self):
        """`runserver` abre un hilo por petición y cada uno dejaría su conexión
        abierta: el healthcheck agotó las 100 de PostgreSQL en veinte minutos."""
        self.assertIn("runserver", _texto("docker/arrancar-aplicacion.sh"))
        self.assertEqual(_entorno_de_la_aplicacion().get("DJANGO_CONN_MAX_AGE"), '"0"')


class DockerfileAlDiaTest(SimpleTestCase):
    def test_python_de_la_imagen_es_el_de_python_version(self):
        version = _texto(".python-version").strip()
        imagen = re.search(r"^FROM python:(\d+\.\d+)", _texto("Dockerfile"), re.M)

        self.assertIsNotNone(imagen, "el Dockerfile ya no parte de la imagen oficial de Python")
        self.assertEqual(imagen.group(1), version)

    def test_la_imagen_no_lleva_el_env(self):
        """La imagen no lleva credenciales: las variables vienen del compose."""
        lineas = _texto(".dockerignore").splitlines()
        self.assertIn(".env", lineas)


class ScriptsDeArranqueAlDiaTest(SimpleTestCase):
    """Un comando renombrado rompe el arranque del contenedor, y en el host
    nadie lo corre a mano ya: nada más lo notaría."""

    SCRIPTS = ("docker/arrancar-aplicacion.sh", "docker/vigilar-estilos.sh")

    def test_los_scripts_que_se_citan_existen(self):
        citados = set(re.findall(r"docker/[a-z-]+\.sh", _texto("compose.yaml") + _texto("Dockerfile")))

        self.assertEqual(citados, set(self.SCRIPTS))
        for script in citados:
            with self.subTest(script=script):
                self.assertTrue((RAIZ / script).is_file())

    def test_los_comandos_que_llaman_existen(self):
        llamados = set()
        for script in self.SCRIPTS:
            llamados |= set(re.findall(r"manage\.py (\w+)", _texto(script)))

        self.assertIn("migrate", llamados)  # contraprueba de la expresión
        self.assertFalse(llamados - set(get_commands()), "un script llama a un comando que no existe")

    def test_sembrar_acepta_las_opciones_con_que_se_le_llama(self):
        comando = load_command_class(get_commands()["sembrar"], "sembrar")
        analizador = comando.create_parser("manage.py", "sembrar")

        opciones = analizador.parse_args(
            ["--contrasena-de-desarrollo", "x", "--estudiantes", "12"]
        )

        self.assertEqual(opciones.estudiantes, 12)
