"""`DEC-24`, `DT-48`. Ver y cancelar los pedidos anticipados (`HU-65` … `HU-67`).

Lo que se sostiene aquí, en el orden en que importa:

1. **Cancelar devuelve el importe íntegro, una vez.** Devolver dos veces es el
   gemelo de cobrar dos veces: el libro cuadraría con el doble y ninguna
   invariante lo notaría. Lo impiden el bloqueo del servicio y una
   `UniqueConstraint`, y las dos se prueban.
2. **Toda cancelación lleva motivo**, sea quien sea, y lo impone la base.
3. **Un pedido cancelado no es venta ni consumo**: libera el cupo y sale del
   reporte de ventas, pero la auditoría y el historial del acudiente lo enseñan.
4. **Se cancela aunque el estudiante no opere**: una devolución no es una
   recarga, e `INVD-7` no la alcanza.
"""

import re
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from billetera.models import MovimientoBilletera, TipoDeMovimiento
from billetera.selectors import consumo_del_dia, saldo_de
from billetera.services import asentar, recargar
from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from personas.services import dar_de_baja, desactivar
from reportes.selectors import auditoria, historial_de_consumo, ventas_registradas
from restricciones.services import fijar_limite_diario
from ventas.models import EstadoDelPedido, PedidoAnticipado
from ventas.selectors import pedidos_de, pedidos_de_la_cafeteria
from ventas.services import (
    PedidoCancelado,
    PedidoYaEntregado,
    cancelar_pedido,
    entregar,
    registrar_venta,
    reservar,
)
from ventas.tests_reserva import familia, producto


class BaseDeCancelacion(TestCase):
    def setUp(self):
        self.acudiente, self.estudiante = familia()
        self.empanada = producto()
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero-cancela@example.com", rol=Rol.CAJERO, nombre="Diego Ramírez"
        )
        self.administracion = Usuario.objects.crear_usuario(
            email="admin-cancela@example.com", rol=Rol.ADMINISTRADOR, nombre="Administración"
        )
        self.institucion = Usuario.objects.crear_usuario(
            email="inst-cancela@example.com", rol=Rol.INSTITUCION, nombre="Secretaría"
        )
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000"))
        # 2 × 3.500 = 7.000.
        self.pedido = reservar(
            actor=self.acudiente, estudiante=self.estudiante, lineas={self.empanada.id: 2}
        )

    def cancelar(self, actor=None, motivo="Ya no lo va a recoger"):
        return cancelar_pedido(
            actor=actor or self.acudiente, pedido=self.pedido, motivo=motivo
        )

    def devoluciones(self):
        return MovimientoBilletera.objects.filter(tipo=TipoDeMovimiento.DEVOLUCION)


# --- HU-66 y HU-67: el servicio ---------------------------------------------


class CancelarDevuelveElImporteTest(BaseDeCancelacion):
    def test_el_saldo_vuelve_entero(self):
        self.assertEqual(saldo_de(self.estudiante), Decimal("43000.00"))

        self.cancelar()

        self.assertEqual(saldo_de(self.estudiante), Decimal("50000.00"))

    def test_el_pedido_dice_quien_cuando_y_por_que(self):
        cancelado = self.cancelar(motivo="  Se enfermó  ")

        cancelado.refresh_from_db()
        self.assertEqual(cancelado.estado, EstadoDelPedido.CANCELADO)
        self.assertEqual(cancelado.cancelado_por, self.acudiente)
        self.assertIsNotNone(cancelado.cancelado_en)
        self.assertEqual(cancelado.motivo_de_cancelacion, "Se enfermó")

    def test_la_devolucion_apunta_a_su_venta(self):
        """El historial de la billetera la enseña como devolución **de ese
        pedido** (`HU-66`, tercer criterio): sin la venta sería un ingreso que
        no se explica (`INV-2`)."""
        self.cancelar()

        devolucion = self.devoluciones().get()
        self.assertEqual(devolucion.venta_id, self.pedido.venta_id)
        self.assertEqual(devolucion.monto, Decimal("7000.00"))

    def test_devuelve_lo_que_se_cobro_y_no_el_precio_de_hoy(self):
        """`DT-8`: si el producto sube entre la reserva y la cancelación, se
        devuelve lo que salió de la billetera."""
        self.empanada.precio = Decimal("9000")
        self.empanada.save(update_fields=["precio"])

        self.cancelar()

        self.assertEqual(saldo_de(self.estudiante), Decimal("50000.00"))

    def test_no_toca_el_inventario(self):
        """La reserva no lo movió (`DT-33`): no hay nada que reponer."""
        from inventario.selectors import existencias_de

        self.cancelar()

        self.assertEqual(existencias_de(self.empanada), 10)


