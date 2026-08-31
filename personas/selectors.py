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
