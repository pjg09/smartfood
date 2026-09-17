"""Comprobación de salud del proceso y su base de datos (`TT-04`, `DT-31`).

Vive en `config/` y no en una app de dominio porque no es dominio: es
infraestructura. La consultaba el PaaS en cada despliegue; `DT-31` retira ese
despliegue y la sonda se queda, porque lo que comprueba sigue valiendo: que
**la base de datos contesta**, no solo que el proceso esté vivo.

Un servicio que arranca pero no alcanza la base es el fallo que se ve como
correcto desde fuera, y el único que esta vista existe para descartar. En
local responde lo mismo contra el PostgreSQL del `docker compose`.
"""

from django.db import connection
from django.http import JsonResponse


def salud(request):
    """Responde 200 si la base de datos contesta, 503 si no."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as error:  # noqa: BLE001 — cualquier fallo es «no sano»
        return JsonResponse(
            {"estado": "degradado", "base_de_datos": str(error)},
            status=503,
        )

    return JsonResponse({"estado": "ok", "base_de_datos": "conectada"})
