"""`TT-167`. El reporte de ventas de la cafetería (`HU-35`).

Los dos criterios de la historia, y dónde se comprueba cada uno:

1. **Se construye sobre las transacciones registradas, no sobre datos
   capturados aparte.** No hay tabla de resumen que nadie mantiene: el reporte
   es el libro de ventas agregado, y el total sale de las líneas con el precio
   que tenían al venderse (`DT-8`). `ElTotalSaleDeLaInstantaneaTest` lo fija.
2. **Solo la administración de la cafetería accede.** `[S11]` son dos filas
   distintas: el cajero registra ventas y **no** consulta el consolidado.

Lo que más fácil se rompe sin que nadie lo note es el recuento: sumar los
importes obliga a unir con las líneas, y sin `distinct` una venta de tres
renglones cuenta como tres **con las cifras de dinero intactas**. Por eso hay
una prueba con una venta de varios renglones.
"""

from datetime import date, datetime, time
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone

from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from reportes.selectors import resumen_de_ventas, ventas_registradas
from ventas.models import MedioDePago, OrigenDeLaVenta, Venta
from ventas.services import registrar_venta, reservar


class BaseDelReporte(TestCase):
    """Una cafetería con un cajero, una familia con saldo y dos productos."""

    def setUp(self):
        self.administracion = Usuario.objects.crear_usuario(
            email="administracion-reporte@example.com",
            rol=Rol.ADMINISTRADOR,
            nombre="Administración",
        )
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero-reporte@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        acudiente = Usuario.objects.crear_usuario(
            email="marta-reporte@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
        )
        ficha = Acudiente.objects.create(
            usuario=acudiente, nombre="Marta Ruiz Ochoa", documento="4310077001"
        )
        self.acudiente = acudiente
        self.estudiante = Estudiante.objects.create(
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001077001",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        recargar(
            actor=acudiente, estudiante=self.estudiante, monto=Decimal("200000")
        )
        self.pan = self.producto("Pan de queso", "2500")
        self.jugo = self.producto("Jugo de mora", "3500")

    def producto(self, nombre, precio):
        categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
        articulo = Producto.objects.create(
            nombre=nombre, precio=Decimal(precio), categoria=categoria
        )
        MovimientoInventario.objects.create(
            producto=articulo,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=100,
            motivo="Ingreso de prueba",
        )
        return articulo

    def vender(self, cantidad=1, articulo=None):
        return registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante,
            lineas={(articulo or self.pan).id: cantidad},
        )

    def vender_generica(self, cantidad=1, medio=MedioDePago.EFECTIVO):
        return registrar_venta(
            actor=self.cajero,
            lineas={self.pan.id: cantidad},
            medio_pago=medio,
        )

    def libro(self):
        return ventas_registradas(actor=self.administracion)

    def resumen(self):
        return resumen_de_ventas(self.libro())


class ElLibroTraeTodaLaActividadComercialTest(BaseDelReporte):
    """Primer criterio: **las transacciones registradas**, todas ellas."""

    def test_la_venta_del_mostrador_entra(self):
        self.vender()

        self.assertEqual(self.libro().count(), 1)

    def test_la_venta_generica_tambien_entra(self):
        """`HU-53`, `DEC-1`. Docentes y visitantes son ventas de la cafetería.

        `[S5]` del anteproyecto lo dice expreso: sus transacciones «forman parte
        de las ventas totales» y hacen falta para que los reportes reflejen la
        actividad real. Excluirlas daría un reporte más limpio y falso.
        """
        self.vender_generica()

        self.assertEqual(self.libro().count(), 1)

    def test_la_reserva_tambien_entra(self):
        """`HU-23`. Una reserva **es** una venta anticipada (`DT-32`): está
        cobrada y es actividad comercial del periodo en que se cobró."""
        reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.pan.id: 1},
        )

        self.assertEqual(self.libro().count(), 1)

    def test_sin_ventas_el_libro_esta_vacio(self):
        self.assertEqual(self.libro().count(), 0)


