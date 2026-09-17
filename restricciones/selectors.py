"""Lecturas del control parental (`DT-15`).

Cubre `HU-09` … `HU-13`, `HU-38` y `HU-61`.

Como los servicios, estos selectores no conocen `request`: reciben lo que
necesitan como argumentos y devuelven datos, nunca respuestas HTTP.
"""

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch

from catalogo.models import Alergeno, Producto, ProductoAlergeno
from cuentas.models import Rol
from restricciones.models import (
    AsientoDeRestriccion,
    LimiteDiario,
    RestriccionAlergeno,
    RestriccionesDelEstudiante,
    RestriccionProducto,
)


def limite_diario_de(estudiante):
    """El `LimiteDiario` del estudiante, o `None` si no tiene ninguno (`HU-09`).

    **`None` es una respuesta legítima y la más frecuente al principio**: no hay
    fila significa que el acudiente no configuró cupo, que es distinto de un cupo
    de cero (ver `restricciones.models.LimiteDiario`). Devolver `Decimal("0")`
    para el caso sin configurar dejaría a quien llame sin forma de distinguir «no
    puede gastar nada» de «puede gastar lo que tenga», que son opuestos.

    **No autoriza a nadie, y es a propósito.** Un selector no sabe quién
    pregunta: quien llama decide si puede. En `INT-1` eso lo hace
    `estudiante_a_cargo`, que solo alcanza a los estudiantes propios (`DT-11`);
    en la venta lo hará el servicio de `TT-116`, donde no hay ningún acudiente a
    quien preguntarle. `[S11]` concede la **consulta** a los cuatro roles
    (`HU-38`), así que la restricción de lectura no vive aquí.

    Este es el selector de un dato; el de **las restricciones vigentes de un
    estudiante**, que compone el límite con los productos y alérgenos bloqueados,
    es `TT-106` y llega en `PR-05`.
    """
    return LimiteDiario.objects.filter(estudiante=estudiante).first()


def productos_bloqueados_de(estudiante):
    """Las `RestriccionProducto` vigentes del estudiante (`HU-10`).

    Devuelve un `QuerySet` sin evaluar, ordenado por nombre de producto —el
    orden lo fija el modelo y aquí no se repite porque no cambia—, con el
    producto y su categoría ya traídos: quien pinta la lista los necesita todos
    y sin esto serían tantas consultas como productos bloqueados.

    **Es una lista de verdad, y esa es la diferencia con `HU-11`.** Lo que hay
    aquí son los productos que el acudiente señaló uno a uno. El bloqueo por
    alérgeno no se responde desde esta función ni desde ninguna lista guardada:
    se evalúa cruzando la condición con lo que cada producto declara (`INV-5`,
    `DT-7`), y llega en `TT-100`.

    **No autoriza a nadie**, como el resto de selectores: quien llama decide si
    puede. `[S11]` concede la **consulta** de restricciones a los cuatro roles
    (`HU-38`).
    """
    return RestriccionProducto.objects.filter(
        estudiante=estudiante
    ).select_related("producto", "producto__categoria")


def identificadores_de_productos_bloqueados(estudiante):
    """Solo los `id` de los productos bloqueados, como conjunto.

    Existe para pintar la pantalla de `TT-99`, que recorre el catálogo entero y
    tiene que saber de cada producto si está bloqueado. Con esto es **una
    consulta**; preguntando producto a producto serían tantas como productos.

    Un `set` y no una lista: lo que se hace con esto es `in`.
    """
    return set(
        RestriccionProducto.objects.filter(estudiante=estudiante).values_list(
            "producto_id", flat=True
        )
    )


