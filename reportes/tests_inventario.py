"""`TT-169`. El reporte de movimientos de inventario (`HU-36`).

Su único criterio —«el reporte cubre los movimientos registrados **con su
motivo**»— y el «para qué» de la historia, que es lo que decide la forma:
**revisar entradas, ventas y mermas en un solo lugar**. No son tres informes:
son tres clases de asiento del mismo libro.

Lo que puede salir mal, y por eso tiene prueba:

1. **El signo.** En el libro una salida es negativa (`DT-5`); «salieron 12
   unidades» no es una cifra negativa.
2. **El agrupamiento**, la trampa que `TT-168` pagó: un `order_by()` explícito
   —el que pone el admin— entra en el `GROUP BY` de un `values().annotate()`.
3. **Que el neto sea de verdad la suma del libro**, que es `INV-3` puesta donde
   se puede comprobar.

`mermas_sin_motivo` debería ser siempre cero porque lo impone una
`CheckConstraint`. Se comprueba **contra la base**, escribiendo por el ORM para
saltarse el servicio: si la restricción desapareciera, esa prueba es la que lo
dice.
"""

from datetime import date, datetime, time
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de
from ventas.models import MedioDePago, Venta
from reportes.selectors import movimientos_registrados, resumen_de_movimientos


class BaseDelLibro(TestCase):
    def setUp(self):
        self.administracion = Usuario.objects.crear_usuario(
            email="administracion-inv@example.com",
            rol=Rol.ADMINISTRADOR,
            nombre="Administración",
        )
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero-inv@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
        self.pan = Producto.objects.create(
            nombre="Pan de queso", precio=Decimal("2500"), categoria=categoria
        )

    def asentar(self, tipo, cantidad, motivo="", producto=None, venta=None):
        """Escribe en el libro **por el ORM**, sin pasar por los servicios.

        Es lo que permite montar un periodo con las tres clases de asiento sin
        tener que fabricar una venta entera, y lo que deja comprobar que la
        `CheckConstraint` de `INV-8` está de verdad en la base.
        """
        return MovimientoInventario.objects.create(
            producto=producto or self.pan,
            tipo=tipo,
            cantidad=cantidad,
            motivo=motivo,
            venta=venta,
        )

    def ingresar(self, cantidad=10, **extra):
        return self.asentar(
            TipoDeMovimientoDeInventario.INGRESO, cantidad, motivo="Compra", **extra
        )

    def vender(self, cantidad=2, **extra):
        """Una salida por venta, **con su venta detrás**.

        Una `CheckConstraint` no admite un movimiento de venta sin ella: el
        motivo de esa salida **es** la venta, y `INV-3` exige poder ir a
        mirarla. Se crea la venta desnuda —genérica y en efectivo, que es la
        combinación que su propia restricción admite sin estudiante— porque lo
        que se está probando es la agregación del libro, no el cobro.
        """
        venta = Venta.objects.create(
            cajero=self.cajero, medio_pago=MedioDePago.EFECTIVO
        )
        return self.asentar(
            TipoDeMovimientoDeInventario.VENTA, -cantidad, venta=venta, **extra
        )

    def mermar(self, cantidad=1, motivo="Rotura", **extra):
        return self.asentar(
            TipoDeMovimientoDeInventario.MERMA, -cantidad, motivo=motivo, **extra
        )

    def libro(self):
        return movimientos_registrados(actor=self.administracion)

    def resumen(self):
        return resumen_de_movimientos(self.libro())


class LasTresClasesDeAsientoEnUnSoloSitioTest(BaseDelLibro):
    """El «para qué» de `HU-36`."""

    def test_entradas_ventas_y_mermas_entran_en_el_mismo_libro(self):
        self.ingresar(cantidad=20)
        self.vender(cantidad=3)
        self.mermar(cantidad=2)

        self.assertEqual(self.libro().count(), 3)

    def test_el_desglose_trae_los_tres_tipos_aunque_falte_alguno(self):
        """Un tipo sin asientos sale en cero. Que en el periodo no hubiera
        ninguna merma es justamente lo que se quiere poder leer."""
        self.ingresar()

        etiquetas = [fila[0] for fila in self.resumen().por_tipo]

        self.assertEqual(
            etiquetas, [t.label for t in TipoDeMovimientoDeInventario]
        )

    def test_el_tipo_sin_asientos_sale_en_cero(self):
        self.ingresar(cantidad=20)

        por_tipo = {
            etiqueta: (cuantos, unidades)
            for etiqueta, cuantos, unidades in self.resumen().por_tipo
        }

        self.assertEqual(
            por_tipo[TipoDeMovimientoDeInventario.INGRESO.label], (1, 20)
        )
        self.assertEqual(por_tipo[TipoDeMovimientoDeInventario.MERMA.label], (0, 0))


