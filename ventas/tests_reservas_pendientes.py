"""`TT-147`, `TT-148`. Consulta de reservas pendientes (`HU-24`).

Su único criterio: **las reservas pendientes son consultables desde la
cafetería**. Y el «para qué» de la historia, que es lo que decide cómo se ve:
tenerlas preparadas **antes** de que lleguen los estudiantes.

De ahí las dos cosas que estas pruebas fijan y que una lista sin más no daría:

1. **La cola va del más antiguo al más reciente**, al revés que todos los
   historiales del proyecto. Una cola de trabajo se atiende por orden de espera.
2. **Solo lo pendiente.** Un pedido entregado sale de la lista; si no, la cola
   crecería con el día y el personal tendría que ir descartando.

`HU-24` nombra **dos actores**, `USR-3` y `USR-4`, que no comparten interfaz: el
cajero no entra al admin y la administración recibe `403` en el punto de venta.
`SoloElPersonalDeLaCafeteriaConsultaTest` comprueba que los dos llegan y que
nadie más lo hace.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from ventas.models import EstadoDelPedido, PedidoAnticipado
from ventas.selectors import reservas_pendientes
from ventas.services import reservar


def familia(documento="1001234501", email=None, nombre="Ana Sofía"):
    usuario = Usuario.objects.crear_usuario(
        email=email or f"acudiente{documento}@example.com",
        rol=Rol.ACUDIENTE,
        nombre="Marta",
    )
    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"43{documento}"
    )
    estudiante = Estudiante.objects.create(
        nombre=nombre,
        documento=documento,
        acudiente=acudiente,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )
    return usuario, estudiante


def producto(nombre="Empanada", precio="3500", existencias=50):
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


class BaseCola(TestCase):
    def setUp(self):
        self.empanada = producto()
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )

    def reserva_de(self, documento, nombre, cuantas=1):
        acudiente, estudiante = familia(
            documento, email=f"acu{documento}@example.com", nombre=nombre
        )
        recargar(actor=acudiente, estudiante=estudiante, monto=Decimal("50000"))
        return reservar(
            actor=acudiente,
            estudiante=estudiante,
            lineas={self.empanada.id: cuantas},
        )


class LaColaEsDeLoQueEsperaTest(BaseCola):
    """`TT-147`. Qué entra en la cola y en qué orden."""

    def test_sin_reservas_la_cola_esta_vacia(self):
        self.assertEqual(list(reservas_pendientes(actor=self.cajero)), [])

    def test_estan_todas_las_pendientes_sean_de_quien_sean(self):
        """La cola es del colegio, no de un estudiante: el personal prepara
        todo lo del descanso, no lo de una familia."""
        self.reserva_de("1001000001", "Ana Sofía")
        self.reserva_de("1001000002", "Bruno Díaz")

        self.assertEqual(reservas_pendientes(actor=self.cajero).count(), 2)

    def test_lo_mas_antiguo_va_primero(self):
        """**Al revés que todos los historiales del proyecto.**

        Un historial se lee empezando por lo último; una cola de trabajo se
        atiende por orden de espera. Si esto se ordenara como el resto, lo que
        lleva desde ayer sin recoger quedaría al final.
        """
        primera = self.reserva_de("1001000003", "Ana Sofía")
        segunda = self.reserva_de("1001000004", "Bruno Díaz")

        cola = list(reservas_pendientes(actor=self.cajero))

        self.assertEqual([p.pk for p in cola], [primera.pk, segunda.pk])

    def test_un_pedido_entregado_sale_de_la_cola(self):
        """Si no saliera, la cola crecería con el día y habría que ir
        descartando lo ya atendido, que es lo contrario de una cola."""
        entregada = self.reserva_de("1001000005", "Ana Sofía")
        pendiente = self.reserva_de("1001000006", "Bruno Díaz")

        # La entrega es `TT-149` (`HU-25`); aquí se fija el estado a mano para
        # comprobar que el selector mira el estado.
        PedidoAnticipado.objects.filter(pk=entregada.pk).update(
            estado=EstadoDelPedido.ENTREGADO,
            entregado_en="2026-09-18T12:00:00Z",
            entregado_por=self.cajero,
        )

        cola = list(reservas_pendientes(actor=self.cajero))

        self.assertEqual([p.pk for p in cola], [pendiente.pk])

    def test_la_cola_trae_al_estudiante_y_lo_que_lleva(self):
        """Es lo que hace falta para preparar: quién y qué.

        Se comprueba además que llegan **sin consultas de más**: una cola que
        pide el estudiante y las líneas por fila haría tantas consultas como
        reservas, y esta pantalla se abre con la cola delante.
        """
        self.reserva_de("1001000007", "Ana Sofía", cuantas=2)

        with self.assertNumQueries(3):
            for pedido in reservas_pendientes(actor=self.cajero):
                self.assertEqual(pedido.venta.estudiante.nombre, "Ana Sofía")
                self.assertEqual(
                    [(l.cantidad, l.producto.nombre) for l in pedido.venta.lineas.all()],
                    [(2, "Empanada")],
                )


class SoloElPersonalDeLaCafeteriaConsultaTest(BaseCola):
    """`[S11]`, `HU-24`: `USR-3` y `USR-4`, y nadie más.

    Los dos roles están porque `FUN-5` separa quien prepara de quien entrega, y
    no tienen por qué ser la misma persona.
    """

    def test_el_cajero_consulta(self):
        self.reserva_de("1001000010", "Ana Sofía")

        self.assertEqual(reservas_pendientes(actor=self.cajero).count(), 1)

    def test_la_administracion_consulta(self):
        self.reserva_de("1001000011", "Ana Sofía")
        administracion = Usuario.objects.crear_usuario(
            email="admin@example.com", rol=Rol.ADMINISTRADOR, nombre="Administración"
        )

        self.assertEqual(reservas_pendientes(actor=administracion).count(), 1)

    def test_la_institucion_no_consulta(self):
        """No es personal de la cafetería: `FUN-5` habla de quien prepara y
        entrega, y secretaría no hace ninguna de las dos."""
        institucion = Usuario.objects.crear_usuario(
            email="institucion@example.com", rol=Rol.INSTITUCION, nombre="Secretaría"
        )

        with self.assertRaises(PermissionDenied):
            reservas_pendientes(actor=institucion)

    def test_el_acudiente_no_consulta_la_cola_del_colegio(self):
        """Las suyas las ve en su pantalla de reserva, filtradas por su hijo.
        Esta cola es la de todo el colegio, que no es asunto suyo."""
        acudiente, _ = familia("1001000012", email="otro@example.com")

        with self.assertRaises(PermissionDenied):
            reservas_pendientes(actor=acudiente)

    def test_un_anonimo_tampoco(self):
        with self.assertRaises(PermissionDenied):
            reservas_pendientes(actor=None)

    def test_una_cuenta_desactivada_tampoco(self):
        self.cajero.is_active = False
        self.cajero.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            reservas_pendientes(actor=self.cajero)


class LaPantallaDeLaColaTest(BaseCola):
    """`TT-148`. La consulta desde la cafetería, por la ruta."""

    def setUp(self):
        super().setUp()
        sincronizar_grupos_y_permisos()
        self.url = reverse("reservas")

    def _entra(self, rol, email, staff=False):
        usuario = crear_cuenta(
            email=email,
            rol=rol,
            nombre="Persona",
            accede_a_administracion=staff,
            enviar_invitacion=False,
        )
        self.client.force_login(usuario)
        return usuario

    def test_el_cajero_alcanza_la_pantalla(self):
        self._entra(Rol.CAJERO, "cajero2@example.com")

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "ventas/reservas-pendientes.html")

    def test_la_administracion_tambien(self):
        """Y por eso la pantalla no vive dentro de `INT-2`: ahí recibe `403`."""
        self._entra(Rol.ADMINISTRADOR, "admin2@example.com", staff=True)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)

    def test_la_pantalla_ensena_las_reservas(self):
        self.reserva_de("1001000020", "Ana Sofía")
        self.reserva_de("1001000021", "Bruno Díaz")
        self._entra(Rol.CAJERO, "cajero3@example.com")

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.context["cuantas"], 2)
        self.assertContains(respuesta, "data-cuantas-reservas")

    def test_sin_reservas_la_pantalla_lo_dice(self):
        self._entra(Rol.CAJERO, "cajero4@example.com")

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.context["cuantas"], 0)
        self.assertNotContains(respuesta, "data-reserva")

    def test_la_institucion_no_alcanza_la_pantalla(self):
        self._entra(Rol.INSTITUCION, "institucion2@example.com", staff=True)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 403)

    def test_el_acudiente_no_alcanza_la_pantalla(self):
        acudiente, _ = familia("1001000022", email="acudiente-x@example.com")
        self.client.force_login(acudiente)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 403)

    def test_un_anonimo_va_al_acceso(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 302)


class LosDosMenusLlevanALaCola(BaseCola):
    """Sin entrada de menú la pantalla es inalcanzable, y una historia que nadie
    puede usar no está terminada.

    Son **dos menús** porque son dos sitios distintos: la barra de la aplicación
    —donde están el cajero y la administración— y la columna de iconos del punto
    de venta, que el cajero tiene delante mientras cobra.
    """

    def test_el_menu_del_cajero_y_el_de_la_administracion_la_llevan(self):
        from cuentas.templatetags.interfaz import MENU_POR_ROL, RESERVAS

        for rol in [Rol.CAJERO, Rol.ADMINISTRADOR]:
            with self.subTest(rol=rol):
                self.assertIn(RESERVAS, MENU_POR_ROL[rol])

    def test_ningun_otro_rol_la_tiene_en_su_menu(self):
        from cuentas.templatetags.interfaz import MENU_POR_ROL, RESERVAS

        for rol in [Rol.ACUDIENTE, Rol.INSTITUCION]:
            with self.subTest(rol=rol):
                self.assertNotIn(RESERVAS, MENU_POR_ROL[rol])

    def test_la_barra_del_punto_de_venta_la_lleva(self):
        from cuentas.templatetags.interfaz import (
            MENU_DEL_PUNTO_DE_VENTA,
            RESERVAS,
        )

        self.assertIn(RESERVAS, MENU_DEL_PUNTO_DE_VENTA)
