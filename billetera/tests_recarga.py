"""`TT-59`, `TT-60`, `TT-61`. La recarga de la billetera (`HU-06`, `DT-4`, `INV-2`).

Los cuatro criterios de `HU-06`, uno por uno:

1. **La billetera es individual por estudiante.** Un acudiente con dos hijos
   tiene dos billeteras, y el saldo de uno no paga lo del otro.
2. **La recarga la ejecuta únicamente el acudiente**, y solo sobre un estudiante
   a su cargo. Ni la cafetería ni la institución recargan (`[S11]`).
3. **La recarga queda asentada en el historial de movimientos.**
4. **El flujo de pago es simulado**: no hay pasarela ni dinero real.

Y la decisión que sostiene el sprint entero: **no existe una columna `saldo`**.
El saldo es la suma de los movimientos (`DT-4`), así que `INV-2` es cierta por
construcción. La primera clase de este módulo lo comprueba mirando el modelo,
porque una columna `saldo` añadida más adelante no rompería ninguna otra prueba:
todo seguiría pasando mientras las dos cifras coincidieran, y el día que
dejaran de coincidir ya no habría forma de saber cuál miente.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from billetera.models import Billetera, MovimientoBilletera, TipoDeMovimiento
from billetera.selectors import saldo_de
from billetera.services import MONTO_MAXIMO, recargar
from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, EstadoDelEstudiante, Estudiante
from personas.services import EstudianteNoOperativo, dar_de_baja

CLAVE = "clave-de-prueba-2026"


def acudiente_con_estudiante(sufijo="1", estudiantes=1):
    """Un acudiente con su cuenta y `n` estudiantes a cargo."""
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente{sufijo}@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])

    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"4351234{sufijo}"
    )
    hijos = [
        Estudiante.objects.create(
            nombre=f"Estudiante {sufijo}{i}",
            documento=f"100{sufijo}00{i}",
            acudiente=acudiente,
            # El código lo genera el generador de `DT-9`, no una cadena a mano:
            # su forma la vigila una `CheckConstraint` (`INV-7`, `TT-32`).
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        for i in range(estudiantes)
    ]
    return usuario, acudiente, hijos


class LaBilleteraNoGuardaElSaldoTest(TestCase):
    """`DT-4`, `INV-2`. La decisión que este PR no puede perder."""

    def test_el_modelo_no_tiene_ninguna_columna_de_saldo(self):
        campos = {campo.name for campo in Billetera._meta.get_fields()}

        self.assertNotIn("saldo", campos)
        # Ni disfrazada con otro nombre: cualquiera de estos sería el mismo
        # error con otra etiqueta.
        for prohibido in ["balance", "total", "saldo_actual", "disponible"]:
            self.assertNotIn(prohibido, campos)

    def test_el_saldo_es_la_suma_de_los_movimientos(self):
        _, _, (estudiante,) = acudiente_con_estudiante()
        billetera = Billetera.objects.create(estudiante=estudiante)

        MovimientoBilletera.objects.create(
            billetera=billetera, tipo=TipoDeMovimiento.RECARGA, monto=Decimal("20000.00")
        )
        MovimientoBilletera.objects.create(
            billetera=billetera, tipo=TipoDeMovimiento.VENTA, monto=Decimal("-3500.00")
        )
        MovimientoBilletera.objects.create(
            billetera=billetera, tipo=TipoDeMovimiento.DEVOLUCION, monto=Decimal("500.00")
        )

        self.assertEqual(saldo_de(estudiante), Decimal("17000.00"))

    def test_sin_movimientos_el_saldo_es_cero(self):
        """Con billetera o sin ella: son el mismo hecho contado de dos maneras."""
        _, _, (estudiante,) = acudiente_con_estudiante()

        self.assertEqual(saldo_de(estudiante), Decimal("0.00"))

        Billetera.objects.create(estudiante=estudiante)
        self.assertEqual(saldo_de(estudiante), Decimal("0.00"))


class ElSignoLoImponeLaBaseTest(TestCase):
    """`DT-15`: la invariante que la base pueda imponer, la impone la base.

    Un `if` en el servicio se olvida en el siguiente camino de escritura —el
    admin, un comando, la venta de `TT-80`—; una `CheckConstraint`, no.
    """

    def setUp(self):
        _, _, (estudiante,) = acudiente_con_estudiante()
        self.billetera = Billetera.objects.create(estudiante=estudiante)

    def _no_deja(self, tipo, monto):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MovimientoBilletera.objects.create(
                    billetera=self.billetera, tipo=tipo, monto=Decimal(monto)
                )

    def test_una_recarga_no_puede_ser_negativa(self):
        """Sería quitar saldo dejando un movimiento que dice lo contrario."""
        self._no_deja(TipoDeMovimiento.RECARGA, "-1000.00")

    def test_una_venta_no_puede_ser_positiva(self):
        """Sería regalar saldo."""
        self._no_deja(TipoDeMovimiento.VENTA, "1000.00")

    def test_ningun_movimiento_puede_ser_de_cero(self):
        """Un movimiento que no mueve nada es ruido en el historial de `INV-2`."""
        self._no_deja(TipoDeMovimiento.RECARGA, "0")


class LaRecargaEsDelAcudienteTest(TestCase):
    """Segundo criterio de `HU-06`, y `[S11]`."""

    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiante("1")
        self.otro, _, (self.ajeno,) = acudiente_con_estudiante("2")

    def test_el_acudiente_recarga_a_su_estudiante(self):
        movimiento = recargar(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("15000")
        )

        self.assertEqual(movimiento.tipo, TipoDeMovimiento.RECARGA)
        self.assertEqual(movimiento.monto, Decimal("15000"))
        self.assertEqual(movimiento.billetera.estudiante, self.estudiante)
        # Tercer criterio: queda asentada en el historial.
        self.assertEqual(saldo_de(self.estudiante), Decimal("15000"))

    def test_no_recarga_al_estudiante_de_otro_acudiente(self):
        with self.assertRaises(PermissionDenied):
            recargar(actor=self.usuario, estudiante=self.ajeno, monto=Decimal("10000"))

        self.assertEqual(saldo_de(self.ajeno), Decimal("0.00"))

    def test_ningun_otro_rol_recarga(self):
        """`[S11]` da «recargar saldo» a `USR-2` y a nadie más."""
        for rol in [Rol.CAJERO, Rol.ADMINISTRADOR, Rol.INSTITUCION]:
            with self.subTest(rol=rol):
                actor = Usuario.objects.crear_usuario(
                    email=f"{rol}@example.com", rol=rol, nombre="Personal"
                )
                with self.assertRaises(PermissionDenied):
                    recargar(actor=actor, estudiante=self.estudiante, monto=Decimal("1000"))

    def test_una_cuenta_desactivada_no_recarga(self):
        """`HU-42`: una cuenta desactivada no opera."""
        self.usuario.is_active = False
        self.usuario.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            recargar(actor=self.usuario, estudiante=self.estudiante, monto=Decimal("1000"))

    def test_un_anonimo_no_recarga(self):
        with self.assertRaises(PermissionDenied):
            recargar(actor=None, estudiante=self.estudiante, monto=Decimal("1000"))


class LaBilleteraEsIndividualTest(TestCase):
    """Primer criterio de `HU-06`."""

    def test_dos_hijos_del_mismo_acudiente_tienen_billeteras_distintas(self):
        usuario, _, (uno, otro) = acudiente_con_estudiante("3", estudiantes=2)

        recargar(actor=usuario, estudiante=uno, monto=Decimal("30000"))

        self.assertEqual(saldo_de(uno), Decimal("30000"))
        self.assertEqual(saldo_de(otro), Decimal("0.00"))

    def test_la_billetera_nace_en_la_primera_recarga_y_no_se_duplica(self):
        usuario, _, (estudiante,) = acudiente_con_estudiante("4")

        self.assertFalse(Billetera.objects.filter(estudiante=estudiante).exists())

        recargar(actor=usuario, estudiante=estudiante, monto=Decimal("1000"))
        recargar(actor=usuario, estudiante=estudiante, monto=Decimal("2000"))

        self.assertEqual(Billetera.objects.filter(estudiante=estudiante).count(), 1)
        self.assertEqual(saldo_de(estudiante), Decimal("3000"))


class NoSeRecargaAQuienNoOperaTest(TestCase):
    """`INVD-2`: ni desactivado ni de baja se compra **ni se recarga**.

    `HU-52` lo dice del otro lado: el saldo del estudiante de baja queda
    congelado y consultable. Congelado significa que tampoco entra dinero.
    """

    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiante("5")
        self.institucion = Usuario.objects.crear_usuario(
            email="institucion@example.com", rol=Rol.INSTITUCION, nombre="Colegio"
        )

    def _no_deja_recargar(self, estado):
        # Se pasa por el servicio real de `personas` en vez de escribir el estado
        # a mano: la baja lleva fecha y una `CheckConstraint` que las liga
        # (`estudiante_fecha_de_baja_coherente`), así que forzarla desde aquí
        # sería inventar un estado que el sistema no produce.
        if estado == EstadoDelEstudiante.BAJA:
            dar_de_baja(actor=self.institucion, estudiante=self.estudiante)
        else:
            self.estudiante.estado = estado
            self.estudiante.save(update_fields=["estado"])
        self.estudiante.refresh_from_db()

        with self.assertRaises(EstudianteNoOperativo):
            recargar(actor=self.usuario, estudiante=self.estudiante, monto=Decimal("5000"))

        self.assertEqual(saldo_de(self.estudiante), Decimal("0.00"))

    def test_de_baja_no_se_recarga(self):
        self._no_deja_recargar(EstadoDelEstudiante.BAJA)

    def test_desactivado_no_se_recarga(self):
        self._no_deja_recargar(EstadoDelEstudiante.DESACTIVADO)


class ElMontoTieneQueTenerSentidoTest(TestCase):
    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiante("6")

    def _rechaza(self, monto):
        with self.assertRaises(ValidationError):
            recargar(actor=self.usuario, estudiante=self.estudiante, monto=Decimal(monto))
        # Y no deja nada a medias: la transacción es de la función entera.
        self.assertEqual(MovimientoBilletera.objects.count(), 0)

    def test_cero_no_es_una_recarga(self):
        self._rechaza("0")

    def test_un_monto_negativo_no_es_una_recarga(self):
        self._rechaza("-5000")

    def test_por_encima_del_maximo_no_pasa(self):
        self._rechaza(MONTO_MAXIMO + Decimal("0.01"))

    def test_no_admite_un_tercer_decimal(self):
        """Sin esto, la base redondea en silencio y el historial dice otra cifra."""
        self._rechaza("1000.005")


class LaPantallaDeRecargaTest(TestCase):
    """`TT-61`. La vista, que solo traduce lo que decide el servicio (`DT-15`)."""

    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiante("7")
        self.otro, _, (self.ajeno,) = acudiente_con_estudiante("8")
        self.url = reverse("recarga", args=[self.estudiante.id])
        self.client.force_login(self.usuario)

    def test_el_acudiente_ve_el_formulario(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "billetera/recarga.html")

    def test_recargar_asienta_el_movimiento_y_vuelve_al_panel(self):
        respuesta = self.client.post(self.url, {"monto": "25000"})

        self.assertRedirects(respuesta, reverse("mis-estudiantes"))
        self.assertEqual(saldo_de(self.estudiante), Decimal("25000"))

    def test_un_monto_invalido_no_asienta_nada(self):
        respuesta = self.client.post(self.url, {"monto": "-1"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(MovimientoBilletera.objects.count(), 0)

    def test_el_estudiante_ajeno_es_un_404(self):
        """Igual que uno que no existe: distinguirlos confirmaría que existe."""
        respuesta = self.client.get(reverse("recarga", args=[self.ajeno.id]))

        self.assertEqual(respuesta.status_code, 404)

    def test_otro_rol_no_alcanza_la_pantalla(self):
        cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        self.client.force_login(cajero)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 403)

    def test_la_pantalla_dice_que_el_pago_es_simulado(self):
        """Cuarto criterio de `HU-06` (`ALC-OUT-01`, `ALC-OUT-02`)."""
        cuerpo = self.client.get(self.url).content.decode()

        self.assertIn("simulado", cuerpo)
        # Y no pide ningún dato de pago.
        for campo in ["tarjeta de crédito", "cvv", "número de cuenta"]:
            self.assertNotIn(campo, cuerpo.lower())
