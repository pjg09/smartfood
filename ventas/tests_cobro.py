"""`TT-74`, `TT-75`, `TT-76`. La vista de cobro (`HU-17`, `[S11]`).

Los dos criterios de `HU-17`, y por qué esta historia **no se cierra aquí**:

1. **Al identificar al estudiante se muestran los tres datos: saldo, consumo del
   día y restricciones.** De los tres hay dos. Las restricciones son `HU-09` …
   `HU-13`, del Sprint 3, y el panel dice qué falta en lugar de afirmar que no
   tiene ninguna — que es lo único que el sistema todavía no puede sostener.
   `DoD-1` no admite marcar terminada una historia con un criterio sin cumplir,
   así que `HU-17` sigue abierta hasta `HU-13`.
2. **El cajero ve el saldo solo al cobrar, no como consulta libre.** Este es el
   que se prueba entero aquí, y se prueba por las dos caras: que lo ve al
   identificar en la caja, y que **no hay ninguna otra puerta** por la que
   alcance el saldo de un estudiante.

Esa segunda cara es la que importa vigilar. «Solo al cobrar» no lo sostiene un
rótulo ni un enlace escondido: lo sostiene que `informacion_de_cobro` sea el
único camino hasta el saldo para el rol cajero y exija ese rol (`DT-11`,
`INV-4`). Si mañana alguien añade una vista que lo enseñe por otro lado, lo que
tiene que romperse es una prueba, no la matriz de permisos.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from billetera.models import Billetera, MovimientoBilletera, TipoDeMovimiento
from billetera.selectors import consumo_del_dia
from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, EstadoDelEstudiante, Estudiante
from personas.services import dar_de_baja
from ventas.models import MedioDePago, Venta
from ventas.selectors import informacion_de_cobro


def estudiante(documento="1001234501"):
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente{documento}@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
    )
    # El documento del acudiente se deriva del del estudiante para que cada
    # llamada traiga una familia distinta: dos estudiantes con el mismo acudiente
    # chocarían contra el `unique` de `Acudiente.documento`.
    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"43{documento}"
    )
    return Estudiante.objects.create(
        nombre="Ana Sofía Restrepo Ruiz",
        documento=documento,
        acudiente=acudiente,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )


def movimiento(estudiante, tipo, monto, cuando=None):
    """Un asiento del libro, opcionalmente fechado en otro momento.

    `creado_en` es `auto_now_add`, así que no se puede fijar al crear: se
    reescribe después con un `update`, que **no** vuelve a pasar por el campo
    automático. Es la única forma de tener movimientos de ayer sin esperar un día.

    Desde `TT-78`, un movimiento de venta **señala la venta que lo origina**
    (`INV-2`), así que se fabrica una. El cobro de verdad es `TT-80`.
    """
    billetera, _ = Billetera.objects.get_or_create(estudiante=estudiante)
    venta = None
    if tipo == TipoDeMovimiento.VENTA:
        cajero = Usuario.objects.crear_usuario(
            email=f"cajero-{Venta.objects.count()}@example.com",
            rol=Rol.CAJERO,
            nombre="Cajero",
        )
        venta = Venta.objects.create(
            cajero=cajero, estudiante=estudiante, medio_pago=MedioDePago.BILLETERA
        )
    asiento = MovimientoBilletera.objects.create(
        billetera=billetera, tipo=tipo, monto=Decimal(monto), venta=venta
    )
    if cuando is not None:
        MovimientoBilletera.objects.filter(pk=asiento.pk).update(creado_en=cuando)
    return asiento


class ElConsumoDelDiaSaleDelHistorialTest(TestCase):
    """`TT-74`. `INV-2`: no hay contador que alguien tenga que poner a cero."""

    def setUp(self):
        self.estudiante = estudiante()

    def test_sin_movimientos_el_consumo_es_cero(self):
        self.assertEqual(consumo_del_dia(self.estudiante), Decimal("0.00"))

    def test_suma_las_ventas_de_hoy_y_las_devuelve_en_positivo(self):
        """En el libro una venta resta; «lleva gastado» no es una cifra negativa."""
        movimiento(self.estudiante, TipoDeMovimiento.RECARGA, "50000")
        movimiento(self.estudiante, TipoDeMovimiento.VENTA, "-3500")
        movimiento(self.estudiante, TipoDeMovimiento.VENTA, "-4500")

        self.assertEqual(consumo_del_dia(self.estudiante), Decimal("8000"))

    def test_la_recarga_no_es_consumo(self):
        movimiento(self.estudiante, TipoDeMovimiento.RECARGA, "50000")

        self.assertEqual(consumo_del_dia(self.estudiante), Decimal("0.00"))

    def test_la_devolucion_no_descuenta_el_consumo(self):
        """Devolver dinero no deshace que ese día se compró.

        Si `HU-20` —el límite diario, del Sprint 3— decide que una devolución
        libera cupo, esa decisión se toma allí. Esta prueba existe para que el
        cambio sea deliberado y no un efecto colateral de otra cosa.
        """
        movimiento(self.estudiante, TipoDeMovimiento.VENTA, "-3500")
        movimiento(self.estudiante, TipoDeMovimiento.DEVOLUCION, "3500")

        self.assertEqual(consumo_del_dia(self.estudiante), Decimal("3500"))

    def test_lo_de_ayer_no_cuenta_hoy(self):
        """El corte es la medianoche **local**, no la de UTC."""
        ayer = timezone.localtime() - timedelta(days=1)
        movimiento(self.estudiante, TipoDeMovimiento.VENTA, "-9000", cuando=ayer)
        movimiento(self.estudiante, TipoDeMovimiento.VENTA, "-1000")

        self.assertEqual(consumo_del_dia(self.estudiante), Decimal("1000"))

    def test_se_puede_preguntar_por_otra_jornada(self):
        ayer = timezone.localtime() - timedelta(days=1)
        movimiento(self.estudiante, TipoDeMovimiento.VENTA, "-9000", cuando=ayer)

        self.assertEqual(
            consumo_del_dia(self.estudiante, dia=ayer.date()), Decimal("9000")
        )

    def test_el_consumo_es_de_ese_estudiante_y_no_del_acudiente(self):
        """`HU-04`, segundo criterio: las cifras son por estudiante.

        Dos hermanos comparten cuenta de acudiente y **no** comparten billetera.
        """
        hermano = estudiante(documento="1001234502")
        movimiento(hermano, TipoDeMovimiento.VENTA, "-7000")

        self.assertEqual(consumo_del_dia(self.estudiante), Decimal("0.00"))
        self.assertEqual(consumo_del_dia(hermano), Decimal("7000"))


class LaInformacionDeCobroExigeSerCajeroTest(TestCase):
    """`TT-74`, `TT-76`. **Aquí vive el «solo al cobrar»** (`[S11]`, `DT-11`).

    El selector es el único camino por el que el saldo de un estudiante llega al
    rol cajero. Que exija el rol no es redundante con el `403` de la vista: la
    vista protege una URL, y esto protege el dato desde cualquier llamada futura
    —otra vista, un comando, el admin— sin que nadie tenga que acordarse.
    """

    def setUp(self):
        self.estudiante = estudiante()
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )

    def test_el_cajero_obtiene_saldo_y_consumo(self):
        movimiento(self.estudiante, TipoDeMovimiento.RECARGA, "50000")
        movimiento(self.estudiante, TipoDeMovimiento.VENTA, "-3500")

        cobro = informacion_de_cobro(actor=self.cajero, estudiante=self.estudiante)

        self.assertEqual(cobro.saldo, Decimal("46500"))
        self.assertEqual(cobro.consumo_del_dia, Decimal("3500"))

    def test_el_saldo_es_exactamente_la_suma_del_historial(self):
        """`INV-2`, `TST-3`, otra vez y en este camino.

        `TT-63` ya lo prueba sobre `saldo_de`. Se repite aquí porque lo que el
        cajero ve en la caja tiene que ser esa misma cifra, y no una copia que
        alguien pudiera decidir redondear o cachear «para ir más rápido».
        """
        for monto in ["25000", "-3500", "-4500", "10000"]:
            tipo = (
                TipoDeMovimiento.RECARGA
                if Decimal(monto) > 0
                else TipoDeMovimiento.VENTA
            )
            movimiento(self.estudiante, tipo, monto)

        cobro = informacion_de_cobro(actor=self.cajero, estudiante=self.estudiante)

        suma = sum(
            m.monto for m in MovimientoBilletera.objects.filter(
                billetera__estudiante=self.estudiante
            )
        )
        self.assertEqual(cobro.saldo, suma)

    def test_ningun_otro_rol_obtiene_el_saldo(self):
        """Incluido el acudiente: **él tiene su propio camino**, `HU-07`.

        No es una restricción contra el acudiente, es que el saldo del panel del
        acudiente sale de `estudiante_a_cargo`, que solo alcanza a los suyos. Por
        aquí pasaría cualquier estudiante, así que por aquí solo pasa el cajero.
        """
        for rol in [Rol.ACUDIENTE, Rol.ADMINISTRADOR, Rol.INSTITUCION]:
            with self.subTest(rol=rol):
                actor = Usuario.objects.crear_usuario(
                    email=f"{rol}@example.com", rol=rol, nombre="Otro"
                )
                with self.assertRaises(PermissionDenied):
                    informacion_de_cobro(actor=actor, estudiante=self.estudiante)

    def test_sin_actor_no_hay_saldo(self):
        with self.assertRaises(PermissionDenied):
            informacion_de_cobro(actor=None, estudiante=self.estudiante)

    def test_una_cuenta_de_cajero_desactivada_no_cobra(self):
        """`HU-42`. Se le retiró el acceso; la fila sigue ahí."""
        self.cajero.is_active = False
        self.cajero.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            informacion_de_cobro(actor=self.cajero, estudiante=self.estudiante)

    def test_el_estudiante_de_baja_conserva_su_saldo_consultable(self):
        """`HU-52`, `INVD-2`. Congelado, no escondido.

        El cajero acaba de identificarlo con una tarjeta que alguien le puso
        delante: callar la cifra no protege nada y lo deja sin poder explicar por
        qué no se cobra.
        """
        movimiento(self.estudiante, TipoDeMovimiento.RECARGA, "12000")
        institucion = Usuario.objects.crear_usuario(
            email="institucion@example.com", rol=Rol.INSTITUCION, nombre="Colegio"
        )
        dar_de_baja(actor=institucion, estudiante=self.estudiante)

        cobro = informacion_de_cobro(actor=self.cajero, estudiante=self.estudiante)

        self.assertEqual(cobro.saldo, Decimal("12000"))


class ElPanelDeCobroApareceAlIdentificarTest(TestCase):
    """`TT-75`. Primer criterio de `HU-17`, por las dos vías de `HU-15` y `HU-16`."""

    def setUp(self):
        self.estudiante = estudiante()
        movimiento(self.estudiante, TipoDeMovimiento.RECARGA, "50000")
        movimiento(self.estudiante, TipoDeMovimiento.VENTA, "-3500")
        self.client.force_login(
            Usuario.objects.crear_usuario(
                email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
            )
        )
        self.url = reverse("identificacion-en-el-punto-de-venta")

    def _por_tarjeta(self):
        return self.client.get(
            self.url, {"codigo": self.estudiante.codigo_tarjeta}
        ).content.decode()

    def test_el_escaneo_trae_el_saldo(self):
        cuerpo = self._por_tarjeta()

        self.assertIn("Saldo", cuerpo)
        self.assertIn("$46.500 COP", cuerpo)

    def test_el_escaneo_trae_el_consumo_del_dia(self):
        cuerpo = self._por_tarjeta()

        self.assertIn("Consumo de hoy", cuerpo)
        self.assertIn("$3.500", cuerpo)

    def test_las_cifras_llevan_el_formato_del_sistema(self):
        """`DT-25`: el dinero se escribe en un solo sitio, `dinero.py`.

        Si alguna vez aparece aquí un `46500` a secas, es que alguien formateó en
        la plantilla y la misma pantalla va camino de enseñar dos monedas.
        """
        cuerpo = self._por_tarjeta()

        self.assertNotIn(">46500<", cuerpo)
        self.assertNotIn("46,500", cuerpo)

    def test_el_tercer_dato_declara_que_falta_en_vez_de_decir_que_no_hay(self):
        """`HU-17` no se cierra aquí, y la pantalla lo dice.

        «Sin restricciones» se leería en una caja como *puede comprar cualquier
        cosa*, y eso es exactamente lo que nadie puede afirmar hasta `HU-13`.
        """
        cuerpo = self._por_tarjeta()

        self.assertIn("Restricciones", cuerpo)
        self.assertIn("HU-13", cuerpo)
        self.assertNotIn("Sin restricciones", cuerpo)

    def test_por_documento_sale_lo_mismo(self):
        """`HU-16`, primer criterio: **el mismo resultado**, no uno parecido."""
        por_documento = self.client.get(
            self.url, {"documento": self.estudiante.documento}
        ).content.decode()

        self.assertEqual(self._por_tarjeta(), por_documento)

    def test_el_saldo_en_cero_se_dice_en_rojo_y_con_su_motivo(self):
        """`INV-1`. El rojo significa algo en este sistema, y aquí significa esto.

        Es el «para» de la historia: *saber antes de cobrar si la venta va a poder
        realizarse*. Sin saldo, no va a poder. El rechazo de verdad es `HU-19` y
        ocurre en el servicio, dentro del bloqueo (`DT-6`); esto es el aviso.
        """
        sin_saldo = estudiante(documento="1001234503")

        cuerpo = self.client.get(
            self.url, {"codigo": sin_saldo.codigo_tarjeta}
        ).content.decode()

        self.assertIn("$0 COP", cuerpo)
        self.assertIn("No alcanza para cobrar nada", cuerpo)
        self.assertIn("border-error", cuerpo)

    def test_el_estudiante_de_baja_enseña_su_saldo_congelado(self):
        """`HU-52` y `INVD-2` a la vez: se ve, y se avisa de que no se le vende."""
        institucion = Usuario.objects.crear_usuario(
            email="institucion@example.com", rol=Rol.INSTITUCION, nombre="Colegio"
        )
        dar_de_baja(actor=institucion, estudiante=self.estudiante)

        cuerpo = self._por_tarjeta()

        self.assertIn("$46.500 COP", cuerpo)
        self.assertIn("No se le puede vender", cuerpo)

    def test_el_desactivado_tambien(self):
        self.estudiante.estado = EstadoDelEstudiante.DESACTIVADO
        self.estudiante.save(update_fields=["estado"])

        cuerpo = self._por_tarjeta()

        self.assertIn("$46.500 COP", cuerpo)
        self.assertIn("No se le puede vender", cuerpo)

    def test_una_tarjeta_desconocida_no_ensena_ningun_saldo(self):
        """No hay a quién cobrarle, así que no hay información de cobro."""
        cuerpo = self.client.get(self.url, {"codigo": "ZZZZZZZZZZZZZZ"}).content.decode()

        self.assertNotIn("Saldo", cuerpo)
        self.assertNotIn("Consumo de hoy", cuerpo)


class ElCajeroVeElSaldoSoloAlCobrarTest(TestCase):
    """`TT-76`. **El segundo criterio de `HU-17`, y el que vigila `[S11]`.**

    La fila «Consultar saldo de un estudiante» de `[S11]` dice: acudiente «Sí»,
    cajero «Solo al cobrar». Lo primero ya lo prueba `HU-07`. Lo segundo son dos
    afirmaciones, y las dos hacen falta:

    · **Lo ve al cobrar**: identificar en el punto de venta lo trae. Lo prueba
      `ElPanelDeCobroApareceAlIdentificarTest`.
    · **Y no lo ve de ninguna otra manera**: no hay pantalla, ruta ni listado por
      el que el cajero llegue al saldo de un estudiante sin que alguien le haya
      puesto una tarjeta delante.

    Esta clase prueba la segunda, que es la que se rompe sola con el tiempo: cada
    vista nueva que enseñe un saldo es una candidata a abrir esta puerta.
    """

    def setUp(self):
        self.estudiante = estudiante()
        movimiento(self.estudiante, TipoDeMovimiento.RECARGA, "50000")
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        self.client.force_login(self.cajero)

    def test_el_punto_de_venta_recien_abierto_no_ensena_ningun_saldo(self):
        """Entrar a la caja no es cobrar. Sin tarjeta no hay cifra."""
        cuerpo = self.client.get(reverse("punto-de-venta")).content.decode()

        self.assertNotIn("$", cuerpo)
        self.assertNotIn("Consumo de hoy", cuerpo)

    def test_no_hay_listado_de_estudiantes_para_el_cajero(self):
        """El panel del acudiente es de `USR-2` y enseña saldos (`HU-07`).

        Si el cajero llegara, tendría el saldo de todos los estudiantes de esa
        cuenta sin cobrar nada.
        """
        respuesta = self.client.get(reverse("mis-estudiantes"))

        self.assertEqual(respuesta.status_code, 403)

    def test_el_cajero_no_alcanza_la_ficha_de_un_estudiante(self):
        respuesta = self.client.get(
            reverse("estudiante-seleccionado", args=[self.estudiante.id])
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_el_cajero_no_alcanza_la_pantalla_de_recarga(self):
        """Donde también se ve el saldo, y además se escribe."""
        respuesta = self.client.get(reverse("recarga", args=[self.estudiante.id]))

        self.assertEqual(respuesta.status_code, 403)

    def test_cada_escaneo_trae_el_panel_a_la_vista(self):
        """`show:top` en el `hx-swap`, y sin él `HU-17` no se cumple en la caja.

        A 1024 × 600 —la pantalla que `INT-2` declara— la columna del estudiante
        deja 317 px visibles y la caja de búsqueda ocupa 298: lo que el fragmento
        trae nace por debajo del pliegue, y `autofocus` mantiene el scroll en el
        campo. Con `show:top`, cada tarjeta pasada sube su propio resultado.

        Se comprueba en las **dos** vías: si una lo pierde, el saldo deja de
        verse por ahí sin que nada falle.
        """
        cuerpo = self.client.get(reverse("punto-de-venta")).content.decode()

        self.assertEqual(cuerpo.count('hx-swap="innerHTML show:top"'), 2)

    def test_el_cajero_no_entra_a_la_administracion(self):
        """`INT-3` es de `USR-4` y `USR-5` (`[S11]`). El cajero no tiene `is_staff`."""
        respuesta = self.client.get("/admin/", follow=True)

        self.assertNotIn("Movimientos de billetera", respuesta.content.decode())
