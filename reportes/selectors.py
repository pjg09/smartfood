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
from cuentas.models import Rol
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from reportes import referencia, reglas
from ventas.models import (
    EstadoDelPedido,
    LineaVenta,
    MedioDePago,
    OrigenDeLaVenta,
    Venta,
)

# El importe de un renglón, calculado por la base: precio congelado por unidades
# (`DT-8`). Se declara aquí, una vez, porque lo usan el historial del acudiente
# y el reporte de ventas de la cafetería, y repetir la expresión es como acaban
# dando cifras distintas.
#
# Se atraviesa **desde la venta** —`lineas__…`—, así que sirve tal cual en
# cualquier `QuerySet` de `Venta`.
IMPORTE_DE_LA_LINEA = ExpressionWrapper(
    F("lineas__precio_unitario") * F("lineas__cantidad"),
    output_field=DecimalField(max_digits=12, decimal_places=2),
)

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


def _solo_la_administracion(actor):
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
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Consultar los reportes exige identificarse.")
    if actor.rol not in CONSULTAN_LOS_REPORTES_DE_LA_CAFETERIA:
        raise PermissionDenied(
            "Los reportes de ventas e inventario son de la administración de la "
            "cafetería y de ningún otro rol ([S11], HU-35)."
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
