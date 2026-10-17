"""`DT-58`. «Entregas»: la vista del cajero de `/reservas/`.

Lo que se sostiene aquí, en el orden en que importa:

1. **Entregar desde el panel no cobra otra vez.** Es el mismo servicio que el
   punto de venta (`HU-25`), y se comprueba sobre el saldo, no sobre el código.
2. **Todo es del cajero.** La administración no entrega (`[S11]`) y tiene su
   propia pantalla; el rol se comprueba antes del `404`.
3. **Un pedido que otra caja ya cerró no se vuelve a ofrecer**: el panel dice que
   ya no está y la cola se repinta, también si se adelantó entre leer y bloquear.
4. **El buscador compara la tarjeta y el documento exactos**: un documento a
   medias no puede convertirse en un listado de menores (`HU-16`).
5. **El que no puede retirar no tiene botón de entregar** (`INVD-2`), y le queda
   cancelar.
"""

import re
import uuid
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from billetera.selectors import saldo_de
from cuentas.models import Rol, Usuario
from cuentas.services import sincronizar_grupos_y_permisos
from personas.services import desactivar
from ventas.models import EstadoDelPedido
from ventas.selectors import pedidos_de_la_cafeteria
from ventas.services import PedidoYaEntregado, entregar
from ventas.tests_pedidos_de_la_cafeteria import BaseDeLaCafeteria


class BaseDeEntregas(BaseDeLaCafeteria):
    """Los cuatro pedidos de `BaseDeLaCafeteria`, con dos estudiantes que se
    distinguen por el nombre: la fábrica les pone el mismo a todos."""

    def setUp(self):
        super().setUp()
        self.estudiante_b.nombre = "Julián Amariles Pérez"
        self.estudiante_b.save(update_fields=["nombre"])

    def estado(self, pedido):
        pedido.refresh_from_db()
        return pedido.estado


