"""`TT-175`. El selector del reporte de cierres de caja (`HU-56`).

Los tres criterios de la historia, y dónde se comprueba cada uno:

1. **Los cierres quedan registrados y son consultables.** `cierres_registrados`
   devuelve el histórico acotado por jornada, con el cajero traído.
2. **El reporte alimenta la auditoría de `ALC-IN-22`.** Lo que la auditoría
   necesita no es una lista: es poder decir **cuánto descuadró el periodo**, y
   esa cifra tiene dos formas que no son la misma. Ver
   `ElDescuadreNoSeCompensaSoloTest`.
3. **El efectivo esperado de un día se explica desde sus ventas en efectivo**
   (`INVD-5`). Eso se comprueba desde la pantalla, siguiendo el enlace de cada
   fila: `ventas/tests_reporte_de_cierres.py`.

Y una prueba que no sale de ningún criterio: **las dos restas tienen que
coincidir**. `CierreDeCaja.diferencia` resta en Python y `DIFERENCIA_DEL_CIERRE`
en SQL, y son dos escrituras de la misma regla — la clase de duplicación que
`DT-19` evita y que aquí no tiene salida, porque sumar en Python obligaría a
traerse todos los cierres.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone

from cuentas.models import Rol, Usuario
from reportes.selectors import cierres_registrados, resumen_de_cierres
from ventas.models import CierreDeCaja
from ventas.selectors import DIFERENCIA_DEL_CIERRE


class BaseDeCierres(TestCase):
    """Una administración, un cajero y una fábrica de cierres.

    Los cierres se escriben directamente y no por `cerrar_caja`: lo que estas
    pruebas leen es el histórico, y montar una jornada de ventas para cada fila
    metería en el camino el cálculo del esperado, que ya tiene sus pruebas en
    `ventas/tests_cierre_de_caja.py`.
    """

    def setUp(self):
        self.administracion = Usuario.objects.crear_usuario(
            email="administracion-cierres@example.com",
            rol=Rol.ADMINISTRADOR,
            nombre="Administración",
        )
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero-cierres@example.com", rol=Rol.CAJERO, nombre="Diego Ramírez"
        )
        self.hoy = timezone.localdate()

    def cerrar(self, *, dias_atras=0, esperado="10000", base="20000", contado=None,
               motivo=""):
        """Un cierre de una jornada. `contado=None` cuadra exacto."""
        esperado = Decimal(esperado)
        base = Decimal(base)
        if contado is None:
            contado = base + esperado
        return CierreDeCaja.objects.create(
            fecha=self.hoy - timedelta(days=dias_atras),
            cajero=self.cajero,
            base=base,
            efectivo_esperado=esperado,
            efectivo_contado=Decimal(contado),
            motivo=motivo,
        )


class SoloLaAdministracionConsultaLosCierresTest(BaseDeCierres):
    """`[S11]` separa registrar de consolidar, y `HU-55` y `HU-56` son dos
    historias con dos actores distintos."""

    def test_la_administracion_entra(self):
        self.cerrar()

        self.assertEqual(cierres_registrados(actor=self.administracion).count(), 1)

    def test_el_cajero_no_consulta_el_historico_que_el_mismo_escribio(self):
        """No es un olvido. Cuadrar su caja es suyo; leer el patrón de
        descuadres de la cafetería es de quien administra el servicio."""
        with self.assertRaises(PermissionDenied):
            cierres_registrados(actor=self.cajero)

    def test_los_otros_dos_roles_tampoco(self):
        for rol in (Rol.INSTITUCION, Rol.ACUDIENTE):
            with self.subTest(rol=rol):
                actor = Usuario.objects.crear_usuario(
                    email=f"{rol}-cierres@example.com", rol=rol, nombre="Persona"
                )
                with self.assertRaises(PermissionDenied):
                    cierres_registrados(actor=actor)

    def test_el_rechazo_nombra_los_cierres_y_no_los_otros_reportes(self):
        """El rol exigido es el mismo que para los otros dos reportes, **y el
        mensaje no**.

        `cierres_registrados` reutiliza la comprobación de la administración, y
        sin decirle de qué habla contestaba «los reportes de ventas e inventario
        son de la administración» a quien intentó consultar los cierres: nombra
        otros reportes y otra historia. Se vio ejecutándolo, no en las pruebas —
        el mismo defecto que `TT-172` encontró en el servicio de cierre.

        Se afirma sobre la historia citada y no sobre la redacción entera, que
        cualquiera puede mejorar en un PR que no tenga que ver.
        """
        with self.assertRaises(PermissionDenied) as capturado:
            cierres_registrados(actor=self.cajero)

        mensaje = str(capturado.exception)
        self.assertIn("HU-56", mensaje)
        self.assertNotIn("inventario", mensaje.lower())

    def test_una_cuenta_desactivada_no_opera(self):
        self.administracion.is_active = False
        self.administracion.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            cierres_registrados(actor=self.administracion)


class ElPeriodoSeAcotaPorLaJornadaTest(BaseDeCierres):
    """Se filtra por `fecha`, no por `creado_en`.

    Lo que se acota es **la jornada que se cuadró**, no el instante en que
    alguien la registró. Son dos cosas distintas en cuanto un cierre se escribe
    después de medianoche, que es justo cuando se escriben.
    """

    def test_desde_y_hasta_son_inclusivos(self):
        self.cerrar(dias_atras=0)
        self.cerrar(dias_atras=1)
        self.cerrar(dias_atras=5)

        acotado = cierres_registrados(
            actor=self.administracion,
            desde=self.hoy - timedelta(days=1),
            hasta=self.hoy,
        )

        self.assertEqual(acotado.count(), 2)

    def test_sin_fechas_devuelve_el_historico_entero(self):
        self.cerrar(dias_atras=0)
        self.cerrar(dias_atras=30)

        self.assertEqual(cierres_registrados(actor=self.administracion).count(), 2)

    def test_un_cierre_escrito_hoy_de_la_jornada_de_ayer_es_de_ayer(self):
        """`creado_en` dice cuándo se escribió; `fecha`, qué se cuadró.

        El cierre nace con `creado_en` de ahora —es `auto_now_add`— y su jornada
        es la de ayer. Filtrar desde hoy **no** debe alcanzarlo: si el selector
        mirara `creado_en`, esta prueba fallaría.
        """
        self.cerrar(dias_atras=1)

        de_hoy = cierres_registrados(actor=self.administracion, desde=self.hoy)

        self.assertEqual(de_hoy.count(), 0)


class ElResumenCuentaLoQueSeEstaMirandoTest(BaseDeCierres):
    """Las cifras del consolidado, sobre un conjunto conocido."""

    def setUp(self):
        super().setUp()
        self.cerrar(dias_atras=0, esperado="10000", base="20000")            # cuadra
        self.cerrar(dias_atras=1, esperado="12000", base="20000",
                    contado="34000", motivo="Sobró un billete")              # +2.000
        self.cerrar(dias_atras=2, esperado="8000", base="20000",
                    contado="25000", motivo="Faltó un billete")              # -3.000
        self.resumen = resumen_de_cierres(cierres_registrados(actor=self.administracion))

    def test_cuenta_las_jornadas_y_como_acabo_cada_una(self):
        self.assertEqual(self.resumen.cuantos, 3)
        self.assertEqual(self.resumen.cuadrados, 1)
        self.assertEqual(self.resumen.sobrantes, 1)
        self.assertEqual(self.resumen.faltantes, 1)
        self.assertEqual(self.resumen.con_diferencia, 2)
        self.assertTrue(self.resumen.hubo_cierres)

    def test_suma_las_tres_cifras_de_dinero(self):
        self.assertEqual(self.resumen.esperado, Decimal("30000.00"))
        self.assertEqual(self.resumen.base, Decimal("60000.00"))
        self.assertEqual(self.resumen.contado, Decimal("89000.00"))

    def test_ningun_descuadre_va_sin_motivo(self):
        """Debería ser siempre cero: lo impone `cierre_de_caja_diferencia_con
        _motivo`. Se cuenta para poder enseñarlo, como las mermas sin motivo."""
        self.assertEqual(self.resumen.sin_motivo, 0)

    def test_el_resumen_sigue_al_filtro(self):
        """Es lo que justifica que reciba un `QuerySet` y no un periodo.

        Si volviera a consultar por su cuenta, el consolidado de arriba hablaría
        de otro conjunto que la tabla de abajo **sin que nada fallara**.
        """
        solo_ayer = cierres_registrados(
            actor=self.administracion,
            desde=self.hoy - timedelta(days=1),
            hasta=self.hoy - timedelta(days=1),
        )

        resumen = resumen_de_cierres(solo_ayer)

        self.assertEqual(resumen.cuantos, 1)
        self.assertEqual(resumen.sobrantes, 1)
        self.assertEqual(resumen.descuadre_total, Decimal("2000.00"))


class ElDescuadreNoSeCompensaSoloTest(BaseDeCierres):
    """**La cifra que la historia pide, y la que no basta.**

    El «para qué» de `HU-56` es detectar un **patrón** de descuadres en lugar de
    enterarse suelto cada día. Con la suma con signo, un sobrante de $2.000 y un
    faltante de $2.000 dan cero: un mes con veinte descuadres se leería como un
    mes que cuadra.
    """

    def test_la_neta_se_cancela_y_el_descuadre_total_no(self):
        self.cerrar(dias_atras=0, esperado="10000", base="20000",
                    contado="32000", motivo="Sobró")     # +2.000
        self.cerrar(dias_atras=1, esperado="10000", base="20000",
                    contado="28000", motivo="Faltó")     # -2.000

        resumen = resumen_de_cierres(cierres_registrados(actor=self.administracion))

        self.assertEqual(resumen.diferencia_neta, Decimal("0.00"))
        self.assertEqual(resumen.descuadre_total, Decimal("4000.00"))
        self.assertEqual(resumen.con_diferencia, 2)

    def test_una_jornada_que_cuadra_no_suma_descuadre(self):
        self.cerrar(dias_atras=0)

        resumen = resumen_de_cierres(cierres_registrados(actor=self.administracion))

        self.assertEqual(resumen.descuadre_total, Decimal("0.00"))
        self.assertEqual(resumen.diferencia_neta, Decimal("0.00"))


class UnPeriodoSinCierresNoEsUnPeriodoQueCuadroTest(BaseDeCierres):
    """Sin filas no se inventa un cero, por lo mismo que en los otros dos
    reportes: «$0 de descuadre» se lee como «todo cuadró»."""

    def test_sin_cierres_las_cifras_no_existen(self):
        resumen = resumen_de_cierres(cierres_registrados(actor=self.administracion))

        self.assertFalse(resumen.hubo_cierres)
        self.assertEqual(resumen.cuantos, 0)
        self.assertIsNone(resumen.descuadre_total)
        self.assertIsNone(resumen.esperado)


class LasDosRestasTienenQueCoincidirTest(BaseDeCierres):
    """`CierreDeCaja.diferencia` resta en Python; `DIFERENCIA_DEL_CIERRE`, en SQL.

    Son dos escrituras de la misma regla. Aquí no hay salida —agregar en Python
    obligaría a traerse todos los cierres—, así que lo que se hace en su lugar es
    fijar que dicen lo mismo. Si alguien toca una sola de las dos, esto falla.

    Sin esta prueba, el listado podría ordenar por una diferencia y enseñar
    otra, con las dos cifras bien formadas.
    """

    def test_coinciden_fila_a_fila(self):
        self.cerrar(dias_atras=0, esperado="10000", base="20000")
        self.cerrar(dias_atras=1, esperado="12000", base="20000",
                    contado="34000", motivo="Sobró")
        self.cerrar(dias_atras=2, esperado="8000", base="0",
                    contado="5500.50", motivo="Faltó")

        filas = CierreDeCaja.objects.annotate(en_sql=DIFERENCIA_DEL_CIERRE)

        self.assertEqual(filas.count(), 3)
        for cierre in filas:
            with self.subTest(fecha=cierre.fecha):
                self.assertEqual(cierre.en_sql, cierre.diferencia)

    def test_la_contraprueba_las_distinguiria(self):
        """Que la comparación de arriba no pase por casualidad: si una de las
        dos cambiara, la igualdad dejaría de cumplirse."""
        self.cerrar(dias_atras=0, esperado="10000", base="20000",
                    contado="31000", motivo="Sobró")

        cierre = CierreDeCaja.objects.annotate(en_sql=DIFERENCIA_DEL_CIERRE).get()

        self.assertEqual(cierre.diferencia, Decimal("1000.00"))
        self.assertNotEqual(cierre.en_sql, cierre.diferencia + 1)
