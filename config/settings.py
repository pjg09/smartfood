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

APPS_DE_TERCEROS = [
    # Gestiona el binario autónomo de Tailwind: `manage.py tailwind build` y
    # `tailwind watch`. Sin Node y sin package.json (TT-05, DT-16).
    "django_tailwind_cli",
]

APPS_DEL_PROYECTO = [
    "cuentas",
    "personas",
    "catalogo",
]

INSTALLED_APPS = APPS_DE_DJANGO + APPS_DE_TERCEROS + APPS_DEL_PROYECTO

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
        # `templates`, no `plantillas`: el cargador de apps de Django busca el
        # subdirectorio "templates" y no es configurable. Nombrar distinto al
        # del proyecto dejaría dos convenciones en el mismo repositorio.
        "DIRS": [BASE_DIR / "templates"],
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

# Modelo de usuario propio, fijado ANTES de la primera migración (TT-09). El
# correo es la identidad: es por donde llega la invitación, y no hay ningún
# camino de alta que no pase por ella (DEC-3, INVD-1).
AUTH_USER_MODEL = "cuentas.Usuario"

# TT-18. Cuánto vive el enlace de una invitación, en segundos.
#
# Siete días: una invitación que llega un viernes tiene que seguir sirviendo el
# lunes, y el titular puede estar de vacaciones. Más allá de una semana el
# enlace deja de ser una invitación y pasa a ser una credencial olvidada en una
# bandeja de entrada; si caduca, se reenvía desde la vista de cuentas (TT-17).
#
# El token es además **de un solo uso**: Django lo construye a partir del hash
# de la contraseña actual, así que definirla lo invalida. Cambiar el correo o
# iniciar sesión también. Las tres propiedades tienen caso de prueba.
PASSWORD_RESET_TIMEOUT = env.int("DJANGO_CADUCIDAD_INVITACION", default=60 * 60 * 24 * 7)

# `TT-56` (`DEC-12`). La pantalla de acceso común a los cuatro roles.
#
# **No apunta a `/admin/login/`, y no puede hacerlo**: ese formulario exige
# `is_staff`, y `USR-2` no accede a la administración porque `INT-1` no es el
# admin (`DT-2`). Con él, un `@login_required` en la interfaz del acudiente lo
# manda a una pantalla que va a rechazarlo siempre.
#
# La ruta no es un camino de alta: `INV-6` e `INVD-1` siguen enteras y las
# rutas de registro no existen (`DT-10`).
LOGIN_URL = "acceso"

# Tras entrar y tras salir, la portada. Es lo que reparte por rol, y así ningún
# rol aterriza en una pantalla que no le corresponde.
LOGIN_REDIRECT_URL = "inicio"
LOGOUT_REDIRECT_URL = "inicio"

# Base absoluta para los enlaces que viajan por correo. Un enlace de invitación
# no puede ser relativo: se abre desde el cliente de correo, no desde el sitio.
URL_BASE = env(
    "DJANGO_URL_BASE",
    default=f"https://{DOMINIO_PUBLICO}" if DOMINIO_PUBLICO else "http://localhost:8000",
)

# --- Registro (logging) ---------------------------------------------------

