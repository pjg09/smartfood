"""Lecturas del dominio de usuarios, roles, invitaciones y sesión.

**Toda lectura no trivial pasa por aquí** (`DT-15`). Como los servicios, estos
selectores no conocen `request`: reciben lo que necesitan como argumentos y
devuelven objetos del ORM o datos, nunca respuestas HTTP.
"""

from django.core.exceptions import PermissionDenied
from django.db.models import Q

from cuentas.models import Rol, Usuario
from cuentas.services import ROLES_DE_PERSONAL


def personal_de_la_cafeteria(*, actor, busqueda=""):
    """Las cuentas de cajero y de administración de la cafetería (`DT-45`).

    La lista de `/usuarios/`. **Ni acudientes ni la institución**, y no por
    estética: sobre los acudientes la institución tiene su propia pantalla
    (`DEC-17`) y sus cuentas nacen de la carga (`HU-01`); la cuenta de la
    institución no se gestiona desde ningún sitio (`DEC-10`). Lo que aquí se
    administra es el personal: alta (`HU-40`), invitación (`HU-41`) y acceso
    (`HU-42`), los mismos `ROLES_DE_PERSONAL` que aceptan esos servicios.

    **Exclusivo de la institución**, y la comprobación va aquí y no en la vista
    (`DT-11`): es la lista de quién puede cobrar y quién administra el
    inventario, con sus correos.

    Las desactivadas salen siempre: son pocas y reactivarlas es justo lo que se
    viene a hacer aquí.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Consultar el personal exige identificarse.")
    if actor.rol != Rol.INSTITUCION:
        raise PermissionDenied(
            "El personal de la cafetería solo lo gestiona la institución educativa."
        )
    if not actor.is_active:
        raise PermissionDenied(
            "Tu cuenta está desactivada. Pide a la institución educativa que la reactive."
        )

    personal = Usuario.objects.filter(rol__in=ROLES_DE_PERSONAL)

    busqueda = busqueda.strip()
    if busqueda:
        personal = personal.filter(
            Q(nombre__icontains=busqueda) | Q(email__icontains=busqueda)
        )

    return personal.order_by("nombre", "email")