class LaPantallaDelCajeroTest(BaseDeEntregas):
    def test_el_cajero_abre_entregas_sin_cifras(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.get(reverse("reservas"))

        self.assertTemplateUsed(respuesta, "ventas/entregas.html")
        self.assertContains(respuesta, "data-buscador-de-entregas")
        self.assertEqual(respuesta.content.decode().count("data-fila-de-entrega="), 2)
        self.assertNotContains(respuesta, "data-cuantas-reservas")
        self.assertNotContains(respuesta, "data-total-reservado")

    def test_lo_que_falta_por_entregar_sigue_plegado(self):
        """Es para lo que existe `HU-24`: se pliega, no se quita."""
        self.client.force_login(self.cajero)

        respuesta = self.client.get(reverse("reservas"))

        etiqueta = re.search(r"<details data-falta-por-entregar[^>]*>", respuesta.content.decode())
        self.assertIsNotNone(etiqueta)
        self.assertNotRegex(etiqueta.group(0), r"\sopen[\s>=]")

    def test_la_administracion_sigue_con_su_tablero(self):
        self.client.force_login(self.administracion)

        respuesta = self.client.get(reverse("reservas"))

        self.assertTemplateUsed(respuesta, "ventas/reservas-pendientes.html")
        self.assertNotContains(respuesta, "data-buscador-de-entregas")
        self.assertContains(respuesta, "data-total-reservado")

    def test_la_cola_es_un_fragmento_y_la_administracion_no_la_pide(self):
        self.client.force_login(self.cajero)
        fragmento = self.client.get(reverse("cola-de-entregas"))
        self.assertNotContains(fragmento, "<html")
        self.assertContains(fragmento, "data-cola-de-entregas")

        self.client.force_login(self.administracion)
        self.assertEqual(self.client.get(reverse("cola-de-entregas")).status_code, 403)


class ElBuscadorTest(BaseDeEntregas):
    def busca(self, texto):
        return [
            pedido.venta.estudiante_id
            for pedido in pedidos_de_la_cafeteria(
                actor=self.cajero, filtro="por-recoger", busqueda=texto
            )
        ]

    def test_la_tarjeta_escaneada_deja_solo_los_suyos(self):
        """En minúscula y con el salto del lector: la normalización de la caja."""
        codigo = f" {self.estudiante_b.codigo_tarjeta.lower()}\n"

        self.assertEqual(self.busca(codigo), [self.estudiante_b.pk] * 2)

    def test_el_documento_entero(self):
        self.assertEqual(self.busca(self.estudiante_b.documento), [self.estudiante_b.pk] * 2)

    def test_el_documento_a_medias_no_encuentra_a_nadie(self):
        """Si encontrara, el buscador diría a quién pertenece cada trozo de
        documento: un listado de menores por tanteo (`HU-16`)."""
        self.assertEqual(self.busca(self.estudiante_b.documento[:6]), [])

    def test_una_parte_del_nombre(self):
        self.assertEqual(self.busca("julián"), [self.estudiante_b.pk] * 2)
        self.assertEqual(self.busca("Restrepo"), [])

    def test_la_pantalla_dice_que_no_encontro_nada(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.get(reverse("cola-de-entregas"), {"q": "Nadie"})

        self.assertContains(respuesta, "data-cola-vacia")
        self.assertNotContains(respuesta, "data-fila-de-entrega=")


class ElPanelTest(BaseDeEntregas):
    def resumen(self, pedido):
        return reverse("resumen-del-pedido", args=[pedido.pk])

    def test_ensena_el_pedido_y_sus_dos_salidas(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.get(self.resumen(self.primero_por_recoger))

        self.assertNotContains(respuesta, "<html")
        self.assertContains(respuesta, f'data-panel-del-pedido="{self.primero_por_recoger.pk}"')
        self.assertContains(
            respuesta, reverse("confirmacion-de-la-entrega", args=[self.primero_por_recoger.pk])
        )
        self.assertContains(
            respuesta, reverse("confirmacion-de-la-cancelacion", args=[self.primero_por_recoger.pk])
        )

    def test_uno_ya_cerrado_no_se_ofrece_y_repinta_la_cola(self):
        """Sin enseñar cómo se cerró: ese historial no es del cajero (`HU-68`)."""
        self.client.force_login(self.cajero)

        respuesta = self.client.get(self.resumen(self.entregado))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-panel-vacio")
        self.assertNotContains(respuesta, "data-panel-del-pedido")
        self.assertEqual(respuesta["HX-Trigger"], "pedidos-cambiado")

    def test_el_rol_antes_que_el_404(self):
        self.client.force_login(self.administracion)
        inexistente = reverse("resumen-del-pedido", args=[uuid.uuid4()])

        self.assertEqual(self.client.get(inexistente).status_code, 403)
        self.assertEqual(self.client.get(self.resumen(self.primero_por_recoger)).status_code, 403)

        self.client.force_login(self.cajero)
        self.assertEqual(self.client.get(inexistente).status_code, 404)


class LaEntregaTest(BaseDeEntregas):
    def entrega(self, pedido):
        return self.client.post(reverse("entrega-en-el-panel", args=[pedido.pk]))

    def test_la_confirmacion_no_escribe_y_lleva_quien_y_que(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.get(
            reverse("confirmacion-de-la-entrega", args=[self.primero_por_recoger.pk])
        )

        self.assertContains(respuesta, "data-confirmacion-de-la-entrega")
        self.assertContains(respuesta, self.estudiante_b.nombre)
        self.assertContains(respuesta, "data-sin-foto")
        self.assertContains(
            respuesta, reverse("entrega-en-el-panel", args=[self.primero_por_recoger.pk])
        )
        self.assertContains(respuesta, "data-cierra-la-ficha")
        self.assertEqual(self.estado(self.primero_por_recoger), EstadoDelPedido.PENDIENTE)

    def test_entrega_sin_volver_a_cobrar(self):
        """`HU-25`, segundo criterio, desde el otro camino de entrega."""
        self.client.force_login(self.cajero)
        antes = saldo_de(self.estudiante_b)

        respuesta = self.entrega(self.primero_por_recoger)

        self.assertContains(respuesta, "data-pedido-recien-entregado")
        self.assertEqual(respuesta["HX-Trigger"], "pedidos-cambiado")
        self.assertEqual(self.estado(self.primero_por_recoger), EstadoDelPedido.ENTREGADO)
        self.assertEqual(saldo_de(self.estudiante_b), antes)

    def test_la_administracion_no_entrega(self):
        self.client.force_login(self.administracion)

        self.assertEqual(self.entrega(self.primero_por_recoger).status_code, 403)
        self.assertEqual(self.estado(self.primero_por_recoger), EstadoDelPedido.PENDIENTE)

    def test_si_otra_caja_se_adelanto_el_panel_no_lo_vuelve_a_ofrecer(self):
        """Entre leer el pedido y bloquearlo, otra caja lo entrega: el servicio
        lo rechaza y el panel no puede seguir pintando «Marcar como entregado»."""

        def se_adelanta(*, actor, pedido):
            entregar(actor=actor, pedido=pedido)
            raise PedidoYaEntregado("Este pedido ya se entregó. No se entrega dos veces.")

        self.client.force_login(self.cajero)
        with mock.patch("ventas.views.entregar", side_effect=se_adelanta):
            respuesta = self.entrega(self.primero_por_recoger)

        self.assertContains(respuesta, "data-entrega-rechazada")
        self.assertContains(respuesta, "data-panel-vacio")
        self.assertNotContains(respuesta, "data-entregar")
        self.assertEqual(respuesta["HX-Trigger"], "pedidos-cambiado")


class ElQueNoPuedeRetirarTest(BaseDeEntregas):
    def setUp(self):
        super().setUp()
        sincronizar_grupos_y_permisos()
        institucion = Usuario.objects.crear_usuario(
            email="secretaria-entregas@example.com", rol=Rol.INSTITUCION, nombre="Secretaría"
        )
        desactivar(actor=institucion, estudiante=self.estudiante_b)
        self.client.force_login(self.cajero)

    def test_el_panel_no_ofrece_entregar_y_deja_cancelar(self):
        """Ni un botón deshabilitado (`[S2.4]`): se dice por qué."""
        respuesta = self.client.get(
            reverse("resumen-del-pedido", args=[self.primero_por_recoger.pk])
        )

        self.assertNotContains(respuesta, "data-entregar")
        self.assertContains(respuesta, "data-no-puede-retirar")
        self.assertContains(respuesta, "data-cancelar")

    def test_y_el_post_a_mano_lo_rechaza_el_servicio(self):
        respuesta = self.client.post(
            reverse("entrega-en-el-panel", args=[self.primero_por_recoger.pk])
        )

        self.assertContains(respuesta, "data-entrega-rechazada")
        self.assertEqual(self.estado(self.primero_por_recoger), EstadoDelPedido.PENDIENTE)
        self.assertFalse(respuesta.has_header("HX-Trigger"))


class LaCancelacionTest(BaseDeEntregas):
    def cancela(self, pedido, motivo):
        return self.client.post(
            reverse("cancelacion-en-el-panel", args=[pedido.pk]), {"motivo": motivo}
        )

    def test_la_modal_pide_el_motivo_y_no_escribe(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.get(
            reverse("confirmacion-de-la-cancelacion", args=[self.primero_por_recoger.pk])
        )

        self.assertContains(respuesta, 'name="motivo"')
        self.assertContains(respuesta, "data-formulario-validado")
        self.assertContains(
            respuesta, reverse("cancelacion-en-el-panel", args=[self.primero_por_recoger.pk])
        )
        self.assertEqual(self.estado(self.primero_por_recoger), EstadoDelPedido.PENDIENTE)

    def test_cancela_y_devuelve(self):
        self.client.force_login(self.cajero)
        antes = saldo_de(self.estudiante_b)

        respuesta = self.cancela(self.primero_por_recoger, "Se acabaron las empanadas")

        self.assertContains(respuesta, "data-pedido-recien-cancelado")
        self.assertEqual(respuesta["HX-Trigger"], "pedidos-cambiado")
        self.primero_por_recoger.refresh_from_db()
        self.assertEqual(self.primero_por_recoger.estado, EstadoDelPedido.CANCELADO)
        self.assertEqual(self.primero_por_recoger.cancelado_por, self.cajero)
        self.assertEqual(saldo_de(self.estudiante_b), antes + Decimal("5500"))

    def test_sin_motivo_no_cancela(self):
        """La modal apaga el botón; si llega vacío igualmente, decide el servicio."""
        self.client.force_login(self.cajero)

        respuesta = self.cancela(self.primero_por_recoger, "   ")

        self.assertContains(respuesta, "data-entrega-rechazada")
        self.assertContains(respuesta, f'data-panel-del-pedido="{self.primero_por_recoger.pk}"')
        self.assertEqual(self.estado(self.primero_por_recoger), EstadoDelPedido.PENDIENTE)
        self.assertFalse(respuesta.has_header("HX-Trigger"))
