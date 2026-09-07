"""Escrituras de la billetera (`TT-60`, `HU-06`).

**Toda escritura pasa por aquí** (`DT-15`). Reglas que no se negocian:

1. Una vista nunca escribe directamente: llama a una función de este módulo.
2. Cada función abre su propia `transaction.atomic()`.
3. Estas funciones **no saben de HTTP**: reciben `actor` como argumento y lanzan
   `PermissionDenied` si no procede; nunca leen `request.user`.

**El pago es simulado** (`ALC-OUT-01`, `ALC-OUT-02`): no hay pasarela, no hay
dinero real y no se guarda ningún medio de pago. Lo que esta función asienta es
el movimiento, que es lo que `HU-06` pide.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from billetera.models import Billetera, MovimientoBilletera, TipoDeMovimiento
from cuentas.models import Rol
from personas.services import comprobar_que_puede_operar

# Tope de una recarga. No lo pide ninguna historia y por eso no es una regla de
# negocio disfrazada: es la barrera que evita que un cero de más en un formulario
# —un dedo torpe en un teléfono— asiente un movimiento absurdo en un historial
# que `INV-2` obliga a conservar para siempre. En un prototipo con dinero
# simulado no cuesta nada; el día que haya pasarela, el límite lo pondrá ella.
MONTO_MAXIMO = Decimal("1000000.00")


def _comprobar_que_es_su_acudiente(actor, estudiante):
    """Segundo criterio de `HU-06`: **la recarga la ejecuta únicamente el acudiente**.

    Y no cualquier acudiente: el de ese estudiante. `[S11]` da «recargar saldo»
    solo a `USR-2`, así que ni la cafetería ni la institución recargan — no es un
    olvido, es la matriz.

    Vive en el servicio y no en la vista porque `DT-15` no admite reglas que
    dependan de por dónde se entre: el admin también es una vista.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Recargar exige una cuenta identificada.")
    if actor.rol != Rol.ACUDIENTE:
        raise PermissionDenied(
            "Recargar la billetera es función exclusiva del acudiente (HU-06, [S11])."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")

    # El vínculo se comprueba contra la base, no contra lo que traiga la
    # petición: es la misma regla que sostiene `estudiantes_a_cargo` (`DT-11`).
    if not hasattr(actor, "acudiente") or estudiante.acudiente_id != actor.acudiente.id:
        raise PermissionDenied(
            "Solo se recarga la billetera de un estudiante a cargo (HU-06, [S11])."
        )


# Los tipos que **operan** sobre la billetera, es decir, los que exigen que el
# estudiante esté en condiciones de hacerlo (`INVD-2`).
#
# La devolución no está, y es una decisión, no un olvido: devolver es corregir un
# movimiento anterior, no operar. Un estudiante que se retiró del colegio con una
# venta mal cobrada tiene derecho a que se le corrija, y bloquear la corrección
# dejaría su historial diciendo algo que no pasó — justo lo que `INV-2` existe
# para evitar. `HU-52` prohíbe **comprar y recargar** sobre el saldo congelado, y
# eso es exactamente lo que aquí se prohíbe.
TIPOS_QUE_OPERAN = frozenset({TipoDeMovimiento.RECARGA, TipoDeMovimiento.VENTA})


@transaction.atomic
def asentar(*, estudiante, tipo, monto):
    """**El único sitio por el que se escribe en el libro** (`TT-65`, `HU-52`).

    Devuelve el `MovimientoBilletera` creado.

    Existe para que «el saldo congelado no admite compras ni recargas» sea cierto
    **antes de que exista la venta**. `INVD-2` ya estaba escrita y `recargar` ya
    la llamaba, pero eso solo protege a los servicios que se acuerden de llamarla:
    el de venta se escribe en `TT-80`, dos semanas después, y una regla que
    depende de la memoria de quien escriba el siguiente servicio no es una regla.

    Con esto, cualquier movimiento nuevo —la venta de `HU-21`, la devolución, lo
    que venga— pasa por aquí y la comprobación ocurra o no se escriba nada.

    La billetera se crea si no existía: es la primera operación del estudiante.
    `get_or_create` dentro de la transacción evita la carrera entre dos
    operaciones simultáneas, y el `OneToOneField` la cierra del todo.

    **No comprueba quién es el actor**, y no es un descuido: cada operación tiene
    su propia regla de quién puede —recargar es del acudiente (`HU-06`), cobrar
    es del cajero (`[S11]`)— y son los servicios de arriba los que la aplican.
    Meter aquí un `actor` obligaría a inventar uno en la venta, donde quien opera
    es el cajero sobre la billetera de un tercero.
    """
    if tipo in TIPOS_QUE_OPERAN:
        # `INVD-2`: ni desactivado ni de baja se compra ni se recarga. La puerta
        # es única y vive en `personas` desde el Sprint 1, precisamente para que
        # el primer servicio que moviera dinero no tuviera que reconstruirla.
        comprobar_que_puede_operar(estudiante)

    billetera, _ = Billetera.objects.get_or_create(estudiante=estudiante)

    return MovimientoBilletera.objects.create(
        billetera=billetera, tipo=tipo, monto=monto
    )


@transaction.atomic
def recargar(*, actor, estudiante, monto):
    """Asienta una recarga en la billetera del estudiante (`TT-60`, `HU-06`).

    Devuelve el `MovimientoBilletera` creado.

    **Todo ocurre dentro de una transacción**: o queda el movimiento, o no queda
    nada. Un asiento a medias en el libro que define el saldo (`INV-2`) sería un
    saldo que nadie puede explicar.

    La billetera se crea aquí si no existía. Es la primera recarga del
    estudiante, y `get_or_create` dentro de la transacción evita la carrera entre
    dos recargas simultáneas del mismo acudiente; el `OneToOneField` la cierra
    del todo por si acaso.

    **No hace falta bloqueo pesimista, y conviene decir por qué.** `DT-6` lo
    exige en la venta porque allí se lee el saldo para decidir si alcanza
    (`INV-1`): dos cajeros a la vez podrían leer el mismo saldo y gastarlo dos
    veces. Una recarga no lee nada para decidir: inserta una fila positiva. Dos
    recargas simultáneas dan dos movimientos y un saldo correcto sin coordinarse.
    """
    _comprobar_que_es_su_acudiente(actor, estudiante)

    monto = Decimal(monto)
    if monto <= 0:
        raise ValidationError("Una recarga suma: el monto tiene que ser mayor que cero.")
    if monto > MONTO_MAXIMO:
        raise ValidationError(
            f"El monto máximo de una recarga es {MONTO_MAXIMO:.0f}."
        )
    # Dos decimales, ni uno más. Sin esto, un tercer decimal entra y la base lo
    # redondea en silencio: el historial diría una cifra y el formulario otra.
    if monto != monto.quantize(Decimal("0.01")):
        raise ValidationError("El monto admite como mucho dos decimales.")

    # `INVD-2` y `HU-52` los comprueba el asentador, que es por donde pasan todos
    # los movimientos: aquí no se repite para que no haya dos sitios que puedan
    # discrepar sobre cuándo una billetera está congelada.
    return asentar(estudiante=estudiante, tipo=TipoDeMovimiento.RECARGA, monto=monto)