class ElPeriodoRecortaPorLosDosLadosTest(BaseDelReporte):
    """`desde` y `hasta` son fechas locales **inclusivas**.

    El borde de `hasta` es el que se escribe mal: comparar contra la medianoche
    de ese mismo día dejaría fuera todo lo vendido durante la jornada, y el
    reporte de «hasta hoy» no enseñaría lo de hoy.
    """

    def fechar(self, venta, dia):
        Venta.objects.filter(pk=venta.pk).update(
            creado_en=timezone.make_aware(datetime.combine(dia, time(12, 0)))
        )

    def test_lo_de_antes_del_comienzo_no_entra(self):
        venta = self.vender()
        self.fechar(venta, date(2026, 9, 1))

        libro = ventas_registradas(
            actor=self.administracion, desde=date(2026, 9, 2)
        )

        self.assertEqual(libro.count(), 0)

    def test_el_dia_del_comienzo_entra_entero(self):
        venta = self.vender()
        self.fechar(venta, date(2026, 9, 2))

        libro = ventas_registradas(
            actor=self.administracion, desde=date(2026, 9, 2)
        )

        self.assertEqual(libro.count(), 1)

    def test_el_dia_del_final_entra_entero(self):
        """El borde que se escribe mal: una venta del mediodía del último día."""
        venta = self.vender()
        self.fechar(venta, date(2026, 9, 10))

        libro = ventas_registradas(
            actor=self.administracion, hasta=date(2026, 9, 10)
        )

        self.assertEqual(libro.count(), 1)

    def test_lo_de_despues_del_final_no_entra(self):
        venta = self.vender()
        self.fechar(venta, date(2026, 9, 11))

        libro = ventas_registradas(
            actor=self.administracion, hasta=date(2026, 9, 10)
        )

        self.assertEqual(libro.count(), 0)

    def test_sin_periodo_devuelve_el_libro_entero(self):
        venta = self.vender()
        self.fechar(venta, date(2020, 1, 1))

        self.assertEqual(self.libro().count(), 1)


class ElResumenSumaLoQueSeLePasaTest(BaseDelReporte):
    def test_cuenta_las_ventas_y_suma_los_importes(self):
        self.vender(cantidad=2)                      # 2 × 2500 = 5000
        self.vender_generica(cantidad=1)             # 1 × 2500 = 2500

        resumen = self.resumen()

        self.assertEqual(resumen.cuantas, 2)
        self.assertEqual(resumen.total, Decimal("7500.00"))
        self.assertEqual(resumen.unidades, 3)

    def test_una_venta_de_varios_renglones_cuenta_como_una(self):
        """**La prueba que importa del recuento.**

        Sumar los importes une con las líneas, así que sin `distinct` esta venta
        contaría como dos. Y el fallo sería invisible: el dinero saldría bien y
        solo mentiría el número de ventas.
        """
        registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante,
            lineas={self.pan.id: 2, self.jugo.id: 1},
        )

        resumen = self.resumen()

        self.assertEqual(resumen.cuantas, 1)
        self.assertEqual(resumen.total, Decimal("8500.00"))
        self.assertEqual(resumen.unidades, 3)

    def test_sin_ventas_el_total_no_es_cero_sino_nada(self):
        """No es que se vendiera cero: es que no hay nada que sumar. Quien lo
        pinta decide cómo decirlo, y la pantalla no dibuja un «$0»."""
        resumen = self.resumen()

        self.assertEqual(resumen.cuantas, 0)
        self.assertIsNone(resumen.total)
        self.assertFalse(resumen.hubo_ventas)

    def test_resume_exactamente_el_conjunto_que_recibe(self):
        """Recibe un `QuerySet` y no un periodo, y de ahí sale su utilidad: en
        el admin se le pasa el listado ya filtrado, así que el consolidado de
        arriba y la tabla de abajo no pueden hablar de conjuntos distintos."""
        self.vender(cantidad=2)
        self.vender_generica(cantidad=4)

        solo_efectivo = resumen_de_ventas(
            self.libro().filter(medio_pago=MedioDePago.EFECTIVO)
        )

        self.assertEqual(solo_efectivo.cuantas, 1)
        self.assertEqual(solo_efectivo.unidades, 4)


class ElTotalSaleDeLaInstantaneaTest(BaseDelReporte):
    """`DT-8`. Un reporte de mayo tiene que seguir diciendo lo de mayo."""

    def test_subir_el_precio_no_reescribe_el_reporte(self):
        self.vender(cantidad=2)

        self.pan.precio = Decimal("9900")
        self.pan.save(update_fields=["precio"])

        self.assertEqual(self.resumen().total, Decimal("5000.00"))


