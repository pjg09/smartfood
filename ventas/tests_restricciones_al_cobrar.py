"""`TT-109`, `TT-110`. Las restricciones en el panel de cobro (`HU-17`, `HU-13`).

**Aquí se salda la deuda del Sprint 2.** `HU-17` quedó abierta porque su primer
criterio pide **tres** datos al identificar al estudiante —saldo, consumo del día
y restricciones vigentes— y el tercero no existía: no había qué mostrar. Con
`TT-94`, `TT-97` y `TT-100` construidos, existe.

Los dos criterios de `HU-17`:

1. **Al identificar al estudiante se muestran los tres datos.** `LosTresDatosTest`
   los exige juntos, en la misma respuesta: que estén en tres pantallas distintas
   no cumpliría la historia, cuya razón de ser es *saber antes de cobrar si la
   venta va a poder realizarse*.
2. **El cajero ve el saldo solo al cobrar.** Ya lo sostenía `informacion_de_cobro`
   desde `TT-74` y aquí no cambia.

Y el primer criterio de `HU-13`: **el cajero ve las restricciones y no dispone de
ninguna acción para desactivarlas ni omitirlas.** Lo segundo no se demuestra
buscando que no haya botón —eso sería mirar la pantalla, y `PR-05` ya lo probó
donde importa— pero sí se comprueba que el panel no ofrece ninguna salida.

**Una advertencia que estas pruebas fijan y que hay que retirar a su tiempo.** De
las tres restricciones, la caja hoy solo rechaza el producto bloqueado (`HU-60`).
El alérgeno es `HU-18` y el cupo `HU-20`. El panel lo dice, y estas pruebas lo
exigen: un cajero que crea que el sistema frena el maní puede vender el maní.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from billetera.models import TipoDeMovimiento
from catalogo.models import Alergeno, Categoria, Producto
from cuentas.models import Rol, Usuario
from restricciones.services import (
    bloquear_alergeno,
    bloquear_producto,
    fijar_limite_diario,
)
from ventas.tests_cobro import estudiante, movimiento


class PanelConRestricciones(TestCase):
    """Andamiaje: un estudiante con saldo, consumo del día y su acudiente."""

    def setUp(self):
        self.estudiante = estudiante()
        self.acudiente = self.estudiante.acudiente.usuario
        movimiento(self.estudiante, TipoDeMovimiento.RECARGA, "50000")
        movimiento(self.estudiante, TipoDeMovimiento.VENTA, "-3500")

        self.cajero = Usuario.objects.crear_usuario(
            email="cajero-restr@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        self.client.force_login(self.cajero)
        self.url = reverse("identificacion-en-el-punto-de-venta")

        categoria, _ = Categoria.objects.get_or_create(nombre="Prueba")
        self.gaseosa, _ = Producto.objects.get_or_create(
            nombre="Gaseosa",
            defaults={"precio": Decimal("2500"), "categoria": categoria},
        )
        self.mani, _ = Alergeno.objects.get_or_create(nombre="Maní")

    def _panel(self):
        return self.client.get(
            self.url, {"codigo": self.estudiante.codigo_tarjeta}
        ).content.decode()


class LosTresDatosTest(PanelConRestricciones):
    """Primer criterio de `HU-17`, que es el que estaba a medias."""

    def test_los_tres_datos_salen_juntos_al_identificar(self):
        fijar_limite_diario(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("8000")
        )
        bloquear_alergeno(
            actor=self.acudiente, estudiante=self.estudiante, alergeno=self.mani
        )

        cuerpo = self._panel()

        self.assertIn("Saldo", cuerpo)
        self.assertIn("Consumo de hoy", cuerpo)
        self.assertIn("data-restricciones-vigentes", cuerpo)

    def test_sin_restricciones_el_bloque_lo_afirma_en_vez_de_callar(self):
        """Y **antes no podía**: sin tablas, «no tiene» habría sido «no sé»."""
        cuerpo = self._panel()

        self.assertIn("data-restricciones-vigentes", cuerpo)
        self.assertIn("Sin cupo, productos ni alérgenos", cuerpo)

    def test_por_documento_sale_lo_mismo(self):
        """`HU-16`: el mismo resultado, no uno parecido."""
        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.gaseosa
        )

        por_documento = self.client.get(
            self.url, {"documento": self.estudiante.documento}
        ).content.decode()

        self.assertEqual(self._panel(), por_documento)


class ElPanelNombraCadaRestriccionTest(PanelConRestricciones):
    """Un recuento no sirve en una caja: el cajero necesita saber **cuál**."""

    def test_enseña_el_alergeno_por_su_nombre(self):
        bloquear_alergeno(
            actor=self.acudiente, estudiante=self.estudiante, alergeno=self.mani
        )

        cuerpo = self._panel()

        self.assertIn("data-alergenos-bloqueados", cuerpo)
        self.assertIn("Maní", cuerpo)

    def test_enseña_el_producto_por_su_nombre(self):
        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.gaseosa
        )

        cuerpo = self._panel()

        self.assertIn("data-productos-bloqueados", cuerpo)
        self.assertIn("Gaseosa", cuerpo)

    def test_enseña_el_cupo_y_cuanto_queda_hoy(self):
        """El cajero necesita la cifra que decide, no dos que restar de cabeza."""
        fijar_limite_diario(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("8000")
        )

        cuerpo = self._panel()

        self.assertIn("data-limite-diario", cuerpo)
        # Consumo del día: $3.500. Cupo $8.000 → quedan $4.500.
        self.assertIn("$4.500", cuerpo)

    def test_el_cupo_agotado_se_dice_agotado(self):
        fijar_limite_diario(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("3000")
        )

        self.assertIn("agotado", self._panel())

    def test_las_tres_caben_a_la_vez(self):
        fijar_limite_diario(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("8000")
        )
        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.gaseosa
        )
        bloquear_alergeno(
            actor=self.acudiente, estudiante=self.estudiante, alergeno=self.mani
        )

        cuerpo = self._panel()

        for marca in (
            "data-alergenos-bloqueados",
            "data-productos-bloqueados",
            "data-limite-diario",
        ):
            with self.subTest(marca=marca):
                self.assertIn(marca, cuerpo)


class ElCajeroNoPuedeOmitirlasTest(PanelConRestricciones):
    """Primer criterio de `HU-13`: las ve y no tiene con qué saltárselas.

    Lo que de verdad lo garantiza es que no exista el permiso ni el servicio que
    lo admita, y eso lo probó `PR-05` llamando al servicio con cada rol. Aquí se
    comprueba la otra mitad: que el panel no ofrezca la salida.
    """

    def setUp(self):
        super().setUp()
        bloquear_alergeno(
            actor=self.acudiente, estudiante=self.estudiante, alergeno=self.mani
        )

    def test_el_panel_no_ofrece_ninguna_accion_sobre_las_restricciones(self):
        cuerpo = self._panel().lower()

        for tentacion in ("desbloquear", "omitir", "ignorar", "de todos modos",
                          "quitar restricci", "desactivar restricci"):
            with self.subTest(tentacion=tentacion):
                self.assertNotIn(tentacion, cuerpo)

    def test_el_panel_no_enlaza_a_la_pantalla_del_acudiente(self):
        """Configurarlas es de `INT-1` y del acudiente (`[S11]`, `INV-4`).

        Un enlace desde la caja no daría permiso —el servicio lo rechazaría—
        pero sí sugeriría que hay un camino, y en una caja eso es una pregunta
        que el cajero acaba haciéndole a la familia.
        """
        cuerpo = self._panel()

        self.assertNotIn("/restricciones/", cuerpo)


class ElPanelNoFingeQueLaCajaLasAplicaTodasTest(PanelConRestricciones):
    """La advertencia temporal, y por qué merece una prueba.

    De las tres, la caja hoy solo rechaza el producto bloqueado (`HU-60`). Si el
    panel enseñara el alérgeno sin decirlo, un cajero podría vender el maní
    confiando en que el sistema lo habría frenado.

    **Estas dos pruebas se retiran cuando entren `HU-18` y `HU-20`**, junto con
    las marcas que exigen. Que estén aquí es lo que hará que alguien se acuerde.
    """

    def test_el_alergeno_avisa_de_que_la_caja_no_lo_rechaza_todavia(self):
        bloquear_alergeno(
            actor=self.acudiente, estudiante=self.estudiante, alergeno=self.mani
        )

        cuerpo = self._panel()

        self.assertIn("HU-18", cuerpo)
        self.assertIn("no se lo vendas", cuerpo)

    def test_el_cupo_avisa_de_que_la_caja_no_lo_aplica_todavia(self):
        fijar_limite_diario(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("8000")
        )

        self.assertIn("HU-20", self._panel())

    def test_el_producto_bloqueado_no_lleva_esa_advertencia(self):
        """Porque ése **sí** lo rechaza la caja desde `HU-60`.

        Marcar los tres igual sería tan engañoso como no marcar ninguno.
        """
        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.gaseosa
        )

        cuerpo = self._panel()

        self.assertIn("data-productos-bloqueados", cuerpo)
        self.assertNotIn("HU-18", cuerpo)
        self.assertNotIn("HU-20", cuerpo)
