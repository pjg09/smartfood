"""`TT-138`, `TT-139`, `TT-140`. Registro de merma con motivo (`HU-28`, `INV-8`).

Los dos criterios de `HU-28`:

1. **El motivo es obligatorio**: sin él la disminución no se registra.
2. **Aplica a toda disminución manual**, no solo a la merma.

El primero se comprueba en las tres capas por las que puede pasar, y lo que
importa es que la de abajo rechaza sola: `ElMotivoLoImponeLaBaseTest` llama al
ORM **saltándose el formulario y el servicio**. Si esa clase pasa, `INV-8` está
donde `DT-5` dice que debe estar y no donde sea cómodo.

El segundo no se puede comprobar sobre disminuciones manuales que no existen:
hoy la merma es la única. `ElSegundoCriterioSeVigilaTest` lo convierte en algo
que falla si deja de ser cierto — el día que alguien añada un cuarto tipo de
movimiento, esa prueba le recuerda que la restricción también es suya.

**`TST-4` no está aquí.** Es de `HU-29` y lo ejercita `TT-142`, que necesita
además la vista del historial de `TT-141`.
"""

from decimal import Decimal

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from inventario.models import (
    Merma,
    MovimientoInventario,
    TipoDeMovimientoDeInventario,
)
from inventario.selectors import existencias_de, historial_de
from inventario.services import ingresar_mercancia, registrar_merma

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


class ElMotivoLoImponeLaBaseTest(TestCase):
    """**`TT-140`. La prueba que decide si `INV-8` está bien puesta.**

    Escribe con `MovimientoInventario.objects.create`: sin formulario, sin
    `MermaForm`, sin `registrar_merma` y sin `asentar`. Lo único que queda entre
    la llamada y la tabla es la `CheckConstraint`.

    Si estas pruebas pasaran validando en el servicio, pasarían igual el día que
    alguien escriba un segundo camino de escritura y se olvide de validar. Por
    eso `DT-5`: la invariante que la base pueda imponer, la impone la base.
    """

    def setUp(self):
        self.producto = producto()

    def _no_deja(self, **campos):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MovimientoInventario.objects.create(producto=self.producto, **campos)

    def test_una_merma_sin_motivo_la_rechaza_la_base(self):
        self._no_deja(tipo=TipoDeMovimientoDeInventario.MERMA, cantidad=-3, motivo="")

    def test_una_merma_con_el_motivo_en_blanco_tambien(self):
        """Tres espacios no son la cadena vacía, y tampoco son un motivo.

        Es el caso que la primera redacción de la restricción dejaba pasar. El
        servicio nunca lo escribe —`asentar` hace `strip()`—, que es justamente
        la razón por la que tiene que rechazarlo la base: aquí se prueban los
        caminos que el servicio no controla.
        """
        self._no_deja(
            tipo=TipoDeMovimientoDeInventario.MERMA, cantidad=-3, motivo="   "
        )

    def test_una_merma_con_motivo_si_entra(self):
        MovimientoInventario.objects.create(
            producto=self.producto,
            tipo=TipoDeMovimientoDeInventario.MERMA,
            cantidad=-3,
            motivo="Se cayó la bandeja",
        )

        self.assertEqual(existencias_de(self.producto), -3)

    def test_el_ingreso_no_necesita_motivo(self):
        """`INV-8` es sobre las disminuciones. Un ingreso sin motivo es legítimo."""
        MovimientoInventario.objects.create(
            producto=self.producto,
            tipo=TipoDeMovimientoDeInventario.INGRESO,
            cantidad=10,
            motivo="",
        )

        self.assertEqual(existencias_de(self.producto), 10)


