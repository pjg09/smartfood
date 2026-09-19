"""`TT-158`, `TT-159`. Los umbrales de frecuencia, sin tocar la base (`HU-31`).

El contrato que se ejercita es `docs/reglas-de-frecuencia-de-consumo.md`. Aquí
no hay estudiantes, ni ventas, ni consultas: se le pasa al motor un recuento y
se comprueba el veredicto. **Es lo que hace comprobable un umbral sin sembrar
catorce días de compras**, y lo que permite fijar los bordes exactos —cuatro no
avisa, cinco sí— que con datos reales costaría montar.

`OBJ-E3` y `ALC-IN-21` exigen reglas **determinísticas**. Estas pruebas son la
forma de decir qué significa eso: misma entrada, misma salida, mismo orden.
"""

from django.test import SimpleTestCase

from reportes import reglas
from reportes.reglas import (
    UMBRAL_FRECUENCIA_ALTA,
    UMBRAL_FRECUENCIA_MUY_ALTA,
    NivelDeFrecuencia,
)


class LosUmbralesSonLosDelDocumentoTest(SimpleTestCase):
    """Los números de `[S2]`, escritos aquí para que cambiarlos se note.

    Si alguien toca un umbral sin pasar por `docs/reglas-de-frecuencia-de-consumo.md`,
    esto falla. **Es el único sitio donde una prueba fija una cifra de negocio a
    mano**, y es a propósito: el umbral no es un detalle de implementación, es la
    decisión que `TT-158` tomó y que hay que poder defender en la sustentación.
    """

    def test_la_ventana_es_de_catorce_dias(self):
        self.assertEqual(reglas.DIAS_DE_LA_VENTANA, 14)

    def test_los_dos_umbrales_son_cinco_y_ocho(self):
        self.assertEqual(UMBRAL_FRECUENCIA_ALTA, 5)
        self.assertEqual(UMBRAL_FRECUENCIA_MUY_ALTA, 8)


class ElUmbralSeMiraEnElBordeTest(SimpleTestCase):
    """Un umbral mal escrito —`>` donde va `>=`— desplaza la regla un día entero
    y no se ve con datos de ejemplo. Aquí se mira justo en el borde."""

    def test_por_debajo_del_umbral_no_se_publica_nada(self):
        alertas = reglas.evaluar({"Panadería": UMBRAL_FRECUENCIA_ALTA - 1})

        self.assertEqual(alertas, [])

    def test_en_el_umbral_exacto_ya_avisa(self):
        alertas = reglas.evaluar({"Panadería": UMBRAL_FRECUENCIA_ALTA})

        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0].nivel, NivelDeFrecuencia.ALTA)

    def test_justo_debajo_del_segundo_umbral_sigue_siendo_alta(self):
        alertas = reglas.evaluar({"Panadería": UMBRAL_FRECUENCIA_MUY_ALTA - 1})

        self.assertEqual(alertas[0].nivel, NivelDeFrecuencia.ALTA)
        self.assertFalse(alertas[0].es_muy_alta)

    def test_en_el_segundo_umbral_pasa_a_muy_alta(self):
        alertas = reglas.evaluar({"Panadería": UMBRAL_FRECUENCIA_MUY_ALTA})

        self.assertEqual(alertas[0].nivel, NivelDeFrecuencia.MUY_ALTA)
        self.assertTrue(alertas[0].es_muy_alta)


class NoHayNivelNormalTest(SimpleTestCase):
    """`ALC-OUT-20`, `[S1]` del documento. **La ausencia es la regla.**

    Publicar «esta categoría está en su punto» es una valoración nutricional
    individualizada igual que la contraria. Por debajo del umbral no se genera
    nada, y esta prueba existe para que nadie añada un tercer nivel «normal»
    creyendo que mejora la pantalla.
    """

    def test_un_consumo_bajo_no_genera_ninguna_entrada(self):
        alertas = reglas.evaluar({"Frutas": 1, "Bebidas": 2, "Snacks": 4})

        self.assertEqual(alertas, [])

    def test_solo_existen_dos_niveles(self):
        niveles = {
            alerta.nivel
            for alerta in reglas.evaluar({"A": 5, "B": 8, "C": 13, "D": 2})
        }

        self.assertEqual(
            niveles, {NivelDeFrecuencia.ALTA, NivelDeFrecuencia.MUY_ALTA}
        )


