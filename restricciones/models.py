"""Modelos del control parental (`TT-94`, `TT-97`, `TT-100`, `HU-09` … `HU-11`, `DT-28`).

Aquí van la estructura y las invariantes que la base de datos puede imponer:
`CheckConstraint` y `UniqueConstraint`. **Sin lógica de negocio** (`DT-15`).

═══════════════════════════════════════════════════════════════════════════
**ESTA APP ES UNA DESVIACIÓN DECLARADA DE `DT-15`, NO UN DESCUIDO.**

`DT-15` enumeró siete apps y `restricciones` no era ninguna de ellas. El
control parental no cabe en las que hay: pertenece al estudiante pero
referencia el catálogo, así que meterlo en `personas` acopla ese dominio con
`catalogo`, y meterlo en `catalogo` lo acopla al revés — y el catálogo es de la
cafetería, que es justamente quien `INV-4` deja fuera.

La decisión está registrada como `DT-28` en `docs/decisiones-tecnicas.md`. Sin
ese registro, dentro de dos meses nadie sabría si la app nació de una decisión o
de una tarde.
═══════════════════════════════════════════════════════════════════════════

**Ningún modelo de esta app se registra en el admin, y esa ausencia es la mitad
de `INV-4`.** La invariante dice que ni la cafetería ni la institución desactivan
las restricciones, y `DT-11` precisa cómo: con permisos en la capa de datos. El
acudiente no entra al admin —`INT-1` es su interfaz (`DT-2`)—, así que un
`admin.site.register` aquí no serviría a quien sí puede y abriría una puerta a
quien no. El control de quién escribe vive en `services.py`; los permisos de
`[S11]` los cierra `TT-107`.

La clave primaria es UUIDv7 generado en la aplicación (`DT-17`).
"""

import uuid

from django.db import models


