"""Escrituras del dominio de institución educativa, estudiantes y acudientes.

**Toda escritura pasa por aquí** (`DT-15`). Reglas que no se negocian:

1. Una vista nunca escribe directamente: llama a una función de este módulo.
2. Cada función abre su propia `transaction.atomic()`.
3. Estas funciones **no saben de HTTP**.

Funciones, no clases.
"""

from django.db import transaction

from cuentas.models import Rol
from cuentas.services import crear_cuenta
from personas.models import Institucion


@transaction.atomic
def dar_de_alta_la_institucion(*, nombre, email):
    """Crea la institución de referencia con su cuenta, y la invita (`HU-39`).

    **Idempotente.** Si la institución ya existe, no crea otra ni reenvía la
    invitación: el seed se ejecuta más de una vez —al levantar el entorno, tras
    un despliegue, mientras se desarrolla— y no puede mandar un correo cada vez.
    Devuelve `(institucion, creada)`.

    La cuenta accede a la administración porque `INT-3` es el admin de Django
    (`DT-2`) y la institución es quien carga estudiantes desde allí. No se crea
    con `createsuperuser`: eso fijaría una contraseña que alguien conocería,
    contra `DEC-3` e `INVD-1`.
    """
    existente = Institucion.objects.select_related("usuario").first()
    if existente is not None:
        return existente, False

    usuario = crear_cuenta(
        email=email,
        rol=Rol.INSTITUCION,
        nombre=nombre,
        accede_a_administracion=True,
    )
    # La institución administra el sistema entero: es el actor con más permisos
    # del prototipo. La matriz fina la construye `TT-15`.
    usuario.is_superuser = True
    usuario.save(update_fields=["is_superuser"])

    institucion = Institucion.objects.create(nombre=nombre, usuario=usuario)
    return institucion, True
