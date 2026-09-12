"""`TT-80`, `TT-83`. El cobro descuenta saldo y existencias **a la vez**.

`HU-21`, y los dos criterios que la definen:

1. **Ambos descuentos ocurren en la misma operación: no puede quedar uno sin el
   otro.** Es `TT-83`, y se prueba por el lado que duele — forzando un fallo a
   mitad de la escritura y comprobando que no quedó **nada**: ni venta, ni
   líneas, ni movimiento de billetera, ni movimiento de inventario.
2. **La venta queda asentada en el historial de los dos libros.** `INV-2` e
   `INV-3`: el saldo y las existencias que se leen después salen de esos
   asientos, no de ninguna columna.

Y la invariante que no puede esperar a `PR-14`: **`INV-1`, ninguna venta deja
saldo negativo**. El rechazo con su mensaje y su escenario `TST-2` son `HU-19`;
la comprobación dentro del bloqueo es de aquí, porque no puede existir un commit
de `main` en el que una venta pueda dejar deuda.

La concurrencia —que es donde `DT-6` se gana el sueldo— está en
`ventas/tests_concurrencia.py`: necesita transacciones de verdad y no cabe en un
`TestCase`.
"""

from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.test import TestCase

from billetera.models import Billetera, MovimientoBilletera, TipoDeMovimiento
from billetera.selectors import saldo_de
from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from personas.services import EstudianteNoOperativo, dar_de_baja
from ventas.models import LineaVenta, MedioDePago, Venta
from ventas.services import (
    CarritoVacio,
    ExistenciasInsuficientes,
    SaldoInsuficiente,
    VentaRechazada,
    registrar_venta,
)


def cajero(email="cajero@example.com"):
    return Usuario.objects.crear_usuario(email=email, rol=Rol.CAJERO, nombre="Cajero")


def familia(documento="1001234501"):
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente{documento}@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
    )
    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"43{documento}"
    )
    estudiante = Estudiante.objects.create(
        nombre="Ana Sofía Restrepo Ruiz",
        documento=documento,
        acudiente=acudiente,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )
    return usuario, estudiante


def producto(nombre="Empanada", precio="3500", existencias=10):
    categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
    articulo = Producto.objects.create(
        nombre=nombre, precio=Decimal(precio), categoria=categoria
    )
    if existencias:
        MovimientoInventario.objects.create(
            producto=articulo,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=existencias,
            motivo="Ingreso de prueba",
        )
    return articulo


class LaVentaDescuentaLasDosCosasTest(TestCase):
    """`TT-83`, primer y segundo criterio de `HU-21`."""

    def setUp(self):
        self.cajero = cajero()
        self.acudiente, self.estudiante = familia()
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000"))
        self.empanada = producto()

    def test_descuenta_saldo_y_existencias(self):
        registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 2},
        )

        self.assertEqual(saldo_de(self.estudiante), Decimal("43000"))
        self.assertEqual(existencias_de(self.empanada), 8)

    def test_las_dos_cifras_salen_del_historial_y_no_de_una_columna(self):
        """`INV-2`, `INV-3`. Reconstruidas a mano, por un camino distinto al de
        los selectores: si alguien metiera un contador, las dos cifras se
        separarían y esto lo vería."""
        registrar_venta(
            actor=self.cajero, estudiante=self.estudiante, lineas={self.empanada.id: 3}
        )

        movimientos = MovimientoBilletera.objects.filter(
            billetera__estudiante=self.estudiante
        )
        asientos = MovimientoInventario.objects.filter(producto=self.empanada)

        self.assertEqual(
            sum(m.monto for m in movimientos), Decimal("50000") - Decimal("10500")
        )
        self.assertEqual(sum(a.cantidad for a in asientos), 10 - 3)

    def test_los_dos_movimientos_senalan_la_venta(self):
        """`TT-78`. Sin eso, el historial suma bien y no explica nada."""
        venta = registrar_venta(
            actor=self.cajero, estudiante=self.estudiante, lineas={self.empanada.id: 1}
        )

        movimiento = MovimientoBilletera.objects.get(tipo=TipoDeMovimiento.VENTA)
        asiento = MovimientoInventario.objects.get(
            tipo=TipoDeMovimientoDeInventario.VENTA
        )

        self.assertEqual(movimiento.venta, venta)
        self.assertEqual(asiento.venta, venta)

    def test_varios_productos_en_una_sola_venta(self):
        gaseosa = producto(nombre="Gaseosa", precio="2500", existencias=5)

        registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 2, gaseosa.id: 1},
        )

        self.assertEqual(saldo_de(self.estudiante), Decimal("40500"))
        self.assertEqual(existencias_de(self.empanada), 8)
        self.assertEqual(existencias_de(gaseosa), 4)
        self.assertEqual(LineaVenta.objects.count(), 2)

    def test_la_venta_de_un_estudiante_se_paga_con_su_billetera(self):
        """`HU-54`. No hace falta decirlo: es el único medio que admite."""
        venta = registrar_venta(
            actor=self.cajero, estudiante=self.estudiante, lineas={self.empanada.id: 1}
        )

        self.assertEqual(venta.medio_pago, MedioDePago.BILLETERA)


