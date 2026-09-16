"""`TT-134` … `TT-136`. Retiro del límite diario (`HU-61`, `DEC-13`).

`HU-09` dejó al acudiente **fijar** un cupo y cambiarlo. Lo que no podía era
quitarlo: `[S11]` ata «retirar» a la fila de las restricciones alimentarias, y la
del límite dice únicamente «fijar», así que `HU-12` no lo alcanzaba. `DEC-13`
amplía esa fila y esta historia lo construye.

Los tres criterios de `HU-61`:

1. **Solo el acudiente puede retirarlo**, como todo lo demás del control
   parental (`INV-4`).
2. **Retirarlo deja al estudiante sin cupo**, que es distinto de un cupo de cero.
   `RetiradoNoEsCeroTest` es la clase que vigila esa distinción, y no es
   cosmética: un cero significa «no puede gastar nada» y es lo contrario de lo
   que se pide. La `CheckConstraint` de `LimiteDiario` lo impide de todas formas,
   pero el selector tiene que seguir distinguiendo los dos casos.
3. **El retiro queda asentado**: quién y cuándo, y **de cuánto era**.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from restricciones.models import (
    AsientoDeRestriccion,
    LimiteDiario,
    RestriccionAsentada,
    TipoDeAsiento,
)
from restricciones.selectors import historial_de_restricciones, limite_diario_de
from restricciones.services import fijar_limite_diario, retirar_limite_diario

CLAVE = "clave-de-prueba-2026"


def escenario(sufijo="1", estudiantes=1):
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente-lim{sufijo}@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
    ficha = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"8351234{sufijo}"
    )
    hijos = [
        Estudiante.objects.create(
            nombre=f"Estudiante L{sufijo}{i}",
            documento=f"800{sufijo}00{i}",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        for i in range(estudiantes)
    ]
    return usuario, hijos


def cuenta(rol, sufijo):
    u = Usuario.objects.crear_usuario(
        email=f"{rol}-lim{sufijo}@example.com", rol=rol, nombre=f"Cuenta {rol}"
    )
    u.set_password(CLAVE)
    u.save(update_fields=["password"])
    return u


class RetiradoNoEsCeroTest(TestCase):
    """Segundo criterio, y la distinción que esta historia existe para marcar."""

    def setUp(self):
        self.usuario, (self.estudiante,) = escenario()
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("8000")
        )

    def test_retirar_borra_la_fila_y_el_selector_devuelve_none(self):
        retirado = retirar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante
        )

        self.assertTrue(retirado)
        self.assertIsNone(limite_diario_de(self.estudiante))
        self.assertFalse(LimiteDiario.objects.filter(estudiante=self.estudiante).exists())

    def test_no_deja_un_cupo_de_cero(self):
        """Un cero significa «no puede gastar nada», que es lo contrario."""
        retirar_limite_diario(actor=self.usuario, estudiante=self.estudiante)

        self.assertEqual(
            LimiteDiario.objects.filter(estudiante=self.estudiante).count(), 0
        )
        # Y la base sigue sin admitir el cero, por si alguien lo intentara.
        with self.assertRaises(Exception):
            LimiteDiario.objects.create(
                estudiante=self.estudiante, monto=Decimal("0")
            )

    def test_retirar_lo_que_no_habia_no_es_un_error(self):
        retirar_limite_diario(actor=self.usuario, estudiante=self.estudiante)

        self.assertFalse(
            retirar_limite_diario(actor=self.usuario, estudiante=self.estudiante)
        )

    def test_despues_de_retirarlo_se_puede_volver_a_fijar(self):
        retirar_limite_diario(actor=self.usuario, estudiante=self.estudiante)
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("5000")
        )

        self.assertEqual(limite_diario_de(self.estudiante).monto, Decimal("5000.00"))

    def test_retirar_el_de_un_hijo_no_toca_el_del_otro(self):
        """Dos hijos del **mismo** acudiente: el cupo es de cada uno."""
        usuario, (uno, otro) = escenario(sufijo="h", estudiantes=2)
        for estudiante, monto in ((uno, "8000"), (otro, "3000")):
            fijar_limite_diario(
                actor=usuario, estudiante=estudiante, monto=Decimal(monto)
            )

        retirar_limite_diario(actor=usuario, estudiante=uno)

        self.assertIsNone(limite_diario_de(uno))
        self.assertEqual(limite_diario_de(otro).monto, Decimal("3000.00"))


class SoloElAcudienteRetiraTest(TestCase):
    """Primer criterio: `INV-4` también sobre el cupo."""

    def setUp(self):
        self.usuario, (self.estudiante,) = escenario()
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("8000")
        )

    def _rechaza(self, actor):
        with self.assertRaises(PermissionDenied):
            retirar_limite_diario(actor=actor, estudiante=self.estudiante)
        self.assertIsNotNone(limite_diario_de(self.estudiante))

    def test_el_cajero_no_retira(self):
        self._rechaza(cuenta(Rol.CAJERO, "a"))

    def test_la_administracion_no_retira(self):
        self._rechaza(cuenta(Rol.ADMINISTRADOR, "a"))

    def test_la_institucion_no_retira(self):
        self._rechaza(cuenta(Rol.INSTITUCION, "a"))

    def test_otro_acudiente_no_retira_el_de_un_hijo_ajeno(self):
        ajeno, _ = escenario(sufijo="3")
        self._rechaza(ajeno)

    def test_sin_cuenta_identificada_no_se_retira(self):
        self._rechaza(None)

    def test_un_intento_rechazado_no_deja_asiento(self):
        with self.assertRaises(PermissionDenied):
            retirar_limite_diario(
                actor=cuenta(Rol.CAJERO, "b"), estudiante=self.estudiante
            )

        self.assertFalse(
            AsientoDeRestriccion.objects.filter(tipo=TipoDeAsiento.RETIRO).exists()
        )


class ElRetiroDelLimiteQuedaAsentadoTest(TestCase):
    """Tercer criterio: quién, cuándo y **de cuánto era**."""

    def setUp(self):
        self.usuario, (self.estudiante,) = escenario()

    def test_fijar_el_limite_deja_asiento_con_la_cifra(self):
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("8000")
        )

        asiento = AsientoDeRestriccion.objects.get()
        self.assertEqual(asiento.tipo, TipoDeAsiento.BLOQUEO)
        self.assertEqual(asiento.sobre, RestriccionAsentada.LIMITE_DIARIO)
        self.assertEqual(asiento.nombre, "$8.000")
        self.assertIsNone(asiento.producto)
        self.assertIsNone(asiento.alergeno)

    def test_retirarlo_asienta_de_cuanto_era(self):
        """«Se retiró el límite» sin decir de cuánto no explica lo que se hizo."""
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("8000")
        )
        retirar_limite_diario(actor=self.usuario, estudiante=self.estudiante)

        retiro = AsientoDeRestriccion.objects.get(tipo=TipoDeAsiento.RETIRO)
        self.assertEqual(retiro.actor, self.usuario)
        self.assertEqual(retiro.nombre, "$8.000")
        self.assertEqual(retiro.sobre, RestriccionAsentada.LIMITE_DIARIO)

    def test_cambiar_el_limite_asienta_la_cifra_nueva(self):
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("8000")
        )
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("5000")
        )

        self.assertEqual(
            [a.nombre for a in historial_de_restricciones(self.estudiante)],
            ["$5.000", "$8.000"],
        )

    def test_guardar_la_misma_cifra_no_asienta_dos_veces(self):
        """No es un hecho nuevo: sería ruido en el libro."""
        for _ in range(3):
            fijar_limite_diario(
                actor=self.usuario, estudiante=self.estudiante, monto=Decimal("8000")
            )

        self.assertEqual(AsientoDeRestriccion.objects.count(), 1)

    def test_retirar_lo_que_no_habia_no_asienta(self):
        retirar_limite_diario(actor=self.usuario, estudiante=self.estudiante)

        self.assertEqual(AsientoDeRestriccion.objects.count(), 0)

    def test_el_libro_reconstruye_la_historia_del_cupo(self):
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("8000")
        )
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("12000")
        )
        retirar_limite_diario(actor=self.usuario, estudiante=self.estudiante)

        self.assertEqual(
            [(a.tipo, a.nombre) for a in historial_de_restricciones(self.estudiante)],
            [
                (TipoDeAsiento.RETIRO, "$12.000"),
                (TipoDeAsiento.BLOQUEO, "$12.000"),
                (TipoDeAsiento.BLOQUEO, "$8.000"),
            ],
        )


class LaPantallaDelRetiroTest(TestCase):
    """`TT-135`. La acción en la interfaz del acudiente (`INT-1`)."""

    def setUp(self):
        self.usuario, (self.estudiante,) = escenario()
        self.url = reverse("limite-diario", args=[self.estudiante.id])
        self.url_retiro = reverse(
            "retiro-del-limite-diario", args=[self.estudiante.id]
        )

    def _entrar(self):
        self.client.login(email=self.usuario.email, password=CLAVE)

    def test_con_limite_la_pantalla_ofrece_retirarlo(self):
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("8000")
        )
        self._entrar()

        respuesta = self.client.get(self.url)

        self.assertContains(respuesta, self.url_retiro)
        self.assertContains(respuesta, "Retirar el límite")

    def test_sin_limite_no_se_ofrece_retirar_nada(self):
        self._entrar()

        self.assertNotContains(self.client.get(self.url), self.url_retiro)

    def test_retirar_desde_la_pantalla_funciona_y_vuelve_al_panel(self):
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("8000")
        )
        self._entrar()

        respuesta = self.client.post(self.url_retiro)

        self.assertRedirects(respuesta, reverse("mis-estudiantes"))
        self.assertIsNone(limite_diario_de(self.estudiante))

    def test_un_get_al_retiro_no_retira_nada(self):
        """Un `GET` que escribe es una URL que el navegador reproduce solo."""
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("8000")
        )
        self._entrar()

        respuesta = self.client.get(self.url_retiro)

        self.assertEqual(respuesta.status_code, 405)
        self.assertIsNotNone(limite_diario_de(self.estudiante))

    def test_el_cajero_no_puede_retirar_por_la_url(self):
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("8000")
        )
        cajero = cuenta(Rol.CAJERO, "url")
        self.client.login(email=cajero.email, password=CLAVE)

        respuesta = self.client.post(self.url_retiro)

        self.assertEqual(respuesta.status_code, 403)
        self.assertIsNotNone(limite_diario_de(self.estudiante))

    def test_un_estudiante_ajeno_es_un_404(self):
        _, (ajeno,) = escenario(sufijo="4")
        self._entrar()

        respuesta = self.client.post(
            reverse("retiro-del-limite-diario", args=[ajeno.id])
        )

        self.assertEqual(respuesta.status_code, 404)

    def test_la_pantalla_enseña_el_historial_del_cupo(self):
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("8000")
        )
        retirar_limite_diario(actor=self.usuario, estudiante=self.estudiante)
        self._entrar()

        respuesta = self.client.get(self.url)

        self.assertContains(respuesta, "Se retiró el límite diario de")
        self.assertContains(respuesta, "Se fijó el límite diario en")
        self.assertContains(respuesta, "$8.000")

    def test_la_pantalla_ya_no_promete_que_el_retiro_llega_con_otra_historia(self):
        """Esa frase quedó desfasada al existir `HU-61`."""
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("8000")
        )
        self._entrar()

        self.assertNotContains(self.client.get(self.url), "Retirarlo del todo llega con")
