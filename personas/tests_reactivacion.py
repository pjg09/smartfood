"""`TT-123` y `TT-124`. Reactivación exclusiva de la institución (`HU-49`, `INVD-3`).

Los dos criterios de `HU-49`:

1. **Solo la institución reactiva, con independencia de quién haya desactivado.**
   `ConIndependenciaDeQuienDesactivoTest` es la clase que lo ejercita con las dos
   procedencias, y es la que de verdad prueba la historia: que la institución
   pueda deshacer lo suyo no sorprende a nadie; que el acudiente **no pueda
   deshacer lo suyo** es el caso que cuesta aceptar al leerlo, y es el que
   sostiene la invariante.
2. **El acudiente que desactivó debe comunicarse con la institución.** En el
   sistema eso es una ausencia —ni servicio, ni ruta, ni botón— y una frase: la
   ficha le dice a quién pedírselo (`PR-11`).

**Por qué la asimetría, que es lo único que hay que entender aquí.** Bloquear lo
puede pedir cualquiera de los dos (`DEC-5`); desbloquear pasa por una
**verificación presencial**. Es lo que impide que quien encontró la tarjeta
consiga que se reactive: por teléfono podría convencer al acudiente —«soy del
colegio, ya apareció»—; en el mostrador tiene que aparecer el estudiante.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, EstadoDelEstudiante, Estudiante
from personas.services import dar_de_baja, desactivar, reactivar
from ventas.services import registrar_venta

CLAVE = "clave-de-prueba-2026"
REACTIVAR = "reactivacion-de-estudiante"
DESACTIVAR_PADRON = "desactivacion-de-estudiante"
DESACTIVAR_ACUDIENTE = "desactivacion-por-el-acudiente"


class BaseDeReactivacion(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()

        self.institucion = crear_cuenta(
            email="institucion-react@example.com",
            rol=Rol.INSTITUCION,
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.cajero = crear_cuenta(
            email="cajero-react@example.com", rol=Rol.CAJERO, enviar_invitacion=False
        )
        self.administracion = crear_cuenta(
            email="administracion-react@example.com",
            rol=Rol.ADMINISTRADOR,
            enviar_invitacion=False,
        )

        self.acudiente = Usuario.objects.crear_usuario(
            email="acudiente-react@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
        )
        ficha = Acudiente.objects.create(
            usuario=self.acudiente, nombre="Marta Ruiz Ochoa", documento="4310044444"
        )
        self.estudiante = Estudiante.objects.create(
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001244401",
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

    def estado_de(self, estudiante=None):
        estudiante = estudiante or self.estudiante
        estudiante.refresh_from_db()
        return estudiante.estado


# --- Criterio 1: solo la institución, venga de donde venga ----------------


class ConIndependenciaDeQuienDesactivoTest(BaseDeReactivacion):
    """**La clase que prueba la historia.** `TT-124`, `INVD-3`."""

    def test_el_acudiente_que_desactivo_no_puede_reactivar(self):
        """El caso que da sentido a la invariante.

        Lo desactivó él, es su hijo, y aun así el desbloqueo no es suyo: pasa por
        el mostrador. Sin esto, a quien encontró la tarjeta le bastaría con
        convencer al acudiente por teléfono.
        """
        desactivar(actor=self.acudiente, estudiante=self.estudiante)

        with self.assertRaises(PermissionDenied):
            reactivar(actor=self.acudiente, estudiante=self.estudiante)

        self.assertEqual(self.estado_de(), EstadoDelEstudiante.DESACTIVADO)

    def test_y_la_institucion_sí_reactiva_lo_que_desactivó_el_acudiente(self):
        """«Con independencia de quién» en su forma útil: no hace falta que lo
        haya desactivado ella."""
        desactivar(actor=self.acudiente, estudiante=self.estudiante)

        reactivar(actor=self.institucion, estudiante=self.estudiante)

        self.assertEqual(self.estado_de(), EstadoDelEstudiante.ACTIVO)

    def test_tambien_reactiva_lo_que_desactivó_ella_misma(self):
        desactivar(actor=self.institucion, estudiante=self.estudiante)

        reactivar(actor=self.institucion, estudiante=self.estudiante)

        self.assertEqual(self.estado_de(), EstadoDelEstudiante.ACTIVO)

    def test_quien_desactivo_no_se_guarda_en_ninguna_parte(self):
        """No es un olvido: el criterio dice «con independencia de quién».

        Guardarlo invitaría a que alguien escribiera algún día la regla contraria
        —«si desactivó el acudiente, que reactive él»— sin tener que declararla.
        """
        desactivar(actor=self.acudiente, estudiante=self.estudiante)
        self.estudiante.refresh_from_db()

        campos = {c.name for c in Estudiante._meta.get_fields()}
        self.assertFalse({c for c in campos if "desactiv" in c})

    def test_la_cafeteria_tampoco_reactiva(self):
        desactivar(actor=self.institucion, estudiante=self.estudiante)

        for cuenta in [self.cajero, self.administracion]:
            with self.subTest(rol=cuenta.rol):
                with self.assertRaises(PermissionDenied):
                    reactivar(actor=cuenta, estudiante=self.estudiante)

        self.assertEqual(self.estado_de(), EstadoDelEstudiante.DESACTIVADO)

    def test_una_cuenta_de_la_institucion_desactivada_no_reactiva(self):
        """`HU-42`, la misma regla que en el resto de servicios."""
        desactivar(actor=self.institucion, estudiante=self.estudiante)
        self.institucion.is_active = False
        self.institucion.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            reactivar(actor=self.institucion, estudiante=self.estudiante)


class LoQueLaReactivacionDevuelveTest(BaseDeReactivacion):
    """Qué significa «activo otra vez», comprobado donde se nota."""

    def setUp(self):
        super().setUp()
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000")
        )
        desactivar(actor=self.institucion, estudiante=self.estudiante)

    def test_vuelve_a_poder_comprar(self):
        """`INVD-2` mira el estado, así que revertir el estado lo revierte todo."""
        reactivar(actor=self.institucion, estudiante=self.estudiante)

        venta = registrar_venta(
            actor=self.cajero,
            estudiante=Estudiante.objects.get(pk=self.estudiante.pk),
            lineas={self.producto.id: 1},
        )
        self.assertIsNotNone(venta)

    def test_el_saldo_estaba_intacto(self):
        """Desactivar no mueve dinero: lo que bloquea es el uso, no el saldo."""
        from billetera.selectors import saldo_de

        reactivar(actor=self.institucion, estudiante=self.estudiante)

        self.assertEqual(saldo_de(self.estudiante), Decimal("50000.00"))

    def test_reactivar_dos_veces_no_es_un_error(self):
        """Idempotente: dos mostradores atendiendo a la misma familia."""
        reactivar(actor=self.institucion, estudiante=self.estudiante)
        reactivar(actor=self.institucion, estudiante=self.estudiante)

        self.assertEqual(self.estado_de(), EstadoDelEstudiante.ACTIVO)

    def test_a_un_retirado_no_se_le_reactiva(self):
        """De la baja no se vuelve (`HU-51`, `DEC-7`).

        Reactivar revierte una desactivación, no una baja: un retirado que se
        rematricula es un alta, y si algún día hace falta lo contrario hará falta
        una historia.
        """
        dar_de_baja(actor=self.institucion, estudiante=self.estudiante)

        with self.assertRaises(ValidationError):
            reactivar(actor=self.institucion, estudiante=self.estudiante)

        self.assertEqual(self.estado_de(), EstadoDelEstudiante.BAJA)


# --- La acción en el padrón ----------------------------------------------


class LaAccionDelPadronTest(BaseDeReactivacion):
    """`DT-30`. La pareja de la desactivación, en la misma pantalla."""

    def setUp(self):
        super().setUp()
        desactivar(actor=self.institucion, estudiante=self.estudiante)
        self.client.force_login(self.institucion)
        self.url = reverse(REACTIVAR, args=[self.estudiante.id])

    def test_reactiva_y_devuelve_la_tabla_con_el_estado_nuevo(self):
        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-estudiante-reactivado")
        self.assertEqual(self.estado_de(), EstadoDelEstudiante.ACTIVO)

    def test_la_fila_vuelve_a_ofrecer_desactivar(self):
        """Ida y vuelta: la fila queda como estaba antes de todo."""
        cuerpo = self.client.post(self.url).content.decode()

        self.assertIn("data-desactivar-estudiante", cuerpo)
        self.assertNotIn("data-reactivar-estudiante", cuerpo)
        self.assertNotIn("data-estudiante-desactivado-marca", cuerpo)

    def test_conserva_los_filtros_que_estaban_puestos(self):
        respuesta = self.client.post(self.url, {"busqueda": "Ana Sofía"})

        self.assertEqual(
            [e.id for e in respuesta.context["estudiantes"]], [self.estudiante.id]
        )

    def test_el_get_no_reactiva(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(self.estado_de(), EstadoDelEstudiante.DESACTIVADO)

    def test_el_acudiente_no_alcanza_la_ruta_ni_con_su_propio_hijo(self):
        """`INVD-3` por el camino de HTTP: no es que el botón no esté, es que la
        ruta responde `403` a quien no es la institución."""
        self.client.force_login(self.acudiente)

        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertEqual(self.estado_de(), EstadoDelEstudiante.DESACTIVADO)

    def test_el_acudiente_no_tiene_ninguna_ruta_de_reactivacion_en_su_panel(self):
        """La ausencia, comprobada sobre el mapa de rutas y no sobre la pantalla.

        `INT-1` tiene ruta para desactivar (`HU-48`) y **ninguna** para lo
        contrario: si algún día apareciera uno, esta prueba lo dice.
        """
        from config import urls

        rutas = {
            getattr(p, "name", None)
            for p in urls.urlpatterns
            if getattr(p, "name", None)
        }
        de_reactivacion = {r for r in rutas if "reactiv" in r}

        self.assertEqual(de_reactivacion, {REACTIVAR})
        self.assertIn(DESACTIVAR_ACUDIENTE, rutas)

    def test_a_un_retirado_lo_rechaza_y_lo_dice_en_la_tabla(self):
        dar_de_baja(actor=self.institucion, estudiante=self.estudiante)

        respuesta = self.client.post(self.url, {"retirados": "1"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-error-del-padron")
        self.assertEqual(self.estado_de(), EstadoDelEstudiante.BAJA)

    def test_la_ida_y_la_vuelta_completas_por_la_pantalla(self):
        """El recorrido que se enseña en la Sprint Review, de extremo a extremo.

        El acudiente desactiva desde su panel, la institución reactiva desde el
        padrón, y el estudiante vuelve a comprar. Son las dos historias
        (`HU-48`, `HU-49`) y la invariante que las separa.
        """
        reactivar(actor=self.institucion, estudiante=self.estudiante)
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("20000")
        )

        acudiente = self.client_class()
        acudiente.force_login(self.acudiente)
        acudiente.post(reverse(DESACTIVAR_ACUDIENTE, args=[self.estudiante.id]))
        self.assertEqual(self.estado_de(), EstadoDelEstudiante.DESACTIVADO)

        self.client.post(self.url)
        self.assertEqual(self.estado_de(), EstadoDelEstudiante.ACTIVO)

        venta = registrar_venta(
            actor=self.cajero,
            estudiante=Estudiante.objects.get(pk=self.estudiante.pk),
            lineas={self.producto.id: 1},
        )
        self.assertIsNotNone(venta)
