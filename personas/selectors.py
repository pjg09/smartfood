"""Lecturas del dominio de institución educativa, estudiantes y acudientes.

**Toda lectura no trivial pasa por aquí** (`DT-15`). Como los servicios, estos
selectores no conocen `request`: reciben lo que necesitan como argumentos y
devuelven objetos del ORM o datos, nunca respuestas HTTP.
"""

from django.core.exceptions import PermissionDenied

from cuentas.models import Rol
from personas.codigo import ALFABETO, LONGITUD
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


def identificar_por_codigo_de_tarjeta(codigo):
    """El estudiante de una tarjeta escaneada (`TT-70`, `HU-15`).

    Devuelve el `Estudiante`, o lanza `Estudiante.DoesNotExist` si ese código no
    es de nadie.

    ── DEVUELVE TAMBIÉN AL QUE NO PUEDE COMPRAR, Y ESA ES LA DECISIÓN ───────
    Un estudiante de baja o desactivado (`INVD-2`) **se identifica igual**. La
    tentación es filtrarlo aquí y ahorrarse el caso, pero entonces el cajero ve
    «esa tarjeta no es de nadie», que es mentira: la tarjeta es correcta y el
    estudiante existe: lo que pasa es que no puede comprar.

    Con la fila delante, el punto de venta puede decir **por qué** —«se dio de
    baja el 3 de septiembre»— y la familia enterarse de algo que quizá no sabía.
    Sin ella, el cajero repite el escaneo tres veces y acaba mandando al
    estudiante a secretaría sin saber qué decirle.

    Quien impide la venta es `comprobar_que_puede_operar`, dentro de la
    transacción y con el bloqueo puesto (`DT-6`). **Identificar no es autorizar.**
    ─────────────────────────────────────────────────────────────────────────

    El código se normaliza antes de buscar: el lector es un teclado y puede
    añadir espacios o un salto de línea, y quien lo teclea a mano cuando el lector
    falla escribe en minúscula. Un código correcto que no encuentra a nadie por un
    espacio es el peor fallo posible en una fila de veinte minutos.

    **No autoriza a nadie**: como el resto de los selectores, no sabe quién
    pregunta. Que solo el cajero llegue aquí lo decide la vista del punto de venta
    (`TT-58`, `[S11]`).
    """
    normalizado = (codigo or "").strip().upper()

    # Se corta antes de consultar cuando la forma ni siquiera es la de un código
    # (`DT-9`, `INV-7`): un campo vacío, un pegote de cualquier cosa o el
    # resultado de un lector mal configurado. La base tiene la misma regla en una
    # `CheckConstraint`, así que ninguna fila puede tener otra forma y la consulta
    # sería un viaje seguro a cero resultados.
    if len(normalizado) != LONGITUD or any(c not in ALFABETO for c in normalizado):
        raise Estudiante.DoesNotExist("Ese código no tiene la forma de un código de tarjeta.")

    return Estudiante.objects.select_related("acudiente").get(codigo_tarjeta=normalizado)