class ElMotivoEsObligatorioTest(BaseDeCancelacion):
    def test_sin_motivo_no_se_cancela_nada(self):
        for motivo in ("", "   ", None):
            with self.subTest(motivo=motivo), self.assertRaises(ValidationError):
                self.cancelar(motivo=motivo)

        self.pedido.refresh_from_db()
        self.assertTrue(self.pedido.esta_pendiente)
        self.assertFalse(self.devoluciones().exists())

    def test_tambien_para_la_cafeteria(self):
        with self.assertRaises(ValidationError):
            self.cancelar(actor=self.cajero, motivo=" ")

    def test_la_base_rechaza_un_cancelado_sin_motivo(self):
        """`DT-48`. Lo que el servicio rechaza con un mensaje, la base lo impide
        también al camino que alguien escriba mañana (`DT-15`)."""
        for motivo in ("", "   "):
            with self.subTest(motivo=motivo), self.assertRaises(IntegrityError):
                with transaction.atomic():
                    PedidoAnticipado.objects.filter(pk=self.pedido.pk).update(
                        estado=EstadoDelPedido.CANCELADO,
                        cancelado_en=timezone.now(),
                        cancelado_por=self.acudiente,
                        motivo_de_cancelacion=motivo,
                    )

    def test_la_base_rechaza_un_pedido_entregado_y_cancelado_a_la_vez(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            PedidoAnticipado.objects.filter(pk=self.pedido.pk).update(
                estado=EstadoDelPedido.ENTREGADO,
                entregado_en=timezone.now(),
                entregado_por=self.cajero,
                cancelado_en=timezone.now(),
                cancelado_por=self.cajero,
                motivo_de_cancelacion="Las dos cosas",
            )


class NoSeDevuelveDosVecesTest(BaseDeCancelacion):
    def test_lo_cancelado_no_se_cancela_otra_vez(self):
        self.cancelar()

        with self.assertRaises(PedidoCancelado):
            self.cancelar(actor=self.cajero)

        self.assertEqual(self.devoluciones().count(), 1)
        self.assertEqual(saldo_de(self.estudiante), Decimal("50000.00"))

    def test_la_base_impide_una_segunda_devolucion_de_la_misma_venta(self):
        """El gemelo de cobrar dos veces. Quitando el `if` del servicio, la
        segunda devolución **sigue fallando**, aquí."""
        self.cancelar()

        with self.assertRaises(IntegrityError), transaction.atomic():
            asentar(
                estudiante=self.estudiante,
                tipo=TipoDeMovimiento.DEVOLUCION,
                monto=Decimal("7000"),
                venta=self.pedido.venta,
            )

    def test_lo_entregado_no_se_cancela(self):
        entregar(actor=self.cajero, pedido=self.pedido)

        with self.assertRaises(PedidoYaEntregado):
            self.cancelar()

        self.assertFalse(self.devoluciones().exists())

    def test_lo_cancelado_no_se_entrega(self):
        """`HU-67`, cuarto criterio: si se entregara, el estudiante tendría el
        producto **y** el dinero."""
        self.cancelar()

        with self.assertRaises(PedidoCancelado):
            entregar(actor=self.cajero, pedido=self.pedido)


class QuienCancelaTest(BaseDeCancelacion):
    def test_el_acudiente_cancela_los_de_su_estudiante(self):
        self.cancelar(actor=self.acudiente)
        self.assertTrue(PedidoAnticipado.objects.get().esta_cancelado)

    def test_el_cajero_y_la_administracion_cancelan_cualquiera(self):
        for actor in (self.cajero, self.administracion):
            with self.subTest(rol=actor.rol), transaction.atomic():
                self.cancelar(actor=actor)
                self.assertTrue(PedidoAnticipado.objects.get().esta_cancelado)
                transaction.set_rollback(True)

    def test_otro_acudiente_no(self):
        otro, _ = familia("1009999901", email="otra-familia@example.com")

        with self.assertRaises(PermissionDenied):
            self.cancelar(actor=otro)

    def test_la_institucion_no(self):
        with self.assertRaises(PermissionDenied):
            self.cancelar(actor=self.institucion)

    def test_una_cuenta_desactivada_no(self):
        self.cajero.is_active = False
        self.cajero.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            self.cancelar(actor=self.cajero)


class SeCancelaAunqueElEstudianteNoOpereTest(BaseDeCancelacion):
    """`DEC-24`: una devolución no es una recarga, así que `INVD-7` no la alcanza.
    Es la salida del pedido pagado de quien no puede retirarlo (`INVD-2`)."""

    def test_desactivado(self):
        desactivar(actor=self.acudiente, estudiante=self.estudiante)

        self.cancelar(actor=self.cajero)

        self.assertEqual(saldo_de(self.estudiante), Decimal("50000.00"))

    def test_dado_de_baja(self):
        dar_de_baja(actor=self.institucion, estudiante=self.estudiante)

        self.cancelar(actor=self.administracion)

        self.assertEqual(saldo_de(self.estudiante), Decimal("50000.00"))

    def test_la_recarga_sigue_prohibida(self):
        """La contraprueba: lo de arriba no abrió la puerta de `INVD-7`."""
        from personas.services import EstudianteNoOperativo

        desactivar(actor=self.acudiente, estudiante=self.estudiante)

        with self.assertRaises(EstudianteNoOperativo):
            recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("1000"))


