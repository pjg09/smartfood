"""Comprobación de salud del entorno desplegado (`TT-04`).

Vive en `config/` y no en una app de dominio porque no es dominio: es
infraestructura. El PaaS la consulta en cada despliegue y no lo da por bueno
hasta que responde.

Comprueba **la conexión a la base de datos**, no solo que el proceso esté
vivo. Un servicio que arranca pero no alcanza la base gestionada es
exactamente el fallo que `TT-04` tiene que descartar, y sin esta consulta se
vería como un despliegue correcto.
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
