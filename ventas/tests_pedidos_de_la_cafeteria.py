"""`HU-68`, `DT-49`. Los pedidos anticipados vistos desde la cafetería.

Lo que se sostiene aquí, en el orden en que importa:

1. **El cajero solo ve lo que está por recoger.** Lo entregado y lo cancelado
   es un reporte de ventas, y `[S11]` se lo da a la administración sola. Se
   prueba en el selector, en la pantalla y en la modal: una URL escrita a mano
   no puede alcanzar lo que la pestaña no enseña.
2. **El número de un pedido es el mismo que ve el acudiente**: cuenta entre los
   pedidos de su estudiante, y no cambia al filtrar.
3. **Lo reservado no cuenta lo cancelado**, que volvió a la billetera (`DEC-24`).
4. **Lo que falta por entregar suma los pedidos por recoger** producto por
   producto, que es para lo que existe `HU-24`.
"""

import re
import uuid
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from billetera.services import recargar
from cuentas.models import Rol, Usuario
from ventas.selectors import pedido_de_la_cafeteria, pedidos_de, pedidos_de_la_cafeteria, tablero_de_reservas
from ventas.services import cancelar_pedido, entregar, reservar
from ventas.tests_reserva import familia, producto


class BaseDeLaCafeteria(TestCase):
    """Cuatro pedidos de dos familias, uno en cada situación posible.

    Por orden de creación: el primero de A se entrega, el primero de B espera,
    el segundo de A se cancela y el segundo de B espera.
    """

    def setUp(self):
        self.empanada = producto()
        self.jugo = producto(nombre="Jugo de mora", precio="2000")
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero-tablero@example.com", rol=Rol.CAJERO, nombre="Diego Ramírez"
        )
        self.administracion = Usuario.objects.crear_usuario(
            email="admin-tablero@example.com", rol=Rol.ADMINISTRADOR, nombre="Lucía Gómez"
        )
        self.acudiente_a, self.estudiante_a = familia("1002000001")
        self.acudiente_b, self.estudiante_b = familia("1002000002")
        for acudiente, estudiante in (
            (self.acudiente_a, self.estudiante_a),
            (self.acudiente_b, self.estudiante_b),
        ):
            recargar(actor=acudiente, estudiante=estudiante, monto=Decimal("50000"))

        # 2 × 3.500 = 7.000, entregado.
        self.entregado = self._reserva(self.acudiente_a, self.estudiante_a, {self.empanada.id: 2})
        # 3.500 + 2.000 = 5.500, por recoger.
        self.primero_por_recoger = self._reserva(
            self.acudiente_b, self.estudiante_b, {self.empanada.id: 1, self.jugo.id: 1}
        )
        # 2.000, cancelado: vuelve a la billetera.
        self.cancelado = self._reserva(self.acudiente_a, self.estudiante_a, {self.jugo.id: 1})
        # 3 × 3.500 = 10.500, por recoger.
        self.segundo_por_recoger = self._reserva(
            self.acudiente_b, self.estudiante_b, {self.empanada.id: 3}
        )

        entregar(actor=self.cajero, pedido=self.entregado)
        cancelar_pedido(
            actor=self.administracion, pedido=self.cancelado, motivo="No llegó el jugo"
        )

    def _reserva(self, acudiente, estudiante, lineas):
        return reservar(actor=acudiente, estudiante=estudiante, lineas=lineas)

    def ids(self, pedidos):
        return [pedido.pk for pedido in pedidos]


class LaAdministracionLosVeTodosTest(BaseDeLaCafeteria):
    def test_todos_del_mas_reciente_al_mas_antiguo(self):
        """«Todos» es un historial y se lee empezando por lo último."""
        pedidos = pedidos_de_la_cafeteria(actor=self.administracion, filtro="todos")

        self.assertEqual(
            self.ids(pedidos),
            [
                self.segundo_por_recoger.pk,
                self.cancelado.pk,
                self.primero_por_recoger.pk,
                self.entregado.pk,
            ],
        )

    def test_cada_filtro_trae_su_estado(self):
        def filtrados(filtro):
            return self.ids(pedidos_de_la_cafeteria(actor=self.administracion, filtro=filtro))

        self.assertEqual(filtrados("entregados"), [self.entregado.pk])
        self.assertEqual(filtrados("cancelados"), [self.cancelado.pk])

    def test_lo_por_recoger_sigue_siendo_una_cola(self):
        """Del más antiguo al más reciente, al revés que el resto (`HU-24`)."""
        pedidos = pedidos_de_la_cafeteria(actor=self.administracion, filtro="por-recoger")

        self.assertEqual(
            self.ids(pedidos), [self.primero_por_recoger.pk, self.segundo_por_recoger.pk]
        )

    def test_un_filtro_que_no_existe_no_trae_nada(self):
        with self.assertRaises(ValueError):
            pedidos_de_la_cafeteria(actor=self.administracion, filtro="pendientes")

    def test_la_lista_no_hace_una_consulta_por_pedido(self):
        """El estudiante, quién canceló y las líneas ya vienen traídos."""
        with self.assertNumQueries(3):
            for pedido in pedidos_de_la_cafeteria(actor=self.administracion, filtro="todos"):
                pedido.venta.estudiante.nombre
                pedido.cancelado_por
                list(pedido.venta.lineas.all())


