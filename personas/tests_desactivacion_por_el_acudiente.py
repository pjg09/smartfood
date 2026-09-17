"""`TT-121` y `TT-122`. Desactivación por el acudiente (`HU-48`, `INVD-2`, `INVD-3`).

Los dos criterios de `HU-48`:

1. **El acudiente puede desactivar en cualquier momento a los estudiantes a su
   cargo.** «A su cargo» es la mitad que importa: el alcance **es** la
   autorización, como en `estudiantes_a_cargo`.
2. **El acudiente no dispone de la acción de reactivar** (`HU-49`, `INVD-3`). No
   es un botón escondido: no hay servicio ni ruta que lo haga, y
   `ElAcudienteNoReactivaTest` lo comprueba por los dos caminos.

**Por qué existen las dos vías** (`DEC-5`): el colegio bloquea de inmediato en
mitad de la jornada, cuando el niño avisa allí (`HU-47`); el acudiente bloquea
sin depender del horario de secretaría, cuando el niño le avisa a él. Quitar
cualquiera de las dos deja un hueco de horas, que es justo cuando una tarjeta
perdida se usa.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, EstadoDelEstudiante, Estudiante
from personas.services import EstudianteNoOperativo, dar_de_baja, desactivar
from ventas.models import Venta
from ventas.services import registrar_venta

CLAVE = "clave-de-prueba-2026"
DESACTIVAR = "desactivacion-por-el-acudiente"


def familia(sufijo, correo):
    """Un acudiente con dos hijos. Dos familias hacen falta para probar el alcance."""
    usuario = Usuario.objects.crear_usuario(
        email=correo, rol=Rol.ACUDIENTE, nombre=f"Acudiente {sufijo}"
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
    ficha = Acudiente.objects.create(
        usuario=usuario, nombre=f"Acudiente {sufijo} Ruiz", documento=f"43100555{sufijo}"
    )
    hijos = [
        Estudiante.objects.create(
            nombre=f"Estudiante {sufijo}{i}",
            documento=f"10012555{sufijo}{i}",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        for i in range(2)
    ]
    return usuario, hijos


class BaseDelAcudiente(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        self.acudiente, (self.hijo, self.hermano) = familia("1", "acudiente-a@example.com")
        self.vecina, (self.ajeno, _) = familia("2", "acudiente-b@example.com")

        self.institucion = crear_cuenta(
            email="institucion-acu@example.com",
            rol=Rol.INSTITUCION,
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.cajero = crear_cuenta(
            email="cajero-acu@example.com", rol=Rol.CAJERO, enviar_invitacion=False
        )

        self.producto = Producto.objects.create(
            nombre="Empanada",
            precio=Decimal("3000"),
            categoria=Categoria.objects.create(nombre="Cafetería"),
        )
        MovimientoInventario.objects.create(
            producto=self.producto,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=50,
            motivo="Ingreso de prueba",
        )

    def estado_de(self, estudiante):
        estudiante.refresh_from_db()
        return estudiante.estado


# --- Criterio 1: desactiva a los suyos, y solo a los suyos ----------------


class ElAcudienteDesactivaALosSuyosTest(BaseDelAcudiente):
    def test_desactiva_a_su_estudiante(self):
        desactivar(actor=self.acudiente, estudiante=self.hijo)

        self.assertEqual(self.estado_de(self.hijo), EstadoDelEstudiante.DESACTIVADO)

    def test_no_alcanza_al_estudiante_de_otra_familia(self):
        """El alcance **es** la autorización, igual que en `estudiantes_a_cargo`."""
        with self.assertRaises(PermissionDenied):
            desactivar(actor=self.acudiente, estudiante=self.ajeno)

        self.assertEqual(self.estado_de(self.ajeno), EstadoDelEstudiante.ACTIVO)

    def test_desactivar_a_uno_no_toca_a_su_hermano(self):
        desactivar(actor=self.acudiente, estudiante=self.hijo)

        self.assertEqual(self.estado_de(self.hermano), EstadoDelEstudiante.ACTIVO)

    def test_una_cuenta_de_acudiente_desactivada_no_opera(self):
        """`HU-42`, la misma regla que en el resto de servicios."""
        self.acudiente.is_active = False
        self.acudiente.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            desactivar(actor=self.acudiente, estudiante=self.hijo)

    def test_a_un_retirado_tampoco_se_le_desactiva(self):
        """La misma regla que por la vía de la institución: de la baja no se vuelve."""
        dar_de_baja(actor=self.institucion, estudiante=self.hijo)

        with self.assertRaises(ValidationError):
            desactivar(actor=self.acudiente, estudiante=self.hijo)

    def test_la_institucion_sigue_alcanzando_a_cualquiera(self):
        """`HU-47` no se estrecha al ampliar la puerta: son dos vías, no una."""
        desactivar(actor=self.institucion, estudiante=self.ajeno)

        self.assertEqual(self.estado_de(self.ajeno), EstadoDelEstudiante.DESACTIVADO)

    def test_el_efecto_es_el_mismo_venga_de_quien_venga(self):
        """`INVD-2` mira el estado, no quién lo puso."""
        recargar(actor=self.acudiente, estudiante=self.hijo, monto=Decimal("50000"))
        desactivar(actor=self.acudiente, estudiante=self.hijo)

        with self.assertRaises(EstudianteNoOperativo):
            registrar_venta(
                actor=self.cajero,
                estudiante=Estudiante.objects.get(pk=self.hijo.pk),
                lineas={self.producto.id: 1},
            )

        self.assertEqual(Venta.objects.count(), 0)


# --- Criterio 2: no dispone de la acción de reactivar ---------------------


class ElAcudienteNoReactivaTest(BaseDelAcudiente):
    """`INVD-3`. La asimetría tiene un motivo de seguridad.

    El desbloqueo pasa por una verificación presencial en el colegio, y eso es lo
    que impide que quien encontró la tarjeta consiga que se reactive. Si el
    acudiente pudiera reactivar desde el teléfono, bastaría con convencerlo.
    """

    def setUp(self):
        super().setUp()
        desactivar(actor=self.acudiente, estudiante=self.hijo)

    def test_no_existe_ningun_servicio_de_reactivacion(self):
        """Se vigila la ausencia, que es lo que se perdería sin darse cuenta.

        `HU-49` construirá uno **para la institución**; el día que exista, esta
        prueba obliga a mirar de nuevo quién puede llamarlo.
        """
        from personas import services

        candidatos = [n for n in dir(services) if "reactiv" in n.lower()]
        self.assertEqual(candidatos, [])

    def test_desactivar_no_admite_un_argumento_que_lo_deshaga(self):
        with self.assertRaises(TypeError):
            desactivar(actor=self.acudiente, estudiante=self.hijo, reactivar=True)

    def test_la_pantalla_no_ofrece_reactivar_y_dice_a_quien_pedirlo(self):
        self.client.force_login(self.acudiente)

        cuerpo = self.client.get(
            reverse("estudiante-seleccionado", args=[self.hijo.id])
        ).content.decode()

        self.assertIn("data-tarjeta-desactivada", cuerpo)
        self.assertNotIn("data-desactivar-la-tarjeta", cuerpo)
        self.assertNotIn("Reactivar", cuerpo)
        self.assertIn("institución educativa", cuerpo)


# --- `TT-122`: la acción en la interfaz del acudiente ---------------------


class LaAccionDelPanelTest(BaseDelAcudiente):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.acudiente)
        self.url = reverse(DESACTIVAR, args=[self.hijo.id])

    def test_desactiva_y_devuelve_la_ficha_con_el_estado_nuevo(self):
        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-tarjeta-desactivada")
        self.assertEqual(self.estado_de(self.hijo), EstadoDelEstudiante.DESACTIVADO)

    def test_devuelve_un_fragmento_y_no_la_pagina(self):
        """`DT-16`. Lo que se intercambia es la ficha, no el panel entero."""
        respuesta = self.client.post(self.url)

        self.assertTemplateUsed(respuesta, "partials/estudiante-seleccionado.html")
        self.assertTemplateNotUsed(respuesta, "personas/mis-estudiantes.html")

    def test_la_ficha_deja_de_ofrecer_recargar(self):
        """`INVD-2`: a un desactivado no se le recarga, así que no se le ofrece."""
        antes = self.client.get(
            reverse("estudiante-seleccionado", args=[self.hijo.id])
        ).content.decode()
        self.assertIn("Recargar", antes)

        despues = self.client.post(self.url).content.decode()

        self.assertNotIn("Recargar", despues)

    def test_un_estudiante_ajeno_es_404_y_no_403(self):
        """Los dos casos —no existe y no es tuyo— se responden igual a propósito:
        un `403` le confirmaría a un desconocido que ese estudiante existe."""
        ajeno = reverse(DESACTIVAR, args=[self.ajeno.id])

        self.assertEqual(self.client.post(ajeno).status_code, 404)
        self.assertEqual(self.estado_de(self.ajeno), EstadoDelEstudiante.ACTIVO)

    def test_el_get_no_desactiva(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(self.estado_de(self.hijo), EstadoDelEstudiante.ACTIVO)

    def test_los_otros_roles_no_entran_por_esta_ruta(self):
        """`INT-1` es del acudiente. La institución tiene la suya, en el padrón."""
        for cuenta in [self.institucion, self.cajero]:
            with self.subTest(rol=cuenta.rol):
                self.client.force_login(cuenta)

                self.assertEqual(self.client.post(self.url).status_code, 403)

        self.assertEqual(self.estado_de(self.hijo), EstadoDelEstudiante.ACTIVO)

    def test_a_un_retirado_lo_rechaza_y_lo_dice_en_la_ficha(self):
        """Vuelve en `200` con el motivo dentro: htmx no intercambia los `4xx`."""
        dar_de_baja(actor=self.institucion, estudiante=self.hijo)

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-error-de-la-ficha")
        self.assertEqual(self.estado_de(self.hijo), EstadoDelEstudiante.BAJA)

    def test_la_ficha_de_un_activo_ofrece_la_accion(self):
        cuerpo = self.client.get(
            reverse("estudiante-seleccionado", args=[self.hijo.id])
        ).content.decode()

        self.assertIn("data-desactivar-la-tarjeta", cuerpo)
        self.assertNotIn("data-tarjeta-desactivada", cuerpo)

    def test_un_retirado_no_ofrece_desactivar(self):
        """Ya no puede comprar: ofrecer bloquearlo sería ofrecer algo sin efecto."""
        dar_de_baja(actor=self.institucion, estudiante=self.hijo)

        cuerpo = self.client.get(
            reverse("estudiante-seleccionado", args=[self.hijo.id])
        ).content.decode()

        self.assertNotIn("data-desactivar-la-tarjeta", cuerpo)
        self.assertNotIn("data-tarjeta-desactivada", cuerpo)
