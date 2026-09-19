"""`TT-159`. El recuento de días sobre el que se evalúan las reglas (`HU-31`).

Aquí se comprueba **lo que la base cuenta**, no el veredicto: los umbrales
tienen su propio fichero, `tests_reglas.py`, y no necesitan datos. Lo que esta
mitad puede equivocarse es en qué entra en el recuento y con qué fecha, y son
cuatro decisiones del documento que ninguna historia menciona:

1. **Días distintos, no unidades** (`[S2.1]`).
2. **Ventana de 14 días naturales, hoy incluido** (`[S2.2]`).
3. **La reserva sin recoger no cuenta, y la entregada cuenta el día que se
   entregó** (`[S2.3]`).
4. **La categoría es la del producto hoy** (`[S2.4]`), la única cifra del
   módulo que no sale de la instantánea de `DT-8`.

Las fechas se fijan a mano sobre una jornada elegida, y el selector recibe
`hoy=` en vez de mirar el reloj: una prueba de ventanas que dependa de a qué
hora se ejecute falla sola una madrugada y nadie sabe por qué.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone

from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from reportes.reglas import DIAS_DE_LA_VENTANA, UMBRAL_FRECUENCIA_ALTA
from reportes.selectors import alertas_de_frecuencia, dias_de_consumo_por_categoria
from ventas.models import MedioDePago, PedidoAnticipado, Venta
from ventas.services import entregar, registrar_venta, reservar

# Una jornada cualquiera, fija. Que sea fija es lo que hace repetible una prueba
# de ventanas.
HOY = date(2026, 9, 19)


def a_mediodia(dia):
    """El día, a las 12:00 **de Bogotá**.

    A mediodía y no a medianoche: `TruncDate` corta en la zona horaria del
    colegio, y una compra de las 00:30 locales es del día anterior en UTC. Al
    mediodía las dos lecturas coinciden, así que si alguna vez el corte se hace
    mal, lo caza `test_el_dia_se_corta_en_la_zona_del_colegio` y no un fallo
    intermitente en todas las demás.
    """
    return timezone.make_aware(datetime.combine(dia, time(12, 0)))


class BaseDeFrecuencia(TestCase):
    """Una familia con saldo, un cajero y dos categorías en el catálogo."""

    def setUp(self):
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero-frecuencia@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        self.acudiente = Usuario.objects.crear_usuario(
            email="marta-frecuencia@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
        )
        ficha = Acudiente.objects.create(
            usuario=self.acudiente, nombre="Marta Ruiz Ochoa", documento="4310099001"
        )
        self.estudiante = Estudiante.objects.create(
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001099001",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("500000")
        )
        self.pan = self.producto("Pan de queso", "Panadería")
        self.jugo = self.producto("Jugo de mora", "Bebidas")

    def producto(self, nombre, categoria):
        una_categoria, _ = Categoria.objects.get_or_create(nombre=categoria)
        articulo = Producto.objects.create(
            nombre=nombre, precio=Decimal("2500"), categoria=una_categoria
        )
        MovimientoInventario.objects.create(
            producto=articulo,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=200,
            motivo="Ingreso de prueba",
        )
        return articulo

    def comprar(self, dias_atras=0, articulo=None, cantidad=1, estudiante=None):
        """Una venta del mostrador, fechada `dias_atras` días antes de `HOY`."""
        venta = registrar_venta(
            actor=self.cajero,
            estudiante=estudiante or self.estudiante,
            lineas={(articulo or self.pan).id: cantidad},
        )
        # `creado_en` es `auto_now_add`, así que no se puede fijar al crear.
        Venta.objects.filter(pk=venta.pk).update(
            creado_en=a_mediodia(HOY - timedelta(days=dias_atras))
        )
        return venta

    def reservar_para(self, dias_atras=0, articulo=None):
        pedido = reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={(articulo or self.pan).id: 1},
        )
        Venta.objects.filter(pk=pedido.venta_id).update(
            creado_en=a_mediodia(HOY - timedelta(days=dias_atras))
        )
        return pedido

    def entregar_el_dia(self, pedido, dias_atras):
        entregar(actor=self.cajero, pedido=pedido)
        PedidoAnticipado.objects.filter(pk=pedido.pk).update(
            entregado_en=a_mediodia(HOY - timedelta(days=dias_atras))
        )
        return pedido

    def recuento(self, estudiante=None):
        return dias_de_consumo_por_categoria(
            actor=self.acudiente, estudiante=estudiante or self.estudiante, hoy=HOY
        )


class SeCuentanDiasNoUnidadesTest(BaseDeFrecuencia):
    """`[S2.1]`. Dos empanadas el mismo martes son un día de `Almuerzo`."""

    def test_dos_compras_del_mismo_dia_cuentan_una_vez(self):
        self.comprar(dias_atras=3)
        self.comprar(dias_atras=3)

        self.assertEqual(self.recuento(), {"Panadería": 1})

    def test_varias_unidades_en_un_renglon_tampoco_multiplican(self):
        self.comprar(dias_atras=2, cantidad=7)

        self.assertEqual(self.recuento(), {"Panadería": 1})

    def test_dias_distintos_suman(self):
        for dia in (0, 1, 2):
            self.comprar(dias_atras=dia)

        self.assertEqual(self.recuento(), {"Panadería": 3})

    def test_cada_categoria_se_cuenta_por_su_lado(self):
        self.comprar(dias_atras=0)
        self.comprar(dias_atras=1)
        self.comprar(dias_atras=0, articulo=self.jugo)

        self.assertEqual(self.recuento(), {"Panadería": 2, "Bebidas": 1})


class LaVentanaSonCatorceDiasTest(BaseDeFrecuencia):
    """`[S2.2]`. Con el de hoy incluido, así que el borde está en el día 13."""

    def test_hoy_entra(self):
        self.comprar(dias_atras=0)

        self.assertEqual(self.recuento(), {"Panadería": 1})

    def test_el_ultimo_dia_de_la_ventana_entra(self):
        self.comprar(dias_atras=DIAS_DE_LA_VENTANA - 1)

        self.assertEqual(self.recuento(), {"Panadería": 1})

    def test_el_dia_anterior_a_la_ventana_ya_no_entra(self):
        """El borde exacto. Un `>` donde va `>=` desplaza la regla un día
        entero y las cifras siguen pareciendo razonables."""
        self.comprar(dias_atras=DIAS_DE_LA_VENTANA)

        self.assertEqual(self.recuento(), {})

    def test_lo_muy_antiguo_no_cuenta_aunque_sea_mucho(self):
        for dia in range(30, 40):
            self.comprar(dias_atras=dia)

        self.assertEqual(self.recuento(), {})

    def test_el_dia_se_corta_en_la_zona_del_colegio(self):
        """`America/Bogota`, no UTC.

        Una compra de las 19:00 de Bogotá son las 00:00 UTC del día siguiente:
        partir el día por UTC la movería de jornada y, en el borde de la
        ventana, la metería o la sacaría del recuento.
        """
        venta = self.comprar(dias_atras=0)
        Venta.objects.filter(pk=venta.pk).update(
            creado_en=timezone.make_aware(datetime.combine(HOY, time(19, 0)))
        )

        self.assertEqual(self.recuento(), {"Panadería": 1})


class LasReservasCuentanCuandoSeRecogenTest(BaseDeFrecuencia):
    """`[S2.3]`. La regla habla de **consumo**, no de compras.

    Es la diferencia declarada con el historial de `HU-30`, que sí las enseña
    todas: un historial responde «qué se ha comprado» y esto responde «con qué
    frecuencia se ha consumido».
    """

    def test_una_reserva_sin_recoger_no_cuenta(self):
        self.reservar_para(dias_atras=1)

        self.assertEqual(self.recuento(), {})

    def test_una_reserva_entregada_cuenta(self):
        pedido = self.reservar_para(dias_atras=2)
        self.entregar_el_dia(pedido, dias_atras=1)

        self.assertEqual(self.recuento(), {"Panadería": 1})

    def test_cuenta_el_dia_de_la_entrega_y_no_el_del_pago(self):
        """El acudiente puede pagar el domingo por la noche lo del lunes.

        Se reserva **fuera** de la ventana y se entrega dentro: si contara el
        día del pago, no saldría nada.
        """
        pedido = self.reservar_para(dias_atras=DIAS_DE_LA_VENTANA + 5)
        self.entregar_el_dia(pedido, dias_atras=1)

        self.assertEqual(self.recuento(), {"Panadería": 1})

    def test_una_entrega_fuera_de_la_ventana_no_cuenta(self):
        """La contraprueba de la anterior: manda la fecha de entrega, en los
        dos sentidos."""
        pedido = self.reservar_para(dias_atras=1)
        self.entregar_el_dia(pedido, dias_atras=DIAS_DE_LA_VENTANA + 2)

        self.assertEqual(self.recuento(), {})

    def test_la_entrega_y_el_mostrador_del_mismo_dia_son_un_dia(self):
        pedido = self.reservar_para(dias_atras=3)
        self.entregar_el_dia(pedido, dias_atras=2)
        self.comprar(dias_atras=2)

        self.assertEqual(self.recuento(), {"Panadería": 1})


class LaCategoriaEsLaDeHoyTest(BaseDeFrecuencia):
    """`[S2.4]`. La única cifra del módulo que **no** sale de la instantánea.

    `TT-84` congeló el precio y los nutrientes, no la categoría: no hay nada que
    congelar. Cambiar de categoría no reescribe lo que el niño comió, solo
    cambia cómo se agrupa.
    """

    def test_mover_el_producto_de_categoria_reagrupa_el_historico(self):
        self.comprar(dias_atras=0)
        self.comprar(dias_atras=1)

        almuerzo, _ = Categoria.objects.get_or_create(nombre="Almuerzo")
        self.pan.categoria = almuerzo
        self.pan.save(update_fields=["categoria"])

        self.assertEqual(self.recuento(), {"Almuerzo": 2})


class ElRecuentoEsDeUnSoloEstudianteTest(BaseDeFrecuencia):
    def test_la_compra_de_un_hermano_no_entra(self):
        hermano = Estudiante.objects.create(
            nombre="Tomás Restrepo Ruiz",
            documento="1001099002",
            acudiente=self.estudiante.acudiente,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        recargar(actor=self.acudiente, estudiante=hermano, monto=Decimal("50000"))
        for dia in range(5):
            self.comprar(dias_atras=dia, estudiante=hermano)

        self.assertEqual(self.recuento(), {})

    def test_la_venta_generica_no_es_consumo_de_nadie(self):
        """`DEC-1`, `HU-53`. Sin estudiante no hay a quién atribuirla."""
        for dia in range(6):
            venta = registrar_venta(
                actor=self.cajero,
                lineas={self.pan.id: 1},
                medio_pago=MedioDePago.EFECTIVO,
            )
            Venta.objects.filter(pk=venta.pk).update(
                creado_en=a_mediodia(HOY - timedelta(days=dia))
            )

        self.assertEqual(self.recuento(), {})


class LasAlertasSalenDelRecuentoTest(BaseDeFrecuencia):
    """Las dos mitades juntas: la base cuenta y `reportes.reglas` decide."""

    def comprar_dias(self, cuantos, articulo=None):
        for dia in range(cuantos):
            self.comprar(dias_atras=dia, articulo=articulo)

    def alertas(self):
        return alertas_de_frecuencia(
            actor=self.acudiente, estudiante=self.estudiante, hoy=HOY
        )

    def test_sin_compras_no_hay_ninguna_alerta(self):
        self.assertEqual(self.alertas(), [])

    def test_un_consumo_por_debajo_del_umbral_no_genera_alerta(self):
        self.comprar_dias(UMBRAL_FRECUENCIA_ALTA - 1)

        self.assertEqual(self.alertas(), [])

    def test_al_llegar_al_umbral_aparece_la_alerta_de_esa_categoria(self):
        self.comprar_dias(UMBRAL_FRECUENCIA_ALTA)

        alertas = self.alertas()

        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0].categoria, "Panadería")
        self.assertEqual(alertas[0].dias, UMBRAL_FRECUENCIA_ALTA)

    def test_una_categoria_por_encima_y_otra_por_debajo(self):
        """La que no llega **no se publica**, ni siquiera como «normal»
        (`ALC-OUT-20`)."""
        self.comprar_dias(UMBRAL_FRECUENCIA_ALTA + 1)
        self.comprar_dias(2, articulo=self.jugo)

        self.assertEqual([alerta.categoria for alerta in self.alertas()], ["Panadería"])


class SoloSuAcudienteConsultaLaFrecuenciaTest(BaseDeFrecuencia):
    """`[S11]`. La misma puerta que el historial, y por el mismo motivo.

    No basta con que la pantalla sea del acudiente: el selector lo comprueba,
    porque `DT-11` pone el control de acceso en la capa de datos.
    """

    def test_ningun_otro_rol_cuenta_el_consumo_de_un_estudiante(self):
        for numero, rol in enumerate((Rol.CAJERO, Rol.ADMINISTRADOR, Rol.INSTITUCION)):
            with self.subTest(rol=rol):
                actor = Usuario.objects.crear_usuario(
                    email=f"otro-frecuencia-{numero}@example.com",
                    rol=rol,
                    nombre="Persona",
                )
                with self.assertRaises(PermissionDenied):
                    dias_de_consumo_por_categoria(
                        actor=actor, estudiante=self.estudiante
                    )

    def test_un_acudiente_ajeno_tampoco(self):
        otro = Usuario.objects.crear_usuario(
            email="ajeno-frecuencia@example.com", rol=Rol.ACUDIENTE, nombre="Andrés"
        )
        Acudiente.objects.create(
            usuario=otro, nombre="Andrés Ospina", documento="7100099001"
        )

        with self.assertRaises(PermissionDenied):
            alertas_de_frecuencia(actor=otro, estudiante=self.estudiante)
