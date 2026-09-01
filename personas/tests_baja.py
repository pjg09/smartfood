"""`TT-41` y `TT-42`. Baja lógica del estudiante retirado (`HU-51`).

**Protege `INV-2`.** El saldo se reconstruye desde el historial de movimientos, y
un `DELETE` lo destruiría. De ahí que la baja sea un estado y no un borrado, y de
ahí que la primera clase de este fichero compruebe que no se borra nada.

`DT-12` pide una máquina de estados explícita y descarta un booleano: no
distinguiría «perdió la tarjeta» de «se retiró del colegio», que `DEC-7` exige
separar. El estado `desactivado` existe en el modelo desde ahora aunque su
servicio llegue en el Sprint 2 (`HU-47`): una máquina de estados se declara
entera o no es una máquina de estados.
"""

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from personas.models import Acudiente, EstadoDelEstudiante, Estudiante
from personas.services import (
    EstudianteNoOperativo,
    comprobar_que_puede_operar,
    crear_estudiante,
    dar_de_alta_la_institucion,
    dar_de_baja,
    reasignar_codigo_de_tarjeta,
)

CLAVE = "clave-de-prueba-2026"


class BaseDeBaja(TestCase):
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


# --- Primer criterio: la baja es lógica ------------------------------------


class LaBajaNoBorraNadaTest(BaseDeBaja):
    """«El historial de consumo y el de movimientos se conservan íntegros.»

    Hoy no hay historial que conservar —billetera y ventas son el Sprint 2—, así
    que lo que se fija aquí es la propiedad de la que dependerá: **la fila del
    estudiante sigue ahí**, con su identificador, su documento y su código.
    """

    def test_el_estudiante_sigue_existiendo(self):
        identificador = self.estudiante.pk
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)

        self.assertTrue(Estudiante.objects.filter(pk=identificador).exists())
        self.assertEqual(Estudiante.objects.count(), 1)

    def test_no_pierde_ninguno_de_sus_datos(self):
        antes = {
            "nombre": self.estudiante.nombre,
            "documento": self.estudiante.documento,
            "codigo_tarjeta": self.estudiante.codigo_tarjeta,
            "acudiente_id": self.estudiante.acudiente_id,
            "creado_en": self.estudiante.creado_en,
        }
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)
        self.estudiante.refresh_from_db()

        for campo, valor in antes.items():
            with self.subTest(campo=campo):
                self.assertEqual(getattr(self.estudiante, campo), valor)

    def test_sigue_vinculado_a_su_acudiente(self):
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)
        self.assertEqual(self.acudiente.estudiantes.count(), 1)

    def test_el_codigo_de_tarjeta_no_se_libera(self):
        """Podría parecer que hay que liberarlo, y es justo lo contrario.

        Liberarlo permitiría que otro estudiante lo recibiera, y entonces una
        tarjeta vieja identificaría a otra persona — lo mismo que `INVD-4` evita
        al reasignar. Que no pueda comprar lo garantiza el estado.
        """
        codigo = self.estudiante.codigo_tarjeta
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)

        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.codigo_tarjeta, codigo)

    def test_el_admin_sigue_sin_ofrecer_borrado(self):
        """`PR-16` ya lo fijaba; aquí se comprueba que la baja no lo reintrodujo."""
        self.client.force_login(self.actor)
        respuesta = self.client.get(
            reverse("admin:personas_estudiante_delete", args=[self.estudiante.pk])
        )
        self.assertEqual(respuesta.status_code, 403)


# --- Segundo criterio: es un estado distinto de la desactivación ------------


