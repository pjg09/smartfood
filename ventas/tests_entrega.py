"""`TT-149`, `TT-150`, `TT-151`. Registro de la entrega (`HU-25`).

Los dos criterios de la historia:

1. **La entrega se registra en el punto de venta.** `LaEntregaSeRegistraEnLaCajaTest`.
2. **El pedido ya pagado no vuelve a descontar saldo al entregarse.**
   `EntregarNoVuelveACobrarTest`, y es `TT-151`.

**Este fichero vigila el único fallo del sprint que ninguna invariante detecta.**
Si la entrega reutilizara `registrar_venta`, el estudiante pagaría dos veces **y
el sistema seguiría cuadrando**: el historial sería consistente, `INV-2` se
cumpliría y las dos ventas existirían de verdad. No hay restricción de base ni
invariante que lo note. Lo único que lo nota es una prueba que compare el saldo
de antes con el de después, y esa es la razón de que este fichero exista.

Y el título de la historia pide lo otro: «para que quede constancia de que se
entregó **y no se entregue dos veces**». Eso sí lo sostiene la base —una venta
descuenta cada producto una sola vez—, y `LaEntregaNoSeRepiteTest` comprueba las
dos capas: el mensaje del servicio y la restricción por debajo.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse

from billetera.models import MovimientoBilletera, TipoDeMovimiento
from billetera.selectors import saldo_de
from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from personas.services import dar_de_baja, desactivar
from ventas.models import EstadoDelPedido, PedidoAnticipado
from ventas.selectors import existencias_sin_reservar, reservas_pendientes
from ventas.services import (
    EstudianteNoPuedeComprar,
    PedidoYaEntregado,
    entregar,
    registrar_venta,
    reservar,
)


def familia(documento="1001234501", email=None):
    usuario = Usuario.objects.crear_usuario(
        email=email or f"acudiente{documento}@example.com",
        rol=Rol.ACUDIENTE,
        nombre="Marta",
    )
    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"43{documento}"
    )
    estudiante = Estudiante.objects.create(
        nombre="Ana Sofía Restrepo Ruiz",
        documento=documento,
        acudiente=acudiente,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )
    return usuario, estudiante


def producto(nombre="Empanada", precio="3500", existencias=10):
    categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
    articulo = Producto.objects.create(
        nombre=nombre, precio=Decimal(precio), categoria=categoria
    )
    if existencias:
        MovimientoInventario.objects.create(
            producto=articulo,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=existencias,
            motivo="Ingreso de prueba",
        )
    return articulo


class BaseEntrega(TestCase):
    def setUp(self):
        self.acudiente, self.estudiante = familia()
        self.empanada = producto()
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000")
        )
        self.pedido = reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 2},
        )
        # Lo que quedó tras cobrar la reserva: 50.000 − 2 × 3.500.
        self.saldo_tras_reservar = Decimal("43000.00")


# --- Criterio 2: TT-151, el fallo que ninguna invariante detecta ----------


class EntregarNoVuelveACobrarTest(BaseEntrega):
    """**`TT-151`.** El segundo criterio de `HU-25`, y la razón de este fichero.

    El error a evitar deja la base **consistente**: dos ventas de verdad, dos
    movimientos correctos, `INV-2` cumpliéndose. Nada falla. Lo único que lo
    delata es comparar el saldo antes y después de entregar.
    """

    def test_el_saldo_no_se_mueve_al_entregar(self):
        antes = saldo_de(self.estudiante)
        self.assertEqual(antes, self.saldo_tras_reservar)

        entregar(actor=self.cajero, pedido=self.pedido)

        self.assertEqual(saldo_de(self.estudiante), antes)

    def test_no_se_asienta_ningun_movimiento_de_billetera_al_entregar(self):
        """Más fuerte que mirar el saldo: **no aparece ningún asiento nuevo**.

        Un cobro y una devolución del mismo importe dejarían el saldo igual y el
        historial con dos movimientos que nadie hizo.
        """
        cuantos = MovimientoBilletera.objects.count()

        entregar(actor=self.cajero, pedido=self.pedido)

        self.assertEqual(MovimientoBilletera.objects.count(), cuantos)

    def test_la_entrega_no_crea_una_segunda_venta(self):
        """Si reutilizara `registrar_venta` habría dos ventas del mismo pedido, y
        las dos serían legítimas a ojos de la base."""
        ventas = self.pedido.venta.__class__.objects.count()

        entregado = entregar(actor=self.cajero, pedido=self.pedido)

        self.assertEqual(self.pedido.venta.__class__.objects.count(), ventas)
        self.assertEqual(entregado.venta_id, self.pedido.venta_id)

    def test_el_servicio_no_toca_la_billetera_por_ningun_camino(self):
        """La ausencia, comprobada sobre el código.

        Las tres pruebas de arriba se sostienen sobre el comportamiento de hoy.
        Esta fija lo estructural: `entregar` **no menciona la billetera**. Si
        alguien añadiera la llamada, las otras lo cazarían igual; esta dice por
        qué en una línea.
        """
        import inspect

        from ventas import services

        # `co_names` y no el texto del fichero: `inspect.getsource` incluye el
        # docstring, y ahí la ausencia **se explica**, así que buscar el nombre
        # en el código fuente lo encuentra en la explicación de por qué no está.
        # Los nombres que la función de verdad usa están en su bytecode.
        usados = set(inspect.unwrap(services.entregar).__code__.co_names)

        self.assertNotIn("asentar_en_la_billetera", usados)
        self.assertNotIn("registrar_venta", usados)
        # Y la contraprueba: sí usa el del inventario, así que la comprobación
        # de arriba distingue de verdad y no pasa por mirar donde no hay nada.
        self.assertIn("asentar_en_el_inventario", usados)


# --- Criterio 1: se registra en el punto de venta -------------------------


class LaEntregaMueveElInventarioTest(BaseEntrega):
    """`DT-33`: la reserva cobró y no descontó; la entrega descuenta."""

    def test_las_existencias_bajan_al_entregar(self):
        self.assertEqual(existencias_de(self.empanada), 10)

        entregar(actor=self.cajero, pedido=self.pedido)

        self.assertEqual(existencias_de(self.empanada), 8)

    def test_el_movimiento_señala_la_venta_que_lo_explica(self):
        """`INV-3`, `TT-78`. El motivo de una salida por venta **es** la venta."""
        entregar(actor=self.cajero, pedido=self.pedido)

        movimiento = MovimientoInventario.objects.get(
            tipo=TipoDeMovimientoDeInventario.VENTA
        )
        self.assertEqual(movimiento.venta_id, self.pedido.venta_id)
        self.assertEqual(movimiento.cantidad, -2)

    def test_al_entregar_las_unidades_dejan_de_estar_apartadas(self):
        """Antes de entregar estaban en el libro pero apartadas; después salen
        del libro. La cifra disponible no cambia — cambia de sitio."""
        self.assertEqual(existencias_sin_reservar()[self.empanada.id], 8)

        entregar(actor=self.cajero, pedido=self.pedido)

        self.assertEqual(existencias_sin_reservar()[self.empanada.id], 8)
        self.assertEqual(existencias_de(self.empanada), 8)

    def test_la_entrega_no_se_rechaza_por_falta_de_existencias(self):
        """**La decisión que `[S7]` de reglas-de-la-venta.md dejó a esta historia.**

        El compromiso ya se adquirió y se cobró: rechazar la entrega dejaría al
        estudiante sin lo suyo y con el dinero pagado, que es peor que un
        descuadre. El negativo que queda es información verdadera —salió
        mercancía que el libro no tenía— y la pantalla de `HU-29` lo enseña.
        """
        cajero2 = Usuario.objects.crear_usuario(
            email="cajero2@example.com", rol=Rol.CAJERO, nombre="Otro"
        )
        otro_acudiente, otro = familia("1009999902", email="otra@example.com")
        recargar(actor=otro_acudiente, estudiante=otro, monto=Decimal("50000"))
        # La caja vende las diez, incluidas las dos apartadas: es el hueco que
        # `DT-33` dejó abierto y que esta historia decide cómo sobrellevar.
        registrar_venta(
            actor=cajero2, estudiante=otro, lineas={self.empanada.id: 10}
        )
        self.assertEqual(existencias_de(self.empanada), 0)

        entregar(actor=self.cajero, pedido=self.pedido)

        self.assertEqual(existencias_de(self.empanada), -2)
        self.assertTrue(
            PedidoAnticipado.objects.get(pk=self.pedido.pk).estado
            == EstadoDelPedido.ENTREGADO
        )


class LaEntregaNoSeRepiteTest(BaseEntrega):
    """«Para que quede constancia de que se entregó **y no se entregue dos
    veces**», que es el «para qué» de `HU-25`."""

    def test_el_pedido_queda_entregado_con_quien_y_cuando(self):
        entregado = entregar(actor=self.cajero, pedido=self.pedido)

        self.assertEqual(entregado.estado, EstadoDelPedido.ENTREGADO)
        self.assertEqual(entregado.entregado_por, self.cajero)
        self.assertIsNotNone(entregado.entregado_en)
        self.assertFalse(entregado.esta_pendiente)

    def test_entregar_dos_veces_lo_rechaza_el_servicio(self):
        entregar(actor=self.cajero, pedido=self.pedido)

        with self.assertRaises(PedidoYaEntregado):
            entregar(actor=self.cajero, pedido=self.pedido)

    def test_el_segundo_intento_no_descuenta_otra_vez(self):
        entregar(actor=self.cajero, pedido=self.pedido)

        with self.assertRaises(PedidoYaEntregado):
            entregar(actor=self.cajero, pedido=self.pedido)

        self.assertEqual(existencias_de(self.empanada), 8)
        self.assertEqual(saldo_de(self.estudiante), self.saldo_tras_reservar)

    def test_la_base_tambien_lo_impide_saltandose_el_servicio(self):
        """`DT-15`: la invariante que la base pueda imponer, la impone la base.

        Se asienta a mano un segundo movimiento de venta para la misma venta y
        el mismo producto, que es lo que haría una entrega doble por un camino
        que se olvidara de mirar el estado. La restricción lo rechaza.
        """
        entregar(actor=self.cajero, pedido=self.pedido)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MovimientoInventario.objects.create(
                    producto=self.empanada,
                    tipo=TipoDeMovimientoDeInventario.VENTA,
                    cantidad=-2,
                    venta=self.pedido.venta,
                )

    def test_un_pedido_entregado_sale_de_la_cola(self):
        """`HU-24` y `HU-25` se encuentran aquí: lo entregado deja de estar
        pendiente de preparar."""
        self.assertEqual(reservas_pendientes(actor=self.cajero).count(), 1)

        entregar(actor=self.cajero, pedido=self.pedido)

        self.assertEqual(reservas_pendientes(actor=self.cajero).count(), 0)

    def test_se_mira_el_estado_dentro_del_bloqueo(self):
        """`DT-6`, el mismo patrón que el cobro.

        Sin `select_for_update`, dos cajas que leyeran el pedido a la vez verían
        las dos «pendiente» y entregarían las dos. Se fija por el **orden de las
        consultas**: el `SELECT … FOR UPDATE` antes de la escritura del estado.
        """
        with CaptureQueriesContext(connection) as consultas:
            entregar(actor=self.cajero, pedido=self.pedido)

        sentencias = [c["sql"].upper() for c in consultas.captured_queries]

        bloqueo = next(
            (i for i, sql in enumerate(sentencias) if "FOR UPDATE" in sql), None
        )
        escritura = next(
            (
                i
                for i, sql in enumerate(sentencias)
                if sql.startswith("UPDATE") and "PEDIDOANTICIPADO" in sql
            ),
            None,
        )

        self.assertIsNotNone(bloqueo, "No se emitió ningún SELECT ... FOR UPDATE.")
        self.assertIsNotNone(escritura, "No se escribió el estado del pedido.")
        self.assertLess(bloqueo, escritura)


class SoloElCajeroEntregaTest(BaseEntrega):
    """`[S11]`, y el primer criterio: la entrega es del punto de venta."""

    def test_ningun_otro_rol_entrega(self):
        for rol, email in [
            (Rol.ADMINISTRADOR, "admin@example.com"),
            (Rol.INSTITUCION, "institucion@example.com"),
        ]:
            with self.subTest(rol=rol):
                otro = Usuario.objects.crear_usuario(
                    email=email, rol=rol, nombre="Otro"
                )
                with self.assertRaises(PermissionDenied):
                    entregar(actor=otro, pedido=self.pedido)

    def test_el_acudiente_no_retira_el_pedido_de_su_hijo(self):
        """Lo reservó él, pero **retirarlo es un acto del mostrador**: quien
        entrega da fe de que el estudiante se lo llevó."""
        with self.assertRaises(PermissionDenied):
            entregar(actor=self.acudiente, pedido=self.pedido)

    def test_un_anonimo_tampoco(self):
        with self.assertRaises(PermissionDenied):
            entregar(actor=None, pedido=self.pedido)

    def test_un_rechazo_no_deja_nada_escrito(self):
        otro = Usuario.objects.crear_usuario(
            email="admin2@example.com", rol=Rol.ADMINISTRADOR, nombre="Otro"
        )

        with self.assertRaises(PermissionDenied):
            entregar(actor=otro, pedido=self.pedido)

        self.assertEqual(existencias_de(self.empanada), 10)
        self.assertTrue(
            PedidoAnticipado.objects.get(pk=self.pedido.pk).esta_pendiente
        )


class UnEstudianteQueNoOperaNoRetiraTest(BaseEntrega):
    """`INVD-2`, segundo criterio de `HU-50`.

    La regla no se reimplementa: `comprobar_que_puede_operar` es la puerta única
    y la entrega la llama igual que el cobro. Es literalmente lo que la prueba
    del Sprint 3 anticipó al decir «quien construya el retiro llamará a la misma».
    """

    def _no_deja_entregar(self, transicion):
        institucion = Usuario.objects.crear_usuario(
            email=f"institucion{transicion.__name__}@example.com",
            rol=Rol.INSTITUCION,
            nombre="Secretaría",
        )
        transicion(actor=institucion, estudiante=self.estudiante)
        self.estudiante.refresh_from_db()

        with self.assertRaises(EstudianteNoPuedeComprar):
            entregar(actor=self.cajero, pedido=self.pedido)

        self.assertEqual(existencias_de(self.empanada), 10)
        self.assertTrue(
            PedidoAnticipado.objects.get(pk=self.pedido.pk).esta_pendiente
        )

    def test_un_desactivado_no_retira_su_pedido(self):
        self._no_deja_entregar(desactivar)

    def test_uno_de_baja_tampoco(self):
        self._no_deja_entregar(dar_de_baja)


class LaEntregaSeRegistraEnLaCajaTest(BaseEntrega):
    """`TT-150`. Primer criterio: **se registra en el punto de venta**."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.cajero)
        self.identificacion = reverse("identificacion-en-el-punto-de-venta")
        self.url = reverse("entrega")

    def test_al_identificar_se_ve_el_pedido_por_recoger(self):
        """Lo primero que hay que saber de alguien con un pedido es que viene a
        recogerlo. Si el cajero monta una venta sin verlo, le cobra otra vez lo
        que su acudiente ya pagó."""
        respuesta = self.client.get(
            self.identificacion, {"codigo": self.estudiante.codigo_tarjeta}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["pedidos"]), 1)
        self.assertContains(respuesta, "data-pedidos-pendientes")

    def test_sin_pedidos_no_se_dibuja_el_bloque(self):
        entregar(actor=self.cajero, pedido=self.pedido)

        respuesta = self.client.get(
            self.identificacion, {"codigo": self.estudiante.codigo_tarjeta}
        )

        self.assertNotContains(respuesta, "data-pedidos-pendientes")

    def test_entrega_desde_el_punto_de_venta(self):
        respuesta = self.client.post(self.url, {"pedido": str(self.pedido.pk)})

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-entrega-registrada")
        self.assertEqual(existencias_de(self.empanada), 8)
        self.assertEqual(saldo_de(self.estudiante), self.saldo_tras_reservar)

    def test_el_segundo_intento_llega_en_200_con_su_motivo(self):
        """htmx no intercambia lo que llega en `4xx`: la pantalla se quedaría
        igual y el cajero sin saber por qué no pasó nada."""
        self.client.post(self.url, {"pedido": str(self.pedido.pk)})

        respuesta = self.client.post(self.url, {"pedido": str(self.pedido.pk)})

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-entrega-rechazada")

    def test_un_pedido_que_no_existe_no_revienta(self):
        respuesta = self.client.post(
            self.url, {"pedido": "01999999-9999-7999-8999-999999999999"}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-entrega-rechazada")

    def test_la_entrega_arrastra_el_catalogo(self):
        """Las existencias que acaba de mover son las que el cajero va a leer en
        la siguiente venta. Si el catálogo no se repinta, vende contra la cifra
        de antes."""
        respuesta = self.client.post(self.url, {"pedido": str(self.pedido.pk)})

        self.assertTrue(respuesta.context["oob_catalogo"])
        self.assertContains(respuesta, 'hx-swap-oob')

    def test_la_administracion_no_entrega_por_la_ruta(self):
        administracion = Usuario.objects.crear_usuario(
            email="admin3@example.com", rol=Rol.ADMINISTRADOR, nombre="Administración"
        )
        self.client.force_login(administracion)

        respuesta = self.client.post(self.url, {"pedido": str(self.pedido.pk)})

        self.assertEqual(respuesta.status_code, 403)

    def test_un_anonimo_va_al_acceso(self):
        self.client.logout()

        respuesta = self.client.post(self.url, {"pedido": str(self.pedido.pk)})

        self.assertEqual(respuesta.status_code, 302)