class LasSalidasSeCuentanEnPositivoTest(BaseDelLibro):
    """`DT-5`. En el libro una salida resta; «salieron 12 unidades» no es una
    cifra negativa."""

    def test_entradas_y_salidas_van_las_dos_en_positivo(self):
        self.ingresar(cantidad=20)
        self.vender(cantidad=3)
        self.mermar(cantidad=2)

        resumen = self.resumen()

        self.assertEqual(resumen.entradas, 20)
        self.assertEqual(resumen.salidas, 5)

    def test_las_unidades_del_desglose_tambien(self):
        self.vender(cantidad=7)

        por_tipo = {
            etiqueta: unidades
            for etiqueta, _, unidades in self.resumen().por_tipo
        }

        self.assertEqual(por_tipo[TipoDeMovimientoDeInventario.VENTA.label], 7)

    def test_el_neto_si_lleva_signo(self):
        """Es la única cifra con signo, y tiene que tenerlo: dice si el periodo
        dejó más o menos de lo que había."""
        self.ingresar(cantidad=10)
        self.vender(cantidad=14)

        self.assertEqual(self.resumen().neto, -4)


class ElNetoEsLaSumaDelLibroTest(BaseDelLibro):
    """`INV-3` puesta donde se puede comprobar.

    Sobre el libro entero, el neto **son** las existencias. Se compara contra
    `existencias_de`, que suma por otro camino: si alguna vez divergen, esta
    prueba lo dice antes que una pantalla.
    """

    def test_sobre_el_libro_entero_el_neto_son_las_existencias(self):
        self.ingresar(cantidad=40)
        self.vender(cantidad=6)
        self.mermar(cantidad=4)

        self.assertEqual(self.resumen().neto, existencias_de(self.pan))
        self.assertEqual(self.resumen().neto, 30)

    def test_el_neto_de_un_periodo_no_son_las_existencias(self):
        """Y por eso la pantalla lo dice: acotar el periodo deja fuera los
        asientos anteriores, así que el neto pasa a ser «lo que movió esto»."""
        viejo = self.ingresar(cantidad=40)
        MovimientoInventario.objects.filter(pk=viejo.pk).update(
            creado_en=timezone.make_aware(datetime.combine(date(2026, 1, 1), time(12, 0)))
        )
        self.vender(cantidad=6)

        del_periodo = resumen_de_movimientos(
            movimientos_registrados(
                actor=self.administracion, desde=timezone.localdate()
            )
        )

        self.assertEqual(del_periodo.neto, -6)
        self.assertEqual(existencias_de(self.pan), 34)


class ElConsolidadoAgrupaBienAunqueVengaOrdenadoTest(BaseDelLibro):
    """La trampa que `TT-168` pagó, comprobada aquí antes de repetirla.

    Un `order_by()` explícito entra en el `GROUP BY` de un `values().annotate()`
    —el `ordering` del `Meta` ya no, desde Django 3.1— y el admin siempre ordena
    el listado. Sin limpiarlo, cada asiento forma su propio grupo y el desglose
    dice «1» en todas las filas mientras el total de al lado sigue bien.
    """

    def test_varios_asientos_del_mismo_tipo_se_agrupan_en_una_fila(self):
        self.ingresar(cantidad=10)
        self.ingresar(cantidad=5)
        self.vender(cantidad=2)

        ordenados = self.libro().order_by("-creado_en")
        por_tipo = {
            etiqueta: (cuantos, unidades)
            for etiqueta, cuantos, unidades in resumen_de_movimientos(
                ordenados
            ).por_tipo
        }

        self.assertEqual(
            por_tipo[TipoDeMovimientoDeInventario.INGRESO.label], (2, 15)
        )

    def test_el_desglose_cuadra_con_el_total(self):
        self.ingresar(cantidad=10)
        self.ingresar(cantidad=5)
        self.vender(cantidad=2)
        self.mermar(cantidad=3)

        resumen = resumen_de_movimientos(self.libro().order_by("-creado_en"))

        self.assertEqual(
            sum(cuantos for _, cuantos, _ in resumen.por_tipo), resumen.cuantos
        )
        self.assertEqual(
            sum(unidades for _, _, unidades in resumen.por_tipo),
            resumen.entradas + resumen.salidas,
        )