class ElNumeroEsElDelAcudienteTest(BaseDeLaCafeteria):
    def test_cuenta_dentro_del_estudiante_como_en_su_pantalla(self):
        """Una llamada sobre «el pedido 2» tiene que hablar del mismo pedido."""
        del_acudiente = {p.pk: p.numero for p in pedidos_de(self.estudiante_a)}
        de_la_cafeteria = {
            p.pk: p.numero
            for p in pedidos_de_la_cafeteria(actor=self.administracion, filtro="todos")
            if p.venta.estudiante_id == self.estudiante_a.id
        }

        self.assertEqual(de_la_cafeteria, del_acudiente)
        self.assertEqual(de_la_cafeteria[self.cancelado.pk], 2)

    def test_no_cambia_al_filtrar(self):
        """Contar sobre lo que se enseña renumeraría al cambiar de pestaña."""
        (cancelado,) = pedidos_de_la_cafeteria(actor=self.administracion, filtro="cancelados")
        (segundo,) = [
            p
            for p in pedidos_de_la_cafeteria(actor=self.administracion, filtro="por-recoger")
            if p.pk == self.segundo_por_recoger.pk
        ]

        self.assertEqual(cancelado.numero, 2)
        self.assertEqual(segundo.numero, 2)


class ElCajeroSoloVeLoPorRecogerTest(BaseDeLaCafeteria):
    """`[S11]`: el historial de pedidos es un reporte de ventas."""

    def test_el_selector_le_niega_lo_cerrado(self):
        for filtro in ("todos", "entregados", "cancelados"):
            with self.subTest(filtro=filtro), self.assertRaises(PermissionDenied):
                pedidos_de_la_cafeteria(actor=self.cajero, filtro=filtro)

    def test_y_le_da_lo_por_recoger(self):
        """La contraprueba: la regla no le cierra la cola de `HU-24`."""
        pedidos = pedidos_de_la_cafeteria(actor=self.cajero, filtro="por-recoger")

        self.assertEqual(len(pedidos), 2)

    def test_tampoco_abre_un_pedido_cerrado_por_su_identificador(self):
        for pedido in (self.entregado, self.cancelado):
            with self.subTest(estado=pedido.estado), self.assertRaises(PermissionDenied):
                pedido_de_la_cafeteria(actor=self.cajero, pedido_id=pedido.pk)

        abierto = pedido_de_la_cafeteria(actor=self.cajero, pedido_id=self.primero_por_recoger.pk)
        self.assertEqual(abierto.pk, self.primero_por_recoger.pk)


class ElTableroTest(BaseDeLaCafeteria):
    def test_las_cifras_de_la_administracion(self):
        tablero = tablero_de_reservas(actor=self.administracion)

        self.assertEqual(tablero.pedidos, 4)
        self.assertEqual(tablero.por_recoger, 2)
        # 7.000 entregado + 5.500 + 10.500 por recoger. Los 2.000 cancelados volvieron.
        self.assertEqual(tablero.reservado, Decimal("23000.00"))

    def test_lo_que_falta_por_entregar_suma_por_producto(self):
        """Lo que hay que tener preparado: 1 + 3 empanadas y 1 jugo. Ni la
        entregada ni el jugo cancelado cuentan."""
        tablero = tablero_de_reservas(actor=self.administracion)

        self.assertEqual(
            [(f["nombre"], f["unidades"], f["porcentaje"]) for f in tablero.falta_por_entregar],
            [("Empanada", 4, 100), ("Jugo de mora", 1, 25)],
        )

    def test_el_cajero_tiene_lo_que_falta_y_no_el_historial(self):
        tablero = tablero_de_reservas(actor=self.cajero)

        self.assertEqual(tablero.por_recoger, 2)
        self.assertEqual(len(tablero.falta_por_entregar), 2)
        self.assertIsNone(tablero.pedidos)
        self.assertIsNone(tablero.reservado)

    def test_sin_nada_por_recoger_no_falta_nada(self):
        for pedido in (self.primero_por_recoger, self.segundo_por_recoger):
            cancelar_pedido(actor=self.cajero, pedido=pedido, motivo="Cierre del colegio")

        tablero = tablero_de_reservas(actor=self.cajero)

        self.assertEqual(tablero.por_recoger, 0)
        self.assertEqual(tablero.falta_por_entregar, [])