class NoQuedaUnDescuentoSinElOtroTest(TestCase):
    """`TT-83`, y el criterio se prueba por donde duele.

    «No puede quedar uno sin el otro» no se demuestra viendo que los dos
    ocurrieron: se demuestra **rompiendo la operación a mitad** y comprobando que
    no quedó ninguno. Es lo que distingue una transacción de dos escrituras
    seguidas que casi siempre funcionan.
    """

    def setUp(self):
        self.cajero = cajero()
        self.acudiente, self.estudiante = familia()
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000"))
        self.empanada = producto()

    def test_si_falla_el_asiento_de_la_billetera_no_queda_nada(self):
        """El inventario ya se había escrito cuando revienta el segundo libro.

        Sin la transacción única, aquí quedarían unas existencias descontadas y
        un saldo intacto: exactamente el descuadre que `HU-21` existe para
        impedir.
        """
        with patch(
            "ventas.services.asentar_en_la_billetera",
            side_effect=RuntimeError("se cayó la base a mitad"),
        ):
            with self.assertRaises(RuntimeError):
                registrar_venta(
                    actor=self.cajero,
                    estudiante=self.estudiante,
                    lineas={self.empanada.id: 2},
                )

        self.assertEqual(saldo_de(self.estudiante), Decimal("50000"))
        self.assertEqual(existencias_de(self.empanada), 10)
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(LineaVenta.objects.count(), 0)
        self.assertEqual(
            MovimientoInventario.objects.filter(
                tipo=TipoDeMovimientoDeInventario.VENTA
            ).count(),
            0,
        )

    def test_si_falla_el_asiento_del_inventario_tampoco(self):
        with patch(
            "ventas.services.asentar_en_el_inventario",
            side_effect=RuntimeError("se cayó la base a mitad"),
        ):
            with self.assertRaises(RuntimeError):
                registrar_venta(
                    actor=self.cajero,
                    estudiante=self.estudiante,
                    lineas={self.empanada.id: 2},
                )

        self.assertEqual(saldo_de(self.estudiante), Decimal("50000"))
        self.assertEqual(existencias_de(self.empanada), 10)
        self.assertEqual(Venta.objects.count(), 0)

    def test_un_rechazo_tampoco_deja_media_venta(self):
        """Lo que se quiere es que **después de un rechazo no haya nada**, y da
        igual cuál de las validaciones lo produjo: por eso se espera la familia
        `VentaRechazada` y no una subclase. Cuál rechaza qué lo prueba
        `LaVentaSeNiegaConMotivoTest`."""
        with self.assertRaises(VentaRechazada):
            registrar_venta(
                actor=self.cajero, estudiante=self.estudiante, lineas={self.empanada.id: 20}
            )

        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(saldo_de(self.estudiante), Decimal("50000"))
        self.assertEqual(existencias_de(self.empanada), 10)


class NingunaVentaDejaSaldoNegativoTest(TestCase):
    """`INV-1`. La invariante, no el mensaje: el mensaje es `HU-19` (`PR-14`)."""

    def setUp(self):
        self.cajero = cajero()
        self.acudiente, self.estudiante = familia()
        self.empanada = producto(precio="3500")

    def test_sin_saldo_no_hay_venta(self):
        with self.assertRaises(SaldoInsuficiente):
            registrar_venta(
                actor=self.cajero, estudiante=self.estudiante, lineas={self.empanada.id: 1}
            )

        self.assertEqual(saldo_de(self.estudiante), Decimal("0.00"))

    def test_con_el_saldo_justo_la_venta_pasa(self):
        """El límite es «no alcanza», no «no llega con holgura»: un saldo
        exactamente igual al total deja la billetera en cero, que es legal."""
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("3500"))

        registrar_venta(
            actor=self.cajero, estudiante=self.estudiante, lineas={self.empanada.id: 1}
        )

        self.assertEqual(saldo_de(self.estudiante), Decimal("0.00"))

    def test_un_peso_menos_y_no_pasa(self):
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("3499"))

        with self.assertRaises(SaldoInsuficiente):
            registrar_venta(
                actor=self.cajero, estudiante=self.estudiante, lineas={self.empanada.id: 1}
            )

        self.assertEqual(saldo_de(self.estudiante), Decimal("3499"))

    def test_el_saldo_nunca_queda_negativo_venda_lo_que_venda(self):
        """La invariante escrita como invariante: se intenta de todo y después se
        comprueba que la propiedad se mantiene."""
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("10000"))

        for cantidad in [1, 1, 1, 5, 2, 1]:
            try:
                registrar_venta(
                    actor=self.cajero,
                    estudiante=self.estudiante,
                    lineas={self.empanada.id: cantidad},
                )
            except VentaRechazada:
                pass
            self.assertGreaterEqual(saldo_de(self.estudiante), Decimal("0.00"))