class ElSegundoCriterioSeVigilaTest(TestCase):
    """«Aplica a **toda** disminución manual, no solo a la merma» (`HU-28`).

    Hoy la merma es la única disminución manual que existe, así que el criterio
    se cumple por construcción y no hay nada más que probar. Lo que sí se puede
    es **dejar puesto el aviso**: si alguien añade un cuarto tipo de movimiento,
    esto falla y le dice que `INV-8` también va con él.

    Es una prueba que exige una ausencia, del tipo que pasa sola el día que deja
    de proteger. Por eso mira la lista de tipos y no la restricción.
    """

    def test_los_tipos_de_movimiento_siguen_siendo_tres(self):
        self.assertEqual(
            set(TipoDeMovimientoDeInventario.values),
            {"ingreso", "venta", "merma"},
            "Hay un tipo de movimiento nuevo. Si resta y es manual, INV-8 exige "
            "que lleve motivo: extiende la CheckConstraint de "
            "`movimiento_inventario_merma_con_motivo` antes de tocar esta prueba.",
        )

    def test_la_unica_disminucion_manual_es_la_merma(self):
        """La venta resta, pero no es manual: la explica la venta que la origina.

        Se comprueba contra la restricción que lo dice —la salida por venta
        señala su venta—, no contra una lista escrita aquí que podría quedarse
        vieja sin que nada avise.
        """
        nombres = {
            restriccion.name
            for restriccion in MovimientoInventario._meta.constraints
        }

        self.assertIn("movimiento_inventario_de_venta_con_su_venta", nombres)
        self.assertIn("movimiento_inventario_merma_con_motivo", nombres)


class LaMermaEsDeLaAdministracionTest(TestCase):
    """`[S11]`: «gestionar catálogo, precios e inventario» es de `USR-4`."""

    def setUp(self):
        self.producto = producto()
        self.administracion = usuario_con_rol(Rol.ADMINISTRADOR, "admin@example.com")
        ingresar_mercancia(
            actor=self.administracion, producto=self.producto, cantidad=20
        )

    def test_la_administracion_registra_la_merma(self):
        movimiento = registrar_merma(
            actor=self.administracion,
            producto=self.producto,
            cantidad=3,
            motivo="Se cayó la bandeja",
        )

        self.assertEqual(movimiento.tipo, TipoDeMovimientoDeInventario.MERMA)
        self.assertEqual(existencias_de(self.producto), 17)

    def test_la_cantidad_entra_positiva_y_se_asienta_negativa(self):
        """El signo lo pone el servicio, no quien registra.

        Si lo pusiera quien registra, un «3» donde iba «-3» **sumaría**
        existencias que nadie ingresó, y el libro lo aceptaría como un ingreso
        cualquiera.
        """
        movimiento = registrar_merma(
            actor=self.administracion,
            producto=self.producto,
            cantidad=3,
            motivo="Caducadas",
        )

        self.assertEqual(movimiento.cantidad, -3)

    def test_ningun_otro_rol_registra_mermas(self):
        for rol, email in [
            (Rol.CAJERO, "cajero@example.com"),
            (Rol.INSTITUCION, "institucion@example.com"),
            (Rol.ACUDIENTE, "acudiente@example.com"),
        ]:
            with self.subTest(rol=rol):
                with self.assertRaises(PermissionDenied):
                    registrar_merma(
                        actor=usuario_con_rol(rol, email),
                        producto=self.producto,
                        cantidad=1,
                        motivo="Rotura",
                    )

        self.assertEqual(existencias_de(self.producto), 20)

    def test_una_cuenta_desactivada_no_registra_mermas(self):
        self.administracion.is_active = False
        self.administracion.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            registrar_merma(
                actor=self.administracion,
                producto=self.producto,
                cantidad=1,
                motivo="Rotura",
            )

    def test_un_anonimo_tampoco(self):
        with self.assertRaises(PermissionDenied):
            registrar_merma(
                actor=None, producto=self.producto, cantidad=1, motivo="Rotura"
            )


