"""`TT-62`, `TT-63`. El saldo sale del historial y de ningún otro sitio.

`HU-08` y **`TST-3`**, uno de los cuatro escenarios críticos que `ENT-05` exige
demostrar con evidencia de ejecución:

    «Comparación entre saldo mostrado e historial de movimientos →
     correspondencia exacta.»

**Esta prueba no sobra por ser cierta por construcción.** Que hoy no exista una
columna `saldo` hace la correspondencia inevitable; lo que estas pruebas detectan
es el día en que alguien meta un atajo —una caché, un contador, un campo
«para no recalcular»— y las dos cifras empiecen a separarse. Ese día, esto falla.

Los criterios de `HU-08`:

1. **Todo movimiento que altere el saldo queda registrado.** Se comprueba desde
   el otro lado: el saldo se reconstruye sumando el historial **en Python**, sin
   pedirle nada a la base, y tiene que dar exactamente lo mismo. Si algún camino
   alterara el saldo sin dejar movimiento, las dos cifras no coincidirían.
2. **La suma del historial coincide exactamente con el saldo mostrado.**
   *Exactamente*: en dinero, «casi» es un defecto.
"""

from decimal import Decimal
from random import Random

from django.test import TestCase

from billetera.models import Billetera, MovimientoBilletera, TipoDeMovimiento
from billetera.selectors import historial_de, saldo_de
from billetera.services import recargar
from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante


def acudiente_con_estudiante(sufijo="1"):
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente{sufijo}@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
    )
    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"4351234{sufijo}"
    )
    estudiante = Estudiante.objects.create(
        nombre=f"Estudiante {sufijo}",
        documento=f"100{sufijo}0001",
        acudiente=acudiente,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )
    return usuario, estudiante


def suma_en_python(estudiante):
    """El saldo reconstruido a mano, leyendo el historial movimiento a movimiento.

    Deliberadamente ingenuo: si esto usara `Sum` estaría comparando la base
    consigo misma y `TST-3` no probaría nada. La gracia es que las dos cifras
    salgan de caminos distintos.
    """
    total = Decimal("0.00")
    for movimiento in historial_de(estudiante):
        total += movimiento.monto
    return total


