"""`TT-143` … `TT-146`. Reserva y pago anticipado (`HU-23`).

Los tres criterios de la historia:

1. **El pedido se asocia al perfil del estudiante.** Lo lleva la `Venta`, y la
   restricción `venta_cajero_segun_su_origen` no admite una reserva sin él.
2. **Se paga en el momento de reservarse** (pago simulado). Es lo que comprueba
   `ElCobroOcurreAlReservarTest`, y es `TT-146`: el saldo baja al reservar, no
   al entregar.
3. **Se gestiona desde la aplicación del acudiente.** `LaPantallaDeReservaTest`.

**Y lo que la historia no dice, que es lo que de verdad había que asegurar.**
`HU-23` no menciona ninguna de las cuatro reglas de rechazo que construyeron los
Sprints 2 y 3 —estudiante desactivado, alérgeno bloqueado, producto bloqueado y
cupo del día—. Si la reserva tuviera su propio flujo, no se le aplicarían, y un
acudiente podría reservarle a su hijo la noche anterior lo que la caja le
rechazaría por la mañana: el control parental entero con una puerta trasera.

`LaReservaHeredaLasReglasDeLaVentaTest` las ejercita las cuatro sobre `reservar`.
Ninguna de esas pruebas mira el código: todas cobran de verdad y comprueban que
el saldo no se movió.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from billetera.models import MovimientoBilletera, TipoDeMovimiento
from billetera.selectors import saldo_de
from billetera.services import recargar
from catalogo.models import Alergeno, Categoria, Producto, ProductoAlergeno
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from personas.services import dar_de_baja, desactivar
from restricciones.services import (
    bloquear_alergeno,
    bloquear_producto,
    fijar_limite_diario,
)
from ventas.models import (
    EstadoDelPedido,
    MedioDePago,
    OrigenDeLaVenta,
    PedidoAnticipado,
    Venta,
)
from ventas.selectors import existencias_sin_reservar, unidades_reservadas_pendientes
from ventas.services import (
    AlergenoBloqueado,
    CarritoVacio,
    EstudianteNoPuedeComprar,
    ExistenciasInsuficientes,
    LimiteDiarioSuperado,
    ProductoBloqueado,
    SaldoInsuficiente,
    registrar_venta,
    reservar,
    total_de,
)

CLAVE = "clave-de-prueba-2026"


def familia(documento="1001234501", email=None):
    usuario = Usuario.objects.crear_usuario(
        email=email or f"acudiente{documento}@example.com",
        rol=Rol.ACUDIENTE,
        nombre="Marta",
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
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


class BaseReserva(TestCase):
    def setUp(self):
        self.acudiente, self.estudiante = familia()
        self.empanada = producto()
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000")
        )


# --- Criterio 2: se paga al reservarse -----------------------------------


class ElCobroOcurreAlReservarTest(BaseReserva):
    """**`TT-146`.** El saldo baja al reservar, no al entregar.

    Es el caso que da nombre a la tarea, y el que distingue una reserva de un
    apartado: un apartado no cobra hasta que se recoge.
    """

    def test_el_saldo_baja_en_el_momento_de_reservar(self):
        reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 2},
        )

        self.assertEqual(saldo_de(self.estudiante), Decimal("43000.00"))

    def test_el_cobro_queda_asentado_en_el_historial(self):
        """`INV-2`: el saldo **es** la suma de los movimientos, así que el cobro
        tiene que estar ahí y no en una columna aparte."""
        pedido = reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 2},
        )

        movimiento = MovimientoBilletera.objects.get(venta=pedido.venta)
        self.assertEqual(movimiento.tipo, TipoDeMovimiento.VENTA)
        self.assertEqual(movimiento.monto, Decimal("-7000.00"))

    def test_el_pedido_nace_pendiente_y_sin_entrega(self):
        pedido = reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 1},
        )

        self.assertEqual(pedido.estado, EstadoDelPedido.PENDIENTE)
        self.assertTrue(pedido.esta_pendiente)
        self.assertIsNone(pedido.entregado_en)
        self.assertIsNone(pedido.entregado_por)

    def test_la_reserva_no_descuenta_inventario_todavia(self):
        """`DT-33`. El libro de inventario lo mueve la entrega (`HU-25`).

        Es la mitad que hace falta sostener con `existencias_sin_reservar`: las
        unidades siguen en el libro, así que hay que apartarlas de otro modo.
        """
        reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 3},
        )

        self.assertEqual(existencias_de(self.empanada), 10)
        self.assertFalse(
            MovimientoInventario.objects.filter(
                tipo=TipoDeMovimientoDeInventario.VENTA
            ).exists()
        )

    def test_dos_reservas_descuentan_las_dos(self):
        """No hay atajo que cobre una vez por dos reservas."""
        for _ in range(2):
            reservar(
                actor=self.acudiente,
                estudiante=self.estudiante,
                lineas={self.empanada.id: 1},
            )

        self.assertEqual(saldo_de(self.estudiante), Decimal("43000.00"))
        self.assertEqual(PedidoAnticipado.objects.count(), 2)


# --- Criterio 1: el pedido se asocia al estudiante ------------------------


class ElPedidoEsDeUnEstudianteTest(BaseReserva):
    """Primer criterio, y la restricción que lo sostiene."""

    def test_la_venta_de_una_reserva_lleva_su_estudiante_y_no_lleva_cajero(self):
        pedido = reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 1},
        )

        self.assertEqual(pedido.venta.estudiante, self.estudiante)
        self.assertIsNone(pedido.venta.cajero)
        self.assertEqual(pedido.venta.origen, OrigenDeLaVenta.RESERVA)
        self.assertTrue(pedido.venta.es_reserva)

    def test_el_medio_de_pago_es_la_billetera_y_no_se_elige(self):
        """`HU-54`, `DEC-1`: hay estudiante, luego sale de su billetera.

        Una reserva en efectivo sería alguien poniendo billetes en una
        aplicación, que es lo que `ALC-OUT-01` deja fuera.
        """
        pedido = reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 1},
        )

        self.assertEqual(pedido.venta.medio_pago, MedioDePago.BILLETERA)

    def test_la_reserva_congela_el_precio_de_hoy(self):
        """`DT-8`, `HU-22`. Entre reservar y entregar puede pasar una noche, y
        lo que se cobró no lo reescribe una edición del catálogo de mañana."""
        pedido = reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 2},
        )

        self.empanada.precio = Decimal("9000")
        self.empanada.save(update_fields=["precio"])

        self.assertEqual(total_de(pedido.venta), Decimal("7000.00"))

    def test_una_venta_del_mostrador_sigue_exigiendo_cajero(self):
        """La restricción no se relajó para todos: solo la reserva va sin él."""
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Venta.objects.create(
                    cajero=None,
                    estudiante=self.estudiante,
                    medio_pago=MedioDePago.BILLETERA,
                    origen=OrigenDeLaVenta.PUNTO_DE_VENTA,
                )

    def test_una_reserva_con_cajero_tampoco_entra(self):
        from django.db import IntegrityError, transaction

        cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Venta.objects.create(
                    cajero=cajero,
                    estudiante=self.estudiante,
                    medio_pago=MedioDePago.BILLETERA,
                    origen=OrigenDeLaVenta.RESERVA,
                )


# --- Lo que la historia NO dice: las cuatro reglas heredadas --------------


class LaReservaHeredaLasReglasDeLaVentaTest(BaseReserva):
    """**El riesgo de diseño que el plan del sprint marcó en rojo.**

    Las cuatro reglas de rechazo que construyeron los Sprints 2 y 3 se aplican a
    la reserva sin que `HU-23` las mencione, porque valida por la misma función
    que el cobro del mostrador.

    Cada prueba comprueba además que **el saldo no se movió**: un rechazo que
    cobrara sería peor que no rechazar.
    """

    SIN_INDICAR = object()

    def _no_deja_reservar(self, excepcion, lineas=SIN_INDICAR):
        # El centinela y no `None`: `{}` es una entrada legítima —«no reservar
        # nada»— y un `or` la habría tratado como «no me pasaron nada».
        if lineas is self.SIN_INDICAR:
            lineas = {self.empanada.id: 1}

        antes = saldo_de(self.estudiante)

        with self.assertRaises(excepcion):
            reservar(
                actor=self.acudiente,
                estudiante=self.estudiante,
                lineas=lineas,
            )

        self.assertEqual(saldo_de(self.estudiante), antes)
        self.assertFalse(PedidoAnticipado.objects.exists())

    def test_no_se_reserva_para_un_estudiante_desactivado(self):
        """`INVD-2`, y la apuesta que el Sprint 3 dejó hecha: quien construyera
        el retiro heredaría la regla sin acordarse de ella."""
        institucion = Usuario.objects.crear_usuario(
            email="institucion@example.com", rol=Rol.INSTITUCION, nombre="Secretaría"
        )
        desactivar(actor=institucion, estudiante=self.estudiante)
        self.estudiante.refresh_from_db()

        self._no_deja_reservar(EstudianteNoPuedeComprar)

    def test_no_se_reserva_para_un_estudiante_de_baja(self):
        institucion = Usuario.objects.crear_usuario(
            email="institucion2@example.com", rol=Rol.INSTITUCION, nombre="Secretaría"
        )
        dar_de_baja(actor=institucion, estudiante=self.estudiante)
        self.estudiante.refresh_from_db()

        self._no_deja_reservar(EstudianteNoPuedeComprar)

    def test_no_se_reserva_un_producto_con_alergeno_bloqueado(self):
        """`INV-5`, `TST-1`. **La puerta trasera que este PR existe para cerrar**:
        sin esto, el acudiente no podría comprarlo en la caja pero sí reservarlo."""
        mani = Alergeno.objects.create(nombre="Maní")
        ProductoAlergeno.objects.create(producto=self.empanada, alergeno=mani)
        bloquear_alergeno(
            actor=self.acudiente, estudiante=self.estudiante, alergeno=mani
        )

        self._no_deja_reservar(AlergenoBloqueado)

    def test_no_se_reserva_un_producto_bloqueado(self):
        """`HU-10`, `HU-60`."""
        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.empanada
        )

        self._no_deja_reservar(ProductoBloqueado)

    def test_no_se_reserva_por_encima_del_cupo_del_dia(self):
        """`HU-09`, `HU-20`. El cupo lo fija el acudiente, y se aplica también a
        lo que el propio acudiente reserva."""
        fijar_limite_diario(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("5000")
        )

        self._no_deja_reservar(LimiteDiarioSuperado, lineas={self.empanada.id: 2})

    def test_no_se_reserva_sin_saldo(self):
        """`INV-1`. Ninguna venta deja saldo negativo, y una reserva es una venta.

        El producto es caro y hay de sobra: si faltaran existencias saltaría
        antes `ExistenciasInsuficientes`, que es el orden que `DT-6` fija, y esta
        prueba pasaría por el motivo equivocado.
        """
        caro = producto("Almuerzo completo", "30000", existencias=10)

        self._no_deja_reservar(SaldoInsuficiente, lineas={caro.id: 3})

    def test_no_se_reserva_lo_que_no_hay(self):
        self._no_deja_reservar(ExistenciasInsuficientes, lineas={self.empanada.id: 11})

    def test_no_se_reserva_nada(self):
        self._no_deja_reservar(CarritoVacio, lineas={})


class LaReservaApartaLoQueYaReservoTest(BaseReserva):
    """`DT-33`. Como no descuenta inventario, hay que apartarlo de otro modo.

    Sin esto, dos reservas del último paquete pasarían las dos —las existencias
    dicen «queda 1» las dos veces— y quien reservó segundo habría pagado por algo
    que no va a recibir.
    """

    def test_lo_reservado_no_se_puede_volver_a_reservar(self):
        escaso = producto("Torta", "2000", existencias=2)
        reservar(
            actor=self.acudiente, estudiante=self.estudiante, lineas={escaso.id: 2}
        )

        with self.assertRaises(ExistenciasInsuficientes):
            reservar(
                actor=self.acudiente, estudiante=self.estudiante, lineas={escaso.id: 1}
            )

    def test_las_unidades_apartadas_se_cuentan(self):
        reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 3},
        )

        self.assertEqual(
            unidades_reservadas_pendientes()[self.empanada.id], 3
        )
        self.assertEqual(existencias_sin_reservar()[self.empanada.id], 7)
        # Las existencias **reales** no cambian: `INV-3` sigue siendo la suma del
        # historial, y esto es otra cifra que se lee al lado.
        self.assertEqual(existencias_de(self.empanada), 10)

    def test_un_pedido_entregado_deja_de_apartar(self):
        """Al entregarse, las unidades salen del libro y ya no hay que apartarlas.

        La entrega es `TT-149` (`HU-25`); aquí se fija el estado a mano para
        comprobar que el selector mira el estado y no la existencia del pedido.
        """
        pedido = reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 3},
        )
        PedidoAnticipado.objects.filter(pk=pedido.pk).update(
            estado=EstadoDelPedido.ENTREGADO,
            entregado_en="2026-09-18T12:00:00Z",
            entregado_por=self.acudiente,
        )

        self.assertEqual(unidades_reservadas_pendientes(), {})
        self.assertEqual(existencias_sin_reservar()[self.empanada.id], 10)


# --- Criterio 3: se gestiona desde la aplicación del acudiente ------------


class SoloSuAcudienteReservaTest(BaseReserva):
    """`[S11]`, y la mitad que se olvida: que sean **suyos**."""

    def test_ningun_otro_rol_reserva(self):
        for rol, email in [
            (Rol.CAJERO, "cajero3@example.com"),
            (Rol.INSTITUCION, "institucion3@example.com"),
            (Rol.ADMINISTRADOR, "admin3@example.com"),
        ]:
            with self.subTest(rol=rol):
                otro = Usuario.objects.crear_usuario(
                    email=email, rol=rol, nombre="Otro"
                )
                with self.assertRaises(PermissionDenied):
                    reservar(
                        actor=otro,
                        estudiante=self.estudiante,
                        lineas={self.empanada.id: 1},
                    )

    def test_un_acudiente_no_reserva_para_el_hijo_de_otro(self):
        """Reservarle a un estudiante ajeno es pagar con la billetera propia el
        consumo de otro. La comprobación va sobre el vínculo, no sobre el rol."""
        otro_acudiente, _ = familia("1009999902", email="otra@example.com")

        with self.assertRaises(PermissionDenied):
            reservar(
                actor=otro_acudiente,
                estudiante=self.estudiante,
                lineas={self.empanada.id: 1},
            )

    def test_un_anonimo_tampoco(self):
        with self.assertRaises(PermissionDenied):
            reservar(
                actor=None,
                estudiante=self.estudiante,
                lineas={self.empanada.id: 1},
            )

    def test_una_cuenta_desactivada_no_reserva(self):
        self.acudiente.is_active = False
        self.acudiente.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            reservar(
                actor=self.acudiente,
                estudiante=self.estudiante,
                lineas={self.empanada.id: 1},
            )


class LaPantallaDeReservaTest(BaseReserva):
    """`TT-145`. Tercer criterio: se gestiona desde la aplicación del acudiente."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.acudiente)
        self.url = reverse("reserva", args=[self.estudiante.id])

    def test_el_acudiente_alcanza_la_pantalla(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "ventas/reserva.html")

    def test_reserva_desde_el_formulario(self):
        respuesta = self.client.post(
            self.url, {f"cantidad-{self.empanada.id}": "2"}, follow=True
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(saldo_de(self.estudiante), Decimal("43000.00"))
        self.assertEqual(PedidoAnticipado.objects.count(), 1)

    def test_un_rechazo_llega_en_200_con_su_motivo_dentro(self):
        """htmx no intercambia lo que llega en `4xx`, y una pantalla que no
        cambia deja a quien pulsó sin saber por qué. Es el precedente del
        repositorio: el estado de la petición y lo que hay que enseñar son dos
        preguntas distintas."""
        respuesta = self.client.post(self.url, {f"cantidad-{self.empanada.id}": "99"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-reserva-rechazada")
        self.assertFalse(PedidoAnticipado.objects.exists())

    def test_lo_que_se_escribio_se_devuelve_escrito(self):
        """Quien acaba de ver un rechazo no debería teclear otra vez lo mismo."""
        respuesta = self.client.post(self.url, {f"cantidad-{self.empanada.id}": "99"})

        pedido = [
            p for p in respuesta.context["productos"] if p.id == self.empanada.id
        ][0]
        self.assertEqual(pedido.cantidad_pedida, 99)

    def test_las_cantidades_vacias_no_entran_en_la_reserva(self):
        otro = producto("Jugo", "2000")

        self.client.post(
            self.url,
            {f"cantidad-{self.empanada.id}": "1", f"cantidad-{otro.id}": ""},
        )

        pedido = PedidoAnticipado.objects.get()
        self.assertEqual(pedido.venta.lineas.count(), 1)

    def test_la_pantalla_enseña_lo_que_queda_sin_apartar(self):
        """No ofrece lo que el servicio va a rechazar."""
        reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 4},
        )

        respuesta = self.client.get(self.url)
        pintado = [
            p for p in respuesta.context["productos"] if p.id == self.empanada.id
        ][0]

        self.assertEqual(pintado.disponibles, 6)

    def test_la_pantalla_enseña_las_reservas_pendientes(self):
        """Responde a «¿no acabo de reservar esto?», que es lo que evita la
        reserva repetida por no acordarse de la anterior."""
        reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 1},
        )

        respuesta = self.client.get(self.url)

        self.assertEqual(len(respuesta.context["pendientes"]), 1)
        self.assertContains(respuesta, "data-pedido-pendiente")

    def test_un_estudiante_ajeno_es_un_404_igual_que_uno_inexistente(self):
        """Distinguirlos confirmaría a un desconocido que ese estudiante existe."""
        _, ajeno = familia("1009999903", email="tercera@example.com")

        respuesta = self.client.get(reverse("reserva", args=[ajeno.id]))

        self.assertEqual(respuesta.status_code, 404)

    def test_un_anonimo_no_alcanza_la_pantalla(self):
        self.client.logout()

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 302)

    def test_el_panel_enlaza_la_pantalla(self):
        """Sin el enlace la pantalla es inalcanzable, y una historia que nadie
        puede usar no está terminada. Se afirma sobre un `data-*` propio."""
        respuesta = self.client.get(
            reverse("estudiante-seleccionado", args=[self.estudiante.id])
        )

        self.assertContains(respuesta, "data-enlace-a-reserva")
        self.assertContains(respuesta, self.url)
