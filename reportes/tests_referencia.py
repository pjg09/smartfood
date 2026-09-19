"""`TT-162`, `TT-163`. La referencia sanitaria y el cálculo (`HU-32`).

Dos mitades, como en la frecuencia: la tabla y la aritmética se prueban sin base
de datos, y el agregado sobre las ventas tiene su propia clase al final.

La tabla que se ejercita es la de `docs/valores-de-referencia-nutricional.md`:
Resolución 810 de 2021 del Ministerio de Salud, artículo 15, `Tabla 9` y
`Tabla 10`, columna «niños mayores de 4 años y adultos». **Si alguien cambia un
número sin pasar por el documento, esto falla** — que es el único mecanismo que
tiene una cifra de una norma para no derivar en silencio.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.test import SimpleTestCase
from django.utils import timezone

from catalogo.models import Producto
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from reportes import referencia
from reportes.referencia import ClaseDeReferencia, comparar
from reportes.selectors import agregados_nutricionales
from reportes.tests_frecuencia import HOY, BaseDeFrecuencia, a_mediodia
from ventas.models import LineaVenta, Venta
from ventas.services import registrar_venta

# Los siete números del documento, escritos a mano y a propósito.
DEL_DOCUMENTO = {
    "energia_kcal": (Decimal("2000"), ClaseDeReferencia.NECESIDAD),
    "proteinas_g": (Decimal("50"), ClaseDeReferencia.NECESIDAD),
    "carbohidratos_g": (Decimal("300"), ClaseDeReferencia.NECESIDAD),
    "grasas_totales_g": (Decimal("66"), ClaseDeReferencia.NECESIDAD),
    "azucares_g": (Decimal("50"), ClaseDeReferencia.MAXIMO),
    "grasas_saturadas_g": (Decimal("20"), ClaseDeReferencia.MAXIMO),
    "sodio_mg": (Decimal("2000"), ClaseDeReferencia.MAXIMO),
}


class LaTablaEsLaDeLaNormaTest(SimpleTestCase):
    """`HU-32`, primer criterio. Los valores, uno a uno."""

    def test_cada_valor_es_el_de_la_resolucion(self):
        for valor in referencia.REFERENCIA_DIARIA:
            with self.subTest(nutriente=valor.campo):
                esperado, clase = DEL_DOCUMENTO[valor.campo]
                self.assertEqual(valor.valor, esperado)
                self.assertEqual(valor.clase, clase)

    def test_estan_los_siete_y_ninguno_mas(self):
        """Ni falta ninguno de los que el catálogo declara, ni sobra uno que no
        se capture: una referencia sin dato de origen no compara nada."""
        campos = {valor.campo for valor in referencia.REFERENCIA_DIARIA}

        self.assertEqual(campos, set(DEL_DOCUMENTO))
        self.assertEqual(campos, set(LineaVenta.CAMPOS_NUTRICIONALES))

    def test_los_tres_maximos_son_los_nutrientes_criticos(self):
        """`Tabla 10` es de enfermedades no transmisibles y la norma los rotula
        «Máx.»: sodio, grasa saturada y azúcares. Son los mismos tres que
        `docs/campos-nutricionales.md` llamó críticos."""
        maximos = {
            valor.campo
            for valor in referencia.REFERENCIA_DIARIA
            if valor.clase == ClaseDeReferencia.MAXIMO
        }

        self.assertEqual(maximos, {"sodio_mg", "grasas_saturadas_g", "azucares_g"})

    def test_los_azucares_llevan_declarada_su_salvedad(self):
        """`[S4.1]`. El catálogo declara azúcares totales y la norma fija un
        máximo de **añadidos**. La salvedad viaja con el dato, no con la
        plantilla: el día que esto se enseñe en otro sitio, va con él."""
        azucares = next(
            valor
            for valor in referencia.REFERENCIA_DIARIA
            if valor.campo == "azucares_g"
        )

        self.assertIn("añadidos", azucares.nota)


class ElCalculoEsDeterministicoTest(SimpleTestCase):
    """`HU-32`, segundo criterio. Sumas, una división y un redondeo declarado."""

    def test_el_promedio_es_el_total_entre_los_dias_con_consumo(self):
        comparaciones = comparar({"energia_kcal": Decimal("750")}, 2)

        energia = comparaciones[0]
        self.assertEqual(energia.promedio_diario, Decimal("375.00"))
        self.assertEqual(energia.porcentaje, 19)

    def test_el_redondeo_del_porcentaje_es_hacia_arriba_en_el_medio(self):
        """`ROUND_HALF_UP` declarado, no el redondeo al par de Python.

        570 mg sobre 2000 son 28,5 %. Con el redondeo por defecto saldría 28 —al
        par más cercano— y con el declarado, 29. Sin fijarlo, dos nutrientes
        equidistantes se redondearían en direcciones distintas sin que nadie lo
        esperara.
        """
        comparaciones = comparar({"sodio_mg": Decimal("1140")}, 2)

        sodio = next(c for c in comparaciones if c.referencia.campo == "sodio_mg")
        self.assertEqual(sodio.promedio_diario, Decimal("570.00"))
        self.assertEqual(sodio.porcentaje, 29)

    def test_sin_dias_con_consumo_no_hay_nada_que_comparar(self):
        """Un cero aquí sería inventado: no es que aportara cero, es que no hubo
        consumo que promediar."""
        self.assertEqual(comparar({"energia_kcal": Decimal("750")}, 0), [])

    def test_un_nutriente_que_nadie_declaro_no_vale_cero(self):
        """`TT-44`. Se publica como «sin datos», que es lo que se sabe."""
        comparaciones = comparar({"energia_kcal": Decimal("500")}, 1)

        sodio = next(c for c in comparaciones if c.referencia.campo == "sodio_mg")
        self.assertFalse(sodio.declarado)
        self.assertIsNone(sodio.promedio_diario)
        self.assertIsNone(sodio.porcentaje)

    def test_el_orden_es_el_de_la_tabla_y_no_el_de_los_datos(self):
        """Determinístico incluye el orden: la pantalla no ordena por su cuenta
        y dos consultas iguales dan la misma lista."""
        comparaciones = comparar({"sodio_mg": Decimal("100")}, 1)

        self.assertEqual(
            [c.referencia.campo for c in comparaciones],
            [valor.campo for valor in referencia.REFERENCIA_DIARIA],
        )

    def test_la_misma_entrada_da_siempre_la_misma_salida(self):
        entrada = {"energia_kcal": Decimal("1234"), "sodio_mg": Decimal("987")}

        self.assertEqual(comparar(entrada, 3), comparar(entrada, 3))


class ElPromedioSeEnseñaConLosDecimalesDeSuUnidadTest(SimpleTestCase):
    """Cero decimales en kcal y mg, uno en gramos.

    «388,89 kcal» no dice más que «389 kcal» y vuelve ilegible una columna de
    cifras; en gramos, la décima sí distingue.
    """

    def test_las_kilocalorias_van_sin_decimales(self):
        energia = comparar({"energia_kcal": Decimal("3500")}, 9)[0]

        self.assertEqual(energia.promedio_diario, Decimal("389"))

    def test_los_gramos_van_con_una_decima(self):
        comparaciones = comparar({"grasas_saturadas_g": Decimal("84")}, 9)

        saturadas = next(
            c for c in comparaciones if c.referencia.campo == "grasas_saturadas_g"
        )
        self.assertEqual(saturadas.promedio_diario, Decimal("9.3"))

    def test_el_porcentaje_no_depende_de_como_se_redondee_el_promedio(self):
        """Sale del total, no del promedio ya redondeado.

        3500 kcal en 9 días son 388,88… al día: el 19,44 % de 2000, que redondea
        a 19. Si el porcentaje saliera del promedio redondeado a 389, daría lo
        mismo aquí — pero serían dos redondeos encadenados, y la cifra dependería
        de con cuántos decimales se decidiera pintar el promedio.
        """
        energia = comparar({"energia_kcal": Decimal("3500")}, 9)[0]

        self.assertEqual(energia.porcentaje, 19)


class LaBarraSeRecortaPeroLaCifraNoTest(SimpleTestCase):
    """Un 140 % se enseña entero; lo que se recorta es el dibujo.

    Recortar también la cifra escondería justo el caso que más dice."""

    def test_por_debajo_de_cien_la_barra_es_el_porcentaje(self):
        comparacion = comparar({"energia_kcal": Decimal("400")}, 1)[0]

        self.assertEqual(comparacion.porcentaje, 20)
        self.assertEqual(comparacion.ancho_de_la_barra, 20)

    def test_por_encima_de_cien_la_barra_se_queda_en_cien(self):
        comparacion = comparar({"energia_kcal": Decimal("2800")}, 1)[0]

        self.assertEqual(comparacion.porcentaje, 140)
        self.assertEqual(comparacion.ancho_de_la_barra, 100)


class ElAgregadoSaleDeLaInstantaneaTest(BaseDeFrecuencia):
    """`TT-163` sobre las ventas de verdad, en la ventana de la regla."""

    def setUp(self):
        super().setUp()
        self.completo = self.con_ficha("Pan con ficha")
        self.sin_ficha = self.producto("Misterio", "Panadería")

    def con_ficha(self, nombre):
        articulo = Producto.objects.create(
            nombre=nombre,
            precio=Decimal("2000"),
            categoria=self.pan.categoria,
            porcion="unidad de 80 g",
            energia_kcal=250,
            proteinas_g=Decimal("8.00"),
            carbohidratos_g=Decimal("28.00"),
            azucares_g=Decimal("2.00"),
            grasas_totales_g=Decimal("11.00"),
            grasas_saturadas_g=Decimal("6.00"),
            sodio_mg=380,
        )
        MovimientoInventario.objects.create(
            producto=articulo,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=200,
            motivo="Ingreso de prueba",
        )
        return articulo

    def aporte(self):
        return agregados_nutricionales(
            actor=self.acudiente, estudiante=self.estudiante, hoy=HOY
        )

    def test_suma_por_unidades_vendidas(self):
        """Las cifras del catálogo son **por porción vendible** (`TT-44`): dos
        empanadas aportan el doble que una. Aquí sí se cuentan unidades, al
        revés que en la frecuencia."""
        self.comprar(dias_atras=0, articulo=self.completo, cantidad=2)
        self.comprar(dias_atras=1, articulo=self.completo, cantidad=1)

        aporte = self.aporte()
        energia = aporte.comparaciones[0]

        self.assertEqual(aporte.dias_con_consumo, 2)
        self.assertEqual(energia.total, 750)          # 3 × 250
        self.assertEqual(energia.promedio_diario, Decimal("375.00"))
        self.assertEqual(energia.porcentaje, 19)

    def test_un_producto_sin_ficha_queda_fuera_y_se_cuenta(self):
        """`[S2.2]` de `docs/campos-nutricionales.md`, literal: excluir del
        agregado lo que no declara **y decir cuántos se excluyeron**."""
        self.comprar(dias_atras=0, articulo=self.completo, cantidad=1)
        self.comprar(dias_atras=0, articulo=self.sin_ficha, cantidad=5)

        aporte = self.aporte()

        self.assertEqual(aporte.renglones_sin_declarar, 1)
        # Las cinco unidades sin ficha no bajan el promedio: no aportan cero,
        # no aportan nada.
        self.assertEqual(aporte.comparaciones[0].total, 250)

    def test_lo_de_fuera_de_la_ventana_no_entra(self):
        self.comprar(dias_atras=0, articulo=self.completo, cantidad=1)
        self.comprar(
            dias_atras=self.ventana_mas_uno(), articulo=self.completo, cantidad=10
        )

        self.assertEqual(self.aporte().comparaciones[0].total, 250)

    def ventana_mas_uno(self):
        from reportes.reglas import DIAS_DE_LA_VENTANA

        return DIAS_DE_LA_VENTANA + 1

    def test_una_reserva_sin_recoger_no_aporta_todavia(self):
        """Misma definición de «consumido» que la frecuencia: viene del mismo
        ayudante, así que no pueden discrepar."""
        self.reservar_para(dias_atras=1, articulo=self.completo)

        aporte = self.aporte()

        self.assertEqual(aporte.dias_con_consumo, 0)
        self.assertEqual(aporte.comparaciones, [])

    def test_editar_el_catalogo_no_cambia_el_agregado(self):
        """`DT-8`. Se suma la instantánea, no el producto de hoy: corregir una
        ficha nutricional no puede reescribir lo que un niño comió."""
        self.comprar(dias_atras=0, articulo=self.completo, cantidad=1)

        self.completo.energia_kcal = 9000
        self.completo.save(update_fields=["energia_kcal"])

        self.assertEqual(self.aporte().comparaciones[0].total, 250)

    def test_sin_compras_no_hay_aporte(self):
        aporte = self.aporte()

        self.assertFalse(aporte.hay_datos)
        self.assertEqual(aporte.dias_con_consumo, 0)


class SoloSuAcudienteVeElAporteTest(BaseDeFrecuencia):
    """La misma puerta que el resto del módulo (`[S11]`, `DT-11`)."""

    def test_ningun_otro_rol_lo_consulta(self):
        from django.core.exceptions import PermissionDenied

        from cuentas.models import Rol, Usuario

        for numero, rol in enumerate((Rol.CAJERO, Rol.ADMINISTRADOR, Rol.INSTITUCION)):
            with self.subTest(rol=rol):
                actor = Usuario.objects.crear_usuario(
                    email=f"otro-aporte-{numero}@example.com", rol=rol, nombre="Persona"
                )
                with self.assertRaises(PermissionDenied):
                    agregados_nutricionales(actor=actor, estudiante=self.estudiante)