class ElServicioAplicaSusReglasTest(TestCase):
    """`TT-138`. Lo que `registrar_merma` comprueba antes de asentar."""

    def setUp(self):
        self.producto = producto()
        self.administracion = usuario_con_rol(Rol.ADMINISTRADOR, "admin2@example.com")
        ingresar_mercancia(
            actor=self.administracion, producto=self.producto, cantidad=5
        )

    def _rechaza(self, **argumentos):
        with self.assertRaises(ValidationError):
            registrar_merma(actor=self.administracion, producto=self.producto, **argumentos)

    def test_sin_motivo_no_se_registra(self):
        """Primer criterio de `HU-28`, en la capa del servicio."""
        self._rechaza(cantidad=1, motivo="")

    def test_con_el_motivo_en_blanco_tampoco(self):
        self._rechaza(cantidad=1, motivo="   ")

    def test_una_merma_de_cero_o_negativa_no_es_una_merma(self):
        self._rechaza(cantidad=0, motivo="Rotura")
        self._rechaza(cantidad=-3, motivo="Rotura")

    def test_no_deja_las_existencias_en_negativo(self):
        """Mermar diez de las cinco que hay dejaría el inventario en −5.

        `INV-3` seguiría cumpliéndose —la suma explica el número— y lo que
        explicaría sería un disparate. Es el mismo razonamiento con el que la
        venta rechaza por existencias insuficientes (`[S4]` de
        `docs/reglas-de-la-venta.md`).
        """
        self._rechaza(cantidad=10, motivo="Se dañó la nevera")

        self.assertEqual(existencias_de(self.producto), 5)

    def test_mermar_todo_lo_que_hay_si_se_puede(self):
        """El límite es dejar negativo, no dejar en cero."""
        registrar_merma(
            actor=self.administracion,
            producto=self.producto,
            cantidad=5,
            motivo="Se dañó la nevera",
        )

        self.assertEqual(existencias_de(self.producto), 0)

    def test_un_rechazo_no_escribe_nada(self):
        self._rechaza(cantidad=10, motivo="Se dañó la nevera")

        self.assertEqual(
            MovimientoInventario.objects.filter(
                tipo=TipoDeMovimientoDeInventario.MERMA
            ).count(),
            0,
        )

    def test_un_producto_retirado_del_catalogo_tambien_se_merma(self):
        """`activo=False` impide venderlo (`HU-26`), no impide que se dañe.

        Lo que queda en la estantería de un producto retirado sigue siendo
        existencias, y si se rompe hay que poder darlo de baja con su motivo.
        """
        self.producto.activo = False
        self.producto.save(update_fields=["activo"])

        registrar_merma(
            actor=self.administracion,
            producto=self.producto,
            cantidad=2,
            motivo="Caducadas",
        )

        self.assertEqual(existencias_de(self.producto), 3)

    def test_el_motivo_queda_en_el_historial(self):
        """`INV-3`: las existencias se explican desde el historial, y explicar
        exige que el motivo esté ahí y no solo en el formulario."""
        registrar_merma(
            actor=self.administracion,
            producto=self.producto,
            cantidad=2,
            motivo="  Se cayó la bandeja  ",
        )

        ultimo = historial_de(self.producto)[0]
        self.assertEqual(ultimo.motivo, "Se cayó la bandeja")


class SeValidaDentroDelBloqueoTest(TestCase):
    """`DT-6`, el mismo patrón que `registrar_venta`.

    **`connection.in_atomic_block` no sirve como prueba**: bajo `TestCase`
    siempre es `True`, porque cada prueba va envuelta en una transacción. Lo que
    fija «se leyó dentro del bloqueo» es el **orden de las consultas**: el
    `SELECT … FOR UPDATE` sobre el producto antes de la suma que decide.

    Sin ese orden, dos mermas simultáneas de tres unidades sobre un producto que
    tiene cinco leerían las dos «cinco» y pasarían las dos.
    """

    def setUp(self):
        self.producto = producto()
        self.administracion = usuario_con_rol(Rol.ADMINISTRADOR, "admin4@example.com")
        ingresar_mercancia(
            actor=self.administracion, producto=self.producto, cantidad=10
        )

    def test_el_bloqueo_va_antes_de_leer_las_existencias(self):
        with CaptureQueriesContext(connection) as consultas:
            registrar_merma(
                actor=self.administracion,
                producto=self.producto,
                cantidad=2,
                motivo="Rotura",
            )

        sentencias = [c["sql"] for c in consultas.captured_queries]

        bloqueo = next(
            (i for i, sql in enumerate(sentencias) if "FOR UPDATE" in sql.upper()),
            None,
        )
        self.assertIsNotNone(bloqueo, "No se emitió ningún SELECT ... FOR UPDATE.")

        suma = next(
            (
                i
                for i, sql in enumerate(sentencias)
                if "SUM(" in sql.upper() and "INVENTARIO_MOVIMIENTOINVENTARIO" in sql.upper()
            ),
            None,
        )
        self.assertIsNotNone(suma, "No se leyeron las existencias.")
        self.assertLess(
            bloqueo,
            suma,
            "Las existencias se leyeron ANTES del bloqueo: la cifra puede cambiar "
            "debajo y la comprobación no vale (DT-6).",
        )


