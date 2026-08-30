"""Ajustes de Django para SmartFood.

Un solo fichero de ajustes que lee del entorno (DT-13): el mismo código corre en
local y en el entorno desplegado, y lo que cambia son las variables. No hay
`settings/base.py` + `local.py` + `produccion.py`; esa división multiplica los
sitios donde mirar cuando algo no cuadra y no compra nada aquí.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, []),
)

# En local lee el `.env`; en el PaaS no existe y las variables vienen del entorno.
environ.Env.read_env(BASE_DIR / ".env")

# --- Núcleo ---------------------------------------------------------------

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# --- Aplicaciones ---------------------------------------------------------

# Una app por dominio. Aquí están solo las tres que toca el Sprint 1; billetera,
# inventario, ventas y reportes se crean en el sprint que las necesita.
APPS_DE_DJANGO = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

APPS_DEL_PROYECTO = [
    "cuentas",
    "personas",
    "catalogo",
]

INSTALLED_APPS = APPS_DE_DJANGO + APPS_DEL_PROYECTO

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # La plantilla base y el layout llegan con TT-05, en PR-04.
        "DIRS": [BASE_DIR / "plantillas"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Base de datos (DT-1) -------------------------------------------------

# Un único DATABASE_URL porque es el formato que entrega el PaaS en TT-04: la
# conexión se describe igual en local y en el entorno desplegado.
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

# DT-6 exige bloqueo pesimista en la venta (`select_for_update`), que necesita
# una transacción abierta. Los servicios abren la suya con `transaction.atomic()`
# (DT-15), así que aquí NO se activa ATOMIC_REQUESTS: envolver toda la petición
# escondería dónde empieza y acaba cada transacción.

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# NOTA (DT-17): la clave primaria de todas las tablas es UUIDv7 generado en la
# aplicación, no un autoincremental. Se declara en cada modelo con
# `uuid.uuid7` de la biblioteca estándar de Python 3.14. El ajuste de arriba
# solo cubre los modelos de `django.contrib`, que no son nuestros.

# --- Autenticación --------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# AVISO PARA TT-09 (PR-08), que declara el modelo de usuario con rol:
#
#   AUTH_USER_MODEL hay que fijarlo ANTES de la primera migración. Por eso este
#   PR no ejecuta `migrate`: si se crean las tablas de `django.contrib.auth` con
#   el usuario por defecto, cambiarlo después obliga a borrar la base a los
#   cuatro integrantes. Ver el README.

# --- Internacionalización -------------------------------------------------

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos ---------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# El almacenamiento de objetos para fotografías e imágenes (DT-18) se configura
# en TT-50 y TT-55, en PR-07. Hasta entonces no hay STORAGES personalizado.
