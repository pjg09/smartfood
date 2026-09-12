"""`TT-88`, `TT-89`, `TT-90`. La venta a cliente genérico (`HU-53`, `DEC-1`).

Cierra `VAC-1`, el hueco más serio que tenía el anteproyecto: `[S5]` declaraba
`USR-6` —docentes, personal, visitantes— y exigía registrar sus ventas, sin
ningún `ALC-IN` que lo respaldara.

Los cinco criterios de `HU-53`:

1. **No exige identificación ni registro previo del cliente.** No hay fila que
   crear en ninguna tabla: el cliente no existe en el sistema, y eso es el
   diseño, no una carencia.
2. **Descuenta inventario como cualquier otra venta** (`ALC-IN-17`, `INV-3`).
3. **No aplica restricciones alimentarias.** No hay acudiente que las haya
   configurado. Hoy no existen todavía (`HU-09` … `HU-13`, Sprint 3), así que lo
   que se puede comprobar es que el servicio **no pide ningún acudiente** para
   cobrar; cuando lleguen, su caso se añade aquí.
4. **No descuenta ninguna billetera.** Ni la de nadie: se comprueba contra el
   libro entero, no contra un estudiante concreto.
5. **Queda registrada** y entrará en los reportes de `HU-35` (Sprint 5).

**El modo genérico no es un modo** (`TT-89`). Una venta a cliente genérico *es*
una venta sin estudiante —`Venta.es_generica`—, así que la pantalla no enciende
nada: dice que se puede vender sin identificar, y ofrece la vuelta atrás cuando
hay alguien identificado. Un interruptor habría creado un tercer estado que el
modelo no tiene.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from billetera.models import Billetera, MovimientoBilletera, TipoDeMovimiento
from billetera.selectors import saldo_de
from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from ventas.models import MedioDePago, Venta
from ventas.services import VentaRechazada, registrar_venta, total_de


def escenario():
    cajero = Usuario.objects.crear_usuario(
        email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
    )
    acudiente = Usuario.objects.crear_usuario(
        email="acudiente@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
    )
    ficha = Acudiente.objects.create(
        usuario=acudiente, nombre="Marta Ruiz Ochoa", documento="4310012345"
    )
    estudiante = Estudiante.objects.create(
        nombre="Ana Sofía Restrepo Ruiz",
        documento="1001234501",
        acudiente=ficha,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )
    categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
    producto = Producto.objects.create(
        nombre="Empanada de carne", precio=Decimal("3500"), categoria=categoria
    )
    MovimientoInventario.objects.create(
        producto=producto,
        tipo=TipoDeMovimientoDeInventario.INGRESO,
        cantidad=20,
        motivo="Ingreso de prueba",
    )
    return cajero, acudiente, estudiante, producto


class TT90LaVentaGenericaDescuentaInventarioYNadaMasTest(TestCase):
    """`TT-90`. Los criterios 2 y 4, que son los que se pueden romper sin ruido."""

    def setUp(self):
        self.cajero, self.acudiente, self.estudiante, self.producto = escenario()
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000"))

    def _vender(self, cantidad=2, medio=MedioDePago.EFECTIVO):
        return registrar_venta(
            actor=self.cajero, lineas={self.producto.id: cantidad}, medio_pago=medio
        )

    def test_descuenta_inventario_como_cualquier_otra_venta(self):
        """`ALC-IN-17`. No es una venta de segunda: mueve el libro igual."""
        self._vender()

        self.assertEqual(existencias_de(self.producto), 18)

    def test_el_movimiento_de_inventario_senala_su_venta(self):
        """`INV-3`: la salida se explica desde el historial, y su motivo es la
        venta misma (`TT-78`)."""
        venta = self._vender()

        asiento = MovimientoInventario.objects.get(
            tipo=TipoDeMovimientoDeInventario.VENTA
        )
        self.assertEqual(asiento.venta, venta)
        self.assertEqual(asiento.cantidad, -2)

    def test_no_altera_ninguna_billetera(self):
        """Se comprueba contra **el libro entero**, no contra un estudiante.

        Comprobar el saldo de Ana dejaría pasar el fallo de descontarle a otro:
        lo que la historia promete es que la venta genérica no toca ninguna.
        """
        self._vender()

        self.assertEqual(MovimientoBilletera.objects.filter(
            tipo=TipoDeMovimiento.VENTA
        ).count(), 0)
        self.assertEqual(saldo_de(self.estudiante), Decimal("50000"))

    def test_no_crea_una_billetera_de_la_nada(self):
        """La billetera nace en la primera operación de **un estudiante**
        (`HU-06`). Una venta sin estudiante no puede crear ninguna: no habría a
        nombre de quién."""
        billeteras = Billetera.objects.count()

        self._vender()

        self.assertEqual(Billetera.objects.count(), billeteras)

    def test_queda_registrada_con_su_medio_de_pago(self):
        """Quinto criterio. Sin esto, la venta descuadraría el inventario sin
        dejar constancia de por qué, y el reporte de `HU-35` no la vería."""
        venta = self._vender()

        self.assertTrue(venta.es_generica)
        self.assertIsNone(venta.estudiante)
        self.assertEqual(venta.medio_pago, MedioDePago.EFECTIVO)
        self.assertEqual(venta.cajero, self.cajero)
        self.assertEqual(total_de(venta), Decimal("7000.00"))

    def test_tambien_por_transferencia(self):
        """`DEC-1`: los dos medios de la venta genérica. La transferencia va del
        banco del cliente al de la cafetería y **no pasa por el sistema**; aquí
        solo queda constancia (`ALC-OUT-01`)."""
        venta = self._vender(medio=MedioDePago.TRANSFERENCIA)

        self.assertEqual(venta.medio_pago, MedioDePago.TRANSFERENCIA)
        self.assertEqual(existencias_de(self.producto), 18)

    def test_no_exige_identificacion_ni_registro_previo(self):
        """Primer criterio, comprobado por lo que **no** hace falta: ningún
        estudiante, ningún acudiente y ninguna fila nueva de persona."""
        estudiantes = Estudiante.objects.count()
        acudientes = Acudiente.objects.count()

        self._vender()

        self.assertEqual(Estudiante.objects.count(), estudiantes)
        self.assertEqual(Acudiente.objects.count(), acudientes)

    def test_congela_el_precio_igual_que_las_demas(self):
        """`HU-22`. Una venta genérica es una venta: su historial tampoco se
        reescribe al editar el catálogo."""
        venta = self._vender()

        self.producto.precio = Decimal("9900")
        self.producto.save(update_fields=["precio"])

        self.assertEqual(total_de(venta), Decimal("7000.00"))

    def test_sin_existencias_se_rechaza_igual(self):
        with self.assertRaises(VentaRechazada):
            self._vender(cantidad=99)

        self.assertEqual(existencias_de(self.producto), 20)
        self.assertEqual(Venta.objects.count(), 0)


class TT89ElModoGenericoNoEsUnModoTest(TestCase):
    """`TT-89`. La pantalla, y la decisión que la define.

    Una venta a cliente genérico **es** una venta sin estudiante. La pantalla no
    enciende nada: declara que se puede vender sin identificar, y ofrece la
    vuelta atrás cuando hay alguien identificado.
    """

    def setUp(self):
        self.cajero, self.acudiente, self.estudiante, self.producto = escenario()
        self.client.force_login(self.cajero)
        self.pos = reverse("punto-de-venta")
        self.identificacion = reverse("identificacion-en-el-punto-de-venta")

    def test_la_pantalla_dice_que_no_hace_falta_identificar_a_nadie(self):
        """**El fallo que esto arregla es de texto, y era real.** «Pasa una
        tarjeta» se lee como *hay que identificar para vender*, y `DEC-1` dice lo
        contrario. Un cajero que no lo sabe deja la venta del docente fuera del
        sistema, que es exactamente `VAC-1`."""
        cuerpo = self.client.get(self.pos).content.decode()

        self.assertIn("data-venta-generica", cuerpo)
        self.assertIn("No hace falta identificar a nadie para vender", cuerpo)

    def test_no_hay_ningun_interruptor_de_modo(self):
        """Un modo encendido sería un tercer estado que el modelo no tiene, y
        tarde o temprano alguien lo encontraría activo con un estudiante
        identificado."""
        cuerpo = self.client.get(self.pos).content.decode()

        self.assertNotIn('data-modo="generico"', cuerpo)
        self.assertNotIn("Modo cliente genérico", cuerpo)

    def test_con_un_estudiante_identificado_se_puede_volver(self):
        """La vuelta atrás que faltaba: identificado alguien por error, el
        siguiente cliente puede ser un docente."""
        cuerpo = self.client.get(
            self.identificacion, {"codigo": self.estudiante.codigo_tarjeta}
        ).content.decode()

        self.assertIn("data-quitar-cliente", cuerpo)
        self.assertIn("Cobrar sin identificar a nadie", cuerpo)

    def test_al_volver_la_columna_queda_vacia_y_el_medio_cambia(self):
        self.client.get(
            self.identificacion, {"codigo": self.estudiante.codigo_tarjeta}
        )

        cuerpo = self.client.post(reverse("cliente-generico")).content.decode()

        self.assertIn("Ningún estudiante identificado", cuerpo)
        # `HU-54`: sin estudiante, efectivo o transferencia. Y llega fuera de
        # banda, porque vive en la otra columna.
        self.assertIn('hx-swap-oob="true"', cuerpo)
        self.assertIn('data-medio="efectivo"', cuerpo)
        self.assertNotIn('data-medio-fijo="billetera"', cuerpo)

    def test_y_la_venta_siguiente_ya_no_es_del_estudiante(self):
        """Lo que de verdad importa: que el servidor se haya olvidado de él.

        Si solo cambiara la pantalla, el cobro seguiría saliendo del saldo de
        quien ya no está delante.
        """
        recargar(actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000"))
        self.client.get(
            self.identificacion, {"codigo": self.estudiante.codigo_tarjeta}
        )
        self.client.post(reverse("cliente-generico"))

        self.client.post(
            reverse("carrito-del-punto-de-venta"),
            {"producto": str(self.producto.id), "accion": "anadir"},
        )
        cuerpo = self.client.post(
            reverse("cobrar"), {"medio_pago": MedioDePago.EFECTIVO}
        ).content.decode()

        self.assertIn("Venta cobrada", cuerpo)
        self.assertTrue(Venta.objects.get().es_generica)
        self.assertEqual(saldo_de(self.estudiante), Decimal("50000"))

    def test_el_carrito_sobrevive_al_cambio_de_cliente(self):
        """Quitar el cliente no es vaciar la venta: lo que cambia es quién paga.

        Vaciarlo obligaría a montar otra vez lo mismo con la fila delante.
        """
        self.client.post(
            reverse("carrito-del-punto-de-venta"),
            {"producto": str(self.producto.id), "accion": "anadir"},
        )
        self.client.get(
            self.identificacion, {"codigo": self.estudiante.codigo_tarjeta}
        )
        self.client.post(reverse("cliente-generico"))

        cuerpo = self.client.post(
            reverse("carrito-del-punto-de-venta"),
            {"producto": str(self.producto.id), "accion": "anadir"},
        ).content.decode()

        self.assertIn("$7.000 COP", cuerpo)

    def test_no_se_quita_el_cliente_por_GET(self):
        respuesta = self.client.get(reverse("cliente-generico"))

        self.assertEqual(respuesta.status_code, 405)

    def test_solo_el_cajero(self):
        self.client.force_login(
            Usuario.objects.crear_usuario(
                email="otro@example.com", rol=Rol.ADMINISTRADOR, nombre="Otro"
            )
        )

        respuesta = self.client.post(reverse("cliente-generico"))

        self.assertEqual(respuesta.status_code, 403)
