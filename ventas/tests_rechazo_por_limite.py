"""`TT-118`. Venta rechazada por el cupo del día (`HU-20`, `HU-09`, **`TST-2`**).

═══════════════════════════════════════════════════════════════════════════
**EL CASO QUE IMPORTA ES EL CONTRAINTUITIVO: HAY SALDO Y LA VENTA SE RECHAZA.**

Un límite que solo se cumple cuando además falta dinero no es un límite, es una
coincidencia. Por eso casi todas las pruebas de este fichero recargan de sobra
antes de cobrar: lo que se demuestra es que la cifra que decide **no es el
saldo**.
═══════════════════════════════════════════════════════════════════════════

Los tres criterios de `HU-20`:

1. **El consumo del día se evalúa contra el límite en cada venta**, dentro del
   bloqueo de la transacción (`DT-6`). El consumo sale del mismo libro que el
   saldo (`INV-2`): no hay contador diario que alguien tenga que poner a cero.
2. **Si el cupo del día es insuficiente, la venta no se realiza, aunque haya
   saldo.**
3. **Es parte del escenario crítico `TST-2`**, cuya otra mitad —el rechazo por
   saldo— cerró `HU-19` en el Sprint 2.

**Y cierra el tercer criterio de `HU-09`**, que `PR-01` dejó abierto: «el límite
se evalúa contra el consumo del día en cada venta». `HU-09` dejó el cupo
configurable y escribible solo por el acudiente; esto es lo que lo hace valer.

El motivo se distingue del saldo, y no es cosmética: las dos cifras son de dinero
y las dos rechazan, pero «no alcanza» lo arregla una recarga y «se acabó el cupo»
no lo arregla ninguna. `ElMotivoNoSeConfundeConElSaldoTest` es la clase que lo
fija.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from billetera.models import MovimientoBilletera, TipoDeMovimiento
from billetera.selectors import consumo_del_dia, saldo_de
from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from restricciones.selectors import limite_diario_de
from restricciones.services import fijar_limite_diario, retirar_limite_diario
from ventas.models import Venta
from ventas.services import (
    LimiteDiarioSuperado,
    SaldoInsuficiente,
    registrar_venta,
)

CLAVE = "clave-de-prueba-2026"


def escenario():
    """Un cajero, un acudiente con su hijo, y dos productos con existencias."""
    cajero = Usuario.objects.crear_usuario(
        email="cajero-lim@example.com", rol=Rol.CAJERO, nombre="Cajero"
    )
    cajero.set_password(CLAVE)
    cajero.save(update_fields=["password"])

    acudiente = Usuario.objects.crear_usuario(
        email="acudiente-lim@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
    )
    ficha = Acudiente.objects.create(
        usuario=acudiente, nombre="Marta Ruiz Ochoa", documento="4310077777"
    )
    estudiante = Estudiante.objects.create(
        nombre="Ana Sofía Restrepo Ruiz",
        documento="1001277701",
        acudiente=ficha,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )

    categoria = Categoria.objects.create(nombre="Cafetería")
    productos = []
    for nombre, precio in (("Almuerzo", "6000"), ("Jugo", "2000")):
        producto = Producto.objects.create(
            nombre=nombre, precio=Decimal(precio), categoria=categoria
        )
        MovimientoInventario.objects.create(
            producto=producto,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=100,
            motivo="Ingreso de prueba",
        )
        productos.append(producto)

    return cajero, acudiente, estudiante, productos


class BaseDeCupo(TestCase):
    """Con saldo de sobra siempre: lo que decide aquí nunca es el dinero."""

    def setUp(self):
        self.cajero, self.acudiente, self.estudiante, (
            self.almuerzo,
            self.jugo,
        ) = escenario()
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("100000")
        )

    def fijar_cupo(self, monto, estudiante=None):
        return fijar_limite_diario(
            actor=self.acudiente,
            estudiante=estudiante or self.estudiante,
            monto=Decimal(monto),
        )

    def vender(self, lineas, estudiante=None, **extra):
        return registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante if estudiante is None else estudiante,
            lineas=lineas,
            **extra,
        )


# --- Criterios 1 y 2: se evalúa en cada venta, y rechaza con saldo ---------


class ElCupoRechazaAunqueHayaSaldoTest(BaseDeCupo):
    """`TST-2` en su mitad del cupo."""

    def setUp(self):
        super().setUp()
        self.fijar_cupo("8000")

    def test_una_venta_que_pasa_del_cupo_se_rechaza_con_saldo_de_sobra(self):
        """El caso que da sentido a la historia.

        Hay $100.000 de saldo y el carrito suma $10.000: la venta se rechaza
        porque el cupo del día son $8.000. Ninguna recarga lo arregla.
        """
        self.assertEqual(saldo_de(self.estudiante), Decimal("100000.00"))

        with self.assertRaises(LimiteDiarioSuperado):
            self.vender({self.almuerzo.id: 1, self.jugo.id: 2})

    def test_no_se_descuenta_nada_ni_queda_venta(self):
        saldo_antes = saldo_de(self.estudiante)
        existencias_antes = existencias_de(self.almuerzo)

        with self.assertRaises(LimiteDiarioSuperado):
            self.vender({self.almuerzo.id: 2})

        self.assertEqual(saldo_de(self.estudiante), saldo_antes)
        self.assertEqual(existencias_de(self.almuerzo), existencias_antes)
        self.assertEqual(Venta.objects.count(), 0)

    def test_lo_que_cabe_en_el_cupo_se_vende(self):
        """El contraste. Sin esto, la prueba de arriba pasaría con una caja que
        rechazara siempre que hay cupo fijado."""
        self.assertIsNotNone(self.vender({self.almuerzo.id: 1}))

    def test_justo_el_cupo_exacto_se_vende(self):
        """El borde, y se decide a favor de vender.

        `8000 > 8000` es falso: gastar **exactamente** el cupo es gastarlo, no
        pasarse. Un límite de $8.000 que rechaza un almuerzo de $8.000 sería un
        límite de $7.999 y nadie lo habría escrito así.
        """
        self.fijar_cupo("8000")

        self.assertIsNotNone(self.vender({self.almuerzo.id: 1, self.jugo.id: 1}))
        self.assertEqual(consumo_del_dia(self.estudiante), Decimal("8000.00"))

    def test_un_peso_por_encima_del_cupo_se_rechaza(self):
        """La otra cara del borde: lo que decide es la comparación, no un margen."""
        self.fijar_cupo("7999")

        with self.assertRaises(LimiteDiarioSuperado):
            self.vender({self.almuerzo.id: 1, self.jugo.id: 1})


class ElCupoCuentaLoGastadoHoyTest(BaseDeCupo):
    """Primer criterio: **contra el consumo del día**, venta a venta."""

    def setUp(self):
        super().setUp()
        self.fijar_cupo("10000")

    def test_varias_ventas_pequenas_agotan_el_cupo(self):
        """Ninguna se pasa por sí sola; juntas sí.

        Es la forma en que un cupo se agota de verdad en una cafetería: no de
        una compra grande, sino de cuatro pequeñas.
        """
        for _ in range(5):
            self.vender({self.jugo.id: 1})

        self.assertEqual(consumo_del_dia(self.estudiante), Decimal("10000.00"))

        with self.assertRaises(LimiteDiarioSuperado):
            self.vender({self.jugo.id: 1})

    def test_el_consumo_sale_del_historial_y_no_de_un_contador(self):
        """`INV-2`. La cifra que decide es la suma de los movimientos del día.

        Se comprueba de la forma que lo demostraría si alguien añadiera un
        contador: se asienta una venta **en el libro** y la caja lo nota.
        """
        self.vender({self.jugo.id: 1})

        self.assertEqual(consumo_del_dia(self.estudiante), Decimal("2000.00"))
        self.assertEqual(
            MovimientoBilletera.objects.filter(
                billetera__estudiante=self.estudiante, tipo=TipoDeMovimiento.VENTA
            ).count(),
            1,
        )

    def test_lo_gastado_ayer_no_cuenta_hoy(self):
        """El cupo es **diario**: vuelve a empezar cada jornada.

        La venta de ayer se retrasa en el libro —es la única forma de tener
        pasado en una prueba— y el cupo de hoy sigue entero.
        """
        self.vender({self.almuerzo.id: 1})
        MovimientoBilletera.objects.filter(
            billetera__estudiante=self.estudiante, tipo=TipoDeMovimiento.VENTA
        ).update(creado_en=timezone.now() - timedelta(days=1))

        self.assertEqual(consumo_del_dia(self.estudiante), Decimal("0.00"))
        self.assertIsNotNone(self.vender({self.almuerzo.id: 1}))

    def test_una_recarga_no_libera_cupo(self):
        """Recargar sube el saldo y no toca el consumo del día.

        Es lo que hace que el motivo importe: si el cajero dice «no alcanza», el
        acudiente recarga y la venta se rechaza igual.
        """
        self.vender({self.almuerzo.id: 1})
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000")
        )

        with self.assertRaises(LimiteDiarioSuperado):
            self.vender({self.almuerzo.id: 1})


class SinCupoNoHayNadaQueComprobarTest(BaseDeCupo):
    """No haber fijado límite no es un límite de cero: son opuestos."""

    def test_sin_limite_se_vende_lo_que_el_saldo_aguante(self):
        self.assertIsNone(limite_diario_de(self.estudiante))

        self.assertIsNotNone(self.vender({self.almuerzo.id: 10}))

    def test_retirar_el_limite_devuelve_la_venta_a_la_normalidad(self):
        """`HU-61`: retirar borra la fila, no la pone en cero."""
        self.fijar_cupo("5000")
        with self.assertRaises(LimiteDiarioSuperado):
            self.vender({self.almuerzo.id: 1, self.jugo.id: 1})

        retirar_limite_diario(actor=self.acudiente, estudiante=self.estudiante)

        self.assertIsNotNone(self.vender({self.almuerzo.id: 1, self.jugo.id: 1}))

    def test_el_cupo_es_de_ese_estudiante(self):
        """Un acudiente con dos hijos fija dos cupos distintos (`HU-09`)."""
        hermano = Estudiante.objects.create(
            nombre="Tomás Restrepo Ruiz",
            documento="1001277702",
            acudiente=self.estudiante.acudiente,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        recargar(actor=self.acudiente, estudiante=hermano, monto=Decimal("100000"))
        self.fijar_cupo("3000")

        with self.assertRaises(LimiteDiarioSuperado):
            self.vender({self.almuerzo.id: 1})
        self.assertIsNotNone(self.vender({self.almuerzo.id: 1}, estudiante=hermano))

    def test_la_venta_a_cliente_generico_no_tiene_cupo(self):
        """`DEC-1`, `HU-53`: sin estudiante no hay acudiente que haya fijado nada."""
        venta = registrar_venta(
            actor=self.cajero,
            estudiante=None,
            lineas={self.almuerzo.id: 10},
            medio_pago="efectivo",
        )

        self.assertIsNone(venta.estudiante)


# --- Criterio 3: el motivo, y dónde se evalúa -----------------------------


class ElMotivoNoSeConfundeConElSaldoTest(BaseDeCupo):
    """Segundo criterio de `HU-20` y la razón de ser de `TT-117`.

    Las dos cifras son de dinero y las dos rechazan. Lo que las separa es la
    salida: una la arregla el acudiente recargando y la otra no.
    """

    def test_cada_motivo_lleva_su_etiqueta(self):
        self.assertEqual(LimiteDiarioSuperado.motivo, "limite-diario")
        self.assertNotEqual(LimiteDiarioSuperado.motivo, SaldoInsuficiente.motivo)

    def test_con_saldo_y_sin_cupo_el_motivo_es_el_cupo(self):
        self.fijar_cupo("5000")

        with self.assertRaises(LimiteDiarioSuperado):
            self.vender({self.almuerzo.id: 1, self.jugo.id: 1})

    def test_sin_saldo_y_con_cupo_de_sobra_el_motivo_es_el_saldo(self):
        """El contraste que impide que la clase entera pase por accidente."""
        pobre = Estudiante.objects.create(
            nombre="Sara Restrepo Ruiz",
            documento="1001277703",
            acudiente=self.estudiante.acudiente,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        self.fijar_cupo("50000", estudiante=pobre)

        with self.assertRaises(SaldoInsuficiente):
            self.vender({self.almuerzo.id: 1}, estudiante=pobre)

    def test_sin_saldo_y_sin_cupo_gana_el_cupo(self):
        """Los dos motivos a la vez, y se responde el que no se arregla solo.

        Contestar «no alcanza» mandaría al acudiente a recargar para que la
        venta volviera a rechazarse, esta vez sin explicación nueva.
        """
        pobre = Estudiante.objects.create(
            nombre="Luis Restrepo Ruiz",
            documento="1001277704",
            acudiente=self.estudiante.acudiente,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        self.fijar_cupo("1000", estudiante=pobre)

        with self.assertRaises(LimiteDiarioSuperado):
            self.vender({self.almuerzo.id: 1}, estudiante=pobre)

    def test_el_mensaje_lleva_las_cifras_con_las_que_se_decidio(self):
        self.fijar_cupo("8000")
        self.vender({self.jugo.id: 1})

        with self.assertRaises(LimiteDiarioSuperado) as capturado:
            self.vender({self.almuerzo.id: 1, self.jugo.id: 1})

        rechazo = capturado.exception
        self.assertEqual(rechazo.limite, Decimal("8000.00"))
        self.assertEqual(rechazo.consumido, Decimal("2000.00"))
        self.assertEqual(rechazo.disponible, Decimal("6000.00"))
        self.assertEqual(rechazo.total, Decimal("8000.00"))

    def test_el_mensaje_dice_que_recargar_no_lo_arregla(self):
        """La frase que evita el viaje en balde, y por eso se afirma.

        Es una excepción a «no afirmes sobre la copia»: aquí la copia **es** el
        criterio —que el motivo se distinga del saldo— y una prueba sobre la
        etiqueta no lo cubriría.
        """
        self.fijar_cupo("1000")

        with self.assertRaises(LimiteDiarioSuperado) as capturado:
            self.vender({self.almuerzo.id: 1})

        self.assertIn("Recargar no lo cambia", " ".join(capturado.exception.messages))


class SeValidaDespuesDeBloquearTest(BaseDeCupo):
    """`DT-6`: se bloquea, luego se valida, luego se escribe.

    Leer el consumo del día **fuera** del bloqueo daría el mismo resultado en
    todas las pruebas de arriba y dejaría colar dos ventas simultáneas que juntas
    pasan el cupo. Se fija mirando el orden real de las consultas, igual que en
    `tests_rechazo_por_alergeno.py`.
    """

    def test_el_consumo_se_lee_con_la_billetera_ya_bloqueada(self):
        self.fijar_cupo("50000")

        with CaptureQueriesContext(connection) as consultas:
            self.vender({self.jugo.id: 1})

        sentencias = [c["sql"] for c in consultas.captured_queries]
        bloqueo = next(
            (
                i
                for i, sql in enumerate(sentencias)
                if "FOR UPDATE" in sql.upper() and "billetera_billetera" in sql.lower()
            ),
            None,
        )
        consumo = next(
            (
                i
                for i, sql in enumerate(sentencias)
                if "sum" in sql.lower() and "billetera_movimientobilletera" in sql.lower()
            ),
            None,
        )

        self.assertIsNotNone(bloqueo, "la venta no bloqueó la billetera (DT-6)")
        self.assertIsNotNone(consumo, "la venta no sumó el consumo del día")
        self.assertLess(
            bloqueo,
            consumo,
            "el consumo del día se leyó antes de bloquear la billetera: DT-6 pide "
            "bloquear, luego validar, luego escribir",
        )


class ElCajeroNoPuedeForzarloTest(BaseDeCupo):
    """`INV-4`: el cupo lo pone el acudiente y la caja no lo levanta."""

    def setUp(self):
        super().setUp()
        self.fijar_cupo("1000")

    def test_el_servicio_no_admite_ningun_argumento_que_lo_salte(self):
        with self.assertRaises(TypeError):
            self.vender({self.almuerzo.id: 1}, forzar=True)

    def test_el_cajero_no_puede_subir_el_cupo_para_luego_cobrar(self):
        with self.assertRaises(PermissionDenied):
            fijar_limite_diario(
                actor=self.cajero, estudiante=self.estudiante, monto=Decimal("99000")
            )

        self.assertEqual(limite_diario_de(self.estudiante).monto, Decimal("1000.00"))
        with self.assertRaises(LimiteDiarioSuperado):
            self.vender({self.almuerzo.id: 1})

    def test_el_cajero_no_puede_retirar_el_cupo(self):
        with self.assertRaises(PermissionDenied):
            retirar_limite_diario(actor=self.cajero, estudiante=self.estudiante)

        self.assertIsNotNone(limite_diario_de(self.estudiante))

    def test_reintentar_el_cobro_da_el_mismo_rechazo(self):
        for intento in range(3):
            with self.subTest(intento=intento):
                with self.assertRaises(LimiteDiarioSuperado):
                    self.vender({self.almuerzo.id: 1})


class LoQueElCajeroVeTest(BaseDeCupo):
    """`TT-117`. El motivo en la pantalla, por el camino real del cajero."""

    def setUp(self):
        super().setUp()
        self.fijar_cupo("1000")
        self.client.force_login(self.cajero)

    def _montar_y_cobrar(self, producto=None):
        self.client.get(
            reverse("identificacion-en-el-punto-de-venta"),
            {"codigo": self.estudiante.codigo_tarjeta},
        )
        self.client.post(
            reverse("carrito-del-punto-de-venta"),
            {"producto": str((producto or self.almuerzo).id), "accion": "anadir"},
        )
        return self.client.post(reverse("cobrar"))

    def test_el_ticket_marca_el_motivo_con_su_etiqueta(self):
        respuesta = self._montar_y_cobrar()

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'data-motivo="limite-diario"')

    def test_y_no_se_confunde_con_el_de_saldo(self):
        respuesta = self._montar_y_cobrar()

        self.assertNotContains(respuesta, 'data-motivo="saldo-insuficiente"')
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(saldo_de(self.estudiante), Decimal("100000.00"))

    def test_el_carrito_se_queda_montado_para_poder_corregirlo(self):
        self.assertContains(self._montar_y_cobrar(), "data-linea-de-venta")

    def test_la_pantalla_no_ofrece_ninguna_accion_para_forzar(self):
        cuerpo = self._montar_y_cobrar().content.decode().lower()

        for palabra in ["forzar", "omitir", "autorizar", "continuar de todos modos"]:
            with self.subTest(palabra=palabra):
                self.assertNotIn(palabra, cuerpo)
