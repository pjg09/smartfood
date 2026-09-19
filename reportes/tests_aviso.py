"""`TT-161`. El aviso de carácter orientativo (`HU-34`, **`INV-9`**).

`INV-9` dice que las recomendaciones **son** orientativas, no que se acompañen
de un aviso cuando alguien se acuerde. La diferencia se nota en cómo se
comprueba: no basta con mirar la pantalla del historial y encontrar el párrafo,
porque eso seguiría siendo cierto el día que alguien enseñe las alertas en otro
sitio y se deje el descargo atrás.

Por eso las dos primeras clases **renderizan el fragmento por su cuenta**: si
alguien separa las alertas del aviso en dos plantillas, pintar el fragmento de
las alertas deja de traer el descargo y estas pruebas fallan. Es la única forma
de fijar «no hay manera de publicar una recomendación sin él».

Es el único sitio del proyecto donde una prueba afirma sobre **la redacción**,
y es deliberado: aquí el texto es el requisito. El segundo criterio de `HU-34`
pide que declare que no constituye valoración médica ni nutricional
individualizada, y `ALC-OUT-20` es la razón de que eso sea una frase y no una
idea general.
"""

from decimal import Decimal

from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from reportes.referencia import REFERENCIA_DIARIA, Comparacion
from reportes.selectors import AporteNutricional, ResumenDeGasto

from reportes.reglas import (
    DIAS_DE_LA_VENTANA,
    UMBRAL_FRECUENCIA_ALTA,
    AlertaDeFrecuencia,
    NivelDeFrecuencia,
)
from reportes.tests_frecuencia import HOY, BaseDeFrecuencia

FRAGMENTO = "reportes/partials/recomendaciones.html"

# La frase del segundo criterio de `HU-34`, tal como `ALC-OUT-20` la nombra.
DESCARGO = "No constituye una valoración médica ni nutricional individualizada"


def pintar(alertas, aporte=None, gasto=None):
    """El fragmento, con lo que la vista le pasa y nada más.

    `aporte` por defecto es el caso sin datos —un estudiante sin consumo en el
    periodo—, para que cada prueba solo tenga que montar lo que mira.
    """
    return render_to_string(
        FRAGMENTO,
        {
            "alertas": alertas,
            "aporte": aporte
            or AporteNutricional(
                comparaciones=[], dias_con_consumo=0, renglones_sin_declarar=0
            ),
            "gasto": gasto
            or ResumenDeGasto(
                recargado=Decimal("0.00"),
                gastado=Decimal("0.00"),
                devuelto=Decimal("0.00"),
                saldo=Decimal("0.00"),
            ),
            "estudiante": {"nombre": "Ana Sofía"},
            "ventana_de_frecuencia": DIAS_DE_LA_VENTANA,
            "umbral_de_frecuencia": UMBRAL_FRECUENCIA_ALTA,
        },
    )


def aporte_con(porcentajes):
    """Un `AporteNutricional` montado a mano, sin tocar la base."""
    comparaciones = [
        Comparacion(
            referencia=valor,
            total=Decimal("100"),
            promedio_diario=Decimal("50"),
            porcentaje=porcentajes.get(valor.campo),
        )
        for valor in REFERENCIA_DIARIA
        if valor.campo in porcentajes
    ]
    return AporteNutricional(
        comparaciones=comparaciones, dias_con_consumo=2, renglones_sin_declarar=0
    )


class NoSePuedePintarUnaAlertaSinElAvisoTest(SimpleTestCase):
    """**La prueba que sostiene `INV-9`.**

    Si falla, alguien separó el descargo de las recomendaciones y hay un camino
    por el que se puede publicar una sin el otro.
    """

    def test_con_alertas_el_aviso_va_dentro_del_mismo_fragmento(self):
        html = pintar(
            [
                AlertaDeFrecuencia(
                    categoria="Panadería",
                    dias=9,
                    umbral=UMBRAL_FRECUENCIA_ALTA,
                    nivel=NivelDeFrecuencia.MUY_ALTA,
                )
            ]
        )

        self.assertIn("data-alerta", html)
        self.assertIn("data-aviso-orientativo", html)

    def test_sin_alertas_el_aviso_sigue_estando(self):
        """«Ninguna categoría llega al umbral» **no es** «todo va bien».

        Sin el descargo, la frase se leería como una valoración igual que la
        contraria (`[S5]` de `docs/reglas-de-frecuencia-de-consumo.md`).
        """
        html = pintar([])

        self.assertIn("data-sin-alertas", html)
        self.assertIn("data-aviso-orientativo", html)


