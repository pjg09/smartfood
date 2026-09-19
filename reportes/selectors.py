"""Lecturas de los reportes (`TT-155`, `DT-15`).

**Toda lectura no trivial pasa por aquí.** Como los servicios, estos selectores
no conocen `request`: reciben el actor como argumento y devuelven datos, nunca
respuestas HTTP.

**Esta app no escribe nada**, y mientras siga así no tendrá `services.py`. Un
reporte consolida hechos que otro dominio ya asentó; si algún día uno de ellos
necesitara escribir, eso sería un hecho nuevo y no un reporte.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import PermissionDenied
from django.db.models import (
    Case,
    Count,
    DateTimeField,
    DecimalField,
    ExpressionWrapper,
    F,
    IntegerField,
    Sum,
    When,
)
from django.db.models.functions import TruncDate
from django.utils import timezone

from billetera.models import MovimientoBilletera, TipoDeMovimiento
from billetera.selectors import saldo_de
from billetera.templatetags.dinero import dinero
from cuentas.models import Rol
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from reportes import referencia, reglas
from ventas.models import (
    CierreDeCaja,
    EstadoDelPedido,
    LineaVenta,
    MedioDePago,
    OrigenDeLaVenta,
    PedidoAnticipado,
    Venta,
)

# El importe de un renglón lo declara `ventas`, que es de quien es el renglón, y
# desde `TT-172` también lo usa el cierre de caja. Se importa en vez de
# repetirlo: dos expresiones para la misma cifra es como acaban dando cifras
# distintas (`DT-19`).
from ventas.selectors import DIFERENCIA_DEL_CIERRE, IMPORTE_DE_LA_LINEA

# **Cuándo se consumió un renglón**, que no siempre es cuándo se pagó (`[S2.3]`
# de `docs/reglas-de-frecuencia-de-consumo.md`). En el mostrador son el mismo
# momento; en una reserva, no: el acudiente puede pagar el domingo por la noche
# lo del lunes, y lo que la frecuencia mide es el lunes.
#
# `TruncDate` corta en la zona horaria del colegio —`America/Bogota`—, no en
# UTC: partir el día por UTC mandaría la compra de las 19:00 al día siguiente.
MOMENTO_DEL_CONSUMO = Case(
    When(
        venta__origen=OrigenDeLaVenta.RESERVA,
        then=F("venta__pedido_anticipado__entregado_en"),
    ),
    default=F("venta__creado_en"),
    output_field=DateTimeField(),
)
DIA_DEL_CONSUMO = TruncDate(MOMENTO_DEL_CONSUMO)


def _solo_su_acudiente(actor, estudiante):
    """`[S11]`: el consumo de un estudiante lo consulta **su** acudiente.

    La fila «Consultar reportes de consumo de su hijo» de `[S11]` concede a
    `USR-2` y **a ningún otro rol**: ni la cafetería, ni la institución. Es el
    segundo criterio de `HU-30` y la comprobación vive en la capa de datos, no
    en un enlace que no se dibuja (`DT-11`, `INV-4`) — quien escriba la URL a
    mano recibe lo mismo.

    **Que sean suyos es la mitad que se olvida**, y aquí más que en ninguna otra
    puerta: lo que hay detrás es el registro de lo que un menor come y a qué hora
    está en la cafetería. Un acudiente identificado es un actor legítimo; leer el
    consumo del hijo de otro no lo es. Por eso se comprueba el vínculo, no el
    rol.

    Se mira `estudiante.acudiente.usuario_id` y no se vuelve a consultar la lista
    de estudiantes a cargo: es la misma condición que `personas.selectors`
    filtra, resuelta sobre una fila que la vista ya trajo.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Consultar el consumo exige identificarse.")
    if actor.rol != Rol.ACUDIENTE:
        raise PermissionDenied(
            "El historial de consumo de un estudiante es de su acudiente, y de "
            "ningún otro rol (HU-30, [S11])."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")
    if estudiante is None or estudiante.acudiente.usuario_id != actor.id:
        raise PermissionDenied(
            "Solo se consulta el consumo de los estudiantes a cargo de quien "
            "pregunta."
        )


def historial_de_consumo(*, actor, estudiante):
    """Las compras de un estudiante, de la más reciente a la más antigua.

    `TT-155`, `HU-30`, `ALC-IN-20`. Devuelve un `QuerySet` de `Venta` con sus
    líneas ya traídas: cada una lleva **lo que el producto declaraba al
    venderse**, no lo que declara hoy.

    ── LEE LA INSTANTÁNEA, NUNCA EL PRODUCTO ───────────────────────────────
    El precio y los nutrientes salen de `LineaVenta`, que los copió al asentar
    la venta (`TT-84`, `DT-8`). El producto se trae **solo por el nombre**, que
    no se copia porque la clave ajena va con `PROTECT` y siempre se puede leer.

    Si alguien sustituye aquí un campo de la línea por el del producto, editar
    un precio reescribiría lo que costó el mes pasado y corregir una ficha
    nutricional cambiaría lo que un niño comió: el historial dejaría de ser un
    historial para ser una proyección del catálogo de hoy sobre el pasado, y
    `HU-22` quedaría rota hacia atrás sin que nada fallara.
    ─────────────────────────────────────────────────────────────────────────

    ── LAS RESERVAS ENTRAN, Y LA PANTALLA DICE EN QUÉ ESTADO ESTÁN ─────────
    Una reserva **es una venta** (`DT-32`): está pagada, tiene sus líneas y su
    instantánea. Esconder las que todavía no se han entregado dejaría fuera del
    historial dinero que ya salió de la billetera. Por eso se traen todas y
    `pedido_anticipado` viene resuelto, para que la pantalla pueda distinguir lo
    consumido de lo que está esperando en el mostrador.
    ─────────────────────────────────────────────────────────────────────────

    **Las ventas a cliente genérico no aparecen y no hay que excluirlas**
    (`DEC-1`, `HU-53`): no tienen estudiante, así que el filtro no las alcanza.
    Ese es justamente el motivo por el que la venta genérica no tiene historial
    de nadie.

    `total` y `unidades` se anotan en la base. `total` es la misma suma que
    `ventas.services.total_de` —precio congelado por unidades—, calculada aquí
    por SQL porque esta pantalla lista muchas ventas y aquella recorre las
    líneas de una sola. `reportes/tests_historial.py` compara las dos cifras
    para que no puedan separarse en silencio.

    **Sin límite ni paginación**, y es deliberado: `HU-30` pide el historial, no
    su última página. Recortarlo por comodidad dejaría al acudiente creyendo que
    eso es todo lo que su hijo compró.
    """
    _solo_su_acudiente(actor, estudiante)

    return (
        Venta.objects.filter(estudiante=estudiante)
        # `pedido_anticipado` es un uno a uno inverso: entra en el
        # `select_related` y ahorra una consulta por reserva al pintar su estado.
        .select_related("pedido_anticipado")
        .prefetch_related("lineas__producto")
        .annotate(total=Sum(IMPORTE_DE_LA_LINEA), unidades=Sum("lineas__cantidad"))
        # El orden lo fija el modelo —`-creado_en`— y se repite aquí de forma
        # explícita, como en `billetera.selectors.historial_de`: quien lea esta
        # función no tiene por qué ir al `Meta` a averiguar cómo llega un
        # historial.
        .order_by("-creado_en")
    )


def _lineas_consumidas(estudiante, hoy=None):
    """Los renglones **consumidos** por el estudiante dentro de la ventana.

    **Una sola definición de «consumido en el periodo»**, y por eso es una
    función y no dos consultas parecidas: la frecuencia (`HU-31`) y los
    agregados nutricionales (`HU-32`) miran exactamente las mismas filas, y dos
    definiciones que empiezan iguales acaban discrepando en la tercera historia.

    La ventana son `reglas.DIAS_DE_LA_VENTANA` días naturales **con el de hoy
    incluido**, y la reserva sin recoger no entra: está pagada, pero todavía no
    se ha consumido (`[S2.3]` de `docs/reglas-de-frecuencia-de-consumo.md`). Se
    excluye por el estado del pedido y no dejando que su fecha nula se caiga del
    rango — la regla merece leerse en el código tal cual, no deducirse de cómo
    compara un nulo.

    **No autoriza a nadie**: es privada del módulo y quien la usa ya pasó por
    `_solo_su_acudiente`.
    """
    if hoy is None:
        hoy = timezone.localdate()
    desde = hoy - timedelta(days=reglas.DIAS_DE_LA_VENTANA - 1)

    return (
        LineaVenta.objects.filter(venta__estudiante=estudiante)
        .exclude(
            venta__origen=OrigenDeLaVenta.RESERVA,
            venta__pedido_anticipado__estado=EstadoDelPedido.PENDIENTE,
        )
        .alias(dia=DIA_DEL_CONSUMO)
        .filter(dia__gte=desde, dia__lte=hoy)
    )


def dias_de_consumo_por_categoria(*, actor, estudiante, hoy=None):
    """`{categoría: días distintos con consumo}` en la ventana de la regla.

    `TT-159`, `HU-31`. Es lo único que la base tiene que contar para que
    `reportes.reglas` decida: **días distintos, no unidades ni importe**
    (`[S2.1]`). Dos empanadas el mismo martes son un día de `Almuerzo`.

    ── QUÉ ENTRA, Y POR QUÉ NO ES LO MISMO QUE EN EL HISTORIAL ─────────────
    El historial de `HU-30` enseña **todas** las compras, reservas sin recoger
    incluidas. Aquí no: una reserva pagada que sigue en el mostrador todavía no
    se ha consumido, y contarla diría que el estudiante comió algo que no ha
    recogido (`[S2.3]`).

    No es una contradicción entre las dos lecturas: un historial responde «qué
    se ha comprado» y esta regla responde «con qué frecuencia se ha consumido».
    ─────────────────────────────────────────────────────────────────────────

    ── LA CATEGORÍA SE LEE DEL PRODUCTO, Y ES LA ÚNICA CIFRA QUE NO ES DT-8 ─
    `TT-84` congeló en la línea el precio y los nutrientes, **no la categoría**:
    no hay nada que congelar. Si la cafetería mueve un producto de `Panadería` a
    `Almuerzo`, la pregunta «¿cada cuánto come de esto?» se responde con la
    clasificación vigente. Está razonado en `[S2.4]`.
    ─────────────────────────────────────────────────────────────────────────

    `hoy` existe para las pruebas y para poder mirar otra jornada; por defecto
    es hoy en la zona horaria del colegio. La ventana lo **incluye**, así que
    son `DIAS_DE_LA_VENTANA` días contando el de hoy.

    **`alias()` y no `annotate()` para el día**, y esa distinción no es de
    estilo: lo que se anota antes de un `values()` entra en el `GROUP BY`, y el
    recuento saldría agrupado por categoría **y por día** —una fila por día, con
    un uno en cada una—. `alias()` deja filtrar por la expresión sin
    seleccionarla. El fallo sería silencioso: cifras bien formadas, todas a uno.
    """
    _solo_su_acudiente(actor, estudiante)

    recuento = (
        _lineas_consumidas(estudiante, hoy)
        .values("producto__categoria__nombre")
        .annotate(dias=Count(DIA_DEL_CONSUMO, distinct=True))
    )

    return {fila["producto__categoria__nombre"]: fila["dias"] for fila in recuento}


def alertas_de_frecuencia(*, actor, estudiante, hoy=None):
    """Las alertas de frecuencia de un estudiante (`TT-159`, `HU-31`).

    Junta las dos mitades: la base cuenta los días y `reportes.reglas` decide si
    alguno pasa de un umbral. **El veredicto no se calcula aquí a propósito** —
    los umbrales son una decisión de análisis (`TT-158`, `[S12]`) y viven en un
    módulo puro que se puede leer y probar sin sembrar catorce días de ventas.

    Devuelve una lista, ya ordenada, que puede estar vacía: **lo normal es que no
    haya ninguna alerta**, y eso no es un hueco ni un error. Por debajo del
    umbral no se publica nada, ni siquiera un «va bien» — decirlo sería la
    valoración nutricional que `ALC-OUT-20` excluye.

    **Quien las pinte se lleva el aviso de `INV-9` con ellas**: en la plantilla
    son el mismo fragmento (`TT-161`, `[S5]`). Esta función no lo sabe ni tiene
    por qué, pero quien añada una segunda pantalla que la llame, sí.
    """
    return reglas.evaluar(
        dias_de_consumo_por_categoria(actor=actor, estudiante=estudiante, hoy=hoy)
    )


@dataclass(frozen=True)
class AporteNutricional:
    """Lo que la cafetería aportó en el periodo, listo para pintar (`TT-163`).

    Es un objeto y no una lista suelta de comparaciones porque las tres cifras
    se leen juntas o no significan nada: **cuántos días hubo consumo** —que es
    el divisor—, **cuántos renglones quedaron fuera** por no declarar nada, y
    las comparaciones en sí.

    `renglones_sin_declarar` no es una curiosidad: `[S2.2]` de
    `docs/campos-nutricionales.md` obliga a excluir del agregado los productos
    sin declarar **y a decir cuántos se excluyeron**. Un agregado que se calla
    lo que dejó fuera se lee como si estuviera completo.
    """

    comparaciones: list
    dias_con_consumo: int
    renglones_sin_declarar: int
    ventana: int = reglas.DIAS_DE_LA_VENTANA

    @property
    def hay_datos(self):
        return bool(self.comparaciones)


def agregados_nutricionales(*, actor, estudiante, hoy=None):
    """Los agregados del periodo frente a la referencia sanitaria (`HU-32`).

    `TT-163`. Suma lo consumido en la misma ventana que las alertas de
    frecuencia, lo divide entre los días en que hubo consumo y compara ese
    promedio con la tabla de `reportes.referencia` — la Resolución 810 de 2021
    del Ministerio de Salud, artículo 15.

    ── SE SUMA LA INSTANTÁNEA, POR UNIDADES VENDIDAS ───────────────────────
    Los nutrientes salen de `LineaVenta` —lo que el producto declaraba al
    venderse (`DT-8`)— multiplicados por la cantidad del renglón, porque las
    cifras del catálogo son **por porción vendible** (`[S2.1]` de
    `docs/campos-nutricionales.md`). Dos empanadas aportan el doble que una;
    aquí sí se cuentan unidades, al revés que en la frecuencia, y son dos
    preguntas distintas: cada cuánto come algo, y cuánto le aportó.
    ─────────────────────────────────────────────────────────────────────────

    ── VACÍO NO ES CERO, Y LA SUMA LO RESPETA SOLA ─────────────────────────
    `Sum` ignora los nulos, así que un producto sin sodio declarado no aporta
    un cero al sodio: no aporta nada. Si **ningún** renglón del periodo declaró
    un nutriente, su total llega nulo y la comparación se publica como «sin
    datos» en vez de como un cero (`[S4.3]` del documento de referencia).

    Aparte se cuentan los renglones que **no declaran nada**, que es lo que la
    pantalla tiene que decir para que el agregado no se lea como completo.
    ─────────────────────────────────────────────────────────────────────────

    `hoy` existe para las pruebas y para mirar otra jornada, igual que en la
    frecuencia.
    """
    _solo_su_acudiente(actor, estudiante)

    lineas = _lineas_consumidas(estudiante, hoy)

    # Un `Sum` por nutriente, con el prefijo puesto: `aggregate(energia_kcal=…)`
    # choca con el campo del modelo y Django lo rechaza.
    sumas = {
        f"total_{valor.campo}": Sum(
            ExpressionWrapper(
                F(valor.campo) * F("cantidad"),
                output_field=(
                    IntegerField()
                    if valor.campo in ("energia_kcal", "sodio_mg")
                    else DecimalField(max_digits=12, decimal_places=2)
                ),
            )
        )
        for valor in referencia.REFERENCIA_DIARIA
    }

    agregados = lineas.aggregate(dias=Count(DIA_DEL_CONSUMO, distinct=True), **sumas)

    totales = {
        valor.campo: agregados[f"total_{valor.campo}"]
        for valor in referencia.REFERENCIA_DIARIA
        if agregados[f"total_{valor.campo}"] is not None
    }

    # Los renglones que no declararon **ni un** nutriente. Es el mismo criterio
    # que `LineaVenta.declara_informacion_nutricional` pregunta fila a fila,
    # resuelto en la base para no traerse el periodo entero a memoria.
    sin_declarar = lineas.filter(
        **{f"{campo}__isnull": True for campo in LineaVenta.CAMPOS_NUTRICIONALES}
    ).count()

    return AporteNutricional(
        comparaciones=referencia.comparar(totales, agregados["dias"]),
        dias_con_consumo=agregados["dias"],
        renglones_sin_declarar=sin_declarar,
    )


@dataclass(frozen=True)
class ResumenDeGasto:
    """Lo que entró y lo que salió de la billetera en el periodo (`HU-33`).

    Las tres cifras se leen juntas: **recargado**, **gastado** y el **saldo**,
    que no es del periodo sino de toda la vida de la billetera (`INV-2`). Sin la
    tercera, las dos primeras invitan a una resta que no significa lo que parece
    — ver `gasto_sin_recarga_en_el_periodo`.

    Todas positivas, incluido el gasto. En el libro una venta resta y su monto
    es negativo (`DT-4`), pero «gastó $12.000» no es una cifra negativa: es
    cuánto salió. El signo se invierte **una sola vez**, aquí, como hace
    `billetera.selectors.consumo_del_dia`.
    """

    recargado: Decimal
    gastado: Decimal
    devuelto: Decimal
    saldo: Decimal
    ventana: int = reglas.DIAS_DE_LA_VENTANA

    @property
    def hubo_movimiento(self):
        return bool(self.recargado or self.gastado or self.devuelto)

    @property
    def porcentaje_gastado(self):
        """Qué parte de lo recargado en el periodo se gastó, o `None`.

        `None` cuando no hubo recargas: dividir entre cero no es cero por
        ciento, es que la pregunta no aplica. Ese caso tiene su propia frase en
        la pantalla, porque es **el más frecuente y el que más se malinterpreta**
        (ver abajo).
        """
        if not self.recargado:
            return None
        return int(
            (self.gastado / self.recargado * 100).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )

    @property
    def gasto_sin_recarga_en_el_periodo(self):
        """¿Gastó más de lo que se recargó **en estos días**?

        ── ESTO NO ES UNA DEUDA, Y LA PANTALLA TIENE QUE DECIRLO ───────────
        `INV-1` impide que una venta deje el saldo en negativo, así que un
        estudiante **nunca** debe nada. Que gaste más de lo recargado en el
        periodo solo significa que tiró del saldo que ya tenía de antes.

        Sin esta distinción, la resta de las dos cifras se lee como un
        descubierto, que es imposible por construcción. Por eso se pregunta
        aquí y no se deja que cada pantalla la deduzca restando.
        ─────────────────────────────────────────────────────────────────────
        """
        return self.gastado > self.recargado


def resumen_de_gasto(*, actor, estudiante, hoy=None):
    """El gasto frente al saldo recargado en el periodo (`TT-165`, `HU-33`).

    Sale entero del libro de la billetera —recargas contra ventas—, así que no
    hay ningún dato nuevo que capturar: son los mismos asientos de los que sale
    el saldo (`INV-2`, `DT-4`).

    ── AQUÍ LA FECHA ES LA DEL MOVIMIENTO, NO LA DEL CONSUMO ───────────────
    Es la diferencia con los otros dos bloques de la pantalla, y parece una
    incoherencia hasta que se lee entera: la frecuencia y los agregados
    responden «cuándo comió», así que una reserva cuenta el día en que se
    recoge; **esto responde «cuándo salió el dinero», y el dinero sale al
    reservar** (`HU-23`, `TT-146`).

    Un pedido pagado el domingo y recogido el lunes es gasto del domingo y
    consumo del lunes. Las dos cosas son ciertas a la vez, y por eso no se
    reutiliza `_lineas_consumidas`: son dos preguntas con dos calendarios.
    ─────────────────────────────────────────────────────────────────────────

    **La ventana sí es la misma**, para que «el periodo» signifique lo mismo en
    toda la pantalla: los `reglas.DIAS_DE_LA_VENTANA` días naturales con el de
    hoy incluido.

    El saldo **no** es del periodo: es la suma de todos los movimientos de la
    billetera, y se lo pregunta a `billetera.selectors.saldo_de`, que es la
    única definición de «saldo» del sistema. Calcularlo aquí sería la segunda,
    y el día que cambie una, la pantalla enseñaría dos cifras distintas de lo
    mismo.
    """
    _solo_su_acudiente(actor, estudiante)

    if hoy is None:
        hoy = timezone.localdate()
    desde = hoy - timedelta(days=reglas.DIAS_DE_LA_VENTANA - 1)

    # Los límites de la jornada **en la zona horaria del colegio**, como en
    # `consumo_del_dia`: partir el día por UTC movería la recarga de las 19:00
    # al día siguiente. Y es un rango sobre la columna, no un `__date`, que
    # envolvería `creado_en` en una función y dejaría fuera su índice.
    comienzo = timezone.make_aware(datetime.combine(desde, time.min))
    siguiente = timezone.make_aware(
        datetime.combine(hoy + timedelta(days=1), time.min)
    )

    movimientos = MovimientoBilletera.objects.filter(
        billetera__estudiante=estudiante,
        creado_en__gte=comienzo,
        creado_en__lt=siguiente,
    )

    por_tipo = {
        fila["tipo"]: fila["total"]
        for fila in movimientos.values("tipo").annotate(total=Sum("monto"))
    }
    cero = Decimal("0.00")

    return ResumenDeGasto(
        recargado=por_tipo.get(TipoDeMovimiento.RECARGA) or cero,
        # El menos invierte el signo del libro una sola vez.
        gastado=-(por_tipo.get(TipoDeMovimiento.VENTA) or cero),
        # **Hoy siempre es cero y aun así se lee**, en vez de darlo por hecho:
        # el tipo existe en el libro desde `TT-59` y ningún servicio lo asienta
        # todavía (`ALC-OUT-01`: el sistema no devuelve dinero). El día que algo
        # lo asiente, este resumen no se queda mintiendo en silencio.
        devuelto=por_tipo.get(TipoDeMovimiento.DEVOLUCION) or cero,
        saldo=saldo_de(estudiante),
    )


# --- Reportes de la cafetería (`ALC-IN-22`) ---------------------------------
#
# `[S11]`, fila «Consultar reportes de ventas e inventario»: **solo `USR-4`**.
# Ni el cajero, que registra las ventas, ni la institución, que tiene el padrón.
# Es una tupla y no una comparación suelta porque `HU-36` y `HU-37` entran por
# la misma puerta: el día que la matriz cambie, cambia aquí.
CONSULTAN_LOS_REPORTES_DE_LA_CAFETERIA = (Rol.ADMINISTRADOR,)


def _solo_la_administracion(
    actor, *, que="los reportes de ventas e inventario", regla="[S11], HU-35"
):
    """`[S11]`: los reportes de la operación son de `USR-4` y de nadie más.

    **El cajero no entra, y no es un olvido.** Registra las ventas y ve las
    suyas pasar por su pantalla, pero el consolidado de la operación —cuánto se
    vendió, por qué medio, en qué periodo— es función de quien administra el
    servicio, no de quien cobra. `[S11]` lo separa en dos filas distintas y
    `[S5]` del anteproyecto explica por qué: el trabajo del administrador «no se
    centra en cada transacción individual, sino en la información acumulada».

    **La institución tampoco.** Es la responsable de los datos de los menores
    (Ley 1581), no del negocio de la cafetería, que puede estar en manos de un
    operador externo (`[S11]`, preámbulo).

    ── `que` Y `regla` EXISTEN PORQUE EL MENSAJE SE LEE ────────────────────
    El rol exigido es el mismo para los tres reportes, pero **decirle «los
    reportes de ventas e inventario son de la administración» a quien intentó
    consultar los cierres de caja es un mensaje equivocado**: nombra otros
    reportes y otra historia. Se vio ejecutando `cierres_registrados` con los
    otros tres roles (`TT-175`), y es el mismo arreglo que `TT-172` hizo con
    `ventas.services._solo_el_cajero`.

    La alternativa —una comprobación por reporte— repetiría las tres
    condiciones, y la cuarta que se añadiera se olvidaría en una de ellas.
    ─────────────────────────────────────────────────────────────────────────
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Consultar los reportes exige identificarse.")
    if actor.rol not in CONSULTAN_LOS_REPORTES_DE_LA_CAFETERIA:
        # **«Consultar X es de…» y no «X son de…»**: con un sujeto singular
        # —«el reporte de auditoría»— la segunda forma no concuerda, y se vio
        # ejecutándolo. Con el infinitivo delante, la frase vale para los cuatro
        # reportes sin que nadie tenga que acordarse del número.
        raise PermissionDenied(
            f"Consultar {que} es de la administración de la cafetería y de "
            f"ningún otro rol ({regla})."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")


@dataclass(frozen=True)
class ResumenDeVentas:
    """Lo que un periodo de ventas suma (`TT-167`, `HU-35`).

    `total` puede ser `None` cuando no hay ninguna venta: no es cero vendido,
    es que no hay nada que sumar. Quien lo pinte decide cómo decirlo — aquí no
    se inventa un cero, por lo mismo que no se inventa en los nutrientes.

    `por_medio_de_pago` y `por_origen` llegan **ordenados y completos**: con los
    tres medios de `DEC-1` y los dos orígenes de `DT-32` aunque alguno no tenga
    ventas. Una fila en cero dice «no se vendió nada así», que es información;
    una fila ausente se lee como si la categoría no existiera.
    """

    cuantas: int
    total: Decimal
    unidades: int
    por_medio_de_pago: tuple
    por_origen: tuple

    @property
    def hubo_ventas(self):
        return bool(self.cuantas)


def ventas_registradas(*, actor, desde=None, hasta=None):
    """Las ventas del periodo, para el reporte de la cafetería (`HU-35`).

    **Sobre las transacciones registradas, no sobre datos capturados aparte**,
    que es el primer criterio de la historia: esto es el libro de ventas tal
    cual, sin ninguna tabla de resumen que alguien tenga que mantener al día.

    Trae **todas** las ventas, incluidas las genéricas de `HU-53` —que no tienen
    estudiante— y las reservas de `HU-23`. Son actividad comercial del servicio
    igual que las demás, y `[S5]` del anteproyecto lo dice expreso: las compras
    de docentes y visitantes «forman parte de las ventas totales de la cafetería
    y son necesarias para que el cierre de caja y los reportes diarios reflejen
    la actividad real».

    `desde` y `hasta` son fechas locales inclusivas. Sin ellas devuelve el libro
    entero: quien acota es quien pregunta, y en el admin lo hace la navegación
    por fechas.
    """
    _solo_la_administracion(actor)

    ventas = Venta.objects.all()

    # Rango sobre la columna y no `creado_en__date`, por lo mismo que en
    # `consumo_del_dia`: `__date` envuelve la columna en una función y deja
    # fuera el índice `venta_por_fecha`.
    if desde is not None:
        ventas = ventas.filter(
            creado_en__gte=timezone.make_aware(datetime.combine(desde, time.min))
        )
    if hasta is not None:
        ventas = ventas.filter(
            creado_en__lt=timezone.make_aware(
                datetime.combine(hasta + timedelta(days=1), time.min)
            )
        )

    return ventas


def resumen_de_ventas(ventas):
    """Lo que suma un conjunto de ventas: cuántas, cuánto y en qué unidades.

    ── RECIBE UN `QuerySet` Y NO UN PERIODO, Y ESO ES LO QUE LA HACE ÚTIL ──
    El reporte vive en el admin, donde quien consulta filtra por fecha, por
    medio de pago o por origen con los controles de siempre. Si esta función
    volviera a consultar por su cuenta, el resumen de arriba hablaría de un
    conjunto distinto del listado de abajo **sin que nada fallara** — que es la
    peor clase de error que puede tener un reporte.

    Por eso recibe el `QuerySet` ya filtrado y suma exactamente sobre él. No
    autoriza a nadie: quien lo llama ya pasó por `ventas_registradas` o por el
    permiso del admin.
    ─────────────────────────────────────────────────────────────────────────

    **El total sale de las líneas congeladas** (`DT-8`), no de los productos de
    hoy: un reporte de mayo tiene que seguir diciendo lo que se cobró en mayo.

    `Count("pk", distinct=True)` y no `Count("pk")`: la suma de los importes
    obliga a unir con las líneas, y sin `distinct` una venta de tres renglones
    contaría como tres ventas. El total sí es correcto sobre esa unión —hay una
    fila por línea, que es justo lo que se quiere sumar—, así que el error solo
    aparecería en el recuento, con las cifras de dinero intactas: nadie lo
    notaría.
    """
    agregados = ventas.aggregate(
        cuantas=Count("pk", distinct=True),
        total=Sum(IMPORTE_DE_LA_LINEA),
        unidades=Sum("lineas__cantidad"),
    )

    return ResumenDeVentas(
        cuantas=agregados["cuantas"] or 0,
        total=agregados["total"],
        unidades=agregados["unidades"] or 0,
        por_medio_de_pago=_desglose(ventas, "medio_pago", MedioDePago),
        por_origen=_desglose(ventas, "origen", OrigenDeLaVenta),
    )


def _desglose(ventas, campo, opciones):
    """`((etiqueta, cuántas, total), …)` por cada valor de `opciones`.

    **Completo y en el orden de las opciones**, no en el que devuelva la base:
    los medios que no se usaron salen en cero. Que no se haya cobrado nada por
    transferencia es un dato del periodo, y una fila que falta no lo dice — se
    lee como si la transferencia no existiera.
    """
    agrupado = {
        fila[campo]: fila
        # **`order_by()` vacío antes de agrupar, y no es cosmético.** Los campos
        # del orden por defecto —`Venta.Meta.ordering` es `-creado_en`— entran
        # en el `GROUP BY` de un `values().annotate()`, así que sin esta línea
        # se agrupa por medio de pago **y por instante**: una fila por venta,
        # todas con un uno.
        #
        # El fallo es silencioso y peor que un error: el total de arriba sigue
        # bien —`aggregate()` no arrastra el orden— y solo mienten los
        # desgloses, con cifras que parecen razonables. Se vio mirando la
        # pantalla, no en las pruebas.
        for fila in ventas.order_by()
        .values(campo)
        .annotate(
            cuantas=Count("pk", distinct=True),
            total=Sum(IMPORTE_DE_LA_LINEA),
        )
    }

    return tuple(
        (
            opcion.label,
            agrupado.get(opcion.value, {}).get("cuantas", 0),
            agrupado.get(opcion.value, {}).get("total") or Decimal("0.00"),
        )
        for opcion in opciones
    )


@dataclass(frozen=True)
class ResumenDeMovimientos:
    """Lo que un periodo movió en el libro de inventario (`TT-169`, `HU-36`).

    **Todas las cifras son de unidades, no de dinero.** El inventario no sabe
    lo que costó nada: eso es el reporte de ventas. Aquí se cuentan unidades que
    entraron y salieron, que es lo que `ALC-IN-19` pide seguir.

    `entradas` y `salidas` llegan **las dos en positivo**, y `neto` con su signo.
    En el libro una salida es negativa (`DT-5`), pero «se perdieron 12 unidades»
    no es una cifra negativa: el signo se invierte una vez, aquí, como hace
    `billetera.selectors.consumo_del_dia` con el dinero.

    `mermas_sin_motivo` **debería ser siempre cero**: lo impone una
    `CheckConstraint` (`INV-8`, `DT-5`). Se cuenta y se enseña igual, y eso no
    es desconfianza: es lo que convierte la invariante en algo que la
    administración puede ver, como el historial de un producto hace visible que
    las existencias cuadran (`TT-141`).
    """

    cuantos: int
    entradas: int
    salidas: int
    neto: int
    por_tipo: tuple
    mermas_sin_motivo: int

    @property
    def hubo_movimientos(self):
        return bool(self.cuantos)


def movimientos_registrados(*, actor, desde=None, hasta=None):
    """El libro de inventario del periodo (`TT-169`, `HU-36`).

    **Entradas, ventas y mermas en un solo sitio**, que es el «para qué» de la
    historia. No hay tres consultas ni tres pantallas: es un libro con tres
    clases de asiento, y cada uno lleva su motivo cuando lo tiene (`INV-8`).

    Gemela de `ventas_registradas`, con la misma puerta —`[S11]` concede los
    reportes de ventas **e inventario** en la misma fila— y el mismo criterio
    para el periodo: fechas locales inclusivas, y sin ellas el libro entero.
    """
    _solo_la_administracion(actor)

    movimientos = MovimientoInventario.objects.all()

    if desde is not None:
        movimientos = movimientos.filter(
            creado_en__gte=timezone.make_aware(datetime.combine(desde, time.min))
        )
    if hasta is not None:
        movimientos = movimientos.filter(
            creado_en__lt=timezone.make_aware(
                datetime.combine(hasta + timedelta(days=1), time.min)
            )
        )

    return movimientos


def resumen_de_movimientos(movimientos):
    """Lo que suma un conjunto de asientos de inventario.

    Recibe el `QuerySet` ya filtrado por el mismo motivo que
    `resumen_de_ventas`: en el admin se le pasa el listado que se está mirando,
    así que el consolidado de arriba y la tabla de abajo no pueden hablar de
    conjuntos distintos.

    **`Count("pk")` sin `distinct`, al revés que en las ventas.** Allí sumar
    importes obliga a unir con las líneas y una venta de tres renglones contaría
    tres veces; aquí no hay ninguna unión que multiplique: las cantidades están
    en la propia fila y los filtros del admin —tipo, categoría del producto—
    solo atraviesan claves ajenas hacia delante.

    `neto` es la suma con signo. Sobre el libro entero **es la existencia total
    de la cafetería** (`INV-3`); sobre un periodo es lo que ese periodo movió, y
    la pantalla lo dice así para que nadie lo lea como un inventario.
    """
    cantidad = F("cantidad")
    entero = IntegerField()

    agregados = movimientos.aggregate(
        cuantos=Count("pk"),
        neto=Sum("cantidad"),
        entradas=Sum(
            Case(When(cantidad__gt=0, then=cantidad), default=0, output_field=entero)
        ),
        # En positivo: el menos invierte el signo del libro una sola vez.
        salidas=-Sum(
            Case(When(cantidad__lt=0, then=cantidad), default=0, output_field=entero)
        ),
    )

    return ResumenDeMovimientos(
        cuantos=agregados["cuantos"] or 0,
        entradas=agregados["entradas"] or 0,
        salidas=agregados["salidas"] or 0,
        neto=agregados["neto"] or 0,
        por_tipo=_desglose_de_movimientos(movimientos),
        # Una merma sin motivo **no puede existir**: lo impide una
        # `CheckConstraint` (`INV-8`). Se cuenta para poder decirlo en pantalla.
        mermas_sin_motivo=movimientos.filter(
            tipo=TipoDeMovimientoDeInventario.MERMA, motivo=""
        ).count(),
    )


def _desglose_de_movimientos(movimientos):
    """`((etiqueta, cuántos, unidades), …)` por cada tipo de asiento.

    Completo y en el orden de `TipoDeMovimientoDeInventario`, como el desglose
    de las ventas: un tipo sin asientos sale en cero. Que en el periodo no haya
    habido ninguna merma es justamente lo que se quiere leer.

    Las unidades van **en positivo también en las salidas**: la columna dice
    «cuántas unidades movió este tipo», y mezclar signos en una columna obliga a
    leer dos cosas a la vez.
    """
    agrupado = {
        fila["tipo"]: fila
        # `order_by()` vacío antes de agrupar: un orden explícito entra en el
        # `GROUP BY` de un `values().annotate()` y parte el desglose en una fila
        # por asiento. El admin siempre ordena (`TT-168` lo pagó).
        for fila in movimientos.order_by()
        .values("tipo")
        .annotate(cuantos=Count("pk"), unidades=Sum("cantidad"))
    }

    return tuple(
        (
            tipo.label,
            agrupado.get(tipo.value, {}).get("cuantos", 0),
            abs(agrupado.get(tipo.value, {}).get("unidades") or 0),
        )
        for tipo in TipoDeMovimientoDeInventario
    )


@dataclass(frozen=True)
class ResumenDeCierres:
    """Lo que dicen los cierres de un periodo (`TT-175`, `HU-56`).

    ── DOS CIFRAS DE DESCUADRE, Y NO SOBRA NINGUNA ─────────────────────────
    `diferencia_neta` es la suma **con signo** y `descuadre_total` la suma de
    los valores absolutos. No son la misma cifra y la distancia entre las dos es
    el dato: un sobrante de $2.000 el lunes y un faltante de $2.000 el martes
    dan una neta de cero y un descuadre total de $4.000.

    Enseñar solo la neta diría «la caja cuadra» de un mes con veinte
    descuadres, que es exactamente lo contrario del «para qué» de la historia —
    **detectar un patrón** en vez de enterarse suelto cada día.
    ─────────────────────────────────────────────────────────────────────────

    `sin_motivo` **debería ser siempre cero**: lo impone
    `cierre_de_caja_diferencia_con_motivo`. Se cuenta y se enseña igual, por lo
    mismo que `mermas_sin_motivo` en el inventario: es la invariante puesta
    donde la administración puede verla.

    Las cifras de dinero pueden ser `None` si no hay ningún cierre, y quien lo
    pinte decide cómo decirlo: un periodo sin cierres no es un periodo que
    cuadró.
    """

    cuantos: int
    cuadrados: int
    sobrantes: int
    faltantes: int
    esperado: Decimal
    contado: Decimal
    base: Decimal
    diferencia_neta: Decimal
    descuadre_total: Decimal
    sin_motivo: int

    @property
    def hubo_cierres(self):
        return bool(self.cuantos)

    @property
    def con_diferencia(self):
        """Cuántos no cuadraron, que es la cifra que se lee primero."""
        return self.sobrantes + self.faltantes


def cierres_registrados(*, actor, desde=None, hasta=None):
    """Los cierres de caja del periodo (`TT-175`, `HU-56`).

    Primer criterio de la historia: **quedan registrados y son consultables**.
    Es la tabla tal cual, con el cajero traído, y la misma puerta que los otros
    dos reportes de la cafetería.

    ── EL CAJERO NO ENTRA AQUÍ, Y ACABA DE ESCRIBIR ESTAS FILAS ────────────
    Cuadrar la caja es suyo (`HU-55`); **consultar el histórico de cuadres no**.
    `[S11]` separa registrar de consolidar en dos filas distintas y `[S5]` del
    anteproyecto explica por qué: el trabajo del administrador «no se centra en
    cada transacción individual, sino en la información acumulada». Detectar un
    patrón de descuadres es precisamente eso — y sobre el trabajo de quien
    cuenta el dinero.
    ─────────────────────────────────────────────────────────────────────────

    `desde` y `hasta` son fechas locales inclusivas, como en los otros dos. **Se
    comparan contra `fecha` y no contra `creado_en`**: lo que se acota es la
    jornada que se cuadró, no el instante en que alguien la registró. Un cierre
    escrito a las 23:58 de un día que cuadra el anterior pertenece al anterior,
    que es lo que dice su `fecha`.
    """
    _solo_la_administracion(
        actor, que="los cierres de caja registrados", regla="HU-56, DEC-6"
    )

    cierres = CierreDeCaja.objects.select_related("cajero")

    # Sobre un `DateField` no hace falta el rodeo de `creado_en__gte`: la
    # comparación es directa y no envuelve la columna en ninguna función.
    if desde is not None:
        cierres = cierres.filter(fecha__gte=desde)
    if hasta is not None:
        cierres = cierres.filter(fecha__lte=hasta)

    return cierres


def resumen_de_cierres(cierres):
    """Lo que suma un conjunto de cierres: cuántos, cuánto y cuánto descuadró.

    Recibe el `QuerySet` ya filtrado por lo mismo que `resumen_de_ventas` y
    `resumen_de_movimientos`: en el admin se le pasa el listado que se está
    mirando, así que el consolidado de arriba no puede hablar de otro conjunto
    que la tabla de abajo.

    **Todo sale de un solo `aggregate`, sin `values()`.** El desglose de los
    otros dos reportes agrupa por una columna con `choices`; aquí lo que
    distingue las tres clases —cuadró, sobró, faltó— **no es una columna**, es
    el signo de una resta. Con `values()` habría que anotarla antes, y lo que se
    anota antes de un `values()` entra en el `GROUP BY`: una fila por cierre,
    todas con un uno. Contar con `Case`/`When` no tiene ese problema y además se
    lee de una vez.

    `Count("pk")` sin `distinct`: no hay ninguna unión que multiplique filas.
    """
    diferencia = DIFERENCIA_DEL_CIERRE
    dinero_ = DecimalField(max_digits=12, decimal_places=2)

    agregados = cierres.aggregate(
        cuantos=Count("pk"),
        esperado=Sum("efectivo_esperado"),
        contado=Sum("efectivo_contado"),
        base_total=Sum("base"),
        diferencia_neta=Sum(diferencia),
        # El valor absoluto, sin traerse las filas: el signo se invierte en la
        # rama que lo necesita. `Func(..., function="ABS")` haría lo mismo y
        # ataría el reporte a que la base tenga esa función con ese nombre.
        descuadre_total=Sum(
            Case(
                When(efectivo_contado__lt=F("base") + F("efectivo_esperado"),
                     then=-diferencia),
                default=diferencia,
                output_field=dinero_,
            )
        ),
        cuadrados=Count(
            Case(
                When(efectivo_contado=F("base") + F("efectivo_esperado"), then=1),
                output_field=IntegerField(),
            )
        ),
        sobrantes=Count(
            Case(
                When(efectivo_contado__gt=F("base") + F("efectivo_esperado"), then=1),
                output_field=IntegerField(),
            )
        ),
        faltantes=Count(
            Case(
                When(efectivo_contado__lt=F("base") + F("efectivo_esperado"), then=1),
                output_field=IntegerField(),
            )
        ),
    )

    return ResumenDeCierres(
        cuantos=agregados["cuantos"] or 0,
        cuadrados=agregados["cuadrados"] or 0,
        sobrantes=agregados["sobrantes"] or 0,
        faltantes=agregados["faltantes"] or 0,
        esperado=agregados["esperado"],
        contado=agregados["contado"],
        base=agregados["base_total"],
        diferencia_neta=agregados["diferencia_neta"],
        descuadre_total=agregados["descuadre_total"],
        # Un cierre descuadrado sin motivo **no puede existir**: lo impide
        # `cierre_de_caja_diferencia_con_motivo`. Se cuenta para poder decirlo.
        sin_motivo=cierres.exclude(
            efectivo_contado=F("base") + F("efectivo_esperado")
        ).filter(motivo="").count(),
    )


@dataclass(frozen=True)
class Operacion:
    """Una línea del reporte de auditoría (`TT-177`, `HU-37`).

    **Quién hizo qué, y cuándo.** Es el «para» de la historia —«poder rastrear
    quién hizo qué cuando algo no cuadre»— y por eso los tres campos que la
    definen son `cuando`, `quien` y `accion`; lo demás acompaña.

    `quien` es `None` cuando el sistema **no lo registró**, no cuando no lo
    sabemos. Hoy pasa con el ingreso de mercancía y la merma:
    `MovimientoInventario` no tiene columna de actor —sus servicios reciben el
    `actor`, lo comprueban y no lo guardan—. La pantalla lo dice con esas
    palabras en vez de dejar el hueco en blanco, que se leería como un error de
    la consulta. Está declarado en el `ANEXO B` de `./docs/decisiones-de-alcance.md`.

    `modelo` y `objeto_id` no son adorno: son lo que permite **ir a mirar la
    operación** en su propio reporte. Un renglón de auditoría que no se puede
    abrir obliga a buscar la fila a mano, que es justo lo que no se hace cuando
    algo no cuadra. Se devuelven como identificadores y no como URL: un selector
    no sabe de rutas (`DT-15`).
    """

    cuando: object
    clase: str
    accion: str
    quien: object
    detalle: str
    importe: object
    modelo: str
    objeto_id: object

    @property
    def tiene_actor(self):
        return self.quien is not None

    @property
    def ruta_admin(self):
        """El nombre de la ruta del admin donde se abre esta operación.

        El nombre, no la URL: resolverla es cosa de la plantilla con `{% url %}`,
        que es lo que hace que renombrar una ruta no deje aquí un enlace roto y
        silencioso. Un selector no sabe de rutas (`DT-15`), y esto sigue sin
        saberlo — es una traducción del nombre del modelo, que sí es suyo.

        **Todas las operaciones apuntan a un modelo registrado en el admin.** La
        entrega es la excepción aparente: `PedidoAnticipado` no está registrado,
        así que apunta a su venta, que es donde está lo que se entregó. Si algún
        día se añade una clase que apunte a un modelo sin admin, esto reventará
        con `NoReverseMatch` al pintar — ruidoso, que es lo que se quiere.
        """
        return f"admin:{self.modelo.replace('.', '_')}_change"


#: Las cuatro clases de operación, y el orden en que se declaran en la pantalla.
#: No son las tres tablas: la entrega de un pedido es una operación por derecho
#: propio —mueve existencias y la hace otra persona en otro momento— y sale de
#: `PedidoAnticipado`, que es quien guarda **quién** entregó.
CLASES_DE_OPERACION = (
    ("venta", "Ventas"),
    ("entrega", "Entregas de pedidos"),
    ("inventario", "Movimientos de inventario"),
    ("cierre", "Cierres de caja"),
)

#: Cuántas operaciones devuelve como mucho. Un reporte de auditoría se consulta
#: acotado —«qué pasó el martes»—, y sin tope una consulta sin fechas se traería
#: el libro entero a memoria para ordenarlo. Quien necesite más, acota el
#: periodo; la pantalla dice cuándo se llegó al tope en vez de recortar en
#: silencio.
OPERACIONES_MAXIMAS = 500


def auditoria(*, actor, desde=None, hasta=None, limite=OPERACIONES_MAXIMAS):
    """Las operaciones registradas del periodo, en una sola línea de tiempo.

    `TT-177`, `HU-37`, `ALC-IN-22`. Devuelve `(operaciones, hubo_mas)`: la lista
    ordenada de la más reciente a la más antigua, y si el tope dejó algo fuera.

    ── SE CONSTRUYE SOBRE LAS TRANSACCIONES REGISTRADAS ────────────────────
    Único criterio de la historia, y aquí significa algo concreto: **no hay
    tabla de auditoría**. Ninguna operación se escribe dos veces —una en su
    libro y otra en un registro de eventos—, porque dos fuentes de la misma
    verdad acaban divergiendo (`DT-19`) y la segunda es la que nadie mira
    cuando falla. Esto lee los libros que ya existen y los mezcla al leerlos.

    Es la misma decisión que `DT-4` y `DT-5` toman con el saldo y las
    existencias, aplicada a la trazabilidad.
    ─────────────────────────────────────────────────────────────────────────

    ── LOS MOVIMIENTOS DE VENTA NO ENTRAN, Y ESO NO DEJA NINGÚN HUECO ──────
    Un cobro asienta la venta **y** su salida de inventario en la misma
    transacción (`HU-21`), así que incluir las dos pondría cada venta dos veces
    en la línea de tiempo, con el mismo instante y el mismo actor.

    Lo que sí es una operación aparte es la **entrega** de un pedido anticipado:
    mueve existencias en otro momento y la hace otra persona (`HU-25`). Entra
    por `PedidoAnticipado`, que es quien guarda quién entregó — el movimiento no
    lo guarda.
    ─────────────────────────────────────────────────────────────────────────

    **La mezcla se hace en Python, no en SQL.** Son cuatro tablas sin ninguna
    columna en común más que el instante, así que una `UNION` obligaría a
    inventarles un esquema compartido y a repetirlo en cada `SELECT`. Con el
    periodo acotado y el tope de `OPERACIONES_MAXIMAS`, ordenar cuatro listas
    cortas en memoria cuesta menos que mantener esa consulta.
    """
    _solo_la_administracion(
        actor, que="el reporte de auditoría", regla="HU-37, ALC-IN-22"
    )

    inicio = (
        timezone.make_aware(datetime.combine(desde, time.min))
        if desde is not None
        else None
    )
    fin = (
        timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min))
        if hasta is not None
        else None
    )

    def acotar(consulta, campo="creado_en"):
        if inicio is not None:
            consulta = consulta.filter(**{f"{campo}__gte": inicio})
        if fin is not None:
            consulta = consulta.filter(**{f"{campo}__lt": fin})
        return consulta

    operaciones = [
        *_ventas_de_la_auditoria(acotar, limite),
        *_entregas_de_la_auditoria(acotar, limite),
        *_movimientos_de_la_auditoria(acotar, limite),
        *_cierres_de_la_auditoria(acotar, limite),
    ]
    operaciones.sort(key=lambda operacion: operacion.cuando, reverse=True)

    return operaciones[:limite], len(operaciones) > limite


def _ventas_de_la_auditoria(acotar, limite):
    """Cada venta, con quién la cobró y a quién.

    **Una reserva no la cobra un cajero**: la paga el acudiente desde su
    aplicación (`DT-32`), así que el actor sale del acudiente del estudiante y
    no del campo `cajero`, que en una reserva es nulo por restricción.
    """
    consulta = (
        acotar(Venta.objects.all())
        .select_related("cajero", "estudiante__acudiente")
        .prefetch_related("lineas")
        .order_by("-creado_en")[:limite]
    )

    for venta in consulta:
        unidades = sum(linea.cantidad for linea in venta.lineas.all())
        total = sum(
            (linea.precio_unitario * linea.cantidad for linea in venta.lineas.all()),
            Decimal("0.00"),
        )
        if venta.es_reserva:
            quien = venta.estudiante.acudiente.nombre
            accion = "Reservó y pagó por adelantado"
        else:
            quien = venta.cajero.nombre if venta.cajero_id else None
            accion = "Cobró una venta"

        cliente = venta.estudiante.nombre if venta.estudiante_id else "cliente genérico"
        yield Operacion(
            cuando=venta.creado_en,
            clase="venta",
            accion=accion,
            quien=quien,
            detalle=(
                f"{unidades} artículo{'s' if unidades != 1 else ''} para {cliente} "
                f"({venta.get_medio_pago_display().lower()})"
            ),
            importe=total,
            modelo="ventas.venta",
            objeto_id=venta.pk,
        )


def _entregas_de_la_auditoria(acotar, limite):
    """La entrega de un pedido anticipado: **mueve existencias y no cobra**.

    Es la operación que más fácil se cae de un reporte de auditoría, porque no
    deja asiento en la billetera ni crea una venta: solo cambia un estado y
    descuenta inventario (`HU-25`). Y es justamente la que conviene poder
    rastrear — quien pregunta «¿quién le entregó esto?» pregunta por esto.
    """
    consulta = (
        acotar(
            PedidoAnticipado.objects.filter(estado=EstadoDelPedido.ENTREGADO),
            campo="entregado_en",
        )
        .select_related("entregado_por", "venta__estudiante")
        .prefetch_related("venta__lineas")
        .order_by("-entregado_en")[:limite]
    )

    for pedido in consulta:
        unidades = sum(linea.cantidad for linea in pedido.venta.lineas.all())
        yield Operacion(
            cuando=pedido.entregado_en,
            clase="entrega",
            accion="Entregó un pedido anticipado",
            quien=pedido.entregado_por.nombre if pedido.entregado_por_id else None,
            detalle=(
                f"{unidades} artículo{'s' if unidades != 1 else ''} a "
                f"{pedido.venta.estudiante.nombre}"
            ),
            # **Sin importe, y no es un cero**: la entrega no cobra nada. Se pagó
            # al reservar, y ese asiento ya está en su propia línea.
            importe=None,
            # Apunta a la **venta**, no al pedido: `PedidoAnticipado` no está
            # registrado en el admin —no hay nada que administrar en él, su
            # única escritura es la entrega (`DT-34`)— y la venta es donde está
            # lo que se entregó, con sus renglones.
            modelo="ventas.venta",
            objeto_id=pedido.venta_id,
        )


def _movimientos_de_la_auditoria(acotar, limite):
    """El ingreso de mercancía y la merma. **Sin quién, y se dice.**

    Los dos son ajustes manuales y los dos pasan por un servicio que exige el
    rol administrador, pero `MovimientoInventario` **no guarda el actor**: lo
    recibe, lo comprueba y lo descarta. Así que estas dos líneas dicen qué y
    cuándo, y en la columna de quién va el hueco declarado.

    Los movimientos de tipo venta no entran: los explica su venta o su entrega,
    que ya están arriba.
    """
    consulta = (
        acotar(
            MovimientoInventario.objects.filter(
                tipo__in=[
                    TipoDeMovimientoDeInventario.INGRESO,
                    TipoDeMovimientoDeInventario.MERMA,
                ]
            )
        )
        .select_related("producto")
        .order_by("-creado_en")[:limite]
    )

    for movimiento in consulta:
        es_merma = movimiento.tipo == TipoDeMovimientoDeInventario.MERMA
        detalle = f"{movimiento.cantidad:+d} {movimiento.producto.nombre}"
        if movimiento.motivo:
            detalle += f" — {movimiento.motivo}"
        yield Operacion(
            cuando=movimiento.creado_en,
            clase="inventario",
            accion="Registró una merma" if es_merma else "Ingresó mercancía",
            quien=None,
            detalle=detalle,
            importe=None,
            modelo="inventario.movimientoinventario",
            objeto_id=movimiento.pk,
        )


def _cierres_de_la_auditoria(acotar, limite):
    """El cuadre de cada jornada, con su diferencia y su motivo.

    Se acota por `creado_en` y no por `fecha`, al revés que el reporte de
    `HU-56`: en la línea de tiempo lo que importa es **cuándo se registró la
    operación**, no qué jornada cuadraba. Un cierre de ayer escrito esta mañana
    es una operación de esta mañana.
    """
    consulta = (
        acotar(CierreDeCaja.objects.all())
        .select_related("cajero")
        .order_by("-creado_en")[:limite]
    )

    for cierre in consulta:
        # **Las dos cifras pasan por `dinero`**, como la de al lado. El `Decimal`
        # crudo sale «10500.00» y el importe de la fila sale «-$2.000»: dos
        # formatos de dinero en la misma línea, que es lo que ese filtro existe
        # para evitar. Se vio en la captura, igual que en `TT-176`.
        detalle = (
            f"jornada del {cierre.fecha:%d/%m/%Y} · "
            f"esperado {dinero(cierre.efectivo_esperado)} · "
            f"contado {dinero(cierre.efectivo_contado)}"
        )
        if not cierre.cuadra:
            detalle += f" — {cierre.motivo}"
        yield Operacion(
            cuando=cierre.creado_en,
            clase="cierre",
            accion="Cuadró la caja" if cierre.cuadra else "Cuadró la caja con diferencia",
            quien=cierre.cajero.nombre,
            detalle=detalle,
            importe=cierre.diferencia,
            modelo="ventas.cierredecaja",
            objeto_id=cierre.pk,
        )


@dataclass(frozen=True)
class ResumenDeAuditoria:
    """Cuántas operaciones y de qué clase, más las que no dicen quién.

    `sin_actor` **no debería ser cero**, al revés que las mermas sin motivo del
    reporte de inventario: hoy es exactamente el número de ingresos y mermas del
    periodo. Se cuenta y se enseña para que el hueco se lea como lo que es —algo
    que el sistema no registra— y no como un fallo de la consulta.
    """

    cuantas: int
    por_clase: tuple
    sin_actor: int

    @property
    def hubo_operaciones(self):
        return bool(self.cuantas)


def resumen_de_auditoria(operaciones):
    """Lo que suma una línea de tiempo ya construida.

    Recibe la lista y no el periodo, por lo mismo que los otros tres resúmenes:
    lo que se cuenta tiene que ser exactamente lo que se está mirando. Aquí es
    todavía más literal —la lista ya está en memoria—, así que no hay forma de
    que las dos mitades de la pantalla hablen de conjuntos distintos.
    """
    por_clase = {clase: 0 for clase, _ in CLASES_DE_OPERACION}
    for operacion in operaciones:
        por_clase[operacion.clase] += 1

    return ResumenDeAuditoria(
        cuantas=len(operaciones),
        por_clase=tuple(
            (etiqueta, por_clase[clase]) for clase, etiqueta in CLASES_DE_OPERACION
        ),
        sin_actor=sum(1 for operacion in operaciones if not operacion.tiene_actor),
    )
