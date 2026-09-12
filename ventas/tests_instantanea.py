"""`TT-84`, `TT-85`. La venta congela precio y nutrientes (`HU-22`, `DT-8`).

Los dos criterios de `HU-22`:

1. **La venta almacena la información nutricional vigente al momento de
   registrarse.** Es `TT-84`: la línea copia del producto, no lo referencia.
2. **Una edición posterior del catálogo no altera las ventas ya asentadas.** Es
   `TT-85`, y es el que de verdad prueba algo: la copia solo sirve si se
   comprueba que el original puede moverse sin arrastrarla.

**Por qué esto no es una desnormalización** (`DT-19`), que es la objeción obvia:
«lo que el producto declara hoy» y «lo que declaraba cuando se vendió» son hechos
distintos, no dos copias del mismo. Una desnormalización guarda un valor que se
podría recalcular; esto guarda uno que, sin copiarlo, se perdería para siempre.

La prueba a la que hay que mirar cuando esto falle es
`test_editar_el_producto_no_reescribe_la_venta`: si pasa a fallar, alguien
convirtió la instantánea en una referencia y el historial de consumo de `HU-30`
dejó de ser un historial.
"""

from decimal import Decimal

from django.test import TestCase

from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from billetera.services import recargar
from ventas.models import LineaVenta
from ventas.services import registrar_venta, total_de


def producto(nombre="Empanada de carne", precio="3500", existencias=20):
    categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
    articulo = Producto.objects.create(
        nombre=nombre,
        precio=Decimal(precio),
        categoria=categoria,
        porcion="unidad de 80 g",
        energia_kcal=210,
        proteinas_g=Decimal("6.50"),
        carbohidratos_g=Decimal("22.00"),
        azucares_g=Decimal("1.20"),
        grasas_totales_g=Decimal("11.00"),
        grasas_saturadas_g=Decimal("4.30"),
        sodio_mg=340,
    )
    MovimientoInventario.objects.create(
        producto=articulo,
        tipo=TipoDeMovimientoDeInventario.INGRESO,
        cantidad=existencias,
        motivo="Ingreso de prueba",
    )
    return articulo


class LaLineaCopiaLoQueElProductoDeclarabaTest(TestCase):
    """Primer criterio de `HU-22`."""

    def setUp(self):
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        acudiente = Usuario.objects.crear_usuario(
            email="acudiente@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
        )
        ficha = Acudiente.objects.create(
            usuario=acudiente, nombre="Marta Ruiz Ochoa", documento="4310012345"
        )
        self.estudiante = Estudiante.objects.create(
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001234501",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        recargar(actor=acudiente, estudiante=self.estudiante, monto=Decimal("100000"))
        self.empanada = producto()

    def _vender(self, cantidad=2):
        return registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante,
            lineas={self.empanada.id: cantidad},
        )

    def test_copia_el_precio_de_la_venta(self):
        venta = self._vender()

        linea = venta.lineas.get()
        self.assertEqual(linea.precio_unitario, Decimal("3500.00"))
        self.assertEqual(linea.importe, Decimal("7000.00"))

    def test_copia_todos_los_campos_declarados_de_la_instantanea(self):
        """Uno por uno, contra `CAMPOS_DE_LA_INSTANTANEA`.

        No se comprueba «algunos nutrientes»: si la lista del modelo crece y el
        servicio no la copia entera, esto falla. Es la única forma de que un
        nutriente nuevo no se pierda en silencio.
        """
        venta = self._vender()
        linea = venta.lineas.get()

        for campo in LineaVenta.CAMPOS_DE_LA_INSTANTANEA:
            with self.subTest(campo=campo):
                self.assertEqual(
                    getattr(linea, campo),
                    getattr(self.empanada, campo),
                    f"«{campo}» no llegó a la línea de venta",
                )

    def test_un_nutriente_no_declarado_sigue_sin_declarar(self):
        """Nulo significa «no declarado», no «cero» (`TT-44`).

        Convertirlo en cero haría que los reportes de `HU-30` sumaran ceros
        inventados en vez de enseñar que el dato falta.
        """
        self.empanada.sodio_mg = None
        self.empanada.save(update_fields=["sodio_mg"])

        venta = self._vender()

        self.assertIsNone(venta.lineas.get().sodio_mg)

    def test_el_total_sale_de_los_precios_congelados(self):
        venta = self._vender(cantidad=3)

        self.assertEqual(total_de(venta), Decimal("10500.00"))


