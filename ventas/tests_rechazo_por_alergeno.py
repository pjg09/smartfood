"""`TT-115`. Venta rechazada por alérgeno bloqueado (`HU-18`, **`TST-1`**).

═══════════════════════════════════════════════════════════════════════════
**`TST-1` ES EL ESCENARIO QUE DA SENTIDO AL PROYECTO.** Un niño alérgico no
puede comprar lo que le hace daño, y el momento en que eso importa es la caja.
Es el primero de los cuatro escenarios críticos que `ENT-05` exige demostrar.
═══════════════════════════════════════════════════════════════════════════

Los tres criterios de `HU-18`:

1. **La validación ocurre en tiempo real, en el momento de la venta.** No sobre
   una lista calculada antes: se cruza la condición que el acudiente bloqueó con
   lo que cada producto declara, dentro del bloqueo de la transacción (`DT-6`).
   `ElCruceSeEvaluaAlCobrarTest` es la clase que lo demuestra, y es la que de
   verdad vigila `INV-5`: el producto se crea **después** del bloqueo.
2. **La venta se rechaza y el cajero no dispone de una vía para forzarla**
   (`INV-4`, primer criterio de `HU-13`). Se comprueba por las dos vías por las
   que alguien lo intentaría —el servicio y la pantalla— y comprobando que la
   restricción sigue en pie después de intentarlo.
3. **Es el escenario crítico `TST-1`.**

La diferencia con `HU-60` (`tests_producto_bloqueado.py`) no es de forma sino de
fondo: allí se rechaza **un producto identificado**; aquí, **cualquiera que
declare la condición**, lo hubiera o no en el catálogo cuando el acudiente la
bloqueó.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from billetera.selectors import saldo_de
from billetera.services import recargar
from catalogo.models import Alergeno, Categoria, Producto, ProductoAlergeno
from cuentas.models import Rol, Usuario
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from restricciones.models import RestriccionProducto
from restricciones.selectors import identificadores_de_alergenos_bloqueados
from restricciones.services import (
    bloquear_alergeno,
    bloquear_producto,
    desbloquear_alergeno,
)
from ventas.models import Venta
from ventas.services import (
    AlergenoBloqueado,
    ProductoBloqueado,
    SaldoInsuficiente,
    registrar_venta,
)

CLAVE = "clave-de-prueba-2026"


def escenario():
    """Un cajero, un acudiente con su hijo, y el catálogo con maní declarado."""
    cajero = Usuario.objects.crear_usuario(
        email="cajero-alg@example.com", rol=Rol.CAJERO, nombre="Cajero"
    )
    cajero.set_password(CLAVE)
    cajero.save(update_fields=["password"])

    acudiente = Usuario.objects.crear_usuario(
        email="acudiente-alg@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
    )
    ficha = Acudiente.objects.create(
        usuario=acudiente, nombre="Marta Ruiz Ochoa", documento="4310088888"
    )
    estudiante = Estudiante.objects.create(
        nombre="Ana Sofía Restrepo Ruiz",
        documento="1001288801",
        acudiente=ficha,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )

    mani = Alergeno.objects.create(nombre="Maní")
    lactosa = Alergeno.objects.create(nombre="Lactosa")
    categoria = Categoria.objects.create(nombre="Panadería")

    galleta = producto_con("Galleta de maní", "2500", categoria, [mani])
    empanada = producto_con("Empanada de carne", "3000", categoria, [])

    return cajero, acudiente, estudiante, mani, lactosa, categoria, galleta, empanada


def producto_con(nombre, precio, categoria, alergenos, existencias=50):
    """Un producto del catálogo, con sus alérgenos declarados y con existencias.

    Las declaraciones se escriben en `ProductoAlergeno`, que es **la** tabla del
    cruce (`DT-7`). No hay ninguna otra lista que actualizar, y esa ausencia es
    `INV-5`.
    """
    producto = Producto.objects.create(
        nombre=nombre, precio=Decimal(precio), categoria=categoria
    )
    for alergeno in alergenos:
        ProductoAlergeno.objects.create(producto=producto, alergeno=alergeno)
    MovimientoInventario.objects.create(
        producto=producto,
        tipo=TipoDeMovimientoDeInventario.INGRESO,
        cantidad=existencias,
        motivo="Ingreso de prueba",
    )
    return producto


class BaseDeVenta(TestCase):
    def setUp(self):
        (
            self.cajero,
            self.acudiente,
            self.estudiante,
            self.mani,
            self.lactosa,
            self.categoria,
            self.galleta,
            self.empanada,
        ) = escenario()
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000")
        )

    def vender(self, lineas, estudiante=None, **extra):
        return registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante if estudiante is None else estudiante,
            lineas=lineas,
            **extra,
        )

    def bloquear_el_mani(self):
        bloquear_alergeno(
            actor=self.acudiente, estudiante=self.estudiante, alergeno=self.mani
        )


# --- Criterio 1 y 2: se rechaza, y no se escribe nada ----------------------


class LaVentaConAlergenoBloqueadoSeRechazaTest(BaseDeVenta):
    """`TST-1` en su forma más directa."""

    def setUp(self):
        super().setUp()
        self.bloquear_el_mani()

    def test_se_rechaza_aunque_haya_saldo_de_sobra(self):
        """El caso contraintuitivo: nada de lo que se ve en la caja lo explica.

        Hay saldo, hay existencias y el producto está en el catálogo. Lo que lo
        rechaza no se ve en la fila: es una condición de salud que declaró el
        acudiente.
        """
        with self.assertRaises(AlergenoBloqueado):
            self.vender({self.galleta.id: 1})

    def test_no_se_descuenta_nada_ni_queda_venta(self):
        saldo_antes = saldo_de(self.estudiante)
        existencias_antes = existencias_de(self.galleta)

        with self.assertRaises(AlergenoBloqueado):
            self.vender({self.galleta.id: 1})

        self.assertEqual(saldo_de(self.estudiante), saldo_antes)
        self.assertEqual(existencias_de(self.galleta), existencias_antes)
        self.assertEqual(Venta.objects.count(), 0)

    def test_un_renglon_con_el_alergeno_tumba_la_venta_entera(self):
        """No se cobra «lo que sí se puede» por su cuenta.

        Cobrar el resto en silencio dejaría al estudiante creyendo que se llevó
        lo que pidió. El mensaje dice qué quitar; quitarlo lo decide quien está
        en la caja.
        """
        with self.assertRaises(AlergenoBloqueado):
            self.vender({self.galleta.id: 1, self.empanada.id: 2})

        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(existencias_de(self.empanada), 50)

    def test_lo_que_no_lo_declara_se_vende_con_normalidad(self):
        """El bloqueo es de la condición, no del catálogo entero."""
        self.assertIsNotNone(self.vender({self.empanada.id: 1}))

    def test_el_mensaje_dice_el_producto_y_el_alergeno(self):
        """«Por qué» es la mitad del mensaje: el cajero tiene que explicarlo."""
        with self.assertRaises(AlergenoBloqueado) as capturado:
            self.vender({self.galleta.id: 1})

        self.assertEqual(capturado.exception.productos, ("Galleta de maní",))
        self.assertEqual(capturado.exception.alergenos, ("Maní",))
        mensaje = " ".join(capturado.exception.messages)
        self.assertIn("Galleta de maní", mensaje)
        self.assertIn("Maní", mensaje)

    def test_solo_el_alergeno_bloqueado_rechaza(self):
        """Otro alérgeno declarado por el mismo producto no lo hace.

        Se declara lactosa en la galleta y **no** se bloquea: la venta se
        rechaza por maní, y si el maní se retira deja de rechazarse.
        """
        ProductoAlergeno.objects.create(producto=self.galleta, alergeno=self.lactosa)

        with self.assertRaises(AlergenoBloqueado) as capturado:
            self.vender({self.galleta.id: 1})
        self.assertEqual(capturado.exception.alergenos, ("Maní",))

        desbloquear_alergeno(
            actor=self.acudiente, estudiante=self.estudiante, alergeno=self.mani
        )
        self.assertIsNotNone(self.vender({self.galleta.id: 1}))


class ElBloqueoEsDeEseEstudianteTest(BaseDeVenta):
    def setUp(self):
        super().setUp()
        self.bloquear_el_mani()
        self.hermano = Estudiante.objects.create(
            nombre="Tomás Restrepo Ruiz",
            documento="1001288802",
            acudiente=self.estudiante.acudiente,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        recargar(actor=self.acudiente, estudiante=self.hermano, monto=Decimal("50000"))

    def test_al_hermano_sin_esa_alergia_si_se_le_vende(self):
        """Dos hijos del mismo acudiente, y la alergia es de uno."""
        self.assertIsNotNone(
            self.vender({self.galleta.id: 1}, estudiante=self.hermano)
        )

    def test_la_venta_a_cliente_generico_no_consulta_restricciones(self):
        """`DEC-1`, `HU-53`: sin estudiante no hay a quién consultarle nada."""
        venta = registrar_venta(
            actor=self.cajero,
            estudiante=None,
            lineas={self.galleta.id: 1},
            medio_pago="efectivo",
        )

        self.assertIsNone(venta.estudiante)


# --- Criterio 1: se evalúa al cobrar, no sobre una lista ------------------


class ElCruceSeEvaluaAlCobrarTest(BaseDeVenta):
    """**`INV-5` en la caja, y la clase que más importa de este fichero.**

    `TT-103` demostró que el bloqueo cubre productos futuros **en la consulta**.
    Esto lo demuestra donde tiene consecuencias: en el cobro. Si alguien
    materializara la lista de productos bloqueados por estudiante, todas las
    pruebas de arriba seguirían pasando —usan productos creados antes— y estas
    tres fallarían. Por eso existen.
    """

    def setUp(self):
        super().setUp()
        self.bloquear_el_mani()

    def test_un_producto_creado_despues_del_bloqueo_se_rechaza(self):
        """El caso que ninguna lista guardada puede acertar.

        La cafetería agrega un producto nuevo esta mañana; el bloqueo se puso
        ayer y nadie lo tocó. La caja lo rechaza esta tarde.
        """
        nuevo = producto_con("Torta de maní", "4000", self.categoria, [self.mani])

        with self.assertRaises(AlergenoBloqueado) as capturado:
            self.vender({nuevo.id: 1})

        self.assertEqual(capturado.exception.productos, ("Torta de maní",))

    def test_un_producto_que_declara_el_alergeno_despues_se_rechaza(self):
        """El producto ya existía y se vendía; hoy la cafetería corrige su ficha.

        Se vende primero —para que la venta haya ocurrido de verdad— y después
        se declara el alérgeno. La siguiente venta se rechaza sin tocar la
        restricción.
        """
        self.assertIsNotNone(self.vender({self.empanada.id: 1}))

        ProductoAlergeno.objects.create(producto=self.empanada, alergeno=self.mani)

        with self.assertRaises(AlergenoBloqueado):
            self.vender({self.empanada.id: 1})

    def test_retirar_la_declaracion_devuelve_la_venta_a_la_normalidad(self):
        """La simétrica: la verdad vive en `ProductoAlergeno`, en un solo sitio."""
        with self.assertRaises(AlergenoBloqueado):
            self.vender({self.galleta.id: 1})

        ProductoAlergeno.objects.filter(
            producto=self.galleta, alergeno=self.mani
        ).delete()

        self.assertIsNotNone(self.vender({self.galleta.id: 1}))

    def test_bloquear_el_alergeno_no_escribe_ninguna_restriccion_de_producto(self):
        """La comprobación que cuenta filas, como en `TT-103`.

        Si el bloqueo se resolviera materializando la lista, aquí habría una
        `RestriccionProducto` por cada producto con maní.
        """
        producto_con("Torta de maní", "4000", self.categoria, [self.mani])

        self.assertEqual(
            RestriccionProducto.objects.filter(estudiante=self.estudiante).count(), 0
        )


class SeValidaDespuesDeBloquearTest(BaseDeVenta):
    """Primer criterio: «en el momento de la venta», y `DT-6` precisa dónde.

    **Consultar las restricciones antes del bloqueo daría el mismo resultado en
    todas las pruebas de arriba.** Es la clase de error que
    `tests_concurrencia.py` existe para detectar en el saldo: el que pasa las
    pruebas secuenciales y falla con dos cajas a la vez.

    Aquí se fija mirando el orden real de las consultas: el `SELECT … FOR
    UPDATE` que toma el bloqueo tiene que haberse emitido **antes** de que se
    pregunte por los alérgenos.

    ── POR QUÉ NO SE COMPRUEBA CON `in_atomic_block` ───────────────────────
    Porque no comprobaría nada: `TestCase` envuelve cada prueba en una
    transacción, así que dentro de una prueba **siempre** hay uno abierto,
    valga lo que valga el servicio. Una prueba que no puede fallar es peor que
    no tenerla: ocupa el sitio de la que sí vigila.
    ─────────────────────────────────────────────────────────────────────────
    """

    def test_el_cruce_se_consulta_con_los_productos_ya_bloqueados(self):
        with CaptureQueriesContext(connection) as consultas:
            self.vender({self.empanada.id: 1})

        sentencias = [c["sql"] for c in consultas.captured_queries]
        bloqueo = next(
            (i for i, sql in enumerate(sentencias) if "FOR UPDATE" in sql.upper()), None
        )
        cruce = next(
            (
                i
                for i, sql in enumerate(sentencias)
                if "catalogo_productoalergeno" in sql.lower()
                and "restricciones_restriccionalergeno" in sql.lower()
            ),
            None,
        )

        self.assertIsNotNone(bloqueo, "la venta no tomó ningún bloqueo (DT-6)")
        self.assertIsNotNone(cruce, "la venta no consultó los alérgenos bloqueados")
        self.assertLess(
            bloqueo,
            cruce,
            "las restricciones se consultaron antes de bloquear: DT-6 pide "
            "bloquear, luego validar, luego escribir",
        )


# --- Criterio 2: el motivo se distingue, y nadie la fuerza ----------------


class ElMotivoSeDistingueTest(BaseDeVenta):
    """Cuatro motivos de rechazo, y el cajero tiene que poder decir cuál."""

    def test_cada_motivo_lleva_su_etiqueta(self):
        self.assertEqual(AlergenoBloqueado.motivo, "alergeno-bloqueado")
        self.assertEqual(
            len({AlergenoBloqueado.motivo, ProductoBloqueado.motivo, SaldoInsuficiente.motivo}),
            3,
        )

    def test_sin_saldo_y_con_alergeno_gana_el_alergeno(self):
        """El alérgeno no se arregla recargando, y el saldo sí.

        Contestar «no alcanza» mandaría al acudiente a recargar para que la
        venta volviera a rechazarse — y esta vez sin explicación nueva.
        """
        sin_saldo = Estudiante.objects.create(
            nombre="Sara Restrepo Ruiz",
            documento="1001288803",
            acudiente=self.estudiante.acudiente,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        bloquear_alergeno(actor=self.acudiente, estudiante=sin_saldo, alergeno=self.mani)

        with self.assertRaises(AlergenoBloqueado):
            self.vender({self.galleta.id: 1}, estudiante=sin_saldo)

        # Y sin el alérgeno de por medio, el mismo carrito da el otro motivo.
        with self.assertRaises(SaldoInsuficiente):
            self.vender({self.empanada.id: 1}, estudiante=sin_saldo)

    def test_si_cae_por_las_dos_razones_se_nombra_la_alergia(self):
        """Un producto en la lista de `HU-10` que además declara el alérgeno.

        Se responde `HU-18`. «Lo bloqueó tu acudiente» invita a pedirle al
        acudiente que lo quite, y con una alergia esa conversación no puede
        empezar en la caja.
        """
        self.bloquear_el_mani()
        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.galleta
        )

        with self.assertRaises(AlergenoBloqueado):
            self.vender({self.galleta.id: 1})


class ElCajeroNoPuedeForzarlaTest(BaseDeVenta):
    """Segundo criterio: `INV-4` y el primer criterio de `HU-13`.

    Es el que da sentido al resto: una protección que la caja puede descartar no
    protege, solo informa.
    """

    def setUp(self):
        super().setUp()
        self.bloquear_el_mani()

    def test_el_servicio_no_admite_ningun_argumento_que_la_salte(self):
        """No hay `forzar=True`, y que no lo haya es la garantía.

        Si algún día aparece uno, esta prueba falla al pasarlo: el servicio
        rechaza el argumento desconocido. Es una forma de vigilar una ausencia.
        """
        with self.assertRaises(TypeError):
            self.vender({self.galleta.id: 1}, forzar=True)

    def test_el_cajero_no_puede_desbloquear_para_luego_cobrar(self):
        with self.assertRaises(PermissionDenied):
            desbloquear_alergeno(
                actor=self.cajero, estudiante=self.estudiante, alergeno=self.mani
            )

        self.assertIn(
            self.mani.id, identificadores_de_alergenos_bloqueados(self.estudiante)
        )
        with self.assertRaises(AlergenoBloqueado):
            self.vender({self.galleta.id: 1})

    def test_el_cajero_no_puede_quitarle_el_alergeno_al_producto(self):
        """El otro camino, y es el propio de esta historia.

        La declaración del producto es del catálogo, y el catálogo es de la
        administración de la cafetería (`[S11]`): el cajero no llega a ella ni
        por el admin —no entra— ni por el servicio, que exige el rol.
        """
        from catalogo.services import declarar_alergenos

        with self.assertRaises(PermissionDenied):
            declarar_alergenos(actor=self.cajero, producto=self.galleta, alergenos=[])

        with self.assertRaises(AlergenoBloqueado):
            self.vender({self.galleta.id: 1})

    def test_reintentar_el_cobro_da_el_mismo_rechazo(self):
        """No es un aviso descartable: insistir no la vence."""
        for intento in range(3):
            with self.subTest(intento=intento):
                with self.assertRaises(AlergenoBloqueado):
                    self.vender({self.galleta.id: 1})


class LoQueElCajeroVeTest(BaseDeVenta):
    """`TT-114`. El motivo, en la pantalla y por el camino real del cajero."""

    def setUp(self):
        super().setUp()
        self.bloquear_el_mani()
        self.client.force_login(self.cajero)

    def _montar_y_cobrar(self, producto=None):
        """Escanear, añadir al carrito y cobrar, por HTTP.

        No se llama al servicio porque lo que se comprueba aquí es **lo que el
        cajero ve**.
        """
        self.client.get(
            reverse("identificacion-en-el-punto-de-venta"),
            {"codigo": self.estudiante.codigo_tarjeta},
        )
        self.client.post(
            reverse("carrito-del-punto-de-venta"),
            {"producto": str((producto or self.galleta).id), "accion": "anadir"},
        )
        return self.client.post(reverse("cobrar"))

    def test_el_ticket_marca_el_motivo_con_su_etiqueta(self):
        """Se busca `data-motivo`, no una frase: el texto cambia, la etiqueta no."""
        respuesta = self._montar_y_cobrar()

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'data-motivo="alergeno-bloqueado"')

    def test_el_ticket_nombra_el_alergeno_y_no_cobra(self):
        respuesta = self._montar_y_cobrar()

        self.assertContains(respuesta, "Maní")
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(saldo_de(self.estudiante), Decimal("50000.00"))

    def test_el_carrito_se_queda_montado_para_poder_corregirlo(self):
        """No se ha escrito nada, así que quitar el renglón es todo lo que falta."""
        respuesta = self._montar_y_cobrar()

        self.assertContains(respuesta, "data-linea-de-venta")

    def test_la_pantalla_no_ofrece_ninguna_accion_para_forzar(self):
        """Lo que lo garantiza no es que no haya botón —es que no hay servicio
        que lo admita (`INV-4`)—; esto comprueba que tampoco se ofrece."""
        respuesta = self._montar_y_cobrar()
        cuerpo = respuesta.content.decode()

        for palabra in ["forzar", "omitir", "autorizar", "continuar de todos modos"]:
            with self.subTest(palabra=palabra):
                self.assertNotIn(palabra, cuerpo.lower())

    def test_y_lo_que_no_lo_declara_se_cobra_igual(self):
        """El contraste. Sin esto, la prueba de arriba pasaría con una caja que
        rechazara siempre."""
        respuesta = self._montar_y_cobrar(producto=self.empanada)

        self.assertNotContains(respuesta, 'data-motivo="alergeno-bloqueado"')
        self.assertEqual(Venta.objects.count(), 1)
