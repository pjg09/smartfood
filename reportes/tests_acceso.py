"""`TT-157`. Quién ve el consumo de un estudiante (`HU-30`, `[S11]`, `DT-11`).

El segundo criterio de `HU-30` —«solo el acudiente accede al consumo de los
estudiantes a su cargo»— tiene **dos mitades que fallan por separado**, y aquí
se comprueban las dos:

1. **El rol.** `[S11]`, fila «Consultar reportes de consumo de su hijo», concede
   a `USR-2` y a nadie más: ni la cafetería, que vende, ni la institución, que
   tiene el padrón. Los tres reciben `403`.
2. **El vínculo.** Un acudiente es un actor legítimo, y esa es justamente la
   forma en que esto se rompe sin que el rol lo note: leer el historial del hijo
   de otro. Responde `404`, no `403`, porque un `403` le confirmaría que ese
   estudiante existe.

**No se mira ninguna plantilla para afirmar nada de esto.** Esconder el enlace
no es control de acceso, es aparentarlo (`DT-11`): las pruebas van contra la
ruta y contra el selector, que es donde vive la regla.

Lo que hay detrás no es una cifra: es el registro de qué come un menor y a qué
hora está en la cafetería. Por eso la comprobación es de la capa de datos y no
de la interfaz (`ALC-OUT-08`, Ley 1581 de 2012).
"""

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from reportes.selectors import historial_de_consumo

# Los tres roles que `[S11]` deja fuera de esta fila. El acudiente no está: es
# el único que sí.
ROLES_SIN_CONSUMO = (Rol.CAJERO, Rol.ADMINISTRADOR, Rol.INSTITUCION)


def acudiente_con_estudiante(sufijo, nombre="Ana Sofía Restrepo Ruiz"):
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente-{sufijo}@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
    )
    ficha = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"431001{sufijo}"
    )
    estudiante = Estudiante.objects.create(
        nombre=nombre,
        documento=f"100123{sufijo}",
        acudiente=ficha,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )
    return usuario, estudiante


class BaseDeAcceso(TestCase):
    """Dos familias sin relación entre sí: la de Marta y la de Andrés."""

    def setUp(self):
        self.acudiente, self.estudiante = acudiente_con_estudiante("4501")
        self.ajeno, self.estudiante_ajeno = acudiente_con_estudiante(
            "7801", nombre="Julián Ospina Vélez"
        )

    def consultar(self, estudiante=None):
        return self.client.get(
            reverse("historial-de-consumo", args=[(estudiante or self.estudiante).id])
        )


class SoloElAcudienteEntraAlHistorialTest(BaseDeAcceso):
    """Primera mitad: el rol."""

    def test_el_acudiente_llega_a_la_pantalla_de_su_estudiante(self):
        self.client.force_login(self.acudiente)

        respuesta = self.consultar()

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "reportes/historial-de-consumo.html")

    def test_ningun_otro_rol_entra(self):
        """Incluida la institución educativa, que sí tiene el padrón.

        Tener los datos del estudiante para administrarlo no es tener su
        consumo: `[S11]` son dos filas distintas.
        """
        for numero, rol in enumerate(ROLES_SIN_CONSUMO):
            with self.subTest(rol=rol):
                self.client.force_login(
                    Usuario.objects.crear_usuario(
                        email=f"otro-rol-{numero}@example.com",
                        rol=rol,
                        nombre="Persona de prueba",
                    )
                )
                self.assertEqual(self.consultar().status_code, 403)

    def test_sin_sesion_manda_a_la_pantalla_de_acceso(self):
        """No un `403`: quien no ha entrado todavía no tiene rol que rechazar."""
        respuesta = self.consultar()

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("acceso"), respuesta.headers["Location"])

    def test_la_pantalla_no_se_escribe(self):
        """`POST` responde `405`: un reporte es una lectura y nada más."""
        self.client.force_login(self.acudiente)

        respuesta = self.client.post(
            reverse("historial-de-consumo", args=[self.estudiante.id])
        )

        self.assertEqual(respuesta.status_code, 405)


