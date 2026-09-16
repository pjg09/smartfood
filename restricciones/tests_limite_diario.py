"""`TT-94`, `TT-95`, `TT-96`. El límite diario de gasto (`HU-09`, `ALC-IN-07`).

Los tres criterios de `HU-09`, uno por uno:

1. **El límite se define por estudiante.** Un acudiente con dos hijos fija dos
   cupos independientes, y cambiar el de uno no toca el del otro.
2. **Solo el acudiente puede fijarlo o modificarlo.** Ni el cajero, ni la
   administración de la cafetería, ni la institución educativa — es `INV-4`
   escrita sobre la fila «Recargar saldo y fijar límite diario» de `[S11]`.
3. **El límite se evalúa contra el consumo del día en cada venta.** *No se
   comprueba aquí, y se declara en lugar de saltarse:* la evaluación la
   construye `TT-116` dentro del bloqueo de `registrar_venta` (`PR-09`,
   `HU-20`, `DT-6`), y su caso de prueba es `TT-118`. Lo que este módulo sí
   comprueba es lo que esa evaluación necesita: que el cupo quede guardado por
   estudiante y que solo el acudiente lo haya podido escribir.

Y la decisión de modelado que conviene vigilar: **no haber fila es no tener
límite**, y un cupo de cero no existe. Son hechos opuestos y escribirlos igual
—`monto = 0` para «no configuré nada»— dejaría a la venta de `TT-116` sin forma
de distinguir «puede gastar lo que tenga» de «no puede comprar nada».
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from personas.services import dar_de_baja
from restricciones.models import LimiteDiario
from restricciones.selectors import limite_diario_de
from restricciones.services import MONTO_MAXIMO, fijar_limite_diario

CLAVE = "clave-de-prueba-2026"


def acudiente_con_estudiantes(sufijo="1", estudiantes=1):
    """Un acudiente con su cuenta y `n` estudiantes a cargo."""
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente{sufijo}@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])

    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"9351234{sufijo}"
    )
    hijos = [
        Estudiante.objects.create(
            nombre=f"Estudiante {sufijo}{i}",
            documento=f"900{sufijo}00{i}",
            acudiente=acudiente,
            # El código lo genera el generador de `DT-9`, no una cadena a mano:
            # su forma la vigila una `CheckConstraint` (`INV-7`, `TT-32`).
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        for i in range(estudiantes)
    ]
    return usuario, acudiente, hijos


def cuenta(rol, sufijo):
    """Una cuenta de un rol cualquiera, para probar quién NO puede."""
    usuario = Usuario.objects.crear_usuario(
        email=f"{rol}{sufijo}@example.com", rol=rol, nombre=f"Cuenta {rol}"
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
    return usuario


class ElLimiteEsPorEstudianteTest(TestCase):
    """Primer criterio de `HU-09`, que es además una propiedad del esquema."""

    def setUp(self):
        self.usuario, self.acudiente, self.hijos = acudiente_con_estudiantes(estudiantes=2)

    def test_dos_hijos_del_mismo_acudiente_llevan_limites_independientes(self):
        uno, otro = self.hijos

        fijar_limite_diario(actor=self.usuario, estudiante=uno, monto=Decimal("5000"))
        fijar_limite_diario(actor=self.usuario, estudiante=otro, monto=Decimal("12000"))

        self.assertEqual(limite_diario_de(uno).monto, Decimal("5000.00"))
        self.assertEqual(limite_diario_de(otro).monto, Decimal("12000.00"))

    def test_cambiar_el_limite_de_un_hijo_no_toca_el_del_otro(self):
        uno, otro = self.hijos
        fijar_limite_diario(actor=self.usuario, estudiante=uno, monto=Decimal("5000"))
        fijar_limite_diario(actor=self.usuario, estudiante=otro, monto=Decimal("12000"))

        fijar_limite_diario(actor=self.usuario, estudiante=uno, monto=Decimal("3000"))

        self.assertEqual(limite_diario_de(uno).monto, Decimal("3000.00"))
        self.assertEqual(limite_diario_de(otro).monto, Decimal("12000.00"))

    def test_el_estudiante_no_puede_tener_dos_limites(self):
        """Lo impone el `OneToOneField`, no el servicio.

        Si el criterio dependiera de que `fijar_limite_diario` se acuerde de
        buscar antes de crear, bastaría un segundo camino de escritura para
        dejar dos cupos sobre el mismo estudiante y ninguna forma de saber cuál
        manda.
        """
        uno = self.hijos[0]
        LimiteDiario.objects.create(estudiante=uno, monto=Decimal("5000"))

        with self.assertRaises(IntegrityError), transaction.atomic():
            LimiteDiario.objects.create(estudiante=uno, monto=Decimal("9000"))

    def test_fijar_dos_veces_modifica_en_lugar_de_acumular(self):
        uno = self.hijos[0]
        fijar_limite_diario(actor=self.usuario, estudiante=uno, monto=Decimal("5000"))
        fijar_limite_diario(actor=self.usuario, estudiante=uno, monto=Decimal("7500.50"))

        self.assertEqual(LimiteDiario.objects.filter(estudiante=uno).count(), 1)
        self.assertEqual(limite_diario_de(uno).monto, Decimal("7500.50"))


class SoloElAcudienteFijaElLimiteTest(TestCase):
    """Segundo criterio de `HU-09`, que es `INV-4` sobre la fila de `[S11]`.

    **Se llama al servicio con cada rol**, no se mira la pantalla: `DT-11` dice
    que la regla vive en la capa de datos, y un botón oculto lo salta cualquiera
    que escriba la URL.
    """

    def setUp(self):
        self.usuario, self.acudiente, (self.estudiante,) = acudiente_con_estudiantes()

    def _rechaza(self, actor):
        with self.assertRaises(PermissionDenied):
            fijar_limite_diario(
                actor=actor, estudiante=self.estudiante, monto=Decimal("5000")
            )
        self.assertIsNone(limite_diario_de(self.estudiante))

    def test_el_cajero_no_fija_el_limite(self):
        self._rechaza(cuenta(Rol.CAJERO, "a"))

    def test_la_administracion_de_la_cafeteria_no_fija_el_limite(self):
        self._rechaza(cuenta(Rol.ADMINISTRADOR, "a"))

    def test_la_institucion_educativa_no_fija_el_limite(self):
        self._rechaza(cuenta(Rol.INSTITUCION, "a"))

    def test_otro_acudiente_no_fija_el_limite_de_un_hijo_ajeno(self):
        """Tener el rol no basta: hay que ser **su** acudiente."""
        ajeno, _, _ = acudiente_con_estudiantes(sufijo="2")
        self._rechaza(ajeno)

    def test_una_cuenta_de_acudiente_desactivada_no_fija_el_limite(self):
        self.usuario.is_active = False
        self.usuario.save(update_fields=["is_active"])
        self._rechaza(self.usuario)

    def test_sin_cuenta_identificada_no_se_fija_ningun_limite(self):
        self._rechaza(None)

    def test_el_acudiente_del_estudiante_si_lo_fija(self):
        limite = fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("5000")
        )
        self.assertEqual(limite.monto, Decimal("5000.00"))

    def test_el_cajero_tampoco_modifica_uno_ya_fijado(self):
        """`INV-4` en su forma literal: la cafetería **no desactiva** lo puesto."""
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("5000")
        )

        with self.assertRaises(PermissionDenied):
            fijar_limite_diario(
                actor=cuenta(Rol.CAJERO, "b"),
                estudiante=self.estudiante,
                monto=Decimal("999999"),
            )

        self.assertEqual(limite_diario_de(self.estudiante).monto, Decimal("5000.00"))


class UnLimiteDeCeroNoExisteTest(TestCase):
    """No haber fila y haber un cero son hechos opuestos, y no se escriben igual."""

    def setUp(self):
        self.usuario, self.acudiente, (self.estudiante,) = acudiente_con_estudiantes()

    def test_sin_configurar_el_selector_devuelve_none_y_no_un_cero(self):
        self.assertIsNone(limite_diario_de(self.estudiante))

    def test_el_servicio_rechaza_el_cero(self):
        with self.assertRaises(ValidationError):
            fijar_limite_diario(
                actor=self.usuario, estudiante=self.estudiante, monto=Decimal("0")
            )

    def test_el_servicio_rechaza_un_monto_negativo(self):
        with self.assertRaises(ValidationError):
            fijar_limite_diario(
                actor=self.usuario, estudiante=self.estudiante, monto=Decimal("-100")
            )

    def test_la_base_rechaza_el_cero_aunque_nadie_pase_por_el_servicio(self):
        """La `CheckConstraint`, que es la que sobrevive a un `shell` o a una migración."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            LimiteDiario.objects.create(estudiante=self.estudiante, monto=Decimal("0"))

    def test_la_base_rechaza_un_negativo(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            LimiteDiario.objects.create(estudiante=self.estudiante, monto=Decimal("-1"))


class ElMontoSeValidaTest(TestCase):
    def setUp(self):
        self.usuario, self.acudiente, (self.estudiante,) = acudiente_con_estudiantes()

    def test_por_encima_del_maximo_se_rechaza_con_una_frase_y_no_con_un_error_de_postgres(self):
        with self.assertRaises(ValidationError):
            fijar_limite_diario(
                actor=self.usuario,
                estudiante=self.estudiante,
                monto=MONTO_MAXIMO + Decimal("0.01"),
            )

    def test_un_tercer_decimal_se_rechaza_en_lugar_de_redondearse_en_silencio(self):
        with self.assertRaises(ValidationError):
            fijar_limite_diario(
                actor=self.usuario, estudiante=self.estudiante, monto=Decimal("5000.001")
            )

    def test_lo_que_no_es_una_cifra_se_rechaza(self):
        with self.assertRaises(ValidationError):
            fijar_limite_diario(
                actor=self.usuario, estudiante=self.estudiante, monto="cinco mil"
            )


class ConfigurarNoEsOperarTest(TestCase):
    """`INVD-2` no alcanza a esto, y es una decisión declarada.

    Un estudiante de baja no compra ni recarga —eso lo impide
    `billetera.services.asentar`—, pero fijar un cupo no mueve dinero ni
    existencias y no tiene efecto hasta que haya una venta, que es justo lo que
    `INVD-2` ya impide. Bloquearlo dejaría al hijo sin protección el día que se
    reactivara.
    """

    def setUp(self):
        self.usuario, self.acudiente, (self.estudiante,) = acudiente_con_estudiantes()
        self.institucion = cuenta(Rol.INSTITUCION, "baja")

    def test_el_acudiente_de_un_estudiante_de_baja_sigue_pudiendo_fijar_el_limite(self):
        dar_de_baja(actor=self.institucion, estudiante=self.estudiante)
        self.estudiante.refresh_from_db()

        limite = fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("4000")
        )

        self.assertEqual(limite.monto, Decimal("4000.00"))


