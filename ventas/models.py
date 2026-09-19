"""Modelos de la venta (`TT-78`, `HU-54`, `DEC-1`).

Aquí van la estructura y las invariantes que la base de datos puede imponer:
`CheckConstraint` y `UniqueConstraint`. **Sin lógica de negocio** (`DT-15`). El
servicio que asienta una venta dentro de una única transacción con bloqueo
pesimista es `TT-80` (`PR-12`, `INV-1`).

═══════════════════════════════════════════════════════════════════════════
**EL MEDIO DE PAGO ES UN CAMPO DEL ASIENTO, Y POR ESO LLEGA ANTES QUE LA VENTA.**

`HU-54` se construye en `PR-11` y la venta en `PR-12`, en ese orden y a
propósito. Añadir el medio de pago después obligaría a reescribir ventas ya
registradas para rellenarlo, que es exactamente la clase de reescritura que
`INV-2` prohíbe sobre el libro de la billetera: un asiento no se edita.

Es más barato declarar el campo con el modelo que añadirlo sobre datos ya
escritos — el mismo razonamiento con el que `TT-67` creó la restricción de
`INV-8` antes de que `HU-28` la ejercitara.
═══════════════════════════════════════════════════════════════════════════

**`estudiante` es opcional, y eso no es laxitud: es `DEC-1`.** Una venta sin
estudiante **es** una venta a cliente genérico (`USR-6`, `HU-53`), que descuenta
inventario como cualquier otra y no aplica restricciones alimentarias porque no
hay acudiente que las haya configurado. La pantalla que la emite es `PR-15`; el
modelo que la hace posible, esta.

La clave primaria es UUIDv7 generado en la aplicación (`DT-17`).
"""

import uuid

from django.db import models


class MedioDePago(models.TextChoices):
    """Los tres de `DEC-1`, y no hay un cuarto.

    **La transferencia no pasa por el sistema.** Va de la app bancaria del
    cliente a la cuenta de la cafetería; aquí solo queda constancia de que la
    venta se pagó así. No es una recarga, no toca ninguna billetera y no mueve
    dinero real (`ALC-OUT-01`, `ALC-OUT-02`). Si algún día alguien la confunde
    con un ingreso de saldo, lo que hay que releer es este párrafo.

    `EFECTIVO` existe porque el problema que ataca el proyecto es **el efectivo
    en manos de un menor**, no el efectivo en sí (`DEC-1`): un docente o un
    visitante pueden pagar con billetes sin que ninguno de los riesgos de
    `OBJ-GEN` aplique.
    """

    BILLETERA = "billetera", "Billetera"
    EFECTIVO = "efectivo", "Efectivo"
    TRANSFERENCIA = "transferencia", "Transferencia"


class OrigenDeLaVenta(models.TextChoices):
    """De dónde sale una venta (`TT-143`, `DT-32`, `HU-23`).

    **Una reserva es una venta anticipada, no un apartado.** Pasa por el mismo
    servicio de cobro, deja los mismos asientos y hereda las mismas reglas de
    rechazo. Lo único que cambia es quién la origina y cuándo: el punto de venta
    con un cajero delante, o el acudiente desde su aplicación la noche anterior.

    Ese «quién» es lo que obliga a nombrar el origen. `cajero` es obligatorio en
    una venta del mostrador y **no existe** en una reserva, y sin un campo que
    diga cuál es cuál, «venta sin cajero» no significaría nada: nada impediría
    que una venta del punto de venta se guardara sin él.
    """

    PUNTO_DE_VENTA = "punto_de_venta", "Punto de venta"
    RESERVA = "reserva", "Reserva anticipada"