def bloqueos_entre(estudiante, productos):
    """De esos productos, los que este estudiante tiene bloqueados (`HU-60`).

    Devuelve las `RestriccionProducto` que coinciden, con su producto ya traído.
    Vacío si ninguno lo está.

    **Existe para la venta, y por eso pregunta solo por lo que se está
    cobrando.** `identificadores_de_productos_bloqueados` trae toda la lista del
    estudiante, que es lo que necesita la pantalla del acudiente; aquí la
    pregunta es otra —«¿alguno de estos cuatro?»— y se hace con un `IN` sobre lo
    que hay en el carrito. Es una consulta, dentro de una transacción con cola
    delante (`DT-6`).

    **No resuelve el bloqueo por alérgeno**, y no es un olvido: eso no se
    responde desde una lista sino cruzando la condición con lo que cada producto
    declara (`INV-5`, `DT-7`), y llega con `TT-100`. Meterlo aquí sería
    justamente materializar la lista que `INV-5` prohíbe.
    """
    return RestriccionProducto.objects.filter(
        estudiante=estudiante, producto__in=productos
    ).select_related("producto")


def alergenos_bloqueados_de(estudiante):
    """Las `RestriccionAlergeno` vigentes del estudiante (`HU-11`).

    Devuelve un `QuerySet` sin evaluar, con el alérgeno ya traído.

    **Esto es la lista de condiciones, no la de productos.** Lo que hay aquí son
    los alérgenos que el acudiente señaló; qué productos quedan fuera por su
    causa lo responde `productos_cubiertos_por_alergeno`, y lo responde
    calculándolo.
    """
    return RestriccionAlergeno.objects.filter(estudiante=estudiante).select_related(
        "alergeno"
    )


def identificadores_de_alergenos_bloqueados(estudiante):
    """Solo los `id` de los alérgenos bloqueados, como conjunto.

    Para pintar la pantalla de `TT-102`, que recorre el catálogo de alérgenos y
    tiene que saber de cada uno si está bloqueado. Con esto es **una** consulta.
    """
    return set(
        RestriccionAlergeno.objects.filter(estudiante=estudiante).values_list(
            "alergeno_id", flat=True
        )
    )


def productos_cubiertos_por_alergeno(estudiante):
    """Los productos que este estudiante no puede comprar **por su alérgeno**.

    ═══════════════════════════════════════════════════════════════════════
    **ESTA FUNCIÓN ES `INV-5`. SU FORMA IMPORTA MÁS QUE SU RESULTADO.**

    No lee ninguna lista guardada, porque no existe: cruza las restricciones de
    alérgeno del estudiante con `catalogo.ProductoAlergeno` **cada vez que se la
    llama**. De ahí salen las dos propiedades que `HU-11` pide y que ninguna
    lista materializada puede dar:

    · Un producto que la cafetería añada mañana declarando ese alérgeno queda
      cubierto **sin que nadie recalcule nada**.
    · Un producto que hoy existe y mañana declara el alérgeno queda cubierto en
      el mismo momento en que lo declara.

    Y la simétrica, que también importa: retirar la declaración de un producto lo
    descubre en el acto. La verdad vive en `ProductoAlergeno`, en un solo sitio.

    **Si alguien convierte esto en una tabla «porque consulta más rápido»,
    `INV-5` se rompe y no se nota.** No falla nada ese día: falla semanas
    después, en la caja, con un niño alérgico delante.
    ═══════════════════════════════════════════════════════════════════════

    `distinct()` no sobra: un producto que declare dos alérgenos bloqueados del
    mismo estudiante saldría dos veces del cruce.

    **No incluye los de `HU-10`.** Son dos restricciones distintas y se
    consultan por separado; quien necesite las dos —la pantalla de `TT-106`, la
    venta de `TT-113`— las junta arriba.
    """
    return Producto.objects.filter(
        declaraciones__alergeno__bloqueos__estudiante=estudiante
    ).distinct()


