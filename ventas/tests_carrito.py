"""`TT-81`. El carrito y la confirmación en el punto de venta (`HU-21`, `INT-2`).

Lo que se comprueba aquí es la pantalla, no la transacción: esa es
`ventas/tests_venta.py` y su concurrencia, `ventas/tests_concurrencia.py`.

Tres propiedades, y las tres se rompen solas con el tiempo:

1. **Un renglón por producto.** Pulsar dos veces la empanada suma cantidades, no
   apila líneas — que es lo que `LineaVenta` admite (`TT-78`) y lo que el cajero
   espera ver.
2. **Sin diálogo de confirmación.** `INT-2` los descarta: un modal roba el foco,
   y el foco es del lector.
3. **Al cobrar, la caja queda lista para el siguiente cliente.** El carrito se
   vacía y el estudiante se olvida. Dejarlo puesto invitaría a cobrarle la
   siguiente venta a quien ya se fue.

El carrito vive en la sesión y no en el navegador (`DT-26`). La consecuencia que
importa para estas pruebas: el cliente de prueba lo lleva solo, como lo llevaría
un navegador.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from billetera.selectors import saldo_de
from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from ventas.models import LineaVenta, MedioDePago, Venta


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


class ElCarritoSeMontaDesdeElCatalogoTest(TestCase):
    def setUp(self):
        self.client.force_login(
            Usuario.objects.crear_usuario(
                email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
            )
        )
        self.empanada = producto()
        self.gaseosa = producto(nombre="Gaseosa", precio="2500", existencias=4)
        self.carrito = reverse("carrito-del-punto-de-venta")

    def _anadir(self, articulo, veces=1):
        for _ in range(veces):
            respuesta = self.client.post(
                self.carrito, {"producto": str(articulo.id), "accion": "anadir"}
            )
        return respuesta.content.decode()

    def test_el_catalogo_sale_con_su_precio_y_sus_existencias(self):
        cuerpo = self.client.get(reverse("punto-de-venta")).content.decode()

        self.assertIn("Empanada", cuerpo)
        self.assertIn("$3.500", cuerpo)
        self.assertIn("Quedan", cuerpo)

    def test_pulsar_un_producto_lo_pone_en_el_ticket(self):
        cuerpo = self._anadir(self.empanada)

        self.assertIn("Empanada", cuerpo)
        self.assertIn("$3.500 COP", cuerpo)

    def test_pulsarlo_dos_veces_suma_cantidad_y_no_apila_renglones(self):
        """`TT-78`: una línea por producto en cada venta."""
        cuerpo = self._anadir(self.empanada, veces=3)

        # Se cuenta el marcador propio del renglón y no el nombre del producto:
        # el nombre sale además en las etiquetas de los tres botones.
        self.assertEqual(cuerpo.count("data-linea-de-venta"), 1)
        self.assertIn("$10.500 COP", cuerpo)

    def test_el_total_suma_productos_distintos(self):
        self._anadir(self.empanada, veces=2)
        cuerpo = self._anadir(self.gaseosa)

        self.assertIn("$9.500 COP", cuerpo)

    def test_se_descuenta_una_unidad_sin_perder_el_renglon(self):
        self._anadir(self.empanada, veces=2)

        cuerpo = self.client.post(
            self.carrito, {"producto": str(self.empanada.id), "accion": "descontar"}
        ).content.decode()

        self.assertIn("Empanada", cuerpo)
        self.assertIn("$3.500 COP", cuerpo)

    def test_descontar_la_ultima_unidad_saca_el_renglon(self):
        self._anadir(self.empanada)

        cuerpo = self.client.post(
            self.carrito, {"producto": str(self.empanada.id), "accion": "descontar"}
        ).content.decode()

        self.assertIn("Todavía no hay nada en la venta", cuerpo)

    def test_quitar_saca_el_renglon_entero(self):
        self._anadir(self.empanada, veces=4)

        cuerpo = self.client.post(
            self.carrito, {"producto": str(self.empanada.id), "accion": "quitar"}
        ).content.decode()

        self.assertIn("Todavía no hay nada en la venta", cuerpo)

    def test_vaciar_deja_la_venta_como_recien_abierta(self):
        self._anadir(self.empanada)
        self._anadir(self.gaseosa)

        cuerpo = self.client.post(self.carrito, {"accion": "vaciar"}).content.decode()

        self.assertIn("Todavía no hay nada en la venta", cuerpo)

    def test_el_carrito_devuelve_un_fragmento_y_no_una_pagina(self):
        """`DT-16`. Si devolviera la página, cada toque repintaría el punto de
        venta y el foco del lector se iría con él."""
        cuerpo = self._anadir(self.empanada)

        self.assertNotIn("<html", cuerpo)
        self.assertNotIn("<body", cuerpo)

    def test_el_carrito_no_se_toca_por_GET(self):
        """Un `GET` que cambia algo es una URL que el navegador reproduce solo."""
        respuesta = self.client.get(self.carrito, {"producto": str(self.empanada.id)})

        self.assertEqual(respuesta.status_code, 405)

    def test_solo_el_cajero_monta_una_venta(self):
        for rol in [Rol.ACUDIENTE, Rol.ADMINISTRADOR, Rol.INSTITUCION]:
            with self.subTest(rol=rol):
                self.client.force_login(
                    Usuario.objects.crear_usuario(
                        email=f"{rol}@example.com", rol=rol, nombre="Otro"
                    )
                )
                respuesta = self.client.post(
                    self.carrito, {"producto": str(self.empanada.id)}
                )
                self.assertEqual(respuesta.status_code, 403)


class LaConfirmacionCobraSinPreguntarTest(TestCase):
    """`INT-2`: sin diálogos. El botón cobra."""

    def setUp(self):
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        self.client.force_login(self.cajero)

        acudiente = Usuario.objects.crear_usuario(
            email="acudiente@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
        )
        ficha = Acudiente.objects.create(
            usuario=acudiente, nombre="Marta Ruiz Ochoa", documento="4310012345"
        )
        self.estudiante = Estudiante.objects.create(
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001234501",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        recargar(actor=acudiente, estudiante=self.estudiante, monto=Decimal("50000"))

        self.empanada = producto()
        self.carrito = reverse("carrito-del-punto-de-venta")
        self.cobrar = reverse("cobrar")

    def _montar_venta_de_estudiante(self, cantidad=2):
        self.client.get(
            reverse("identificacion-en-el-punto-de-venta"),
            {"codigo": self.estudiante.codigo_tarjeta},
        )
        for _ in range(cantidad):
            self.client.post(
                self.carrito, {"producto": str(self.empanada.id), "accion": "anadir"}
            )

    def test_el_ticket_no_pide_confirmar_nada(self):
        """Ni `confirm`, ni `<dialog>`, ni un botón deshabilitado esperando."""
        self._montar_venta_de_estudiante()
        cuerpo = self.client.post(
            self.carrito, {"producto": str(self.empanada.id), "accion": "descontar"}
        ).content.decode()

        self.assertNotIn("hx-confirm", cuerpo)
        self.assertNotIn("<dialog", cuerpo)
        self.assertNotIn("disabled", cuerpo)

    def test_cobrar_descuenta_saldo_y_existencias(self):
        self._montar_venta_de_estudiante()

        cuerpo = self.client.post(self.cobrar).content.decode()

        self.assertIn("Venta cobrada", cuerpo)
        self.assertIn("$7.000 COP", cuerpo)
        self.assertEqual(saldo_de(self.estudiante), Decimal("43000"))
        self.assertEqual(existencias_de(self.empanada), 8)

    def test_la_venta_queda_a_nombre_del_estudiante_identificado(self):
        """Quién es el cliente lo recuerda el servidor: entre escanear y cobrar
        puede haber otro escaneo, y manda el último."""
        self._montar_venta_de_estudiante()

        self.client.post(self.cobrar)

        venta = Venta.objects.get()
        self.assertEqual(venta.estudiante, self.estudiante)
        self.assertEqual(venta.cajero, self.cajero)
        self.assertEqual(venta.medio_pago, MedioDePago.BILLETERA)
        self.assertEqual(venta.lineas.count(), 1)

    def test_tras_cobrar_la_caja_queda_lista_para_el_siguiente(self):
        """El carrito se vacía **y el estudiante se olvida**. Dejarlo puesto
        invitaría a cobrarle la siguiente venta a quien ya se fue."""
        self._montar_venta_de_estudiante()

        cuerpo = self.client.post(self.cobrar).content.decode()

        # El intercambio fuera de banda devuelve la columna del estudiante a su
        # estado vacío y el medio de pago al suyo.
        self.assertIn('hx-swap-oob="true"', cuerpo)
        self.assertIn("Ningún estudiante identificado", cuerpo)
        self.assertIn('data-medio="efectivo"', cuerpo)

        # Y el ticket, ya sin líneas: una segunda confirmación no cobra nada.
        segunda = self.client.post(self.cobrar).content.decode()
        self.assertIn("La venta no se realizó", segunda)
        self.assertEqual(Venta.objects.count(), 1)

    def test_el_catalogo_vuelve_con_las_existencias_de_ahora(self):
        """Las que acaba de mover la venta son las que el siguiente cobro lee."""
        self._montar_venta_de_estudiante(cantidad=3)

        cuerpo = self.client.post(self.cobrar).content.decode()

        self.assertIn('id="catalogo-de-venta"', cuerpo)
        self.assertIn("Quedan", cuerpo)
        self.assertIn(">7<", cuerpo.replace(" ", "").replace("\n", ""))

    def test_un_rechazo_deja_el_carrito_intacto(self):
        """No se ha escrito nada, así que arreglar el motivo y volver a pulsar es
        todo lo que hace falta. Vaciar el carrito obligaría a montarlo otra vez
        con la fila delante."""
        self._montar_venta_de_estudiante(cantidad=1)
        # Se le va el saldo por otro lado: la venta ya no alcanza.
        Venta.objects.all().delete()
        self.empanada.precio = Decimal("99000")
        self.empanada.save(update_fields=["precio"])

        cuerpo = self.client.post(self.cobrar).content.decode()

        self.assertIn("La venta no se realizó", cuerpo)
        self.assertIn("No se descontó nada", cuerpo)
        self.assertIn("Empanada", cuerpo)
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(saldo_de(self.estudiante), Decimal("50000"))

    def test_cobrar_sin_estudiante_usa_el_medio_que_llega(self):
        """La venta genérica ya funciona por aquí; la pantalla que la ofrece es
        `TT-89` (`PR-15`)."""
        self.client.post(
            self.carrito, {"producto": str(self.empanada.id), "accion": "anadir"}
        )

        cuerpo = self.client.post(
            self.cobrar, {"medio_pago": MedioDePago.EFECTIVO}
        ).content.decode()

        self.assertIn("Venta cobrada", cuerpo)
        self.assertEqual(Venta.objects.get().medio_pago, MedioDePago.EFECTIVO)
        self.assertEqual(LineaVenta.objects.count(), 1)

    def test_no_se_cobra_por_GET(self):
        respuesta = self.client.get(self.cobrar)

        self.assertEqual(respuesta.status_code, 405)

    def test_solo_el_cajero_cobra(self):
        self.client.force_login(
            Usuario.objects.crear_usuario(
                email="otro@example.com", rol=Rol.ADMINISTRADOR, nombre="Otro"
            )
        )

        respuesta = self.client.post(self.cobrar)

        self.assertEqual(respuesta.status_code, 403)
