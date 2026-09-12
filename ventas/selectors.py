"""Lecturas del punto de venta (`DT-15`).

**Toda lectura no trivial pasa por aquí.** Como los servicios, estos selectores
no conocen `request`: reciben el actor como argumento y devuelven datos, nunca
respuestas HTTP.
"""

from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import PermissionDenied

from billetera.selectors import consumo_del_dia, saldo_de
from catalogo.selectors import productos_en_el_catalogo
from cuentas.models import Rol
from inventario.selectors import existencias_por_producto


@dataclass(frozen=True)
class InformacionDeCobro:
    """Lo que el cajero ve del estudiante para decidir si cobra (`HU-17`).

    Dos cifras hoy —saldo y consumo del día— y **una tercera que falta**: las
    restricciones vigentes son `HU-09` … `HU-13`, del Sprint 3. Por eso `HU-17`
    no se cierra en este Pull Request: su primer criterio pide los tres datos, y
    `DoD-1` no admite dar por terminada una historia con un criterio sin cumplir.

    Es un objeto y no dos valores sueltos porque las dos cifras se leen juntas o
    no se leen: «tiene $3.000» sin «y lleva $12.000 gastados hoy» es media
    respuesta, y el día que se sume el límite diario habrá un solo sitio donde
    añadirlo.
    """

    saldo: Decimal
    consumo_del_dia: Decimal


def informacion_de_cobro(*, actor, estudiante):
    """Saldo y consumo del día del estudiante identificado (`TT-74`, `HU-17`).

    ── ESTA FUNCIÓN ES «SOLO AL COBRAR» ────────────────────────────────────
    `[S11]`, fila «Consultar saldo de un estudiante»: el acudiente lo consulta
    libremente y el cajero **solo al cobrar**. Esa distinción no se sostiene con
    un rótulo en una pantalla: se sostiene aquí, porque este es el único camino
    por el que el saldo de un estudiante llega al rol cajero, y exige el rol.

    `saldo_de` no autoriza a nadie a propósito —lo explica en su docstring: el
    servicio de venta también lo consulta, y ahí no hay ningún acudiente—. La
    autorización va en quien llama, y en el punto de venta ese quien es esta
    función. Un rol distinto del cajero recibe `PermissionDenied` aunque escriba
    la URL a mano (`DT-11`, `INV-4`).
    ─────────────────────────────────────────────────────────────────────────

    **Se responde también del estudiante que no puede comprar** (`INVD-2`), y no
    es una grieta en lo anterior: el saldo de un estudiante de baja sigue siendo
    consultable (`HU-52`), y el cajero acaba de identificarlo con una tarjeta que
    alguien le puso delante en la caja. Callar la cifra no lo protegería de nada
    y dejaría al cajero sin poder explicar por qué no se cobra.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Consultar el saldo para cobrar exige identificarse.")
    if actor.rol != Rol.CAJERO:
        raise PermissionDenied(
            "El saldo de un estudiante se le muestra al cajero solo al cobrar, "
            "y cobrar es del rol cajero (HU-17, [S11])."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")

    return InformacionDeCobro(
        saldo=saldo_de(estudiante),
        consumo_del_dia=consumo_del_dia(estudiante),
    )


def catalogo_de_venta():
    """Lo que hoy se puede vender, con sus existencias (`TT-81`, `HU-21`).

    Los productos retirados no salen: siguen existiendo porque el historial los
    referencia, pero no se ofrecen (`HU-26`).

    **Las existencias llegan en una sola consulta**, no una por fila: el catálogo
    del colegio no es corto y esto se pinta en cada gesto del cajero. Un producto
    sin movimientos no aparece en el agregado, así que se lee con `.get(id, 0)` —
    el cero no es un caso especial, es la suma de una lista vacía (`INV-3`).

    **Lo que devuelve es informativo, no autorizante.** Que aquí figuren tres
    empanadas no significa que al confirmar sigan estando: entre este pintado y
    el cobro puede haber otra caja. La cifra que decide se lee **dentro** del
    bloqueo, en `registrar_venta` (`DT-6`).
    """
    productos = list(productos_en_el_catalogo().order_by("categoria__nombre", "nombre"))
    existencias = existencias_por_producto(productos)

    for producto in productos:
        producto.existencias = existencias.get(producto.id, 0)

    return productos


def lineas_del_carrito(carrito):
    """Los renglones de la venta en curso, listos para pintar.

    Recibe `{id_de_producto: cantidad}` tal como lo guarda `ventas.carrito` —con
    los identificadores en texto, que es como los devuelve la sesión— y resuelve
    los productos en **una** consulta.

    Devuelve `(lineas, total)`. Cada línea trae producto, cantidad e importe; el
    importe se calcula aquí y no en la plantilla porque una plantilla no
    multiplica, y desde luego no en JavaScript (`DT-25`).

    Un producto que ya no está en el catálogo **se cae del carrito en silencio**:
    la alternativa es pintar un renglón de algo que el cobro va a rechazar de
    todas formas. El cobro lo vuelve a comprobar, que es donde importa.
    """
    productos = {
        str(producto.id): producto
        for producto in productos_en_el_catalogo().filter(id__in=carrito)
    }

    lineas = []
    total = Decimal("0.00")
    for producto_id, cantidad in carrito.items():
        producto = productos.get(str(producto_id))
        if producto is None:
            continue
        importe = producto.precio * cantidad
        total += importe
        lineas.append({"producto": producto, "cantidad": cantidad, "importe": importe})

    lineas.sort(key=lambda linea: linea["producto"].nombre)
    return lineas, total
