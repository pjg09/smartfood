"""`TT-82`. Dos ventas simultáneas sobre la misma billetera (`DT-6`, `INV-1`).

═══════════════════════════════════════════════════════════════════════════
**ESTA PRUEBA EXISTE PORQUE UNA PRUEBA SECUENCIAL NO DETECTA EL FALLO.**

Un servicio que lea el saldo, decida, y **después** escriba, pasa todas las
pruebas de `ventas/tests_venta.py`. Falla en producción, con dos cajas cobrando
a la vez: las dos leen 5.000, las dos ven que 3.500 alcanza, las dos escriben, y
la billetera queda en −2.000. `INV-1` dice que eso no puede pasar nunca.

Lo que lo impide es el orden de `DT-6`: **se bloquea, luego se valida, luego se
escribe**. Con `select_for_update()` sobre la billetera, la segunda venta se
queda esperando en el `SELECT` hasta que la primera confirma, y cuando por fin
lee ve el saldo ya descontado.
═══════════════════════════════════════════════════════════════════════════

── POR QUÉ `TransactionTestCase` Y NO `TestCase` ──────────────────────────
`TestCase` envuelve cada prueba en una transacción que nunca se confirma. Dos
hilos dentro de eso **no se ven entre sí** —cada uno con su conexión, ninguna
capaz de leer lo que la otra no ha confirmado—, así que el bloqueo no llegaría a
disputarse y la prueba pasaría dijera lo que dijera el servicio. Con
`TransactionTestCase` las transacciones se confirman de verdad, que es la única
forma de que haya algo que bloquear.

Cuesta: la base se recrea entre pruebas y esto tarda. Son tres casos, y es el
precio de comprobar la invariante más cara del proyecto.
───────────────────────────────────────────────────────────────────────────
"""

import threading
from decimal import Decimal

from django.db import connection, connections
from django.test import TransactionTestCase

from billetera.selectors import saldo_de
from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from ventas.models import MedioDePago, Venta
from ventas.services import VentaRechazada, registrar_venta


def _en_paralelo(trabajos):
    """Lanza cada trabajo en su propio hilo y devuelve `[(resultado, error)]`.

    **Cada hilo cierra su conexión al terminar.** Django abre una por hilo, y una
    conexión que se queda abierta contra la base de prueba impide borrarla al
    final: la suite se cuelga esperando, sin decir por qué.
    """
    resultados = [None] * len(trabajos)

    def envolver(indice, trabajo):
        def correr():
            try:
                resultados[indice] = (trabajo(), None)
            except Exception as error:  # noqa: BLE001 — se reporta, no se traga
                resultados[indice] = (None, error)
            finally:
                connections.close_all()

        return correr

    hilos = [
        threading.Thread(target=envolver(indice, trabajo))
        for indice, trabajo in enumerate(trabajos)
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=20)

    for hilo in hilos:
        assert not hilo.is_alive(), (
            "Un hilo no terminó en 20 s: probablemente dos bloqueos esperándose "
            "el uno al otro. Los productos se bloquean ordenados por "
            "identificador precisamente para que eso no pase."
        )
    return resultados


