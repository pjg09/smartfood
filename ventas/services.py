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
from billetera.selectors import consumo_del_dia, saldo_de
from billetera.services import asentar as asentar_en_la_billetera
from billetera.templatetags.dinero import dinero
from catalogo.models import Producto
from cuentas.models import Rol
from inventario.models import TipoDeMovimientoDeInventario
from inventario.selectors import existencias_por_producto
from inventario.services import asentar as asentar_en_el_inventario
from personas.services import EstudianteNoOperativo, comprobar_que_puede_operar
from restricciones.selectors import (
    alergenos_que_bloquean_entre,
    bloqueos_entre,
    limite_diario_de,
)
from ventas.models import (
    EstadoDelPedido,
    LineaVenta,
    MedioDePago,
    OrigenDeLaVenta,
    PedidoAnticipado,
    Venta,
)
from ventas.selectors import existencias_sin_reservar


class VentaRechazada(ValidationError):
    """La venta no se realiza, y **no se escribe nada**.

    Una sola familia de errores para todos los motivos de rechazo —saldo,
    existencias, carrito vacío— porque quien llama hace lo mismo con todos:
    enseñar el motivo y no cobrar. Los motivos concretos son subclases para que
    una prueba pueda exigir **cuál**, no solo que falló.

    ── `motivo`: LA ETIQUETA QUE LLEGA HASTA LA PANTALLA (`TT-132`) ────────
    La subclase distingue el rechazo **en Python**. `motivo` lo distingue en el
    HTML: la vista lo pone en el fragmento del ticket y una prueba puede exigir
    cuál se enseñó sin buscar un texto dentro de otro texto —que es lo que se
    rompe en cuanto alguien reescribe el mensaje—.

    Se introduce aquí porque `HU-60` es el primer motivo que **no** se distingue
    por la cifra que lleva, y porque vienen tres más: `TT-114` (alérgeno),
    `TT-117` (límite diario) y `TT-126` (desactivado). Con un mecanismo por
    historia acabarían siendo cuatro maneras distintas de decir lo mismo.
    ─────────────────────────────────────────────────────────────────────────
    """

    #: Etiqueta estable del motivo, para la pantalla y para las pruebas.
    motivo = "rechazo"


class CarritoVacio(VentaRechazada):
    """Cobrar sin líneas no es una venta de cero: no es una venta."""

    motivo = "carrito-vacio"


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

    motivo = "saldo-insuficiente"

    def __init__(self, mensaje, *, saldo=None, total=None):
        super().__init__(mensaje)
        self.saldo = saldo
        self.total = total
        self.faltante = None if saldo is None or total is None else total - saldo


