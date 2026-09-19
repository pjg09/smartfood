"""`TT-170`. El consolidado del libro de inventario en el admin (`HU-36`).

El libro ya estaba desde `TT-69` y ya enseñaba los tres tipos con su motivo. Lo
que `HU-36` añade y estas pruebas fijan es lo que le faltaba para ser un
reporte:

1. **Acotar un periodo** —`date_hierarchy`—, sin lo cual el consolidado solo
   podría hablar del libro entero.
2. **Decir cuánto suma lo que se está mirando**, calculado sobre el mismo
   `QuerySet` que pinta la tabla. Si se calculara aparte, filtrar por «merma»
   dejaría arriba el total de todo y **nadie lo notaría**: las dos cifras
   seguirían siendo correctas cada una por su lado.

Y lo que no cambia y conviene que siga sin cambiar: **el libro no se edita ni se
borra** (`INV-3`), y el alta solo asienta ingresos.

Las cuentas se crean por el camino real —`sincronizar_grupos_y_permisos` y
`crear_cuenta(..., accede_a_administracion=True)`—: poner `is_staff` a mano deja
una cuenta que entra al admin sin un solo permiso.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from ventas.models import MedioDePago, Venta

LISTADO = "admin:inventario_movimientoinventario_changelist"


class BaseDelReporteDeInventario(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero-inv-admin@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
        self.pan = Producto.objects.create(
            nombre="Pan de queso", precio=Decimal("2500"), categoria=categoria
        )

    def entrar(self, rol=Rol.ADMINISTRADOR, email="admin-inv@example.com", staff=True):
        usuario = crear_cuenta(
            email=email,
            rol=rol,
            nombre="Persona",
            accede_a_administracion=staff,
            enviar_invitacion=False,
        )
        self.client.force_login(usuario)
        return usuario

    def ingresar(self, cantidad=10):
        return MovimientoInventario.objects.create(
            producto=self.pan,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=cantidad,
            motivo="Compra",
        )

    def vender(self, cantidad=2):
        venta = Venta.objects.create(
            cajero=self.cajero, medio_pago=MedioDePago.EFECTIVO
        )
        return MovimientoInventario.objects.create(
            producto=self.pan,
            tipo=TipoDeMovimientoDeInventario.VENTA,
            cantidad=-cantidad,
            venta=venta,
        )

    def mermar(self, cantidad=1, motivo="Rotura"):
        return MovimientoInventario.objects.create(
            producto=self.pan,
            tipo=TipoDeMovimientoDeInventario.MERMA,
            cantidad=-cantidad,
            motivo=motivo,
        )


class ElConsolidadoEsDelListadoQueSeMiraTest(BaseDelReporteDeInventario):
    def setUp(self):
        super().setUp()
        self.ingresar(cantidad=20)
        self.ingresar(cantidad=5)
        self.vender(cantidad=3)
        self.mermar(cantidad=2)
        self.entrar()

    def resumen_de(self, **filtros):
        respuesta = self.client.get(reverse(LISTADO), filtros)
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.context["resumen"]

    def test_sin_filtros_suma_el_libro_entero(self):
        resumen = self.resumen_de()

        self.assertEqual(resumen.cuantos, 4)
        self.assertEqual(resumen.entradas, 25)
        self.assertEqual(resumen.salidas, 5)
        self.assertEqual(resumen.neto, 20)

    def test_al_filtrar_por_tipo_el_consolidado_se_filtra_con_el(self):
        """Si esto falla, el neto de arriba habla de otro conjunto que la tabla
        de abajo y las dos cifras parecen correctas."""
        resumen = self.resumen_de(tipo=TipoDeMovimientoDeInventario.MERMA)

        self.assertEqual(resumen.cuantos, 1)
        self.assertEqual(resumen.entradas, 0)
        self.assertEqual(resumen.salidas, 2)
        self.assertEqual(resumen.neto, -2)

    def test_el_desglose_agrupa_bien_sobre_el_listado_ordenado(self):
        """El admin ordena explícitamente, y un `order_by()` explícito entra en
        el `GROUP BY` de un `values().annotate()`: sin limpiarlo, los dos
        ingresos saldrían como dos filas de uno."""
        resumen = self.resumen_de()

        por_tipo = {
            etiqueta: (cuantos, unidades)
            for etiqueta, cuantos, unidades in resumen.por_tipo
        }

        self.assertEqual(
            por_tipo[TipoDeMovimientoDeInventario.INGRESO.label], (2, 25)
        )
        self.assertEqual(
            sum(cuantos for _, cuantos, _ in resumen.por_tipo), resumen.cuantos
        )

    def test_la_pantalla_enseña_el_consolidado(self):
        respuesta = self.client.get(reverse(LISTADO))

        self.assertContains(respuesta, "data-resumen-de-movimientos")
        self.assertContains(respuesta, "data-neto")
        self.assertContains(respuesta, "data-por-tipo")
        self.assertContains(respuesta, "data-mermas-con-motivo")

    def test_un_filtro_sin_resultados_no_inventa_un_cero(self):
        """Un «0 unidades netas» se lee como «no se movió nada», y lo que pasa
        es que el filtro no alcanzó ningún asiento."""
        respuesta = self.client.get(reverse(LISTADO), {"q": "zzzz-no-existe"})

        self.assertFalse(respuesta.context["resumen"].hubo_movimientos)
        self.assertContains(respuesta, "data-sin-movimientos")

    def test_la_pantalla_deja_acotar_un_periodo(self):
        """`date_hierarchy`: sin él, el consolidado solo puede hablar del libro
        entero y el reporte no sirve para «la semana pasada»."""
        respuesta = self.client.get(reverse(LISTADO))

        self.assertIsNotNone(respuesta.context["cl"].date_hierarchy)


class ElLibroSigueSinEscribirseTest(BaseDelReporteDeInventario):
    """Lo que el reporte **no** puede haber aflojado (`INV-3`)."""

    def setUp(self):
        super().setUp()
        self.movimiento = self.ingresar()
        self.entrar()

    def test_la_ficha_no_se_edita(self):
        respuesta = self.client.get(
            reverse(
                "admin:inventario_movimientoinventario_change",
                args=[self.movimiento.pk],
            )
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.context["has_change_permission"])
        self.assertFalse(respuesta.context["has_delete_permission"])

    def test_el_borrado_responde_403(self):
        respuesta = self.client.get(
            reverse(
                "admin:inventario_movimientoinventario_delete",
                args=[self.movimiento.pk],
            )
        )

        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(
            MovimientoInventario.objects.filter(pk=self.movimiento.pk).exists()
        )


class SoloLaAdministracionVeElReporteDeInventarioTest(BaseDelReporteDeInventario):
    def test_la_administracion_entra(self):
        self.entrar()

        self.assertEqual(self.client.get(reverse(LISTADO)).status_code, 200)

    def test_la_institucion_no_entra(self):
        self.entrar(Rol.INSTITUCION, "institucion-inv@example.com")

        self.assertEqual(self.client.get(reverse(LISTADO)).status_code, 403)

    def test_el_cajero_no_entra_al_admin(self):
        self.entrar(Rol.CAJERO, "cajero-inv2@example.com", staff=False)

        self.assertEqual(self.client.get(reverse(LISTADO)).status_code, 302)
