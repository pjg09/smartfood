"""`TT-133`. Venta rechazada por producto bloqueado (`HU-60`, `INV-4`).

`HU-10` dejó al acudiente marcar qué productos no puede comprar su estudiante.
Esto es lo que hace que esa marca signifique algo: **sin este rechazo, el bloqueo
es una anotación bonita y la caja cobra igual.**

Los cuatro criterios de `HU-60`:

1. **La venta de un producto bloqueado para ese estudiante se rechaza**, y no a
   medias: no se descuenta saldo ni existencias, porque los dos descuentos van
   en la misma transacción (`HU-21`).
2. **La validación ocurre dentro de la transacción**, junto a las de saldo y
   existencias (`DT-6`).
3. **El motivo se distingue** de los de `HU-18`, `HU-19`, `HU-20` y `HU-50`.
4. **El cajero no tiene forma de forzarla** (`INV-4`, primer criterio de
   `HU-13`: no dispone de ninguna acción para omitirlas).

El cuarto es el que da sentido al resto y el más fácil de perder: se comprueba
por las dos vías por las que alguien intentaría saltárselo —el servicio y la
pantalla— y comprobando que la restricción sigue en pie después de intentarlo.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from billetera.selectors import saldo_de
from billetera.services import recargar
from catalogo.models import Alergeno, Categoria, Producto, ProductoAlergeno
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from restricciones.selectors import identificadores_de_productos_bloqueados
from restricciones.services import bloquear_producto
from ventas.models import Venta
from ventas.services import ProductoBloqueado, SaldoInsuficiente, registrar_venta

CLAVE = "clave-de-prueba-2026"


def escenario():
    """Un cajero, un acudiente con su hijo, y dos productos con existencias."""
    cajero = Usuario.objects.crear_usuario(
        email="cajero-pb@example.com", rol=Rol.CAJERO, nombre="Cajero"
    )
    cajero.set_password(CLAVE)
    cajero.save(update_fields=["password"])

    acudiente = Usuario.objects.crear_usuario(
        email="acudiente-pb@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
    )
    ficha = Acudiente.objects.create(
        usuario=acudiente, nombre="Marta Ruiz Ochoa", documento="4310099999"
    )
    estudiante = Estudiante.objects.create(
        nombre="Ana Sofía Restrepo Ruiz",
        documento="1001299901",
        acudiente=ficha,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )

    categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
    productos = []
    for nombre, precio in (("Gaseosa", "2500"), ("Empanada de carne", "3000")):
        p = Producto.objects.create(
            nombre=nombre, precio=Decimal(precio), categoria=categoria
        )
        MovimientoInventario.objects.create(
            producto=p,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=50,
            motivo="Ingreso de prueba",
        )
        productos.append(p)

    return cajero, acudiente, estudiante, productos


class LaVentaDeUnProductoBloqueadoSeRechazaTest(TestCase):
    """Primer criterio, y el que convierte `HU-10` en algo real."""

    def setUp(self):
        self.cajero, self.acudiente, self.estudiante, (
            self.gaseosa,
            self.empanada,
        ) = escenario()
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000")
        )
        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.gaseosa
        )

    def _vender(self, lineas):
        return registrar_venta(
            actor=self.cajero, estudiante=self.estudiante, lineas=lineas
        )

    def test_se_rechaza_aunque_haya_saldo_de_sobra(self):
        """El caso contraintuitivo, que es el que importa.

        Hay saldo, hay existencias y el producto está en el catálogo. La venta
        se rechaza igual, y por un motivo que ninguna recarga arregla.
        """
        with self.assertRaises(ProductoBloqueado):
            self._vender({self.gaseosa.id: 1})

    def test_no_se_descuenta_nada_ni_queda_venta(self):
        saldo_antes = saldo_de(self.estudiante)
        existencias_antes = existencias_de(self.gaseosa)

        with self.assertRaises(ProductoBloqueado):
            self._vender({self.gaseosa.id: 1})

        self.assertEqual(saldo_de(self.estudiante), saldo_antes)
        self.assertEqual(existencias_de(self.gaseosa), existencias_antes)
        self.assertEqual(Venta.objects.count(), 0)

    def test_un_renglon_bloqueado_tumba_la_venta_entera(self):
        """No se cobra «lo que sí se puede» por su cuenta.

        Cobrar el resto en silencio dejaría al cajero sin saber que faltó algo y
        al estudiante creyendo que se llevó lo que pidió. El mensaje dice qué
        quitar; quitarlo es una decisión de quien está en la caja.
        """
        with self.assertRaises(ProductoBloqueado):
            self._vender({self.gaseosa.id: 1, self.empanada.id: 1})

        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(existencias_de(self.empanada), 50)

    def test_lo_no_bloqueado_se_vende_con_normalidad(self):
        venta = self._vender({self.empanada.id: 1})

        self.assertIsNotNone(venta)
        self.assertEqual(Venta.objects.count(), 1)

    def test_el_mensaje_dice_cual_es_el_producto(self):
        with self.assertRaises(ProductoBloqueado) as capturado:
            self._vender({self.gaseosa.id: 1})

        self.assertEqual(capturado.exception.productos, ("Gaseosa",))
        self.assertIn("Gaseosa", " ".join(capturado.exception.messages))

    def test_desbloquear_devuelve_la_venta_a_la_normalidad(self):
        """La única salida es que el acudiente retire la restricción."""
        from restricciones.services import desbloquear_producto

        desbloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.gaseosa
        )

        self.assertIsNotNone(self._vender({self.gaseosa.id: 1}))


class ElBloqueoEsDeEseEstudianteTest(TestCase):
    def setUp(self):
        self.cajero, self.acudiente, self.estudiante, (
            self.gaseosa,
            _,
        ) = escenario()
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000")
        )

        # Un segundo hijo del mismo acudiente, sin bloqueos.
        self.hermano = Estudiante.objects.create(
            nombre="Tomás Restrepo Ruiz",
            documento="1001299902",
            acudiente=self.estudiante.acudiente,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        recargar(actor=self.acudiente, estudiante=self.hermano, monto=Decimal("50000"))
        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.gaseosa
        )

    def test_al_hermano_sin_bloqueo_si_se_le_vende(self):
        venta = registrar_venta(
            actor=self.cajero,
            estudiante=self.hermano,
            lineas={self.gaseosa.id: 1},
        )
        self.assertIsNotNone(venta)

    def test_la_venta_a_cliente_generico_no_consulta_restricciones(self):
        """`DEC-1`, `HU-53`: sin estudiante no hay a quién consultarle nada."""
        venta = registrar_venta(
            actor=self.cajero,
            estudiante=None,
            lineas={self.gaseosa.id: 1},
            medio_pago="efectivo",
        )
        self.assertIsNotNone(venta)
        self.assertIsNone(venta.estudiante)


class ElMotivoSeDistingueTest(TestCase):
    """Tercer criterio. Cuatro motivos por delante, y hay que poder decir cuál."""

    def setUp(self):
        self.cajero, self.acudiente, self.estudiante, (
            self.gaseosa,
            self.empanada,
        ) = escenario()

    def test_bloqueado_y_saldo_insuficiente_son_excepciones_distintas(self):
        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.gaseosa
        )

        # Sin saldo y con el producto bloqueado: gana el bloqueo, porque es el
        # único motivo que no se arregla recargando.
        with self.assertRaises(ProductoBloqueado):
            registrar_venta(
                actor=self.cajero,
                estudiante=self.estudiante,
                lineas={self.gaseosa.id: 1},
            )

        # Y sin bloqueo, el mismo carrito sin saldo da el otro motivo.
        with self.assertRaises(SaldoInsuficiente):
            registrar_venta(
                actor=self.cajero,
                estudiante=self.estudiante,
                lineas={self.empanada.id: 1},
            )

    def test_cada_motivo_lleva_su_etiqueta(self):
        self.assertEqual(ProductoBloqueado.motivo, "producto-bloqueado")
        self.assertEqual(SaldoInsuficiente.motivo, "saldo-insuficiente")
        self.assertNotEqual(ProductoBloqueado.motivo, SaldoInsuficiente.motivo)


class ElCajeroNoPuedeForzarlaTest(TestCase):
    """Cuarto criterio: `INV-4` y el primer criterio de `HU-13`.

    Es el que da sentido a todo lo demás. Se comprueba por las dos vías por las
    que alguien intentaría saltárselo, y comprobando además que la restricción
    sigue en pie después de intentarlo.
    """

    def setUp(self):
        self.cajero, self.acudiente, self.estudiante, (
            self.gaseosa,
            _,
        ) = escenario()
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000")
        )
        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.gaseosa
        )

    def test_el_servicio_no_admite_ningun_argumento_que_la_salte(self):
        """No hay `forzar=True`, y que no lo haya es la garantía.

        Si algún día aparece uno, esta prueba falla al pasarlo: el servicio
        rechaza el argumento desconocido. Es una forma de vigilar una ausencia.
        """
        with self.assertRaises(TypeError):
            registrar_venta(
                actor=self.cajero,
                estudiante=self.estudiante,
                lineas={self.gaseosa.id: 1},
                forzar=True,
            )

    def test_el_cajero_no_puede_desbloquear_para_luego_cobrar(self):
        from django.core.exceptions import PermissionDenied
        from restricciones.services import desbloquear_producto

        with self.assertRaises(PermissionDenied):
            desbloquear_producto(
                actor=self.cajero, estudiante=self.estudiante, producto=self.gaseosa
            )

        self.assertIn(
            self.gaseosa.id, identificadores_de_productos_bloqueados(self.estudiante)
        )
        with self.assertRaises(ProductoBloqueado):
            registrar_venta(
                actor=self.cajero,
                estudiante=self.estudiante,
                lineas={self.gaseosa.id: 1},
            )

    def test_reintentar_el_cobro_da_el_mismo_rechazo(self):
        """No es un aviso descartable: insistir no la vence."""
        for intento in range(3):
            with self.subTest(intento=intento):
                with self.assertRaises(ProductoBloqueado):
                    registrar_venta(
                        actor=self.cajero,
                        estudiante=self.estudiante,
                        lineas={self.gaseosa.id: 1},
                    )
        self.assertEqual(Venta.objects.count(), 0)


class ElPuntoDeVentaEnseniaElMotivoTest(TestCase):
    """`TT-132`. Lo que el cajero ve cuando la venta se rechaza."""

    def setUp(self):
        self.cajero, self.acudiente, self.estudiante, (
            self.gaseosa,
            _,
        ) = escenario()
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000")
        )
        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.gaseosa
        )
        self.client.force_login(self.cajero)

    def _montar_y_cobrar(self):
        """El recorrido real del cajero: escanear, añadir al carrito y cobrar.

        La identificación es un `GET` —devuelve el fragmento del estudiante, no
        escribe nada— y el carrito un `POST`. Se hace por HTTP y no llamando al
        servicio porque lo que se comprueba aquí es **lo que el cajero ve**.
        """
        self.client.get(
            reverse("identificacion-en-el-punto-de-venta"),
            {"codigo": self.estudiante.codigo_tarjeta},
        )
        self.client.post(
            reverse("carrito-del-punto-de-venta"),
            {"producto": str(self.gaseosa.id), "accion": "anadir"},
        )
        return self.client.post(reverse("cobrar"))

    def test_el_ticket_marca_el_motivo_con_su_etiqueta(self):
        """Se busca `data-motivo`, no una frase: el texto cambia, la etiqueta no.

        Es la regla de `CLAUDE.md` —una prueba sobre una pantalla busca un
        `data-*` propio, no un atributo genérico ni un trozo de copia—.
        """
        respuesta = self._montar_y_cobrar()

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'data-motivo="producto-bloqueado"')

    def test_el_ticket_nombra_el_producto_y_no_cobra(self):
        respuesta = self._montar_y_cobrar()

        self.assertContains(respuesta, "Gaseosa")
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(saldo_de(self.estudiante), Decimal("50000.00"))

    def test_el_ticket_no_ofrece_ninguna_accion_para_omitirla(self):
        """`INV-4`. Si algún día aparece un «cobrar de todos modos», esto falla."""
        cuerpo = self._montar_y_cobrar().content.decode().lower()

        for tentacion in ("de todos modos", "forzar", "omitir", "ignorar"):
            self.assertNotIn(tentacion, cuerpo)