class ExistenciasInsuficientes(VentaRechazada):
    """No se vende lo que no hay.

    `motivo = "existencias-insuficientes"`.

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

    motivo = "existencias-insuficientes"


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


class ProductoBloqueado(VentaRechazada):
    """`HU-60`, `INV-4`. El acudiente prohibió ese producto a este estudiante.

    ── EL CAJERO NO TIENE CÓMO FORZARLA, Y ESO ES LA HISTORIA ──────────────
    No hay argumento que la salte, ni una variante del servicio que la omita,
    ni un permiso que la levante. `INV-4` dice que las restricciones no las
    desactiva la cafetería, y el primer criterio de `HU-13` precisa que el
    cajero no dispone de ninguna acción para **omitirlas**. Un aviso descartable
    sería justamente una acción para omitirla.

    Si algún día hace falta una excepción —el estudiante olvidó el almuerzo y su
    acudiente autoriza por teléfono—, la salida es que el acudiente retire la
    restricción desde su interfaz (`HU-12`), que deja asiento. No un botón en la
    caja.
    ─────────────────────────────────────────────────────────────────────────

    Lleva `productos`, los nombres de lo bloqueado, para que una prueba pueda
    exigir **cuál** sin buscar un texto dentro de otro texto.
    """

    motivo = "producto-bloqueado"

    def __init__(self, mensaje, *, productos=()):
        super().__init__(mensaje)
        self.productos = tuple(productos)


class AlergenoBloqueado(VentaRechazada):
    """`HU-18`, `INV-5`, escenario crítico **`TST-1`**.

    ═══════════════════════════════════════════════════════════════════════
    **ES EL RECHAZO QUE DA SENTIDO AL PROYECTO.** Un niño alérgico no puede
    comprar lo que le hace daño, y el momento en que eso importa es este.

    No se decide contra ninguna lista de productos prohibidos: se cruza la
    condición que el acudiente bloqueó con lo que cada producto declara, en el
    instante del cobro (`INV-5`, `DT-7`). Un producto que la cafetería agregó
    esta mañana declarando maní se rechaza esta tarde **sin que nadie
    recalcule nada** — que es literalmente el segundo criterio de `HU-11`.
    ═══════════════════════════════════════════════════════════════════════

    **El cajero no tiene cómo forzarla**, igual que en `ProductoBloqueado` y por
    el mismo motivo: `INV-4` y el primer criterio de `HU-13`. No hay argumento
    que la salte ni permiso que la levante, y un aviso descartable sería una
    acción para omitirla. La única salida es que el acudiente retire el bloqueo
    desde su interfaz (`HU-12`), que deja asiento.

    Lleva `productos` y `alergenos` —los nombres— para que el mensaje diga
    **cuál y por qué**, y para que una prueba pueda exigirlos sin buscar un
    texto dentro de otro texto.
    """

    motivo = "alergeno-bloqueado"

    def __init__(self, mensaje, *, productos=(), alergenos=()):
        super().__init__(mensaje)
        self.productos = tuple(productos)
        self.alergenos = tuple(alergenos)


class EstudianteNoPuedeComprar(VentaRechazada):
    """`HU-50`, `INVD-2`. Desactivado o de baja: la tarjeta no compra.

    ── POR QUÉ ES UNA `VentaRechazada` Y NO LA EXCEPCIÓN DE `personas` ─────
    La regla es de `personas` y allí se queda: `comprobar_que_puede_operar` es
    la puerta única de `INVD-2` y esta clase **no la reimplementa**, la traduce.
    Lo que aporta es la etiqueta de motivo (`TT-126`): sin ella, el rechazo
    llegaba al ticket como «rechazo» a secas, mezclado con cualquier otro fallo,
    y el cajero no podía distinguir «esta tarjeta está bloqueada» de «no alcanza
    el saldo» — que es el cuarto criterio de la historia.
    ─────────────────────────────────────────────────────────────────────────

    **Una sola etiqueta para los dos estados, y el mensaje dice cuál.** Son dos
    situaciones distintas para quien está en la caja —una se arregla yendo a
    secretaría y la otra no se arregla— pero para la venta son lo mismo: no se
    cobra, y no hay nada que el cajero pueda hacer en el mostrador. Dos etiquetas
    obligarían a toda pantalla futura a tratar por separado dos casos que se
    pintan igual.
    """

    motivo = "estudiante-no-opera"


class LimiteDiarioSuperado(VentaRechazada):
    """`HU-20`, `HU-09`, mitad del escenario crítico **`TST-2`**.

    El estudiante ya gastó hoy lo que su acudiente le fijó como tope, o esta
    venta lo pasaría. **Se rechaza aunque haya saldo de sobra**, y eso es
    exactamente lo que la historia pide: un límite que solo se cumple cuando
    además falta dinero no es un límite, es una coincidencia.

    ── SE DISTINGUE DEL SALDO, Y NO ES COSMÉTICA ───────────────────────────
    Es el segundo criterio de `HU-20` y el motivo por el que `TT-117` existe.
    Las dos cifras son de dinero y las dos rechazan, pero se arreglan de forma
    opuesta: «no alcanza el saldo» lo resuelve el acudiente recargando; «se
    acabó el cupo de hoy» **no lo resuelve ninguna recarga** —el cupo vuelve
    mañana, o lo cambia quien lo puso—. Decir el motivo equivocado manda al
    acudiente a recargar para que la venta se rechace igual.
    ─────────────────────────────────────────────────────────────────────────

    Lleva las cuatro cifras con las que se decidió —`limite`, `consumido`,
    `disponible` y `total`— para que el mensaje las diga sin volver a consultar
    nada y para que una prueba pueda exigirlas en vez de buscar un texto dentro
    de otro texto.
    """

    motivo = "limite-diario"

    def __init__(self, mensaje, *, limite=None, consumido=None, total=None):
        super().__init__(mensaje)
        self.limite = limite
        self.consumido = consumido
        self.total = total
        self.disponible = (
            None if limite is None or consumido is None else limite - consumido
        )


def _normalizar_lineas(lineas, *, vacio="No hay nada que cobrar."):
    """Deja `lineas` como `{UUID: entero positivo}`, o rechaza (`TT-144`).

    **Compartida por la venta y la reserva** desde `TT-144`. Estaba dentro de
    `registrar_venta` y se extrajo tal cual: la reserva necesita exactamente las
    mismas comprobaciones, y dos copias de esto es como una de las dos se queda
    sin el arreglo de la próxima.
    """
    if not lineas:
        raise CarritoVacio(vacio)

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

    return lineas


def _bloquear_y_validar(*, estudiante, lineas, existencias_de_los=None):
    """Los pasos 1 y 2 de `DT-6`, **compartidos por la venta y la reserva**.

    Devuelve `(productos, total)`, con los productos ya bloqueados.

    ── POR QUÉ ESTO ES UNA FUNCIÓN Y NO ESTÁ COPIADO EN LOS DOS SITIOS ─────
    Es **el riesgo de diseño que el plan del Sprint 4 marcó en rojo**. Aquí
    dentro viven las cuatro reglas de rechazo que construyeron los Sprints 2 y 3
    —estudiante desactivado, alérgeno bloqueado, producto bloqueado y cupo del
    día— más las existencias y el saldo.

    Si la reserva tuviera su propio flujo, esas reglas **no se le aplicarían**, y
    quedaría una puerta trasera para saltarse el control parental entero: el
    acudiente no podría comprarle a su hijo algo con un alérgeno bloqueado en la
    caja, pero sí reservárselo la noche anterior. Que haya una sola copia no es
    higiene, es la invariante.

    `HU-23` no menciona ninguna de las cuatro. Hay que saberlo.
    ─────────────────────────────────────────────────────────────────────────

    ── `existencias_de_los` ────────────────────────────────────────────────
    Qué cuenta como disponible. La venta del mostrador mira las existencias
    reales; la reserva mira las que quedan **descontando lo ya reservado y no
    entregado** (`existencias_sin_reservar`, `TT-144`), porque no descuenta
    inventario al cobrar y dos reservas del último paquete pasarían las dos.

    Es lo único que cambia entre las dos, y por eso es un argumento y no una
    rama dentro de la función: una rama invita a añadir la segunda.
    ─────────────────────────────────────────────────────────────────────────
    """
    if existencias_de_los is None:
        existencias_de_los = existencias_por_producto

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
    #
    # ── `HU-50`, `INVD-2`. LO PRIMERO: ¿ESTE ESTUDIANTE PUEDE COMPRAR? ──────
    # Va antes que cualquier restricción y que el saldo, porque con la tarjeta
    # bloqueada da igual lo que lleve en el carrito: ningún otro motivo describe
    # lo que pasa. Es además el único que no se arregla en el mostrador — ni
    # quitando un renglón, ni recargando—: hay que pasar por secretaría (`HU-49`).
    #
    # **La regla no se reimplementa aquí.** `comprobar_que_puede_operar` es la
    # puerta única de `INVD-2` y vive en `personas`, junto al estado; esto la
    # llama dentro del bloqueo y traduce su excepción a un rechazo de venta con
    # etiqueta propia (`TT-126`). Antes llegaba igualmente —`asentar` la exige al
    # escribir—, pero al final de todo y sin motivo distinguible.
    if estudiante is not None:
        try:
            comprobar_que_puede_operar(estudiante)
        except EstudianteNoOperativo as bloqueado:
            raise EstudianteNoPuedeComprar(str(bloqueado)) from bloqueado

    # **Las restricciones van primero, y el orden es una decisión.** Todas
    # rechazan; lo que cambia es qué se le dice al cajero que tiene la fila
    # delante:
    #
    # · «Está bloqueado» y «contiene maní» no cambian por recargar ni por
    #   reponer: son sobre el mundo, no sobre el estado de hoy.
    # · «No hay existencias» y «no alcanza el saldo» se arreglan los dos, y
    #   ofrecen una salida —quitar el renglón, recargar—.
    #
    # Con el orden al revés, a un estudiante con la billetera vacía que intenta
    # comprar algo prohibido se le contestaría «no alcanza», su acudiente
    # recargaría y volvería a pasar lo mismo. Es el mismo criterio con el que
    # `billetera.services.asentar` pone `INVD-2` antes que la validación de la
    # referencia a la venta.
    #
    # **Solo cuando hay estudiante.** Una venta a cliente genérico no tiene a
    # quién consultarle restricciones (`DEC-1`, `HU-53`): no hay persona detrás,
    # y quien compra sin tarjeta no es un estudiante del padrón.
    #
    # ── Y ENTRE LAS DOS, EL ALÉRGENO ANTES QUE EL PRODUCTO ──────────────────
    # `HU-18` (`TST-1`) antes que `HU-60`. Un producto puede caer por las dos:
    # estar en la lista de `HU-10` y además declarar un alérgeno bloqueado.
    # Cuando pasa, lo que el cajero tiene que poder decir es la alergia. «Lo
    # bloqueó tu acudiente» invita a pedirle al acudiente que lo quite, y con
    # una alergia de por medio esa conversación no puede empezar en la caja.
    # ────────────────────────────────────────────────────────────────────────
    if estudiante is not None:
        por_alergeno = list(alergenos_que_bloquean_entre(estudiante, productos))
        if por_alergeno:
            # Los nombres se recogen en el orden en que llegan y sin repetir:
            # un producto con dos alérgenos bloqueados sale una vez en la lista
            # de productos y dos veces en la de motivos, que es lo cierto.
            productos_afectados = list(
                dict.fromkeys(d.producto.nombre for d in por_alergeno)
            )
            alergenos = list(dict.fromkeys(d.alergeno.nombre for d in por_alergeno))
            enumerados = ", ".join(f"«{n}»" for n in productos_afectados)
            raise AlergenoBloqueado(
                f"{enumerados} {'contienen' if len(productos_afectados) > 1 else 'contiene'} "
                f"{', '.join(alergenos)}, que {estudiante.nombre} tiene bloqueado. "
                "La venta no se realiza: quita "
                f"{'esos renglones' if len(productos_afectados) > 1 else 'ese renglón'} "
                "para cobrar el resto.",
                productos=productos_afectados,
                alergenos=alergenos,
            )

        bloqueados = list(bloqueos_entre(estudiante, productos))
        if bloqueados:
            nombres = [b.producto.nombre for b in bloqueados]
            enumerados = ", ".join(f"«{n}»" for n in nombres)
            raise ProductoBloqueado(
                f"{enumerados} {'están' if len(nombres) > 1 else 'está'} "
                f"bloqueado{'s' if len(nombres) > 1 else ''} para "
                f"{estudiante.nombre} por decisión de su acudiente. Quita "
                f"{'esos renglones' if len(nombres) > 1 else 'ese renglón'} "
                "para poder cobrar el resto.",
                productos=nombres,
            )

    existencias = existencias_de_los(productos)
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
        # ── `HU-20`, `HU-09` (tercer criterio), mitad de `TST-2` ─────────────
        # **Va antes del saldo y después de las existencias, y las dos cosas
        # son deliberadas.** Antes del saldo, porque «no alcanza» mandaría al
        # acudiente a recargar para que la venta se rechazara igual: el cupo no
        # lo arregla ninguna recarga. Después de las existencias, porque «de eso
        # quedan dos» es sobre la vitrina y se resuelve en el acto.
        #
        # El consumo del día se lee **dentro del bloqueo**, como el saldo, y del
        # mismo libro (`INV-2`): no hay contador de consumo diario que pudiera
        # discrepar del historial. La billetera está bloqueada desde el paso 1,
        # así que dos cajas simultáneas no pueden leer las dos el mismo consumo
        # y colar dos ventas que juntas pasan el cupo.
        #
        # **Sin límite fijado no hay nada que comprobar**, y eso es distinto de
        # un cupo de cero: `limite_diario_de` devuelve `None` cuando el
        # acudiente no configuró ninguno (`LimiteDiario`, `HU-61`).
        limite = limite_diario_de(estudiante)
        if limite is not None:
            consumido = consumo_del_dia(estudiante)
            if consumido + total > limite.monto:
                disponible = limite.monto - consumido
                raise LimiteDiarioSuperado(
                    f"Se acabó el cupo de hoy: el límite diario de "
                    f"{estudiante.nombre} es {dinero(limite.monto)} y ya lleva "
                    f"{dinero(consumido)}. "
                    + (
                        f"Le quedan {dinero(disponible)} y la venta suma "
                        f"{dinero(total)}."
                        if disponible > 0
                        else "No le queda cupo para hoy."
                    )
                    + " Recargar no lo cambia: el cupo lo fija su acudiente.",
                    limite=limite.monto,
                    consumido=consumido,
                    total=total,
                )

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

    return productos, total


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

    **Las tres restricciones del control parental se evalúan aquí**, en el paso
    2 y por este orden: alérgeno (`TT-113`), producto bloqueado (`TT-131`) y
    cupo del día (`TT-116`). Las tres van antes del saldo, que es donde `DT-6`
    pide que vayan y lo que hace que el cajero lea el motivo que de verdad
    explica el rechazo.

    **Y antes que todas ellas, si el estudiante puede comprar** (`TT-125`,
    `INVD-2`): con la tarjeta bloqueada da igual qué lleve en el carrito.
    """
    _solo_el_cajero(actor)

    lineas = _normalizar_lineas(lineas)

    medio_pago = _medio_de_pago_de(estudiante, medio_pago)

    productos, total = _bloquear_y_validar(estudiante=estudiante, lineas=lineas)

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


