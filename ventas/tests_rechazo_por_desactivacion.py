"""`TT-127`. Venta rechazada por estudiante desactivado (`HU-50`, `INVD-2`).

Los cuatro criterios de `HU-50`:

1. **Un estudiante desactivado o dado de baja no puede comprar.**
2. **Tampoco puede retirar pedidos anticipados.** Los pedidos son `HU-23` …
   `HU-25`, del Sprint 4: hoy no existen, y la puerta que los rechazará es la
   misma que rechaza la venta —`comprobar_que_puede_operar`—, así que la
   comprobación llegará sin construir ninguna regla nueva.
   `LaPuertaEsLaMismaParaLoQueVengaTest` deja eso fijado.
3. **Sí puede recibir recargas, por ser inocuo.** Es el criterio que corrigió al
   sistema y no al revés: el código era **más restrictivo que `INVD-2`**, que
   habla de comprar y de retirar pedidos y no del dinero que entra.
   `NoCompraPeroSiRecibeRecargasTest` es la clase central de este fichero.
4. **El motivo se distingue** de los de `HU-18`, `HU-19`, `HU-20` y `HU-60`.

**El de baja es otro caso, y no se junta con este**: su saldo queda congelado y
tampoco recibe recargas (`HU-52`). Los dos estados coinciden en no comprar y se
separan en todo lo demás (`DEC-7`).
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from billetera.selectors import saldo_de
from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from personas.services import (
    EstudianteNoOperativo,
    comprobar_que_puede_operar,
    dar_de_baja,
    desactivar,
    reactivar,
)
from ventas.models import Venta
from ventas.services import (
    EstudianteNoPuedeComprar,
    LimiteDiarioSuperado,
    ProductoBloqueado,
    SaldoInsuficiente,
    registrar_venta,
)

CLAVE = "clave-de-prueba-2026"


class BaseDesactivado(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        self.institucion = crear_cuenta(
            email="institucion-hu50@example.com",
            rol=Rol.INSTITUCION,
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.cajero = crear_cuenta(
            email="cajero-hu50@example.com",
            rol=Rol.CAJERO,
            enviar_invitacion=False,
            contrasena_de_desarrollo=CLAVE,
        )
        self.acudiente = Usuario.objects.crear_usuario(
            email="acudiente-hu50@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
        )
        ficha = Acudiente.objects.create(
            usuario=self.acudiente, nombre="Marta Ruiz Ochoa", documento="4310033333"
        )
        self.estudiante = Estudiante.objects.create(
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001233301",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )

        self.producto = Producto.objects.create(
            nombre="Empanada",
            precio=Decimal("3000"),
            categoria=Categoria.objects.create(nombre="Cafetería"),
        )
        MovimientoInventario.objects.create(
            producto=self.producto,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=50,
            motivo="Ingreso de prueba",
        )
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000")
        )

    def vender(self):
        return registrar_venta(
            actor=self.cajero,
            estudiante=Estudiante.objects.get(pk=self.estudiante.pk),
            lineas={self.producto.id: 1},
        )


# --- Criterios 1 y 3: no compra, pero sí recibe recargas ------------------


class NoCompraPeroSiRecibeRecargasTest(BaseDesactivado):
    """**La clase que corrige el sistema**, y conviene leer por qué.

    Hasta `PR-13` un estudiante desactivado tampoco podía recibir recargas. No
    salía de ninguna historia: salía de aplicar `INVD-2` más ancha de lo que
    dice —«no puede comprar ni retirar pedidos anticipados»—. El tercer criterio
    de `HU-50` lo zanja: **sí puede, por ser inocuo**, porque su tarjeta no
    compra igualmente y el dinero le espera a la reactivación (`HU-49`).
    """

    def setUp(self):
        super().setUp()
        desactivar(actor=self.institucion, estudiante=self.estudiante)

    def test_no_compra(self):
        with self.assertRaises(EstudianteNoPuedeComprar):
            self.vender()

        self.assertEqual(Venta.objects.count(), 0)

    def test_no_se_descuenta_nada(self):
        saldo_antes = saldo_de(self.estudiante)

        with self.assertRaises(EstudianteNoPuedeComprar):
            self.vender()

        self.assertEqual(saldo_de(self.estudiante), saldo_antes)
        self.assertEqual(existencias_de(self.producto), 50)

    def test_pero_sí_recibe_recargas(self):
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("10000")
        )

        self.assertEqual(saldo_de(self.estudiante), Decimal("60000.00"))

    def test_y_recargar_no_lo_desbloquea(self):
        """El malentendido que hay que evitar: el dinero entra, la tarjeta no abre."""
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("10000")
        )

        with self.assertRaises(EstudianteNoPuedeComprar):
            self.vender()

    def test_al_reactivarlo_compra_con_todo_lo_recargado(self):
        """El recorrido completo: se recarga bloqueado, se reactiva, se compra."""
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("10000")
        )
        reactivar(actor=self.institucion, estudiante=self.estudiante)

        venta = self.vender()

        self.assertIsNotNone(venta)
        self.assertEqual(saldo_de(self.estudiante), Decimal("57000.00"))


class ElDeBajaEsOtroCasoTest(BaseDesactivado):
    """`HU-52`: el saldo del retirado queda congelado, y eso incluye las recargas.

    Los dos estados coinciden en no comprar y se separan aquí. Sin esta clase, la
    de arriba podría pasar con un sistema que hubiera abierto las recargas a los
    dos, que es lo que `HU-52` prohíbe.
    """

    def setUp(self):
        super().setUp()
        dar_de_baja(actor=self.institucion, estudiante=self.estudiante)

    def test_tampoco_compra(self):
        with self.assertRaises(EstudianteNoPuedeComprar):
            self.vender()

    def test_y_no_recibe_recargas(self):
        with self.assertRaises(EstudianteNoOperativo):
            recargar(
                actor=self.acudiente,
                estudiante=self.estudiante,
                monto=Decimal("10000"),
            )

        self.assertEqual(saldo_de(self.estudiante), Decimal("50000.00"))

    def test_su_saldo_sigue_siendo_consultable(self):
        """Congelado no es borrado: es la constancia de que ese dinero existió."""
        self.assertEqual(saldo_de(self.estudiante), Decimal("50000.00"))


# --- Criterio 2: lo que venga también pasa por aquí -----------------------


class LaPuertaEsLaMismaParaLoQueVengaTest(BaseDesactivado):
    """Segundo criterio: tampoco retira pedidos anticipados.

    **Los pedidos son del Sprint 4** (`HU-23` … `HU-25`) y hoy no existen. Lo que
    se puede comprobar —y es lo que de verdad hará que el criterio se cumpla
    entonces— es que la regla vive en **una sola puerta**, y que la venta la
    llama en vez de reimplementarla: quien construya el retiro llamará a la misma
    y no tendrá que acordarse de ninguna regla.
    """

    def test_la_venta_no_reimplementa_la_regla(self):
        """Si alguien copiara la condición en `ventas`, esto seguiría pasando y
        la del retiro nacería sin ella. Por eso se comprueba la llamada."""
        import inspect

        from ventas import services

        fuente = inspect.getsource(services.registrar_venta)
        self.assertIn("comprobar_que_puede_operar", fuente)

    def test_la_puerta_rechaza_los_dos_estados(self):
        for transicion, estado in [
            (lambda: desactivar(actor=self.institucion, estudiante=self.estudiante),
             "desactivado"),
            (lambda: dar_de_baja(actor=self.institucion, estudiante=self.estudiante),
             "de baja"),
        ]:
            with self.subTest(estado=estado):
                transicion()
                self.estudiante.refresh_from_db()

                with self.assertRaises(EstudianteNoOperativo):
                    comprobar_que_puede_operar(self.estudiante)


# --- Criterio 4: el motivo se distingue ----------------------------------


class ElMotivoSeDistingueTest(BaseDesactivado):
    """Cuatro motivos de rechazo antes de este, y el cajero tiene que saber cuál."""

    def test_su_etiqueta_es_distinta_de_las_otras_cuatro(self):
        etiquetas = {
            EstudianteNoPuedeComprar.motivo,
            ProductoBloqueado.motivo,
            SaldoInsuficiente.motivo,
            LimiteDiarioSuperado.motivo,
        }

        self.assertEqual(len(etiquetas), 4)
        self.assertEqual(EstudianteNoPuedeComprar.motivo, "estudiante-no-opera")

    def test_gana_a_cualquier_otro_motivo(self):
        """Con la tarjeta bloqueada da igual lo que lleve en el carrito.

        Se monta el peor caso posible —sin saldo, con el producto bloqueado y con
        el cupo agotado— y el motivo sigue siendo este: es el único que no se
        arregla en el mostrador, ni quitando un renglón ni recargando.
        """
        from restricciones.services import bloquear_producto, fijar_limite_diario

        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.producto
        )
        fijar_limite_diario(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("100")
        )
        desactivar(actor=self.institucion, estudiante=self.estudiante)

        with self.assertRaises(EstudianteNoPuedeComprar):
            self.vender()

    def test_el_mensaje_dice_cuál_de_los_dos_estados_es(self):
        """Una etiqueta para los dos y un mensaje que los distingue: para la venta
        son lo mismo —no se cobra—, pero para quien está en la caja no."""
        desactivar(actor=self.institucion, estudiante=self.estudiante)
        with self.assertRaises(EstudianteNoPuedeComprar) as desactivado:
            self.vender()

        reactivar(actor=self.institucion, estudiante=self.estudiante)
        dar_de_baja(actor=self.institucion, estudiante=self.estudiante)
        with self.assertRaises(EstudianteNoPuedeComprar) as de_baja:
            self.vender()

        self.assertIn("desactivado", " ".join(desactivado.exception.messages))
        self.assertIn("de baja", " ".join(de_baja.exception.messages))


class LoQueElCajeroVeTest(BaseDesactivado):
    """`TT-126`. El motivo en la pantalla, por el camino real del cajero."""

    def setUp(self):
        super().setUp()
        desactivar(actor=self.institucion, estudiante=self.estudiante)
        self.client.force_login(self.cajero)

    def _montar_y_cobrar(self):
        self.client.get(
            reverse("identificacion-en-el-punto-de-venta"),
            {"codigo": self.estudiante.codigo_tarjeta},
        )
        self.client.post(
            reverse("carrito-del-punto-de-venta"),
            {"producto": str(self.producto.id), "accion": "anadir"},
        )
        return self.client.post(reverse("cobrar"))

    def test_el_ticket_marca_el_motivo_con_su_etiqueta(self):
        respuesta = self._montar_y_cobrar()

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'data-motivo="estudiante-no-opera"')

    def test_y_no_se_confunde_con_el_de_saldo(self):
        respuesta = self._montar_y_cobrar()

        self.assertNotContains(respuesta, 'data-motivo="saldo-insuficiente"')
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(saldo_de(self.estudiante), Decimal("50000.00"))

    def test_el_estudiante_se_identifica_igual(self):
        """Decir «esa tarjeta no es de nadie» sería mentir y dejaría al cajero
        repitiendo el escaneo."""
        respuesta = self.client.get(
            reverse("identificacion-en-el-punto-de-venta"),
            {"codigo": self.estudiante.codigo_tarjeta},
        )

        self.assertContains(respuesta, self.estudiante.nombre)

    def test_la_pantalla_no_ofrece_ninguna_accion_para_forzar(self):
        cuerpo = self._montar_y_cobrar().content.decode().lower()

        for palabra in ["forzar", "omitir", "autorizar"]:
            with self.subTest(palabra=palabra):
                self.assertNotIn(palabra, cuerpo)
