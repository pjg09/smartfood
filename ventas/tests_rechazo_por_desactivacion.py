"""`TT-127`. Venta rechazada por estudiante desactivado (`HU-50`, `INVD-2`).

Los cuatro criterios de `HU-50`:

1. **Un estudiante desactivado o dado de baja no puede comprar.**
2. **Tampoco puede retirar pedidos anticipados.** Los pedidos son `HU-23` …
   `HU-25`, del Sprint 4: hoy no existen, y la puerta que los rechazará es la
   misma que rechaza la venta —`comprobar_que_puede_operar`—, así que la
   comprobación llegará sin construir ninguna regla nueva.
   `LaPuertaEsLaMismaParaLoQueVengaTest` deja eso fijado.
3. **Tampoco puede recibir recargas** (`DEC-14`, `INVD-7`). El criterio decía lo
   contrario —«sí puede, por ser inocuo»— y así se construyó en `PR-13`; al verlo
   funcionando, el equipo concluyó que la premisa no se sostiene: una tarjeta se
   desactiva porque **se perdió**, y acumular saldo sobre un medio de pago fuera
   de control no es inocuo cuando el sistema no sabe devolver dinero
   (`ALC-OUT-01`). `DEC-14` corrigió el criterio y estas pruebas con él.
4. **El motivo se distingue** de los de `HU-18`, `HU-19`, `HU-20` y `HU-60`.

**El de baja sigue siendo otro caso** aunque coincidan en esto: su saldo queda
congelado **para siempre** —no hay reactivación que lo libere (`HU-52`, `DEC-7`)—
mientras que el del desactivado le espera a que la institución reactive la
tarjeta (`HU-49`).
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


class NiCompraNiRecibeRecargasTest(BaseDesactivado):
    """Las dos direcciones del dinero, cerradas mientras la tarjeta esté perdida.

    Esta clase se escribió al revés en `PR-13`, siguiendo el tercer criterio de
    `HU-50` —«sí puede recibir recargas, por ser inocuo»—. `DEC-14` corrigió el
    criterio: una tarjeta se desactiva porque **se perdió** (`DEC-5`), y
    engordar el saldo de un medio de pago que está fuera de control no es inocuo
    cuando el sistema no sabe devolver dinero (`ALC-OUT-01`).

    **Lo que ya tenía no se toca**, y eso también se prueba aquí: el saldo sigue
    siendo suyo y lo gasta al reactivarse.
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

    def test_tampoco_recibe_recargas(self):
        with self.assertRaises(EstudianteNoOperativo):
            recargar(
                actor=self.acudiente,
                estudiante=self.estudiante,
                monto=Decimal("10000"),
            )

        self.assertEqual(saldo_de(self.estudiante), Decimal("50000.00"))

    def test_el_saldo_que_ya_tenía_sigue_siendo_suyo(self):
        """Desactivar bloquea la tarjeta, no confisca el dinero."""
        self.assertEqual(saldo_de(self.estudiante), Decimal("50000.00"))

    def test_al_reactivarlo_vuelve_a_comprar_y_a_poder_recargar(self):
        """El recorrido completo, que es el que la familia vive: se bloquea, se
        va al colegio, se reactiva, y todo vuelve a funcionar (`HU-49`)."""
        reactivar(actor=self.institucion, estudiante=self.estudiante)

        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("10000")
        )
        venta = self.vender()

        self.assertIsNotNone(venta)
        self.assertEqual(saldo_de(self.estudiante), Decimal("57000.00"))


class ElDeBajaEsOtroCasoTest(BaseDesactivado):
    """`HU-52`: el saldo del retirado queda congelado **y no vuelve**.

    Desde `DEC-14` los dos estados coinciden en no comprar y en no recibir
    recargas; lo que los separa es que del desactivado se vuelve —la institución
    lo reactiva (`HU-49`) y su saldo se usa— y de la baja no. Esta clase fija ese
    lado para que la de arriba no pueda pasar describiendo mal al retirado.
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

    Esta clase se escribió en el Sprint 3, cuando los pedidos no existían, para
    fijar que la regla vive en **una sola puerta** y que quien construyera el
    retiro la heredaría sin acordarse de nada. Los pedidos llegaron con `HU-23`
    y la apuesta salió: `reservar` no menciona `INVD-2` por ninguna parte y la
    cumple, porque valida por la misma función que la venta (`TT-144`).

    Que la reserva **de verdad** rechace a un estudiante desactivado se
    comprueba ejecutándola, en `./tests_reserva.py`. Aquí se fija lo estructural
    que hace que eso siga siendo cierto mañana.
    """

    def test_ni_la_venta_ni_la_reserva_reimplementan_la_regla(self):
        """La condición vive en `_bloquear_y_validar` y en ningún otro sitio.

        Si alguien la copiara dentro de `registrar_venta` o de `reservar`, esto
        fallaría: lo que se exige no es solo que la llamen, es que **no la
        tengan escrita aparte** — una copia es como uno de los dos caminos se
        queda sin el arreglo de la próxima.
        """
        import inspect

        from ventas import services

        compartida = inspect.getsource(services._bloquear_y_validar)
        self.assertIn("comprobar_que_puede_operar", compartida)

        for servicio in [services.registrar_venta, services.reservar]:
            with self.subTest(servicio=servicio.__name__):
                fuente = inspect.getsource(servicio)
                self.assertIn("_bloquear_y_validar", fuente)
                self.assertNotIn("comprobar_que_puede_operar", fuente)

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