class SoloDeLosEstudiantesAsuCargoTest(BaseDeAcceso):
    """Segunda mitad: el vínculo. **La que el rol no cubre.**"""

    def test_un_acudiente_no_ve_el_historial_de_un_estudiante_ajeno(self):
        self.client.force_login(self.acudiente)

        respuesta = self.consultar(self.estudiante_ajeno)

        self.assertEqual(respuesta.status_code, 404)

    def test_un_estudiante_inexistente_responde_lo_mismo_que_uno_ajeno(self):
        """Los dos casos se responden igual **a propósito**.

        Distinguirlos convertiría la ruta en un oráculo: probar identificadores
        diría cuáles corresponden a un estudiante matriculado.
        """
        self.client.force_login(self.acudiente)

        inexistente = self.client.get(
            reverse(
                "historial-de-consumo",
                args=["0199c0de-0000-7000-8000-000000000000"],
            )
        )

        self.assertEqual(inexistente.status_code, 404)
        self.assertEqual(self.consultar(self.estudiante_ajeno).status_code, 404)


class ElSelectorAutorizaPorSuCuentaTest(BaseDeAcceso):
    """La regla vive en la capa de datos, no en la vista (`DT-11`, `DT-15`).

    Si mañana aparece otra pantalla que lea el consumo —el informe final, una
    exportación—, la comprobación ya está hecha aquí y no hay que acordarse de
    repetirla.
    """

    def test_el_acudiente_del_estudiante_consulta(self):
        historial = historial_de_consumo(
            actor=self.acudiente, estudiante=self.estudiante
        )

        self.assertEqual(historial.count(), 0)

    def test_otro_rol_no_consulta_aunque_llame_directamente(self):
        for numero, rol in enumerate(ROLES_SIN_CONSUMO):
            with self.subTest(rol=rol):
                actor = Usuario.objects.crear_usuario(
                    email=f"directo-{numero}@example.com", rol=rol, nombre="Persona"
                )
                with self.assertRaises(PermissionDenied):
                    historial_de_consumo(actor=actor, estudiante=self.estudiante)

    def test_un_acudiente_ajeno_no_consulta(self):
        with self.assertRaises(PermissionDenied):
            historial_de_consumo(actor=self.ajeno, estudiante=self.estudiante)

    def test_una_cuenta_desactivada_no_consulta(self):
        """`HU-42`. Desactivar una cuenta apaga todo lo que hacía, no una parte."""
        self.acudiente.is_active = False
        self.acudiente.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            historial_de_consumo(actor=self.acudiente, estudiante=self.estudiante)

    def test_sin_actor_no_consulta(self):
        with self.assertRaises(PermissionDenied):
            historial_de_consumo(actor=None, estudiante=self.estudiante)


class ElPanelEnlazaAlHistorialTest(BaseDeAcceso):
    """`TT-156`. La tarjeta de consumo es la única puerta a la pantalla.

    Se afirma sobre la URL y sobre un `data-*` propio, nunca sobre la redacción
    del enlace: mejorar una frase no puede romper una prueba de otro asunto.
    """

    def test_la_ficha_del_estudiante_enlaza_a_su_historial(self):
        self.client.force_login(self.acudiente)

        respuesta = self.client.get(reverse("mis-estudiantes"))

        self.assertContains(respuesta, "data-enlace-al-consumo")
        self.assertContains(
            respuesta, reverse("historial-de-consumo", args=[self.estudiante.id])
        )

    def test_el_panel_no_enlaza_al_historial_de_un_estudiante_ajeno(self):
        self.client.force_login(self.acudiente)

        respuesta = self.client.get(reverse("mis-estudiantes"))

        self.assertNotContains(
            respuesta,
            reverse("historial-de-consumo", args=[self.estudiante_ajeno.id]),
        )
