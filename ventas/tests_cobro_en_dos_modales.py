"""`DT-57`. El catálogo con foto y el cobro en dos modales, en el punto de venta.

Lo que estas pruebas fijan:

1. **La tarjeta y el ticket cambian juntos.** Cada gesto sobre el carrito
   devuelve el ticket y, fuera de banda, la tarjeta del producto tocado:
   «Añadir» o «− n +». Si no viajara, el catálogo diría una cosa y el ticket otra.
2. **La primera modal no escribe nada.** Cerrarla es no cobrar.
3. **El dinero recibido es una calculadora**: la devuelta la calcula el servidor
   y no se guarda. La de la segunda modal se calcula contra lo que se cobró de
   verdad, no contra el total estimado.
4. **El medio no lo elige el navegador**: con estudiante es la billetera
   (`HU-54`), aunque llegue otro.
5. **Enter en el campo no cobra**: lo sostiene `interfaz.js`, y aquí se vigila
   que la pieza siga en su sitio y que la plantilla lleve sus marcadores.
"""

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from billetera.selectors import saldo_de
from billetera.services import recargar
from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from ventas.models import Venta
from ventas.tests_carrito import producto


class BaseDelCobro(TestCase):
    def setUp(self):
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero-modales@example.com", rol=Rol.CAJERO, nombre="Diego Ramírez"
        )
        self.client.force_login(self.cajero)
        self.empanada = producto()                                    # $3.500, 10 unidades
        self.gaseosa = producto(nombre="Gaseosa", precio="2500", existencias=4)
        self.carrito = reverse("carrito-del-punto-de-venta")
        self.confirmacion = reverse("confirmacion-del-cobro")
        self.devuelta = reverse("devuelta-del-cobro")
        self.cobrar = reverse("cobrar")

    def anadir(self, articulo, veces=1):
        for _ in range(veces):
            respuesta = self.client.post(self.carrito, {"producto": str(articulo.id), "accion": "anadir"})
        return respuesta

    def identificar_estudiante(self, saldo="50000"):
        acudiente = Usuario.objects.crear_usuario(
            email="acudiente-modales@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
        )
        ficha = Acudiente.objects.create(usuario=acudiente, nombre="Marta Ruiz", documento="4310077001")
        estudiante = Estudiante.objects.create(
            nombre="Ana Sofía Restrepo", documento="1001077001", acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        if saldo:
            recargar(actor=acudiente, estudiante=estudiante, monto=Decimal(saldo))
        self.client.get(
            reverse("identificacion-en-el-punto-de-venta"), {"codigo": estudiante.codigo_tarjeta}
        )
        return estudiante


class LaTarjetaYElTicketCambianJuntosTest(BaseDelCobro):
    def test_sin_el_producto_en_la_venta_la_tarjeta_ofrece_anadir(self):
        cuerpo = self.client.get(reverse("punto-de-venta")).content.decode()

        self.assertIn(f'id="tarjeta-del-producto-{self.empanada.id}"', cuerpo)
        self.assertIn("data-producto-del-catalogo", cuerpo)
        self.assertNotIn("data-contador-del-punto-de-venta", cuerpo)

    def test_anadir_devuelve_el_ticket_y_la_tarjeta_con_su_contador(self):
        cuerpo = self.anadir(self.empanada, veces=2).content.decode()

        self.assertIn('data-linea-de-venta', cuerpo)
        self.assertIn(f'id="tarjeta-del-producto-{self.empanada.id}"', cuerpo)
        self.assertIn('hx-swap-oob="true"', cuerpo)
        self.assertIn("data-contador-del-punto-de-venta", cuerpo)
        self.assertIn(">2</span>", cuerpo)
        # Solo esa tarjeta: el catálogo entero costaría el doble en cada toque.
        self.assertNotIn(f'id="tarjeta-del-producto-{self.gaseosa.id}"', cuerpo)

    def test_al_llegar_a_cero_la_tarjeta_vuelve_a_anadir(self):
        self.anadir(self.empanada)

        cuerpo = self.client.post(
            self.carrito, {"producto": str(self.empanada.id), "accion": "descontar"}
        ).content.decode()

        self.assertIn(f'id="tarjeta-del-producto-{self.empanada.id}"', cuerpo)
        self.assertIn("data-producto-del-catalogo", cuerpo)
        self.assertNotIn("data-contador-del-punto-de-venta", cuerpo)

    def test_vaciar_repinta_el_catalogo_entero(self):
        self.anadir(self.empanada)
        self.anadir(self.gaseosa)

        cuerpo = self.client.post(self.carrito, {"accion": "vaciar"}).content.decode()

        self.assertIn('id="catalogo-de-venta"', cuerpo)
        self.assertNotIn("data-contador-del-punto-de-venta", cuerpo)

    def test_la_foto_si_la_hay_y_el_hueco_si_no(self):
        self.empanada.imagen_clave = "0" * 32 + ".webp"
        self.empanada.save(update_fields=["imagen_clave"])

        cuerpo = self.client.get(reverse("punto-de-venta")).content.decode()

        self.assertIn(f'src="{self.empanada.url_de_la_imagen}"', cuerpo)
        self.assertIn("data-sin-imagen-del-producto", cuerpo)  # la gaseosa


class LaPrimeraModalNoEscribeNadaTest(BaseDelCobro):
    def test_en_efectivo_lleva_la_calculadora(self):
        self.anadir(self.empanada, veces=2)

        respuesta = self.client.get(self.confirmacion, {"medio_pago": "efectivo"})

        self.assertContains(respuesta, 'data-medio="efectivo"')
        self.assertContains(respuesta, "data-dinero-recibido")
        self.assertContains(respuesta, 'data-total-estimado>$7.000 COP<')
        self.assertContains(respuesta, "Cliente genérico")
        self.assertNotContains(respuesta, "<html")
        self.assertEqual(Venta.objects.count(), 0)

    def test_en_efectivo_el_foco_nace_en_el_campo_y_no_en_cobrar(self):
        """Si naciera en «Cobrar», una tarjeta pasada por error con la modal
        abierta cobraría con su Enter. En el campo, Enter solo mueve el foco."""
        self.anadir(self.empanada)

        respuesta = self.client.get(self.confirmacion, {"medio_pago": "efectivo"})

        self.assertContains(respuesta, "autofocus data-dinero-recibido")
        self.assertNotContains(respuesta, "data-confirmar-cobro autofocus")

    def test_en_transferencia_no_y_el_foco_nace_en_cobrar(self):
        self.anadir(self.empanada)

        respuesta = self.client.get(self.confirmacion, {"medio_pago": "transferencia"})

        self.assertContains(respuesta, 'data-medio="transferencia"')
        self.assertNotContains(respuesta, "data-dinero-recibido")
        self.assertContains(respuesta, "data-confirmar-cobro autofocus")

    def test_con_estudiante_es_la_billetera_aunque_llegue_otro_medio(self):
        estudiante = self.identificar_estudiante()
        self.anadir(self.empanada)

        respuesta = self.client.get(self.confirmacion, {"medio_pago": "efectivo"})

        self.assertContains(respuesta, 'data-medio="billetera"')
        self.assertContains(respuesta, estudiante.nombre)
        self.assertNotContains(respuesta, "data-dinero-recibido")

    def test_un_medio_inventado_es_efectivo(self):
        self.anadir(self.empanada)

        self.assertContains(self.client.get(self.confirmacion, {"medio_pago": "cripto"}), 'data-medio="efectivo"')

    def test_sin_nada_en_la_venta_no_ofrece_cobrar(self):
        respuesta = self.client.get(self.confirmacion)

        self.assertContains(respuesta, "data-nada-que-cobrar")
        self.assertNotContains(respuesta, "data-confirmar-cobro")


class LaCalculadoraDeLaDevueltaTest(BaseDelCobro):
    def setUp(self):
        super().setUp()
        self.anadir(self.empanada, veces=2)  # $7.000

    def test_sobra(self):
        respuesta = self.client.get(self.devuelta, {"recibido": "20.000"})

        self.assertContains(respuesta, "data-devuelta")
        self.assertContains(respuesta, "$13.000")

    def test_falta(self):
        respuesta = self.client.get(self.devuelta, {"recibido": "5000"})

        self.assertContains(respuesta, "data-faltan")
        self.assertContains(respuesta, "$2.000")

    def test_justo_es_devuelta_cero_y_no_faltan_cero(self):
        respuesta = self.client.get(self.devuelta, {"recibido": "7000"})

        self.assertContains(respuesta, "data-devuelta")
        self.assertNotContains(respuesta, "data-faltan")

    def test_vacio_no_dice_nada(self):
        respuesta = self.client.get(self.devuelta, {"recibido": ""})

        self.assertNotContains(respuesta, "data-devuelta")
        self.assertNotContains(respuesta, "data-faltan")


class LaSegundaModalDiceLoQueSeCobroTest(BaseDelCobro):
    def test_en_efectivo_con_su_devuelta_y_sin_guardar_lo_recibido(self):
        self.anadir(self.empanada, veces=2)

        respuesta = self.client.post(self.cobrar, {"medio_pago": "efectivo", "recibido": "10000"})

        self.assertContains(respuesta, "data-venta-registrada")
        self.assertContains(respuesta, 'data-total-cobrado>$7.000 COP<')
        self.assertContains(respuesta, "$3.000")  # la devuelta
        venta = Venta.objects.get()
        self.assertNotIn("recibido", {campo.name for campo in Venta._meta.get_fields()})
        self.assertEqual(venta.medio_pago, "efectivo")

    def test_la_devuelta_es_contra_lo_cobrado_y_no_contra_lo_estimado(self):
        """El precio cambió entre las dos modales: manda el del momento del cobro."""
        self.anadir(self.empanada, veces=2)
        self.client.get(self.confirmacion, {"medio_pago": "efectivo"})
        self.empanada.precio = Decimal("4000")
        self.empanada.save(update_fields=["precio"])

        respuesta = self.client.post(self.cobrar, {"medio_pago": "efectivo", "recibido": "10000"})

        self.assertContains(respuesta, 'data-total-cobrado>$8.000 COP<')
        self.assertContains(respuesta, "$2.000")

    def test_en_billetera_no_hay_devuelta_aunque_llegue_recibido(self):
        estudiante = self.identificar_estudiante()
        self.anadir(self.empanada)

        respuesta = self.client.post(self.cobrar, {"medio_pago": "billetera", "recibido": "99999"})

        self.assertContains(respuesta, "data-venta-registrada")
        self.assertNotContains(respuesta, "data-devuelta")
        self.assertEqual(saldo_de(estudiante), Decimal("46500"))

    def test_arrastra_el_ticket_el_cliente_y_el_catalogo(self):
        self.anadir(self.empanada)

        cuerpo = self.client.post(self.cobrar, {"medio_pago": "efectivo"}).content.decode()

        self.assertIn('id="ticket-de-venta" class="flex grow flex-col gap-3" hx-swap-oob="true"', cuerpo)
        self.assertIn('id="estudiante-identificado"', cuerpo)
        self.assertIn('id="catalogo-de-venta"', cuerpo)

    def test_venta_nueva_es_la_unica_salida(self):
        self.anadir(self.empanada)

        respuesta = self.client.post(self.cobrar, {"medio_pago": "efectivo"})

        self.assertContains(respuesta, "data-venta-nueva autofocus")
        self.assertNotContains(respuesta, "Seguir con")

    def test_un_rechazo_se_dice_en_la_modal_y_no_toca_el_carrito(self):
        self.identificar_estudiante(saldo="1000")
        self.anadir(self.empanada)

        respuesta = self.client.post(self.cobrar, {"medio_pago": "billetera"})

        self.assertContains(respuesta, "data-cobro-rechazado")
        self.assertContains(respuesta, "data-venta-rechazada")  # el ticket de detrás
        self.assertEqual(Venta.objects.count(), 0)
        self.assertContains(self.client.get(self.confirmacion), "data-confirmar-cobro")


class SoloElCajeroTest(BaseDelCobro):
    def test_ningun_otro_rol(self):
        for rol in (Rol.ADMINISTRADOR, Rol.INSTITUCION, Rol.ACUDIENTE):
            self.client.force_login(
                Usuario.objects.crear_usuario(email=f"{rol}-modales@example.com", rol=rol)
            )
            for ruta in (self.confirmacion, self.devuelta):
                with self.subTest(rol=rol, ruta=ruta):
                    self.assertEqual(self.client.get(ruta).status_code, 403)

    def test_la_confirmacion_y_la_devuelta_solo_responden_a_get(self):
        for ruta in (self.confirmacion, self.devuelta):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.post(ruta).status_code, 405)


class EnterEnElCampoNoCobraTest(TestCase):
    """La pieza vive en `interfaz.js`; aquí se vigila que siga en su sitio y que
    la plantilla lleve los marcadores que busca."""

    INTERFAZ = Path(settings.BASE_DIR) / "assets/js/interfaz.js"
    CONFIRMACION = Path(settings.BASE_DIR) / "templates/ventas/partials/confirmacion-del-cobro.html"

    def test_la_pieza_y_sus_marcadores(self):
        interfaz = self.INTERFAZ.read_text()
        plantilla = self.CONFIRMACION.read_text()

        self.assertIn('closest("[data-dinero-recibido]")', interfaz)
        self.assertIn('querySelector("[data-confirmar-cobro]")', interfaz)
        self.assertIn("data-dinero-recibido", plantilla)
        self.assertIn("data-confirmar-cobro", plantilla)
