"""`TT-78`, `TT-79`. El medio de pago de toda venta (`HU-54`, `DEC-1`).

Los cuatro criterios de `HU-54`:

1. **Toda venta registra su medio de pago**: `billetera`, `efectivo` o
   `transferencia`. El campo no admite nada más y no admite quedarse vacío.
2. **Las ventas de estudiante son siempre `billetera`.** Y su otra mitad, que
   está en `DEC-1`: los medios de una venta genérica son efectivo y
   transferencia. Juntas son una sola regla —hay estudiante **si y solo si** el
   medio es billetera—, y quien la impone es la base, no un `if` (`DT-15`).
3. **La transferencia no pasa por el sistema.** No hay nada que probar de una
   operación que ocurre fuera; lo que sí se comprueba es que la pantalla lo diga,
   porque quien lee «Transferencia» en una caja puede entender que el sistema la
   cobra.
4. **Ninguna modalidad mueve dinero real.** Es `ALC-OUT-01`: no hay pasarela que
   probar, y la ausencia se sostiene no habiéndola.

Lo que **no** se prueba aquí porque todavía no existe: que la venta se asiente
(`TT-80`, `PR-12`) y que la genérica se pueda emitir desde la pantalla (`HU-53`,
`PR-15`). Este PR trae el campo y el control; el cobro los usará.
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from ventas.models import LineaVenta, MedioDePago, Venta


def cajero(email="cajero@example.com"):
    return Usuario.objects.crear_usuario(email=email, rol=Rol.CAJERO, nombre="Cajero")


def estudiante(documento="1001234501"):
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente{documento}@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
    )
    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"43{documento}"
    )
    return Estudiante.objects.create(
        nombre="Ana Sofía Restrepo Ruiz",
        documento=documento,
        acudiente=acudiente,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )


def producto(nombre="Empanada"):
    categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
    return Producto.objects.create(nombre=nombre, precio=3500, categoria=categoria)


class ElMedioDePagoSeAtaAlClienteTest(TestCase):
    """Segundo criterio de `HU-54` más `DEC-1`, que son la misma regla.

    **La impone la base.** El servicio de venta es de `TT-80` y lo escribe otra
    persona dos semanas después; una regla que depende de que alguien se acuerde
    de comprobarla no es una regla, es una costumbre (`DT-15`, `DT-24`).
    """

    def setUp(self):
        self.cajero = cajero()
        self.estudiante = estudiante()

    def test_la_venta_a_un_estudiante_se_paga_con_su_billetera(self):
        venta = Venta.objects.create(
            cajero=self.cajero,
            estudiante=self.estudiante,
            medio_pago=MedioDePago.BILLETERA,
        )

        self.assertEqual(venta.medio_pago, MedioDePago.BILLETERA)
        self.assertFalse(venta.es_generica)

    def test_una_venta_de_estudiante_no_se_paga_en_efectivo(self):
        """Sería devolverle al menor el dinero suelto que `OBJ-GEN` vino a quitar
        de en medio, y dejaría su saldo sin reflejar lo que consumió."""
        for medio in [MedioDePago.EFECTIVO, MedioDePago.TRANSFERENCIA]:
            with self.subTest(medio=medio):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Venta.objects.create(
                        cajero=self.cajero,
                        estudiante=self.estudiante,
                        medio_pago=medio,
                    )

    def test_la_venta_generica_se_paga_en_efectivo_o_por_transferencia(self):
        """`DEC-1`. Sin estudiante no hay restricciones que aplicar ni billetera
        que descontar; lo que sí hay es inventario que descontar (`ALC-IN-17`)."""
        for medio in [MedioDePago.EFECTIVO, MedioDePago.TRANSFERENCIA]:
            with self.subTest(medio=medio):
                venta = Venta.objects.create(cajero=self.cajero, medio_pago=medio)

                self.assertTrue(venta.es_generica)

    def test_sin_estudiante_no_se_cobra_contra_ninguna_billetera(self):
        """La billetera es individual por estudiante (`HU-06`): cobrar contra
        ella sin decir de quién no significa nada."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Venta.objects.create(cajero=self.cajero, medio_pago=MedioDePago.BILLETERA)

    def test_no_hay_un_cuarto_medio_de_pago(self):
        """Primer criterio: los tres de `DEC-1` y ninguno más.

        `full_clean` es lo que valida las opciones —la base guarda un texto—, así
        que lo que se comprueba es que el campo las declare.
        """
        venta = Venta(
            cajero=self.cajero, estudiante=self.estudiante, medio_pago="tarjeta"
        )

        with self.assertRaises(ValidationError):
            venta.full_clean()

    def test_el_medio_de_pago_no_se_queda_vacio(self):
        venta = Venta(cajero=self.cajero, estudiante=self.estudiante, medio_pago="")

        with self.assertRaises(ValidationError):
            venta.full_clean()


