"""`TT-119` y `TT-120`. Desactivación por la institución (`HU-47`, `INVD-2`).

Los dos criterios de `HU-47`:

1. **La institución puede desactivar en cualquier momento.** El servicio es la
   regla (`DT-15`) y el padrón es la puerta (`DT-29`).
2. **El efecto es inmediato en el punto de venta.** No hay nada que propagar:
   `INVD-2` se comprueba leyendo el estado, y la venta ya pasa por esa puerta.
   `ElEfectoEsInmediatoEnLaCajaTest` lo demuestra cobrando de verdad.

**Desactivar no es dar de baja**, y estas pruebas lo separan igual que lo separan
`DEC-7` y `EstadoDelEstudiante`: la baja es del que se fue del colegio y no se
revierte; la desactivación es de la tarjeta perdida y la revierte la institución
(`HU-49`, que llega después).

`HU-48` —el acudiente desactivando a los suyos— amplía esta misma puerta y tiene
sus propias pruebas (`tests_desactivacion_por_el_acudiente.py`). Aquí se
comprueba lo que esa ampliación **no** toca: que la cafetería sigue fuera y que
la vía del padrón es de la institución.
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
from personas.services import (
    EstudianteNoOperativo,
    comprobar_que_puede_operar,
    dar_de_baja,
    desactivar,
)
from ventas.models import Venta
from ventas.services import EstudianteNoPuedeComprar, registrar_venta

CLAVE = "clave-de-prueba-2026"
PADRON = "padron"
DESACTIVAR = "desactivacion-de-estudiante"


def escenario():
    """La institución, un acudiente con dos hijos, un cajero y un producto."""
    sincronizar_grupos_y_permisos()

    institucion = crear_cuenta(
        email="institucion-desact@example.com",
        rol=Rol.INSTITUCION,
        accede_a_administracion=True,
        enviar_invitacion=False,
        contrasena_de_desarrollo=CLAVE,
    )
    cajero = crear_cuenta(
        email="cajero-desact@example.com",
        rol=Rol.CAJERO,
        enviar_invitacion=False,
        contrasena_de_desarrollo=CLAVE,
    )
    acudiente = Usuario.objects.crear_usuario(
        email="acudiente-desact@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
    )
    ficha = Acudiente.objects.create(
        usuario=acudiente, nombre="Marta Ruiz Ochoa", documento="4310066666"
    )
    estudiante = Estudiante.objects.create(
        nombre="Ana Sofía Restrepo Ruiz",
        documento="1001266601",
        acudiente=ficha,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )
    hermano = Estudiante.objects.create(
        nombre="Tomás Restrepo Ruiz",
        documento="1001266602",
        acudiente=ficha,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )

    producto = Producto.objects.create(
        nombre="Empanada",
        precio=Decimal("3000"),
        categoria=Categoria.objects.create(nombre="Cafetería"),
    )
    MovimientoInventario.objects.create(
        producto=producto,
        tipo=TipoDeMovimientoDeInventario.INGRESO,
        cantidad=50,
        motivo="Ingreso de prueba",
    )

    return institucion, cajero, acudiente, estudiante, hermano, producto


class BaseDeDesactivacion(TestCase):
    def setUp(self):
        (
            self.institucion,
            self.cajero,
            self.acudiente,
            self.estudiante,
            self.hermano,
            self.producto,
        ) = escenario()

    def estado_de(self, estudiante):
        estudiante.refresh_from_db()
        return estudiante.estado


# --- Criterio 1: la institución desactiva en cualquier momento -------------


class SoloLaInstitucionDesactivaTest(BaseDeDesactivacion):
    """`[S11]` y `HU-44`: administrar estudiantes es suyo, y esto lo es."""

    def test_la_institucion_desactiva(self):
        desactivar(actor=self.institucion, estudiante=self.estudiante)

        self.assertEqual(
            self.estado_de(self.estudiante), EstadoDelEstudiante.DESACTIVADO
        )

    def test_la_cafeteria_no_puede(self):
        """`[S11]` no le da estudiantes a la cafetería, ni para esto.

        **El acudiente no está en esta lista desde `HU-48`**, que amplió la
        puerta a los estudiantes a su cargo; lo suyo se prueba en
        `tests_desactivacion_por_el_acudiente.py`. Quienes siguen fuera son los
        dos roles de la cafetería, y por eso la prueba se reescribió en vez de
        borrarse.
        """
        administracion = crear_cuenta(
            email="administracion-desact@example.com",
            rol=Rol.ADMINISTRADOR,
            enviar_invitacion=False,
        )

        for cuenta in [self.cajero, administracion]:
            with self.subTest(rol=cuenta.rol):
                with self.assertRaises(PermissionDenied):
                    desactivar(actor=cuenta, estudiante=self.estudiante)

        self.assertEqual(self.estado_de(self.estudiante), EstadoDelEstudiante.ACTIVO)

    def test_una_cuenta_desactivada_de_la_institucion_no_opera(self):
        """`HU-42`, la misma regla que en el resto de servicios."""
        self.institucion.is_active = False
        self.institucion.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            desactivar(actor=self.institucion, estudiante=self.estudiante)

    def test_es_de_ese_estudiante_y_no_de_sus_hermanos(self):
        desactivar(actor=self.institucion, estudiante=self.estudiante)

        self.assertEqual(self.estado_de(self.hermano), EstadoDelEstudiante.ACTIVO)


class DesactivarNoEsDarDeBajaTest(BaseDeDesactivacion):
    """`DEC-7`, `DT-12`. Dos hechos distintos, dos estados distintos."""

    def test_desactivar_no_marca_la_fecha_de_baja(self):
        """`dado_de_baja_en` responde «cuándo se retiró del colegio».

        Escribirlo aquí haría que un estudiante con la tarjeta perdida figurara
        como retirado en cualquier consulta que mire esa fecha.
        """
        desactivar(actor=self.institucion, estudiante=self.estudiante)

        self.estudiante.refresh_from_db()
        self.assertIsNone(self.estudiante.dado_de_baja_en)
        self.assertFalse(self.estudiante.esta_de_baja)

    def test_a_un_retirado_no_se_le_desactiva(self):
        """De la baja no se vuelve, así que no es un paso intermedio hacia nada.

        Aceptarlo dejaría en el padrón a un retirado marcado como desactivado,
        que se lee como si pudiera reactivarse.
        """
        dar_de_baja(actor=self.institucion, estudiante=self.estudiante)

        with self.assertRaises(ValidationError):
            desactivar(actor=self.institucion, estudiante=self.estudiante)

        self.assertEqual(self.estado_de(self.estudiante), EstadoDelEstudiante.BAJA)

    def test_desactivar_dos_veces_no_es_un_error(self):
        """Idempotente: en una secretaría con dos personas atendiendo el mismo
        teléfono, la segunda no tiene por qué recibir un fallo."""
        desactivar(actor=self.institucion, estudiante=self.estudiante)
        desactivar(actor=self.institucion, estudiante=self.estudiante)

        self.assertEqual(
            self.estado_de(self.estudiante), EstadoDelEstudiante.DESACTIVADO
        )

    def test_no_existe_ningun_argumento_que_reactive(self):
        """`INVD-3`, `HU-49`: reactivar es otra historia y otro servicio.

        Se vigila la ausencia, que es lo que se perdería sin darse cuenta.
        """
        with self.assertRaises(TypeError):
            desactivar(
                actor=self.institucion, estudiante=self.estudiante, reactivar=True
            )


# --- Criterio 2: el efecto es inmediato en el punto de venta --------------


class ElEfectoEsInmediatoEnLaCajaTest(BaseDeDesactivacion):
    """`INVD-2`. No hay nada que propagar: la caja lee el estado.

    El motivo de rechazo propio llega con `HU-50` (`TT-126`); lo que este PR
    tiene que demostrar es que **la venta no ocurre**, que es el criterio.
    """

    def setUp(self):
        super().setUp()
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000")
        )

    def _vender(self):
        return registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante,
            lineas={self.producto.id: 1},
        )

    def test_antes_de_desactivar_la_venta_se_cobra(self):
        """El contraste, y es imprescindible: sin él, la prueba de abajo pasaría
        con una caja que no vendiera nunca."""
        self.assertIsNotNone(self._vender())

    def test_despues_de_desactivar_la_misma_venta_se_rechaza(self):
        """Desde `TT-125` el rechazo es una `VentaRechazada` con motivo propio.

        Cuando se escribió esta prueba (`PR-10`) llegaba como
        `EstudianteNoOperativo`, al escribir en el libro; `HU-50` lo movió al
        principio de la venta y le puso etiqueta.
        """
        desactivar(actor=self.institucion, estudiante=self.estudiante)

        with self.assertRaises(EstudianteNoPuedeComprar):
            self._vender()

        self.assertEqual(Venta.objects.count(), 0)

    def test_tampoco_se_le_recarga(self):
        """`INVD-7` (`DEC-14`): las dos direcciones del dinero, cerradas.

        `PR-13` llegó a abrirlas, siguiendo el tercer criterio de `HU-50`, y
        `DEC-14` corrigió el criterio: la tarjeta está perdida, y engordar su
        saldo no es inocuo cuando el sistema no sabe devolver dinero.
        """
        desactivar(actor=self.institucion, estudiante=self.estudiante)

        with self.assertRaises(EstudianteNoOperativo):
            recargar(
                actor=self.acudiente,
                estudiante=self.estudiante,
                monto=Decimal("10000"),
            )

    def test_la_puerta_de_invd_2_lo_reconoce(self):
        desactivar(actor=self.institucion, estudiante=self.estudiante)
        self.estudiante.refresh_from_db()

        with self.assertRaises(EstudianteNoOperativo):
            comprobar_que_puede_operar(self.estudiante)

    def test_al_hermano_se_le_sigue_cobrando(self):
        desactivar(actor=self.institucion, estudiante=self.estudiante)
        recargar(actor=self.acudiente, estudiante=self.hermano, monto=Decimal("50000"))

        venta = registrar_venta(
            actor=self.cajero,
            estudiante=self.hermano,
            lineas={self.producto.id: 1},
        )
        self.assertIsNotNone(venta)


# --- `TT-120`: la acción en el padrón -------------------------------------


class LaAccionDelPadronTest(BaseDeDesactivacion):
    """`DT-29`. La primera escritura del padrón, por el camino real."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.institucion)
        self.url = reverse(DESACTIVAR, args=[self.estudiante.id])

    def test_desactiva_y_devuelve_la_tabla_con_el_estado_nuevo(self):
        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-estudiante-desactivado")
        self.assertEqual(
            self.estado_de(self.estudiante), EstadoDelEstudiante.DESACTIVADO
        )

    def test_devuelve_un_fragmento_y_no_la_pagina(self):
        """`DT-16`. Lo que se intercambia es la tabla, no el padrón entero."""
        respuesta = self.client.post(self.url)

        self.assertTemplateUsed(respuesta, "personas/partials/padron-tabla.html")
        self.assertTemplateNotUsed(respuesta, "personas/padron.html")

    def test_conserva_la_busqueda_que_estaba_puesta(self):
        """Quien desactiva estaba buscando a alguien: devolverle el padrón
        entero le borra la búsqueda."""
        respuesta = self.client.post(self.url, {"busqueda": "Ana Sofía"})

        self.assertEqual(
            [e.id for e in respuesta.context["estudiantes"]], [self.estudiante.id]
        )
        self.assertEqual(respuesta.context["busqueda"], "Ana Sofía")

    def test_el_get_no_desactiva(self):
        """Una escritura por `GET` la dispara un rastreador o un prefetch."""
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(self.estado_de(self.estudiante), EstadoDelEstudiante.ACTIVO)

    def test_un_identificador_que_no_existe_es_404(self):
        ajeno = reverse(DESACTIVAR, args=["01234567-89ab-7def-8123-456789abcdef"])

        self.assertEqual(self.client.post(ajeno).status_code, 404)

    def test_los_demas_roles_reciben_403(self):
        """`DT-11`: el rol se rechaza en la capa de datos, no escondiendo el botón.

        **El acudiente también, y aunque el estudiante sea suyo.** Desde `HU-48`
        puede desactivarlo, pero por su propia ruta (`INT-1`): esta es la del
        padrón, y el padrón es de la institución.
        """
        for cuenta in [self.cajero, self.acudiente]:
            with self.subTest(rol=cuenta.rol):
                self.client.force_login(cuenta)

                self.assertEqual(self.client.post(self.url).status_code, 403)

        self.assertEqual(self.estado_de(self.estudiante), EstadoDelEstudiante.ACTIVO)

    def test_a_un_retirado_lo_rechaza_y_lo_dice_en_la_tabla(self):
        """El rechazo vuelve en `200`: htmx no intercambia lo que llega en `4xx`,
        así que un `400` dejaría la pantalla igual y sin explicación."""
        dar_de_baja(actor=self.institucion, estudiante=self.estudiante)

        respuesta = self.client.post(self.url, {"retirados": "1"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-error-del-padron")
        self.assertEqual(self.estado_de(self.estudiante), EstadoDelEstudiante.BAJA)

    def test_el_padron_en_si_sigue_sin_aceptar_escrituras(self):
        """`DT-27` sigue en pie salvo en lo que `DT-29` corrige: la pantalla no
        escribe, **una ruta suya** sí."""
        self.assertEqual(self.client.post(reverse(PADRON)).status_code, 405)


class LoQueLaTablaEnsenaTest(BaseDeDesactivacion):
    """Qué ve secretaría, antes y después."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.institucion)

    def _tabla(self):
        return self.client.get(reverse("padron-tabla")).content.decode()

    def test_un_estudiante_activo_ofrece_desactivarlo_y_no_lleva_marca(self):
        cuerpo = self._tabla()

        self.assertIn("data-desactivar-estudiante", cuerpo)
        self.assertNotIn("data-estudiante-desactivado-marca", cuerpo)

    def test_un_desactivado_se_marca_y_deja_de_ofrecer_la_accion(self):
        desactivar(actor=self.institucion, estudiante=self.estudiante)
        desactivar(actor=self.institucion, estudiante=self.hermano)

        cuerpo = self._tabla()

        self.assertIn("data-estudiante-desactivado-marca", cuerpo)
        self.assertNotIn("data-desactivar-estudiante", cuerpo)

    def test_donde_habia_un_hueco_ahora_esta_la_accion(self):
        """El hueco de `PR-10` declaraba que reactivar llegaba con `HU-49`.

        Llegó (`PR-12`), así que la fila ya no anuncia nada: ofrece la acción.
        Un hueco que sobrevive a la historia que lo iba a llenar es tan falso
        como un botón deshabilitado, que es lo que `[S2.4]` prohíbe.
        """
        desactivar(actor=self.institucion, estudiante=self.estudiante)

        cuerpo = self._tabla()

        self.assertIn("data-reactivar-estudiante", cuerpo)
        self.assertNotIn("data-reactivar-pendiente", cuerpo)
        self.assertNotIn("disabled", cuerpo)

    def test_un_retirado_no_ofrece_desactivar_ni_reactivar(self):
        dar_de_baja(actor=self.institucion, estudiante=self.estudiante)
        dar_de_baja(actor=self.institucion, estudiante=self.hermano)

        cuerpo = self.client.get(
            reverse("padron-tabla"), {"retirados": "1"}
        ).content.decode()

        self.assertIn("data-estudiante-retirado", cuerpo)
        self.assertNotIn("data-desactivar-estudiante", cuerpo)
        self.assertNotIn("data-reactivar-estudiante", cuerpo)

    def test_el_desactivado_sigue_saliendo_en_el_padron(self):
        """Desactivado no es retirado: sigue matriculado y sale sin marcar nada.

        Esconderlo dejaría a secretaría sin la fila desde la que lo reactivará.
        """
        desactivar(actor=self.institucion, estudiante=self.estudiante)

        respuesta = self.client.get(reverse("padron-tabla"))

        self.assertIn(self.estudiante.id, [e.id for e in respuesta.context["estudiantes"]])
