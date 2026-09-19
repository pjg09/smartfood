"""`TT-168`. El reporte de ventas en el admin (`HU-35`, `INT-3`).

**El reporte vive en el admin y no en una pantalla propia** (`DT-2`): las dos
excepciones declaradas —el padrón (`DT-27`) y la cola de reservas (`DT-34`)—
existen porque las abre a diario alguien que no es administrador, y aquí quien
consulta es justamente quien vive en el admin. Una tercera excepción tendría que
explicar por qué no es ya un patrón.

Lo que estas pruebas fijan, y que un `ModelAdmin` corriente no daría:

1. **El consolidado es del listado que se está mirando.** Si el resumen
   consultara por su cuenta, filtrar por «efectivo» dejaría arriba el total de
   todo y **nadie lo notaría**: las dos cifras seguirían siendo correctas cada
   una por su lado. Es el fallo más caro que puede tener un reporte.
2. **Nadie escribe una venta desde aquí**, ni siquiera quien la consulta. Se
   comprueba por los dos caminos: las respuestas del admin y la ausencia del
   permiso en el grupo del rol (`DT-11`).
3. **Solo `USR-4`**: el cajero registra ventas y no las reporta.

Las cuentas se crean por el camino real —`sincronizar_grupos_y_permisos` y
`crear_cuenta(..., accede_a_administracion=True)`—: poner `is_staff` a mano deja
una cuenta que entra al admin sin un solo permiso y todo responde `403` por el
motivo equivocado.
"""

from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.permisos import nombre_del_grupo
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from ventas.models import MedioDePago, Venta
from ventas.services import registrar_venta

LISTADO = "admin:ventas_venta_changelist"


