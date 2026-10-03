# syntax=docker/dockerfile:1
#
# Imagen de la aplicación Django para `compose.yaml` (DT-37).
#
# Es una imagen de DESARROLLO, no de producción: no hay entorno desplegado
# (DEC-15, DT-31). En `compose.yaml` el repositorio se monta encima de /app, así
# que lo que la imagen aporta de verdad son dos cosas que NO están en el
# repositorio: el entorno de Python con las dependencias exactas de `uv.lock` y
# el binario de Tailwind. El código que corre es siempre el de tu disco.
#
# Si cambias la versión de Python (`.python-version`), la de uv o la forma de
# instalar algo, cambia esto en el mismo PR. `config/tests_contenedor.py`
# vigila lo que se puede vigilar sin Docker; la comprobación desde cero de
# `[S5.3]` de docs/desarrollo.md levanta el stack entero. La CI ya no (DT-39).

# La versión menor tiene que ser la de `.python-version`.
FROM python:3.14.4-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /usr/local/bin/uv

# El entorno virtual vive FUERA de /app: el montaje del repositorio lo taparía,
# y el `.venv` del host está enlazado a un Python que aquí no existe.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_CACHE_DIR=/root/.cache/uv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TAILWIND_CLI_PATH=/opt/tailwind

WORKDIR /app

# Primero solo las dependencias: esta capa se reaprovecha mientras `uv.lock` no
# cambie, y cambiar código no reinstala nada.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# El binario de Tailwind, en la versión que fija `TAILWIND_CLI_VERSION` en los
# ajustes: se descarga con el propio comando para que la versión viva en un solo
# sitio. NO se copia el resto del código: llega montado, y copiarlo haría que
# cada cambio en una plantilla produjera una imagen nueva y recreara los
# contenedores en el siguiente `up`. De ahí los ajustes de construcción, que
# cargan Django sin las apps. La caché evita volver a descargarlo.
# Los ajustes exigen estas dos variables para cargar; aquí no se conecta a nada.
COPY config/__init__.py config/settings.py config/ajustes_de_construccion.py config/
RUN --mount=type=cache,target=/cache/tailwind \
    DJANGO_SETTINGS_MODULE=config.ajustes_de_construccion \
    DJANGO_SECRET_KEY=solo-para-construir-la-imagen \
    DATABASE_URL=postgres://nadie@localhost/nada \
    TAILWIND_CLI_PATH=/cache/tailwind \
    python -m django tailwind download_cli \
 && mkdir -p /opt/tailwind \
 && cp /cache/tailwind/tailwindcss-* /opt/tailwind/ \
 && chmod -R a+rx /opt/tailwind \
 && rm -rf /app/config

# El contenedor corre con el usuario del host (`user:` en `compose.yaml`) para
# que lo que escribe en el repositorio —las hojas compiladas— sea tuyo. Ese
# usuario no existe en la imagen y no tiene casa.
ENV HOME=/tmp

EXPOSE 8000

# Sin CMD a propósito: el arranque es `docker/arrancar-aplicacion.sh`, que está
# en el repositorio montado y no en la imagen. Lo declara `compose.yaml`.