class TST3ElSaldoCoincideConSuHistorialTest(TestCase):
    """`TST-3`, `INV-2`, `HU-08`. El escenario crítico, en cuatro formas."""

    def setUp(self):
        self.usuario, self.estudiante = acudiente_con_estudiante("1")

    def test_sin_movimientos_las_dos_cifras_son_cero(self):
        self.assertEqual(saldo_de(self.estudiante), Decimal("0.00"))
        self.assertEqual(suma_en_python(self.estudiante), Decimal("0.00"))

    def test_tras_una_recarga_real_las_dos_cifras_coinciden(self):
        """La recarga entra por el servicio, no escribiendo el movimiento a mano:
        lo que se comprueba es el camino que usa la aplicación."""
        recargar(actor=self.usuario, estudiante=self.estudiante, monto=Decimal("25000"))

        self.assertEqual(saldo_de(self.estudiante), Decimal("25000"))
        self.assertEqual(saldo_de(self.estudiante), suma_en_python(self.estudiante))

    def test_con_los_tres_tipos_de_movimiento(self):
        """Recarga, venta y devolución. La venta todavía no tiene servicio
        —llega con `TT-80`—, así que su movimiento se asienta directamente; el
        signo lo sigue imponiendo la base."""
        recargar(actor=self.usuario, estudiante=self.estudiante, monto=Decimal("50000"))
        billetera = Billetera.objects.get(estudiante=self.estudiante)

        MovimientoBilletera.objects.create(
            billetera=billetera, tipo=TipoDeMovimiento.VENTA, monto=Decimal("-12500.50")
        )
        MovimientoBilletera.objects.create(
            billetera=billetera, tipo=TipoDeMovimiento.DEVOLUCION, monto=Decimal("2500.50")
        )

        self.assertEqual(saldo_de(self.estudiante), Decimal("40000.00"))
        self.assertEqual(saldo_de(self.estudiante), suma_en_python(self.estudiante))

    def test_con_un_historial_largo_y_desordenado(self):
        """Cien movimientos con céntimos, en un orden que no ayuda.

        La semilla es fija: una prueba que falla una vez de cada veinte no es una
        prueba, es una moneda. Los montos llevan céntimos a propósito — es donde
        aparecería un redondeo, y en dinero un redondeo silencioso es el defecto
        que nadie encuentra hasta que las cifras ya no cuadran.
        """
        azar = Random(20260901)
        billetera = Billetera.objects.create(estudiante=self.estudiante)
        esperado = Decimal("0.00")

        for _ in range(100):
            # Se recarga más de lo que se gasta: el saldo no puede quedar
            # negativo (`INV-1`), y aunque esta prueba no lo ejercita, un
            # historial imposible no demostraría nada sobre el sistema real.
            if azar.random() < 0.6:
                tipo = TipoDeMovimiento.RECARGA
                monto = Decimal(azar.randrange(100, 5000000)) / 100
            else:
                tipo = TipoDeMovimiento.VENTA
                monto = -Decimal(azar.randrange(100, 300000)) / 100

            MovimientoBilletera.objects.create(
                billetera=billetera, tipo=tipo, monto=monto
            )
            esperado += monto

        self.assertEqual(saldo_de(self.estudiante), esperado)
        self.assertEqual(saldo_de(self.estudiante), suma_en_python(self.estudiante))

    def test_el_saldo_no_depende_del_orden_en_que_se_lea(self):
        """Una suma no tiene orden, y el saldo tampoco puede tenerlo.

        Si algún día el saldo se calculara arrastrando un acumulado por el
        historial, leerlo al revés daría otra cifra. Aquí no.
        """
        recargar(actor=self.usuario, estudiante=self.estudiante, monto=Decimal("10000"))
        billetera = Billetera.objects.get(estudiante=self.estudiante)
        MovimientoBilletera.objects.create(
            billetera=billetera, tipo=TipoDeMovimiento.VENTA, monto=Decimal("-2500")
        )

        al_derecho = sum(
            (m.monto for m in historial_de(self.estudiante)), Decimal("0.00")
        )
        al_reves = sum(
            (m.monto for m in reversed(list(historial_de(self.estudiante)))),
            Decimal("0.00"),
        )

        self.assertEqual(al_derecho, al_reves)
        self.assertEqual(saldo_de(self.estudiante), al_derecho)


class CadaBilleteraExplicaSoloLoSuyoTest(TestCase):
    """El saldo de un estudiante no se contamina con el de otro.

    Parece obvio y es justo lo que un `filter` mal escrito rompe sin ruido: la
    suma seguiría cuadrando con *algún* historial, solo que con el que no es.
    """

    def test_dos_estudiantes_no_se_mezclan(self):
        uno_usuario, uno = acudiente_con_estudiante("2")
        otro_usuario, otro = acudiente_con_estudiante("3")

        recargar(actor=uno_usuario, estudiante=uno, monto=Decimal("30000"))
        recargar(actor=otro_usuario, estudiante=otro, monto=Decimal("7000"))

        self.assertEqual(saldo_de(uno), Decimal("30000"))
        self.assertEqual(saldo_de(otro), Decimal("7000"))
        self.assertEqual(saldo_de(uno), suma_en_python(uno))
        self.assertEqual(saldo_de(otro), suma_en_python(otro))


class ElHistorialSeLeeEnteroYEnOrdenTest(TestCase):
    """`TT-62`. La otra mitad de `INV-2`: poder desglosar el saldo."""

    def setUp(self):
        self.usuario, self.estudiante = acudiente_con_estudiante("4")
        for monto in ["1000", "2000", "3000"]:
            recargar(actor=self.usuario, estudiante=self.estudiante, monto=Decimal(monto))

    def test_llega_del_mas_reciente_al_mas_antiguo(self):
        """Es el orden en que se lee un extracto."""
        montos = [m.monto for m in historial_de(self.estudiante)]

        self.assertEqual(montos, [Decimal("3000"), Decimal("2000"), Decimal("1000")])

    def test_el_limite_recorta_pero_no_cambia_el_orden(self):
        montos = [m.monto for m in historial_de(self.estudiante, limite=2)]

        self.assertEqual(montos, [Decimal("3000"), Decimal("2000")])

    def test_sin_limite_llega_el_historial_entero(self):
        """`TST-3` compara contra el historial completo: una página no probaría nada."""
        self.assertEqual(historial_de(self.estudiante).count(), 3)
