"""`TT-87`. **`TST-2`**: venta rechazada por saldo insuficiente (`HU-19`, `INV-1`).

Uno de los cuatro escenarios críticos que `ENT-05` exige demostrar con evidencia
de ejecución:

    «Venta con saldo insuficiente o límite diario superado → venta rechazada.»

**Aquí se cubre la mitad del saldo.** La otra mitad —límite diario— es `HU-20`,
del Sprint 3: el límite no existe todavía como modelo, y una prueba sobre una
regla que no se aplica no demostraría nada. Cuando llegue, su caso se añade a
este mismo fichero y `TST-2` queda completo.

Los tres criterios de `HU-19`:

1. **Si los fondos son insuficientes, la venta no se realiza.** Y no a medias:
   tampoco se descuentan existencias, porque los dos descuentos van en la misma
   transacción (`HU-21`).
2. **El saldo nunca queda negativo, bajo ninguna combinación de operaciones.**
   Ese «bajo ninguna combinación» no se demuestra con tres casos elegidos a mano:
   se recorre una secuencia larga y desordenada de recargas, ventas y
   devoluciones, y se comprueba la propiedad **después de cada paso**.
3. **Es parte del escenario crítico `TST-2`.**

**La validación ocurre dentro del bloqueo** (`DT-6`), y esa es la parte que una
prueba secuencial no puede comprobar: está en `ventas/tests_concurrencia.py`, que
falla con la billetera en `-2000,00` si alguien invierte el orden.
"""

from decimal import Decimal
from random import Random

from django.test import TestCase
from django.urls import reverse

from billetera.models import MovimientoBilletera, TipoDeMovimiento
from billetera.selectors import saldo_de
from billetera.services import asentar, recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from ventas.models import Venta
from ventas.services import SaldoInsuficiente, registrar_venta


def escenario(precio="3500", existencias=50):
    cajero = Usuario.objects.crear_usuario(
        email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
    )
    acudiente = Usuario.objects.crear_usuario(
        email="acudiente@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
    )
    ficha = Acudiente.objects.create(
        usuario=acudiente, nombre="Marta Ruiz Ochoa", documento="4310012345"
    )
    estudiante = Estudiante.objects.create(
        nombre="Ana Sofía Restrepo Ruiz",
        documento="1001234501",
        acudiente=ficha,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )
    categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
    producto = Producto.objects.create(
        nombre="Empanada de carne", precio=Decimal(precio), categoria=categoria
    )
    MovimientoInventario.objects.create(
        producto=producto,
        tipo=TipoDeMovimientoDeInventario.INGRESO,
        cantidad=existencias,
        motivo="Ingreso de prueba",
    )
    return cajero, acudiente, estudiante, producto


