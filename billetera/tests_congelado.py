"""`TT-65`, `TT-66`. El saldo del estudiante dado de baja (`HU-52`, `INVD-2`).

Cierra lo que el Sprint 1 dejó a medias: `HU-51` construyó la baja lógica, pero
sin billetera no había saldo que congelar.

Los tres criterios:

1. **El saldo remanente queda congelado y sigue siendo consultable.** Las dos
   cosas a la vez, y es lo que hace difícil la historia: desaparecer del panel
   sería fácil, y sería perder la constancia de que ese dinero existió.
2. **No se puede comprar ni recargar sobre él.**
3. **La devolución del dinero queda fuera del sistema** (`ALC-OUT-01`,
   `ALC-OUT-02`). Un prototipo que no mueve dinero real no puede devolverlo, y
   callarlo dejaría a la familia esperando un reintegro que no va a llegar.

Lo que estas pruebas vigilan de verdad es el punto 2 **antes de que exista la
venta**: `asentar()` es el único sitio por donde se escribe en el libro, así que
el servicio de venta de `TT-80` no puede saltarse la comprobación por olvido.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from billetera.models import MovimientoBilletera, TipoDeMovimiento
from billetera.selectors import saldo_de
from billetera.services import asentar, recargar
from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, EstadoDelEstudiante, Estudiante
from personas.services import EstudianteNoOperativo, dar_de_baja


def familia(sufijo="1"):
    """Un acudiente, su estudiante con saldo, y la institución que lo da de baja."""
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente{sufijo}@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
    )
    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"4351234{sufijo}"
    )
    estudiante = Estudiante.objects.create(
        nombre="Tomás Restrepo Ruiz",
        documento=f"100{sufijo}0001",
        acudiente=acudiente,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )
    institucion = Usuario.objects.crear_usuario(
        email=f"institucion{sufijo}@example.com", rol=Rol.INSTITUCION, nombre="Colegio"
    )
    return usuario, estudiante, institucion


class ElSaldoQuedaCongeladoYConsultableTest(TestCase):
    """Primer criterio, que son dos cosas y hay que comprobar las dos."""

    def setUp(self):
        self.usuario, self.estudiante, self.institucion = familia("1")
        recargar(actor=self.usuario, estudiante=self.estudiante, monto=Decimal("18500.75"))
        dar_de_baja(actor=self.institucion, estudiante=self.estudiante)
        self.estudiante.refresh_from_db()

    def test_la_baja_no_toca_el_saldo(self):
        """Congelado es congelado: ni se pone a cero ni se descuenta nada."""
        self.assertEqual(saldo_de(self.estudiante), Decimal("18500.75"))

    def test_la_baja_no_borra_ningun_movimiento(self):
        """`DEC-7`: baja lógica, nunca borrado. Sin el historial no hay saldo."""
        self.assertEqual(
            MovimientoBilletera.objects.filter(billetera__estudiante=self.estudiante).count(),
            1,
        )

    def test_el_acudiente_lo_sigue_viendo_en_su_panel(self):
        """La constancia de que ese dinero existió, que es lo que pide la historia."""
        self.client.force_login(self.usuario)

        cuerpo = self.client.get(reverse("mis-estudiantes")).content.decode()

        self.assertIn("$ 18.500,75", cuerpo)
        self.assertIn("De baja", cuerpo)

    def test_el_panel_dice_que_esta_congelado(self):
        self.client.force_login(self.usuario)

        cuerpo = self.client.get(reverse("mis-estudiantes")).content.decode()

        self.assertIn("congelado", cuerpo.lower())

    def test_el_panel_dice_que_la_devolucion_queda_fuera(self):
        """Tercer criterio. Callarlo deja esperando un reintegro que no llega."""
        self.client.force_login(self.usuario)

        cuerpo = self.client.get(reverse("mis-estudiantes")).content.decode()

        self.assertIn("La devolución del dinero no se hace desde aquí", cuerpo)

    def test_el_panel_no_ofrece_recargar(self):
        """No es lo que lo impide —el servicio rechaza igual—, pero ofrecer algo
        que va a fallar es una promesa que la pantalla no puede cumplir."""
        self.client.force_login(self.usuario)

        cuerpo = self.client.get(reverse("mis-estudiantes")).content.decode()

        self.assertNotIn(reverse("recarga", args=[self.estudiante.id]), cuerpo)


class SobreElSaldoCongeladoNoSeOperaTest(TestCase):
    """Segundo criterio. **Y por el único sitio que escribe en el libro.**"""

    def setUp(self):
        self.usuario, self.estudiante, self.institucion = familia("2")
        recargar(actor=self.usuario, estudiante=self.estudiante, monto=Decimal("10000"))
        dar_de_baja(actor=self.institucion, estudiante=self.estudiante)
        self.estudiante.refresh_from_db()

    def test_no_se_recarga(self):
        with self.assertRaises(EstudianteNoOperativo):
            recargar(actor=self.usuario, estudiante=self.estudiante, monto=Decimal("5000"))

        self.assertEqual(saldo_de(self.estudiante), Decimal("10000"))

    def test_no_se_compra(self):
        """**La venta no existe todavía** —es `TT-80`, dos semanas después—, así
        que se comprueba en `asentar()`, que es por donde tendrá que pasar.

        Sin esto, `HU-52` quedaría medio cumplida hasta el Sprint 2 tardío y
        nadie lo notaría: no hay pantalla desde la que probarlo.
        """
        with self.assertRaises(EstudianteNoOperativo):
            asentar(
                estudiante=self.estudiante,
                tipo=TipoDeMovimiento.VENTA,
                monto=Decimal("-2500"),
            )

        self.assertEqual(saldo_de(self.estudiante), Decimal("10000"))

    def test_una_devolucion_si_se_asienta(self):
        """Devolver no es operar: es corregir un movimiento anterior.

        Un estudiante que se retiró con una venta mal cobrada tiene derecho a que
        se le corrija, y bloquearlo dejaría su historial diciendo algo que no
        pasó — justo lo que `INV-2` existe para evitar. `HU-52` prohíbe comprar y
        recargar; no, corregir.
        """
        asentar(
            estudiante=self.estudiante,
            tipo=TipoDeMovimiento.DEVOLUCION,
            monto=Decimal("2500"),
        )

        self.assertEqual(saldo_de(self.estudiante), Decimal("12500"))

    def test_la_pantalla_de_recarga_lo_rechaza(self):
        """De extremo a extremo: aunque se escriba la URL a mano."""
        self.client.force_login(self.usuario)

        respuesta = self.client.post(
            reverse("recarga", args=[self.estudiante.id]), {"monto": "5000"}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(saldo_de(self.estudiante), Decimal("10000"))
        self.assertIn("de baja", respuesta.content.decode().lower())


class ElDesactivadoTampocoOperaTest(TestCase):
    """`INVD-2` junta los dos estados para esto, aunque son distintos (`DEC-7`).

    La diferencia está en otra parte: la desactivación es reversible y la pide el
    acudiente (`HU-47`); la baja no vuelve. Para operar, ninguno de los dos.
    """

    def test_ni_recarga_ni_compra(self):
        usuario, estudiante, _ = familia("3")
        recargar(actor=usuario, estudiante=estudiante, monto=Decimal("4000"))
        estudiante.estado = EstadoDelEstudiante.DESACTIVADO
        estudiante.save(update_fields=["estado"])

        with self.assertRaises(EstudianteNoOperativo):
            recargar(actor=usuario, estudiante=estudiante, monto=Decimal("1000"))
        with self.assertRaises(EstudianteNoOperativo):
            asentar(
                estudiante=estudiante, tipo=TipoDeMovimiento.VENTA, monto=Decimal("-1000")
            )

        self.assertEqual(saldo_de(estudiante), Decimal("4000"))