class ElAporteTampocoSePublicaSinElAvisoTest(SimpleTestCase):
    """`TT-164` entra en el mismo fragmento que las alertas, y por lo mismo.

    La comparación con la referencia sanitaria es una recomendación informativa
    de `ALC-IN-21` igual que las alertas, así que `INV-9` la alcanza igual. Si
    alguien la saca a una plantilla propia, esto falla.
    """

    def test_con_agregados_y_sin_alertas_el_aviso_sigue_estando(self):
        html = pintar([], aporte=aporte_con({"energia_kcal": 19}))

        self.assertIn("data-aporte-nutricional", html)
        self.assertIn("data-aviso-orientativo", html)

    def test_sin_agregados_el_bloque_no_se_pinta(self):
        """Sin consumo en el periodo no hay nada que promediar, y un cero sería
        inventado."""
        html = pintar([])

        self.assertNotIn("data-aporte-nutricional", html)
        self.assertIn("data-aviso-orientativo", html)


class ElGastoTampocoSePublicaSinElAvisoTest(SimpleTestCase):
    """`TT-166` entra en el mismo fragmento por la misma razón que el aporte.

    `ALC-IN-21` lista **las tres** —alertas de frecuencia, agregados frente a la
    referencia y resumen de gasto— como recomendaciones informativas, y la frase
    que las declara orientativas las cubre a las tres. Que esta no hable de
    nutrición no la saca de la lista.
    """

    def test_con_gasto_y_sin_nada_mas_el_aviso_sigue_estando(self):
        html = pintar(
            [],
            gasto=ResumenDeGasto(
                recargado=Decimal("20000"),
                gastado=Decimal("5000"),
                devuelto=Decimal("0"),
                saldo=Decimal("15000"),
            ),
        )

        self.assertIn("data-resumen-de-gasto", html)
        self.assertIn("data-aviso-orientativo", html)

    def test_sin_movimientos_el_bloque_no_se_pinta(self):
        html = pintar([])

        self.assertNotIn("data-resumen-de-gasto", html)
        self.assertIn("data-aviso-orientativo", html)


class ElAporteDiceDeDondeSaleTest(SimpleTestCase):
    """`HU-32`, primer criterio: la referencia es la de la autoridad sanitaria
    colombiana, **y la pantalla dice cuál**.

    Sin la cita, la cifra es un número que hay que creerse. Con ella, cualquiera
    puede ir a la norma y comprobarla — que es lo que separa una comparación de
    una opinión.
    """

    def test_la_pantalla_nombra_la_norma(self):
        html = pintar([], aporte=aporte_con({"energia_kcal": 19}))

        self.assertIn("Resolución 810 de 2021", html)
        self.assertIn("Ministerio de Salud", html)

    def test_declara_que_la_referencia_no_es_lo_que_el_estudiante_necesita(self):
        """`[S3]` de `docs/valores-de-referencia-nutricional.md`.

        Es lo que mantiene la comparación fuera de `ALC-OUT-20`: el VRN del
        etiquetado es el mismo para toda la población mayor de cuatro años y no
        afirma lo que un niño necesita. Callarlo convertiría una regla de tres
        pública en algo que parece un requerimiento personal.
        """
        html = pintar([], aporte=aporte_con({"energia_kcal": 19}))

        self.assertIn("No es lo que", html)
        self.assertIn("necesita", html)