class TodaMermaLlevaSuMotivoTest(BaseDelLibro):
    """El criterio de `HU-36` —«con su motivo»— e `INV-8`.

    El recuento debería ser siempre cero, y no por revisión: lo impone una
    `CheckConstraint`. Se enseña igual, que es lo que convierte la invariante en
    algo que la administración puede ver.
    """

    def test_las_mermas_con_motivo_no_cuentan_como_huecos(self):
        self.mermar(cantidad=2, motivo="Caducidad")
        self.mermar(cantidad=1, motivo="Rotura")

        self.assertEqual(self.resumen().mermas_sin_motivo, 0)

    def test_la_base_no_admite_una_merma_sin_motivo(self):
        """**Escribiendo por el ORM**, sin pasar por el servicio: si la
        restricción desapareciera, el formulario seguiría exigiéndolo y nadie
        se enteraría hasta que alguien escribiera desde un `shell`."""
        with self.assertRaises(IntegrityError):
            self.asentar(TipoDeMovimientoDeInventario.MERMA, -3, motivo="")

    def test_un_ingreso_sin_motivo_no_cuenta_como_merma_sin_motivo(self):
        """El motivo es obligatorio **solo en la merma** (`INV-8`): el ingreso y
        la venta pueden no llevarlo, y contarlos aquí daría una alarma falsa."""
        self.asentar(TipoDeMovimientoDeInventario.INGRESO, 10, motivo="")
        self.vender(cantidad=1)

        self.assertEqual(self.resumen().mermas_sin_motivo, 0)


class ElPeriodoRecortaElLibroTest(BaseDelLibro):
    def fechar(self, movimiento, dia):
        MovimientoInventario.objects.filter(pk=movimiento.pk).update(
            creado_en=timezone.make_aware(datetime.combine(dia, time(12, 0)))
        )

    def test_el_dia_del_final_entra_entero(self):
        self.fechar(self.ingresar(), date(2026, 9, 10))

        libro = movimientos_registrados(
            actor=self.administracion, hasta=date(2026, 9, 10)
        )

        self.assertEqual(libro.count(), 1)

    def test_lo_de_antes_del_comienzo_no_entra(self):
        self.fechar(self.ingresar(), date(2026, 9, 1))

        libro = movimientos_registrados(
            actor=self.administracion, desde=date(2026, 9, 2)
        )

        self.assertEqual(libro.count(), 0)

    def test_sin_movimientos_no_se_inventa_un_cero(self):
        resumen = self.resumen()

        self.assertFalse(resumen.hubo_movimientos)
        self.assertEqual(resumen.cuantos, 0)


class SoloLaAdministracionConsultaElLibroTest(BaseDelLibro):
    """Misma puerta que el reporte de ventas: `[S11]` los concede en la misma
    fila, «reportes de ventas **e inventario**»."""

    def test_ningun_otro_rol_consulta(self):
        for numero, rol in enumerate((Rol.CAJERO, Rol.INSTITUCION, Rol.ACUDIENTE)):
            with self.subTest(rol=rol):
                actor = Usuario.objects.crear_usuario(
                    email=f"otro-inv-{numero}@example.com", rol=rol, nombre="Persona"
                )
                with self.assertRaises(PermissionDenied):
                    movimientos_registrados(actor=actor)

    def test_sin_actor_tampoco(self):
        with self.assertRaises(PermissionDenied):
            movimientos_registrados(actor=None)

    def test_una_cuenta_desactivada_no_consulta(self):
        self.administracion.is_active = False
        self.administracion.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            movimientos_registrados(actor=self.administracion)