class LaPantallaTest(BaseDeLaCafeteria):
    def setUp(self):
        super().setUp()
        self.url = reverse("reservas")

    def test_la_administracion_abre_todos_con_las_cuatro_pestanas(self):
        self.client.force_login(self.administracion)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.context["filtro"], "todos")
        self.assertEqual(respuesta.content.decode().count("data-filtro-de-pedidos="), 4)
        self.assertContains(respuesta, "data-total-reservado")
        for pedido in (self.entregado, self.cancelado, self.primero_por_recoger):
            self.assertContains(respuesta, reverse("pedido-en-la-cafeteria", args=[pedido.pk]))

    def test_el_filtro_viaja_en_la_url(self):
        self.client.force_login(self.administracion)

        respuesta = self.client.get(self.url, {"ver": "cancelados"})

        self.assertEqual(self.ids(respuesta.context["pedidos"]), [self.cancelado.pk])
        self.assertRegex(
            respuesta.content.decode(), r'data-filtro-de-pedidos="cancelados"\s+aria-current="page"'
        )

    def test_el_cajero_abre_lo_por_recoger_sin_pestanas_ni_historial(self):
        """Su vista es «Entregas» (`DT-58`), y lo que no ve sigue sin verlo."""
        self.client.force_login(self.cajero)

        respuesta = self.client.get(self.url)

        self.assertEqual(len(respuesta.context["pedidos"]), 2)
        self.assertNotContains(respuesta, "data-filtro-de-pedidos")
        self.assertNotContains(respuesta, "data-total-reservado")
        self.assertContains(respuesta, "data-falta-por-entregar")

    def test_el_cajero_no_alcanza_el_historial_escribiendo_la_url(self):
        self.client.force_login(self.cajero)

        for filtro in ("todos", "entregados", "cancelados"):
            with self.subTest(filtro=filtro):
                self.assertEqual(self.client.get(self.url, {"ver": filtro}).status_code, 403)

    def test_un_filtro_que_no_existe_es_un_404(self):
        """No la pestaña por defecto: una URL mal escrita que enseña otra cosa
        es peor que un error."""
        self.client.force_login(self.administracion)

        self.assertEqual(self.client.get(self.url, {"ver": "pendientes"}).status_code, 404)

    def test_el_tablero_se_repinta_solo_y_es_un_fragmento(self):
        """La página lo vuelve a pedir, con su filtro, cuando la modal cancela."""
        self.client.force_login(self.administracion)
        tablero = reverse("tablero-de-reservas") + "?ver=entregados"

        pagina = self.client.get(self.url, {"ver": "entregados"})
        fragmento = self.client.get(tablero)

        self.assertContains(pagina, f'hx-get="{tablero}" hx-trigger="pedidos-cambiado from:body"')
        self.assertNotContains(fragmento, "<html")
        self.assertContains(fragmento, "data-reserva")


class LaModalDeLaCafeteriaTest(BaseDeLaCafeteria):
    def detalle(self, pedido):
        return reverse("pedido-en-la-cafeteria", args=[pedido.pk])

    def bloque_de_cancelacion(self, respuesta):
        return re.search(r"data-cancelacion.*?</div>", respuesta.content.decode(), re.S).group(0)

    def test_el_cancelado_dice_quien_de_la_casa_lo_cancelo_y_por_que(self):
        self.client.force_login(self.administracion)

        respuesta = self.client.get(self.detalle(self.cancelado))

        self.assertContains(respuesta, 'data-detalle-del-pedido="cancelado"')
        bloque = self.bloque_de_cancelacion(respuesta)
        self.assertIn("Lucía Gómez", bloque)
        self.assertIn("No llegó el jugo", bloque)
        self.assertNotContains(respuesta, "data-formulario-de-cancelacion")

    def test_si_lo_cancelo_la_familia_no_da_su_nombre(self):
        """A la cafetería le basta saber que fue el acudiente."""
        cancelar_pedido(
            actor=self.acudiente_b, pedido=self.primero_por_recoger, motivo="Está enfermo"
        )
        self.client.force_login(self.administracion)

        bloque = self.bloque_de_cancelacion(self.client.get(self.detalle(self.primero_por_recoger)))

        self.assertIn("Está enfermo", bloque)
        self.assertNotIn(self.acudiente_b.nombre, bloque)

    def test_el_por_recoger_ofrece_cancelar_hacia_la_cafeteria(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.get(self.detalle(self.primero_por_recoger))

        self.assertContains(respuesta, "data-formulario-de-cancelacion")
        self.assertContains(
            respuesta,
            reverse("cancelacion-por-la-cafeteria", args=[self.primero_por_recoger.pk]),
        )

    def test_el_cajero_no_abre_uno_cerrado(self):
        self.client.force_login(self.cajero)

        self.assertEqual(self.client.get(self.detalle(self.entregado)).status_code, 403)

    def test_un_pedido_que_no_existe_es_un_404(self):
        self.client.force_login(self.administracion)

        respuesta = self.client.get(reverse("pedido-en-la-cafeteria", args=[uuid.uuid4()]))

        self.assertEqual(respuesta.status_code, 404)