# --- Lo cancelado no es venta ni consumo -------------------------------------


class LoCanceladoNoEsVentaNiConsumoTest(BaseDeCancelacion):
    def test_libera_el_cupo_del_dia(self):
        """`HU-66`, cuarto criterio."""
        self.assertEqual(consumo_del_dia(self.estudiante), Decimal("7000.00"))

        self.cancelar()

        self.assertEqual(consumo_del_dia(self.estudiante), Decimal("0.00"))

    def test_con_el_cupo_liberado_se_vuelve_a_comprar(self):
        """La misma regla vista desde la caja: con un cupo de 8.000 y 7.000
        reservados, una compra de 3.500 no cabe; cancelada la reserva, sí."""
        fijar_limite_diario(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("8000")
        )
        self.cancelar()

        registrar_venta(
            actor=self.cajero, estudiante=self.estudiante, lineas={self.empanada.id: 1}
        )

        self.assertEqual(consumo_del_dia(self.estudiante), Decimal("3500.00"))

    def test_sale_del_reporte_de_ventas(self):
        registrar_venta(
            actor=self.cajero, estudiante=self.estudiante, lineas={self.empanada.id: 1}
        )
        self.cancelar()

        ventas = ventas_registradas(actor=self.administracion)

        self.assertEqual(ventas.count(), 1)
        self.assertNotIn(self.pedido.venta, ventas)

    def test_sale_de_la_cola_de_reservas(self):
        self.cancelar()
        self.assertEqual(pedidos_de_la_cafeteria(actor=self.cajero, filtro="por-recoger"), [])

    def test_la_auditoria_la_ensena_con_quien_y_por_que(self):
        self.cancelar(actor=self.cajero, motivo="No llegó el pan")

        operaciones, _ = auditoria(actor=self.administracion)
        cancelacion = [o for o in operaciones if o.clase == "cancelacion"]

        self.assertEqual(len(cancelacion), 1)
        self.assertEqual(cancelacion[0].quien, "Diego Ramírez")
        self.assertIn("No llegó el pan", cancelacion[0].detalle)
        self.assertEqual(cancelacion[0].importe, Decimal("7000.00"))
        # La venta sigue en su línea: se cobró de verdad.
        self.assertTrue(any(o.clase == "venta" for o in operaciones))

    def test_el_historial_del_acudiente_la_conserva(self):
        """El dinero salió y volvió: esconderla dejaría la billetera sin explicar."""
        self.cancelar()

        historial = historial_de_consumo(actor=self.acudiente, estudiante=self.estudiante)

        self.assertIn(self.pedido.venta, historial)


# --- Las pantallas -----------------------------------------------------------


