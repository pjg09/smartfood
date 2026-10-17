"""`DEC-16`. El panel de la cafetería, donde aterriza `USR-4`.

Tres cosas que fijar, y las tres se rompen solas:

1. **Quién entra.** Es un reporte de la operación: `[S11]` lo da a la
   administración y a nadie más. El cajero cobra y ve pasar sus ventas, pero el
   consolidado no es suyo.
2. **Que las cifras salgan de los mismos hechos que su reporte.** Un panel que
   suma por su cuenta acaba diciendo una cosa arriba y otra en el reporte, las
   dos bien formadas.
3. **Que la jornada sea la que se le pasa y no la del reloj.** Sin esto, la
   prueba falla sola una madrugada y nadie sabe por qué.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import tablero_del_inventario
from reportes.selectors import (
    CUANTOS_EN_EL_PANEL,
    UMBRAL_DE_EXISTENCIAS_BAJAS,
    panel_de_la_cafeteria,
)
from ventas.models import LineaVenta, MedioDePago, Venta

CLAVE = "clave-de-prueba-2026"


def cuenta(rol, staff=False):
    sincronizar_grupos_y_permisos()
    usuario = crear_cuenta(
        email=f"{rol}-panel@example.com",
        rol=rol,
        nombre=f"Cuenta {rol}",
        accede_a_administracion=staff,
        enviar_invitacion=False,
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
    return usuario


def producto(nombre="Empanada", precio="3000", existencias=40):
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


def cajero_de_turno():
    """Toda venta del punto de venta lleva cajero: lo exige la base.

    `venta_cajero_segun_su_origen` es una `CheckConstraint`, no un `if` de
    servicio (`DT-15`), así que una venta de prueba sin cajero no falla en la
    lógica: revienta en el `INSERT`.
    """
    existente = Usuario.objects.filter(email="cajero-de-turno@example.com").first()
    if existente is not None:
        return existente
    return Usuario.objects.crear_usuario(
        email="cajero-de-turno@example.com", rol=Rol.CAJERO, nombre="Cajero de turno"
    )


def venta_de(articulo, cantidad=1, medio=MedioDePago.EFECTIVO, cuando=None):
    venta = Venta.objects.create(medio_pago=medio, cajero=cajero_de_turno())
    LineaVenta.objects.create(
        venta=venta,
        producto=articulo,
        cantidad=cantidad,
        precio_unitario=articulo.precio,
    )
    if cuando is not None:
        # `creado_en` es `auto_now_add`: no se puede fijar al crear.
        Venta.objects.filter(pk=venta.pk).update(creado_en=cuando)
    return venta


class SoloLaAdministracionVeElPanelTest(TestCase):
    def test_los_otros_tres_roles_no_entran(self):
        for rol in (Rol.CAJERO, Rol.ACUDIENTE, Rol.INSTITUCION):
            with self.subTest(rol=rol):
                with self.assertRaises(PermissionDenied) as fallo:
                    panel_de_la_cafeteria(actor=cuenta(rol))

                # **El mensaje nombra esta pantalla y no otra.** Un rechazo que
                # cite «los reportes de ventas e inventario» manda a buscar algo
                # que no es lo que se pidió; pasó tres veces en el Sprint 5.
                self.assertIn("panel de la cafetería", str(fallo.exception))

    def test_la_administracion_sí_entra(self):
        panel = panel_de_la_cafeteria(actor=cuenta(Rol.ADMINISTRADOR, staff=True))

        self.assertEqual(panel.de_hoy.cuantas, 0)


class LasCifrasDelPanelTest(TestCase):
    def setUp(self):
        self.actor = cuenta(Rol.ADMINISTRADOR, staff=True)
        self.hoy = timezone.localdate()
        self.empanada = producto()

    def _panel(self):
        return panel_de_la_cafeteria(actor=self.actor, hoy=self.hoy)

    def test_la_jornada_cuenta_solo_lo_de_hoy(self):
        venta_de(self.empanada, 2)
        venta_de(
            self.empanada,
            5,
            cuando=timezone.now() - timedelta(days=3),
        )

        panel = self._panel()

        self.assertEqual(panel.de_hoy.cuantas, 1)
        self.assertEqual(panel.de_hoy.unidades, 2)
        # Y los treinta días traen las dos.
        self.assertEqual(panel.de_treinta_dias.cuantas, 2)

    def test_el_ticket_medio_es_el_total_entre_las_ventas(self):
        venta_de(self.empanada, 2)  # 6.000
        venta_de(self.empanada, 1)  # 3.000

        self.assertEqual(self._panel().ticket_medio, Decimal("4500"))

    def test_sin_ventas_no_hay_ticket_medio_y_eso_no_es_un_error(self):
        """Una jornada que no ha empezado no es una división por cero."""
        self.assertIsNone(self._panel().ticket_medio)

    def test_el_desglose_por_medio_de_pago_reparte_la_jornada(self):
        venta_de(self.empanada, 1, medio=MedioDePago.EFECTIVO)
        venta_de(self.empanada, 1, medio=MedioDePago.TRANSFERENCIA)

        por_medio = dict(
            (etiqueta, total) for etiqueta, _, total in self._panel().de_hoy.por_medio_de_pago
        )

        self.assertEqual(por_medio["Efectivo"], Decimal("3000.00"))
        self.assertEqual(por_medio["Transferencia"], Decimal("3000.00"))
        self.assertEqual(por_medio["Billetera"], Decimal("0.00"))

    def test_una_venta_de_varios_renglones_cuenta_como_una(self):
        """Una venta es una, sumen lo que sumen sus renglones.

        Lo protege el `distinct` de `resumen_de_ventas`, no el del recuento de
        renglones de aquí: en esta consulta hay una sola unión y quitarlo no
        cambia ninguna cifra — se comprobó quitándolo.
        """
        gaseosa = producto(nombre="Gaseosa", precio="2500")
        venta = Venta.objects.create(
            medio_pago=MedioDePago.EFECTIVO, cajero=cajero_de_turno()
        )
        for articulo in (self.empanada, gaseosa):
            LineaVenta.objects.create(
                venta=venta, producto=articulo, cantidad=1,
                precio_unitario=articulo.precio,
            )

        panel = self._panel()

        self.assertEqual(panel.de_hoy.cuantas, 1)
        self.assertEqual(panel.ultimas_ventas[0].renglones, 2)
        self.assertEqual(panel.ultimas_ventas[0].total_cobrado, Decimal("5500.00"))


class ElAvisoDeExistenciasTest(TestCase):
    def setUp(self):
        self.actor = cuenta(Rol.ADMINISTRADOR, staff=True)

    def test_solo_avisa_de_lo_que_esta_por_debajo_del_umbral(self):
        escaso = producto(nombre="Crispeta", existencias=UMBRAL_DE_EXISTENCIAS_BAJAS - 6)
        producto(nombre="Agua", existencias=UMBRAL_DE_EXISTENCIAS_BAJAS + 50)

        panel = panel_de_la_cafeteria(actor=self.actor)

        self.assertEqual([p.nombre for p, _ in panel.quedan_pocas], [escaso.nombre])
        self.assertEqual(panel.agotados, ())

    def test_agotado_y_quedan_pocas_son_los_cortes_del_inventario(self):
        """`DEC-25`: agotado es cero o menos, y «quedan pocas», de uno al umbral.
        El panel llamaba «quedan pocas» a los dos, y el inventario contaba los
        mismos productos como agotados."""
        producto(nombre="Banano", existencias=0)
        producto(nombre="Pan", existencias=1)
        producto(nombre="Jugo", existencias=UMBRAL_DE_EXISTENCIAS_BAJAS)

        panel = panel_de_la_cafeteria(actor=self.actor)
        tablero = tablero_del_inventario(actor=self.actor)

        self.assertEqual([p.nombre for p, _ in panel.agotados], ["Banano"])
        self.assertEqual([p.nombre for p, _ in panel.quedan_pocas], ["Pan", "Jugo"])
        self.assertEqual(len(panel.agotados), tablero.agotados)
        self.assertEqual(len(panel.quedan_pocas), tablero.quedan_pocas)

    def test_la_pantalla_dice_cada_grupo_por_su_nombre(self):
        producto(nombre="Banano", existencias=0)
        producto(nombre="Pan", existencias=1)
        self.client.force_login(self.actor)

        respuesta = self.client.get("/cafeteria/")

        self.assertContains(respuesta, 'data-grupo-de-existencias="agotados"')
        self.assertContains(respuesta, 'data-grupo-de-existencias="quedan-pocas"')

    def test_con_todo_surtido_no_hay_aviso(self):
        """Un hueco no es un aviso vacío: el bloque no se dibuja."""
        producto(nombre="Agua", existencias=200)

        panel = panel_de_la_cafeteria(actor=self.actor)

        self.assertEqual((panel.agotados, panel.quedan_pocas), ((), ()))

    def test_lo_mas_vendido_se_mide_contra_el_mas_vendido(self):
        uno = producto(nombre="Mandarina", precio="1200")
        otro = producto(nombre="Banano", precio="1500")
        venta_de(uno, 4)
        venta_de(otro, 1)

        filas = panel_de_la_cafeteria(actor=self.actor).mas_vendidos

        self.assertEqual(filas[0]["nombre"], "Mandarina")
        self.assertEqual(filas[0]["porcentaje"], 100)
        self.assertEqual(filas[1]["porcentaje"], 25)

    def test_el_panel_no_se_pasa_de_lo_que_cabe(self):
        for i in range(CUANTOS_EN_EL_PANEL + 4):
            venta_de(producto(nombre=f"Producto {i}", precio="1000"))

        panel = panel_de_la_cafeteria(actor=self.actor)

        self.assertEqual(len(panel.ultimas_ventas), CUANTOS_EN_EL_PANEL)
        self.assertEqual(len(panel.mas_vendidos), CUANTOS_EN_EL_PANEL)


class LaPantallaDelPanelTest(TestCase):
    """`DT-53`: el panel vive en el armazón de la aplicación, fuera del admin."""

    def setUp(self):
        self.actor = cuenta(Rol.ADMINISTRADOR, staff=True)
        self.client.force_login(self.actor)

    def test_se_sirve_en_el_armazon_de_la_aplicacion(self):
        respuesta = self.client.get("/cafeteria/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "reportes/panel-de-la-cafeteria.html")
        self.assertTemplateUsed(respuesta, "base-aplicacion.html")
        self.assertTemplateNotUsed(respuesta, "admin/base_site.html")

    def test_ya_no_esta_en_el_admin(self):
        """El nombre de la ruta se conserva —el reparto y la barra lo usan—; la
        URL del admin deja de existir y el admin responde su propio 404."""
        self.assertEqual(reverse("panel-de-la-cafeteria"), "/cafeteria/")
        self.assertEqual(self.client.get("/admin/panel/").status_code, 404)

    def test_no_depende_del_acceso_al_admin(self):
        """El rol lo exige el selector; `is_staff` era cosa del armazón del admin."""
        self.client.force_login(
            crear_cuenta(
                email="admin-sin-staff-panel@example.com",
                rol=Rol.ADMINISTRADOR,
                accede_a_administracion=False,
                enviar_invitacion=False,
            )
        )

        self.assertEqual(self.client.get("/cafeteria/").status_code, 200)

    def test_ningun_otro_rol_alcanza_la_pantalla(self):
        for rol in (Rol.CAJERO, Rol.INSTITUCION, Rol.ACUDIENTE):
            with self.subTest(rol=rol):
                self.client.force_login(cuenta(rol))
                self.assertEqual(self.client.get("/cafeteria/").status_code, 403)

    def test_sin_sesion_lleva_al_acceso(self):
        self.client.logout()

        respuesta = self.client.get("/cafeteria/")

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta["Location"].startswith("/login/"))
