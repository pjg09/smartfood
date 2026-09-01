"""`TT-38`, `TT-39` y `TT-40`. Reasignación del código de tarjeta (`HU-46`).

Sostiene **`INVD-4`**: reasignar invalida el anterior de forma **inmediata y
definitiva**.

`TT-40` es la prueba que el plan sitúa en este PR y no después, y el motivo está
escrito allí: si el código anterior siguiera siendo válido, `HU-47` y `HU-48` del
Sprint 2 —desactivar a un estudiante— no protegerían nada. Alguien con la tarjeta
vieja seguiría comprando.

**La identificación por escaneo es `HU-15`, del Sprint 2, y todavía no existe.**
Así que «no identifica a nadie» se comprueba donde hoy se puede comprobar de
verdad: en la base. Cuando el punto de venta llegue, buscará por este mismo campo
único, así que la propiedad se conserva por construcción.
"""

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from unittest import mock

from cuentas.models import Rol
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from personas.codigo import ALFABETO, LONGITUD
from personas.models import Acudiente, Estudiante
from personas.services import (
    crear_estudiante,
    dar_de_alta_la_institucion,
    reasignar_codigo_de_tarjeta,
)

CLAVE = "clave-de-prueba-2026"


class BaseDeReasignacion(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo=CLAVE,
            )
        self.actor = institucion.usuario

        cuenta = crear_cuenta(
            email="marta.ruiz@example.com",
            rol=Rol.ACUDIENTE,
            nombre="Marta Ruiz Ochoa",
            enviar_invitacion=False,
        )
        self.acudiente = Acudiente.objects.create(
            usuario=cuenta, nombre="Marta Ruiz Ochoa", documento="43512345"
        )
        self.estudiante = crear_estudiante(
            actor=self.actor,
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001234501",
            acudiente=self.acudiente,
        )

    def reasignar(self, estudiante=None):
        return reasignar_codigo_de_tarjeta(
            actor=self.actor, estudiante=estudiante or self.estudiante
        )


# --- Primer criterio: el nuevo es aleatorio y no secuencial -----------------


class ElCodigoNuevoTest(BaseDeReasignacion):
    def test_reasignar_cambia_el_codigo(self):
        anterior, nuevo = self.reasignar()

        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.codigo_tarjeta, nuevo)
        self.assertNotEqual(nuevo, anterior)

    def test_el_nuevo_sale_del_mismo_generador(self):
        """Primer criterio: aleatorio y no secuencial, igual que en el alta."""
        _, nuevo = self.reasignar()

        self.assertEqual(len(nuevo), LONGITUD)
        self.assertTrue(set(nuevo) <= set(ALFABETO))

    def test_no_se_deriva_del_anterior(self):
        anterior, nuevo = self.reasignar()

        comun = 0
        for a, b in zip(anterior, nuevo):
            if a != b:
                break
            comun += 1
        self.assertLess(comun, 6, "el nuevo se parece demasiado al anterior")

    def test_reasignar_muchas_veces_no_repite(self):
        codigos = {self.estudiante.codigo_tarjeta}
        for _ in range(50):
            _, nuevo = self.reasignar()
            self.assertNotIn(nuevo, codigos)
            codigos.add(nuevo)

    def test_el_nuevo_nunca_es_el_que_se_acaba_de_retirar(self):
        """Una entre 10^21, y resucitaría la tarjeta que se está reponiendo.

        Se fuerza el caso: el generador devuelve primero el código actual.
        """
        actual = self.estudiante.codigo_tarjeta
        libre = "ZZZZZZZZZZZZZZ"

        with mock.patch(
            "personas.services.generar_codigo_de_tarjeta",
            side_effect=[actual, libre],
        ):
            anterior, nuevo = self.reasignar()

        self.assertEqual(anterior, actual)
        self.assertEqual(nuevo, libre)

    def test_sortea_otro_si_el_codigo_ya_es_de_alguien(self):
        otro = crear_estudiante(
            actor=self.actor,
            nombre="Tomás Restrepo Ruiz",
            documento="1001234502",
            acudiente=self.acudiente,
        )
        libre = "ZZZZZZZZZZZZZZ"

        with mock.patch(
            "personas.services.generar_codigo_de_tarjeta",
            side_effect=[otro.codigo_tarjeta, libre],
        ):
            _, nuevo = self.reasignar()

        self.assertEqual(nuevo, libre)
        otro.refresh_from_db()
        self.assertNotEqual(otro.codigo_tarjeta, nuevo, "le pisó el código a otro")


# --- `TT-40`. Segundo y tercer criterio, que son `INVD-4` -------------------


