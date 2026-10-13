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

import re
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
        """`DT-33`. El libro de inventario lo mueve la entrega (`HU-25`)."""
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
        """`INV-1`. Ninguna venta deja saldo negativo, y una reserva es una venta."""
        caro = producto("Almuerzo completo", "30000", existencias=10)

        self._no_deja_reservar(SaldoInsuficiente, lineas={caro.id: 3})

    def test_no_se_reserva_nada(self):
        self._no_deja_reservar(CarritoVacio, lineas={})


class LaReservaEsUnEncargoTest(BaseReserva):
    """`DEC-24`, `DT-47`. La reserva no mira la vitrina: la cafetería la prepara.

    Antes validaba contra lo que quedaba sin apartar, y con el inventario a
    cero no se podía reservar nada. **Las otras cinco comprobaciones siguen**:
    las ejercita `LaReservaHeredaLasReglasDeLaVentaTest`.
    """

    def test_se_reserva_aunque_no_haya_existencias(self):
        agotado = producto("Torta", "2000", existencias=0)

        pedido = reservar(
            actor=self.acudiente, estudiante=self.estudiante, lineas={agotado.id: 3}
        )

        self.assertTrue(pedido.esta_pendiente)
        self.assertEqual(saldo_de(self.estudiante), Decimal("44000.00"))

    def test_se_reserva_mas_de_lo_que_hay(self):
        pedido = reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 11},
        )

        self.assertTrue(pedido.esta_pendiente)

    def test_lo_reservado_se_puede_volver_a_reservar(self):
        """Nada se aparta: dos encargos del mismo producto pasan los dos."""
        escaso = producto("Torta", "2000", existencias=2)
        for _ in range(2):
            reservar(
                actor=self.acudiente, estudiante=self.estudiante, lineas={escaso.id: 2}
            )

        self.assertEqual(PedidoAnticipado.objects.count(), 2)
        # El libro no se movió: lo mueve la entrega (`DT-33`).
        self.assertEqual(existencias_de(escaso), 2)

    def test_la_caja_sigue_mirando_las_existencias(self):
        """La contraprueba: solo cambió la reserva. Si `_bloquear_y_validar`
        dejara de mirar existencias para todos, esta caería y las de arriba no."""
        cajero = Usuario.objects.crear_usuario(
            email="cajero-encargo@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )

        with self.assertRaises(ExistenciasInsuficientes):
            registrar_venta(
                actor=cajero, estudiante=self.estudiante, lineas={self.empanada.id: 11}
            )


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

    def test_la_pantalla_no_limita_por_existencias(self):
        """`DT-47`. Un producto agotado se ofrece igual: ni `max`, ni campo
        deshabilitado. Se mira el `<input>` y no la copia (`[S3.6]`)."""
        agotado = producto("Torta", "2000", existencias=0)

        cuerpo = self.client.get(self.url).content.decode()
        campo = re.search(
            rf'<input[^>]*name="cantidad-{agotado.id}"[^>]*>', cuerpo
        ).group(0)

        self.assertNotIn("max=", campo)
        self.assertNotIn("disabled", campo)

    def test_la_pantalla_enseña_sus_pedidos(self):
        """Responde a «¿no acabo de reservar esto?», que es lo que evita la
        reserva repetida por no acordarse de la anterior (`HU-65`)."""
        reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 1},
        )

        respuesta = self.client.get(self.url)

        self.assertEqual(len(respuesta.context["pedidos"]), 1)
        self.assertContains(respuesta, 'data-pedido="pendiente"')

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


