"""Escrituras de la venta (`TT-80`, `HU-21`, `DT-6`).

**Toda escritura pasa por aquí** (`DT-15`). Reglas que no se negocian:

1. Una vista nunca escribe directamente: llama a una función de este módulo.
2. Cada función abre su propia `transaction.atomic()`.
3. Estas funciones **no saben de HTTP**: reciben `actor` como argumento y lanzan
   `PermissionDenied` si no procede; nunca leen `request.user`.

═══════════════════════════════════════════════════════════════════════════
**ESTE ES EL FICHERO DE MAYOR RIESGO DEL PROYECTO.**

`registrar_venta` sostiene `INV-1`, `INV-2` e `INV-3` **a la vez**, y el orden de
lo que hace no es estilo: es la invariante. `DT-6` lo dice en una línea —se
bloquea, **luego** se valida, **luego** se escribe— y el motivo es que validar
fuera del bloqueo abre la ventana en la que dos cajeros cobran a la vez, los dos
leen saldo suficiente y la billetera acaba en negativo. Con dos a cinco cajas en
una ventana de veinte a treinta minutos, esa concurrencia no es teórica.

Si alguien mueve la validación antes del `select_for_update`, las pruebas de
`ventas/tests_concurrencia.py` fallan. Están escritas para eso.
═══════════════════════════════════════════════════════════════════════════
"""

from decimal import Decimal
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from billetera.models import Billetera, TipoDeMovimiento
from billetera.selectors import saldo_de
from billetera.services import asentar as asentar_en_la_billetera
from billetera.templatetags.dinero import dinero
from catalogo.models import Producto
from cuentas.models import Rol
from inventario.models import TipoDeMovimientoDeInventario
from inventario.selectors import existencias_por_producto
from inventario.services import asentar as asentar_en_el_inventario
from ventas.models import LineaVenta, MedioDePago, Venta


class VentaRechazada(ValidationError):
    """La venta no se realiza, y **no se escribe nada**.

    Una sola familia de errores para todos los motivos de rechazo —saldo,
    existencias, carrito vacío— porque quien llama hace lo mismo con todos:
    enseñar el motivo y no cobrar. Los motivos concretos son subclases para que
    una prueba pueda exigir **cuál**, no solo que falló.
    """


class CarritoVacio(VentaRechazada):
    """Cobrar sin líneas no es una venta de cero: no es una venta."""


class SaldoInsuficiente(VentaRechazada):
    """`INV-1`, `HU-19`, escenario crítico `TST-2`.

    **Ninguna venta deja la billetera en negativo.** El primer criterio de
    `HU-19` —«si los fondos son insuficientes, la venta no se realiza»— se
    cumple lanzando esto **dentro** del bloqueo, antes de escribir nada
    (`DT-6`); el segundo —«el saldo nunca queda negativo, bajo ninguna
    combinación de operaciones»— lo vigila `ventas/tests_saldo_insuficiente.py`.

    Lleva `saldo`, `total` y `faltante` además del mensaje. Quien la atienda
    puede así decir cuánto falta sin volver a consultar nada, y una prueba puede
    exigir la cifra en lugar de buscar un texto dentro de otro texto.
    """

    def __init__(self, mensaje, *, saldo=None, total=None):
        super().__init__(mensaje)
        self.saldo = saldo
        self.total = total
        self.faltante = None if saldo is None or total is None else total - saldo