class LimiteDiario(models.Model):
    """Cuánto puede gastar un estudiante en una jornada (`HU-09`, `ALC-IN-07`).

    ── ES POR ESTUDIANTE, Y LO IMPONE LA BASE ──────────────────────────────
    Primer criterio de `HU-09`. Un acudiente con tres hijos fija tres límites
    distintos, y el cupo de uno no es el del otro. Lo sostiene el
    `OneToOneField` sobre `Estudiante`, no una comprobación del servicio: colgar
    el límite de la cuenta del acudiente —que es la alternativa que parece más
    cómoda— haría imposible el criterio, y ningún `if` podría recuperarlo.
    ─────────────────────────────────────────────────────────────────────────

    ── NO HAY FILA = NO HAY LÍMITE ─────────────────────────────────────────
    La ausencia de límite se representa **sin fila**, nunca con `monto = 0`. Un
    cero es una cifra legítima —«no puede gastar nada»— y usarla para decir «no
    configuré nada» dejaría dos hechos opuestos escritos igual. Por eso el monto
    lleva `CheckConstraint(monto > 0)`.

    **Hoy no hay forma de retirar un límite ya fijado, solo de cambiarlo**, y no
    es un olvido: `[S11]` ata «retirar» a la fila de las restricciones
    alimentarias, y la del límite diario dice únicamente «fijar». `HU-12` cubre
    el producto y el alérgeno, no esto. Si el equipo decide que un acudiente
    debe poder quitarlo del todo, hace falta una historia — y entonces el camino
    es borrar la fila, nunca ponerla a cero.
    ─────────────────────────────────────────────────────────────────────────

    **No guarda cuánto se lleva gastado hoy, y no es un olvido.** El consumo del
    día es la suma de los movimientos de venta de la jornada y ya lo calcula
    `billetera.selectors.consumo_del_dia` (`INV-2`, `DT-4`). Un contador aquí
    sería un segundo dato que alguien tendría que acordarse de poner a cero cada
    medianoche, y el día que discrepara del libro no habría forma de saber cuál
    de los dos miente. La comparación la hará `TT-116` en la venta, leyendo el
    historial.

    `PROTECT` sobre el estudiante: dar de baja no borra —es un estado (`DT-12`,
    `HU-51`)—, y una cascada se llevaría por delante la configuración que el
    acudiente hizo si algún día esa baja se revirtiera.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    estudiante = models.OneToOneField(
        "personas.Estudiante",
        on_delete=models.PROTECT,
        related_name="limite_diario",
        verbose_name="estudiante",
    )
    monto = models.DecimalField("monto", max_digits=10, decimal_places=2)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "límite diario"
        verbose_name_plural = "límites diarios"
        constraints = [
            # Un límite de cero o negativo no es un límite: es la ausencia de
            # uno escrita donde no toca. La regla la impone la base y no un `if`
            # del servicio, porque un `if` se olvida en el siguiente camino de
            # escritura y una restricción no (`DT-15`).
            models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name="limite_diario_monto_positivo",
            ),
        ]

    def __str__(self):
        return f"Límite diario de {self.estudiante.nombre}"


class RestriccionProducto(models.Model):
    """Un producto concreto que este estudiante no puede comprar (`HU-10`, `ALC-IN-08`).

    ── ES UNA LISTA, Y `HU-11` ES UNA CONDICIÓN. NO SE UNIFICAN ────────────
    Segundo criterio de `HU-10`: el bloqueo por producto **se distingue
    explícitamente** del bloqueo por alérgeno. Aquí eso no es una etiqueta, es
    una tabla aparte.

    La alternativa tentadora —una sola tabla `Restriccion` con un campo `tipo`
    y una clave ajena nullable a cada cosa— parece más económica y es la puerta
    de entrada al defecto que `INV-5` prohíbe: con las dos cosas en la misma
    forma, implementar el alérgeno como «las filas de los productos que hoy lo
    declaran» deja de parecer un error y empieza a parecer una optimización. Y
    el día que la cafetería añade un producto con ese alérgeno, el estudiante
    deja de estar protegido sin que nada falle.

    **Un producto es un identificador; un alérgeno es una condición que se
    evalúa.** Son cosas distintas y por eso ocupan tablas distintas
    (`RestriccionAlergeno` llega en `TT-100`).
    ─────────────────────────────────────────────────────────────────────────

    **El bloqueo es del estudiante, no del acudiente.** Un acudiente con tres
    hijos puede prohibirle la gaseosa a uno y no a los otros. Lo mismo que el
    límite diario (`LimiteDiario`) y por el mismo motivo.

    `UniqueConstraint(estudiante, producto)`: bloquear dos veces el mismo
    producto no es bloquearlo «más». Lo impone la base y no un `if` del
    servicio, que es lo que hace que un segundo camino de escritura no pueda
    dejar filas duplicadas y con ellas un desbloqueo que no desbloquea (`DT-15`).

    `PROTECT` en los dos extremos. Sobre el estudiante, por lo mismo que en
    `LimiteDiario`. Sobre el producto, porque el catálogo **no borra**: un
    producto que salió del menú se marca `activo=False` y sigue existiendo
    (`INV-3`). Una cascada convertiría un cambio de catálogo de la cafetería en
    el borrado silencioso de una restricción que puso una familia — que es
    justo lo que `INV-4` no admite.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    estudiante = models.ForeignKey(
        "personas.Estudiante",
        on_delete=models.PROTECT,
        related_name="productos_bloqueados",
        verbose_name="estudiante",
    )
    producto = models.ForeignKey(
        "catalogo.Producto",
        on_delete=models.PROTECT,
        related_name="bloqueos",
        verbose_name="producto",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "producto bloqueado"
        verbose_name_plural = "productos bloqueados"
        ordering = ["producto__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["estudiante", "producto"],
                name="un_solo_bloqueo_por_estudiante_y_producto",
            ),
        ]

    def __str__(self):
        return f"{self.producto.nombre} bloqueado para {self.estudiante.nombre}"


