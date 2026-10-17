"""`HU-56`, `DT-55`. El reporte de cierres de caja, en `/cierres/`, fuera del admin.

Lo que estas pruebas fijan:

1. **Las cifras de arriba son las del conjunto filtrado.** Si el resumen
   consultara por su cuenta, filtrar por «con faltante» dejaría arriba el
   descuadre de todo el periodo y nadie lo notaría: las dos cifras seguirían
   siendo correctas cada una por su lado.
2. **El enlace que hace comprobable `INVD-5`.** El tercer criterio de `HU-56`
   dice que el esperado de un día se explica desde sus ventas en efectivo.
   `ElEsperadoSeExplicaDesdeLasVentasTest` **sigue el enlace** y comprueba que
   las ventas que trae suman esa cifra.
3. **El cajero, por su nombre**: el correo es una credencial, ni se enseña ni
   se busca.
4. **Solo `USR-4`**, por todas las rutas, y el rol antes del `404`.
5. **Nadie escribe un cierre desde aquí**: solo `GET`, y el permiso no existe.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.permisos import nombre_del_grupo
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from ventas.models import CierreDeCaja, MedioDePago
from ventas.services import cerrar_caja, registrar_venta

PANTALLA = "cierres-de-caja"


class BaseDelReporteDeCierres(TestCase):
    """Un cajero que cobra y cuadra, y la cuenta de la administración."""

    def setUp(self):
        sincronizar_grupos_y_permisos()
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero-cierres@example.com", rol=Rol.CAJERO, nombre="Diego Ramírez"
        )
        self.hoy = timezone.localdate()

        categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
        self.pan = Producto.objects.create(
            nombre="Pan de queso", precio=Decimal("2500"), categoria=categoria
        )
        MovimientoInventario.objects.create(
            producto=self.pan,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=200,
            motivo="Ingreso de prueba",
        )

    def entrar(self, rol, email, staff=True):
        usuario = crear_cuenta(
            email=email, rol=rol, nombre="Persona",
            accede_a_administracion=staff, enviar_invitacion=False,
        )
        self.client.force_login(usuario)
        return usuario

    def entrar_como_administracion(self):
        return self.entrar(Rol.ADMINISTRADOR, "administracion-cierres@example.com")

    def vender_en_efectivo(self, cantidad=1):
        return registrar_venta(
            actor=self.cajero, lineas={self.pan.id: cantidad}, medio_pago=MedioDePago.EFECTIVO,
        )

    def cerrar(self, *, dias_atras=0, esperado="10000", base="20000", contado=None,
               motivo="", cajero=None):
        """Un cierre escrito a mano, para poblar el histórico.

        `cerrar_caja` calcula el esperado de la jornada de hoy, así que no sirve
        para fabricar jornadas anteriores con cifras elegidas. Lo que ese
        servicio garantiza tiene sus pruebas en `ventas/tests_cierre_de_caja.py`.
        """
        esperado = Decimal(esperado)
        base = Decimal(base)
        if contado is None:
            contado = base + esperado
        return CierreDeCaja.objects.create(
            fecha=self.hoy - timedelta(days=dias_atras),
            cajero=cajero or self.cajero,
            base=base,
            efectivo_esperado=esperado,
            efectivo_contado=Decimal(contado),
            motivo=motivo,
        )

    def pantalla(self, **parametros):
        respuesta = self.client.get(reverse(PANTALLA), {"periodo": "todo", **parametros})
        self.assertEqual(respuesta.status_code, 200)
        return respuesta


class LasCifrasSonDelConjuntoFiltradoTest(BaseDelReporteDeCierres):
    """**Lo que el admin daba hecho y aquí hay que sostener a mano.**"""

    def setUp(self):
        super().setUp()
        self.cuadrado = self.cerrar(dias_atras=0)                                      # cuadra
        self.sobrante = self.cerrar(dias_atras=1, contado="32000", motivo="Sobró un billete")  # +2.000
        self.faltante = self.cerrar(dias_atras=2, contado="27000", motivo="Faltó cambio")      # -3.000
        self.entrar_como_administracion()

    def reporte(self, **parametros):
        return self.pantalla(**parametros).context["reporte"]

    def test_sin_filtros_resume_el_historico(self):
        resumen = self.reporte().resumen

        self.assertEqual(resumen.cuantos, 3)
        self.assertEqual(resumen.cuadrados, 1)
        self.assertEqual(resumen.descuadre_total, Decimal("5000.00"))
        self.assertEqual(resumen.diferencia_neta, Decimal("-1000.00"))

    def test_al_filtrar_las_cifras_y_la_tabla_se_filtran_juntas(self):
        """Si esto falla, el descuadre de arriba habla de otro conjunto que la
        tabla de abajo, y las dos cifras parecen correctas."""
        reporte = self.reporte(resultado="faltante")

        self.assertEqual(reporte.resumen.cuantos, 1)
        self.assertEqual(reporte.resumen.descuadre_total, Decimal("3000.00"))
        self.assertEqual([c.pk for c in reporte.cierres], [self.faltante.pk])

    def test_el_resultado_distingue_las_tres_clases(self):
        """Lo que separa las tres **no es una columna**: es el signo de una resta."""
        for resultado, cierre in (("cuadra", self.cuadrado), ("sobrante", self.sobrante),
                                  ("faltante", self.faltante)):
            with self.subTest(resultado=resultado):
                self.assertEqual([c.pk for c in self.reporte(resultado=resultado).cierres], [cierre.pk])

    def test_por_cajero_y_el_desplegable_no_se_vacia(self):
        otra = Usuario.objects.crear_usuario(
            email="cajera-cierres@example.com", rol=Rol.CAJERO, nombre="Lina Patiño"
        )
        suyo = self.cerrar(dias_atras=3, contado="29000", motivo="Error de cambio", cajero=otra)

        reporte = self.reporte(cajero=str(otra.pk))

        self.assertEqual([c.pk for c in reporte.cierres], [suyo.pk])
        self.assertEqual({nombre for _, nombre in reporte.cajeros}, {"Diego Ramírez", "Lina Patiño"})

    def test_la_busqueda_es_en_el_motivo_y_no_en_el_correo(self):
        self.assertEqual([c.pk for c in self.reporte(q="faltó").cierres], [self.faltante.pk])
        self.assertEqual(self.reporte(q="cajero-cierres@").cierres, ())

    def test_ordenar_por_mayor_descuadre_encuentra_el_peor_dia(self):
        cierres = self.reporte(orden="descuadre").cierres

        self.assertEqual([c.pk for c in cierres], [self.faltante.pk, self.sobrante.pk, self.cuadrado.pk])

    def test_lo_que_no_se_reconoce_se_ignora(self):
        reporte = self.reporte(resultado="todo-mal", cajero="no-es-uuid", orden="al-azar")

        self.assertEqual(reporte.resumen.cuantos, 3)

    def test_el_periodo_es_la_jornada_y_no_cuando_se_registro(self):
        """Un cierre de hace cuarenta días no entra en «últimos 30», aunque se
        hubiera escrito hoy."""
        self.cerrar(dias_atras=40)

        self.assertEqual(self.reporte(periodo="30").resumen.cuantos, 3)
        self.assertEqual(self.reporte(periodo="todo").resumen.cuantos, 4)

    def test_los_atajos_conservan_los_filtros(self):
        respuesta = self.pantalla(resultado="faltante")

        self.assertContains(respuesta, 'href="?periodo=7&amp;resultado=faltante"')

    def test_cada_fila_pide_su_modal(self):
        respuesta = self.pantalla()

        self.assertContains(
            respuesta, f'hx-get="{reverse("cierre-de-caja-ficha", args=[self.faltante.pk])}"'
        )

    def test_la_diferencia_lleva_su_estado(self):
        respuesta = self.pantalla()

        for estado in ("cuadra", "sobrante", "faltante"):
            with self.subTest(estado=estado):
                self.assertContains(respuesta, f'data-diferencia="{estado}"')

    def test_la_invariante_del_motivo_esta_a_la_vista(self):
        self.assertContains(self.pantalla(), "data-sin-motivo")
        self.assertEqual(self.reporte().resumen.sin_motivo, 0)

    def test_sin_cierres_no_se_inventa_un_cero(self):
        """«$0 de descuadre» se leería como «todo cuadró», y lo que pasa es que
        no se alcanzó ninguna jornada."""
        respuesta = self.pantalla(q="no-existe-este-motivo")

        self.assertContains(respuesta, "data-sin-cierres")
        self.assertNotContains(respuesta, "data-descuadre-total")


class ElEsperadoSeExplicaDesdeLasVentasTest(BaseDelReporteDeCierres):
    """**El tercer criterio de `HU-56`, y no se cumple enseñando la cifra.**

    Esta prueba **sigue el enlace** de la modal y comprueba que lleva a las
    ventas que suman esa cifra. Si alguien cambia los parámetros del enlace, o
    el reporte de ventas pierde el filtro por medio, falla.
    """

    def setUp(self):
        super().setUp()
        self.vender_en_efectivo(cantidad=2)   # 5.000
        self.vender_en_efectivo(cantidad=2)   # 5.000
        self.cierre = cerrar_caja(
            actor=self.cajero, base=Decimal("20000"), efectivo_contado=Decimal("30000"),
        )
        self.entrar_como_administracion()

    def test_la_modal_enlaza_a_las_ventas_de_esa_jornada(self):
        respuesta = self.client.get(reverse("cierre-de-caja-ficha", args=[self.cierre.pk]))

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "<html")
        self.assertContains(
            respuesta,
            f"{reverse('ventas-del-dia', args=[self.cierre.fecha.isoformat()])}"
            f"?medio={MedioDePago.EFECTIVO}",
        )

    def test_seguir_el_enlace_trae_las_ventas_que_suman_el_esperado(self):
        dia = self.cierre.fecha.isoformat()
        ficha = f"{reverse('ventas-del-dia-ficha', args=[dia])}?medio={MedioDePago.EFECTIVO}"
        pagina = self.client.get(reverse("ventas-del-dia", args=[dia]), {"medio": MedioDePago.EFECTIVO})
        self.assertContains(pagina, f'hx-get="{ficha}"')

        respuesta = self.client.get(ficha)

        self.assertEqual(len(respuesta.context["ventas"]), 2)
        self.assertEqual(respuesta.context["total"], self.cierre.efectivo_esperado)

    def test_la_pagina_del_cierre_abre_su_modal_y_acota_la_jornada(self):
        respuesta = self.client.get(reverse("cierre-de-la-cafeteria", args=[self.cierre.pk]))

        self.assertEqual(respuesta.context["reporte"].desde, self.cierre.fecha)
        self.assertEqual(respuesta.context["reporte"].hasta, self.cierre.fecha)
        self.assertContains(
            respuesta, f'hx-get="{reverse("cierre-de-caja-ficha", args=[self.cierre.pk])}"'
        )


class ElCajeroPorSuNombreTest(BaseDelReporteDeCierres):
    """El correo es la credencial de acceso de esa cuenta y no hace falta para
    leer un cuadre (`TT-176`)."""

    def setUp(self):
        super().setUp()
        self.cierre = self.cerrar()
        self.entrar_como_administracion()

    def test_la_tabla_y_el_filtro_dicen_el_nombre_y_no_el_correo(self):
        respuesta = self.pantalla()

        self.assertContains(respuesta, "Diego Ramírez")
        self.assertNotContains(respuesta, self.cajero.email)

    def test_la_modal_tampoco(self):
        respuesta = self.client.get(reverse("cierre-de-caja-ficha", args=[self.cierre.pk]))

        self.assertContains(respuesta, "Diego Ramírez")
        self.assertNotContains(respuesta, self.cajero.email)


class SoloLaAdministracionTest(BaseDelReporteDeCierres):
    """`HU-55` y `HU-56` son dos historias con dos actores distintos: el cajero
    cuadra y no consulta el histórico."""

    def setUp(self):
        super().setUp()
        self.cierre = self.cerrar()
        self.rutas = [
            reverse(PANTALLA),
            reverse("cierre-de-la-cafeteria", args=[self.cierre.pk]),
            reverse("cierre-de-caja-ficha", args=[self.cierre.pk]),
        ]

    def test_la_administracion_entra(self):
        self.entrar_como_administracion()
        for ruta in self.rutas:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_ningun_otro_rol(self):
        for rol in (Rol.CAJERO, Rol.INSTITUCION, Rol.ACUDIENTE):
            self.entrar(rol, f"{rol}-cierres-entra@example.com")
            for ruta in self.rutas:
                with self.subTest(rol=rol, ruta=ruta):
                    self.assertEqual(self.client.get(ruta).status_code, 403)

    def test_sin_sesion_va_al_acceso(self):
        self.assertEqual(self.client.get(reverse(PANTALLA)).status_code, 302)

    def test_el_rol_se_comprueba_antes_que_el_404(self):
        self.entrar(Rol.CAJERO, "cajero-404-cierres@example.com")
        inexistente = "00000000-0000-0000-0000-000000000000"

        self.assertEqual(
            self.client.get(reverse("cierre-de-caja-ficha", args=[inexistente])).status_code, 403
        )

    def test_a_la_administracion_si_le_dice_que_no_existe(self):
        self.entrar_como_administracion()
        inexistente = "00000000-0000-0000-0000-000000000000"

        self.assertEqual(
            self.client.get(reverse("cierre-de-caja-ficha", args=[inexistente])).status_code, 404
        )

    def test_la_ruta_no_comparte_nombre_con_el_cuadre_del_cajero(self):
        """`cierre-de-caja` es `/punto-de-venta/cierre/`, donde el cajero cuadra.
        Con el mismo nombre, Django elegía el patrón por los argumentos y
        funcionaba por casualidad."""
        self.assertEqual(reverse("cierre-de-caja"), "/punto-de-venta/cierre/")
        self.assertEqual(
            reverse("cierre-de-la-cafeteria", args=[self.cierre.pk]), f"/cierres/{self.cierre.pk}/"
        )

    def test_el_listado_del_admin_ya_no_existe(self):
        with self.assertRaises(NoReverseMatch):
            reverse("admin:ventas_cierredecaja_changelist")
        self.entrar_como_administracion()
        self.assertEqual(self.client.get("/admin/ventas/cierredecaja/").status_code, 404)

    def test_esta_en_el_menu_de_la_administracion(self):
        self.entrar_como_administracion()

        self.assertContains(
            self.client.get(reverse("panel-de-la-cafeteria")), f'href="{reverse(PANTALLA)}"'
        )


class NadieEscribeUnCierreDesdeAquiTest(BaseDelReporteDeCierres):
    """Un cierre es un asiento con el efectivo esperado congelado (`INVD-5`): se
    registra en el punto de venta o no existe. Por los dos caminos que `DT-11`
    exige: lo que responde la pantalla **y** el permiso."""

    def setUp(self):
        super().setUp()
        self.cierre = self.cerrar(contado="32000", motivo="Sobró un billete")
        self.entrar_como_administracion()

    def test_las_rutas_solo_responden_a_get(self):
        for ruta in (reverse(PANTALLA), reverse("cierre-de-caja-ficha", args=[self.cierre.pk])):
            with self.subTest(ruta=ruta):
                respuesta = self.client.post(ruta, {"efectivo_esperado": "999999", "motivo": ""})
                self.assertEqual(respuesta.status_code, 405)
        self.cierre.refresh_from_db()
        self.assertEqual(self.cierre.efectivo_esperado, Decimal("10000.00"))
        self.assertEqual(self.cierre.motivo, "Sobró un billete")

    def test_ningun_grupo_tiene_escritura_sobre_el_cierre(self):
        """La mitad que no depende de la pantalla: el permiso **no existe** en
        ningún rol, porque `ventas` está en `APPS_SIN_ESCRITURA_PARA_NINGUN_ROL`."""
        for rol in Rol:
            with self.subTest(rol=rol):
                codigos = set(
                    Permission.objects.filter(
                        group__name=nombre_del_grupo(rol),
                        content_type__app_label="ventas",
                        content_type__model="cierredecaja",
                    ).values_list("codename", flat=True)
                )
                self.assertEqual({c for c in codigos if not c.startswith("view_")}, set())