def _solo_su_acudiente(actor, estudiante):
    """`[S11]`: el acudiente opera sobre **sus** estudiantes y sobre ningún otro.

    `TT-144`, `HU-23` —«se gestiona desde la aplicación del acudiente»—. Vive en
    el servicio y no en la vista porque `DT-15` no admite reglas que dependan de
    por dónde se entre.

    **Que sean suyos es la mitad que se olvida.** Un acudiente identificado es
    un actor legítimo; reservarle a un estudiante que no es su hijo es pagar con
    su billetera el consumo de otro. La comprobación va sobre el vínculo, no
    sobre el rol.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Reservar exige identificarse.")
    if actor.rol != Rol.ACUDIENTE:
        raise PermissionDenied(
            "Reservar el consumo por adelantado es del acudiente, y de ningún "
            "otro rol ([S11], HU-23)."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")
    if estudiante is None or estudiante.acudiente.usuario_id != actor.id:
        raise PermissionDenied(
            "Solo se reserva para los estudiantes a cargo de quien reserva."
        )


@transaction.atomic
def reservar(*, actor, estudiante, lineas):
    """Reserva y **cobra en el momento** el consumo de un estudiante (`HU-23`).

    Devuelve el `PedidoAnticipado` creado.

    Los tres criterios de la historia, y dónde se cumple cada uno:

    1. **El pedido se asocia al perfil del estudiante.** La `Venta` lo lleva, y
       la restricción `venta_cajero_segun_su_origen` no admite una reserva sin
       él: no hay reserva de un cliente genérico.
    2. **Se paga en el momento de reservarse.** El movimiento de billetera se
       asienta aquí, no al entregar. Es lo que `TT-146` comprueba.
    3. **Se gestiona desde la aplicación del acudiente.** `_solo_su_acudiente`.

    ── ES UNA VENTA ANTICIPADA, NO UN APARTADO ────────────────────────────
    Valida por **la misma función** que el cobro del mostrador,
    `_bloquear_y_validar`, y por eso hereda las cuatro reglas de rechazo que
    construyeron los Sprints 2 y 3: estudiante desactivado (`INVD-2`), alérgeno
    bloqueado (`INV-5`), producto bloqueado y cupo del día.

    **Ninguna de las cuatro aparece en `HU-23`.** Si esto tuviera su propio
    flujo, un acudiente no podría comprarle a su hijo en la caja algo con un
    alérgeno bloqueado, pero sí reservárselo la noche anterior — y el control
    parental entero tendría una puerta trasera. Es el riesgo de diseño que el
    plan del sprint marcó en rojo, y la única defensa es que no haya dos copias.
    ─────────────────────────────────────────────────────────────────────────

    ── LO QUE SÍ CAMBIA: NO DESCUENTA INVENTARIO ──────────────────────────
    El libro de inventario se mueve **al entregar** (`HU-25`, `TT-149`), no
    aquí. Decisión del equipo, registrada en `DT-33`.

    Tiene una consecuencia que hay que sostener: como las unidades no salen del
    libro, dos reservas del último paquete pasarían las dos. Por eso la reserva
    valida contra `existencias_sin_reservar` —existencias menos lo apartado por
    pedidos pendientes— y no contra las existencias a secas.

    **El hueco que queda es la caja**, que sigue mirando las existencias reales
    y puede vender lo apartado. Está anotado en `[S6]` de
    `./docs/reglas-de-la-venta.md` y lo decide `HU-25`, que es quien tiene que
    saber qué hacer cuando el estudiante llega y no hay lo suyo.
    ─────────────────────────────────────────────────────────────────────────

    **El medio de pago es la billetera y no se pregunta.** Hay estudiante, así
    que `HU-54` y `DEC-1` no dejan otro: el efectivo y la transferencia son de
    la venta genérica, y una reserva pagada en efectivo sería alguien poniendo
    billetes en una aplicación, que es lo que `ALC-OUT-01` deja fuera.
    """
    _solo_su_acudiente(actor, estudiante)

    lineas = _normalizar_lineas(lineas, vacio="No hay nada que reservar.")

    productos, total = _bloquear_y_validar(
        estudiante=estudiante,
        lineas=lineas,
        existencias_de_los=existencias_sin_reservar,
    )

    venta = Venta.objects.create(
        cajero=None,
        estudiante=estudiante,
        medio_pago=MedioDePago.BILLETERA,
        origen=OrigenDeLaVenta.RESERVA,
    )

    # La instantánea, igual que en el mostrador (`DT-8`, `HU-22`): el precio y
    # los nutrientes se copian de la fila bloqueada. Importa más aquí todavía —
    # entre reservar y entregar puede pasar una noche, y lo que se cobró no lo
    # puede reescribir una edición del catálogo de mañana.
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

    # **El cobro, ahora.** Por el único punto de asiento del libro (`DT-24`).
    # El de inventario no se toca: lo mueve la entrega (`DT-33`).
    asentar_en_la_billetera(
        estudiante=estudiante,
        tipo=TipoDeMovimiento.VENTA,
        monto=-total,
        venta=venta,
    )

    return PedidoAnticipado.objects.create(
        venta=venta, estado=EstadoDelPedido.PENDIENTE
    )