class RestriccionAlergeno(models.Model):
    """Un alérgeno que este estudiante no puede consumir (`HU-11`, `INV-5`).

    ═══════════════════════════════════════════════════════════════════════
    **ESTA TABLA NO GUARDA PRODUCTOS, Y ESA AUSENCIA ES LA INVARIANTE.**

    `INV-5`: el bloqueo por alérgeno se aplica **sobre la condición**, no sobre
    una lista fija de productos. Aquí eso significa dos columnas —estudiante y
    alérgeno— y ninguna más. No hay, ni puede haber, un campo con «los productos
    que hoy lo llevan».

    Qué productos quedan cubiertos **es el resultado de una consulta**, no un
    dato: se cruza esta fila con `catalogo.ProductoAlergeno` cada vez que se
    pregunta (`restricciones.selectors.productos_cubiertos_por_alergeno`). Por
    eso un producto que la cafetería añada mañana, o uno que hoy existe y mañana
    declara el alérgeno, quedan cubiertos **sin que nadie recalcule nada** — que
    es literalmente el segundo criterio de `HU-11`.

    ── LA TENTACIÓN, Y POR QUÉ NO SE CEDE ──────────────────────────────────
    Materializar la lista consulta más rápido y parece equivalente. No lo es, y
    el fallo es silencioso: nada se rompe el día que se materializa, se rompe
    semanas después, cuando la cafetería añade un producto con maní y el
    estudiante alérgico puede comprarlo. Ninguna prueba de las que existían
    fallaría, porque todas usan productos creados antes.

    `restricciones/tests_alergeno_bloqueado.py` existe para eso: crea el
    producto **después** del bloqueo (`TT-103`).
    ═══════════════════════════════════════════════════════════════════════

    **Es una tabla distinta de `RestriccionProducto`, y no se unifican.** Una es
    una lista de identificadores; esta es una condición que se evalúa. Juntarlas
    bajo un campo «tipo» es el primer paso hacia resolver el alérgeno como lista
    de productos — ver `RestriccionProducto`.

    `PROTECT` en los dos extremos, por lo mismo que en las otras dos: ni dar de
    baja a un estudiante ni retirar un alérgeno del catálogo pueden borrar en
    silencio lo que una familia declaró (`INV-4`).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    estudiante = models.ForeignKey(
        "personas.Estudiante",
        on_delete=models.PROTECT,
        related_name="alergenos_bloqueados",
        verbose_name="estudiante",
    )
    alergeno = models.ForeignKey(
        "catalogo.Alergeno",
        on_delete=models.PROTECT,
        related_name="bloqueos",
        verbose_name="alérgeno",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "alérgeno bloqueado"
        verbose_name_plural = "alérgenos bloqueados"
        ordering = ["alergeno__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["estudiante", "alergeno"],
                name="un_solo_bloqueo_por_estudiante_y_alergeno",
            ),
        ]

    def __str__(self):
        return f"{self.alergeno.nombre} bloqueado para {self.estudiante.nombre}"


class TipoDeAsiento(models.TextChoices):
    """Qué pasó con una restricción. Dos hechos, y los dos se anotan."""

    BLOQUEO = "bloqueo", "Bloqueo"
    RETIRO = "retiro", "Retiro"


class RestriccionAsentada(models.TextChoices):
    """Sobre cuál de las tres restricciones va el asiento (`TT-134`, `DEC-13`).

    **Es un campo explícito y no se deduce de qué clave ajena está puesta.**
    Cuando solo había producto y alérgeno, «la que no es nula» bastaba; con el
    límite diario —que no tiene clave ajena a la que apuntar— «ninguna de las
    dos» pasaría a significar «límite», y eso es exactamente la codificación
    implícita contra la que este mismo módulo argumenta en `LimiteDiario`: dos
    hechos distintos escritos igual.
    """

    PRODUCTO = "producto", "Producto"
    ALERGENO = "alergeno", "Alérgeno"
    LIMITE_DIARIO = "limite_diario", "Límite diario"


class AsientoDeRestriccion(models.Model):
    """El libro de lo que se hizo con las restricciones (`TT-104`, `HU-12`).

    Segundo criterio de `HU-12`: **el retiro queda asentado**, por ser una acción
    auditable sobre la seguridad alimentaria de un menor. Tiene que poder
    reconstruirse quién la hizo y cuándo.

    **Nunca se edita ni se borra.** Es un libro, como los de `billetera` e
    `inventario` (`DT-4`, `DT-5`): se le añaden asientos y nada más. Un asiento
    corregido a posteriori deja un historial que ya no explica lo que pasó, que
    es justo lo contrario de para lo que existe.

    ── ANOTA TAMBIÉN EL BLOQUEO, Y EL CRITERIO SOLO PEDÍA EL RETIRO ─────────
    Es una decisión, no un exceso por inercia. Un registro que solo guarda los
    retiros no permite reconstruir nada: «se retiró el bloqueo de maní el día 3»
    no dice si el niño estuvo protegido antes, ni desde cuándo. La pregunta que
    un auditor trae —«¿estaba protegido este estudiante el día X?»— necesita los
    dos hechos.

    Es además el idioma del proyecto: `INV-2` e `INV-3` no dicen «anota las
    salidas», dicen que el estado se reconstruya desde el historial. Media
    historia no reconstruye.
    ─────────────────────────────────────────────────────────────────────────

    ── GUARDA EL NOMBRE ADEMÁS DE LA CLAVE AJENA (`DT-8`) ──────────────────
    La clave ajena dice **cuál** y sobrevive a los renombres; el nombre dice
    **cómo se llamaba entonces**. Sin lo segundo, renombrar «Galleta de maní» a
    «Galleta» reescribe el pasado: el asiento pasaría a decir que se retiró la
    protección sobre algo que no es lo que el acudiente vio al retirarla.

    Es el mismo criterio con el que `LineaVenta` congela precio y nutrientes: lo
    que se registró es lo que había, y editar el catálogo mañana no reescribe lo
    que pasó hoy.
    ─────────────────────────────────────────────────────────────────────────

    **`sobre` dice de qué restricción habla la fila, y la base exige que cuadre
    con las claves ajenas.** Producto y alérgeno traen la suya; el límite diario
    no trae ninguna —no hay una tabla de límites a la que apuntar, hay uno por
    estudiante—, y por eso hace falta el campo: sin él, «ninguna clave puesta»
    tendría que significar «límite», que es adivinar en vez de decir.

    Lo impone una `CheckConstraint` y no un `if` del servicio: un asiento que no
    dice sobre qué es ruido en un libro que existe para poder leerse (`DT-15`).

    `PROTECT` sobre el actor: borrar la cuenta de quien retiró una protección
    dejaría el asiento sin la mitad que `HU-12` pide —quién—.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    estudiante = models.ForeignKey(
        "personas.Estudiante",
        on_delete=models.PROTECT,
        related_name="asientos_de_restriccion",
        verbose_name="estudiante",
    )
    # Quién lo hizo. Hoy solo puede ser el acudiente —`[S11]` no da la escritura
    # a nadie más (`INV-4`)—, y aun así se guarda: el libro tiene que explicarse
    # solo, sin que haya que saberse la matriz de permisos para leerlo.
    actor = models.ForeignKey(
        "cuentas.Usuario",
        on_delete=models.PROTECT,
        related_name="asientos_de_restriccion",
        verbose_name="quién",
    )
    tipo = models.CharField("tipo", max_length=10, choices=TipoDeAsiento.choices)

    producto = models.ForeignKey(
        "catalogo.Producto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="asientos_de_restriccion",
        verbose_name="producto",
    )
    alergeno = models.ForeignKey(
        "catalogo.Alergeno",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="asientos_de_restriccion",
        verbose_name="alérgeno",
    )
    # Cómo se llamaba en ese momento (`DT-8`).
    sobre = models.CharField(
        "sobre", max_length=20, choices=RestriccionAsentada.choices
    )
    # Cómo se llamaba —o cuánto era— en ese momento. Para un producto o un
    # alérgeno, su nombre; para el límite diario, la cifra ya formateada con el
    # único formateador del sistema. En los tres casos responde lo mismo: qué vio
    # el acudiente cuando decidió.
    nombre = models.CharField("nombre en ese momento", max_length=160)

    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "asiento de restricción"
        verbose_name_plural = "asientos de restricción"
        # Del más reciente al más antiguo: es el orden en que se lee un
        # historial.
        ordering = ["-creado_en"]
        indexes = [
            models.Index(
                fields=["estudiante", "creado_en"], name="asiento_por_estudiante"
            ),
        ]
        constraints = [
            # Exactamente uno de los dos. Ni ninguno —un asiento que no dice
            # sobre qué— ni los dos —un asiento que dice dos cosas a la vez—.
            models.CheckConstraint(
                condition=(
                    models.Q(
                        sobre=RestriccionAsentada.PRODUCTO,
                        producto__isnull=False,
                        alergeno__isnull=True,
                    )
                    | models.Q(
                        sobre=RestriccionAsentada.ALERGENO,
                        producto__isnull=True,
                        alergeno__isnull=False,
                    )
                    | models.Q(
                        sobre=RestriccionAsentada.LIMITE_DIARIO,
                        producto__isnull=True,
                        alergeno__isnull=True,
                    )
                ),
                name="asiento_coherente_con_lo_que_restringe",
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.nombre} · {self.estudiante.nombre}"