class TresEstadosYNoUnBooleanoTest(BaseDeBaja):
    """`DT-12`. «Se retiró» no es «perdió la tarjeta»."""

    def test_la_maquina_de_estados_esta_declarada_entera(self):
        self.assertEqual(
            [e.value for e in EstadoDelEstudiante],
            ["activo", "desactivado", "baja"],
        )

    def test_baja_y_desactivado_son_estados_distintos(self):
        self.assertNotEqual(EstadoDelEstudiante.BAJA, EstadoDelEstudiante.DESACTIVADO)

    def test_el_estudiante_nace_activo(self):
        self.assertEqual(self.estudiante.estado, EstadoDelEstudiante.ACTIVO)
        self.assertTrue(self.estudiante.puede_operar)
        self.assertFalse(self.estudiante.esta_de_baja)

    def test_no_existe_un_booleano_de_actividad(self):
        """`DT-12` lo descarta explícitamente."""
        campos = {c.name for c in Estudiante._meta.get_fields()}
        for booleano in ["activo", "is_active", "dado_de_baja", "retirado"]:
            self.assertNotIn(booleano, campos)

    def test_la_base_rechaza_un_estado_inventado(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Estudiante.objects.filter(pk=self.estudiante.pk).update(
                    estado="expulsado"
                )

    def test_la_fecha_de_baja_no_puede_contradecir_al_estado(self):
        """Un estado `baja` sin fecha, o una fecha sin baja, es incoherente."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Estudiante.objects.filter(pk=self.estudiante.pk).update(estado="baja")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Estudiante.objects.filter(pk=self.estudiante.pk).update(
                    dado_de_baja_en="2026-08-31T12:00:00Z"
                )


class LaBajaDejaConstanciaTest(BaseDeBaja):
    def test_cambia_el_estado_y_anota_la_fecha(self):
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)
        self.estudiante.refresh_from_db()

        self.assertEqual(self.estudiante.estado, EstadoDelEstudiante.BAJA)
        self.assertIsNotNone(self.estudiante.dado_de_baja_en)
        self.assertTrue(self.estudiante.esta_de_baja)

    def test_es_idempotente(self):
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)
        self.estudiante.refresh_from_db()
        fecha = self.estudiante.dado_de_baja_en

        dar_de_baja(actor=self.actor, estudiante=self.estudiante)
        self.estudiante.refresh_from_db()

        self.assertEqual(self.estudiante.dado_de_baja_en, fecha)


# --- Tercer criterio: no puede comprar ni recargar --------------------------


class UnEstudianteDeBajaNoOperaTest(BaseDeBaja):
    """`INVD-2`, en la puerta que los servicios del Sprint 2 tendrán que llamar.

    Ni la billetera ni la venta existen todavía. La regla es de `HU-51` y
    `DEC-7`, así que se escribe ahora: dejarla para el sprint que la necesita es
    dejarla al descuido de quien escriba la venta.
    """

    def test_el_activo_opera(self):
        comprobar_que_puede_operar(self.estudiante)  # no levanta

    def test_el_de_baja_no_opera(self):
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)

        with self.assertRaises(EstudianteNoOperativo) as ctx:
            comprobar_que_puede_operar(self.estudiante)

        self.assertIn("se retiró del colegio", str(ctx.exception))

    def test_el_desactivado_tampoco(self):
        """`INVD-2` junta los dos estados para esto, aunque sean distintos.

        El servicio que desactiva es `HU-47`, del Sprint 2. La puerta ya lo
        contempla, así que cuando llegue no hay que acordarse de nada.
        """
        Estudiante.objects.filter(pk=self.estudiante.pk).update(estado="desactivado")
        self.estudiante.refresh_from_db()

        with self.assertRaises(EstudianteNoOperativo):
            comprobar_que_puede_operar(self.estudiante)

    def test_reasignarle_el_codigo_no_lo_devuelve_a_la_vida(self):
        """Una tarjeta nueva no revierte una baja."""
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)
        reasignar_codigo_de_tarjeta(actor=self.actor, estudiante=self.estudiante)

        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.estado, EstadoDelEstudiante.BAJA)
        with self.assertRaises(EstudianteNoOperativo):
            comprobar_que_puede_operar(self.estudiante)


# --- Quién puede darla ------------------------------------------------------


class SoloLaInstitucionDaDeBajaTest(BaseDeBaja):
    def test_ningun_otro_rol(self):
        for rol in [Rol.CAJERO, Rol.ADMINISTRADOR, Rol.ACUDIENTE]:
            with self.subTest(rol=rol):
                otro = crear_cuenta(
                    email=f"{rol}@example.com", rol=rol, enviar_invitacion=False
                )
                with self.assertRaises(PermissionDenied):
                    dar_de_baja(actor=otro, estudiante=self.estudiante)

    def test_el_acudiente_tampoco_para_su_propio_hijo(self):
        """`HU-48` deja al acudiente **desactivar**, que es otro estado y otro
        sprint. Retirar del colegio es cosa del colegio."""
        with self.assertRaises(PermissionDenied):
            dar_de_baja(actor=self.acudiente.usuario, estudiante=self.estudiante)

        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.estado, EstadoDelEstudiante.ACTIVO)

    def test_ni_una_cuenta_desactivada(self):
        self.actor.is_active = False
        self.actor.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            dar_de_baja(actor=self.actor, estudiante=self.estudiante)


# --- `TT-42`. La acción de la ficha ----------------------------------------


class LaAccionDeBajaTest(BaseDeBaja):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.actor)
        self.url = reverse("admin:personas_estudiante_changelist")

    def _lanzar(self, confirmado=False):
        datos = {
            "action": "accion_dar_de_baja",
            "_selected_action": [str(self.estudiante.pk)],
        }
        if confirmado:
            datos["confirmado"] = "si"
        return self.client.post(self.url, datos)

    def test_el_primer_intento_solo_pregunta(self):
        respuesta = self._lanzar()

        self.assertTemplateUsed(
            respuesta, "admin/personas/estudiante/confirmar-baja.html"
        )
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.estado, EstadoDelEstudiante.ACTIVO)

    def test_la_confirmacion_avisa_de_lo_que_conserva_y_de_lo_que_no(self):
        respuesta = self._lanzar()

        self.assertContains(respuesta, "no se deshace")
        self.assertContains(respuesta, "se conservan íntegros")
        # Y recuerda cuál es la acción que sí tiene vuelta.
        self.assertContains(respuesta, "Reasigna el código")

    def test_al_confirmar_da_de_baja(self):
        respuesta = self._lanzar(confirmado=True)
        self.assertEqual(respuesta.status_code, 302)

        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.estado, EstadoDelEstudiante.BAJA)

    def test_el_listado_muestra_el_estado_y_deja_filtrar(self):
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)
        respuesta = self.client.get(self.url)

        self.assertContains(respuesta, "De baja")
        self.assertContains(respuesta, "estado")

        solo_activos = self.client.get(self.url, {"estado": "activo"})
        self.assertNotContains(solo_activos, "Ana Sofía Restrepo Ruiz")

    def test_el_estado_no_se_edita_a_mano_desde_la_ficha(self):
        """Se transita con la acción, que pasa por el servicio (`DT-15`)."""
        cuerpo = self.client.get(
            reverse("admin:personas_estudiante_change", args=[self.estudiante.pk])
        ).content.decode()

        self.assertNotIn('name="estado"', cuerpo)
        self.assertNotIn('name="dado_de_baja_en"', cuerpo)


# --- Lo que el acudiente ve -------------------------------------------------


class ElAcudienteVeQueSuHijoEstaDeBajaTest(BaseDeBaja):
    """No puede desaparecer del panel —su saldo sigue siendo consultable
    (`HU-52`)— pero tampoco puede verse igual que uno activo."""

    def test_el_panel_lo_sigue_mostrando(self):
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)
        self.client.force_login(self.acudiente.usuario)

        respuesta = self.client.get(reverse("mis-estudiantes"))
        self.assertContains(respuesta, "Ana Sofía Restrepo Ruiz")

    def test_y_dice_que_esta_de_baja(self):
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)
        self.client.force_login(self.acudiente.usuario)

        respuesta = self.client.get(
            reverse("estudiante-seleccionado", args=[self.estudiante.pk])
        )
        self.assertContains(respuesta, "De baja")
        self.assertContains(respuesta, "congelado")

    def test_mientras_esta_activo_no_dice_nada(self):
        self.client.force_login(self.acudiente.usuario)
        respuesta = self.client.get(
            reverse("estudiante-seleccionado", args=[self.estudiante.pk])
        )
        self.assertNotContains(respuesta, "De baja")