class BaseDelAdmin(TestCase):
    """Una cafetería con ventas de los dos medios y las cuentas del admin."""

    def setUp(self):
        sincronizar_grupos_y_permisos()
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero-admin@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        acudiente = Usuario.objects.crear_usuario(
            email="marta-admin@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
        )
        ficha = Acudiente.objects.create(
            usuario=acudiente, nombre="Marta Ruiz", documento="4310088001"
        )
        self.estudiante = Estudiante.objects.create(
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001088001",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        recargar(actor=acudiente, estudiante=self.estudiante, monto=Decimal("100000"))

        categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
        self.pan = Producto.objects.create(
            nombre="Pan de queso", precio=Decimal("2500"), categoria=categoria
        )
        MovimientoInventario.objects.create(
            producto=self.pan,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=100,
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
        return self.entrar(Rol.ADMINISTRADOR, "administracion-admin@example.com")

    def vender_a_estudiante(self, cantidad=1):
        return registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante,
            lineas={self.pan.id: cantidad},
        )

    def vender_en_efectivo(self, cantidad=1):
        return registrar_venta(
            actor=self.cajero,
            lineas={self.pan.id: cantidad},
            medio_pago=MedioDePago.EFECTIVO,
        )


class ElConsolidadoEsDelListadoQueSeMiraTest(BaseDelAdmin):
    """**La prueba que justifica que el reporte esté en el admin.**"""

    def setUp(self):
        super().setUp()
        self.vender_a_estudiante(cantidad=2)   # billetera, 5.000
        self.vender_en_efectivo(cantidad=4)    # efectivo, 10.000
        self.entrar_como_administracion()

    def resumen_de(self, **filtros):
        respuesta = self.client.get(reverse(LISTADO), filtros)
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.context["resumen"]

    def test_sin_filtros_suma_todas_las_ventas(self):
        resumen = self.resumen_de()

        self.assertEqual(resumen.cuantas, 2)
        self.assertEqual(resumen.total, Decimal("15000.00"))
        self.assertEqual(resumen.unidades, 6)

    def test_al_filtrar_el_consolidado_se_filtra_con_el(self):
        """Si esto falla, el total de arriba está hablando de otro conjunto que
        la tabla de abajo, y las dos cifras parecen correctas."""
        resumen = self.resumen_de(medio_pago=MedioDePago.EFECTIVO)

        self.assertEqual(resumen.cuantas, 1)
        self.assertEqual(resumen.total, Decimal("10000.00"))
        self.assertEqual(resumen.unidades, 4)

    def test_la_busqueda_tambien_acota_el_consolidado(self):
        """La búsqueda es por el nombre del estudiante, así que deja fuera la
        venta genérica."""
        resumen = self.resumen_de(q="Ana Sofía")

        self.assertEqual(resumen.cuantas, 1)
        self.assertEqual(resumen.total, Decimal("5000.00"))

    def test_un_filtro_sin_resultados_no_inventa_un_cero(self):
        """Sin ventas no se pinta «$0»: se dice que el filtro no alcanzó
        ninguna, que es otra cosa."""
        respuesta = self.client.get(
            reverse(LISTADO), {"medio_pago": MedioDePago.TRANSFERENCIA}
        )

        self.assertFalse(respuesta.context["resumen"].hubo_ventas)
        self.assertContains(respuesta, "data-sin-ventas")

    def test_los_desgloses_cuadran_con_el_total_del_listado(self):
        """**El fallo que la pantalla enseñó y las pruebas del selector no.**

        El admin ordena el listado explícitamente, y un `order_by()` explícito
        entra en el `GROUP BY` de un `values().annotate()`: sin limpiarlo, cada
        venta forma su propio grupo y las tres filas del desglose dicen «1»
        mientras el total de arriba —que sale por `aggregate()`— sigue bien.

        Por eso aquí se comprueba contra el consolidado y no contra cifras
        escritas a mano: lo que tiene que cuadrar es que las dos mitades de la
        misma pantalla hablen del mismo conjunto.
        """
        # Dos más de billetera, sobre la que ya trae el escenario: son tres, y
        # hacen falta al menos dos para que agrupar mal se note.
        self.vender_a_estudiante(cantidad=1)
        self.vender_a_estudiante(cantidad=3)

        resumen = self.client.get(reverse(LISTADO)).context["resumen"]

        self.assertEqual(
            sum(cuantas for _, cuantas, _ in resumen.por_medio_de_pago),
            resumen.cuantas,
        )
        self.assertEqual(
            sum(total for _, _, total in resumen.por_medio_de_pago), resumen.total
        )
        por_medio = {
            etiqueta: cuantas for etiqueta, cuantas, _ in resumen.por_medio_de_pago
        }
        self.assertEqual(por_medio[MedioDePago.BILLETERA.label], 3)

    def test_la_pantalla_enseña_el_consolidado_y_sus_desgloses(self):
        respuesta = self.client.get(reverse(LISTADO))

        self.assertContains(respuesta, "data-resumen-de-ventas")
        self.assertContains(respuesta, "data-total-vendido")
        self.assertContains(respuesta, "data-por-medio-de-pago")
        self.assertContains(respuesta, "data-por-origen")


class SoloLaAdministracionEntraAlReporteTest(BaseDelAdmin):
    """`[S11]`: «consultar reportes de ventas e inventario» es de `USR-4`."""

    def test_la_administracion_entra(self):
        self.entrar_como_administracion()

        respuesta = self.client.get(reverse(LISTADO))

        self.assertEqual(respuesta.status_code, 200)

    def test_el_cajero_no_entra_aunque_registre_las_ventas(self):
        self.entrar(Rol.CAJERO, "cajero-entra@example.com")

        self.assertEqual(self.client.get(reverse(LISTADO)).status_code, 403)

    def test_la_institucion_no_entra(self):
        self.entrar(Rol.INSTITUCION, "institucion-entra@example.com")

        self.assertEqual(self.client.get(reverse(LISTADO)).status_code, 403)

    def test_el_acudiente_no_entra_ni_al_admin(self):
        """`INT-1` no es el admin (`DT-2`): sin `is_staff` el admin redirige a
        su propia pantalla de acceso."""
        self.entrar(Rol.ACUDIENTE, "acudiente-entra@example.com", staff=False)

        self.assertEqual(self.client.get(reverse(LISTADO)).status_code, 302)


class NadieEscribeUnaVentaDesdeElAdminTest(BaseDelAdmin):
    """Una venta es un asiento: se registra en el punto de venta, con su
    transacción, o no existe (`INV-1`, `INV-2`, `INV-3`).

    Se comprueba por los dos caminos que `DT-11` exige: lo que responde la
    pantalla **y** que el permiso no exista en el grupo del rol.
    """

    def setUp(self):
        super().setUp()
        self.venta = self.vender_a_estudiante()
        self.entrar_como_administracion()

    def test_el_alta_responde_403(self):
        self.assertEqual(
            self.client.get(reverse("admin:ventas_venta_add")).status_code, 403
        )

    def test_la_ficha_es_de_solo_lectura(self):
        """Con `view` y sin `change`, el admin pinta la ficha en modo lectura:
        responde `200` y **no** trae formulario de guardado."""
        respuesta = self.client.get(
            reverse("admin:ventas_venta_change", args=[self.venta.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.context["has_change_permission"])
        self.assertFalse(respuesta.context["has_delete_permission"])

    def test_un_post_a_la_ficha_no_la_cambia(self):
        respuesta = self.client.post(
            reverse("admin:ventas_venta_change", args=[self.venta.pk]),
            {"medio_pago": MedioDePago.EFECTIVO},
        )

        self.assertEqual(respuesta.status_code, 403)
        self.venta.refresh_from_db()
        self.assertEqual(self.venta.medio_pago, MedioDePago.BILLETERA)

    def test_el_borrado_responde_403(self):
        respuesta = self.client.get(
            reverse("admin:ventas_venta_delete", args=[self.venta.pk])
        )

        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(Venta.objects.filter(pk=self.venta.pk).exists())

    def test_ningun_grupo_tiene_permiso_de_escritura_sobre_ventas(self):
        """La otra mitad, y la que no depende de la pantalla: el permiso **no
        existe** en ningún rol. `ventas` está en
        `APPS_SIN_ESCRITURA_PARA_NINGUN_ROL`, y `restricciones/tests_permisos.py`
        lo recorre entero; aquí se fija además el caso concreto.
        """
        for rol in Rol:
            with self.subTest(rol=rol):
                codigos = set(
                    Permission.objects.filter(
                        group__name=nombre_del_grupo(rol),
                        content_type__app_label="ventas",
                    ).values_list("codename", flat=True)
                )
                escrituras = {
                    c
                    for c in codigos
                    if c.startswith(("add_", "change_", "delete_"))
                }
                self.assertEqual(escrituras, set())


class LaFichaExplicaDeQueSeCompusoLaVentaTest(BaseDelAdmin):
    """El inline de renglones, con **los precios de entonces** (`DT-8`).

    «$12.000» no dice si fueron tres empanadas o un almuerzo, y el primer
    criterio de `HU-35` solo significa algo si las transacciones se pueden
    abrir.
    """

    def test_la_ficha_enseña_los_renglones_con_su_precio_congelado(self):
        venta = self.vender_a_estudiante(cantidad=2)
        self.pan.precio = Decimal("9900")
        self.pan.save(update_fields=["precio"])
        self.entrar_como_administracion()

        respuesta = self.client.get(
            reverse("admin:ventas_venta_change", args=[venta.pk])
        )

        self.assertContains(respuesta, "$2.500")
        self.assertNotContains(respuesta, "$9.900")

    def test_la_ficha_tampoco_enseña_el_documento_del_estudiante(self):
        """**El listado no era suficiente.**

        Un campo de relación se pinta con el `__str__` del modelo apuntado, y el
        de `Estudiante` es «Nombre (documento)»: la ficha lo enseñaba enlazado
        mientras el listado se cuidaba de no hacerlo. Se vio en la captura.
        """
        venta = self.vender_a_estudiante()
        self.entrar_como_administracion()

        respuesta = self.client.get(
            reverse("admin:ventas_venta_change", args=[venta.pk])
        )

        self.assertContains(respuesta, self.estudiante.nombre)
        self.assertNotContains(respuesta, self.estudiante.documento)
        self.assertNotContains(respuesta, self.estudiante.codigo_tarjeta)

    def test_el_listado_no_enseña_el_documento_ni_el_codigo_de_tarjeta(self):
        """La cafetería consulta su actividad comercial, no el padrón: el
        código es la credencial de acceso al saldo (`INV-7`) y el documento es
        un dato personal de un menor (`ALC-OUT-08`)."""
        self.vender_a_estudiante()
        self.entrar_como_administracion()

        respuesta = self.client.get(reverse(LISTADO))

        self.assertNotContains(respuesta, self.estudiante.documento)
        self.assertNotContains(respuesta, self.estudiante.codigo_tarjeta)