class LaVentaSeNiegaConMotivoTest(TestCase):
    def setUp(self):
        self.cajero = cajero()
        self.acudiente, self.estudiante = familia()
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000"))
        self.empanada = producto(existencias=3)

    def test_no_se_vende_lo_que_no_hay(self):
        with self.assertRaises(ExistenciasInsuficientes):
            registrar_venta(
                actor=self.cajero, estudiante=self.estudiante, lineas={self.empanada.id: 4}
            )

        self.assertEqual(existencias_de(self.empanada), 3)

    def test_cobrar_sin_lineas_no_es_una_venta_de_cero(self):
        with self.assertRaises(CarritoVacio):
            registrar_venta(actor=self.cajero, estudiante=self.estudiante, lineas={})

        self.assertEqual(Venta.objects.count(), 0)

    def test_una_cantidad_que_no_es_un_entero_positivo_no_entra(self):
        for cantidad in [0, -1, "dos"]:
            with self.subTest(cantidad=cantidad):
                with self.assertRaises(VentaRechazada):
                    registrar_venta(
                        actor=self.cajero,
                        estudiante=self.estudiante,
                        lineas={self.empanada.id: cantidad},
                    )

    def test_al_estudiante_de_baja_no_se_le_vende(self):
        """`INVD-2`, por la puerta única de `DT-24`: lo rechaza `asentar()`, que
        es por donde pasa todo movimiento."""
        institucion = Usuario.objects.crear_usuario(
            email="institucion@example.com", rol=Rol.INSTITUCION, nombre="Colegio"
        )
        dar_de_baja(actor=institucion, estudiante=self.estudiante)

        with self.assertRaises(EstudianteNoOperativo):
            registrar_venta(
                actor=self.cajero, estudiante=self.estudiante, lineas={self.empanada.id: 1}
            )

        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(existencias_de(self.empanada), 3)

    def test_un_producto_que_ya_no_esta_en_el_catalogo_no_se_vende(self):
        self.empanada.activo = False
        self.empanada.save(update_fields=["activo"])

        with self.assertRaises(VentaRechazada):
            registrar_venta(
                actor=self.cajero, estudiante=self.estudiante, lineas={self.empanada.id: 1}
            )


class SoloElCajeroCobraTest(TestCase):
    """`[S11]`, y en el servicio: la vista también lo comprueba, pero la regla
    vive aquí (`DT-15`)."""

    def setUp(self):
        self.acudiente, self.estudiante = familia()
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000"))
        self.empanada = producto()

    def test_ningun_otro_rol_registra_una_venta(self):
        for rol in [Rol.ACUDIENTE, Rol.ADMINISTRADOR, Rol.INSTITUCION]:
            with self.subTest(rol=rol):
                actor = Usuario.objects.crear_usuario(
                    email=f"{rol}@example.com", rol=rol, nombre="Otro"
                )
                with self.assertRaises(PermissionDenied):
                    registrar_venta(
                        actor=actor,
                        estudiante=self.estudiante,
                        lineas={self.empanada.id: 1},
                    )

        self.assertEqual(Venta.objects.count(), 0)

    def test_una_cuenta_de_cajero_desactivada_no_cobra(self):
        actor = cajero()
        actor.is_active = False
        actor.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            registrar_venta(
                actor=actor, estudiante=self.estudiante, lineas={self.empanada.id: 1}
            )


class LaVentaSinEstudianteNoTocaNingunaBilleteraTest(TestCase):
    """El camino de `HU-53` (`PR-15`) ya existe en el servicio.

    No se separa en dos funciones porque serían **dos caminos de escritura para
    el mismo libro**, que es justo lo que `DT-24` evita. La pantalla que la emite
    es `TT-89`; esto comprueba que el servicio no descuadra nada por el camino.
    """

    def setUp(self):
        self.cajero = cajero()
        self.acudiente, self.estudiante = familia()
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000"))
        self.empanada = producto()

    def test_descuenta_inventario_y_no_altera_ninguna_billetera(self):
        registrar_venta(
            actor=self.cajero,
            lineas={self.empanada.id: 2},
            medio_pago=MedioDePago.EFECTIVO,
        )

        self.assertEqual(existencias_de(self.empanada), 8)
        self.assertEqual(saldo_de(self.estudiante), Decimal("50000"))
        self.assertEqual(
            MovimientoBilletera.objects.filter(tipo=TipoDeMovimiento.VENTA).count(), 0
        )

    def test_sin_estudiante_hace_falta_decir_con_qué_se_paga(self):
        with self.assertRaises(VentaRechazada):
            registrar_venta(actor=self.cajero, lineas={self.empanada.id: 1})

    def test_sin_estudiante_no_se_cobra_contra_una_billetera(self):
        with self.assertRaises(VentaRechazada):
            registrar_venta(
                actor=self.cajero,
                lineas={self.empanada.id: 1},
                medio_pago=MedioDePago.BILLETERA,
            )

    def test_a_un_estudiante_no_se_le_cobra_en_efectivo(self):
        """`HU-54`. Sería devolverle al menor el dinero suelto que `OBJ-GEN` vino
        a quitar de en medio."""
        with self.assertRaises(VentaRechazada):
            registrar_venta(
                actor=self.cajero,
                estudiante=self.estudiante,
                lineas={self.empanada.id: 1},
                medio_pago=MedioDePago.EFECTIVO,
            )