class LaInterfazAdministrativaTest(TestCase):
    """`TT-139`. `INT-3` es el admin (`DT-2`), y el admin es una vista (`DT-15`)."""

    def setUp(self):
        # Por el camino real: `crear_cuenta` asigna el grupo del rol y los
        # permisos van al grupo (`TT-15`). Poner `is_staff` a mano dejaría una
        # cuenta que entra al admin sin ningún permiso.
        sincronizar_grupos_y_permisos()
        self.administracion = crear_cuenta(
            email="admin5@example.com",
            rol=Rol.ADMINISTRADOR,
            nombre="Administración de la cafetería",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.producto = producto()
        ingresar_mercancia(
            actor=self.administracion, producto=self.producto, cantidad=20
        )
        self.client.force_login(self.administracion)

    def test_alcanza_el_listado_de_mermas(self):
        respuesta = self.client.get(reverse("admin:inventario_merma_changelist"))

        self.assertEqual(respuesta.status_code, 200)

    def test_registra_una_merma_desde_el_formulario(self):
        """De extremo a extremo: el admin delega en el servicio (`DT-15`)."""
        respuesta = self.client.post(
            reverse("admin:inventario_merma_add"),
            {
                "producto": str(self.producto.pk),
                "cantidad": "3",
                "motivo": "Se cayó la bandeja",
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(existencias_de(self.producto), 17)

        movimiento = MovimientoInventario.objects.get(
            tipo=TipoDeMovimientoDeInventario.MERMA
        )
        self.assertEqual(movimiento.cantidad, -3)
        self.assertEqual(movimiento.motivo, "Se cayó la bandeja")

    def test_el_formulario_exige_el_motivo(self):
        """Primer criterio de `HU-28`, en la capa de arriba.

        Se afirma sobre el efecto —no se escribió nada— y no sobre el texto del
        error, que cambia con la redacción de Django.
        """
        respuesta = self.client.post(
            reverse("admin:inventario_merma_add"),
            {"producto": str(self.producto.pk), "cantidad": "3", "motivo": ""},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(
            MovimientoInventario.objects.filter(
                tipo=TipoDeMovimientoDeInventario.MERMA
            ).exists()
        )
        self.assertEqual(existencias_de(self.producto), 20)

    def test_el_formulario_no_ofrece_elegir_el_tipo(self):
        """La entrada se llama «merma» y solo asienta mermas.

        Un selector de tipo aquí dejaría descontar existencias como venta sin
        que hubiera venta, que es lo que `INV-3` no admite.
        """
        cuerpo = self.client.get(
            reverse("admin:inventario_merma_add")
        ).content.decode()

        self.assertNotIn('name="tipo"', cuerpo)

    def test_el_formulario_no_acepta_cantidades_negativas(self):
        respuesta = self.client.post(
            reverse("admin:inventario_merma_add"),
            {"producto": str(self.producto.pk), "cantidad": "-3", "motivo": "Rotura"},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(existencias_de(self.producto), 20)

    def test_el_listado_de_mermas_no_enseña_los_ingresos(self):
        """Un proxy comparte la tabla con su modelo base.

        Sin el filtro de `get_queryset`, la entrada «Mermas» listaría el libro
        entero y la cifra de cada fila sería la de un movimiento cualquiera.
        """
        registrar_merma(
            actor=self.administracion,
            producto=self.producto,
            cantidad=3,
            motivo="Caducadas",
        )

        respuesta = self.client.get(reverse("admin:inventario_merma_changelist"))
        listadas = respuesta.context["cl"].queryset

        self.assertEqual(listadas.count(), 1)
        self.assertEqual(listadas.get().tipo, TipoDeMovimientoDeInventario.MERMA)

    def test_una_merma_registrada_no_se_edita_ni_se_borra(self):
        """`INV-3`: un asiento no se reescribe.

        Los permisos `change_merma` y `delete_merma` **no existen**
        (`default_permissions`), así que no hay nada que conceder por error.
        """
        permisos = set(
            Permission.objects.filter(
                content_type__app_label="inventario", content_type__model="merma"
            ).values_list("codename", flat=True)
        )

        self.assertEqual(permisos, {"add_merma", "view_merma"})

    def test_el_cajero_no_alcanza_las_mermas(self):
        cajero = crear_cuenta(
            email="cajero2@example.com",
            rol=Rol.CAJERO,
            nombre="Cajero",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.client.force_login(cajero)

        respuesta = self.client.get(reverse("admin:inventario_merma_changelist"))

        self.assertIn(respuesta.status_code, [302, 403])