class LaPantallaEnsenaLaImagenDelProductoTest(BaseReserva):
    """La imagen del producto en la tarjeta de la reserva (`HU-59`, `DEC-24`).

    Sobre el marcado y por `data-*` (`[S3.6]` de `escribir-pruebas.md`). La URL
    sale de la clave, así que no hace falta almacenamiento (`[S3.7]`).
    """

    def setUp(self):
        super().setUp()
        Producto.objects.filter(pk=self.empanada.pk).update(
            imagen_clave="0123456789abcdef0123456789abcdef.webp"
        )
        self.empanada.refresh_from_db()
        self.client.force_login(self.acudiente)
        self.url = reverse("reserva", args=[self.estudiante.id])

    def test_con_imagen_la_tarjeta_la_pinta(self):
        self.assertRegex(
            self.client.get(self.url).content.decode(),
            r'<img src="' + re.escape(self.empanada.url_de_la_imagen) + r'"[^>]*data-imagen-del-producto',
        )

    def test_sin_imagen_marca_el_hueco_sin_img_vacio(self):
        Producto.objects.filter(pk=self.empanada.pk).update(imagen_clave="")
        cuerpo = self.client.get(self.url).content.decode()

        self.assertEqual(cuerpo.count("data-sin-imagen-del-producto"), 1)
        self.assertNotIn('src=""', cuerpo)

    def test_reservar_y_pagar_es_la_accion_principal(self):
        """Como «Recargar»: `bg-primario`, no el acento de los enlaces. Sale en
        el ticket en cuanto hay algo elegido y el saldo alcanza."""
        ticket = self.client.get(
            reverse("ticket-de-la-reserva", args=[self.estudiante.id]),
            {f"cantidad-{self.empanada.id}": "1"},
        ).content.decode()
        boton = re.search(r"<button[^>]*data-reservar[^>]*>", ticket).group(0)

        self.assertIn("bg-primario", boton)
        self.assertNotIn("bg-acento", boton)


