"""Escrituras del control parental (`TT-95`, `HU-09`).

**Toda escritura pasa por aquí** (`DT-15`). Reglas que no se negocian:

1. Una vista nunca escribe directamente: llama a una función de este módulo.
2. Cada función abre su propia `transaction.atomic()`.
3. Estas funciones **no saben de HTTP**: reciben `actor` como argumento y lanzan
   `PermissionDenied` si no procede; nunca leen `request.user`.

═══════════════════════════════════════════════════════════════════════════
**AQUÍ EMPIEZA `INV-4`, Y CONVIENE DECIR DÓNDE ACABA.**

La invariante dice que las restricciones no las desactiva la cafetería. Este
módulo pone la primera mitad: el servicio exige que quien escribe sea el
acudiente **de ese estudiante**, entre por donde entre. La segunda mitad son los
permisos de `[S11]` en la capa de datos, y los cierra `TT-107` (`PR-05`).

No basta con esto solo, y no conviene creer que sí: un servicio protege el
camino que pasa por él. Lo que impide que aparezca un segundo camino es que el
permiso no exista (`DT-11`).
═══════════════════════════════════════════════════════════════════════════
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from cuentas.models import Rol
from restricciones.models import LimiteDiario

# Tope de un límite diario. **No es una regla de negocio disfrazada**: ninguna
# historia fija un máximo, y un límite altísimo es indistinguible de no tener
# ninguno, que es una opción legítima y gratuita —basta con no configurarlo—.
#
# Existe por algo más prosaico: `monto` es `DecimalField(max_digits=10)`, así
# que por encima de ocho enteros la base contesta `NumericValueOutOfRange`, que
# es un error de Postgres y no una frase que un acudiente pueda leer. El tope
# convierte ese fallo en un mensaje, y de paso frena el cero de más de un dedo
# torpe en un teléfono, que es desde donde entra `INT-1`.
MONTO_MAXIMO = Decimal("1000000.00")


def _comprobar_que_es_su_acudiente(actor, estudiante):
    """Segundo criterio de `HU-09`: **solo el acudiente fija o modifica el límite**.

    Y no cualquier acudiente: el de ese estudiante. `[S11]` da «fijar límite
    diario» únicamente a `USR-2`, así que ni el cajero, ni la administración de
    la cafetería, ni la institución educativa pasan de aquí — no es un olvido, es
    la matriz, y es literalmente `INV-4`.

    Vive en el servicio y no en la vista porque `DT-15` no admite reglas que
    dependan de por dónde se entre: el admin también es una vista.

    Es el mismo control que `billetera.services._comprobar_que_es_su_acudiente`
    hace sobre la recarga, y **se escribe otra vez a propósito**. Compartirlo
    obligaría a que `restricciones` importara de `billetera` —dos dominios que no
    se tocan— para heredar un mensaje de error sobre recargas. Lo que tienen en
    común no es la implementación, son tres líneas de `[S11]`; el día que una de
    las dos filas cambie, la otra no tiene por qué seguirla.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Fijar un límite diario exige una cuenta identificada.")
    if actor.rol != Rol.ACUDIENTE:
        raise PermissionDenied(
            "Fijar el límite diario de gasto es función exclusiva del acudiente "
            "(HU-09, INV-4, [S11])."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")

    # El vínculo se comprueba contra la base, no contra lo que traiga la
    # petición: es la misma regla que sostiene `estudiantes_a_cargo` (`DT-11`).
    if not hasattr(actor, "acudiente") or estudiante.acudiente_id != actor.acudiente.id:
        raise PermissionDenied(
            "Solo se fija el límite diario de un estudiante a cargo (HU-09, [S11])."
        )


def _monto_valido(monto):
    """El monto, normalizado, o `ValidationError` con una frase que se entienda."""
    try:
        monto = Decimal(monto)
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("El límite diario tiene que ser una cifra.") from None

    if not monto.is_finite():
        raise ValidationError("El límite diario tiene que ser una cifra.")
    if monto <= 0:
        raise ValidationError(
            "Un límite diario de cero no es un límite: es no poder comprar nada. "
            "Si no quieres límite, retíralo en lugar de ponerlo a cero."
        )
    if monto > MONTO_MAXIMO:
        raise ValidationError(f"El límite diario máximo es {MONTO_MAXIMO:.0f}.")
    # Dos decimales, ni uno más. Sin esto, un tercer decimal entra y la base lo
    # redondea en silencio: la pantalla diría una cifra y el cupo sería otra.
    if monto != monto.quantize(Decimal("0.01")):
        raise ValidationError("El límite admite como mucho dos decimales.")

    return monto


@transaction.atomic
def fijar_limite_diario(*, actor, estudiante, monto):
    """Fija o modifica el límite diario de un estudiante (`TT-95`, `HU-09`).

    Devuelve el `LimiteDiario` vigente tras la operación.

    **Fijar y modificar son la misma operación**, y por eso hay una función y no
    dos. Lo que el acudiente hace es declarar cuál es el cupo de hoy en adelante;
    que antes hubiera otro número o ninguno no cambia ni quién puede hacerlo ni
    qué queda escrito. Dos servicios habrían obligado a la pantalla a preguntar
    primero si existía fila, que es una pregunta sobre la base y no sobre lo que
    el acudiente quiere.

    `update_or_create` dentro de la transacción cierra la carrera entre dos
    envíos simultáneos del mismo formulario; el `OneToOneField` la cierra del
    todo por si acaso.

    ── NO COMPRUEBA `INVD-2`, Y ES UNA DECISIÓN ────────────────────────────
    Un estudiante desactivado o de baja no compra ni recarga (`INVD-2`), y
    `billetera.services.asentar` lo exige antes de mover un peso. Aquí no se
    exige: configurar un cupo no mueve dinero ni existencias, no puede dejar un
    saldo negativo y no tiene efecto hasta que haya una venta — que es justo lo
    que `INVD-2` ya impide. Bloquearlo obligaría al acudiente de un estudiante
    reactivado a recordar que tiene que volver a configurarlo todo, y le quitaría
    protección al hijo en el momento de volver.
    ─────────────────────────────────────────────────────────────────────────

    **El límite no se aplica todavía en la venta.** La comparación contra el
    consumo del día —tercer criterio de `HU-09` y razón de ser de `HU-20`— la
    construye `TT-116` dentro del bloqueo de `registrar_venta` (`PR-09`, `DT-6`).
    Hasta entonces esto guarda una cifra que nadie consulta al cobrar, y las
    pantallas lo dicen: prometerle al acudiente una protección que aún no existe
    sería peor que no ofrecerle el campo.
    """
    _comprobar_que_es_su_acudiente(actor, estudiante)

    monto = _monto_valido(monto)

    limite, _ = LimiteDiario.objects.update_or_create(
        estudiante=estudiante, defaults={"monto": monto}
    )
    return limite
