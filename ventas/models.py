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
    cajero = models.ForeignKey(
        "cuentas.Usuario",
        on_delete=models.PROTECT,
        related_name="ventas_registradas",
        verbose_name="cajero",
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
        ]

    def __str__(self):
        quien = self.estudiante.nombre if self.estudiante_id else "cliente genérico"
        return f"Venta a {quien} ({self.get_medio_pago_display()})"

    @property
    def es_generica(self):
        """`DEC-1`. Una venta sin estudiante **es** una venta a `USR-6`.

        Se pregunta aquí y no repitiendo `venta.estudiante_id is None` por ahí:
        la ausencia de estudiante significa algo, y nombrarlo evita que alguien
        lo lea como un dato que falta.
        """
        return self.estudiante_id is None


class LineaVenta(models.Model):
    """Un renglón de la venta: qué producto y cuántas unidades.

    **Todavía no guarda el precio ni la información nutricional.** Los copia
    `TT-84` (`PR-13`, `DT-8`, `HU-22`), y hasta entonces no se declaran campos
    vacíos que finjan tenerlos: una columna de precio siempre nula diría que el
    dato existe y no se llenó, cuando lo que pasa es que la historia que lo
    congela no ha llegado.

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

    class Meta:
        verbose_name = "línea de venta"
        verbose_name_plural = "líneas de venta"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="linea_venta_cantidad_positiva",
            ),
            models.UniqueConstraint(
                fields=["venta", "producto"],
                name="linea_venta_un_renglon_por_producto",
            ),
        ]

    def __str__(self):
        return f"{self.cantidad} × {self.producto}"