class LosPedidosDelEstudianteTest(BaseDeCancelacion):
    """`HU-65`. La lista vive en la pantalla de reserva; cada fila abre su modal."""

    def setUp(self):
        super().setUp()
        self.lista = reverse("pedidos-del-estudiante", args=[self.estudiante.id])
        self.detalle = reverse("detalle-del-pedido", args=[self.estudiante.id, self.pedido.id])
        self.client.force_login(self.acudiente)

    def test_la_lista_es_un_fragmento_y_cada_fila_pide_su_detalle(self):
        respuesta = self.client.get(self.lista)

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "<html")
        self.assertContains(respuesta, 'data-pedido="pendiente"')
        self.assertContains(respuesta, self.detalle)

    def test_la_pantalla_de_reserva_la_incluye(self):
        respuesta = self.client.get(reverse("reserva", args=[self.estudiante.id]))
        self.assertContains(respuesta, self.detalle)

    def test_numera_del_mas_antiguo_y_ordena_del_mas_reciente(self):
        reservar(actor=self.acudiente, estudiante=self.estudiante, lineas={self.empanada.id: 1})

        cuerpo = self.client.get(self.lista).content.decode()

        self.assertLess(cuerpo.index("Pedido #2"), cuerpo.index("Pedido #1"))

    def test_el_detalle_de_un_cancelado_dice_quien_y_por_que(self):
        self.cancelar(actor=self.cajero, motivo="No llegó el pan")

        respuesta = self.client.get(self.detalle)

        self.assertContains(respuesta, 'data-detalle-del-pedido="cancelado"')
        cancelacion = re.search(
            r"data-cancelacion.*?</div>", respuesta.content.decode(), re.S
        ).group(0)
        self.assertIn("No llegó el pan", cancelacion)
        self.assertIn("por la cafetería", cancelacion)
        self.assertNotContains(respuesta, "data-formulario-de-cancelacion")

    def test_el_detalle_de_uno_entregado_no_ofrece_cancelar(self):
        entregar(actor=self.cajero, pedido=self.pedido)

        respuesta = self.client.get(self.detalle)

        self.assertContains(respuesta, 'data-detalle-del-pedido="entregado"')
        self.assertNotContains(respuesta, "data-formulario-de-cancelacion")

    def test_de_un_estudiante_ajeno_es_un_404(self):
        _, ajeno = familia("1009999902", email="ajena@example.com")

        respuesta = self.client.get(reverse("pedidos-del-estudiante", args=[ajeno.id]))

        self.assertEqual(respuesta.status_code, 404)

    def test_otro_rol_no_entra(self):
        self.client.force_login(self.cajero)
        self.assertEqual(self.client.get(self.lista).status_code, 403)

    def test_el_panel_enlaza_los_pedidos_aunque_el_estudiante_no_opere(self):
        """El pendiente de un desactivado es justo el que querrá cancelar."""
        desactivar(actor=self.acudiente, estudiante=self.estudiante)

        respuesta = self.client.get(
            reverse("estudiante-seleccionado", args=[self.estudiante.id])
        )

        self.assertContains(respuesta, "data-enlace-a-pedidos")
        self.assertContains(respuesta, reverse("reserva", args=[self.estudiante.id]) + "#pedidos")


