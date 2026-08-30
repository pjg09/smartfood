"""Escrituras del dominio de usuarios, roles, invitaciones y sesión.

**Toda escritura pasa por aquí** (`DT-15`). Reglas que no se negocian:

1. Una vista nunca escribe directamente: llama a una función de este módulo.
2. Cada función abre su propia `transaction.atomic()`.
3. Estas funciones **no saben de HTTP**: no reciben `request`, no devuelven
   `HttpResponse` y no leen `request.user` —el usuario se pasa como argumento—.

Funciones, no clases.
"""

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from config.correo import enviar_correo
from cuentas.models import Rol, Usuario
from cuentas.permisos import PERMISOS_POR_ROL, nombre_del_grupo

# Los dos roles que la institución da de alta (`HU-40`, `DEC-2`).
ROLES_DE_PERSONAL = frozenset({Rol.CAJERO, Rol.ADMINISTRADOR})


def construir_enlace_de_invitacion(usuario):
    """Devuelve la URL absoluta con la que el titular define su contraseña.

    Reutiliza el generador de tokens de Django en lugar de inventar uno. No es
    pereza: `CLAUDE.md` descarta explícitamente construir autenticación propia,
    y este generador ya invalida el token en cuanto la contraseña cambia y
    caduca solo (`PASSWORD_RESET_TIMEOUT`). `TT-18` revisa ambas propiedades;
    aquí se usan, no se dan por decididas.
    """
    ruta = reverse(
        "definir-contrasena",
        kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(usuario.pk)),
            "token": default_token_generator.make_token(usuario),
        },
    )
    return f"{settings.URL_BASE.rstrip('/')}{ruta}"


def invitar(usuario):
    """Manda al titular la invitación con la que definirá su contraseña.

    No escribe nada, pero vive entre los servicios porque es el efecto que
    acompaña a toda alta de cuenta (`HU-39`, `HU-41`, `HU-03`) y las vistas no
    deben construirlo por su cuenta.

    El envío se difiere hasta que la transacción confirme (`config/correo.py`):
    invitar a alguien cuya alta se revirtió es mandarle un enlace a una cuenta
    que no existe.
    """
    enviar_correo(
        destinatario=usuario.email,
        asunto="Te damos acceso a SmartFood",
        plantilla="correo/invitacion",
        contexto={
            "nombre": usuario.nombre or usuario.email,
            "rol": usuario.get_rol_display(),
            "enlace": construir_enlace_de_invitacion(usuario),
            "dias_de_validez": settings.PASSWORD_RESET_TIMEOUT // (60 * 60 * 24),
        },
    )


@transaction.atomic
def crear_cuenta(*, email, rol, nombre="", accede_a_administracion=False,
                 contrasena_de_desarrollo=None):
    """Crea una cuenta **sin contraseña utilizable** y la invita.

    `INV-6` e `INVD-1`: ninguna cuenta nace de un autorregistro, y quien la crea
    no llega a conocer nunca la clave del titular (`DEC-3`).

    `contrasena_de_desarrollo` es la **única excepción**, y está acotada por
    `DEC-10`: fija una clave conocida y **no envía invitación**. Existe solo para
    la cuenta institucional del prototipo, que nadie va a activar por correo
    porque su dirección no es de nadie. Su nombre es largo a propósito: quien lo
    escriba tiene que saber lo que está haciendo.

    **No lo uses para cuentas de acudiente ni de personal.** Ahí la invitación
    es el mecanismo, y `HU-41` exige que quien crea la cuenta no conozca la
    clave.
    """
    usuario = Usuario.objects.crear_usuario(
        email=email,
        rol=rol,
        nombre=nombre,
        is_staff=accede_a_administracion,
    )

    asignar_grupo_del_rol(usuario)

    if contrasena_de_desarrollo:
        usuario.set_password(contrasena_de_desarrollo)
        usuario.save(update_fields=["password"])
        return usuario

    invitar(usuario)
    return usuario


def asignar_grupo_del_rol(usuario):
    """Pone al usuario en el grupo de su rol, y solo en ese.

    Los permisos van al **grupo**, no al usuario: así cambiar lo que puede hacer
    un rol es una operación, no recorrer las cuentas una a una.
    """
    grupo, _ = Group.objects.get_or_create(name=nombre_del_grupo(usuario.rol))
    usuario.groups.set([grupo])
    return grupo