class ElTicketDeLaReservaTest(BaseReserva):
    """`DEC-24`. El ticket lo calcula y lo formatea el servidor a cada cambio.

    Saldo de partida: 50.000. La empanada cuesta 3.500.
    """

    def setUp(self):
        super().setUp()
        self.client.force_login(self.acudiente)
        self.url = reverse("ticket-de-la-reserva", args=[self.estudiante.id])

    def _ticket(self, **cantidades):
        return self.client.get(
            self.url, {f"cantidad-{k}": v for k, v in cantidades.items()}
        )

    def test_es_un_fragmento_con_el_total_y_el_saldo_despues(self):
        respuesta = self._ticket(**{str(self.empanada.id): "3"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "<html")
        resumen = respuesta.context["resumen"]
        self.assertEqual(resumen.total, Decimal("10500.00"))
        self.assertEqual(resumen.saldo_despues, Decimal("39500.00"))
        self.assertContains(respuesta, "data-linea-de-la-reserva", count=1)

    def test_vacio_no_ofrece_reservar(self):
        """Un hueco nunca es un botón deshabilitado (`[S2.4]`)."""
        respuesta = self._ticket()

        self.assertNotContains(respuesta, "data-reservar")
        self.assertEqual(respuesta.context["resumen"].lineas, ())

    def test_lo_que_no_es_un_entero_o_no_es_de_ningun_producto_se_ignora(self):
        respuesta = self.client.get(
            self.url,
            {
                f"cantidad-{self.empanada.id}": "dos",
                "cantidad-no-es-un-uuid": "4",
                "cantidad-0123e456-e89b-12d3-a456-426614174000": "4",
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["resumen"].lineas, ())

    def test_si_no_alcanza_dice_cuanto_falta_y_no_ofrece_reservar(self):
        """`INV-1`. Se dice antes de enviar; quien rechaza sigue siendo el servicio."""
        caro = producto("Almuerzo completo", "30000")

        respuesta = self._ticket(**{str(caro.id): "2"})

        self.assertContains(respuesta, "data-no-alcanza")
        self.assertNotContains(respuesta, "data-reservar")
        self.assertEqual(respuesta.context["resumen"].faltan, Decimal("10000.00"))
        self.assertContains(respuesta, reverse("recarga", args=[self.estudiante.id]))

    def test_si_supera_el_cupo_lo_dice_y_no_ofrece_reservar(self):
        """`HU-20`: la reserva cuenta en el cupo del día."""
        fijar_limite_diario(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("5000")
        )

        respuesta = self._ticket(**{str(self.empanada.id): "2"})

        self.assertContains(respuesta, "data-supera-el-cupo")
        self.assertNotContains(respuesta, "data-reservar")

    def test_de_un_estudiante_ajeno_es_un_404(self):
        _, ajeno = familia("1009999960", email="ajena-ticket@example.com")

        respuesta = self.client.get(reverse("ticket-de-la-reserva", args=[ajeno.id]))

        self.assertEqual(respuesta.status_code, 404)


class LasTarjetasAvisanDeLoBloqueadoTest(BaseReserva):
    """`HU-10`, `HU-11`. La tarjeta dice **antes** de añadir que no se podrá.

    Es aviso, no autorización: la que rechaza es `reservar`, y sus pruebas
    están en `LaReservaHeredaLasReglasDeLaVentaTest`.
    """

    def setUp(self):
        super().setUp()
        self.client.force_login(self.acudiente)
        self.url = reverse("reserva", args=[self.estudiante.id])

    def _tarjeta(self, articulo):
        cuerpo = self.client.get(self.url).content.decode()
        inicio = cuerpo.index(f'data-tarjeta-de-producto="{articulo.id}"')
        return cuerpo[inicio : cuerpo.index("</li>", inicio)]

    def test_un_producto_bloqueado_no_tiene_cantidad_que_elegir(self):
        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.empanada
        )

        tarjeta = self._tarjeta(self.empanada)

        self.assertIn("data-no-reservable", tarjeta)
        self.assertNotIn(f'name="cantidad-{self.empanada.id}"', tarjeta)

    def test_un_alergeno_bloqueado_se_nombra_en_la_tarjeta(self):
        mani, _ = Alergeno.objects.get_or_create(nombre="Maní")
        ProductoAlergeno.objects.create(producto=self.empanada, alergeno=mani)
        bloquear_alergeno(actor=self.acudiente, estudiante=self.estudiante, alergeno=mani)

        tarjeta = self._tarjeta(self.empanada)

        self.assertIn("data-aviso-de-restriccion", tarjeta)
        self.assertIn("maní", tarjeta)
        self.assertIn("data-no-reservable", tarjeta)

    def test_la_contraprueba_un_producto_libre_se_puede_agregar(self):
        tarjeta = self._tarjeta(self.empanada)

        self.assertIn("data-agregar", tarjeta)
        self.assertNotIn("data-no-reservable", tarjeta)

    def test_lleva_lo_que_filtra_el_navegador_sin_formato(self):
        """El precio como número —`3500.00`, no «$3.500»— para comparar."""
        tarjeta = self._tarjeta(self.empanada)

        self.assertIn('data-precio="3500.00"', tarjeta)
        self.assertIn(f'data-categoria="{self.empanada.categoria_id}"', tarjeta)

    def test_tras_un_rechazo_las_cantidades_siguen_elegidas(self):
        caro = producto("Almuerzo completo", "30000")

        cuerpo = self.client.post(self.url, {f"cantidad-{caro.id}": "2"}).content.decode()

        self.assertIn("data-reserva-rechazada", cuerpo)
        self.assertRegex(cuerpo, rf'name="cantidad-{caro.id}"\s+value="2"')


class LaFichaDelProductoTest(BaseReserva):
    """«Detalle»: la ficha nutricional en la modal (`DEC-24`)."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.acudiente)

    def test_es_un_fragmento_con_lo_que_declara(self):
        Producto.objects.filter(pk=self.empanada.pk).update(energia_kcal=290)

        respuesta = self.client.get(
            reverse("detalle-del-producto", args=[self.estudiante.id, self.empanada.id])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "<html")
        self.assertContains(respuesta, "data-detalle-del-producto")
        self.assertContains(respuesta, "290 kcal")

    def test_un_alergeno_bloqueado_se_marca(self):
        mani, _ = Alergeno.objects.get_or_create(nombre="Maní")
        ProductoAlergeno.objects.create(producto=self.empanada, alergeno=mani)
        bloquear_alergeno(actor=self.acudiente, estudiante=self.estudiante, alergeno=mani)

        respuesta = self.client.get(
            reverse("detalle-del-producto", args=[self.estudiante.id, self.empanada.id])
        )

        self.assertContains(respuesta, "data-alergeno-bloqueado", count=1)

    def test_un_producto_retirado_es_un_404(self):
        Producto.objects.filter(pk=self.empanada.pk).update(activo=False)

        respuesta = self.client.get(
            reverse("detalle-del-producto", args=[self.estudiante.id, self.empanada.id])
        )

        self.assertEqual(respuesta.status_code, 404)


class QuienNoOperaVeSusPedidosTest(BaseReserva):
    """`INVD-2`: no reserva, pero sus pedidos siguen en la pantalla (`DEC-24`)."""

    def test_sin_catalogo_y_con_sus_pedidos(self):
        reservar(actor=self.acudiente, estudiante=self.estudiante, lineas={self.empanada.id: 1})
        desactivar(actor=self.acudiente, estudiante=self.estudiante)
        self.client.force_login(self.acudiente)

        respuesta = self.client.get(reverse("reserva", args=[self.estudiante.id]))

        self.assertContains(respuesta, "data-no-puede-reservar")
        self.assertNotContains(respuesta, "data-formulario-de-reserva")
        self.assertContains(respuesta, 'data-pedido="pendiente"')