class ElMismoUmbralParaTodasLasCategoriasTest(SimpleTestCase):
    """`[S3]` del documento, y es la decisión de fondo de `TT-158`.

    Un umbral más bajo para `Snacks` que para `Frutas` sería afirmar que una
    conviene menos que la otra — la valoración nutricional que `ALC-OUT-20`
    excluye. La regla cuenta días y no mira qué hay dentro de la categoría.
    """

    def test_frutas_y_snacks_avisan_con_los_mismos_dias(self):
        alertas = reglas.evaluar({"Frutas": 6, "Snacks": 6})

        self.assertEqual({alerta.nivel for alerta in alertas}, {NivelDeFrecuencia.ALTA})
        self.assertEqual({alerta.umbral for alerta in alertas}, {UMBRAL_FRECUENCIA_ALTA})

    def test_el_nombre_de_la_categoria_no_cambia_el_veredicto(self):
        """Contraprueba: lo único que decide es el número."""
        una = reglas.evaluar({"Postres fritos": 9})[0]
        otra = reglas.evaluar({"Verduras al vapor": 9})[0]

        self.assertEqual(una.nivel, otra.nivel)
        self.assertEqual(una.dias, otra.dias)


class ElOrdenEsParteDeLaReglaTest(SimpleTestCase):
    """`[S2.5]`. Determinístico no es solo que el umbral no cambie: es que la
    misma entrada dé la misma salida **en el mismo orden**, siempre."""

    def test_de_mas_dias_a_menos(self):
        alertas = reglas.evaluar({"Bebidas": 5, "Panadería": 9, "Almuerzo": 7})

        self.assertEqual(
            [alerta.categoria for alerta in alertas],
            ["Panadería", "Almuerzo", "Bebidas"],
        )

    def test_a_igual_numero_de_dias_manda_el_alfabeto(self):
        """Sin desempate, el orden lo decidiría la base y dos consultas
        idénticas darían dos pantallas distintas."""
        alertas = reglas.evaluar({"Snacks": 6, "Almuerzo": 6, "Frutas": 6})

        self.assertEqual(
            [alerta.categoria for alerta in alertas],
            ["Almuerzo", "Frutas", "Snacks"],
        )


class LaAlertaLlevaConQueSeComparoTest(SimpleTestCase):
    """`[S4]`, punto 3. El umbral viaja con la alerta para que el acudiente
    pueda contar los días en el historial y comprobarla.

    Una alerta sin su umbral es indistinguible de una opinión, y `OBJ-E3` pide
    lo contrario.
    """

    def test_la_alerta_dice_su_umbral_y_su_ventana(self):
        alerta = reglas.evaluar({"Panadería": 6})[0]

        self.assertEqual(alerta.dias, 6)
        self.assertEqual(alerta.umbral, UMBRAL_FRECUENCIA_ALTA)
        self.assertEqual(alerta.ventana, reglas.DIAS_DE_LA_VENTANA)

    def test_la_muy_alta_se_compara_contra_su_propio_umbral(self):
        alerta = reglas.evaluar({"Panadería": 10})[0]

        self.assertEqual(alerta.umbral, UMBRAL_FRECUENCIA_MUY_ALTA)


class EsDeterministicaTest(SimpleTestCase):
    """`OBJ-E3`, `ALC-IN-21`: reglas determinísticas, **nada de modelos**."""

    def test_la_misma_entrada_da_siempre_la_misma_salida(self):
        entrada = {"Panadería": 9, "Bebidas": 5, "Frutas": 3}

        self.assertEqual(reglas.evaluar(entrada), reglas.evaluar(entrada))

    def test_evaluar_no_usa_azar_ni_reloj(self):
        """Prueba de ausencia sobre el **bytecode**, no sobre el fuente.

        El docstring de `evaluar` habla de determinismo, así que buscar la
        palabra en el código fuente encontraría la explicación y la prueba
        pasaría sola. `co_names` lista lo que la función usa de verdad.
        """
        import inspect

        usados = set(inspect.unwrap(reglas.evaluar).__code__.co_names)

        self.assertNotIn("random", usados)
        self.assertNotIn("now", usados)
        self.assertNotIn("today", usados)
        # Contraprueba: sí encuentra lo que la función usa de verdad.
        self.assertIn("append", usados)
