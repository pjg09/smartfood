#!/usr/bin/env bash
# Arranque de la aplicación en el servidor de las exposiciones (DEC-27, DT-61).
#
# El de desarrollo (`arrancar-aplicacion.sh`) sirve con `runserver` y deja las
# hojas al servicio `estilos`. Aquí no hay `estilos`: las hojas se compilan una
# vez, antes de `collectstatic`, que es quien las publica con su hash.
set -euo pipefail

python manage.py tailwind build --force
python manage.py estilos_del_admin

python manage.py migrate --noinput
python manage.py sincronizar_permisos --verbosity 0

# Idempotente (DEC-10): en cada arranque deja las cuentas como estaban.
if [ -n "${SEMBRAR_CONTRASENA:-}" ]; then
    python manage.py sembrar \
        --contrasena-de-desarrollo "$SEMBRAR_CONTRASENA" \
        --estudiantes "${SEMBRAR_ESTUDIANTES:-12}"
fi

python manage.py collectstatic --noinput --verbosity 0

# El registro va a la salida estándar (`config/settings.py`), y con él el de
# acceso: `docker compose logs app` es todo lo que hay que mirar.
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-5}" \
    --timeout 60 \
    --access-logfile -
