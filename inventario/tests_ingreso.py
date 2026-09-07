"""`TT-67`, `TT-68`, `TT-69`. Ingreso de mercancía (`HU-27`, `DT-5`, `INV-3`, `INV-8`).

Los tres criterios de `HU-27`:

1. **El inventario opera sobre unidades vendibles**, no sobre insumos ni recetas.
   Se ve en el modelo: la cantidad es un entero de un producto del catálogo, y no
   hay nada que descomponer.
2. **El aumento se registra como ajuste manual de la administración.** De ella y
   de nadie más (`[S11]`).
3. **Un producto preparado en la cafetería entra por el mismo ajuste**, sin
   descomponerlo en insumos.

Y la decisión que sostiene el sprint entero, la misma de `PR-02` aplicada al otro
libro: **no existe una columna `existencias`**. Son la suma de los movimientos
(`INV-3`), así que la correspondencia con el historial es cierta por
construcción. `TST-4` la ejercitará en el Sprint 4 con la merma; aquí se
comprueba lo que ya se puede.

`INV-8` —toda disminución manual exige motivo— se crea con el modelo aunque
`HU-28` la ejercite más adelante: **es más barato poner la restricción ahora que
añadirla sobre datos ya escritos**.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de, existencias_por_producto, historial_de
from inventario.services import asentar, ingresar_mercancia

CLAVE = "clave-de-prueba-2026"


def producto(nombre="Empanada de carne", precio="3500"):
    categoria, _ = Categoria.objects.get_or_create(nombre="Comidas")
    return Producto.objects.create(
        nombre=nombre, precio=Decimal(precio), categoria=categoria
    )


def usuario_con_rol(rol, email):
    usuario = Usuario.objects.crear_usuario(email=email, rol=rol, nombre="Persona")
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
    return usuario


class LasExistenciasNoSeGuardanTest(TestCase):
    """`DT-5`, `INV-3`. La decisión que este PR no puede perder."""

    def test_el_producto_no_tiene_ninguna_columna_de_existencias(self):
        campos = {campo.name for campo in Producto._meta.get_fields()}

        for prohibido in ["existencias", "stock", "cantidad", "disponible"]:
            self.assertNotIn(prohibido, campos)

    def test_las_existencias_son_la_suma_de_los_movimientos(self):
        empanada = producto()

        asentar(producto=empanada, tipo=TipoDeMovimientoDeInventario.INGRESO, cantidad=30)
        asentar(producto=empanada, tipo=TipoDeMovimientoDeInventario.VENTA, cantidad=-4)
        asentar(
            producto=empanada,
            tipo=TipoDeMovimientoDeInventario.MERMA,
            cantidad=-2,
            motivo="Se cayeron al suelo",
        )

        self.assertEqual(existencias_de(empanada), 24)
        # Reconstruido a mano, por un camino distinto al de la base.
        self.assertEqual(sum(m.cantidad for m in historial_de(empanada)), 24)

    def test_sin_movimientos_son_cero_y_no_un_hueco(self):
        """No es un caso especial: es la suma de una lista vacía."""
        self.assertEqual(existencias_de(producto()), 0)


class ElSignoYElMotivoLosImponeLaBaseTest(TestCase):
    """`DT-15`: la invariante que la base pueda imponer, la impone la base."""

    def setUp(self):
        self.producto = producto()

    def _no_deja(self, tipo, cantidad, motivo=""):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MovimientoInventario.objects.create(
                    producto=self.producto, tipo=tipo, cantidad=cantidad, motivo=motivo
                )

    def test_un_ingreso_no_puede_ser_negativo(self):
        self._no_deja(TipoDeMovimientoDeInventario.INGRESO, -10)

    def test_una_venta_no_puede_sumar(self):
        self._no_deja(TipoDeMovimientoDeInventario.VENTA, 10)

    def test_ningun_movimiento_puede_ser_de_cero(self):
        self._no_deja(TipoDeMovimientoDeInventario.INGRESO, 0)

    def test_una_merma_sin_motivo_no_entra(self):
        """`INV-8`. Es la única forma de que desaparezcan existencias sin una
        venta que lo explique: sin motivo, el inventario tendría un agujero."""
        self._no_deja(TipoDeMovimientoDeInventario.MERMA, -3)

    def test_una_merma_con_motivo_si(self):
        MovimientoInventario.objects.create(
            producto=self.producto,
            tipo=TipoDeMovimientoDeInventario.MERMA,
            cantidad=-3,
            motivo="Caducadas",
        )

        self.assertEqual(existencias_de(self.producto), -3)


class ElIngresoEsDeLaAdministracionTest(TestCase):
    """Segundo criterio de `HU-27`, y `[S11]`."""

    def setUp(self):
        self.producto = producto()
        self.administracion = usuario_con_rol(Rol.ADMINISTRADOR, "admin@example.com")

    def test_la_administracion_registra_el_ingreso(self):
        movimiento = ingresar_mercancia(
            actor=self.administracion,
            producto=self.producto,
            cantidad=40,
            motivo="Pedido semanal",
        )

        self.assertEqual(movimiento.tipo, TipoDeMovimientoDeInventario.INGRESO)
        self.assertEqual(existencias_de(self.producto), 40)

    def test_ningun_otro_rol_ingresa(self):
        """Ni la institución, que no vende, ni el cajero, que cobra lo que ya está."""
        for rol in [Rol.CAJERO, Rol.INSTITUCION, Rol.ACUDIENTE]:
            with self.subTest(rol=rol):
                actor = usuario_con_rol(rol, f"{rol}@example.com")
                with self.assertRaises(PermissionDenied):
                    ingresar_mercancia(actor=actor, producto=self.producto, cantidad=10)

        self.assertEqual(existencias_de(self.producto), 0)

    def test_una_cuenta_desactivada_no_ingresa(self):
        self.administracion.is_active = False
        self.administracion.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            ingresar_mercancia(actor=self.administracion, producto=self.producto, cantidad=10)

    def test_un_ingreso_de_cero_o_negativo_no_es_un_ingreso(self):
        for cantidad in [0, -5]:
            with self.subTest(cantidad=cantidad):
                with self.assertRaises(ValidationError):
                    ingresar_mercancia(
                        actor=self.administracion, producto=self.producto, cantidad=cantidad
                    )

        self.assertEqual(MovimientoInventario.objects.count(), 0)

    def test_el_producto_preparado_entra_igual_que_el_comprado(self):
        """Tercer criterio: treinta empanadas hechas esta mañana son treinta
        unidades vendibles, y no se descomponen en harina y aceite."""
        preparado = producto(nombre="Empanada de la casa")

        ingresar_mercancia(
            actor=self.administracion,
            producto=preparado,
            cantidad=30,
            motivo="Producción del martes",
        )

        self.assertEqual(existencias_de(preparado), 30)


class LasExistenciasSeLeenDeUnaVezTest(TestCase):
    """`TT-69`. El listado de la administración no puede hacer una consulta por fila."""

    def test_una_consulta_para_todos_los_productos(self):
        administracion = usuario_con_rol(Rol.ADMINISTRADOR, "admin2@example.com")
        uno, otro = producto("Jugo de mango"), producto("Sándwich")
        ingresar_mercancia(actor=administracion, producto=uno, cantidad=12)
        ingresar_mercancia(actor=administracion, producto=otro, cantidad=5)
        sin_movimientos = producto("Galleta")

        with self.assertNumQueries(1):
            existencias = existencias_por_producto()

        self.assertEqual(existencias[uno.pk], 12)
        self.assertEqual(existencias[otro.pk], 5)
        # Los productos sin movimientos no aparecen: quien lo use lee con `.get(id, 0)`.
        self.assertNotIn(sin_movimientos.pk, existencias)


class LaInterfazAdministrativaTest(TestCase):
    """`TT-69`. `INT-3` es el admin de Django (`DT-2`), y el admin es una vista."""

    def setUp(self):
        # Por el camino real: `crear_cuenta` asigna el grupo del rol, y los
        # permisos van al grupo (`TT-15`). Poner `is_staff` a mano dejaría una
        # cuenta que entra al admin sin ningún permiso, que no es lo que hay que
        # probar.
        sincronizar_grupos_y_permisos()
        self.administracion = crear_cuenta(
            email="admin3@example.com",
            rol=Rol.ADMINISTRADOR,
            nombre="Administración de la cafetería",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.producto = producto()
        self.client.force_login(self.administracion)

    def test_alcanza_el_listado_de_movimientos(self):
        respuesta = self.client.get(
            reverse("admin:inventario_movimientoinventario_changelist")
        )

        self.assertEqual(respuesta.status_code, 200)

    def test_registra_un_ingreso_desde_el_formulario(self):
        """De extremo a extremo: el admin delega en el servicio (`DT-15`)."""
        respuesta = self.client.post(
            reverse("admin:inventario_movimientoinventario_add"),
            {"producto": str(self.producto.pk), "cantidad": "25", "motivo": "Pedido"},
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(existencias_de(self.producto), 25)
        movimiento = MovimientoInventario.objects.get()
        self.assertEqual(movimiento.tipo, TipoDeMovimientoDeInventario.INGRESO)

    def test_el_formulario_no_ofrece_elegir_el_tipo(self):
        """Solo ingresos desde aquí.

        La venta la asienta el punto de venta (`TT-80`) y la merma es `HU-28`.
        Ofrecer los tres tipos dejaría descontar existencias a mano saltándose la
        venta, que es lo que `INV-3` no admite.
        """
        cuerpo = self.client.get(
            reverse("admin:inventario_movimientoinventario_add")
        ).content.decode()

        self.assertNotIn('name="tipo"', cuerpo)

    def test_el_listado_de_productos_muestra_las_existencias(self):
        ingresar_mercancia(actor=self.administracion, producto=self.producto, cantidad=17)

        cuerpo = self.client.get(
            reverse("admin:catalogo_producto_changelist")
        ).content.decode()

        self.assertIn("17", cuerpo)
        self.assertIn("existencias", cuerpo.lower())

    def test_el_cajero_no_alcanza_el_inventario(self):
        cajero = crear_cuenta(
            email="cajero-admin@example.com",
            rol=Rol.CAJERO,
            nombre="Cajero",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.client.force_login(cajero)

        respuesta = self.client.get(
            reverse("admin:inventario_movimientoinventario_changelist")
        )

        self.assertEqual(respuesta.status_code, 403)
