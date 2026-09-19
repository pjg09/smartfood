"""`TT-176`. El reporte de cierres de caja en el admin (`HU-56`, `INT-3`).

Vive en el admin por lo mismo que el de ventas (`TT-168`) y el de inventario
(`TT-170`): quien lo consulta es la administración de la cafetería, que trabaja
ahí (`DT-2`). **No abre una tercera excepción.**

Lo que estas pruebas fijan, y que un `ModelAdmin` corriente no daría:

1. **El consolidado es del listado que se está mirando.** Igual que en los otros
   dos reportes, y por el mismo motivo: si consultara por su cuenta, filtrar por
   «con faltante» dejaría arriba el descuadre de todo el periodo y nadie lo
   notaría.
2. **El enlace que hace comprobable `INVD-5`.** El tercer criterio de `HU-56`
   dice que el efectivo esperado de un día se explica desde sus ventas en
   efectivo registradas. Una columna con una cifra no explica nada: hay que
   poder abrirla. `ElEsperadoSeExplicaDesdeLasVentasTest` **sigue el enlace** y
   comprueba que las ventas que trae suman esa cifra.
3. **Nadie escribe un cierre desde aquí**, ni siquiera quien lo consulta.
4. **La pantalla no enseña el correo del cajero**: el `__str__` de `Usuario` es
   «correo (rol)», y un campo de relación se pinta con él.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.permisos import nombre_del_grupo
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from ventas.models import CierreDeCaja, MedioDePago
from ventas.services import cerrar_caja, registrar_venta

LISTADO = "admin:ventas_cierredecaja_changelist"


class BaseDelReporteDeCierres(TestCase):
    """Un cajero que cobra y cuadra, y las cuentas del admin."""

    def setUp(self):
        sincronizar_grupos_y_permisos()
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero-cierres-admin@example.com",
            rol=Rol.CAJERO,
            nombre="Diego Ramírez",
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
            email=email,
            rol=rol,
            nombre="Persona",
            accede_a_administracion=staff,
            enviar_invitacion=False,
        )
        self.client.force_login(usuario)
        return usuario

    def entrar_como_administracion(self):
        return self.entrar(Rol.ADMINISTRADOR, "administracion-cierres@example.com")

    def vender_en_efectivo(self, cantidad=1):
        return registrar_venta(
            actor=self.cajero,
            lineas={self.pan.id: cantidad},
            medio_pago=MedioDePago.EFECTIVO,
        )

    def cerrar(self, *, dias_atras=0, esperado="10000", base="20000", contado=None,
               motivo=""):
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
            cajero=self.cajero,
            base=base,
            efectivo_esperado=esperado,
            efectivo_contado=Decimal(contado),
            motivo=motivo,
        )


class ElConsolidadoEsDelListadoQueSeMiraTest(BaseDelReporteDeCierres):
    """**La prueba que justifica que el reporte esté en el admin.**"""

    def setUp(self):
        super().setUp()
        self.cerrar(dias_atras=0)                                        # cuadra
        self.cerrar(dias_atras=1, contado="32000", motivo="Sobró")       # +2.000
        self.cerrar(dias_atras=2, contado="27000", motivo="Faltó")       # -3.000
        self.entrar_como_administracion()

    def resumen_de(self, **filtros):
        respuesta = self.client.get(reverse(LISTADO), filtros)
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.context["resumen"]

    def test_sin_filtros_resume_el_historico(self):
        resumen = self.resumen_de()

        self.assertEqual(resumen.cuantos, 3)
        self.assertEqual(resumen.cuadrados, 1)
        self.assertEqual(resumen.descuadre_total, Decimal("5000.00"))
        self.assertEqual(resumen.diferencia_neta, Decimal("-1000.00"))

    def test_al_filtrar_por_faltante_el_consolidado_se_filtra_con_el(self):
        """Si esto falla, el descuadre de arriba habla de otro conjunto que la
        tabla de abajo, y las dos cifras parecen correctas."""
        resumen = self.resumen_de(cuadre="faltante")

        self.assertEqual(resumen.cuantos, 1)
        self.assertEqual(resumen.faltantes, 1)
        self.assertEqual(resumen.descuadre_total, Decimal("3000.00"))

    def test_el_filtro_de_cuadre_distingue_las_tres_clases(self):
        """Es un `SimpleListFilter` porque lo que separa las tres **no es una
        columna**: es el signo de una resta."""
        self.assertEqual(self.resumen_de(cuadre="cuadra").cuantos, 1)
        self.assertEqual(self.resumen_de(cuadre="sobrante").cuantos, 1)
        self.assertEqual(self.resumen_de(cuadre="faltante").cuantos, 1)

    def test_un_filtro_sin_resultados_no_inventa_un_cero(self):
        """«$0 de descuadre» se leería como «todo cuadró», y lo que pasa es que
        el filtro no alcanzó ninguna jornada."""
        respuesta = self.client.get(
            reverse(LISTADO), {"fecha__year": self.hoy.year - 5}
        )

        self.assertFalse(respuesta.context["resumen"].hubo_cierres)
        self.assertContains(respuesta, "data-sin-cierres")

    def test_la_pantalla_enseña_el_consolidado_y_sus_tablas(self):
        respuesta = self.client.get(reverse(LISTADO))

        self.assertContains(respuesta, "data-resumen-de-cierres")
        self.assertContains(respuesta, "data-descuadre-total")
        self.assertContains(respuesta, "data-por-resultado")
        self.assertContains(respuesta, "data-por-concepto")
        self.assertContains(respuesta, "data-sin-motivo")

    def test_las_tres_clases_suman_las_jornadas_del_listado(self):
        """Lo que tiene que cuadrar es que las dos mitades de la pantalla hablen
        del mismo conjunto, como en el reporte de ventas."""
        resumen = self.resumen_de()

        self.assertEqual(
            resumen.cuadrados + resumen.sobrantes + resumen.faltantes,
            resumen.cuantos,
        )


class ElEsperadoSeExplicaDesdeLasVentasTest(BaseDelReporteDeCierres):
    """**El tercer criterio de `HU-56`, y no se cumple enseñando la cifra.**

    «El efectivo esperado de un día se explica a partir de sus ventas en
    efectivo registradas» (`INVD-5`). Una columna con `$10.000` hay que
    creérsela; lo que la explica es poder abrirla.

    Esta prueba **sigue el enlace** y comprueba que el listado al que lleva trae
    justamente las ventas que suman esa cifra. Si alguien cambia los parámetros
    del enlace, o el reporte de ventas pierde su navegación por fechas, falla.
    """

    def setUp(self):
        super().setUp()
        self.vender_en_efectivo(cantidad=2)   # 5.000
        self.vender_en_efectivo(cantidad=2)   # 5.000
        self.cierre = cerrar_caja(
            actor=self.cajero,
            base=Decimal("20000"),
            efectivo_contado=Decimal("30000"),
        )
        self.entrar_como_administracion()

    def test_la_ficha_enlaza_a_las_ventas_de_esa_jornada(self):
        respuesta = self.client.get(
            reverse("admin:ventas_cierredecaja_change", args=[self.cierre.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, reverse("admin:ventas_venta_changelist"))
        self.assertContains(respuesta, f"creado_en__day={self.hoy.day}")
        self.assertContains(respuesta, f"medio_pago__exact={MedioDePago.EFECTIVO}")

    def test_seguir_el_enlace_trae_las_ventas_que_suman_el_esperado(self):
        """La comprobación de verdad: el destino existe, responde y su
        consolidado coincide con el efectivo esperado del cierre."""
        destino = reverse("admin:ventas_venta_changelist")

        respuesta = self.client.get(
            destino,
            {
                "medio_pago__exact": MedioDePago.EFECTIVO,
                "creado_en__year": self.hoy.year,
                "creado_en__month": self.hoy.month,
                "creado_en__day": self.hoy.day,
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        resumen = respuesta.context["resumen"]
        self.assertEqual(resumen.cuantas, 2)
        self.assertEqual(resumen.total, self.cierre.efectivo_esperado)


class LaPantallaNoEnseñaElCorreoDelCajeroTest(BaseDelReporteDeCierres):
    """Un campo de relación se pinta con el `__str__` del modelo apuntado, y el
    de `Usuario` es «correo (rol)».

    Es la misma trampa que `TT-168` pagó con `Estudiante.__str__` y el documento
    del menor. Aquí no hay un menor de por medio, pero el correo es la
    credencial de acceso de esa cuenta y no hace falta para leer un cuadre — y
    el rol es siempre el mismo: todos los cierres los firma un cajero.
    """

    def setUp(self):
        super().setUp()
        self.cierre = self.cerrar()
        self.entrar_como_administracion()

    def test_el_listado_dice_el_nombre_y_no_el_correo(self):
        respuesta = self.client.get(reverse(LISTADO))

        self.assertContains(respuesta, "Diego Ramírez")
        self.assertNotContains(respuesta, self.cajero.email)

    def test_la_ficha_tampoco(self):
        respuesta = self.client.get(
            reverse("admin:ventas_cierredecaja_change", args=[self.cierre.pk])
        )

        self.assertContains(respuesta, "Diego Ramírez")
        self.assertNotContains(respuesta, self.cajero.email)


class SoloLaAdministracionEntraAlReporteDeCierresTest(BaseDelReporteDeCierres):
    """`HU-55` y `HU-56` son dos historias con dos actores distintos."""

    def test_la_administracion_entra(self):
        self.entrar_como_administracion()

        self.assertEqual(self.client.get(reverse(LISTADO)).status_code, 200)

    def test_el_cajero_no_entra_aunque_escriba_los_cierres(self):
        """No es un olvido: `[S5]` del anteproyecto dice que el trabajo del
        administrador «no se centra en cada transacción individual, sino en la
        información acumulada»."""
        self.entrar(Rol.CAJERO, "cajero-entra-cierres@example.com")

        self.assertEqual(self.client.get(reverse(LISTADO)).status_code, 403)

    def test_la_institucion_no_entra(self):
        self.entrar(Rol.INSTITUCION, "institucion-entra-cierres@example.com")

        self.assertEqual(self.client.get(reverse(LISTADO)).status_code, 403)

    def test_el_acudiente_no_entra_ni_al_admin(self):
        self.entrar(Rol.ACUDIENTE, "acudiente-entra-cierres@example.com", staff=False)

        self.assertEqual(self.client.get(reverse(LISTADO)).status_code, 302)


class NadieEscribeUnCierreDesdeElAdminTest(BaseDelReporteDeCierres):
    """Un cierre es un asiento con el efectivo esperado congelado (`INVD-5`).

    Se registra en el punto de venta, con la cifra calculada en ese momento, o no
    existe. Editarlo sería peor que registrarlo mal: reescribiría un descuadre ya
    explicado por escrito.

    Se comprueba por los dos caminos que `DT-11` exige: lo que responde la
    pantalla **y** que el permiso no exista en el grupo del rol.
    """

    def setUp(self):
        super().setUp()
        self.cierre = self.cerrar(contado="32000", motivo="Sobró un billete")
        self.entrar_como_administracion()

    def test_el_alta_responde_403(self):
        self.assertEqual(
            self.client.get(reverse("admin:ventas_cierredecaja_add")).status_code, 403
        )

    def test_la_ficha_es_de_solo_lectura(self):
        respuesta = self.client.get(
            reverse("admin:ventas_cierredecaja_change", args=[self.cierre.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.context["has_change_permission"])
        self.assertFalse(respuesta.context["has_delete_permission"])

    def test_un_post_a_la_ficha_no_reescribe_el_esperado(self):
        respuesta = self.client.post(
            reverse("admin:ventas_cierredecaja_change", args=[self.cierre.pk]),
            {"efectivo_esperado": "999999", "motivo": ""},
        )

        self.assertEqual(respuesta.status_code, 403)
        self.cierre.refresh_from_db()
        self.assertEqual(self.cierre.efectivo_esperado, Decimal("10000.00"))
        self.assertEqual(self.cierre.motivo, "Sobró un billete")

    def test_el_borrado_responde_403(self):
        respuesta = self.client.get(
            reverse("admin:ventas_cierredecaja_delete", args=[self.cierre.pk])
        )

        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(CierreDeCaja.objects.filter(pk=self.cierre.pk).exists())

    def test_ningun_grupo_tiene_escritura_sobre_el_cierre(self):
        """La otra mitad, y la que no depende de la pantalla: el permiso **no
        existe** en ningún rol, porque `ventas` está en
        `APPS_SIN_ESCRITURA_PARA_NINGUN_ROL`."""
        for rol in Rol:
            with self.subTest(rol=rol):
                codigos = set(
                    Permission.objects.filter(
                        group__name=nombre_del_grupo(rol),
                        content_type__app_label="ventas",
                        content_type__model="cierredecaja",
                    ).values_list("codename", flat=True)
                )
                self.assertEqual(
                    {c for c in codigos if not c.startswith("view_")}, set()
                )

    def test_solo_la_administracion_tiene_el_permiso_de_lectura(self):
        con_permiso = {
            rol
            for rol in Rol
            if Permission.objects.filter(
                group__name=nombre_del_grupo(rol),
                content_type__app_label="ventas",
                content_type__model="cierredecaja",
                codename="view_cierredecaja",
            ).exists()
        }

        self.assertEqual(con_permiso, {Rol.ADMINISTRADOR})