def alergenos_que_bloquean(estudiante, producto):
    """Qué alérgenos bloqueados de ese estudiante declara ese producto.

    Devuelve un `QuerySet` de `Alergeno`, vacío si ninguno. Es la pregunta que
    hará la venta en `TT-113` —«¿por qué no puede comprar esto?»— y la que
    permite decírselo al cajero con el nombre del alérgeno y no con un «está
    prohibido» sin explicación.

    Se calcula igual que `productos_cubiertos_por_alergeno`, mirando de un lado
    lo que el producto declara y del otro lo que el acudiente bloqueó. Ninguna
    de las dos es una lista guardada (`INV-5`).
    """
    return Alergeno.objects.filter(
        declaraciones__producto=producto, bloqueos__estudiante=estudiante
    ).distinct()


def alergenos_que_bloquean_entre(estudiante, productos):
    """De esos productos, cuáles caen por un alérgeno bloqueado, y por cuál (`HU-18`).

    Devuelve las `catalogo.ProductoAlergeno` que cruzan: una fila por pareja
    producto–alérgeno, con los dos ya traídos. Vacío si ninguno cae.

    **Es la pregunta de la venta, y por eso pregunta solo por lo que se está
    cobrando** (`TT-113`). `productos_cubiertos_por_alergeno` responde «qué no
    puede comprar este estudiante», que es la lista entera del catálogo y no
    cabe en una transacción con cola delante; aquí la pregunta es «¿alguno de
    estos cuatro?», y se resuelve con un `IN`. Una consulta, dentro del bloqueo
    (`DT-6`).

    ── SIGUE SIENDO LA CONDICIÓN, NO UNA LISTA (`INV-5`) ───────────────────
    Lo que se cruza es `RestriccionAlergeno` con `catalogo.ProductoAlergeno`
    **en el momento de cobrar**. No hay ninguna lista de productos prohibidos
    guardada en ninguna parte, y por eso un producto que la cafetería agregó
    esta mañana declarando maní queda rechazado esta misma tarde sin que nadie
    recalcule nada.

    Devuelve la declaración y no solo el producto porque el cajero necesita
    **por qué**: «contiene maní» le deja explicarlo y le dice que eso no se
    arregla quitando el renglón de otra forma. Un producto que declare dos
    alérgenos bloqueados del mismo estudiante sale dos veces, una por cada
    motivo, y es correcto: son dos razones distintas.
    ─────────────────────────────────────────────────────────────────────────
    """
    return ProductoAlergeno.objects.filter(
        producto__in=productos, alergeno__bloqueos__estudiante=estudiante
    ).select_related("producto", "alergeno")


def historial_de_restricciones(estudiante, limite=None):
    """Lo que se hizo con las restricciones de un estudiante, lo último primero.

    Segundo criterio de `HU-12`: el retiro queda asentado, y asentado significa
    **legible**. Un registro que nadie puede leer no hace auditable nada; esta
    es la función que lo convierte en algo que se mira.

    Devuelve un `QuerySet` sin evaluar, con el actor, el producto y el alérgeno
    ya traídos: quien pinta el historial los necesita todos y sin esto serían
    tres consultas por fila.

    `limite` recorta para las pantallas que enseñan «los últimos cambios».
    **Sin él se devuelve el historial entero**, que es lo que una auditoría
    necesita: media lista no reconstruye nada.

    El orden lo fija el modelo —`-creado_en`— y se repite aquí explícito: quien
    lea esta función no tiene por qué ir al `Meta` a averiguarlo.
    """
    asientos = AsientoDeRestriccion.objects.filter(
        estudiante=estudiante
    ).select_related("actor", "producto", "alergeno").order_by("-creado_en")

    return asientos[:limite] if limite is not None else asientos