class LaLineaDeVentaEsUnRenglonPorProductoTest(TestCase):
    """`TT-78`. Lo que la base puede imponer sobre el renglón."""

    def setUp(self):
        self.venta = Venta.objects.create(cajero=cajero(), medio_pago=MedioDePago.EFECTIVO)
        self.producto = producto()

    def test_dos_renglones_del_mismo_producto_son_el_mismo_renglon(self):
        """El total saldría igual —es una suma—, pero el reporte de `HU-35`
        tendría que decidir si «tres empanadas» son una línea o tres. Obliga al
        carrito de `TT-81` a agrupar, que es además lo que el cajero espera."""
        LineaVenta.objects.create(
            venta=self.venta, producto=self.producto, cantidad=2, precio_unitario=3500
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            LineaVenta.objects.create(
                venta=self.venta, producto=self.producto, cantidad=1, precio_unitario=3500
            )

    def test_el_mismo_producto_en_otra_venta_si(self):
        otra = Venta.objects.create(cajero=cajero("otro@example.com"),
                                    medio_pago=MedioDePago.EFECTIVO)
        LineaVenta.objects.create(
            venta=self.venta, producto=self.producto, cantidad=2, precio_unitario=3500
        )

        LineaVenta.objects.create(
            venta=otra, producto=self.producto, cantidad=1, precio_unitario=3500
        )

        self.assertEqual(LineaVenta.objects.count(), 2)

    def test_no_se_vende_una_cantidad_de_cero_ni_negativa(self):
        """Media empanada no se vende y menos una tampoco: el signo lo pone el
        movimiento de inventario, no el renglón."""
        for cantidad in [0, -1]:
            with self.subTest(cantidad=cantidad):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    LineaVenta.objects.create(
                        venta=self.venta,
                        producto=self.producto,
                        cantidad=cantidad,
                        precio_unitario=3500,
                    )

    def test_la_linea_congela_el_precio_y_los_nutrientes(self):
        """`TT-84`, `DT-8`, `HU-22`. Hasta `PR-13` esta prueba afirmaba lo
        contrario —que la línea **no** guardaba el precio— y era cierta: la
        historia que lo congela no había llegado. Lo que se vigila ahora es que
        la instantánea siga completa.

        Se compara contra `CAMPOS_DE_LA_INSTANTANEA`, que es la lista que el
        servicio copia: si alguien añade un nutriente al catálogo y no lo trae
        aquí, el historial se queda corto sin que nada falle."""
        campos = {f.name for f in LineaVenta._meta.get_fields()}

        self.assertIn("precio_unitario", campos)
        for campo in LineaVenta.CAMPOS_DE_LA_INSTANTANEA:
            with self.subTest(campo=campo):
                self.assertIn(campo, campos)


class LosLibrosSenalanLaVentaQueLosOriginaTest(TestCase):
    """`TT-78`. La clave ajena que `TT-59` y `TT-67` dejaron prometida.

    Es la mitad de `INV-2` e `INV-3` que faltaba: que el saldo y las existencias
    se reconstruyan desde el historial exige que cada sumando se pueda explicar,
    y «−3.500» sin decir de qué compra sale no explica nada.
    """

    def setUp(self):
        self.estudiante = estudiante()
        self.venta = Venta.objects.create(
            cajero=cajero(), estudiante=self.estudiante, medio_pago=MedioDePago.BILLETERA
        )

    def test_un_movimiento_de_venta_sin_su_venta_no_entra(self):
        from decimal import Decimal

        from billetera.models import Billetera, MovimientoBilletera, TipoDeMovimiento

        billetera = Billetera.objects.create(estudiante=self.estudiante)

        with self.assertRaises(IntegrityError), transaction.atomic():
            MovimientoBilletera.objects.create(
                billetera=billetera, tipo=TipoDeMovimiento.VENTA, monto=Decimal("-3500")
            )

    def test_una_recarga_no_sale_de_una_venta(self):
        """Sin esto, el libro podría decir que un ingreso de saldo salió de una
        compra."""
        from decimal import Decimal

        from billetera.models import Billetera, MovimientoBilletera, TipoDeMovimiento

        billetera = Billetera.objects.create(estudiante=self.estudiante)

        with self.assertRaises(IntegrityError), transaction.atomic():
            MovimientoBilletera.objects.create(
                billetera=billetera,
                tipo=TipoDeMovimiento.RECARGA,
                monto=Decimal("50000"),
                venta=self.venta,
            )

    def test_una_salida_de_inventario_por_venta_senala_cual(self):
        from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario

        with self.assertRaises(IntegrityError), transaction.atomic():
            MovimientoInventario.objects.create(
                producto=producto(),
                tipo=TipoDeMovimientoDeInventario.VENTA,
                cantidad=-1,
            )

    def test_un_ingreso_no_sale_de_una_venta(self):
        """El ingreso y la merma son manuales: los explica su motivo (`INV-8`),
        no una compra que no existió."""
        from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario

        with self.assertRaises(IntegrityError), transaction.atomic():
            MovimientoInventario.objects.create(
                producto=producto(),
                tipo=TipoDeMovimientoDeInventario.INGRESO,
                cantidad=10,
                venta=self.venta,
            )

    def test_asentar_en_la_billetera_exige_la_venta(self):
        """`DT-24`: **todo movimiento pasa por `asentar()`**, así que es ahí donde
        la exigencia tiene que estar además de en la base.

        La restricción de la base no se olvida; el mensaje de `asentar()` es el
        que se entiende. Y el argumento `venta` es, de paso, el único camino por
        el que el servicio de venta de `TT-80` podrá dejar la referencia.
        """
        from decimal import Decimal

        from billetera.services import asentar
        from billetera.models import TipoDeMovimiento

        with self.assertRaises(ValidationError):
            asentar(
                estudiante=self.estudiante,
                tipo=TipoDeMovimiento.VENTA,
                monto=Decimal("-3500"),
            )

    def test_asentar_acepta_la_venta_y_la_guarda(self):
        from decimal import Decimal

        from billetera.services import asentar
        from billetera.models import TipoDeMovimiento

        movimiento = asentar(
            estudiante=self.estudiante,
            tipo=TipoDeMovimiento.VENTA,
            monto=Decimal("-3500"),
            venta=self.venta,
        )

        self.assertEqual(movimiento.venta, self.venta)

    def test_asentar_en_inventario_exige_la_venta_en_la_salida_por_venta(self):
        from inventario.models import TipoDeMovimientoDeInventario
        from inventario.services import asentar

        with self.assertRaises(ValidationError):
            asentar(
                producto=producto(),
                tipo=TipoDeMovimientoDeInventario.VENTA,
                cantidad=-1,
            )

    def test_asentar_en_inventario_rechaza_la_venta_en_un_ingreso(self):
        """Un ingreso con una venta detrás contaría una compra que no existió."""
        from inventario.models import TipoDeMovimientoDeInventario
        from inventario.services import asentar

        with self.assertRaises(ValidationError):
            asentar(
                producto=producto(),
                tipo=TipoDeMovimientoDeInventario.INGRESO,
                cantidad=10,
                venta=self.venta,
            )

    def test_el_estudiante_que_no_opera_lo_es_antes_que_nada(self):
        """`INVD-2` se comprueba **antes** que la forma del movimiento.

        Las dos rechazan; lo que cambia es qué se le dice a quien llama. «Este
        estudiante no opera» es una respuesta sobre el mundo; «falta la
        referencia a la venta» es una respuesta sobre el código. Cobrarle a un
        estudiante de baja tiene que contestar lo primero.
        """
        from decimal import Decimal

        from billetera.models import TipoDeMovimiento
        from billetera.services import asentar
        from personas.services import EstudianteNoOperativo, dar_de_baja

        institucion = Usuario.objects.crear_usuario(
            email="institucion@example.com", rol=Rol.INSTITUCION, nombre="Colegio"
        )
        dar_de_baja(actor=institucion, estudiante=self.estudiante)

        with self.assertRaises(EstudianteNoOperativo):
            asentar(
                estudiante=self.estudiante,
                tipo=TipoDeMovimiento.VENTA,
                monto=Decimal("-3500"),
            )

    def test_una_venta_con_movimientos_no_se_puede_borrar(self):
        """`PROTECT`. Borrarla dejaría los movimientos sin lo que los explica, y
        el saldo que `INV-2` reconstruye pasaría a tener un sumando mudo."""
        from decimal import Decimal

        from django.db.models import ProtectedError

        from billetera.models import Billetera, MovimientoBilletera, TipoDeMovimiento

        billetera = Billetera.objects.create(estudiante=self.estudiante)
        MovimientoBilletera.objects.create(
            billetera=billetera,
            tipo=TipoDeMovimiento.VENTA,
            monto=Decimal("-3500"),
            venta=self.venta,
        )

        with self.assertRaises(ProtectedError):
            self.venta.delete()


class LaPantallaOfreceSoloLoQueLaBaseAdmiteTest(TestCase):
    """`TT-79`. El control, y que refleje la regla en vez de repetirla.

    No se comprueba «hay tres botones»: se comprueba que **lo que se ofrece
    coincide con lo que la base va a aceptar**. Es la propiedad que importa, y la
    que se rompe el día que alguien añada un medio en un sitio y no en el otro.
    """

    def setUp(self):
        self.estudiante = estudiante()
        self.client.force_login(cajero())
        self.pos = reverse("punto-de-venta")
        self.identificacion = reverse("identificacion-en-el-punto-de-venta")

    def test_sin_estudiante_se_ofrecen_efectivo_y_transferencia(self):
        cuerpo = self.client.get(self.pos).content.decode()

        self.assertIn('data-medio="efectivo"', cuerpo)
        self.assertIn('data-medio="transferencia"', cuerpo)

    def test_sin_estudiante_no_se_ofrece_la_billetera(self):
        """No es un botón apagado: **no es una opción**. Sin estudiante no hay
        billetera contra la que cobrar (`HU-06`)."""
        cuerpo = self.client.get(self.pos).content.decode()

        self.assertNotIn('data-medio="billetera"', cuerpo)

    def test_la_pantalla_avisa_de_que_la_transferencia_ocurre_fuera(self):
        """Tercer criterio de `HU-54`, y hay que decirlo **en la caja**: quien lee
        «Transferencia» puede entender que el sistema la cobra o que recarga
        algo, y lo único que hace es dejar constancia (`ALC-OUT-01`)."""
        cuerpo = self.client.get(self.pos).content.decode()

        self.assertIn("por fuera", cuerpo)
        self.assertIn("queda constancia", cuerpo)

    def test_al_identificar_a_un_estudiante_el_medio_pasa_a_billetera(self):
        cuerpo = self.client.get(
            self.identificacion, {"codigo": self.estudiante.codigo_tarjeta}
        ).content.decode()

        self.assertIn('data-medio-fijo="billetera"', cuerpo)
        self.assertIn('value="billetera"', cuerpo)

    def test_con_estudiante_ya_no_se_ofrece_elegir(self):
        """Con un estudiante delante, efectivo y transferencia no son opciones
        deshabilitadas: no son opciones. La base rechazaría la venta."""
        cuerpo = self.client.get(
            self.identificacion, {"codigo": self.estudiante.codigo_tarjeta}
        ).content.decode()

        self.assertNotIn('data-medio="efectivo"', cuerpo)
        self.assertNotIn('data-medio="transferencia"', cuerpo)

    def test_el_bloque_viaja_con_la_identificacion_y_no_en_otra_peticion(self):
        """`hx-swap-oob`. Una segunda llamada costaría otro viaje por tarjeta, y
        eso es lo que `INT-2` no tiene."""
        cuerpo = self.client.get(
            self.identificacion, {"codigo": self.estudiante.codigo_tarjeta}
        ).content.decode()

        self.assertIn('hx-swap-oob="true"', cuerpo)

    def test_una_tarjeta_desconocida_devuelve_el_medio_a_su_estado_sin_estudiante(self):
        """**El caso que se olvida.** Si el bloque se quedara con «Billetera» del
        escaneo anterior, el cajero cobraría contra el saldo de quien ya no está
        en pantalla."""
        cuerpo = self.client.get(
            self.identificacion, {"codigo": "ZZZZZZZZZZZZZZ"}
        ).content.decode()

        self.assertIn('data-medio="efectivo"', cuerpo)
        self.assertNotIn('data-medio-fijo="billetera"', cuerpo)

    def test_lo_que_se_ofrece_es_exactamente_lo_que_la_base_admite(self):
        """La propiedad que de verdad se quiere, comprobada contra el modelo.

        Si mañana alguien añade un medio a `MedioDePago` y no a la pantalla —o al
        revés—, esto falla. Es lo único que mantiene las dos listas juntas sin
        que nadie tenga que acordarse.
        """
        sin_estudiante = self.client.get(self.pos).content.decode()
        ofrecidos = {
            medio.value
            for medio in MedioDePago
            if f'data-medio="{medio.value}"' in sin_estudiante
        }

        admitidos_por_la_base = set()
        for medio in MedioDePago:
            try:
                with transaction.atomic():
                    Venta.objects.create(cajero=cajero(f"{medio.value}@example.com"),
                                         medio_pago=medio)
                admitidos_por_la_base.add(medio.value)
            except IntegrityError:
                pass

        self.assertEqual(ofrecidos, admitidos_por_la_base)
