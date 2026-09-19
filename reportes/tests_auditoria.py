"""`TT-177`, `TT-178`. El reporte de auditoría (`HU-37`, `ALC-IN-22`).

Único criterio de la historia: **se construye sobre las transacciones
registradas**. Aquí eso significa algo concreto y comprobable: no hay tabla de
auditoría, así que ninguna operación se escribe dos veces. Lo que estas pruebas
fijan es lo que esa decisión obliga a acertar:

1. **Una venta del mostrador es una operación, no dos.** El cobro asienta la
   venta y su salida de inventario en la misma transacción, así que incluir los
   movimientos de tipo venta pondría cada venta dos veces con el mismo instante
   y el mismo actor. `NingunaOperacionSeCuentaDosVecesTest`.
2. **La entrega sí es una operación aparte**, y es la que más fácil se cae: no
   crea venta ni mueve saldo, solo cambia un estado y descuenta existencias.
3. **Quién**, que es el «para» de la historia. El cajero cobra, el acudiente
   reserva, el cajero entrega, el cajero cuadra — y el ingreso y la merma **no
   lo registran**, que es un hueco declarado y no un fallo.
4. **Todas las operaciones se pueden abrir.** Si una clase apuntara a un modelo
   sin admin, la pantalla reventaría al pintar: `TodasLasOperacionesSeAbrenTest`
   lo comprueba resolviendo cada ruta.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from inventario.services import ingresar_mercancia, registrar_merma
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from reportes.selectors import auditoria, resumen_de_auditoria
from ventas.models import MedioDePago, Venta
from ventas.services import cerrar_caja, entregar, registrar_venta, reservar


class BaseDeLaAuditoria(TestCase):
    """Una jornada con una operación de cada clase."""

    def setUp(self):
        sincronizar_grupos_y_permisos()
        self.administracion = crear_cuenta(
            email="auditoria-admin@example.com",
            rol=Rol.ADMINISTRADOR,
            nombre="Administración",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.cajero = Usuario.objects.crear_usuario(
            email="auditoria-cajero@example.com", rol=Rol.CAJERO, nombre="Diego Ramírez"
        )
        self.acudiente = Usuario.objects.crear_usuario(
            email="auditoria-acu@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
        )
        ficha = Acudiente.objects.create(
            usuario=self.acudiente, nombre="Marta Ruiz Ochoa", documento="4310066001"
        )
        self.estudiante = Estudiante.objects.create(
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001066001",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("100000")
        )
        categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
        self.pan = Producto.objects.create(
            nombre="Pan de queso", precio=Decimal("2500"), categoria=categoria
        )
        ingresar_mercancia(
            actor=self.administracion,
            producto=self.pan,
            cantidad=100,
            motivo="Compra semanal",
        )

    def operaciones(self, **filtros):
        operaciones, _ = auditoria(actor=self.administracion, **filtros)
        return operaciones

    def clases_de(self, operaciones):
        return [operacion.clase for operacion in operaciones]


class LasCuatroClasesEntranEnLaLineaDeTiempoTest(BaseDeLaAuditoria):
    """`TT-177`: consolida ventas, movimientos de inventario y cierres — más la
    entrega, que es una operación por derecho propio."""

    def setUp(self):
        super().setUp()
        registrar_venta(
            actor=self.cajero, estudiante=self.estudiante, lineas={self.pan.id: 2}
        )
        pedido = reservar(
            actor=self.acudiente, estudiante=self.estudiante, lineas={self.pan.id: 1}
        )
        entregar(actor=self.cajero, pedido=pedido)
        registrar_merma(
            actor=self.administracion,
            producto=self.pan,
            cantidad=3,
            motivo="Se cayó una bandeja",
        )
        cerrar_caja(
            actor=self.cajero, base=Decimal("0"), efectivo_contado=Decimal("0")
        )

    def test_estan_las_cuatro(self):
        clases = set(self.clases_de(self.operaciones()))

        self.assertEqual(clases, {"venta", "entrega", "inventario", "cierre"})

    def test_van_de_la_mas_reciente_a_la_mas_antigua(self):
        cuandos = [operacion.cuando for operacion in self.operaciones()]

        self.assertEqual(cuandos, sorted(cuandos, reverse=True))

    def test_el_resumen_cuenta_lo_mismo_que_la_lista(self):
        operaciones = self.operaciones()
        resumen = resumen_de_auditoria(operaciones)

        self.assertEqual(resumen.cuantas, len(operaciones))
        self.assertEqual(
            sum(cuantas for _, cuantas in resumen.por_clase), resumen.cuantas
        )


class NingunaOperacionSeCuentaDosVecesTest(BaseDeLaAuditoria):
    """**La prueba que justifica dejar fuera los movimientos de tipo venta.**

    Un cobro asienta la venta y su salida de inventario a la vez (`HU-21`). Si
    los dos entraran, cada venta saldría dos veces con el mismo instante y el
    mismo actor, y el recuento de un reporte de auditoría diría el doble.
    """

    def test_una_venta_del_mostrador_es_una_sola_operacion(self):
        registrar_venta(
            actor=self.cajero, lineas={self.pan.id: 3}, medio_pago=MedioDePago.EFECTIVO
        )

        clases = self.clases_de(self.operaciones())

        self.assertEqual(clases.count("venta"), 1)
        # Y el movimiento que descontó esas tres unidades **no** aparece aparte:
        # el único de inventario es el ingreso del escenario.
        self.assertEqual(clases.count("inventario"), 1)

    def test_una_reserva_entregada_son_dos_operaciones_y_no_tres(self):
        """Pagar y recoger son dos momentos y dos personas, así que son dos
        líneas. La salida de inventario que asienta la entrega **no** es una
        tercera: la explica la entrega, que además dice quién."""
        pedido = reservar(
            actor=self.acudiente, estudiante=self.estudiante, lineas={self.pan.id: 2}
        )
        entregar(actor=self.cajero, pedido=pedido)

        clases = self.clases_de(self.operaciones())

        self.assertEqual(clases.count("venta"), 1)
        self.assertEqual(clases.count("entrega"), 1)
        self.assertEqual(clases.count("inventario"), 1)


class QuienHizoQueTest(BaseDeLaAuditoria):
    """El «para» de `HU-37`: rastrear quién hizo qué cuando algo no cuadre."""

    def una(self, clase):
        return next(o for o in self.operaciones() if o.clase == clase)

    def test_la_venta_del_mostrador_la_firma_el_cajero(self):
        registrar_venta(
            actor=self.cajero, lineas={self.pan.id: 1}, medio_pago=MedioDePago.EFECTIVO
        )

        self.assertEqual(self.una("venta").quien, "Diego Ramírez")

    def test_la_reserva_la_firma_el_acudiente_y_no_un_cajero(self):
        """Una reserva no tiene cajero —la restricción no lo admite (`DT-32`)—,
        así que el actor sale del acudiente del estudiante. Sin esto, la
        operación aparecería sin nadie."""
        reservar(
            actor=self.acudiente, estudiante=self.estudiante, lineas={self.pan.id: 1}
        )

        operacion = self.una("venta")
        self.assertEqual(operacion.quien, "Marta Ruiz Ochoa")
        self.assertTrue(operacion.tiene_actor)

    def test_la_entrega_la_firma_quien_entrego(self):
        pedido = reservar(
            actor=self.acudiente, estudiante=self.estudiante, lineas={self.pan.id: 1}
        )
        entregar(actor=self.cajero, pedido=pedido)

        self.assertEqual(self.una("entrega").quien, "Diego Ramírez")

    def test_el_cierre_lo_firma_el_cajero_que_conto(self):
        cerrar_caja(
            actor=self.cajero, base=Decimal("0"), efectivo_contado=Decimal("0")
        )

        self.assertEqual(self.una("cierre").quien, "Diego Ramírez")

    def test_el_ingreso_y_la_merma_no_registran_quien_y_se_dice(self):
        """**El hueco declarado.** `MovimientoInventario` recibe el `actor`, lo
        comprueba y no lo guarda, así que estas dos operaciones no pueden decir
        quién. `quien` es `None` —no una cadena vacía ni un «desconocido»— para
        que la pantalla pueda decirlo con palabras."""
        registrar_merma(
            actor=self.administracion, producto=self.pan, cantidad=2, motivo="Rotura"
        )

        de_inventario = [o for o in self.operaciones() if o.clase == "inventario"]

        self.assertEqual(len(de_inventario), 2)  # el ingreso y la merma
        for operacion in de_inventario:
            with self.subTest(accion=operacion.accion):
                self.assertIsNone(operacion.quien)
                self.assertFalse(operacion.tiene_actor)

    def test_el_resumen_cuenta_las_que_no_dicen_quien(self):
        registrar_venta(
            actor=self.cajero, lineas={self.pan.id: 1}, medio_pago=MedioDePago.EFECTIVO
        )

        resumen = resumen_de_auditoria(self.operaciones())

        # Solo el ingreso del escenario: la venta sí dice quién.
        self.assertEqual(resumen.sin_actor, 1)


class TodasLasOperacionesSeAbrenTest(BaseDeLaAuditoria):
    """Un renglón de auditoría que no se puede abrir obliga a buscar la fila a
    mano, que es lo que no se hace cuando algo no cuadra.

    Y si una clase apuntara a un modelo sin admin —`PedidoAnticipado` no lo
    tiene—, la pantalla reventaría con `NoReverseMatch` **al pintar**. Esto lo
    caza antes, resolviendo cada ruta.
    """

    def setUp(self):
        super().setUp()
        registrar_venta(
            actor=self.cajero, lineas={self.pan.id: 1}, medio_pago=MedioDePago.EFECTIVO
        )
        pedido = reservar(
            actor=self.acudiente, estudiante=self.estudiante, lineas={self.pan.id: 1}
        )
        entregar(actor=self.cajero, pedido=pedido)
        registrar_merma(
            actor=self.administracion, producto=self.pan, cantidad=1, motivo="Rotura"
        )
        cerrar_caja(
            actor=self.cajero, base=Decimal("0"), efectivo_contado=Decimal("2500")
        )

    def test_cada_operacion_resuelve_su_ruta_del_admin(self):
        operaciones = self.operaciones()

        self.assertGreaterEqual(len(operaciones), 5)
        for operacion in operaciones:
            with self.subTest(clase=operacion.clase, accion=operacion.accion):
                self.assertTrue(
                    reverse(operacion.ruta_admin, args=[operacion.objeto_id])
                )

    def test_la_entrega_apunta_a_su_venta_porque_el_pedido_no_tiene_admin(self):
        entrega = next(o for o in self.operaciones() if o.clase == "entrega")

        self.assertEqual(entrega.modelo, "ventas.venta")
        self.assertTrue(Venta.objects.filter(pk=entrega.objeto_id).exists())


class ElPeriodoYElTopeTest(BaseDeLaAuditoria):
    """Acotar y no recortar en silencio."""

    def test_el_periodo_deja_fuera_lo_de_otro_dia(self):
        registrar_venta(
            actor=self.cajero, lineas={self.pan.id: 1}, medio_pago=MedioDePago.EFECTIVO
        )
        ayer = timezone.localdate() - timedelta(days=1)

        de_ayer = self.operaciones(desde=ayer, hasta=ayer)

        self.assertEqual(de_ayer, [])

    def test_sin_fechas_devuelve_todo_lo_registrado(self):
        registrar_venta(
            actor=self.cajero, lineas={self.pan.id: 1}, medio_pago=MedioDePago.EFECTIVO
        )

        self.assertEqual(len(self.operaciones()), 2)  # el ingreso y la venta

    def test_el_tope_recorta_y_lo_dice(self):
        """**Recortar sin decirlo sería lo peor que puede hacer un reporte de
        auditoría**: quien lo lee concluiría que no hubo más operaciones."""
        for _ in range(4):
            registrar_venta(
                actor=self.cajero,
                lineas={self.pan.id: 1},
                medio_pago=MedioDePago.EFECTIVO,
            )

        operaciones, hubo_mas = auditoria(actor=self.administracion, limite=3)

        self.assertEqual(len(operaciones), 3)
        self.assertTrue(hubo_mas)

    def test_sin_recorte_no_dice_que_hubo_mas(self):
        operaciones, hubo_mas = auditoria(actor=self.administracion, limite=50)

        self.assertFalse(hubo_mas)
        self.assertEqual(len(operaciones), 1)


class SoloLaAdministracionAuditaTest(BaseDeLaAuditoria):
    """`[S11]`: los reportes de la operación son de `USR-4`."""

    def test_los_otros_tres_roles_no_entran(self):
        for actor in (self.cajero, self.acudiente):
            with self.subTest(rol=actor.rol):
                with self.assertRaises(PermissionDenied):
                    auditoria(actor=actor)

        institucion = Usuario.objects.crear_usuario(
            email="auditoria-inst@example.com", rol=Rol.INSTITUCION, nombre="Secretaría"
        )
        with self.assertRaises(PermissionDenied):
            auditoria(actor=institucion)

    def test_el_rechazo_nombra_la_auditoria_y_no_los_otros_reportes(self):
        """El rol exigido es el mismo que para los otros tres, **y el mensaje
        no**: decirle «los reportes de ventas e inventario» a quien pidió la
        auditoría nombra otros reportes y otra historia."""
        with self.assertRaises(PermissionDenied) as capturado:
            auditoria(actor=self.cajero)

        mensaje = str(capturado.exception)
        self.assertIn("HU-37", mensaje)
        self.assertNotIn("inventario", mensaje.lower())
        # Y concuerda: el sujeto es singular. «El reporte de auditoría **son**
        # de la administración» es lo que salía antes, y se vio ejecutándolo.
        self.assertIn("Consultar el reporte de auditoría es", mensaje)


class LaPantallaDeAuditoriaTest(BaseDeLaAuditoria):
    """`TT-178`. Lo que se puede hacer desde `/admin/auditoria/`."""

    def setUp(self):
        super().setUp()
        self.url = reverse("auditoria")
        registrar_merma(
            actor=self.administracion, producto=self.pan, cantidad=1, motivo="Rotura"
        )

    def test_la_administracion_entra_y_ve_la_linea_de_tiempo(self):
        self.client.force_login(self.administracion)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-resumen-de-auditoria")
        self.assertContains(respuesta, "data-linea-de-tiempo")
        self.assertContains(respuesta, "data-por-clase")

    def test_dice_cuantas_operaciones_no_registran_quien(self):
        self.client.force_login(self.administracion)

        respuesta = self.client.get(self.url)

        self.assertContains(respuesta, "data-sin-actor")
        self.assertContains(respuesta, "data-sin-quien")

    def test_el_cajero_no_entra_aunque_registre_las_operaciones(self):
        cajero_con_admin = crear_cuenta(
            email="auditoria-cajero-staff@example.com",
            rol=Rol.CAJERO,
            nombre="Cajero",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.client.force_login(cajero_con_admin)

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_sin_is_staff_no_se_llega_ni_al_armazon(self):
        self.client.force_login(self.acudiente)

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_sin_sesion_lleva_al_acceso(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("acceso"), respuesta["Location"])

    def test_el_periodo_se_pide_por_la_url_y_se_puede_compartir(self):
        self.client.force_login(self.administracion)
        ayer = (timezone.localdate() - timedelta(days=1)).isoformat()

        respuesta = self.client.get(self.url, {"desde": ayer, "hasta": ayer})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["operaciones"], [])
        self.assertContains(respuesta, "data-sin-operaciones")

    def test_los_tres_reportes_enlazan_a_la_auditoria(self):
        """La entrada está donde ya se está mirando: quien ve algo raro en un
        consolidado no tiene por qué saberse la URL."""
        self.client.force_login(self.administracion)
        registrar_venta(
            actor=self.cajero, lineas={self.pan.id: 1}, medio_pago=MedioDePago.EFECTIVO
        )
        cerrar_caja(
            actor=self.cajero, base=Decimal("0"), efectivo_contado=Decimal("2500")
        )

        for listado in (
            "admin:ventas_venta_changelist",
            "admin:inventario_movimientoinventario_changelist",
            "admin:ventas_cierredecaja_changelist",
        ):
            with self.subTest(listado=listado):
                respuesta = self.client.get(reverse(listado))
                self.assertContains(respuesta, "data-enlace-a-la-auditoria")
                self.assertContains(respuesta, self.url)
