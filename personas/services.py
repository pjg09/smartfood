"""Escrituras del dominio de institución educativa, estudiantes y acudientes.

**Toda escritura pasa por aquí** (`DT-15`). Reglas que no se negocian:

1. Una vista nunca escribe directamente: llama a una función de este módulo.
2. Cada función abre su propia `transaction.atomic()`.
3. Estas funciones **no saben de HTTP**.

Funciones, no clases.
"""

from dataclasses import dataclass, field

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction

from cuentas.models import Rol
from cuentas.services import crear_cuenta, generar_invitacion
from personas.carga import leer
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante, Institucion
from personas.validacion import ArchivoInvalido, validar

# Cuántas veces se vuelve a intentar si el código sorteado ya existía (`DT-9`).
#
# Cinco es generoso hasta lo absurdo, y a propósito: con 2^70 combinaciones y un
# colegio de miles de estudiantes, la probabilidad de una sola colisión ya es del
# orden de 10^-15. Que haya cinco seguidas no va a ocurrir nunca. El reintento
# existe porque `DT-9` lo pide y porque la alternativa —confiar en que no pase—
# no es una garantía, no porque se espere usarlo.
INTENTOS_DE_CODIGO = 5


@transaction.atomic
def dar_de_alta_la_institucion(*, nombre, email, contrasena_de_desarrollo=None):
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
        # Restablecer la clave de desarrollo de una institución ya sembrada es
        # el caso de «se me olvidó» y de «acabo de recrear el entorno pero no la
        # base». Sigue sin enviar correo (`DEC-10`).
        if contrasena_de_desarrollo:
            existente.usuario.set_password(contrasena_de_desarrollo)
            existente.usuario.save(update_fields=["password"])
        return existente, False

    usuario = crear_cuenta(
        email=email,
        rol=Rol.INSTITUCION,
        nombre=nombre,
        accede_a_administracion=True,
        contrasena_de_desarrollo=contrasena_de_desarrollo,
    )
    # La institución administra el sistema entero: es el actor con más permisos
    # del prototipo. La matriz fina la construye `TT-15`.
    usuario.is_superuser = True
    usuario.save(update_fields=["is_superuser"])

    institucion = Institucion.objects.create(nombre=nombre, usuario=usuario)
    return institucion, True