class DosCajasSobreLaMismaBilleteraTest(TransactionTestCase):
    """`TT-82`. El escenario que `DT-6` existe para impedir."""

    def setUp(self):
        self.cajero_uno = Usuario.objects.crear_usuario(
            email="caja1@example.com", rol=Rol.CAJERO, nombre="Caja 1"
        )
        self.cajero_dos = Usuario.objects.crear_usuario(
            email="caja2@example.com", rol=Rol.CAJERO, nombre="Caja 2"
        )

        acudiente = Usuario.objects.crear_usuario(
            email="acudiente@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
        )
        ficha = Acudiente.objects.create(
            usuario=acudiente, nombre="Marta Ruiz Ochoa", documento="4310012345"
        )
        self.estudiante = Estudiante.objects.create(
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001234501",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        # Alcanza para **una** de las dos ventas, no para las dos.
        recargar(actor=acudiente, estudiante=self.estudiante, monto=Decimal("5000"))

        categoria = Categoria.objects.create(nombre="Panadería")
        self.empanada = Producto.objects.create(
            nombre="Empanada", precio=Decimal("3500"), categoria=categoria
        )
        MovimientoInventario.objects.create(
            producto=self.empanada,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=50,
            motivo="Ingreso de prueba",
        )
        connection.close()

    def _cobrar(self, cajero):
        return lambda: registrar_venta(
            actor=cajero, estudiante=self.estudiante, lineas={self.empanada.id: 1}
        )

    def test_solo_una_de_las_dos_ventas_se_cobra(self):
        """5.000 de saldo, dos ventas de 3.500 a la vez. Pasa una."""
        resultados = _en_paralelo(
            [self._cobrar(self.cajero_uno), self._cobrar(self.cajero_dos)]
        )

        cobradas = [venta for venta, error in resultados if venta is not None]
        rechazos = [error for _, error in resultados if error is not None]

        self.assertEqual(len(cobradas), 1, f"resultados: {resultados}")
        self.assertEqual(len(rechazos), 1)
        self.assertIsInstance(rechazos[0], VentaRechazada)

    def test_el_saldo_nunca_queda_negativo(self):
        """`INV-1`, comprobada sobre el estado final.

        Es la afirmación que importa: no «se rechazó una», sino que la billetera
        no quedó debiendo. Con la validación fuera del bloqueo esto daría −2.000.
        """
        _en_paralelo([self._cobrar(self.cajero_uno), self._cobrar(self.cajero_dos)])

        self.assertEqual(saldo_de(self.estudiante), Decimal("1500"))
        self.assertGreaterEqual(saldo_de(self.estudiante), Decimal("0.00"))

    def test_las_existencias_descuentan_una_sola_vez(self):
        """`INV-3`. La venta rechazada no puede haber movido el inventario: los
        dos descuentos van en la misma transacción (`HU-21`)."""
        _en_paralelo([self._cobrar(self.cajero_uno), self._cobrar(self.cajero_dos)])

        self.assertEqual(existencias_de(self.empanada), 49)
        self.assertEqual(Venta.objects.count(), 1)


class DosCajasSobreElMismoProductoTest(TransactionTestCase):
    """El otro lado del bloqueo de `DT-6`: los productos implicados.

    Aquí no hay billetera en disputa —son dos ventas genéricas— y lo que se
    disputa son las existencias. El escenario es el mismo: los dos cajeros leen
    que queda una empanada.
    """

    def setUp(self):
        self.cajero_uno = Usuario.objects.crear_usuario(
            email="caja1@example.com", rol=Rol.CAJERO, nombre="Caja 1"
        )
        self.cajero_dos = Usuario.objects.crear_usuario(
            email="caja2@example.com", rol=Rol.CAJERO, nombre="Caja 2"
        )
        categoria = Categoria.objects.create(nombre="Panadería")
        self.empanada = Producto.objects.create(
            nombre="Empanada", precio=Decimal("3500"), categoria=categoria
        )
        MovimientoInventario.objects.create(
            producto=self.empanada,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=1,
            motivo="La última",
        )
        connection.close()

    def test_la_ultima_unidad_se_vende_una_vez(self):
        cobrar = lambda cajero: (  # noqa: E731 — se necesita el cierre por hilo
            lambda: registrar_venta(
                actor=cajero,
                lineas={self.empanada.id: 1},
                medio_pago=MedioDePago.EFECTIVO,
            )
        )

        resultados = _en_paralelo([cobrar(self.cajero_uno), cobrar(self.cajero_dos)])

        cobradas = [venta for venta, error in resultados if venta is not None]

        self.assertEqual(len(cobradas), 1, f"resultados: {resultados}")
        self.assertEqual(existencias_de(self.empanada), 0)