@dataclass(frozen=True)
class RestriccionesVigentes:
    """Todo lo que hoy limita lo que un estudiante puede comprar (`TT-106`).

    Las tres restricciones juntas, porque **juntas es como significan algo**.
    «Tiene un cupo de $8.000» sin «y el maní está bloqueado» es media respuesta,
    y quien las lee —el cajero al cobrar (`HU-13`), los cuatro roles al
    consultar (`HU-38`), la venta al validar (`TT-113`, `TT-116`)— las necesita
    todas o no necesita ninguna.

    Es un objeto y no tres valores sueltos por lo mismo que `InformacionDeCobro`
    de `ventas`: el día que haya una cuarta restricción hay **un solo sitio**
    donde añadirla, y ninguna pantalla se queda enseñando dos de tres sin que
    nadie lo note.

    ── LOS ALÉRGENOS NO TRAEN SU LISTA DE PRODUCTOS, Y ES `INV-5` ──────────
    `alergenos` son las condiciones que el acudiente bloqueó, no los productos
    que hoy las declaran. Meter aquí esa lista la convertiría en un dato —algo
    que alguien podría guardar, cachear o pasar por ahí— y es exactamente lo que
    `INV-5` prohíbe. Qué productos quedan fuera se pregunta cuando hace falta,
    con `productos_cubiertos_por_alergeno` o `alergenos_que_bloquean`.
    ─────────────────────────────────────────────────────────────────────────
    """

    #: El `LimiteDiario` del estudiante, o `None` si no tiene cupo. `None` no es
    #: cero: es «puede gastar lo que tenga» (`HU-09`, `HU-61`).
    limite: LimiteDiario | None
    #: `QuerySet` de `RestriccionProducto`, sin evaluar.
    productos: object
    #: `QuerySet` de `RestriccionAlergeno`, sin evaluar. **Las condiciones, no
    #: los productos que hoy las declaran** (`INV-5`).
    alergenos: object

    @property
    def hay_alguna(self):
        """Si el estudiante tiene algo configurado, sea de la clase que sea.

        Existe para que una pantalla no tenga que preguntar por las tres y
        acordarse de las tres. Un `or` olvidado es una pantalla que dice «sin
        restricciones» sobre un niño alérgico.
        """
        return bool(self.limite or self.productos or self.alergenos)


def restricciones_vigentes(estudiante):
    """Las tres restricciones de un estudiante, de una vez (`TT-106`, `HU-13`).

    **El único sitio por el que se leen juntas.** Lo usan el panel de cobro
    (`TT-109`) y, en lo que a cada una toca, las validaciones de la venta. El
    admin de `TT-112` lee el mismo objeto armado desde lo ya traído
    (`restricciones_precargadas`), para no pagar tres consultas por fila.

    ── NO AUTORIZA A NADIE, Y ESO TAMBIÉN ES `INV-4` ───────────────────────
    Un selector no sabe quién pregunta. Parece que aquí debería exigirse el rol
    —son datos de un menor—, pero `[S11]` concede **consultar** restricciones a
    los cuatro roles (`HU-38`): no hay a quién negárselo. Lo que `INV-4` prohíbe
    es **escribirlas**, y eso no se defiende en una lectura: se defiende en los
    servicios y en los permisos por modelo (`TT-107`, `DT-11`).

    Quien llama decide a qué estudiante puede llegar: `estudiante_a_cargo` en
    `INT-1`, la identificación por tarjeta en `INT-2` y
    `estudiantes_con_sus_restricciones` en `INT-3`.
    ─────────────────────────────────────────────────────────────────────────

    Devuelve `QuerySet` sin evaluar en las dos listas: quien solo necesite
    contarlas no paga por traerlas.
    """
    return RestriccionesVigentes(
        limite=limite_diario_de(estudiante),
        productos=productos_bloqueados_de(estudiante),
        alergenos=alergenos_bloqueados_de(estudiante),
    )


# --- `HU-38`. La consulta de los cuatro roles ---------------------------------
#
# `[S11]`, fila «Consultar restricciones de un estudiante»: Sí en las cuatro
# columnas. Cada rol llega por su interfaz y con su propio alcance, y ninguno de
# los cuatro caminos escribe:
#
# | Rol           | Dónde   | A qué estudiantes llega                            |
# |---------------|---------|----------------------------------------------------|
# | Acudiente     | `INT-1` | los suyos: `estudiante_a_cargo`                    |
# | Cajero        | `INT-2` | al que identifica: `informacion_de_cobro` (TT-109) |
# | Administrador | `INT-3` | todos: `estudiantes_con_sus_restricciones`         |
# | Institución   | `INT-3` | todos: `estudiantes_con_sus_restricciones`         |