class LaPantallaDelLimiteTest(TestCase):
    """`TT-96`. La pantalla del acudiente (`INT-1`).

    La vista no decide nada: el 404 lo produce `estudiante_a_cargo` y el rechazo
    lo produce el servicio (`DT-15`). Lo que se comprueba aquí es que la pantalla
    exista, escriba por el servicio y no se le abra a quien no le corresponde.
    """

    def setUp(self):
        self.usuario, self.acudiente, self.hijos = acudiente_con_estudiantes(estudiantes=2)
        self.estudiante = self.hijos[0]
        self.url = reverse("limite-diario", args=[self.estudiante.id])

    def test_el_acudiente_abre_la_pantalla(self):
        self.client.login(email=self.usuario.email, password=CLAVE)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)

    def test_sin_sesion_se_redirige_al_acceso(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("acceso"), respuesta["Location"])

    def test_un_estudiante_ajeno_es_un_404_igual_que_uno_inexistente(self):
        ajeno_usuario, _, (ajeno,) = acudiente_con_estudiantes(sufijo="2")
        self.client.login(email=self.usuario.email, password=CLAVE)

        respuesta = self.client.get(reverse("limite-diario", args=[ajeno.id]))
        self.assertEqual(respuesta.status_code, 404)

    def test_el_cajero_no_alcanza_la_pantalla_de_un_estudiante(self):
        """`403` y no `404`, y la diferencia importa.

        `estudiantes_a_cargo` rechaza el rol **antes** de mirar ningún
        identificador, así que el cajero no llega a consultar nada. El `404` se
        reserva para quien sí es acudiente y pregunta por un estudiante que no
        es suyo: ahí el objetivo es no confirmarle que existe.
        """
        cajero = cuenta(Rol.CAJERO, "pantalla")
        self.client.login(email=cajero.email, password=CLAVE)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 403)

    def test_enviar_el_formulario_fija_el_limite_y_vuelve_al_panel(self):
        self.client.login(email=self.usuario.email, password=CLAVE)

        respuesta = self.client.post(self.url, {"monto": "6500"})

        self.assertRedirects(respuesta, reverse("mis-estudiantes"))
        self.assertEqual(limite_diario_de(self.estudiante).monto, Decimal("6500.00"))

    def test_un_cero_no_escribe_nada_y_la_pantalla_lo_dice(self):
        self.client.login(email=self.usuario.email, password=CLAVE)

        respuesta = self.client.post(self.url, {"monto": "0"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertIsNone(limite_diario_de(self.estudiante))

    def test_el_campo_llega_con_el_limite_vigente_en_formato_que_el_navegador_acepta(self):
        """Un defecto encontrado al fotografiar la pantalla, y la prueba que lo fija.

        El proyecto está en `es-CO`, así que Django escribe un `Decimal` como
        «8000,00». Un `<input type="number">` con coma **se pinta vacío y no da
        ningún error**: el acudiente que entra a cambiar su límite vería el campo
        en blanco y concluiría que no tenía ninguno. Lo arregla `unlocalize` en
        la plantilla, y esto impide que vuelva.
        """
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("8000")
        )
        self.client.login(email=self.usuario.email, password=CLAVE)

        cuerpo = self.client.get(self.url).content.decode()

        self.assertIn('value="8000.00"', cuerpo)
        self.assertNotIn('value="8000,00"', cuerpo)

    def test_la_ficha_del_panel_enseña_el_limite_vigente(self):
        """`TT-96` sobre el panel de `HU-04`: la tarjeta deja de ser un hueco."""
        fijar_limite_diario(
            actor=self.usuario, estudiante=self.estudiante, monto=Decimal("7000")
        )
        self.client.login(email=self.usuario.email, password=CLAVE)

        respuesta = self.client.get(reverse("mis-estudiantes"))

        self.assertContains(respuesta, "$7.000")
        self.assertContains(respuesta, self.url)

    def test_sin_limite_la_ficha_dice_que_no_hay_y_no_enseña_un_cero(self):
        """Un cero se leería como un cupo de cero, que es lo contrario."""
        self.client.login(email=self.usuario.email, password=CLAVE)

        respuesta = self.client.get(reverse("mis-estudiantes"))

        self.assertContains(respuesta, "Sin límite")
        self.assertContains(respuesta, "Fijar un límite")
        self.assertNotContains(respuesta, "Cambiar el límite")