# Sin esto, un error 500 en el entorno desplegado NO DEJA RASTRO. La
# configuración por defecto de Django manda `django.request` al manejador
# `mail_admins`, y con `ADMINS` vacío ese manejador descarta el mensaje en
# silencio: el usuario ve un 500 y en los registros no hay ni una línea.
#
# Costó un diagnóstico a ciegas descubrirlo. Todo va a la salida estándar, que
# es donde el PaaS recoge los registros.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detallado": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "consola": {
            "class": "logging.StreamHandler",
            "formatter": "detallado",
        },
    },
    "root": {
        "handlers": ["consola"],
        "level": env("DJANGO_NIVEL_DE_REGISTRO", default="INFO"),
    },
    "loggers": {
        # La traza completa de cada 500, en la salida estándar.
        "django.request": {
            "handlers": ["consola"],
            "level": "ERROR",
            "propagate": False,
        },
        # Ruidoso y sin valor: una petición por cada fichero estático.
        "django.server": {
            "handlers": ["consola"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# --- Correo (TT-06) -------------------------------------------------------

# Una sola variable describe el envío entero, igual que DATABASE_URL describe la
# base: mismo formato en local y en el entorno desplegado (DT-13).
#
#   local        consolemail://                 (imprime el correo por consola)
#   desplegado   smtp+tls://usuario:clave@host:587
#
# Por defecto, consola: nadie necesita credenciales para desarrollar, y ningún
# correo sale de una máquina de desarrollo por accidente.
EMAIL_CONFIG = env.email_url("EMAIL_URL", default="consolemail://")

EMAIL_BACKEND = EMAIL_CONFIG["EMAIL_BACKEND"]
EMAIL_HOST = EMAIL_CONFIG.get("EMAIL_HOST", "")
EMAIL_PORT = EMAIL_CONFIG.get("EMAIL_PORT", 25)
EMAIL_HOST_USER = EMAIL_CONFIG.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = EMAIL_CONFIG.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = EMAIL_CONFIG.get("EMAIL_USE_TLS", False)
EMAIL_USE_SSL = EMAIL_CONFIG.get("EMAIL_USE_SSL", False)

# Sin tiempo límite, un servidor de correo que no responde deja colgado un
# trabajador de gunicorn hasta que el sistema operativo corte la conexión. Con
# dos trabajadores, dos correos así dejan la aplicación sin atender a nadie.
EMAIL_TIMEOUT = env.int("DJANGO_EMAIL_TIMEOUT", default=10)

DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="SmartFood <onboarding@resend.dev>",
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# --- Internacionalización -------------------------------------------------

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos ---------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "assets"]

# --- Tailwind (TT-05, DT-16) ----------------------------------------------

# Versión fijada, no "latest": una construcción reproducible no puede depender
# de lo que hubiera publicado GitHub esa mañana.
TAILWIND_CLI_VERSION = "4.3.3"
# La fuente vive fuera de STATICFILES_DIRS a propósito: dentro, collectstatic
# la recogería y el backend con manifiesto fallaría al resolver su
# `@import "tailwindcss"`. El paquete lo avisa con su check W001.
TAILWIND_CLI_SRC_CSS = BASE_DIR / "estilos" / "fuente.css"
TAILWIND_CLI_DIST_CSS = "css/tailwind.css"
TAILWIND_CLI_PATH = BASE_DIR / ".tailwind"

# --- Almacenamiento de objetos (TT-50, DT-18, DT-21) ----------------------

# La base guarda la CLAVE del objeto, nunca el binario (DT-18).
#
# Dos almacenamientos lógicos, `privado` y `publico`, sobre UN bucket con dos
# prefijos. No son dos buckets porque los de Railway son privados sin excepción
# —no existe modo público en ningún plan— y el plan gratuito además permite uno
# por proyecto (DT-21). Como en el código son dos alias distintos, pasar a dos
# buckets el día que haga falta es cambiar estas rutas, no rediseñar nada.
#
# `publico` no significa accesible sin credenciales: significa «no sensible».
# Las imágenes de producto se sirven a través de la aplicación con caché larga;
# las fotografías de estudiantes, con URL firmada de caducidad corta.

S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", default="")
S3_BUCKET = env("S3_BUCKET", default="smartfood")

_s3_comun = {
    "bucket_name": S3_BUCKET,
    "endpoint_url": S3_ENDPOINT_URL,
    "access_key": env("S3_ACCESS_KEY_ID", default=""),
    "secret_key": env("S3_SECRET_ACCESS_KEY", default=""),
    "region_name": env("S3_REGION", default="auto"),
    "file_overwrite": False,
    "querystring_auth": True,
    "addressing_style": env("S3_ADDRESSING_STYLE", default="path"),
}

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # Comprime y versiona cada fichero con un hash del contenido, de modo
        # que se puedan cachear indefinidamente sin servir uno viejo.
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    # Fotografías de estudiantes (HU-57). URL firmada y de caducidad corta: la
    # fotografía de un menor no puede quedar en una URL adivinable ni en una que
    # siga sirviendo meses después (DEC-8, ALC-OUT-08).
    "privado": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_s3_comun,
            "location": "privado",
            "querystring_expire": env.int("S3_CADUCIDAD_FIRMA", default=300),
        },
    },
    # Imágenes de producto (HU-59). No son sensibles, pero el bucket sigue
    # siendo privado: las sirve la aplicación (DT-21).
    "publico": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_s3_comun,
            "location": "publico",
        },
    },
}

# Cuánto puede cachear el navegador una imagen de producto. Son inmutables: la
# clave del objeto cambia al reemplazar la imagen, así que no hay que invalidar
# nada y el punto de venta (INT-2) no vuelve a descargar el catálogo entero en
# cada pintado.
CACHE_IMAGEN_PRODUCTO = env.int("DJANGO_CACHE_IMAGEN_PRODUCTO", default=60 * 60 * 24 * 30)

# --- Canalización de subida (TT-55, DT-20) --------------------------------

IMAGEN_TAMANO_MAXIMO_BYTES = env.int("IMAGEN_TAMANO_MAXIMO_BYTES", default=5 * 1024 * 1024)
IMAGEN_LADO_MAXIMO = env.int("IMAGEN_LADO_MAXIMO", default=1600)
IMAGEN_CALIDAD = env.int("IMAGEN_CALIDAD", default=82)

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