@transaction.atomic
def crear_estudiante(*, actor, nombre, documento, acudiente):
    """Da de alta a un estudiante con su código de tarjeta (`TT-32`, `HU-43`).

    **El código se asigna aquí y en ningún otro sitio.** Primer criterio de
    `HU-43`: la asignación es automática al dar de alta al estudiante, sea por
    carga masiva o individual. Las dos entran por esta función, así que no hay
    un camino de alta que se olvide de generarlo. El admin de `HU-44` (`TT-33`)
    delega también aquí: el admin es una vista y una vista nunca escribe
    directamente (`DT-15`).

    **Solo la institución educativa** matricula estudiantes (`[S11]`). El actor
    llega como argumento: este servicio no sabe de HTTP.

    El reintento ante colisión es la mitad de `DT-9` que el índice único no
    puede cubrir. Cada intento va en su propio punto de guardado —el `atomic`
    interno— porque una `IntegrityError` deja la transacción abortada: sin él, el
    primer choque tumbaría la carga entera del colegio en lugar de sortear otro
    código.
    """
    if actor is None or actor.rol != Rol.INSTITUCION:
        raise PermissionDenied(
            "Matricular estudiantes es función exclusiva de la institución "
            "educativa (HU-43, [S11])."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")

    for intento in range(INTENTOS_DE_CODIGO):
        codigo = generar_codigo_de_tarjeta()
        try:
            with transaction.atomic():
                return Estudiante.objects.create(
                    nombre=nombre,
                    documento=documento,
                    acudiente=acudiente,
                    codigo_tarjeta=codigo,
                )
        except IntegrityError:
            # Puede no haber sido el código: el documento del estudiante también
            # es único, y ese choque no se arregla sorteando otro valor. Si el
            # código sorteado no está en la base, el problema era otro y se
            # propaga tal cual en vez de reintentar cinco veces en balde.
            if not Estudiante.objects.filter(codigo_tarjeta=codigo).exists():
                raise

    raise RuntimeError(
        f"No se pudo asignar un código de tarjeta libre en {INTENTOS_DE_CODIGO} "
        "intentos. Con 2^70 combinaciones esto no ocurre por azar: revisa el "
        "generador (INV-7, DT-9)."
    )


@dataclass
class ResultadoDeCarga:
    """Lo que la carga hizo, para poder enseñárselo a quien la ejecutó."""

    filas_leidas: int = 0
    acudientes_creados: int = 0
    acudientes_reutilizados: int = 0
    estudiantes_creados: int = 0
    invitaciones_generadas: int = 0
    avisos: list = field(default_factory=list)

    @property
    def acudientes_totales(self):
        return self.acudientes_creados + self.acudientes_reutilizados


@transaction.atomic
def cargar_estudiantes_y_acudientes(*, actor, archivo, contrasena_de_desarrollo=None):
    """Carga el archivo entero, o no carga nada (`TT-23`, `HU-01`).

    **Una sola transacción.** `HU-02` exige que la carga sea todo o nada: si
    algo falla a mitad, el sistema no puede quedar con la mitad de un colegio
    dentro. La validación que acumula errores y los reporta antes de escribir es
    `TT-25`; aquí la atomicidad ya está, y es la que sostiene aquello.

    **Solo la institución educativa.** Segundo criterio de `HU-01`, y `[S11]`:
    ningún otro rol carga datos de menores. El actor llega como argumento —este
    servicio no sabe de HTTP (`DT-15`)—.

    **Un mismo acudiente puede quedar a cargo de varios estudiantes** (cuarto
    criterio, `ALC-IN-04`). El correo es la identidad: filas con el mismo correo
    son la misma persona y comparten cuenta.

    **Cada estudiante sale de aquí con su código de tarjeta** (`HU-43`), porque
    el alta pasa por `crear_estudiante` y ese es el único sitio donde se asigna.
    El código **no viene en el archivo**: lo genera el sistema (`INV-7`).

    **Se genera una invitación por cada acudiente que la carga crea** (`TT-28`,
    `HU-03`), dentro de esta misma transacción y sin entregarla por correo
    (`DEC-9`). Generarla es construir su enlace, y hacerlo aquí comprueba que la
    cuenta recién creada es activable: si alguna no lo fuera, la carga entera se
    revierte en vez de dejar acudientes que nadie puede activar. El enlace **no
    se guarda ni se muestra**: es una credencial, y se obtiene de una en una con
    `manage.py invitacion <correo>` (`DEC-3`).

    `contrasena_de_desarrollo` asigna una clave conocida a las cuentas creadas y
    no envía correo (`DEC-11`). Por ese camino **tampoco se genera invitación**:
    la cuenta ya tiene contraseña, así que no hay nada que activar. Sin él, las
    cuentas nacen sin contraseña utilizable y la invitación se genera pero no se
    entrega (`DEC-9`).
    """
    if actor is None or actor.rol != Rol.INSTITUCION:
        raise PermissionDenied(
            "Cargar estudiantes es función exclusiva de la institución educativa "
            "(HU-01, [S11])."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")

    filas = leer(archivo)

    # `HU-02`, primer criterio: **la validación ocurre antes de escribir
    # cualquier dato**. No es lo mismo que deshacer con una transacción: la
    # historia pide que no se llegue a escribir. La transacción de arriba sigue
    # ahí como segunda red, para lo que la validación no pueda anticipar.
    errores = validar(filas)
    if errores:
        raise ArchivoInvalido(errores)

    resultado = ResultadoDeCarga(filas_leidas=len(filas))

    # El correo agrupa: `[S3]` de docs/formato-de-carga.md.
    acudientes_por_correo = {}

    for fila in filas:
        correo = fila.correo_acudiente.lower()

        acudiente = acudientes_por_correo.get(correo)
        if acudiente is None:
            acudiente = Acudiente.objects.filter(usuario__email__iexact=correo).first()
            if acudiente is not None:
                resultado.acudientes_reutilizados += 1
            else:
                usuario = crear_cuenta(
                    email=correo,
                    rol=Rol.ACUDIENTE,
                    nombre=fila.nombre_acudiente,
                    contrasena_de_desarrollo=contrasena_de_desarrollo,
                    # DEC-9: la carga no entrega correo.
                    enviar_invitacion=False,
                )
                acudiente = Acudiente.objects.create(
                    usuario=usuario,
                    nombre=fila.nombre_acudiente,
                    documento=fila.documento_acudiente,
                )
                resultado.acudientes_creados += 1

                # `TT-28`, `HU-03`: una invitación por acudiente cargado,
                # automáticamente al completarse la carga. Con contraseña
                # asignada (`DEC-11`) no hay invitación que generar: la cuenta
                # ya está activada.
                if not contrasena_de_desarrollo:
                    generar_invitacion(usuario)
                    resultado.invitaciones_generadas += 1
            acudientes_por_correo[correo] = acudiente

        crear_estudiante(
            actor=actor,
            nombre=fila.nombre_estudiante,
            documento=fila.documento_estudiante,
            acudiente=acudiente,
        )
        resultado.estudiantes_creados += 1

    return resultado