class TST2LaVentaSeRechazaPorSaldoInsuficienteTest(TestCase):
    """**El escenario crítico**, en las formas en que puede presentarse."""

    def setUp(self):
        self.cajero, self.acudiente, self.estudiante, self.producto = escenario()

    def _vender(self, cantidad=1):
        return registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante,
            lineas={self.producto.id: cantidad},
        )

    def test_sin_ningun_saldo(self):
        """El caso más simple: nunca se recargó."""
        with self.assertRaises(SaldoInsuficiente):
            self._vender()

        self.assertEqual(saldo_de(self.estudiante), Decimal("0.00"))
        self.assertEqual(Venta.objects.count(), 0)

    def test_con_saldo_que_no_llega_por_un_peso(self):
        """El límite es «no alcanza», y un peso es no alcanzar."""
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("3499"))

        with self.assertRaises(SaldoInsuficiente):
            self._vender()

        self.assertEqual(saldo_de(self.estudiante), Decimal("3499"))

    def test_con_el_saldo_exacto_la_venta_si_se_realiza(self):
        """La otra cara, y hace falta: un rechazo que rechazara también lo que
        alcanza justo dejaría saldo inservible en todas las billeteras."""
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("3500"))

        self._vender()

        self.assertEqual(saldo_de(self.estudiante), Decimal("0.00"))

    def test_alcanza_para_una_unidad_pero_no_para_dos(self):
        """Lo que rechaza es **el total de la venta**, no el precio del producto.

        Es el caso realista: el estudiante lleva dos empanadas al mostrador y su
        saldo da para una.
        """
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("5000"))

        with self.assertRaises(SaldoInsuficiente):
            self._vender(cantidad=2)

        self.assertEqual(saldo_de(self.estudiante), Decimal("5000"))
        self.assertEqual(existencias_de(self.producto), 50)

    def test_alcanza_para_cada_producto_por_separado_pero_no_para_los_dos(self):
        """Un carrito de varios renglones se evalúa **entero**: rechazar por
        renglón dejaría pasar la suma."""
        gaseosa = Producto.objects.create(
            nombre="Jugo de mora",
            precio=Decimal("3000"),
            categoria=self.producto.categoria,
        )
        MovimientoInventario.objects.create(
            producto=gaseosa,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=10,
            motivo="Ingreso de prueba",
        )
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("4000"))

        with self.assertRaises(SaldoInsuficiente):
            registrar_venta(
                actor=self.cajero,
                estudiante=self.estudiante,
                lineas={self.producto.id: 1, gaseosa.id: 1},
            )

        self.assertEqual(saldo_de(self.estudiante), Decimal("4000"))

    def test_el_rechazo_no_descuenta_existencias(self):
        """`HU-21`: los dos descuentos van en la misma operación, y eso vale
        también cuando no ocurre ninguno. Sin esto, una venta rechazada dejaría
        el inventario mermado sin ninguna venta que lo explique (`INV-3`)."""
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("1000"))

        with self.assertRaises(SaldoInsuficiente):
            self._vender(cantidad=3)

        self.assertEqual(existencias_de(self.producto), 50)
        self.assertEqual(MovimientoInventario.objects.count(), 1)

    def test_el_rechazo_no_deja_ningun_movimiento_en_el_libro(self):
        """`INV-2`: el historial no puede registrar lo que no pasó."""
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("1000"))

        with self.assertRaises(SaldoInsuficiente):
            self._vender()

        self.assertEqual(
            MovimientoBilletera.objects.filter(tipo=TipoDeMovimiento.VENTA).count(), 0
        )

    def test_el_motivo_dice_las_tres_cifras_y_en_pesos(self):
        """Lo opera el cajero con una fila delante. «46500.00» obliga a traducir
        mentalmente; `$46.500` no. Y decir **cuánto falta** es lo que permite
        resolverlo: quitar un renglón o pedir una recarga."""
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("5000"))

        with self.assertRaises(SaldoInsuficiente) as rechazo:
            self._vender(cantidad=2)

        mensaje = " ".join(rechazo.exception.messages)
        self.assertIn("$5.000", mensaje)
        self.assertIn("$7.000", mensaje)
        self.assertIn("$2.000", mensaje)
        self.assertEqual(rechazo.exception.faltante, Decimal("2000"))