class ExistenciasInsuficientes(VentaRechazada):
    """No se vende lo que no hay.

    ── ESTA REGLA NO SALE DE NINGÚN CRITERIO DE ACEPTACIÓN ─────────────────
    Ninguna historia dice «rechaza la venta si no hay existencias». Se aplica
    igualmente, y conviene que quede escrito por qué:

    · `DT-6` manda bloquear «los productos implicados». Un bloqueo que no
      protege ninguna lectura no protege nada; si no se comprueban existencias,
      ese bloqueo sobra y `DT-6` estaría pidiendo algo sin sentido.
    · `inventario.selectors.existencias_de` ya declara este uso desde `TT-62`:
      «el punto de venta lo consultará para decidir si hay stock (`HU-21`)».
    · Sin ella, vender cien empanadas de las tres que hay deja el inventario en
      −97. `INV-3` seguiría cumpliéndose —la suma explica el número— pero lo que
      explicaría es un disparate, y el ingreso de `HU-27` y la auditoría de
      `HU-29` dejarían de significar nada.

    Si el equipo prefiere permitir la venta sin existencias, esto se quita y se
    registra como decisión; lo que no se puede es dejarlo sin decidir.
    ─────────────────────────────────────────────────────────────────────────
    """


def _solo_el_cajero(actor):
    """`[S11]`: «registrar ventas en el punto de venta» es de `USR-3`.

    Vive en el servicio y no en la vista porque `DT-15` lo exige: el control de
    acceso es de la capa de datos. La vista también lo comprueba —para devolver
    un `403` antes de montar nada—, y esa duplicación es deliberada: si mañana
    hay un comando, una tarea programada o una segunda pantalla, la regla sigue
    aquí.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Registrar una venta exige identificarse.")
    if actor.rol != Rol.CAJERO:
        raise PermissionDenied(
            "Registrar ventas en el punto de venta es del rol cajero, y de "
            "ningún otro ([S11], INV-4)."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")


def _medio_de_pago_de(estudiante, medio_pago):
    """El medio que corresponde, comprobado contra `HU-54` y `DEC-1`.

    Hay estudiante **si y solo si** el medio es billetera. La base lo impone con
    `venta_medio_de_pago_segun_el_cliente`; aquí se comprueba antes para que el
    cajero lea un motivo y no un error de integridad.
    """
    if estudiante is not None:
        if medio_pago not in (None, MedioDePago.BILLETERA):
            raise VentaRechazada(
                "La compra de un estudiante sale siempre de su billetera (HU-54)."
            )
        return MedioDePago.BILLETERA

    if medio_pago not in (MedioDePago.EFECTIVO, MedioDePago.TRANSFERENCIA):
        raise VentaRechazada(
            "Una venta sin estudiante se paga en efectivo o por transferencia "
            "(DEC-1): no hay billetera contra la que cobrar."
        )
    return medio_pago


@transaction.atomic
def registrar_venta(*, actor, lineas, estudiante=None, medio_pago=None):
    """Cobra: descuenta saldo y existencias **en la misma operación** (`HU-21`).

    Devuelve la `Venta` creada.

    `lineas` es `{producto_id: cantidad}` — un renglón por producto, que es lo
    que `LineaVenta` admite (`TT-78`). Cantidades enteras y positivas.

    ── EL ORDEN ES LA INVARIANTE ───────────────────────────────────────────
    `DT-6`, y se lee de arriba abajo en el cuerpo de esta función:

    1. **Se bloquea.** `select_for_update()` sobre la billetera y sobre los
       productos implicados. Desde aquí hasta el `COMMIT`, ninguna otra venta
       toca esas filas: espera.
    2. **Se valida** —existencias y saldo— leyendo **dentro** del bloqueo. Es lo
       único que hace cierta `INV-1`: la cifra que se lee ya no puede cambiar
       debajo.
    3. **Se escribe**: la venta, sus líneas y los movimientos de los dos libros.

    Todo dentro de **una** `transaction.atomic()`. Si cualquier validación falla
    —o falla la escritura a medio camino— no queda nada: ni venta, ni líneas, ni
    movimientos. Eso es literalmente el primer criterio de `HU-21`, «ambos
    descuentos ocurren en la misma operación: no puede quedar uno sin el otro».

    Validar antes del bloqueo daría el mismo resultado en una prueba secuencial y
    rompería `INV-1` en producción, que es la peor clase de error: el que pasa
    las pruebas. `ventas/tests_concurrencia.py` existe para detectarlo.
    ─────────────────────────────────────────────────────────────────────────

    ── LOS PRODUCTOS SE BLOQUEAN ORDENADOS POR IDENTIFICADOR ───────────────
    Dos ventas simultáneas que compartan dos productos podrían bloquearlos en
    orden distinto y quedarse esperando la una a la otra para siempre. Un orden
    total y fijo —el del identificador— hace imposible el ciclo. La billetera va
    primero, y no entra en el ciclo porque cada venta toca como mucho una.
    ─────────────────────────────────────────────────────────────────────────

    **`estudiante=None` es una venta a cliente genérico** (`DEC-1`): descuenta
    inventario como cualquier otra y no toca ninguna billetera. La pantalla que
    la emite es `HU-53` (`PR-15`); el servicio ya la sabe hacer porque separarla
    habría significado dos caminos de escritura para el mismo libro, que es justo
    lo que `DT-24` evita.

    **Lo que todavía NO evalúa**: restricciones alimentarias (`HU-18`) ni límite
    diario (`HU-20`), que son del Sprint 3. `DT-6` las nombra y su sitio es el
    paso 2, junto al saldo. No se dejan preparadas con un `pass`: cuando lleguen,
    se añaden donde se lee el saldo.
    """
    _solo_el_cajero(actor)

    if not lineas:
        raise CarritoVacio("No hay nada que cobrar.")

    # Las claves se normalizan a `UUID`. El carrito vive en la sesión, que se
    # serializa a JSON y devuelve los identificadores como **texto**; las pruebas
    # del servicio los pasan como `UUID`. Sin normalizar, `lineas[producto.id]`
    # encuentra la clave en un caso y lanza `KeyError` en el otro — y lo hace
    # dentro de la transacción, ya bloqueada.
    try:
        lineas = {UUID(str(producto_id)): cantidad for producto_id, cantidad in lineas.items()}
    except (ValueError, AttributeError, TypeError):
        raise VentaRechazada("Alguno de los renglones no identifica a ningún producto.")

    for cantidad in lineas.values():
        if not isinstance(cantidad, int) or cantidad <= 0:
            raise VentaRechazada("Cada renglón se vende por unidades enteras y positivas.")

    medio_pago = _medio_de_pago_de(estudiante, medio_pago)

    # ── 1. BLOQUEAR ─────────────────────────────────────────────────────────
    # `list()` no es decorativo: sin evaluar el `QuerySet` no se emite ningún
    # `SELECT ... FOR UPDATE` y no se bloquea nada. Un bloqueo perezoso es un
    # bloqueo que no existe.
    if estudiante is not None:
        billetera, _ = Billetera.objects.get_or_create(estudiante=estudiante)
        list(Billetera.objects.select_for_update().filter(pk=billetera.pk))

    # `activo=True`: un producto retirado sigue existiendo —el historial lo
    # referencia— pero **no se vende** (`HU-26`). El carrito ya lo deja caer al
    # pintarse, y aun así se filtra aquí: una sesión abierta desde antes del
    # retiro lo seguiría llevando, y quien decide es el cobro.
    productos = list(
        Producto.objects.select_for_update()
        .filter(id__in=lineas, activo=True)
        .order_by("id")
    )
    if len(productos) != len(lineas):
        raise VentaRechazada(
            "Alguno de los productos ya no está en el catálogo: vuelve a montar "
            "la venta."
        )

    # ── 2. VALIDAR, DENTRO DEL BLOQUEO ──────────────────────────────────────
    existencias = existencias_por_producto(productos)
    for producto in productos:
        disponibles = existencias.get(producto.id, 0)
        if disponibles < lineas[producto.id]:
            raise ExistenciasInsuficientes(
                f"De «{producto.nombre}» quedan {disponibles} y se piden "
                f"{lineas[producto.id]}."
            )

    total = sum(
        (producto.precio * lineas[producto.id] for producto in productos),
        Decimal("0.00"),
    )

    if estudiante is not None:
        # `INV-1`. La resta se hace aquí, con el saldo leído bajo el bloqueo: es
        # el único punto del sistema donde esa comparación es de fiar.
        saldo = saldo_de(estudiante)
        if saldo < total:
            # ── EL MENSAJE VA EN PESOS, NO EN `Decimal` ─────────────────
            # `HU-19` la opera el cajero con una fila delante: «El saldo es de
            # 46500.00» obliga a traducir mentalmente, y a las tres de la tarde
            # eso se lee mal. Se formatea con **el único formateador del
            # sistema**, `billetera.templatetags.dinero`, que es una función
            # normal además de un filtro — importarla aquí no rompe la regla de
            # un solo sitio, la cumple.
            #
            # Y dice **cuánto falta**, que es lo que el cajero necesita para
            # decirle al estudiante si quita algo o si su acudiente recarga.
            # ─────────────────────────────────────────────────────────────
            raise SaldoInsuficiente(
                f"No alcanza: el saldo es {dinero(saldo)} y la venta suma "
                f"{dinero(total)}. Faltan {dinero(total - saldo)}.",
                saldo=saldo,
                total=total,
            )

    # ── 3. ESCRIBIR ─────────────────────────────────────────────────────────
    venta = Venta.objects.create(
        cajero=actor, estudiante=estudiante, medio_pago=medio_pago
    )

    # ── LA INSTANTÁNEA (`TT-84`, `DT-8`, `HU-22`) ───────────────────────────
    # El precio y los nutrientes se copian **de la fila bloqueada**, que es la
    # que se acaba de leer para validar. No se vuelve a consultar el producto:
    # entre una lectura y otra podría haberse editado, y entonces la venta se
    # habría cobrado a un precio y registrado a otro.
    #
    # Los nutrientes salen de `CAMPOS_DE_LA_INSTANTANEA` y no de una lista
    # escrita aquí: el día que el catálogo declare un nutriente más, esto lo
    # copia sin tocarse. Si la lista se quedara corta, el dato nuevo no llegaría
    # al historial y nadie lo echaría en falta hasta el reporte de `HU-30`.
    LineaVenta.objects.bulk_create(
        [
            LineaVenta(
                venta=venta,
                producto=producto,
                cantidad=lineas[producto.id],
                precio_unitario=producto.precio,
                **{
                    campo: getattr(producto, campo)
                    for campo in LineaVenta.CAMPOS_DE_LA_INSTANTANEA
                },
            )
            for producto in productos
        ]
    )

    # Los dos libros, por su único punto de asiento (`DT-24`). El de inventario
    # se escribe también en la venta genérica; el de billetera, solo si hay
    # estudiante — no hay billetera de nadie que descontar.
    for producto in productos:
        asentar_en_el_inventario(
            producto=producto,
            tipo=TipoDeMovimientoDeInventario.VENTA,
            cantidad=-lineas[producto.id],
            venta=venta,
        )

    if estudiante is not None:
        asentar_en_la_billetera(
            estudiante=estudiante,
            tipo=TipoDeMovimiento.VENTA,
            monto=-total,
            venta=venta,
        )

    return venta


def total_de(venta):
    """Lo que sumó la venta, **con los precios de entonces** (`HU-22`).

    **No hay columna `total`**, y es la misma decisión que `DT-4` y `DT-5`: un
    total guardado al lado de las líneas es una segunda fuente de verdad que un
    día dirá algo distinto. Aquí sí se puede calcular sin riesgo porque los
    sumandos ya no cambian: desde `TT-84` el precio vive congelado en la línea
    (`DT-8`), así que subir el precio de una empanada mañana no reescribe lo que
    costó la venta de hoy.

    Es la diferencia entre calcular un dato derivable —legítimo— y leer uno que
    se movió por debajo, que es lo que hacía esta función antes de `TT-84`.
    """
    return sum((linea.importe for linea in venta.lineas.all()), Decimal("0.00"))
