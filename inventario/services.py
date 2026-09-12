"""Escrituras del inventario (`TT-68`, `HU-27`).

**Toda escritura pasa por aquí** (`DT-15`). Reglas que no se negocian:

1. Una vista nunca escribe directamente: llama a una función de este módulo.
   **El admin también es una vista**: su `save_model` delega aquí (`INT-3`).
2. Cada función abre su propia `transaction.atomic()`.
3. Estas funciones **no saben de HTTP**: reciben `actor` como argumento y lanzan
   `PermissionDenied` si no procede; nunca leen `request.user`.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from cuentas.models import Rol
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario


def _comprobar_que_gestiona_el_inventario(actor, accion):
    """`[S11]`: «gestionar catálogo, precios e inventario» es de `USR-4`.

    De la administración de la cafetería y de nadie más: ni la institución —que
    no vende— ni el cajero, que cobra lo que ya está. Vive en el servicio y no en
    la vista porque `DT-15` no admite reglas que dependan de por dónde se entre.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied(f"{accion} exige una cuenta identificada.")
    if actor.rol != Rol.ADMINISTRADOR:
        raise PermissionDenied(
            f"{accion} es función exclusiva de la administración de la "
            "cafetería (HU-27, [S11])."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")


@transaction.atomic
def asentar(*, producto, tipo, cantidad, motivo="", venta=None):
    """**El único sitio por el que se escribe en el libro** (`TT-67`, `INV-3`).

    Devuelve el `MovimientoInventario` creado.

    Existe por el mismo motivo que su gemelo en `billetera`: el servicio de venta
    se escribe en `TT-80`, dos semanas después de esto, y descontará existencias.
    Si cada servicio creara el movimiento por su cuenta, las reglas del libro
    dependerían de que cada uno se acuerde de aplicarlas.

    **No comprueba quién es el actor**: cada operación tiene su propia regla de
    quién puede —ingresar es de la administración (`HU-27`), vender es del cajero
    (`[S11]`)— y la aplican los servicios de arriba. Lo que sí comprueba es la
    forma del movimiento, que es igual venga de donde venga.

    El signo y el motivo obligatorio de `INV-8` los impone además la base
    (`DT-5`). Aquí se comprueban antes para dar un mensaje que se entienda, no
    para sustituirla: la restricción es la que no se olvida.

    ── `venta` (`TT-78`) ───────────────────────────────────────────────────
    La salida por venta **señala la venta que la origina**. Es lo que hace
    comprobable la frase de arriba —el motivo de una venta es la venta misma— y
    lo que `INV-3` necesita para que unas existencias se puedan explicar.

    El ingreso y la merma no la llevan: los dos son manuales y los explica su
    motivo, no una compra que no existió.

    Como `asentar()` es el único punto de escritura del libro, **este argumento
    es el único camino** por el que el servicio de venta de `TT-80` podrá dejar
    esa referencia.
    ─────────────────────────────────────────────────────────────────────────
    """
    if cantidad == 0:
        raise ValidationError("Un movimiento de cero no mueve nada.")

    esperado_positivo = tipo == TipoDeMovimientoDeInventario.INGRESO
    if esperado_positivo and cantidad < 0:
        raise ValidationError("Un ingreso suma: la cantidad tiene que ser positiva.")
    if not esperado_positivo and cantidad > 0:
        raise ValidationError(
            "Una venta o una merma restan: la cantidad tiene que ser negativa."
        )

    if tipo == TipoDeMovimientoDeInventario.VENTA and venta is None:
        raise ValidationError(
            "Una salida por venta tiene que decir de qué venta sale: es lo que "
            "explica las existencias que quedaron (INV-3)."
        )
    if tipo != TipoDeMovimientoDeInventario.VENTA and venta is not None:
        raise ValidationError(
            "El ingreso y la merma son manuales: los explica su motivo, no una venta."
        )

    # `INV-8`: toda disminución **manual** exige motivo. La venta no, porque su
    # motivo es la venta misma.
    if tipo == TipoDeMovimientoDeInventario.MERMA and not motivo.strip():
        raise ValidationError(
            "Una merma exige motivo: es la única forma de que desaparezcan "
            "existencias sin una venta que lo explique (INV-8)."
        )

    return MovimientoInventario.objects.create(
        producto=producto,
        tipo=tipo,
        cantidad=cantidad,
        motivo=motivo.strip(),
        venta=venta,
    )


@transaction.atomic
def ingresar_mercancia(*, actor, producto, cantidad, motivo=""):
    """Registra un ingreso de mercancía por ajuste manual (`TT-68`, `HU-27`).

    Devuelve el `MovimientoInventario` creado.

    **Ajuste manual, no orden de compra.** `ALC-OUT-11` y `ALC-OUT-12` dejan
    fuera los proveedores y las órdenes: aquí no hay quién suministra, ni precio
    de costo, ni recepción parcial. Alguien de la administración cuenta lo que
    llegó y lo registra, y eso es todo el flujo.

    **Un producto preparado en la cafetería entra por aquí igual que uno
    comprado** (tercer criterio de `HU-27`): treinta empanadas hechas esta mañana
    son treinta unidades vendibles, y no se descomponen en harina y aceite.

    El motivo es opcional en un ingreso —`INV-8` lo exige en las disminuciones—,
    pero se acepta porque «pedido semanal» o «producción del martes» cuesta nada
    de escribir y explica el asiento seis meses después.
    """
    _comprobar_que_gestiona_el_inventario(actor, "Registrar ingresos de mercancía")

    cantidad = int(cantidad)
    if cantidad <= 0:
        raise ValidationError("Un ingreso suma: la cantidad tiene que ser mayor que cero.")

    return asentar(
        producto=producto,
        tipo=TipoDeMovimientoDeInventario.INGRESO,
        cantidad=cantidad,
        motivo=motivo,
    )
