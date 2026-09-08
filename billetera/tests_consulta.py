"""`TT-64`. El acudiente consulta el saldo de su estudiante (`HU-07`).

Los dos criterios:

1. **El acudiente ve el saldo de cada estudiante a su cargo.** De cada uno el
   suyo: la billetera es individual (`HU-06`), y en una cuenta con dos hijos la
   pantalla no puede enseñar el mismo número dos veces.
2. **El saldo mostrado corresponde exactamente al historial de movimientos.**
   `TST-3` lo prueba en el selector; aquí se comprueba **lo que llega al
   navegador**, que es donde el acudiente lo lee: si la plantilla formateara mal,
   redondeara o cogiera otra cifra, el selector seguiría en verde.

`[S11]` da «consultar saldo de un estudiante» al acudiente como consulta libre.
El cajero lo verá **solo al cobrar** (`HU-17`, `PR-09`), que es otra cosa.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from billetera.selectors import saldo_de
from billetera.services import recargar
from billetera.templatetags.dinero import dinero
from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante


def acudiente_con_hijos(sufijo="1", cuantos=1):
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente{sufijo}@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
    )
    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"4351234{sufijo}"
    )
    hijos = [
        Estudiante.objects.create(
            nombre=f"Hijo {sufijo}{i}",
            documento=f"100{sufijo}00{i}",
            acudiente=acudiente,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        for i in range(cuantos)
    ]
    return usuario, hijos


class ElAcudienteVeElSaldoTest(TestCase):
    def setUp(self):
        self.usuario, (self.hijo, self.otro_hijo) = acudiente_con_hijos("1", cuantos=2)
        self.client.force_login(self.usuario)

    def test_el_panel_muestra_el_saldo_del_estudiante_elegido(self):
        recargar(actor=self.usuario, estudiante=self.hijo, monto=Decimal("25000"))

        cuerpo = self.client.get(reverse("mis-estudiantes")).content.decode()

        self.assertIn("$25.000", cuerpo)

    def test_cada_hijo_tiene_el_suyo(self):
        """Primer criterio. Con una sola billetera compartida esto fallaría."""
        recargar(actor=self.usuario, estudiante=self.hijo, monto=Decimal("25000"))
        recargar(actor=self.usuario, estudiante=self.otro_hijo, monto=Decimal("7000"))

        del_hijo = self.client.get(
            reverse("estudiante-seleccionado", args=[self.hijo.id])
        ).content.decode()
        del_otro = self.client.get(
            reverse("estudiante-seleccionado", args=[self.otro_hijo.id])
        ).content.decode()

        self.assertIn("$25.000", del_hijo)
        self.assertNotIn("$7.000", del_hijo)
        self.assertIn("$7.000", del_otro)
        self.assertNotIn("$25.000", del_otro)

    def test_lo_que_se_ve_es_la_suma_del_historial(self):
        """Segundo criterio, comprobado contra el HTML servido.

        Tres recargas y una cifra: si la plantilla enseñara la última, o
        redondeara, el selector seguiría en verde y esto no.
        """
        for monto in ["10000", "5000.50", "2500.25"]:
            recargar(actor=self.usuario, estudiante=self.hijo, monto=Decimal(monto))

        cuerpo = self.client.get(reverse("mis-estudiantes")).content.decode()

        self.assertEqual(saldo_de(self.hijo), Decimal("17500.75"))
        self.assertIn(dinero(saldo_de(self.hijo)), cuerpo)
        self.assertIn("$17.500,75", cuerpo)

    def test_sin_movimientos_ensena_cero_y_lo_dice(self):
        cuerpo = self.client.get(reverse("mis-estudiantes")).content.decode()

        self.assertIn("$0", cuerpo)
        self.assertIn("Todavía no hay movimientos", cuerpo)

    def test_no_ve_el_saldo_de_un_estudiante_ajeno(self):
        """La cifra no se cuela ni por el fragmento: el selector no lo alcanza."""
        _, (ajeno,) = acudiente_con_hijos("2")
        recargar(
            actor=Usuario.objects.get(email="acudiente2@example.com"),
            estudiante=ajeno,
            monto=Decimal("99000"),
        )

        respuesta = self.client.get(reverse("estudiante-seleccionado", args=[ajeno.id]))

        self.assertEqual(respuesta.status_code, 404)


class LosUltimosMovimientosExplicanElSaldoTest(TestCase):
    """`TT-64`. La cifra sola habría que creerla; con el historial, no."""

    def setUp(self):
        self.usuario, (self.hijo,) = acudiente_con_hijos("3")
        self.client.force_login(self.usuario)

    def test_los_movimientos_salen_en_la_ficha(self):
        recargar(actor=self.usuario, estudiante=self.hijo, monto=Decimal("12000"))

        cuerpo = self.client.get(reverse("mis-estudiantes")).content.decode()

        self.assertIn("Últimos movimientos", cuerpo)
        self.assertIn("Recarga", cuerpo)
        self.assertIn("$12.000", cuerpo)

    def test_solo_los_ultimos_cinco(self):
        """El extracto completo empujaría el resto del panel fuera de un teléfono."""
        for i in range(1, 8):
            recargar(actor=self.usuario, estudiante=self.hijo, monto=Decimal(i * 1000))

        cuerpo = self.client.get(reverse("mis-estudiantes")).content.decode()

        # Las cinco más recientes son de 7.000 a 3.000; las dos primeras no salen.
        for visible in ["$7.000", "$6.000", "$5.000", "$4.000", "$3.000"]:
            self.assertIn(visible, cuerpo)
        for oculto in ["$2.000", "$1.000"]:
            self.assertNotIn(oculto, cuerpo)

    def test_el_fragmento_htmx_trae_lo_mismo_que_la_pagina(self):
        """La página y el fragmento pintan la misma plantilla (`DT-16`).

        El contexto lo arma una sola función precisamente para que no puedan
        divergir; esto lo comprueba desde fuera.
        """
        recargar(actor=self.usuario, estudiante=self.hijo, monto=Decimal("4500"))

        fragmento = self.client.get(
            reverse("estudiante-seleccionado", args=[self.hijo.id])
        ).content.decode()

        self.assertIn("$4.500", fragmento)
        self.assertIn("Últimos movimientos", fragmento)


class ElFormatoDelDineroTest(TestCase):
    """Un solo sitio decide cómo se escribe una cifra (`TT-64`)."""

    def test_formato_colombiano(self):
        self.assertEqual(dinero(Decimal("25000")), "$25.000")
        self.assertEqual(dinero(Decimal("1234567.89")), "$1.234.567,89")

    def test_los_centavos_solo_si_los_hay(self):
        """Arrastrar dos ceros en cada importe hace más difícil comparar cifras."""
        self.assertEqual(dinero(Decimal("3500.00")), "$3.500")
        self.assertEqual(dinero(Decimal("3500.50")), "$3.500,50")

    def test_el_signo_va_delante_del_simbolo(self):
        """«-$500» se lee de un vistazo; «$-500» hace dudar."""
        self.assertEqual(dinero(Decimal("-500")), "-$500")

    def test_sin_saldo_es_cero_y_no_un_hueco(self):
        self.assertEqual(dinero(None), "$0")

    def test_la_divisa_es_opcional_y_va_detras(self):
        """`DT-23`: la divisa solo acompaña a las cifras grandes.

        En una columna de tabla donde todo son pesos, repetir «COP» en cada fila
        es ruido y ensancha el importe sin decir nada nuevo. Por eso el filtro no
        la pone solo: hay que pedirla.
        """
        self.assertEqual(dinero(Decimal("25000"), "COP"), "$25.000 COP")
        self.assertEqual(dinero(Decimal("-500"), "COP"), "-$500 COP")
        self.assertEqual(dinero(None, "COP"), "$0 COP")
