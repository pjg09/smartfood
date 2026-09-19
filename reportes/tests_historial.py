"""`TT-155`, `TT-156`. El historial de consumo del acudiente (`HU-30`).

El primer criterio de la historia —«el historial muestra cada venta con la
información nutricional registrada en ese momento»— es el único de todo el
proyecto que **puede romperse sin que nada falle**: sustituir un campo de la
línea por el del producto devuelve cifras perfectamente formadas, solo que del
catálogo de hoy. Por eso la prueba a la que hay que mirar cuando esto se rompa
es `test_editar_el_producto_no_cambia_el_historial`, y su gemela sobre la
plantilla, `test_la_pantalla_enseña_el_precio_de_entonces`.

El segundo criterio —quién puede ver qué— está en `tests_acceso.py` (`TT-157`).
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from reportes.selectors import historial_de_consumo
from ventas.models import EstadoDelPedido, MedioDePago
from ventas.services import registrar_venta, reservar, total_de


def producto(nombre="Empanada de carne", precio="3500", existencias=40, **nutrientes):
    """Un producto del catálogo con su ficha nutricional y sus existencias.

    Los valores son **por porción vendible** (`[S2.1]` de
    `docs/campos-nutricionales.md`), como los declara la cafetería.
    """
    declarado = {
        "porcion": "unidad de 80 g",
        "energia_kcal": 210,
        "proteinas_g": Decimal("6.50"),
        "carbohidratos_g": Decimal("22.00"),
        "azucares_g": Decimal("1.20"),
        "grasas_totales_g": Decimal("11.00"),
        "grasas_saturadas_g": Decimal("4.30"),
        "sodio_mg": 340,
    }
    declarado.update(nutrientes)

    categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
    articulo = Producto.objects.create(
        nombre=nombre, precio=Decimal(precio), categoria=categoria, **declarado
    )
    MovimientoInventario.objects.create(
        producto=articulo,
        tipo=TipoDeMovimientoDeInventario.INGRESO,
        cantidad=existencias,
        motivo="Ingreso de prueba",
    )
    return articulo


def familia(sufijo="", estudiantes=("Ana Sofía Restrepo Ruiz",)):
    """Un acudiente con los estudiantes que se le pidan, y saldo para comprar."""
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente{sufijo}@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
    )
    ficha = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"4310012{sufijo or '345'}"
    )
    matriculados = []
    for numero, nombre in enumerate(estudiantes):
        estudiante = Estudiante.objects.create(
            nombre=nombre,
            documento=f"100123450{numero}{sufijo}",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        recargar(actor=usuario, estudiante=estudiante, monto=Decimal("100000"))
        matriculados.append(estudiante)
    return usuario, matriculados


class BaseDelHistorial(TestCase):
    """Una familia, un cajero y una empanada en el catálogo."""

    def setUp(self):
        self.cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, nombre="Cajero"
        )
        self.acudiente, (self.estudiante,) = familia()
        self.empanada = producto()

    def vender(self, cantidad=2, articulo=None):
        return registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante,
            lineas={(articulo or self.empanada).id: cantidad},
        )

    def historial(self):
        return historial_de_consumo(actor=self.acudiente, estudiante=self.estudiante)


class ElHistorialTraeLasComprasDelEstudianteTest(BaseDelHistorial):
    """`HU-30`, primer criterio, por el lado de qué entra en el historial."""

    def test_cada_venta_es_una_entrada_del_historial(self):
        self.vender()
        self.vender(cantidad=1, articulo=producto(nombre="Jugo de mora", precio="2500"))

        self.assertEqual(self.historial().count(), 2)

    def test_lo_mas_reciente_va_primero(self):
        primera = self.vender()
        segunda = self.vender(cantidad=1, articulo=producto(nombre="Arepa", precio="2000"))

        self.assertEqual(
            [compra.id for compra in self.historial()], [segunda.id, primera.id]
        )

    def test_un_estudiante_sin_compras_tiene_historial_vacio(self):
        """Vacío, no un error: todavía no ha comprado nada."""
        self.assertEqual(self.historial().count(), 0)

    def test_las_ventas_a_cliente_generico_no_son_historial_de_nadie(self):
        """`DEC-1`, `HU-53`. Sin estudiante no hay a quién atribuirlas.

        No hace falta excluirlas: el filtro por estudiante no las alcanza. La
        prueba fija que siga siendo así, que es lo que impide que la compra de
        un docente aparezca en el historial de un menor.
        """
        registrar_venta(
            actor=self.cajero,
            lineas={self.empanada.id: 1},
            medio_pago=MedioDePago.EFECTIVO,
        )

        self.assertEqual(self.historial().count(), 0)

    def test_no_se_cuela_la_compra_de_un_hermano(self):
        """El segundo criterio, en la capa de datos y no en la pantalla.

        Los dos estudiantes son del mismo acudiente, así que el rol no distingue:
        lo único que separa un historial del otro es el filtro.
        """
        acudiente, (ana, tomas) = familia(
            sufijo="2", estudiantes=("Ana Restrepo", "Tomás Restrepo")
        )
        registrar_venta(actor=self.cajero, estudiante=tomas, lineas={self.empanada.id: 1})

        de_ana = historial_de_consumo(actor=acudiente, estudiante=ana)

        self.assertEqual(de_ana.count(), 0)


class ElHistorialLeeLaInstantaneaTest(BaseDelHistorial):
    """`HU-30` primer criterio, `HU-22`, `DT-8`. **La prueba que importa.**"""

    def test_trae_los_nutrientes_congelados_en_la_linea(self):
        self.vender()

        linea = self.historial().get().lineas.get()

        self.assertEqual(linea.energia_kcal, 210)
        self.assertEqual(linea.sodio_mg, 340)
        self.assertEqual(linea.precio_unitario, Decimal("3500.00"))

    def test_editar_el_producto_no_cambia_el_historial(self):
        """Subir el precio o corregir la ficha **no reescribe el pasado**.

        Si esta prueba falla, alguien cambió la instantánea por una referencia al
        producto y el historial dejó de ser un historial: pasó a ser una
        proyección del catálogo de hoy sobre lo que un niño comió el mes pasado.
        """
        self.vender()

        self.empanada.precio = Decimal("4200")
        self.empanada.energia_kcal = 900
        self.empanada.save(update_fields=["precio", "energia_kcal"])

        linea = self.historial().get().lineas.get()
        self.assertEqual(linea.precio_unitario, Decimal("3500.00"))
        self.assertEqual(linea.energia_kcal, 210)

    def test_un_nutriente_sin_declarar_no_se_convierte_en_cero(self):
        """`TT-44`, `[S2.2]`. Vacío es «no declarado», y cero es una afirmación."""
        self.vender(articulo=producto(nombre="Galleta", precio="1500", sodio_mg=None))

        linea = self.historial().first().lineas.get()

        self.assertIsNone(linea.sodio_mg)

    def test_una_linea_sin_ningun_nutriente_se_declara_como_hueco(self):
        sin_ficha = producto(
            nombre="Sándwich de la casa",
            precio="6000",
            energia_kcal=None,
            proteinas_g=None,
            carbohidratos_g=None,
            azucares_g=None,
            grasas_totales_g=None,
            grasas_saturadas_g=None,
            sodio_mg=None,
        )
        self.vender(articulo=sin_ficha)

        linea = self.historial().first().lineas.get()

        self.assertFalse(linea.declara_informacion_nutricional)

    def test_la_porcion_sola_no_es_informacion_nutricional(self):
        """Contraprueba de la anterior: `porcion` es texto, no una cifra.

        Sin ella, `declara_informacion_nutricional` pasaría sola en cuanto un
        producto tuviera escrito «paquete de 30 g» y ningún nutriente.
        """
        self.vender()

        self.assertTrue(self.historial().first().lineas.get().declara_informacion_nutricional)


class LosTotalesSalenDeLaInstantaneaTest(BaseDelHistorial):
    """El total anotado y `total_de` son la misma suma, y tienen que seguir siéndolo."""

    def test_el_total_anotado_coincide_con_el_de_las_lineas(self):
        """Ata la anotación SQL a `ventas.services.total_de`.

        Son dos formas de sumar lo mismo —precio congelado por unidades— y viven
        en sitios distintos: esta prueba es lo que impide que se separen sin que
        nadie se entere.
        """
        self.vender(cantidad=3)
        self.vender(cantidad=1, articulo=producto(nombre="Jugo", precio="2500"))

        for compra in self.historial():
            with self.subTest(compra=compra.id):
                self.assertEqual(compra.total, total_de(compra))

    def test_el_total_es_el_de_entonces_y_no_el_de_hoy(self):
        self.vender(cantidad=2)

        self.empanada.precio = Decimal("9900")
        self.empanada.save(update_fields=["precio"])

        self.assertEqual(self.historial().get().total, Decimal("7000.00"))

    def test_cuenta_las_unidades_de_la_compra(self):
        self.vender(cantidad=3)

        self.assertEqual(self.historial().get().unidades, 3)

    def test_una_compra_de_varios_renglones_suma_una_sola_vez(self):
        """**Dos agregados sobre la misma unión**, y el riesgo de que se crucen.

        `total` y `unidades` salen los dos de `lineas`. Con una sola línea por
        venta —que es lo que comprueban las demás— un error de multiplicación no
        se vería: uno por uno es uno. Aquí hay dos renglones, así que una unión
        mal planteada daría el doble en las dos cifras.
        """
        jugo = producto(nombre="Jugo de mora", precio="2800")

        registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 2, jugo.id: 1},
        )

        compra = self.historial().get()
        self.assertEqual(compra.total, Decimal("9800.00"))
        self.assertEqual(compra.unidades, 3)
        self.assertEqual(compra.total, total_de(compra))


class LasReservasEntranEnElHistorialTest(BaseDelHistorial):
    """`DT-32`. Una reserva **es** una venta: está pagada y ya salió de la billetera."""

    def test_una_reserva_pendiente_aparece(self):
        reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 1},
        )

        compra = self.historial().get()

        self.assertTrue(compra.es_reserva)
        self.assertEqual(compra.pedido_anticipado.estado, EstadoDelPedido.PENDIENTE)

    def test_la_pantalla_marca_la_reserva_sin_recoger(self):
        """Que esté pagada no significa que se la haya comido."""
        reservar(
            actor=self.acudiente,
            estudiante=self.estudiante,
            lineas={self.empanada.id: 1},
        )
        self.client.force_login(self.acudiente)

        respuesta = self.client.get(
            reverse("historial-de-consumo", args=[self.estudiante.id])
        )

        self.assertContains(respuesta, "data-reserva-pendiente")


class LaPantallaPintaLaInstantaneaTest(BaseDelHistorial):
    """La otra mitad de `DT-8`: **la plantilla también puede romperlo.**

    El selector puede traer la línea congelada y la plantilla pintar
    `{{ linea.producto.precio }}` de todas formas. Es un fallo que ninguna
    prueba sobre el selector caza, y en pantalla se ve perfectamente bien.
    """

    def setUp(self):
        super().setUp()
        self.vender(cantidad=2)
        self.client.force_login(self.acudiente)

    def pantalla(self):
        return self.client.get(
            reverse("historial-de-consumo", args=[self.estudiante.id])
        )

    def test_la_pantalla_enseña_el_precio_de_entonces(self):
        self.empanada.precio = Decimal("9900")
        self.empanada.save(update_fields=["precio"])

        respuesta = self.pantalla()

        self.assertContains(respuesta, "$3.500")
        self.assertNotContains(respuesta, "$9.900")

    def test_la_pantalla_enseña_los_nutrientes_de_entonces(self):
        self.empanada.energia_kcal = 901
        self.empanada.save(update_fields=["energia_kcal"])

        respuesta = self.pantalla()

        self.assertContains(respuesta, "210 kcal")
        self.assertNotContains(respuesta, "901 kcal")

    def test_la_pantalla_dice_que_un_producto_no_declaró_nada(self):
        """Un hueco se marca; una fila de ceros mentiría (`[S2.4]`)."""
        sin_ficha = producto(
            nombre="Sándwich de la casa",
            precio="6000",
            energia_kcal=None,
            proteinas_g=None,
            carbohidratos_g=None,
            azucares_g=None,
            grasas_totales_g=None,
            grasas_saturadas_g=None,
            sodio_mg=None,
        )
        self.vender(cantidad=1, articulo=sin_ficha)

        self.assertContains(self.pantalla(), "data-sin-informacion-nutricional")

    def test_un_producto_a_medio_declarar_no_se_trata_como_hueco(self):
        """Declarar **algo** no es declararlo todo, y son dos casos distintos.

        La ficha a medias enseña lo que hay y marca lo que falta renglón a
        renglón; el bloque de «no declaró nada» es para el producto sin ficha
        ninguna. Confundirlos escondería las cifras que sí existen.
        """
        a_medias = producto(
            nombre="Galleta integral",
            precio="1500",
            porcion="paquete de 30 g",
            energia_kcal=140,
            proteinas_g=Decimal("3.00"),
            carbohidratos_g=None,
            azucares_g=None,
            grasas_totales_g=None,
            grasas_saturadas_g=None,
            sodio_mg=None,
        )
        self.vender(cantidad=1, articulo=a_medias)

        respuesta = self.pantalla()

        self.assertContains(respuesta, "140 kcal")
        self.assertNotContains(respuesta, "data-sin-informacion-nutricional")

    def test_sin_compras_la_pantalla_lo_dice(self):
        acudiente, (estudiante,) = familia(sufijo="3", estudiantes=("Julián Ospina",))
        self.client.force_login(acudiente)

        respuesta = self.client.get(
            reverse("historial-de-consumo", args=[estudiante.id])
        )

        self.assertContains(respuesta, "data-sin-compras")
