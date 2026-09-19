"""`TT-165`, `TT-166`. El gasto frente al saldo recargado (`HU-33`).

Sale entero del libro de la billetera, así que lo que puede equivocarse no es
una regla de negocio sino **qué entra y con qué fecha**:

1. La ventana, y que el saldo **no** sea del periodo sino de toda la vida de la
   billetera (`INV-2`).
2. El signo: en el libro una venta resta, y «se gastó» es una cifra positiva.
3. **La fecha es la del movimiento, no la del consumo** — que es la diferencia
   con los otros dos bloques de la pantalla y la que parece una incoherencia
   hasta que se lee entera.
4. Que gastar más de lo recargado **no sea** una deuda: `INV-1` no deja que una
   venta deje el saldo en negativo.

Las fechas se fijan a mano sobre la jornada de `tests_frecuencia`, y el selector
recibe `hoy=`: una prueba de ventanas que mire el reloj falla sola.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils import timezone

from billetera.models import MovimientoBilletera
from billetera.services import recargar
from reportes.reglas import DIAS_DE_LA_VENTANA
from reportes.selectors import resumen_de_gasto
from reportes.tests_frecuencia import HOY, BaseDeFrecuencia, a_mediodia


class BaseDeGasto(BaseDeFrecuencia):
    """La familia de siempre, con la recarga inicial **fuera de la ventana**.

    `BaseDeFrecuencia` recarga al montar el escenario para que haya con qué
    comprar, y esa recarga cae en el día en que se ejecuta la prueba. Se la
    empuja atrás para que cada prueba controle lo que hay dentro del periodo:
    de lo contrario, el primer `recargado` que se mire llevaría medio millón
    que nadie puso ahí a propósito.
    """

    def setUp(self):
        super().setUp()
        MovimientoBilletera.objects.filter(
            billetera__estudiante=self.estudiante
        ).update(creado_en=a_mediodia(HOY - timedelta(days=90)))

    def recargar_el_dia(self, monto, dias_atras):
        movimiento = recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal(monto)
        )
        MovimientoBilletera.objects.filter(pk=movimiento.pk).update(
            creado_en=a_mediodia(HOY - timedelta(days=dias_atras))
        )
        return movimiento

    def fechar_los_movimientos_de(self, venta, dias_atras):
        """La venta ya está fechada; su movimiento de billetera, no.

        Son dos asientos distintos —el de la venta y el de la billetera— y cada
        bloque de la pantalla mira el suyo. Aquí se fija el del dinero.
        """
        MovimientoBilletera.objects.filter(venta=venta).update(
            creado_en=a_mediodia(HOY - timedelta(days=dias_atras))
        )

    def gastar_el_dia(self, dias_atras, cantidad=1):
        venta = self.comprar(dias_atras=dias_atras, cantidad=cantidad)
        self.fechar_los_movimientos_de(venta, dias_atras)
        return venta

    def resumen(self):
        return resumen_de_gasto(
            actor=self.acudiente, estudiante=self.estudiante, hoy=HOY
        )


class LasDosCifrasDelPeriodoTest(BaseDeGasto):
    """`HU-33`, criterio único: contrasta gasto contra saldo recargado."""

    def test_suma_las_recargas_del_periodo(self):
        self.recargar_el_dia("20000", 3)
        self.recargar_el_dia("10000", 1)

        self.assertEqual(self.resumen().recargado, Decimal("30000.00"))

    def test_el_gasto_se_enseña_en_positivo(self):
        """En el libro una venta resta (`DT-4`), pero «se gastó $5.000» no es
        una cifra negativa: es cuánto salió."""
        self.gastar_el_dia(dias_atras=1, cantidad=2)

        gastado = self.resumen().gastado
        self.assertGreater(gastado, 0)
        self.assertEqual(gastado, Decimal("5000.00"))

    def test_sin_movimientos_las_dos_cifras_son_cero(self):
        resumen = self.resumen()

        self.assertEqual(resumen.recargado, Decimal("0.00"))
        self.assertEqual(resumen.gastado, Decimal("0.00"))
        self.assertFalse(resumen.hubo_movimiento)

    def test_hoy_ningun_servicio_asienta_devoluciones(self):
        """`ALC-OUT-01`: el sistema no devuelve dinero. El tipo existe en el
        libro desde `TT-59` y se lee igual, para que el día que algo lo asiente
        el resumen no se quede callado."""
        self.recargar_el_dia("10000", 2)
        self.gastar_el_dia(dias_atras=1)

        self.assertEqual(self.resumen().devuelto, Decimal("0.00"))


class LaVentanaRecortaLoViejoTest(BaseDeGasto):
    def test_el_ultimo_dia_de_la_ventana_entra(self):
        self.recargar_el_dia("15000", DIAS_DE_LA_VENTANA - 1)

        self.assertEqual(self.resumen().recargado, Decimal("15000.00"))

    def test_el_dia_anterior_a_la_ventana_no_entra(self):
        self.recargar_el_dia("15000", DIAS_DE_LA_VENTANA)

        self.assertEqual(self.resumen().recargado, Decimal("0.00"))

    def test_una_recarga_de_hoy_entra_aunque_sea_de_la_tarde(self):
        """El día se corta en la zona del colegio: una recarga de las 19:00 de
        Bogotá son las 00:00 UTC del día siguiente, y partir por UTC la sacaría
        del periodo."""
        movimiento = self.recargar_el_dia("8000", 0)
        MovimientoBilletera.objects.filter(pk=movimiento.pk).update(
            creado_en=timezone.make_aware(datetime.combine(HOY, time(19, 0)))
        )

        self.assertEqual(self.resumen().recargado, Decimal("8000.00"))


class ElSaldoNoEsDelPeriodoTest(BaseDeGasto):
    """`INV-2`. El saldo es la suma de **todos** los movimientos.

    Es la cifra que evita la resta mental que no cuadra: lo recargado menos lo
    gastado en catorce días no da el saldo, y sin decirlo la pantalla invita a
    pensar que sí.
    """

    def test_el_saldo_incluye_lo_recargado_antes_de_la_ventana(self):
        resumen = self.resumen()

        self.assertEqual(resumen.recargado, Decimal("0.00"))
        self.assertEqual(resumen.saldo, Decimal("500000.00"))

    def test_el_saldo_baja_con_lo_gastado(self):
        self.gastar_el_dia(dias_atras=0, cantidad=2)

        self.assertEqual(self.resumen().saldo, Decimal("495000.00"))


class ElPorcentajeYLaDeudaQueNoExisteTest(BaseDeGasto):
    def test_el_porcentaje_es_lo_gastado_sobre_lo_recargado(self):
        self.recargar_el_dia("10000", 2)
        self.gastar_el_dia(dias_atras=1, cantidad=2)

        self.assertEqual(self.resumen().porcentaje_gastado, 50)

    def test_sin_recargas_en_el_periodo_el_porcentaje_no_aplica(self):
        """`None` y no cero: dividir entre cero no es «el 0 %», es que la
        pregunta no tiene sentido. La pantalla tiene su propia frase."""
        self.gastar_el_dia(dias_atras=1)

        self.assertIsNone(self.resumen().porcentaje_gastado)

    def test_gastar_mas_de_lo_recargado_se_señala_y_no_es_deuda(self):
        """`INV-1` impide que una venta deje el saldo en negativo, así que la
        resta de las dos cifras **nunca** es un descubierto: es que tiró del
        saldo que ya tenía."""
        self.recargar_el_dia("2000", 3)
        self.gastar_el_dia(dias_atras=1, cantidad=2)

        resumen = self.resumen()
        self.assertTrue(resumen.gasto_sin_recarga_en_el_periodo)
        self.assertGreater(resumen.saldo, 0)

    def test_recargando_de_sobra_no_se_señala_nada(self):
        self.recargar_el_dia("50000", 3)
        self.gastar_el_dia(dias_atras=1)

        self.assertFalse(self.resumen().gasto_sin_recarga_en_el_periodo)


class ElDineroSaleAlReservarTest(BaseDeGasto):
    """La diferencia con los otros dos bloques, y la que parece un error.

    La frecuencia y los agregados cuentan una reserva **el día en que se
    recoge**; el gasto, **el día en que se paga**. Las dos cosas son ciertas: se
    comió el lunes y el dinero salió el domingo.
    """

    def test_una_reserva_sin_recoger_ya_es_gasto(self):
        pedido = self.reservar_para(dias_atras=2)
        MovimientoBilletera.objects.filter(venta=pedido.venta).update(
            creado_en=a_mediodia(HOY - timedelta(days=2))
        )

        self.assertEqual(self.resumen().gastado, Decimal("2500.00"))

    def test_entregarla_despues_no_vuelve_a_cobrar(self):
        """`TT-151`. La entrega no asienta ningún movimiento de billetera."""
        pedido = self.reservar_para(dias_atras=2)
        MovimientoBilletera.objects.filter(venta=pedido.venta).update(
            creado_en=a_mediodia(HOY - timedelta(days=2))
        )
        antes = self.resumen().gastado

        self.entregar_el_dia(pedido, dias_atras=1)

        self.assertEqual(self.resumen().gastado, antes)

    def test_el_gasto_cuenta_el_dia_del_pago_y_no_el_de_la_entrega(self):
        """Se paga **fuera** de la ventana y se entrega dentro: para el dinero,
        no hubo gasto en el periodo."""
        pedido = self.reservar_para(dias_atras=DIAS_DE_LA_VENTANA + 3)
        MovimientoBilletera.objects.filter(venta=pedido.venta).update(
            creado_en=a_mediodia(HOY - timedelta(days=DIAS_DE_LA_VENTANA + 3))
        )
        self.entregar_el_dia(pedido, dias_atras=1)

        self.assertEqual(self.resumen().gastado, Decimal("0.00"))


class LaPantallaResumeElGastoTest(BaseDeGasto):
    """`TT-166`, contra `data-*` propios y nunca contra la redacción."""

    def pantalla(self):
        self.client.force_login(self.acudiente)
        return self.client.get(
            reverse("historial-de-consumo", args=[self.estudiante.id])
        )

    def test_con_movimientos_la_pantalla_enseña_el_resumen(self):
        self.recargar_el_dia("20000", 2)
        self.gastar_el_dia(dias_atras=1)

        respuesta = self.pantalla()

        self.assertContains(respuesta, "data-resumen-de-gasto")
        self.assertContains(respuesta, "data-recargado")
        self.assertContains(respuesta, "data-gastado")
        self.assertContains(respuesta, "data-saldo")

    def test_la_pantalla_explica_que_no_hay_deuda(self):
        self.recargar_el_dia("2000", 3)
        self.gastar_el_dia(dias_atras=1, cantidad=2)

        self.assertContains(self.pantalla(), "data-gasto-sin-recarga")

    def test_sin_movimientos_no_se_dibuja_el_bloque(self):
        """Hay historial —para eso está la compra de hace tres meses— pero
        ningún movimiento dentro del periodo: un resumen de ceros no dice
        nada."""
        venta = self.comprar(dias_atras=0)
        self.fechar_los_movimientos_de(venta, 90)

        self.assertNotContains(self.pantalla(), "data-resumen-de-gasto")

    def test_no_se_dibuja_la_devolucion_que_no_existe(self):
        self.recargar_el_dia("20000", 2)
        self.gastar_el_dia(dias_atras=1)

        self.assertNotContains(self.pantalla(), "data-devuelto")


class SoloSuAcudienteVeElGastoTest(BaseDeGasto):
    """La misma puerta que el resto del módulo (`[S11]`, `DT-11`)."""

    def test_ningun_otro_rol_lo_consulta(self):
        from cuentas.models import Rol, Usuario

        for numero, rol in enumerate((Rol.CAJERO, Rol.ADMINISTRADOR, Rol.INSTITUCION)):
            with self.subTest(rol=rol):
                actor = Usuario.objects.crear_usuario(
                    email=f"otro-gasto-{numero}@example.com", rol=rol, nombre="Persona"
                )
                with self.assertRaises(PermissionDenied):
                    resumen_de_gasto(actor=actor, estudiante=self.estudiante)
