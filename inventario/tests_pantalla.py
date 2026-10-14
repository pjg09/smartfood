"""`DEC-25`, `DT-50`. La pantalla de `/inventario/`: sus cifras, sus filtros y
quién la alcanza.

Lo que escribe —crear, editar, retirar, ingresar, mermar— se prueba en
`catalogo/tests_catalogo.py`, `catalogo/tests_imagen.py`, `tests_ingreso.py` y
`tests_merma.py`, junto a la regla que sostiene cada cosa. Aquí queda lo que es
de la pantalla:

1. **Las cifras de arriba.** Agotado es cero **o menos** —la entrega de un
   pedido puede dejar negativo (`DT-35`)—, «quedan pocas» no cuenta los
   agotados, y el valor no resta los negativos ni cuenta lo retirado.
2. **Los filtros**, y que uno mal escrito se ignore en vez de romper la lista.
3. **Solo la administración** la alcanza (`[S11]`), por la ruta y no por el menú.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Producto
from catalogo.services import retirar_del_catalogo
from cuentas.models import Rol
from cuentas.services import crear_cuenta
from inventario.selectors import (
    UMBRAL_DE_EXISTENCIAS_BAJAS,
    productos_del_inventario,
    tablero_del_inventario,
)
from inventario.services import asentar, ingresar_mercancia
from inventario.models import TipoDeMovimientoDeInventario
from ventas.models import MedioDePago, Venta


class BaseDeLaPantalla(TestCase):
    def setUp(self):
        self.administracion = crear_cuenta(
            email="admin-inventario@example.com",
            rol=Rol.ADMINISTRADOR,
            nombre="Lucía Gómez",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.bebidas = Categoria.objects.create(nombre="Bebidas")
        self.snacks = Categoria.objects.create(nombre="Snacks")

    def producto(self, nombre, precio, categoria=None, existencias=0):
        producto = Producto.objects.create(
            nombre=nombre, precio=Decimal(precio), categoria=categoria or self.snacks
        )
        if existencias:
            ingresar_mercancia(
                actor=self.administracion, producto=producto, cantidad=existencias,
                motivo="Inventario inicial",
            )
        return producto

    def dejar_en_negativo(self, producto, cuantas):
        """Lo que hace una entrega sin existencias (`DT-35`): una salida por
        venta que el libro no tenía con qué cubrir."""
        asentar(
            producto=producto,
            tipo=TipoDeMovimientoDeInventario.VENTA,
            cantidad=-cuantas,
            venta=Venta.objects.create(cajero=self.administracion, medio_pago=MedioDePago.EFECTIVO),
            registrado_por=self.administracion,
        )


class LasCifrasDelTableroTest(BaseDeLaPantalla):
    def setUp(self):
        super().setUp()
        self.agua = self.producto("Agua", "2000", self.bebidas, existencias=25)
        self.crispetas = self.producto("Crispetas", "1500", existencias=UMBRAL_DE_EXISTENCIAS_BAJAS)
        self.pony = self.producto("Pony Malta", "3450", self.bebidas)  # nunca ingresó
        self.arepa = self.producto("Arepa", "2800")
        self.dejar_en_negativo(self.arepa, 2)
        # Retirado, con existencias: no se vende, así que no cuenta.
        self.retirado = self.producto("Galleta vieja", "9999", existencias=50)
        retirar_del_catalogo(actor=self.administracion, producto=self.retirado)

    def tablero(self):
        return tablero_del_inventario(actor=self.administracion)

    def test_cuenta_solo_lo_que_esta_a_la_venta(self):
        self.assertEqual(self.tablero().productos, 4)

    def test_agotado_es_cero_o_menos(self):
        """Pony Malta en cero y Arepa en -2: los dos urgen reponer."""
        self.assertEqual(self.tablero().agotados, 2)

    def test_quedan_pocas_va_de_uno_al_umbral_y_no_repite_los_agotados(self):
        """Las crispetas, justo en el umbral. Los agotados ya tienen su tarjeta."""
        self.assertEqual(self.tablero().quedan_pocas, 1)

    def test_el_valor_no_resta_los_negativos_ni_cuenta_lo_retirado(self):
        """25 × 2.000 + 10 × 1.500. La arepa en -2 no vale -5.600, y los 50 de
        la galleta retirada no se venden."""
        self.assertEqual(self.tablero().valor, Decimal("65000.00"))


class LosFiltrosTest(BaseDeLaPantalla):
    def setUp(self):
        super().setUp()
        self.agua = self.producto("Agua sin gas", "2000", self.bebidas, existencias=4)
        self.jugo = self.producto("Jugo de mora", "3500", self.bebidas)
        self.empanada = self.producto("Empanada", "3000")
        self.client.force_login(self.administracion)

    def nombres(self, **filtros):
        return [p.nombre for p in productos_del_inventario(actor=self.administracion, **filtros)]

    def test_de_la_a_a_la_z_con_sus_existencias(self):
        productos = productos_del_inventario(actor=self.administracion)

        self.assertEqual([p.nombre for p in productos], ["Agua sin gas", "Empanada", "Jugo de mora"])
        self.assertEqual([p.existencias for p in productos], [4, 0, 0])

    def test_por_nombre_categoria_y_precio(self):
        self.assertEqual(self.nombres(nombre="MORA"), ["Jugo de mora"])
        self.assertEqual(self.nombres(categoria=self.bebidas), ["Agua sin gas", "Jugo de mora"])
        self.assertEqual(
            self.nombres(precio_minimo=Decimal("2500"), precio_maximo=Decimal("3200")), ["Empanada"]
        )

    def test_los_retirados_van_aparte(self):
        retirar_del_catalogo(actor=self.administracion, producto=self.jugo)

        self.assertEqual(self.nombres(), ["Agua sin gas", "Empanada"])
        self.assertEqual(self.nombres(retirados=True), ["Jugo de mora"])

    def test_los_filtros_viajan_en_la_url_de_la_lista(self):
        respuesta = self.client.get(
            reverse("lista-del-inventario"),
            {"categoria": str(self.bebidas.pk), "precio_maximo": "2500"},
        )

        self.assertNotContains(respuesta, "<html")
        self.assertEqual([p.nombre for p in respuesta.context["productos"]], ["Agua sin gas"])

    def test_un_filtro_mal_escrito_se_ignora_y_no_rompe_la_lista(self):
        respuesta = self.client.get(
            reverse("lista-del-inventario"),
            {"categoria": "no-es-un-uuid", "precio_minimo": "barato", "precio_maximo": "-5"},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["productos"]), 3)

    def test_la_lista_no_hace_una_consulta_por_producto(self):
        """Tres consultas con ocho productos: los productos con su categoría, los
        alérgenos de todos y las existencias de todos. Una por fila serían ocho."""
        for i in range(5):
            self.producto(f"Producto {i}", "1000", existencias=3)

        with self.assertNumQueries(3):
            for producto in productos_del_inventario(actor=self.administracion):
                producto.categoria.nombre
                list(producto.alergenos.all())
                producto.existencias


class LaPantallaSeRepintaTest(BaseDeLaPantalla):
    def test_las_cifras_y_la_lista_escuchan_las_escrituras(self):
        """Cada escritura responde con `HX-Trigger: inventario-cambiado`; si
        estas dos zonas no lo escucharan, la pantalla se quedaría con lo de antes."""
        self.client.force_login(self.administracion)

        cuerpo = self.client.get(reverse("inventario")).content.decode()

        self.assertIn(f'hx-get="{reverse("cifras-del-inventario")}" hx-trigger="inventario-cambiado from:body"', cuerpo)
        self.assertIn(f'hx-get="{reverse("lista-del-inventario")}" hx-trigger="inventario-cambiado from:body"', cuerpo)


class SoloLaAdministracionTest(BaseDeLaPantalla):
    """`[S11]`: «gestionar catálogo, precios e inventario» es de `USR-4`."""

    def rutas(self):
        producto = self.producto("Agua", "2000", existencias=3)
        return [
            reverse("inventario"),
            reverse("cifras-del-inventario"),
            reverse("lista-del-inventario"),
            reverse("movimiento-del-producto", args=[producto.pk]),
            reverse("historial-del-producto", args=[producto.pk]),
        ]

    def test_ningun_otro_rol(self):
        rutas = self.rutas()
        for rol in (Rol.CAJERO, Rol.INSTITUCION, Rol.ACUDIENTE):
            usuario = crear_cuenta(email=f"{rol}@example.com", rol=rol, enviar_invitacion=False)
            self.client.force_login(usuario)
            for url in rutas:
                with self.subTest(rol=rol, url=url):
                    self.assertEqual(self.client.get(url).status_code, 403)

    def test_un_anonimo_va_al_acceso(self):
        for url in self.rutas():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)

    def test_la_administracion_si(self):
        """La contraprueba: la regla no le cierra la pantalla a quien es suya."""
        self.client.force_login(self.administracion)
        for url in self.rutas():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_un_producto_que_no_existe_no_le_dice_a_otro_rol_que_no_existe(self):
        """Primero el rol, después el `404`: si no, un cajero podría preguntar
        qué identificadores existen."""
        cajero = crear_cuenta(email="cajero-x@example.com", rol=Rol.CAJERO, enviar_invitacion=False)
        self.client.force_login(cajero)

        respuesta = self.client.get(
            reverse("historial-del-producto", args=["01999999-9999-7999-8999-999999999999"])
        )

        self.assertEqual(respuesta.status_code, 403)