class ElCodigoAnteriorNoIdentificaANadieTest(BaseDeReasignacion):
    """`TT-40`. La prueba que impide que `HU-47` y `HU-48` no protejan nada."""

    def test_el_anterior_desaparece_de_la_base(self):
        anterior, _ = self.reasignar()

        self.assertFalse(
            Estudiante.objects.filter(codigo_tarjeta=anterior).exists(),
            "el código anterior todavía encuentra a alguien (INVD-4)",
        )

    def test_no_lo_conserva_ningun_otro_campo(self):
        """No hay «código anterior» guardado en ninguna parte, a propósito.

        Un modelo con lista de códigos y bandera de cuál está activo dejaría la
        puerta a una consulta que olvide filtrar por la bandera. Aquí el valor
        viejo deja de existir.
        """
        anterior, _ = self.reasignar()
        self.estudiante.refresh_from_db()

        valores = [
            getattr(self.estudiante, campo.name)
            for campo in Estudiante._meta.get_fields()
            if hasattr(self.estudiante, campo.name)
        ]
        self.assertNotIn(anterior, [v for v in valores if isinstance(v, str)])

    def test_la_invalidacion_es_inmediata(self):
        """En la misma petición, sin trabajo diferido ni caducidad."""
        anterior = self.estudiante.codigo_tarjeta
        self.reasignar()

        # Sin `refresh_from_db` de por medio: se consulta la base directamente.
        self.assertEqual(
            Estudiante.objects.filter(codigo_tarjeta=anterior).count(), 0
        )

    def test_es_definitiva_aunque_se_reasigne_muchas_veces(self):
        """Ninguno de los retirados vuelve a encontrar a nadie."""
        retirados = []
        for _ in range(20):
            anterior, _ = self.reasignar()
            retirados.append(anterior)

        self.assertEqual(
            Estudiante.objects.filter(codigo_tarjeta__in=retirados).count(), 0
        )

    def test_la_tarjeta_impresa_del_anterior_deja_de_valer(self):
        """De extremo a extremo, contra la vista imprimible (`HU-45`).

        Es lo más cerca del papel que se puede llegar sin un lector: la página
        que produce la tarjeta ya no contiene el código viejo.
        """
        self.client.force_login(self.actor)
        url = reverse("tarjeta-del-estudiante", args=[self.estudiante.pk])

        anterior = self.estudiante.codigo_tarjeta
        self.assertContains(self.client.get(url), anterior)

        self.reasignar()

        respuesta = self.client.get(url)
        self.assertNotContains(respuesta, anterior)
        self.estudiante.refresh_from_db()
        self.assertContains(respuesta, self.estudiante.codigo_tarjeta)


# --- Quién puede reasignar --------------------------------------------------


class SoloLaInstitucionReasignaTest(BaseDeReasignacion):
    def test_ningun_otro_rol(self):
        for rol in [Rol.CAJERO, Rol.ADMINISTRADOR, Rol.ACUDIENTE]:
            with self.subTest(rol=rol):
                otro = crear_cuenta(
                    email=f"{rol}@example.com", rol=rol, enviar_invitacion=False
                )
                with self.assertRaises(PermissionDenied):
                    reasignar_codigo_de_tarjeta(actor=otro, estudiante=self.estudiante)

    def test_ni_una_cuenta_desactivada(self):
        self.actor.is_active = False
        self.actor.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            self.reasignar()

    def test_el_codigo_no_cambio_tras_el_rechazo(self):
        antes = self.estudiante.codigo_tarjeta
        cajero = crear_cuenta(
            email="cajero@example.com", rol=Rol.CAJERO, enviar_invitacion=False
        )

        with self.assertRaises(PermissionDenied):
            reasignar_codigo_de_tarjeta(actor=cajero, estudiante=self.estudiante)

        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.codigo_tarjeta, antes)


# --- `TT-39`. La acción de la ficha, con confirmación -----------------------


class LaAccionPideConfirmacionTest(BaseDeReasignacion):
    """Reasignar no se deshace, así que no ocurre con un clic."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.actor)
        self.url = reverse("admin:personas_estudiante_changelist")

    def _lanzar(self, confirmado=False):
        datos = {
            "action": "accion_reasignar_codigo",
            "_selected_action": [str(self.estudiante.pk)],
        }
        if confirmado:
            datos["confirmado"] = "si"
        return self.client.post(self.url, datos)

    def test_el_primer_intento_solo_pregunta(self):
        antes = self.estudiante.codigo_tarjeta
        respuesta = self._lanzar()

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(
            respuesta, "admin/personas/estudiante/confirmar-reasignacion.html"
        )
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.codigo_tarjeta, antes, "reasignó sin preguntar")

    def test_la_confirmacion_enseña_el_codigo_que_va_a_invalidar(self):
        respuesta = self._lanzar()

        self.assertContains(respuesta, self.estudiante.codigo_tarjeta)
        self.assertContains(respuesta, "Ana Sofía Restrepo Ruiz")
        self.assertContains(respuesta, "no se puede deshacer")

    def test_al_confirmar_se_reasigna(self):
        antes = self.estudiante.codigo_tarjeta
        respuesta = self._lanzar(confirmado=True)

        self.assertEqual(respuesta.status_code, 302)
        self.estudiante.refresh_from_db()
        self.assertNotEqual(self.estudiante.codigo_tarjeta, antes)

    def test_el_mensaje_dice_cual_murio_y_ofrece_reimprimir(self):
        antes = self.estudiante.codigo_tarjeta
        respuesta = self._lanzar(confirmado=True)

        mensajes = " ".join(str(m) for m in respuesta.wsgi_request._messages)
        self.estudiante.refresh_from_db()

        self.assertIn(antes, mensajes)
        self.assertIn(self.estudiante.codigo_tarjeta, mensajes)
        self.assertIn(
            reverse("tarjeta-del-estudiante", args=[self.estudiante.pk]), mensajes
        )

    def test_reasigna_a_varios_de_una_vez(self):
        otro = crear_estudiante(
            actor=self.actor,
            nombre="Tomás Restrepo Ruiz",
            documento="1001234502",
            acudiente=self.acudiente,
        )
        antes = {self.estudiante.codigo_tarjeta, otro.codigo_tarjeta}

        self.client.post(
            self.url,
            {
                "action": "accion_reasignar_codigo",
                "_selected_action": [str(self.estudiante.pk), str(otro.pk)],
                "confirmado": "si",
            },
        )

        self.estudiante.refresh_from_db()
        otro.refresh_from_db()
        ahora = {self.estudiante.codigo_tarjeta, otro.codigo_tarjeta}
        self.assertEqual(ahora & antes, set())

    def test_el_personal_no_ve_la_accion(self):
        cajero = crear_cuenta(
            email="cajero@example.com",
            rol=Rol.CAJERO,
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.client.force_login(cajero)

        self.assertEqual(self.client.get(self.url).status_code, 403)
