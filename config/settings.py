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

# El PaaS publica el dominio del servicio en una variable propia (TT-04). Se
# añade solo si existe, para no obligar a declararla en local.
DOMINIO_PUBLICO = env("RAILWAY_PUBLIC_DOMAIN", default="")
if DOMINIO_PUBLICO:
    # `healthcheck.railway.app` es la cabecera Host que envía la sonda de salud
    # del PaaS. Sin ella, la sonda recibe un 400 y el despliegue se marca como
    # fallido aunque la aplicación esté perfectamente viva.
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, DOMINIO_PUBLICO, "healthcheck.railway.app"]
    CSRF_TRUSTED_ORIGINS = [f"https://{DOMINIO_PUBLICO}"]

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
    # Sirve los estáticos en el entorno desplegado, donde no hay servidor web
    # delante (TT-04). Va justo detrás de SecurityMiddleware, como pide su
    # documentación, y antes que todo lo demás.
    "whitenoise.middleware.WhiteNoiseMiddleware",
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

# Reutilizar la conexión evita abrir una por petición contra la base gestionada,
# que está al otro lado de la red y no en localhost.
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DJANGO_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

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

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # Comprime y versiona cada fichero con un hash del contenido, de modo
        # que se puedan cachear indefinidamente sin servir uno viejo.
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# El almacenamiento de objetos para fotografías e imágenes (DT-18) se configura
# en TT-50 y TT-55, en PR-07: `default` pasará a apuntar a los buckets. Hasta
# entonces queda el sistema de archivos, que nadie usa todavía.

# --- Seguridad en el entorno desplegado (TT-04) ---------------------------

# Solo fuera de DEBUG. En local no hay HTTPS y activarlas rompería el
# desarrollo con redirecciones a https://localhost.
if not DEBUG:
    # El PaaS termina el TLS y reenvía por HTTP; sin esto Django cree que la
    # petición no es segura y entra en un bucle de redirección.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    # La sonda de salud llega por HTTP interno, sin pasar por el proxy que
    # añade X-Forwarded-Proto. Sin esta excepción recibiría un 301 y el PaaS
    # daría el despliegue por fallido con la aplicación funcionando.
    SECURE_REDIRECT_EXEMPT = [r"^salud/$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    X_FRAME_OPTIONS = "DENY"