class ElAvisoDiceLoQueTieneQueDecirTest(SimpleTestCase):
    """Segundo criterio de `HU-34`, literal."""

    def test_declara_que_no_es_valoracion_medica_ni_nutricional(self):
        self.assertIn(DESCARGO, pintar([]))

    def test_lo_declara_tambien_cuando_hay_recomendaciones(self):
        alerta = AlertaDeFrecuencia(
            categoria="Bebidas",
            dias=6,
            umbral=UMBRAL_FRECUENCIA_ALTA,
            nivel=NivelDeFrecuencia.ALTA,
        )

        self.assertIn(DESCARGO, pintar([alerta]))


class LaAlertaDescribeYNoAconsejaTest(SimpleTestCase):
    """`ALC-OUT-20`, `[S1]`. La regla produce un hecho, no un consejo.

    No se puede comprobar «no aconseja» sobre cualquier redacción futura, así
    que lo que se fija es lo que la alerta **sí** enseña: la categoría, los días
    y el umbral con el que se comparó, que es lo que la hace comprobable contra
    el historial.
    """

    def test_la_alerta_enseña_los_dias_la_ventana_y_el_umbral(self):
        html = pintar(
            [
                AlertaDeFrecuencia(
                    categoria="Panadería",
                    dias=6,
                    umbral=UMBRAL_FRECUENCIA_ALTA,
                    nivel=NivelDeFrecuencia.ALTA,
                )
            ]
        )

        self.assertIn("Panadería", html)
        self.assertIn("6", html)
        self.assertIn(str(DIAS_DE_LA_VENTANA), html)
        self.assertIn(f"a partir de {UMBRAL_FRECUENCIA_ALTA} días", html)


class LaPantallaPublicaLasAlertasConSuAvisoTest(BaseDeFrecuencia):
    """`TT-160`. Las dos historias juntas, ya en la pantalla del acudiente.

    Va contra la página entera y afirma sobre `data-*` propios, no sobre el
    armazón ni sobre la redacción de los rótulos.
    """

    def pantalla(self):
        self.client.force_login(self.acudiente)
        return self.client.get(
            reverse("historial-de-consumo", args=[self.estudiante.id])
        )

    def test_con_una_frecuencia_alta_la_pantalla_la_publica_con_el_descargo(self):
        for dia in range(UMBRAL_FRECUENCIA_ALTA):
            self.comprar(dias_atras=dia)

        respuesta = self.pantalla()

        self.assertContains(respuesta, "data-alerta")
        self.assertContains(respuesta, "data-aviso-orientativo")

    def test_con_compras_pero_sin_patron_tambien_lleva_el_descargo(self):
        self.comprar(dias_atras=0)

        respuesta = self.pantalla()

        self.assertContains(respuesta, "data-sin-alertas")
        self.assertContains(respuesta, "data-aviso-orientativo")

    def test_sin_compras_no_se_publica_ninguna_recomendacion(self):
        """Y entonces tampoco hay descargo, porque no hay nada que descargar.

        Lo que la pantalla dice es que todavía no ha comprado nada, que no es
        una valoración de nada.
        """
        respuesta = self.pantalla()

        self.assertContains(respuesta, "data-sin-compras")
        self.assertNotContains(respuesta, "data-alertas-de-frecuencia")
        self.assertNotContains(respuesta, "data-aviso-orientativo")


class LasAlertasSonDeSuAcudienteTest(BaseDeFrecuencia):
    """La pantalla hereda la puerta del historial: `[S11]` y `DT-11`."""

    def test_otro_rol_no_ve_la_pantalla_ni_sus_alertas(self):
        from cuentas.models import Rol, Usuario

        for dia in range(UMBRAL_FRECUENCIA_ALTA):
            self.comprar(dias_atras=dia)

        self.client.force_login(
            Usuario.objects.crear_usuario(
                email="curioso-aviso@example.com",
                rol=Rol.ADMINISTRADOR,
                nombre="Administración",
            )
        )
        respuesta = self.client.get(
            reverse("historial-de-consumo", args=[self.estudiante.id])
        )

        self.assertEqual(respuesta.status_code, 403)