class EditarElCatalogoNoAlteraLasVentasAsentadasTest(TestCase):
    """`TT-85`. **El segundo criterio, y el que prueba algo.**

    Una copia que nadie ha visto sobrevivir a una edición no es una copia: es un
    campo más que podría estar leyéndose del producto sin que nadie lo note.
    """

    def setUp(self):
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        acudiente = Usuario.objects.crear_usuario(
            email="acudiente@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
        )
        ficha = Acudiente.objects.create(
            usuario=acudiente, nombre="Marta Ruiz Ochoa", documento="4310012345"
        )
        self.estudiante = Estudiante.objects.create(
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001234501",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        recargar(actor=acudiente, estudiante=self.estudiante, monto=Decimal("100000"))
        self.empanada = producto()

        self.venta = registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 2},
        )

    def test_editar_el_producto_no_reescribe_la_venta(self):
        """**La prueba central de `HU-22`.**

        Se cambia todo lo que se puede cambiar —el precio y los ocho campos
        nutricionales— y la venta ya asentada tiene que decir exactamente lo
        mismo que decía.
        """
        antes = {
            campo: getattr(self.venta.lineas.get(), campo)
            for campo in LineaVenta.CAMPOS_DE_LA_INSTANTANEA
        }
        antes["precio_unitario"] = self.venta.lineas.get().precio_unitario

        self.empanada.precio = Decimal("9900")
        self.empanada.porcion = "unidad de 120 g"
        self.empanada.energia_kcal = 999
        self.empanada.proteinas_g = Decimal("99.00")
        self.empanada.carbohidratos_g = Decimal("99.00")
        self.empanada.azucares_g = Decimal("99.00")
        self.empanada.grasas_totales_g = Decimal("99.00")
        self.empanada.grasas_saturadas_g = Decimal("99.00")
        self.empanada.sodio_mg = 9999
        self.empanada.save()

        linea = LineaVenta.objects.get(venta=self.venta)
        for campo, valor in antes.items():
            with self.subTest(campo=campo):
                self.assertEqual(getattr(linea, campo), valor)

    def test_subir_el_precio_no_reescribe_el_total_de_la_venta_de_ayer(self):
        """Es la misma propiedad contada en pesos, que es como se nota.

        Sin la instantánea, un cambio de precio reescribiría el importe de todas
        las ventas pasadas del producto — y con él, el reporte de `HU-35` y lo
        que el acudiente ve en `HU-30`.
        """
        self.assertEqual(total_de(self.venta), Decimal("7000.00"))

        self.empanada.precio = Decimal("9900")
        self.empanada.save(update_fields=["precio"])

        self.venta.refresh_from_db()
        self.assertEqual(total_de(self.venta), Decimal("7000.00"))

    def test_la_venta_siguiente_si_usa_el_precio_nuevo(self):
        """La otra mitad, y hace falta: una instantánea que nunca se actualizara
        sería un precio fijado para siempre, no una fotografía."""
        self.empanada.precio = Decimal("4000")
        self.empanada.save(update_fields=["precio"])

        otra = registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 1},
        )

        self.assertEqual(total_de(otra), Decimal("4000.00"))
        self.assertEqual(total_de(self.venta), Decimal("7000.00"))

    def test_retirar_el_producto_del_catalogo_no_borra_lo_vendido(self):
        """`HU-26`: retirar es un estado, no un borrado. La línea sigue diciendo
        qué se vendió y a qué precio."""
        self.empanada.activo = False
        self.empanada.save(update_fields=["activo"])

        linea = LineaVenta.objects.get(venta=self.venta)

        self.assertEqual(linea.precio_unitario, Decimal("3500.00"))
        self.assertEqual(linea.energia_kcal, 210)

    def test_el_nombre_se_lee_del_producto_y_eso_es_deliberado(self):
        """No se copia: `ALC-IN-20` habla de la información nutricional, y la
        clave ajena va con `PROTECT`, así que el nombre siempre se puede leer.

        Esta prueba documenta la decisión en vez de dejarla implícita. Si algún
        día renombrar un producto hiciera ilegible un historial, hay que
        registrarlo como decisión y cambiar esto a propósito.
        """
        self.empanada.nombre = "Empanada de pollo"
        self.empanada.save(update_fields=["nombre"])

        linea = LineaVenta.objects.get(venta=self.venta)

        self.assertEqual(linea.producto.nombre, "Empanada de pollo")
        self.assertEqual(linea.precio_unitario, Decimal("3500.00"))