class CancelarDesdeLaModalDelAcudienteTest(BaseDeCancelacion):
    """`HU-66`. La cancelación responde con la misma modal (`DT-16`)."""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            "cancelacion-por-el-acudiente", args=[self.estudiante.id, self.pedido.id]
        )
        self.client.force_login(self.acudiente)

    def test_el_detalle_ofrece_cancelar_y_dice_cuanto_vuelve(self):
        respuesta = self.client.get(
            reverse("detalle-del-pedido", args=[self.estudiante.id, self.pedido.id])
        )

        self.assertContains(respuesta, "data-formulario-de-cancelacion")
        self.assertContains(respuesta, self.url)
        self.assertEqual(respuesta.context["pedido"].total, Decimal("7000.00"))

    def test_cancelar_devuelve_la_modal_cancelada_y_avisa_a_la_lista(self):
        respuesta = self.client.post(self.url, {"motivo": "Ya no lo quiere"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "<html")
        self.assertContains(respuesta, "data-pedido-recien-cancelado")
        self.assertEqual(respuesta["HX-Trigger"], "pedidos-cambiado")
        self.assertEqual(saldo_de(self.estudiante), Decimal("50000.00"))

    def test_sin_motivo_vuelve_con_el_error_y_no_avisa(self):
        respuesta = self.client.post(self.url, {"motivo": "  "})

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-cancelacion-rechazada")
        self.assertNotIn("HX-Trigger", respuesta)
        self.assertTrue(PedidoAnticipado.objects.get().esta_pendiente)

    def test_cancelar_solo_por_post(self):
        """Un `GET` que escribe es una URL que el navegador puede repetir solo."""
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_un_pedido_de_otro_estudiante_es_un_404(self):
        """Aunque exista: el pedido se busca dentro del estudiante a cargo."""
        otro_acudiente, otro = familia("1009999903", email="otra@example.com")
        recargar(actor=otro_acudiente, estudiante=otro, monto=Decimal("10000"))
        ajeno = reservar(actor=otro_acudiente, estudiante=otro, lineas={self.empanada.id: 1})

        respuesta = self.client.post(
            reverse("cancelacion-por-el-acudiente", args=[self.estudiante.id, ajeno.id]),
            {"motivo": "No es mío"},
        )

        self.assertEqual(respuesta.status_code, 404)
        ajeno.refresh_from_db()
        self.assertTrue(ajeno.esta_pendiente)

    def test_un_pedido_ya_cerrado_responde_su_motivo_sin_tocar_nada(self):
        self.cancelar(actor=self.cajero)

        respuesta = self.client.post(self.url, {"motivo": "Otra vez"})

        self.assertContains(respuesta, "data-cancelacion-rechazada")
        self.assertEqual(self.devoluciones().count(), 1)


class CancelarDesdeLaModalDeLaCafeteriaTest(BaseDeCancelacion):
    """`HU-67`, `DT-49`. La cafetería cancela desde la modal, como el acudiente.

    Antes era una página de confirmación que redirigía a la cola (`DT-48`).
    """

    def setUp(self):
        super().setUp()
        self.url = reverse("cancelacion-por-la-cafeteria", args=[self.pedido.id])
        self.detalle = reverse("pedido-en-la-cafeteria", args=[self.pedido.id])

    def test_la_fila_abre_el_detalle_y_el_detalle_ofrece_cancelar(self):
        self.client.force_login(self.cajero)

        self.assertContains(self.client.get(reverse("reservas")), self.detalle)
        respuesta = self.client.get(self.detalle)

        self.assertNotContains(respuesta, "<html")
        self.assertContains(respuesta, "data-formulario-de-cancelacion")
        self.assertContains(respuesta, self.url)

    def test_cajero_y_administracion_cancelan_y_avisan_al_tablero(self):
        for actor in (self.cajero, self.administracion):
            with self.subTest(rol=actor.rol), transaction.atomic():
                self.client.force_login(actor)
                respuesta = self.client.post(self.url, {"motivo": "No hay pan hoy"})

                self.assertEqual(respuesta.status_code, 200)
                self.assertNotContains(respuesta, "<html")
                self.assertContains(respuesta, "data-pedido-recien-cancelado")
                self.assertEqual(respuesta["HX-Trigger"], "pedidos-cambiado")
                self.assertEqual(PedidoAnticipado.objects.get().cancelado_por, actor)
                transaction.set_rollback(True)

    def test_sin_motivo_vuelve_con_el_error_y_no_avisa(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.post(self.url, {"motivo": "  "})

        self.assertContains(respuesta, "data-cancelacion-rechazada")
        self.assertNotIn("HX-Trigger", respuesta)
        self.assertTrue(PedidoAnticipado.objects.get().esta_pendiente)

    def test_cancelar_solo_por_post(self):
        """Mueve dinero: un `GET` es una URL que el navegador puede repetir solo."""
        self.client.force_login(self.cajero)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_el_acudiente_y_la_institucion_reciben_403(self):
        for actor in (self.acudiente, self.institucion):
            with self.subTest(rol=actor.rol):
                self.client.force_login(actor)
                respuesta = self.client.post(self.url, {"motivo": "Intento"})

                self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(PedidoAnticipado.objects.get().esta_pendiente)


class LoCanceladoFueraDelListadoDeVentasTest(BaseDeCancelacion):
    """El reporte de ventas del admin no cuenta lo cancelado, pero su ficha se
    abre: la auditoría enlaza con ella (`VentaAdmin.get_object`)."""

    def setUp(self):
        super().setUp()
        sincronizar_grupos_y_permisos()
        self.cuenta_admin = crear_cuenta(
            email="reporte-cancelado@example.com",
            rol=Rol.ADMINISTRADOR,
            nombre="Administración",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.client.force_login(self.cuenta_admin)
        self.cancelar(actor=self.cajero)

    def test_no_sale_en_el_listado(self):
        respuesta = self.client.get(reverse("admin:ventas_venta_changelist"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["cl"].result_count, 0)

    def test_su_ficha_se_abre(self):
        respuesta = self.client.get(
            reverse("admin:ventas_venta_change", args=[self.pedido.venta_id])
        )

        self.assertEqual(respuesta.status_code, 200)


class LosPedidosDeUnEstudianteTest(BaseDeCancelacion):
    """El selector de `HU-65`: todos, del más reciente al más antiguo."""

    def test_trae_los_tres_estados_con_su_total(self):
        segundo = reservar(
            actor=self.acudiente, estudiante=self.estudiante, lineas={self.empanada.id: 1}
        )
        self.cancelar()

        pedidos = pedidos_de(self.estudiante)

        self.assertEqual([p.pk for p in pedidos], [segundo.pk, self.pedido.pk])
        self.assertEqual([p.total for p in pedidos], [Decimal("3500.00"), Decimal("7000.00")])