#: Los dos roles que consultan desde el admin. **No son «los que pueden
#: consultar»** —esos son los cuatro—, sino los que lo hacen por `INT-3`: el
#: acudiente no entra al admin (`DT-2`) y el cajero tampoco (`cuentas.0004`).
CONSULTAN_EN_LA_ADMINISTRACION = (Rol.ADMINISTRADOR, Rol.INSTITUCION)


def estudiantes_con_sus_restricciones(*, actor):
    """Todos los estudiantes, cada uno con sus restricciones ya traídas (`TT-111`, `HU-38`).

    La consulta de la administración de la cafetería y de la institución, que
    trabajan en `INT-3` (`DT-2`). **Solo lee**: no hay servicio detrás, y lo que
    devuelve es el proxy de `RestriccionesDelEstudiante`, cuyo único permiso es
    `view`.

    ── POR QUÉ LOS DOS VEN A TODOS ─────────────────────────────────────────
    La cafetería atiende a cualquier estudiante del colegio, así que necesita
    saber quién es alérgico al maní antes de que llegue a la caja — no solo el
    cajero en el momento de cobrar. La institución administra a todos (`HU-44`).
    Ninguno de los dos tiene un subconjunto natural que filtrar.
    ─────────────────────────────────────────────────────────────────────────

    **Lo que no autoriza es a más que eso.** Devuelve estudiantes para colgarles
    sus restricciones, no la ficha del estudiante: quien pinta esto decide qué
    campos enseña, y el admin de `TT-112` no enseña ni el código de tarjeta ni
    el acudiente. La comprobación del rol va aquí y no en el admin porque es
    donde vive la regla (`DT-11`, `DT-15`); el admin la repite, como en el resto
    de `INT-3`.

    Una consulta por tabla y no una por fila: el límite viene con el estudiante
    y las dos listas prefetcheadas con su producto y su alérgeno. Para leerlas
    como las lee el resto del sistema, `restricciones_precargadas`.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Consultar restricciones exige identificarse.")
    if actor.rol not in CONSULTAN_EN_LA_ADMINISTRACION:
        raise PermissionDenied(
            "Desde la administración consultan las restricciones la cafetería y "
            "la institución. El acudiente las ve en su panel y el cajero al "
            "identificar al estudiante (HU-38, [S11])."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")

    return (
        RestriccionesDelEstudiante.objects.select_related("limite_diario")
        .prefetch_related(
            Prefetch(
                "productos_bloqueados",
                queryset=RestriccionProducto.objects.select_related("producto"),
            ),
            Prefetch(
                "alergenos_bloqueados",
                queryset=RestriccionAlergeno.objects.select_related("alergeno"),
            ),
        )
        .order_by("nombre")
    )


def restricciones_precargadas(estudiante):
    """Las `RestriccionesVigentes` de un estudiante de `estudiantes_con_sus_restricciones`.

    **El mismo objeto que `restricciones_vigentes`**, armado con lo que ya se
    trajo en vez de con tres consultas más. Existe para que el listado del admin
    no pinte las restricciones de una forma y el panel de cobro de otra: las dos
    pantallas leen un `RestriccionesVigentes`, y `hay_alguna` significa lo mismo
    en ambas.

    Sobre un estudiante que no venga precargado **también responde bien**, solo
    que consultando: los gestores relacionados van a la base cuando no hay nada
    en caché.

    `getattr` con `None` en el límite no esconde un error: la relación inversa
    de un `OneToOneField` lanza al leerla cuando no hay fila, y no haber fila es
    exactamente «sin límite» (`LimiteDiario`).
    """
    return RestriccionesVigentes(
        limite=getattr(estudiante, "limite_diario", None),
        productos=estudiante.productos_bloqueados.all(),
        alergenos=estudiante.alergenos_bloqueados.all(),
    )
