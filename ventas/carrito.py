"""La venta en curso: qué se lleva y a quién se le cobra (`TT-81`).

**Esto no es dominio, es estado de pantalla.** No escribe en ninguna tabla y no
sabe de invariantes: guarda en la sesión lo que el cajero lleva montado para que
sobreviva a un refresco accidental y a los intercambios de HTMX, que van y vienen
sin memoria. Quien cobra de verdad es `ventas.services.registrar_venta`, y
**vuelve a validarlo todo** contra la base (`DT-6`); nada de lo que haya aquí se
da por bueno.

**Vive en el servidor y no en el navegador**, y esa es la decisión que conviene
no perder —está registrada como `DT-26`—. `DT-16` había previsto Alpine.js para
el carrito; el motivo de no usarlo es el mismo por el que `DT-25` descartó el
total vivo de la pantalla de recarga: **un carrito en el navegador necesita
formatear dinero en JavaScript**, y el dinero se escribe en un solo sitio
(`billetera/templatetags/dinero.py`). Con dos formateadores, la misma pantalla
acaba enseñando dos monedas.

Un renglón por producto, que es lo que `LineaVenta` admite (`TT-78`): añadir dos
veces el mismo producto **suma cantidades**, no apila líneas.
"""

from uuid import UUID

CLAVE_CARRITO = "carrito"
CLAVE_ESTUDIANTE = "estudiante_de_la_venta"


def _clave(producto_id):
    """El identificador como texto, o `None` si no es un `UUID`.

    ── EL CARRITO SOLO CONTIENE IDENTIFICADORES VÁLIDOS ────────────────────
    Es la invariante de este módulo, y se sostiene aquí porque es el único
    sitio por el que entra algo. Sin ella, un `POST` sin `producto` guardaba la
    cadena vacía como clave y **la siguiente consulta reventaba**: el selector
    filtra por `id__in` sobre un `UUIDField`, y Postgres recibe `''`.

    El resultado era un `500` donde tocaba un rechazo tranquilo. No se puede
    provocar desde la pantalla —todos los botones mandan `producto` por
    `hx-vals`, y «vaciar» no pasa por aquí—, pero una petición a mano bastaba, y
    la caja es el peor sitio para una traza de error.
    ─────────────────────────────────────────────────────────────────────────
    """
    try:
        return str(UUID(str(producto_id)))
    except (ValueError, AttributeError, TypeError):
        return None


def _guardar(sesion, carrito):
    sesion[CLAVE_CARRITO] = carrito
    # La sesión solo detecta cambios cuando se le reasigna una clave; mutar el
    # diccionario en sitio no la marca como sucia y el cambio se pierde en
    # silencio al terminar la petición.
    sesion.modified = True


def leer(sesion):
    """`{id_de_producto: cantidad}`, con los identificadores como texto.

    La sesión se serializa a JSON, así que las claves vuelven siempre como
    cadenas aunque se guardaran como `UUID`. Se acepta ese hecho en lugar de
    convertirlas de ida y vuelta: quien necesite el `UUID` lo construye al
    consultar la base, y así no hay dos formas del mismo dato circulando.
    """
    # Se filtra también al leer, y no solo al escribir: una sesión abierta antes
    # de esta comprobación puede traer una clave inválida guardada, y así se cura
    # sola en lugar de romper la pantalla hasta que alguien borre la cookie.
    return {
        clave: cantidad
        for clave, cantidad in sesion.get(CLAVE_CARRITO, {}).items()
        if _clave(clave) is not None
    }


def anadir(sesion, producto_id, cantidad=1):
    """Suma unidades de un producto. Si no estaba, lo pone.

    Un identificador que no es un `UUID` **se ignora en silencio**: el carrito
    queda como estaba. Quien llama recibe el carrito y pinta el ticket, así que
    la pantalla no cambia — que es exactamente lo que debe pasar cuando la
    petición no pedía nada reconocible.
    """
    clave = _clave(producto_id)
    if clave is None:
        return leer(sesion)

    carrito = leer(sesion)
    carrito[clave] = carrito.get(clave, 0) + cantidad
    if carrito[clave] <= 0:
        del carrito[clave]
    _guardar(sesion, carrito)
    return carrito


def quitar(sesion, producto_id):
    """Saca el renglón entero, no una unidad.

    Quitar de uno en uno ya lo hace `anadir(..., -1)`; esto es el gesto de
    «esto no era», que en una caja con cola es el que hace falta de verdad.
    """
    carrito = leer(sesion)
    carrito.pop(_clave(producto_id) or "", None)
    _guardar(sesion, carrito)
    return carrito


def vaciar(sesion):
    """Deja la venta en curso como recién abierta: sin líneas y sin cliente.

    Las dos cosas juntas y no solo el carrito: tras cobrar, dejar al estudiante
    puesto invitaría a cobrarle la siguiente venta a quien ya se fue.
    """
    sesion[CLAVE_CARRITO] = {}
    sesion[CLAVE_ESTUDIANTE] = None
    sesion.modified = True


def fijar_estudiante(sesion, estudiante):
    """Recuerda a quién se le está cobrando, o lo olvida si es `None`.

    Lo guarda la identificación (`HU-15`, `HU-16`) para que el cobro no dependa
    de un campo oculto que el navegador podría traer viejo: entre escanear y
    cobrar puede pasar otro escaneo, y quien manda es el último.
    """
    sesion[CLAVE_ESTUDIANTE] = str(estudiante.id) if estudiante is not None else None
    sesion.modified = True


def estudiante_id(sesion):
    return sesion.get(CLAVE_ESTUDIANTE)