class Venta(models.Model):
    """Una venta del punto de venta. **Nunca se edita ni se borra.**

    ── EL MEDIO DE PAGO Y EL ESTUDIANTE SE IMPLICAN MUTUAMENTE ─────────────
    Dos frases del contrato, una en cada documento, que juntas son una sola
    regla:

    · `HU-54`, segundo criterio: «las ventas de estudiante son **siempre**
      `billetera`».
    · `DEC-1`: «los medios de pago de una venta genérica son **efectivo y
      transferencia**».

    Es decir: hay estudiante **si y solo si** el medio es `billetera`. No son dos
    reglas que se parezcan, son las dos direcciones de la misma: la billetera es
    individual por estudiante (`HU-06`), así que cobrar contra ella sin decir de
    quién no significa nada, y cobrar a un estudiante en efectivo sería
    devolverle al menor el dinero suelto que `OBJ-GEN` vino a quitar de en medio.

    Lo impone una `CheckConstraint` y no un `if` en el servicio (`DT-15`, regla
    2): el servicio de venta es de `TT-80` y lo escribe otra persona dos semanas
    después. Una regla que depende de que alguien se acuerde no es una regla.
    ─────────────────────────────────────────────────────────────────────────

    **El cajero no es opcional.** Toda venta la registra alguien, y `[S11]`
    concede «registrar ventas en el punto de venta» a `USR-3` y a nadie más. Que
    el campo exista no autoriza: quién puede vender lo comprueba el servicio, y
    esto solo deja constancia de quién lo hizo — que es lo que `HU-55` necesitará
    para cuadrar la caja.

    `PROTECT` en las dos claves ajenas. Dar de baja a un estudiante no borra
    (`DT-12`, `HU-51`) y su historial de consumo sigue siendo suyo; desactivar
    una cuenta de cajero tampoco (`HU-42`). Un borrado en cascada se llevaría por
    delante ventas que el inventario y la billetera referencian para explicarse
    (`INV-2`, `INV-3`).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    # `null=True` **solo para las reservas** (`DT-32`, `HU-23`): las cobra el
    # acudiente desde su aplicación y no hay cajero que las registre. Cuál es
    # cuál lo dice `origen`, y la restricción de abajo no admite la combinación
    # que no debería existir.
    cajero = models.ForeignKey(
        "cuentas.Usuario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ventas_registradas",
        verbose_name="cajero",
    )
    origen = models.CharField(
        "origen",
        max_length=20,
        choices=OrigenDeLaVenta.choices,
        default=OrigenDeLaVenta.PUNTO_DE_VENTA,
    )
    # `null=True` **y** `blank=True`: una venta a cliente genérico no tiene
    # estudiante ni en la base ni en el formulario (`DEC-1`, `HU-53`).
    estudiante = models.ForeignKey(
        "personas.Estudiante",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="compras",
        verbose_name="estudiante",
    )
    medio_pago = models.CharField(
        "medio de pago", max_length=20, choices=MedioDePago.choices
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        # De la más reciente a la más antigua: es el orden en que se lee una
        # jornada de caja.
        ordering = ["-creado_en"]
        indexes = [
            # `HU-55` cierra la caja por jornada y medio de pago, y `HU-35`
            # reporta ventas por periodo. Las dos consultas empiezan por la
            # fecha.
            models.Index(fields=["creado_en"], name="venta_por_fecha"),
            # El historial de consumo de un estudiante (`HU-30`), que es la otra
            # lectura frecuente. Sin estudiante la fila no entra aquí, que es lo
            # que se quiere: las genéricas no tienen historial de nadie.
            models.Index(fields=["estudiante", "creado_en"], name="venta_por_estudiante"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(estudiante__isnull=False, medio_pago=MedioDePago.BILLETERA)
                    | models.Q(
                        estudiante__isnull=True,
                        medio_pago__in=[
                            MedioDePago.EFECTIVO,
                            MedioDePago.TRANSFERENCIA,
                        ],
                    )
                ),
                name="venta_medio_de_pago_segun_el_cliente",
            ),
            # `DT-32`. El origen y el cajero se implican mutuamente, y por eso
            # es una restricción y no un `if`: una venta del mostrador **tiene**
            # cajero, y una reserva **no**, porque la cobra el acudiente.
            #
            # La reserva exige además estudiante: no hay reserva anticipada de
            # un cliente genérico (`DEC-1`) — nadie a quien asociarla, y `HU-23`
            # pide justamente que se asocie al perfil del estudiante.
            models.CheckConstraint(
                condition=(
                    models.Q(
                        origen=OrigenDeLaVenta.PUNTO_DE_VENTA, cajero__isnull=False
                    )
                    | models.Q(
                        origen=OrigenDeLaVenta.RESERVA,
                        cajero__isnull=True,
                        estudiante__isnull=False,
                    )
                ),
                name="venta_cajero_segun_su_origen",
            ),
        ]

    def __str__(self):
        quien = self.estudiante.nombre if self.estudiante_id else "cliente genérico"
        if self.origen == OrigenDeLaVenta.RESERVA:
            return f"Reserva de {quien}"
        return f"Venta a {quien} ({self.get_medio_pago_display()})"

    @property
    def es_reserva(self):
        """`DT-32`. Una venta con origen `reserva` **es** un pedido anticipado.

        Se pregunta aquí y no repitiendo la comparación por ahí, igual que
        `es_generica`: el origen significa algo y nombrarlo evita que alguien lo
        lea como un campo de clasificación sin consecuencias.
        """
        return self.origen == OrigenDeLaVenta.RESERVA

    @property
    def es_generica(self):
        """`DEC-1`. Una venta sin estudiante **es** una venta a `USR-6`.

        Se pregunta aquí y no repitiendo `venta.estudiante_id is None` por ahí:
        la ausencia de estudiante significa algo, y nombrarlo evita que alguien
        lo lea como un dato que falta.
        """
        return self.estudiante_id is None


class LineaVenta(models.Model):
    """Un renglón de la venta: qué producto, cuántas unidades, y **qué era ese
    producto en ese momento** (`TT-84`, `DT-8`, `HU-22`).

    ═══════════════════════════════════════════════════════════════════════
    **EL PRECIO Y LOS NUTRIENTES SE COPIAN AQUÍ, NO SE LEEN DEL PRODUCTO.**

    `ALC-IN-20` pide que el historial muestre la información nutricional «tal
    como estaba declarada **al momento de la venta**». Con una referencia al
    producto, subir el precio el martes reescribiría lo que costó el lunes, y
    corregir una ficha nutricional cambiaría lo que un niño comió el mes pasado.
    El reporte de consumo de `HU-30` dejaría de ser un historial para ser una
    proyección del catálogo de hoy sobre el pasado.

    **No es una desnormalización** (`DT-19`). «Lo que el producto declara hoy» y
    «lo que declaraba cuando se vendió» son **hechos distintos**, no dos copias
    del mismo: el segundo no se puede derivar del primero. Una desnormalización
    guarda un valor que se podría recalcular; esto guarda uno que se perdería.
    ═══════════════════════════════════════════════════════════════════════

    **El nombre no se copia**, y es deliberado: `ALC-IN-20` habla de la
    información nutricional, y la clave ajena va con `PROTECT` —un producto
    vendido no desaparece, se retira del catálogo—, así que el nombre siempre se
    puede leer. Si algún día renombrar un producto hiciera ilegible un historial,
    eso es una decisión nueva y se registra; hoy no hay criterio que lo pida.

    **Los nutrientes admiten nulo igual que en el producto**, y significan lo
    mismo: «no declarado», no «cero». Una cafetería no tiene la ficha técnica de
    todo lo que vende, y convertir ese hueco en un cero haría que los reportes de
    `HU-30` sumaran ceros inventados en vez de enseñar lo que falta.

    ── UNA LÍNEA POR PRODUCTO EN CADA VENTA ────────────────────────────────
    Dos renglones del mismo producto en la misma venta son el mismo renglón con
    otra cantidad. Sin la restricción, el total sale igual —es una suma— pero el
    reporte de `HU-35` tendría que decidir si «tres empanadas» son una línea o
    tres, y dos lecturas del mismo hecho es justo lo que `DT-19` evita.

    Obliga a que el carrito de `TT-81` **agrupe** al añadir un producto que ya
    está, que es además lo que el cajero espera ver.
    ─────────────────────────────────────────────────────────────────────────

    `CASCADE` sobre la venta y `PROTECT` sobre el producto. Una línea sin su
    venta no significa nada, así que acompaña a lo que cuelga; el producto, en
    cambio, no puede desaparecer dejando renglones que ya no dicen qué se vendió
    — un producto se retira del catálogo, que es un estado, no se borra.

    Borrar la venta, de todas formas, no se podrá en cuanto tenga movimientos:
    `MovimientoBilletera.venta` y `MovimientoInventario.venta` van con `PROTECT`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name="lineas",
        verbose_name="venta",
    )
    producto = models.ForeignKey(
        "catalogo.Producto",
        on_delete=models.PROTECT,
        related_name="lineas_de_venta",
        verbose_name="producto",
    )
    # Entero y positivo: el inventario opera sobre unidades vendibles (`HU-27`),
    # y media empanada no se vende. El signo lo pone el movimiento de inventario,
    # no esto: aquí «tres» son tres unidades vendidas, no menos tres.
    cantidad = models.IntegerField("cantidad")

    # --- La instantánea (`TT-84`, `DT-8`) -----------------------------------
    #
    # Mismos nombres que en `catalogo.Producto` y mismos tipos, con una sola
    # excepción: aquí el precio se llama `precio_unitario`, porque en un renglón
    # conviven dos cifras —lo que costaba **una** unidad y lo que sumó el
    # renglón— y `precio` a secas invita a confundirlas.
    precio_unitario = models.DecimalField(
        "precio unitario", max_digits=10, decimal_places=2
    )
    porcion = models.CharField("porción", max_length=60, blank=True, default="")
    energia_kcal = models.PositiveIntegerField("energía (kcal)", null=True, blank=True)
    proteinas_g = models.DecimalField(
        "proteínas (g)", max_digits=6, decimal_places=2, null=True, blank=True
    )
    carbohidratos_g = models.DecimalField(
        "carbohidratos (g)", max_digits=6, decimal_places=2, null=True, blank=True
    )
    azucares_g = models.DecimalField(
        "azúcares (g)", max_digits=6, decimal_places=2, null=True, blank=True
    )
    grasas_totales_g = models.DecimalField(
        "grasas totales (g)", max_digits=6, decimal_places=2, null=True, blank=True
    )
    grasas_saturadas_g = models.DecimalField(
        "grasas saturadas (g)", max_digits=6, decimal_places=2, null=True, blank=True
    )
    sodio_mg = models.PositiveIntegerField("sodio (mg)", null=True, blank=True)

    # Los nutrientes congelados, sin `porcion`: esa es texto y dice a qué se
    # refieren las cifras, no es una de ellas (`TT-44`, `[S2]`).
    CAMPOS_NUTRICIONALES = (
        "energia_kcal",
        "proteinas_g",
        "carbohidratos_g",
        "azucares_g",
        "grasas_totales_g",
        "grasas_saturadas_g",
        "sodio_mg",
    )

    # Los campos que se copian del producto al vender. Vive aquí y no repartido
    # por el servicio para que añadir un nutriente al catálogo sea **una** línea:
    # si esta lista se queda corta, el dato nuevo no llega al historial y nadie
    # se entera hasta que un reporte lo eche en falta meses después.
    CAMPOS_DE_LA_INSTANTANEA = ("porcion", *CAMPOS_NUTRICIONALES)

    class Meta:
        verbose_name = "línea de venta"
        verbose_name_plural = "líneas de venta"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="linea_venta_cantidad_positiva",
            ),
            # El precio congelado no puede ser negativo. Cero sí: una cortesía o
            # una promoción son ventas legítimas, y `INV-1` no se toca porque
            # restar cero no deja a nadie debiendo.
            models.CheckConstraint(
                condition=models.Q(precio_unitario__gte=0),
                name="linea_venta_precio_no_negativo",
            ),
            models.UniqueConstraint(
                fields=["venta", "producto"],
                name="linea_venta_un_renglon_por_producto",
            ),
        ]

    def __str__(self):
        return f"{self.cantidad} × {self.producto}"

    @property
    def importe(self):
        """Lo que sumó el renglón, **con el precio de entonces**.

        Se calcula y no se guarda: es el producto de dos columnas que ya están
        aquí, así que guardarlo sería la desnormalización que la instantánea no
        es —un valor derivable de otros dos de la misma fila (`DT-19`)—.
        """
        return self.precio_unitario * self.cantidad

    @property
    def declara_informacion_nutricional(self):
        """¿La línea congeló algún nutriente? **Vacío no es cero** (`TT-44`).

        El gemelo de `catalogo.Producto.declara_informacion_nutricional`, sobre
        la instantánea en vez de sobre el catálogo de hoy, y lo necesita el
        historial de `HU-30`: un producto sin ficha técnica tiene que verse como
        un hueco —«no lo declaró»— y no como una fila de ceros, que es una
        afirmación sobre lo que el niño comió y nadie la hizo.

        Se pregunta por los `CAMPOS_NUTRICIONALES`, no por la lista entera de la
        instantánea: `porcion` es texto y describe a qué se refieren las cifras.
        Un producto con «paquete de 30 g» y ningún nutriente sigue sin declarar.
        """
        return any(
            getattr(self, campo) is not None for campo in self.CAMPOS_NUTRICIONALES
        )


