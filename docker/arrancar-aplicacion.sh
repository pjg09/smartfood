#!/bin/sh
# Arranque del servicio `app` de `compose.yaml` (DT-37).
#
# Todo lo que antes era un comando suelto antes de `runserver`. Cada paso es
# idempotente: se repite en cada arranque sin duplicar nada.
set -eu

# Una migración sin aplicar no falla al arrancar: falla al abrir la pantalla que
# la usa. Aquí no puede quedarse ninguna.
python manage.py migrate --noinput

# Los permisos de un modelo nuevo no existen hasta que su tabla está creada, y
# sin ellos el admin responde 403 (TT-15, INV-4).
python manage.py sincronizar_permisos --verbosity 0

# `sembrar` es idempotente (TT-08): la primera vez crea la institución, el
# personal, las familias y el catálogo; las siguientes no duplican nada y solo
# restablecen las contraseñas del seed. Sin contraseña, no siembra.
if [ -n "${SEMBRAR_CONTRASENA:-}" ]; then
    python manage.py sembrar \
        --contrasena-de-desarrollo "$SEMBRAR_CONTRASENA" \
        --estudiantes "${SEMBRAR_ESTUDIANTES:-12}"
fi

# `runserver` no lo necesita —con DEBUG sirve desde `assets/`—, pero las pruebas
# sí: el ejecutor fuerza DEBUG=False y el almacenamiento con manifiesto responde
# «Missing staticfiles manifest entry» en cada plantilla que cite una hoja. Las
# hojas ya están: `estilos` tiene que estar sano antes de que esto arranque.
python manage.py collectstatic --noinput --verbosity 0

exec python manage.py runserver 0.0.0.0:8000