class ElSaldoNuncaQuedaNegativoTest(TestCase):
    """Segundo criterio de `HU-19`: **bajo ninguna combinación de operaciones**.

    Ese «ninguna» no se demuestra con casos elegidos a mano —los que uno elige
    son los que ya sabe que funcionan—, así que se recorre una secuencia larga y
    desordenada y se comprueba la propiedad después de **cada** paso.
    """

    def setUp(self):
        self.cajero, self.acudiente, self.estudiante, self.producto = escenario(
            precio="1500", existencias=400
        )

    def test_una_secuencia_larga_y_desordenada_de_operaciones(self):
        """Recargas, ventas y devoluciones intercaladas, con semilla fija.

        La semilla es fija a propósito: una prueba que falla una vez cada veinte
        ejecuciones y luego pasa no se puede depurar. Lo que se busca aquí no es
        azar, es **variedad**.
        """
        azar = Random(19051805)
        rechazadas = 0

        for paso in range(120):
            tirada = azar.random()

            if tirada < 0.35:
                recargar(
                    actor=self.acudiente,
                    estudiante=self.estudiante,
                    monto=Decimal(azar.randrange(1000, 20000)),
                )
            elif tirada < 0.95:
                try:
                    registrar_venta(
                        actor=self.cajero,
                        estudiante=self.estudiante,
                        lineas={self.producto.id: azar.randrange(1, 6)},
                    )
                except SaldoInsuficiente:
                    rechazadas += 1
            else:
                # Una devolución corrige y **no opera** (`DT-24`): suma saldo, así
                # que no puede dejar la billetera en negativo, pero entra en la
                # mezcla porque la invariante habla de *cualquier* combinación.
                asentar(
                    estudiante=self.estudiante,
                    tipo=TipoDeMovimiento.DEVOLUCION,
                    monto=Decimal(azar.randrange(100, 3000)),
                )

            self.assertGreaterEqual(
                saldo_de(self.estudiante),
                Decimal("0.00"),
                f"El saldo quedó negativo en el paso {paso}",
            )

        # Si ninguna venta se hubiera rechazado, la prueba no habría ejercitado
        # nada: querría decir que el saldo siempre alcanzó.
        self.assertGreater(rechazadas, 0, "ninguna venta llegó a rechazarse")

    def test_el_saldo_final_coincide_con_la_suma_del_historial(self):
        """`INV-2` de paso, y no sobra: un rechazo que dejara un movimiento a
        medias daría un saldo no negativo y un historial que no lo explica."""
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("10000"))
        for cantidad in [2, 3, 9, 1]:
            try:
                registrar_venta(
                    actor=self.cajero,
                    estudiante=self.estudiante,
                    lineas={self.producto.id: cantidad},
                )
            except SaldoInsuficiente:
                pass

        movimientos = MovimientoBilletera.objects.filter(
            billetera__estudiante=self.estudiante
        )

        self.assertEqual(
            saldo_de(self.estudiante), sum(m.monto for m in movimientos)
        )


class ElCajeroLeeElMotivoEnLaPantallaTest(TestCase):
    """`HU-19` la opera `USR-3`, así que el rechazo tiene que llegar a la caja.

    Un servicio que rechaza correctamente y una pantalla que dice «error» no
    cumplen la historia: el cajero necesita saber qué hacer ahora.
    """

    def setUp(self):
        self.cajero, self.acudiente, self.estudiante, self.producto = escenario()
        self.client.force_login(self.cajero)
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("5000"))

        self.client.get(
            reverse("identificacion-en-el-punto-de-venta"),
            {"codigo": self.estudiante.codigo_tarjeta},
        )
        for _ in range(2):
            self.client.post(
                reverse("carrito-del-punto-de-venta"),
                {"producto": str(self.producto.id), "accion": "anadir"},
            )

    def test_la_pantalla_dice_que_no_se_realizo_y_por_cuanto(self):
        cuerpo = self.client.post(reverse("cobrar")).content.decode()

        self.assertIn("La venta no se realizó", cuerpo)
        self.assertIn("No se descontó nada", cuerpo)
        self.assertIn("Faltan $2.000", cuerpo)

    def test_el_carrito_sigue_montado_para_poder_arreglarlo(self):
        """No se escribió nada, así que quitar un renglón y volver a pulsar es
        todo lo que hace falta. Vaciarlo obligaría a montar la venta otra vez con
        la fila esperando."""
        cuerpo = self.client.post(reverse("cobrar")).content.decode()

        self.assertEqual(cuerpo.count("data-linea-de-venta"), 1)
        self.assertIn("$7.000 COP", cuerpo)

    def test_quitando_una_unidad_la_venta_pasa(self):
        """El recorrido completo del rechazo: se cobra, no alcanza, se ajusta y
        se cobra. Es lo que ocurre de verdad en la caja."""
        self.client.post(reverse("cobrar"))

        self.client.post(
            reverse("carrito-del-punto-de-venta"),
            {"producto": str(self.producto.id), "accion": "descontar"},
        )
        cuerpo = self.client.post(reverse("cobrar")).content.decode()

        self.assertIn("Venta cobrada", cuerpo)
        self.assertEqual(saldo_de(self.estudiante), Decimal("1500"))