class LosDesglosesLleganCompletosTest(BaseDelReporte):
    """Un medio sin ventas sale en cero, no desaparece.

    Que no se cobrara nada por transferencia es un dato del periodo; una fila
    ausente se lee como si el medio no existiera.
    """

    def test_estan_los_tres_medios_de_pago_aunque_falten_ventas(self):
        self.vender()

        etiquetas = [fila[0] for fila in self.resumen().por_medio_de_pago]

        self.assertEqual(etiquetas, [m.label for m in MedioDePago])

    def test_el_medio_sin_ventas_sale_en_cero(self):
        self.vender()

        por_medio = dict(
            (etiqueta, (cuantas, total))
            for etiqueta, cuantas, total in self.resumen().por_medio_de_pago
        )

        self.assertEqual(por_medio[MedioDePago.BILLETERA.label], (1, Decimal("2500.00")))
        self.assertEqual(
            por_medio[MedioDePago.TRANSFERENCIA.label], (0, Decimal("0.00"))
        )

    def test_varias_ventas_del_mismo_medio_se_agrupan_en_una_fila(self):
        """**La prueba que faltaba y dejó pasar el fallo.**

        Con una sola venta por medio, agrupar mal es invisible: cada grupo da
        uno de todas formas. Hacen falta dos del mismo medio.
        """
        self.vender(cantidad=1)
        self.vender(cantidad=3)
        self.vender_generica(cantidad=2)

        por_medio = {
            etiqueta: (cuantas, total)
            for etiqueta, cuantas, total in self.resumen().por_medio_de_pago
        }

        self.assertEqual(
            por_medio[MedioDePago.BILLETERA.label], (2, Decimal("10000.00"))
        )
        self.assertEqual(
            por_medio[MedioDePago.EFECTIVO.label], (1, Decimal("5000.00"))
        )

    def test_agrupa_bien_aunque_el_conjunto_venga_ordenado(self):
        """**Este es el caso que de verdad falló, y el de arriba no lo caza.**

        Un `order_by()` **explícito** sí entra en el `GROUP BY` de un
        `values().annotate()` —el `ordering` del `Meta` ya no, desde Django
        3.1—, y el admin siempre ordena el listado explícitamente. Con el orden
        dentro del agrupamiento, cada venta forma su propio grupo y el desglose
        dice «1» en todas las filas **mientras el total de arriba sigue bien**,
        porque `aggregate()` no arrastra el orden.

        Se vio mirando la pantalla: catorce ventas en la tabla y tres filas de
        desglose con un uno cada una.
        """
        self.vender(cantidad=1)
        self.vender(cantidad=3)

        ordenadas = self.libro().order_by("-creado_en")
        por_medio = {
            etiqueta: cuantas
            for etiqueta, cuantas, _ in resumen_de_ventas(
                ordenadas
            ).por_medio_de_pago
        }

        self.assertEqual(por_medio[MedioDePago.BILLETERA.label], 2)

    def test_los_desgloses_suman_lo_mismo_que_el_total(self):
        """Ata las tres cifras entre sí: si un desglose se agrupa mal, deja de
        cuadrar con el total, que sale por otro camino (`aggregate`)."""
        self.vender(cantidad=2)
        self.vender(cantidad=1)
        self.vender_generica(cantidad=4)

        resumen = self.resumen()

        self.assertEqual(
            sum(total for _, _, total in resumen.por_medio_de_pago), resumen.total
        )
        self.assertEqual(
            sum(cuantas for _, cuantas, _ in resumen.por_medio_de_pago),
            resumen.cuantas,
        )
        self.assertEqual(
            sum(total for _, _, total in resumen.por_origen), resumen.total
        )

    def test_el_desglose_por_origen_separa_mostrador_y_reserva(self):
        self.vender()
        reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.jugo.id: 1},
        )

        por_origen = dict(
            (etiqueta, cuantas)
            for etiqueta, cuantas, _ in self.resumen().por_origen
        )

        self.assertEqual(por_origen[OrigenDeLaVenta.PUNTO_DE_VENTA.label], 1)
        self.assertEqual(por_origen[OrigenDeLaVenta.RESERVA.label], 1)


class SoloLaAdministracionConsultaElReporteTest(BaseDelReporte):
    """Segundo criterio de `HU-35`, y `[S11]` en la capa de datos (`DT-11`)."""

    def test_la_administracion_consulta(self):
        self.assertEqual(self.libro().count(), 0)

    def test_el_cajero_no_consulta_el_consolidado(self):
        """**Registra las ventas y no las reporta.** `[S11]` son dos filas
        distintas, y `[S5]` explica por qué: el trabajo del administrador «no se
        centra en cada transacción individual, sino en la información
        acumulada»."""
        with self.assertRaises(PermissionDenied):
            ventas_registradas(actor=self.cajero)

    def test_la_institucion_tampoco(self):
        """Es responsable de los datos de los menores, no del negocio de la
        cafetería, que puede estar en manos de un operador externo."""
        institucion = Usuario.objects.crear_usuario(
            email="institucion-reporte@example.com",
            rol=Rol.INSTITUCION,
            nombre="Secretaría",
        )

        with self.assertRaises(PermissionDenied):
            ventas_registradas(actor=institucion)

    def test_el_acudiente_tampoco(self):
        with self.assertRaises(PermissionDenied):
            ventas_registradas(actor=self.acudiente)

    def test_sin_actor_tampoco(self):
        with self.assertRaises(PermissionDenied):
            ventas_registradas(actor=None)

    def test_una_cuenta_desactivada_no_consulta(self):
        """`HU-42`. Desactivar una cuenta apaga todo lo que hacía."""
        self.administracion.is_active = False
        self.administracion.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            ventas_registradas(actor=self.administracion)
