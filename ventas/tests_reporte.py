"""`HU-35`, `DT-54`. El reporte de ventas, en `/ventas/`, fuera del admin.

Lo que estas pruebas fijan:

1. **Las cifras de arriba cuadran con los desgloses de abajo.** Ingresos por
   categoría, por medio de pago y por día suman el mismo total. Un
   `order_by()` olvidado antes de agrupar deja el total bien y los desgloses
   mal, y nadie lo nota: se comprueban unos contra otros, no contra cifras a
   mano.
2. **Lo que la pantalla dice es verdad aquí**: la categoría es la de hoy, el
   importe es el congelado (`DT-8`), el pedido anticipado va dentro de la
   billetera, y el día es el local.
3. **El cliente, por su nombre y nada más**: ni documento ni código de tarjeta.
4. **Solo `USR-4`** (`[S11]`), por todas las rutas, y el rol antes del `404`.
5. **Nadie escribe una venta desde aquí**: solo `GET`, y el permiso no existe
   en ningún grupo (`DT-11`).
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.permisos import nombre_del_grupo
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from reportes.selectors import MAS_VENDIDOS_EN_EL_REPORTE, reporte_de_ventas
from reportes.views import periodo_pedido
from ventas.models import MedioDePago, Venta
from ventas.services import registrar_venta, reservar

PANTALLA = "ventas-de-la-cafeteria"


class BaseDelReporte(TestCase):
    """Una cafetería con ventas de los medios de pago y las cuentas de verdad."""

    def setUp(self):
        sincronizar_grupos_y_permisos()
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero-reporte@example.com", rol=Rol.CAJERO, nombre="Diego Ramírez"
        )
        self.acudiente = Usuario.objects.crear_usuario(
            email="marta-reporte@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
        )
        ficha = Acudiente.objects.create(
            usuario=self.acudiente, nombre="Marta Ruiz", documento="4310088001"
        )
        self.estudiante = Estudiante.objects.create(
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001088001",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("100000"))

        self.panaderia = Categoria.objects.create(nombre="Panadería")
        self.bebidas = Categoria.objects.create(nombre="Bebidas")
        self.pan = self.producto("Pan de queso", "2500", self.panaderia)
        self.jugo = self.producto("Jugo de mora", "3000", self.bebidas)

    def producto(self, nombre, precio, categoria):
        producto = Producto.objects.create(
            nombre=nombre, precio=Decimal(precio), categoria=categoria
        )
        MovimientoInventario.objects.create(
            producto=producto,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=100,
            motivo="Ingreso de prueba",
        )
        return producto

    def entrar(self, rol, email, staff=True):
        usuario = crear_cuenta(
            email=email, rol=rol, nombre="Persona",
            accede_a_administracion=staff, enviar_invitacion=False,
        )
        self.client.force_login(usuario)
        return usuario

    def entrar_como_administracion(self):
        self.administracion = self.entrar(Rol.ADMINISTRADOR, "administracion-reporte@example.com")
        return self.administracion

    def vender_a_estudiante(self, producto=None, cantidad=1):
        return registrar_venta(
            actor=self.cajero, estudiante=self.estudiante,
            lineas={(producto or self.pan).id: cantidad},
        )

    def vender_en_efectivo(self, producto=None, cantidad=1):
        return registrar_venta(
            actor=self.cajero, lineas={(producto or self.pan).id: cantidad},
            medio_pago=MedioDePago.EFECTIVO,
        )

    def reporte(self, **parametros):
        respuesta = self.client.get(reverse(PANTALLA), {"periodo": "todo", **parametros})
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.context["reporte"]


class LasCifrasCuadranEntreSiTest(BaseDelReporte):
    def setUp(self):
        super().setUp()
        self.vender_a_estudiante(cantidad=2)                  # billetera, 5.000
        self.vender_a_estudiante(self.jugo, cantidad=1)       # billetera, 3.000
        self.vender_en_efectivo(cantidad=4)                   # efectivo, 10.000
        # Dos renglones en una venta: sin ella, un recuento por día sin
        # `distinct` saldría bien por casualidad.
        registrar_venta(actor=self.cajero, lineas={self.pan.id: 1, self.jugo.id: 1},
                        medio_pago=MedioDePago.EFECTIVO)      # efectivo, 5.500
        self.entrar_como_administracion()

    def test_las_cuatro_cifras(self):
        reporte = self.reporte()

        self.assertEqual(reporte.resumen.cuantas, 4)
        self.assertEqual(reporte.resumen.total, Decimal("23500.00"))
        self.assertEqual(reporte.resumen.unidades, 9)
        self.assertEqual(reporte.productos_distintos, 2)
        self.assertEqual(reporte.ticket_medio, Decimal("5875"))
        self.assertEqual(reporte.dias_con_venta, 1)

    def test_los_tres_desgloses_suman_el_total(self):
        """**El fallo que solo la pantalla enseña**: un `GROUP BY` envenenado
        por el orden deja el total bien y los desgloses mal."""
        reporte = self.reporte()
        total = reporte.resumen.total

        self.assertEqual(sum(f["importe"] for f in reporte.por_categoria), total)
        self.assertEqual(sum(f["total"] for f in reporte.por_medio_de_pago), total)
        self.assertEqual(sum(d["total"] for d in reporte.por_dia), total)
        self.assertEqual(sum(d["cuantas"] for d in reporte.por_dia), reporte.resumen.cuantas)
        self.assertEqual(
            sum(f["cuantas"] for f in reporte.por_medio_de_pago), reporte.resumen.cuantas
        )

    def test_una_fila_por_categoria_y_con_su_importe(self):
        """Que los desgloses sumen el total no basta: con el orden metido en el
        `GROUP BY`, cada categoría sale partida en varias filas y la suma sigue
        cuadrando. Se comprueban las filas."""
        categorias = {f["nombre"]: f["importe"] for f in self.reporte().por_categoria}

        self.assertEqual(len(self.reporte().por_categoria), 2)
        self.assertEqual(
            categorias, {"Panadería": Decimal("17500.00"), "Bebidas": Decimal("6000.00")}
        )

    def test_un_dia_es_una_fila(self):
        self.assertEqual(len(self.reporte().por_dia), 1)

    def test_los_tres_medios_salen_aunque_alguno_este_en_cero(self):
        medios = [f["etiqueta"] for f in self.reporte().por_medio_de_pago]

        self.assertEqual(medios, [m.label for m in MedioDePago])

    def test_la_pantalla_pinta_las_cifras_y_los_bloques(self):
        respuesta = self.client.get(reverse(PANTALLA), {"periodo": "todo"})

        self.assertContains(respuesta, 'data-cifra="ingresos">$23.500 COP<')
        for bloque in ("data-por-categoria", "data-por-medio-de-pago", "data-mas-vendidos",
                       "data-por-dia", "data-enlace-a-la-auditoria"):
            with self.subTest(bloque=bloque):
                self.assertContains(respuesta, bloque)

    def test_no_hay_ranking_de_gasto_por_estudiante(self):
        """`DT-54`: el consumo de cada menor es del acudiente (`[S11]`). La
        pantalla no nombra a nadie; los nombres viven en la modal del día."""
        respuesta = self.client.get(reverse(PANTALLA), {"periodo": "todo"})

        self.assertNotContains(respuesta, self.estudiante.nombre)


class LoQueLaPantallaDiceEsVerdadTest(BaseDelReporte):
    def setUp(self):
        super().setUp()
        self.entrar_como_administracion()

    def test_la_categoria_es_la_de_hoy(self):
        """La línea no congela la categoría (`DT-8`, `DT-51`): mover el
        producto arrastra sus ventas pasadas, y la pantalla lo dice."""
        self.vender_en_efectivo(cantidad=2)
        self.pan.categoria = self.bebidas
        self.pan.save(update_fields=["categoria"])

        categorias = [f["nombre"] for f in self.reporte().por_categoria]

        self.assertEqual(categorias, ["Bebidas"])

    def test_el_importe_es_el_congelado(self):
        venta = self.vender_en_efectivo(cantidad=2)
        self.pan.precio = Decimal("9900")
        self.pan.save(update_fields=["precio"])

        self.assertEqual(self.reporte().resumen.total, Decimal("5000.00"))
        ficha = self.client.get(reverse("venta-ficha", args=[venta.pk]))
        self.assertContains(ficha, "$5.000")
        self.assertNotContains(ficha, "$9.900")

    def test_el_pedido_anticipado_va_dentro_de_la_billetera(self):
        """No es un cuarto medio de pago (`DEC-1`): se paga con la billetera."""
        reservar(actor=self.acudiente, estudiante=self.estudiante, lineas={self.jugo.id: 2})
        self.vender_a_estudiante(cantidad=1)

        reporte = self.reporte()
        billetera = next(
            f for f in reporte.por_medio_de_pago if f["etiqueta"] == MedioDePago.BILLETERA.label
        )

        self.assertEqual(billetera["total"], Decimal("8500.00"))
        self.assertEqual(reporte.de_pedidos_anticipados, Decimal("6000.00"))

    def test_el_dia_es_el_local_y_no_el_de_la_base(self):
        """Una venta a las 23:30 de Bogotá ya es el día siguiente en UTC."""
        venta = self.vender_en_efectivo()
        noche = timezone.make_aware(datetime(2026, 10, 1, 23, 30))
        Venta.objects.filter(pk=venta.pk).update(creado_en=noche)

        reporte = self.reporte(desde="2026-10-01", hasta="2026-10-01")

        self.assertEqual([d["dia"] for d in reporte.por_dia], [date(2026, 10, 1)])

    def test_los_mas_vendidos_se_cortan_y_lo_dicen(self):
        for i in range(MAS_VENDIDOS_EN_EL_REPORTE + 1):
            producto = self.producto(f"Producto {i:02}", "1000", self.panaderia)
            self.vender_en_efectivo(producto, cantidad=i + 1)

        reporte = self.reporte()

        self.assertEqual(len(reporte.mas_vendidos), MAS_VENDIDOS_EN_EL_REPORTE)
        self.assertTrue(reporte.hay_mas_productos)
        self.assertEqual(reporte.mas_vendidos[0]["nombre"], "Producto 10")

    def test_sin_ventas_no_se_inventa_una_media(self):
        reporte = self.reporte()

        self.assertIsNone(reporte.ticket_medio)
        self.assertIsNone(reporte.media_por_dia)
        self.assertEqual(reporte.por_dia, ())


class ElPeriodoTest(TestCase):
    """`periodo_pedido` es la única que lee el reloj, y recibe `hoy`."""

    HOY = date(2026, 10, 15)

    def test_por_defecto_treinta_dias(self):
        self.assertEqual(
            periodo_pedido({}, self.HOY), (date(2026, 9, 16), self.HOY, "30", "")
        )

    def test_los_atajos(self):
        self.assertEqual(periodo_pedido({"periodo": "7"}, self.HOY)[:2], (date(2026, 10, 9), self.HOY))
        self.assertEqual(periodo_pedido({"periodo": "todo"}, self.HOY), (None, None, "todo", ""))

    def test_un_atajo_desconocido_es_el_de_por_defecto(self):
        self.assertEqual(periodo_pedido({"periodo": "365"}, self.HOY)[2], "30")

    def test_las_fechas_mandan_sobre_el_atajo(self):
        self.assertEqual(
            periodo_pedido({"periodo": "7", "desde": "2026-09-01", "hasta": "2026-09-30"}, self.HOY),
            (date(2026, 9, 1), date(2026, 9, 30), None, ""),
        )

    def test_al_reves_se_intercambian_y_se_dice(self):
        desde, hasta, atajo, aviso = periodo_pedido(
            {"desde": "2026-09-30", "hasta": "2026-09-01"}, self.HOY
        )

        self.assertEqual((desde, hasta), (date(2026, 9, 1), date(2026, 9, 30)))
        self.assertTrue(aviso)

    def test_una_fecha_que_no_se_entiende_se_ignora(self):
        self.assertEqual(periodo_pedido({"desde": "ayer"}, self.HOY)[2], "30")

    def test_una_sola_fecha_deja_el_otro_extremo_abierto(self):
        self.assertEqual(
            periodo_pedido({"desde": "2026-10-01"}, self.HOY)[:2], (date(2026, 10, 1), None)
        )


class LaModalDelDiaTest(BaseDelReporte):
    def setUp(self):
        super().setUp()
        self.vender_a_estudiante(cantidad=2)
        self.vender_en_efectivo(cantidad=4)
        self.hoy = timezone.localdate()
        self.entrar_como_administracion()

    def ficha(self, **parametros):
        return self.client.get(
            reverse("ventas-del-dia-ficha", args=[self.hoy.isoformat()]), parametros
        )

    def test_trae_las_ventas_del_dia_con_su_total(self):
        respuesta = self.ficha()

        self.assertEqual(len(respuesta.context["ventas"]), 2)
        self.assertEqual(respuesta.context["total"], Decimal("15000.00"))
        self.assertNotContains(respuesta, "<html")

    def test_por_medio_solo_las_de_ese_medio(self):
        respuesta = self.ficha(medio=MedioDePago.EFECTIVO)

        self.assertEqual(len(respuesta.context["ventas"]), 1)
        self.assertEqual(respuesta.context["total"], Decimal("10000.00"))
        self.assertContains(respuesta, "Ventas en efectivo del")

    def test_dice_quien_cobro(self):
        self.assertContains(self.ficha(), "cobró Diego Ramírez")

    def test_el_cliente_por_su_nombre_y_nada_mas(self):
        """Ni documento ni código de tarjeta: la cafetería consulta su actividad
        comercial, no el padrón (`INV-7`, `ALC-OUT-08`)."""
        respuesta = self.ficha()

        self.assertContains(respuesta, self.estudiante.nombre)
        self.assertContains(respuesta, "Cliente genérico")
        self.assertNotContains(respuesta, self.estudiante.documento)
        self.assertNotContains(respuesta, self.estudiante.codigo_tarjeta)

    def test_la_pagina_del_dia_abre_su_modal_y_acota_el_periodo(self):
        respuesta = self.client.get(reverse("ventas-del-dia", args=[self.hoy.isoformat()]))

        self.assertEqual(respuesta.context["reporte"].desde, self.hoy)
        self.assertEqual(respuesta.context["reporte"].hasta, self.hoy)
        self.assertContains(
            respuesta, f'hx-get="{reverse("ventas-del-dia-ficha", args=[self.hoy.isoformat()])}"'
        )

    def test_cada_dia_del_listado_pide_su_modal(self):
        respuesta = self.client.get(reverse(PANTALLA))

        self.assertContains(
            respuesta, f'hx-get="{reverse("ventas-del-dia-ficha", args=[self.hoy.isoformat()])}"'
        )


class SoloLaAdministracionTest(BaseDelReporte):
    """`[S11]`: «consultar reportes de ventas e inventario» es de `USR-4`."""

    def setUp(self):
        super().setUp()
        self.venta = self.vender_a_estudiante()
        dia = timezone.localdate().isoformat()
        self.rutas = [
            reverse(PANTALLA),
            reverse("ventas-del-dia", args=[dia]),
            reverse("ventas-del-dia-ficha", args=[dia]),
            reverse("venta-de-la-cafeteria", args=[self.venta.pk]),
            reverse("venta-ficha", args=[self.venta.pk]),
        ]

    def test_la_administracion_entra(self):
        self.entrar_como_administracion()
        for ruta in self.rutas:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_ningun_otro_rol(self):
        """El cajero registra las ventas y no las reporta; la institución
        responde de los datos de los menores, no del negocio."""
        for rol in (Rol.CAJERO, Rol.INSTITUCION, Rol.ACUDIENTE):
            self.entrar(rol, f"{rol}-reporte-entra@example.com")
            for ruta in self.rutas:
                with self.subTest(rol=rol, ruta=ruta):
                    self.assertEqual(self.client.get(ruta).status_code, 403)

    def test_sin_sesion_va_al_acceso(self):
        self.assertEqual(self.client.get(reverse(PANTALLA)).status_code, 302)

    def test_el_rol_se_comprueba_antes_que_el_404(self):
        self.entrar(Rol.CAJERO, "cajero-404@example.com")
        for ruta in (reverse("ventas-del-dia-ficha", args=["no-es-fecha"]),
                     reverse("venta-ficha", args=["00000000-0000-0000-0000-000000000000"])):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 403)

    def test_a_la_administracion_si_le_dice_que_no_existe(self):
        self.entrar_como_administracion()

        self.assertEqual(
            self.client.get(reverse("ventas-del-dia-ficha", args=["no-es-fecha"])).status_code, 404
        )

    def test_el_listado_del_admin_ya_no_existe(self):
        with self.assertRaises(NoReverseMatch):
            reverse("admin:ventas_venta_changelist")
        self.entrar_como_administracion()
        self.assertEqual(self.client.get("/admin/ventas/venta/").status_code, 404)

    def test_esta_en_el_menu_de_la_administracion(self):
        self.entrar_como_administracion()

        self.assertContains(
            self.client.get(reverse("panel-de-la-cafeteria")), f'href="{reverse(PANTALLA)}"'
        )


class NadieEscribeUnaVentaDesdeAquiTest(BaseDelReporte):
    """Una venta es un asiento: se registra en el punto de venta, con su
    transacción, o no existe (`INV-1`, `INV-2`, `INV-3`). Por los dos caminos
    que `DT-11` exige: lo que responde la pantalla **y** el permiso."""

    def test_las_rutas_solo_responden_a_get(self):
        venta = self.vender_a_estudiante()
        self.entrar_como_administracion()
        for ruta in (reverse(PANTALLA), reverse("venta-ficha", args=[venta.pk])):
            with self.subTest(ruta=ruta):
                self.assertEqual(
                    self.client.post(ruta, {"medio_pago": MedioDePago.EFECTIVO}).status_code, 405
                )
        venta.refresh_from_db()
        self.assertEqual(venta.medio_pago, MedioDePago.BILLETERA)

    def test_ningun_grupo_tiene_permiso_de_escritura_sobre_ventas(self):
        """`ventas` está en `APPS_SIN_ESCRITURA_PARA_NINGUN_ROL`, y
        `restricciones/tests_permisos.py` lo recorre entero; aquí se fija además
        el caso concreto."""
        for rol in Rol:
            with self.subTest(rol=rol):
                codigos = set(
                    Permission.objects.filter(
                        group__name=nombre_del_grupo(rol), content_type__app_label="ventas",
                    ).values_list("codename", flat=True)
                )
                escrituras = {c for c in codigos if c.startswith(("add_", "change_", "delete_"))}
                self.assertEqual(escrituras, set())


class ElSelectorExigeElRolTest(BaseDelReporte):
    def test_otro_rol_no_lee(self):
        from django.core.exceptions import PermissionDenied

        with self.assertRaises(PermissionDenied):
            reporte_de_ventas(actor=self.cajero, desde=date.today() - timedelta(days=1))
