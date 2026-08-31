"""Lecturas del dominio de institución educativa, estudiantes y acudientes.

**Toda lectura no trivial pasa por aquí** (`DT-15`). Como los servicios, estos
selectores no conocen `request`: reciben lo que necesitan como argumentos y
devuelven objetos del ORM o datos, nunca respuestas HTTP.
"""

from django.core.exceptions import PermissionDenied

from cuentas.models import Rol
from personas.models import Estudiante


def estudiantes_a_cargo(*, usuario):
    """Los estudiantes de un acudiente (`TT-29`, `HU-04`, primer criterio).

    **Una cuenta de acudiente puede tener varios estudiantes vinculados**, y esa
    es toda la consulta: el vínculo vive en `Estudiante.acudiente` (`TT-21`), y
    un acudiente con tres hijos matriculados los ve desde una sola cuenta.

    **El filtro es la autorización.** No se consultan todos los estudiantes para
    después esconder los ajenos: la consulta solo alcanza los propios. Es lo que
    pide `DT-11` —los permisos van en la capa de datos, no en un botón que se
    oculta—, y hace imposible que otro rol vea a menores por esta vía.
    """
    if usuario is None or not usuario.is_authenticated:
        raise PermissionDenied("Los estudiantes a cargo son de un acudiente identificado.")
    if usuario.rol != Rol.ACUDIENTE:
        raise PermissionDenied(
            "Solo el acudiente consulta sus estudiantes a cargo (HU-04, [S11])."
        )
    if not usuario.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")

    return Estudiante.objects.filter(acudiente__usuario=usuario).order_by("nombre")


def estudiante_a_cargo(*, usuario, estudiante_id):
    """Uno de los estudiantes del acudiente, o `Estudiante.DoesNotExist`.

    Se apoya en `estudiantes_a_cargo`, así que un identificador de un estudiante
    ajeno **no se distingue de uno inexistente**: ninguno de los dos está en el
    conjunto que la consulta alcanza. Es la propiedad que se quiere — probar
    identificadores no revela si existen.
    """
    return estudiantes_a_cargo(usuario=usuario).get(pk=estudiante_id)


def estudiante_para_la_institucion(*, actor, estudiante_id):
    """Un estudiante, para quien administra la institución (`TT-36`, `HU-45`).

    `HU-45` es de `USR-5`: consultar el código de tarjeta vigente para producir
    la tarjeta que le corresponde. Ningún otro rol pasa por aquí — el acudiente
    tiene `estudiante_a_cargo`, que filtra por los suyos —, y la comprobación
    está en el selector porque es donde vive la regla (`DT-15`, `[S11]`).

    Lanza `Estudiante.DoesNotExist` si no existe.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Consultar la ficha de un estudiante exige identificarse.")
    if actor.rol != Rol.INSTITUCION:
        raise PermissionDenied(
            "Consultar el código de tarjeta es función de la institución educativa "
            "(HU-45, [S11])."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")

    return Estudiante.objects.select_related("acudiente").get(pk=estudiante_id)