class EstadoDelPedido(models.TextChoices):
    """Los dos estados de un pedido anticipado (`TT-143`, `HU-23`, `HU-25`).

    **No hay un tercero.** Ninguna historia pide anular una reserva, y el
    sistema no sabe devolver dinero (`ALC-OUT-01`): un estado «anulado» sin
    quién reintegre el saldo sería una promesa que nadie cumple. Si alguna vez
    hace falta, se registra como decisión y llega con su historia.
    """

    PENDIENTE = "pendiente", "Pendiente de entrega"
    ENTREGADO = "entregado", "Entregado"


class PedidoAnticipado(models.Model):
    """Un pedido reservado y pagado por adelantado (`HU-23`, `TT-143`).

    ── NO GUARDA NI LO QUE SE PIDIÓ NI LO QUE COSTÓ ────────────────────────
    Eso vive en la `Venta` y en sus `LineaVenta`, que es donde vive para
    cualquier otra venta. Copiarlo aquí sería una segunda fuente de verdad del
    mismo dato, que es lo que `DT-4` y `DT-5` evitan en los dos libros y
    `DT-19` en el modelo entero.

    Lo que este modelo añade sobre la venta es **una sola cosa**: en qué estado
    está la entrega. Por eso es tan corto — y por eso es una tabla aparte y no
    dos columnas más en `Venta`: una venta del mostrador se entrega en el acto
    y no tiene estado de entrega que seguir.
    ─────────────────────────────────────────────────────────────────────────

    ── LA VENTA ES UNO A UNO Y ES DE ORIGEN `reserva` ──────────────────────
    `OneToOneField`: un pedido es una venta y una venta anticipada es un
    pedido. Que esa venta tenga `origen = reserva` no lo puede imponer esta
    tabla —una `CheckConstraint` no cruza tablas—, así que lo impone el
    servicio, que es el único que las crea a la vez (`DT-15`).

    `PROTECT`: borrar la venta dejaría el pedido sin lo que se pidió, sin lo que
    costó y sin a quién. Y un asiento no se borra (`INV-2`, `INV-3`).
    ─────────────────────────────────────────────────────────────────────────

    ── LOS CAMPOS DE LA ENTREGA SE DECLARAN AHORA, AUNQUE LOS USE `HU-25` ──
    Es el mismo razonamiento con el que `TT-67` creó la restricción de `INV-8`
    antes de que `HU-28` la ejercitara, y con el que el medio de pago llegó
    antes que la venta: **es más barato declarar el campo con el modelo que
    añadirlo sobre datos ya escritos**. El servicio que los rellena es `TT-149`.
    ─────────────────────────────────────────────────────────────────────────

    La clave primaria es UUIDv7 generado en la aplicación (`DT-17`).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    venta = models.OneToOneField(
        "ventas.Venta",
        on_delete=models.PROTECT,
        related_name="pedido_anticipado",
        verbose_name="venta",
    )
    estado = models.CharField(
        "estado",
        max_length=20,
        choices=EstadoDelPedido.choices,
        default=EstadoDelPedido.PENDIENTE,
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    # `null=True` mientras está pendiente. Qué combinación es legítima lo dice
    # la restricción de abajo, no la buena voluntad de quien escriba la entrega.
    entregado_en = models.DateTimeField("entregado en", null=True, blank=True)
    entregado_por = models.ForeignKey(
        "cuentas.Usuario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pedidos_entregados",
        verbose_name="entregado por",
    )

    class Meta:
        verbose_name = "pedido anticipado"
        verbose_name_plural = "pedidos anticipados"
        # Del más reciente al más antiguo, como la venta.
        ordering = ["-creado_en"]
        indexes = [
            # La consulta de `HU-24`: qué hay pendiente, para tenerlo preparado
            # antes de que lleguen los estudiantes. Empieza por el estado.
            models.Index(fields=["estado", "creado_en"], name="pedido_por_estado"),
        ]
        constraints = [
            # `HU-25`, segundo criterio, en la capa donde no se olvida. Un
            # pedido entregado dice cuándo y quién; uno pendiente no puede
            # decirlo, porque todavía no ha pasado.
            #
            # Es además lo que impide **entregar dos veces sin darse cuenta**:
            # la entrega de `TT-149` solo puede pasar de `pendiente` a
            # `entregado`, y un pedido ya entregado no vuelve a estar pendiente
            # porque perdería la fecha y el cajero que lo atendió.
            models.CheckConstraint(
                condition=(
                    models.Q(
                        estado=EstadoDelPedido.PENDIENTE,
                        entregado_en__isnull=True,
                        entregado_por__isnull=True,
                    )
                    | models.Q(
                        estado=EstadoDelPedido.ENTREGADO,
                        entregado_en__isnull=False,
                        entregado_por__isnull=False,
                    )
                ),
                name="pedido_entrega_completa_o_ninguna",
            ),
        ]

    def __str__(self):
        return f"Pedido de {self.venta.estudiante.nombre} ({self.get_estado_display()})"

    @property
    def esta_pendiente(self):
        return self.estado == EstadoDelPedido.PENDIENTE