@transaction.atomic
def sincronizar_grupos_y_permisos():
    """Materializa la matriz `[S11]` en grupos de Django (`TT-15`).

    **Idempotente y con poda.** No solo concede lo que la matriz dice: **retira
    lo que la matriz no dice**. Sin la poda, un permiso concedido a mano —o
    heredado de una versión anterior de la matriz— se quedaría para siempre, y
    `INV-4` dejaría de estar donde se puede leer.

    Devuelve `{nombre_del_grupo: [codenames]}` para poder informar.
    """
    resultado = {}

    for rol, modelos in PERMISOS_POR_ROL.items():
        grupo, _ = Group.objects.get_or_create(name=nombre_del_grupo(rol))

        codenames = []
        for etiqueta, acciones in modelos.items():
            app, modelo = etiqueta.split(".")
            for accion in acciones:
                codenames.append((app, f"{accion}_{modelo}"))

        permisos = list(
            Permission.objects.filter(
                content_type__app_label__in=[a for a, _ in codenames],
                codename__in=[c for _, c in codenames],
            )
        ) if codenames else []

        # `set` reemplaza: concede lo que falta y retira lo que sobra.
        grupo.permissions.set(permisos)
        resultado[grupo.name] = sorted(p.codename for p in permisos)

    return resultado


@transaction.atomic
def crear_cuenta_de_personal(*, actor, email, rol, nombre=""):
    """Da de alta a un cajero o administrador de la cafetería (`TT-16`, `HU-40`).

    **Solo la institución educativa puede hacerlo** —primer criterio de
    `HU-40`—, y solo sobre los dos roles de personal. El actor se recibe como
    argumento: este servicio no sabe de HTTP y no lee `request.user` (`DT-15`).

    Dispara la invitación de `HU-41`, así que quien crea la cuenta **no llega a
    conocer nunca la clave del titular**.
    """
    if actor is None or actor.rol != Rol.INSTITUCION:
        raise PermissionDenied(
            "Solo la institución educativa da de alta cuentas del personal (HU-40)."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")

    if rol not in ROLES_DE_PERSONAL:
        permitidos = ", ".join(sorted(ROLES_DE_PERSONAL))
        raise ValueError(
            f"«{rol}» no es un rol de personal de la cafetería. Se admiten: {permitidos}. "
            "Las cuentas de acudiente nacen de la carga institucional (HU-01, HU-03)."
        )

    return crear_cuenta(
        email=email,
        rol=rol,
        nombre=nombre,
        # `INT-3` es el admin de Django (`DT-2`): el personal opera desde allí.
        accede_a_administracion=True,
    )


def _comprobar_actor_institucional(actor, verbo):
    """La institución educativa, y activa. `[S11]`, `DEC-2`, `HU-42`."""
    if actor is None or actor.rol != Rol.INSTITUCION:
        raise PermissionDenied(
            f"Solo la institución educativa puede {verbo} cuentas del personal (HU-42)."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")


def _comprobar_es_personal(usuario):
    if usuario.rol not in ROLES_DE_PERSONAL:
        raise ValueError(
            f"«{usuario.rol}» no es personal de la cafetería. `HU-42` cubre a cajeros y "
            "administradores; la baja del estudiante es HU-51 y tiene sus propias reglas."
        )


@transaction.atomic
def desactivar_cuenta(*, actor, usuario):
    """Revoca el acceso sin borrar nada (`TT-19`, `HU-42`).

    **Baja lógica, no borrado.** El tercer criterio de `HU-42` exige que el
    historial de operaciones de la cuenta se conserve: quién cobró qué venta
    sigue siendo cierto después de que esa persona deje de trabajar allí.
    Borrar la fila destruiría esa trazabilidad, que es lo que `OBJ-E2` pide del
    sistema.

    No hace falta cerrar sesiones a mano: el backend de autenticación de Django
    rechaza a los usuarios inactivos también al resolver la sesión, así que la
    sesión abierta deja de identificar a nadie en la siguiente petición. Hay
    caso de prueba, porque «no puede iniciar sesión» y «no puede operar» son dos
    afirmaciones distintas y `HU-42` pide las dos.
    """
    _comprobar_actor_institucional(actor, "desactivar")
    _comprobar_es_personal(usuario)

    if usuario.pk == actor.pk:
        raise PermissionDenied(
            "La institución no puede desactivarse a sí misma: nadie podría reactivarla."
        )

    if not usuario.is_active:
        return usuario

    usuario.is_active = False
    usuario.save(update_fields=["is_active"])
    return usuario


@transaction.atomic
def reactivar_cuenta(*, actor, usuario):
    """Devuelve el acceso. Segundo criterio de `HU-42`."""
    _comprobar_actor_institucional(actor, "reactivar")
    _comprobar_es_personal(usuario)

    if usuario.is_active:
        return usuario

    usuario.is_active = True
    usuario.save(update_fields=["is_active"])
    return usuario


@transaction.atomic
def reenviar_invitacion(usuario):
    """Vuelve a mandar la invitación a quien todavía no definió su contraseña."""
    if usuario.tiene_contrasena_definida:
        raise ValueError("Esa cuenta ya tiene contraseña: no procede una invitación.")
    invitar(usuario)


__all__ = [
    "Rol",
    "asignar_grupo_del_rol",
    "construir_enlace_de_invitacion",
    "crear_cuenta",
    "crear_cuenta_de_personal",
    "desactivar_cuenta",
    "invitar",
    "reactivar_cuenta",
    "reenviar_invitacion",
    "sincronizar_grupos_y_permisos",
]
