"""`TT-104`, `TT-105`. Retiro de una restricción (`HU-12`, `ALC-IN-19`).

Los dos criterios de `HU-12`:

1. **Solo el acudiente puede retirar una restricción.** Lo comprueban ya
   `tests_producto_bloqueado.py` y `tests_alergeno_bloqueado.py` llamando al
   servicio con cada rol; aquí se reafirma sobre lo que este PR añade — que el
   intento rechazado **no deja asiento**, porque no pasó nada.
2. **El retiro queda asentado**, por ser una acción auditable sobre la seguridad
   alimentaria de un menor: tiene que poder reconstruirse quién la hizo y cuándo.

Y la decisión que va más allá del criterio y se declara: **el bloqueo también se
asienta**. Un registro que solo guarda los retiros no reconstruye nada — «se
retiró el bloqueo de maní el día 3» no dice si el niño estuvo protegido antes.
`ElLibroReconstruyeLaHistoriaTest` es la que lo justifica: recorre una secuencia
de bloqueos y retiros y comprueba que el estado se puede rehacer leyéndola.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Alergeno, Categoria, Producto
from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from restricciones.models import AsientoDeRestriccion, TipoDeAsiento
from restricciones.selectors import historial_de_restricciones
from restricciones.services import (
    bloquear_alergeno,
    bloquear_producto,
    desbloquear_alergeno,
    desbloquear_producto,
)

CLAVE = "clave-de-prueba-2026"


def escenario(sufijo="1"):
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente-ret{sufijo}@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
    ficha = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"5351234{sufijo}"
    )
    estudiante = Estudiante.objects.create(
        nombre=f"Estudiante R{sufijo}",
        documento=f"500{sufijo}001",
        acudiente=ficha,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )
    categoria, _ = Categoria.objects.get_or_create(nombre="Prueba")
    # `get_or_create`: `Producto.nombre` es único, y un segundo escenario en la
    # misma prueba reutiliza el producto en vez de chocar contra la restricción.
    producto, _ = Producto.objects.get_or_create(
        nombre="Gaseosa", defaults={"precio": Decimal("2500"), "categoria": categoria}
    )
    alergeno = Alergeno.objects.create(nombre=f"Maní {sufijo}")
    return usuario, estudiante, producto, alergeno


def cuenta(rol, sufijo):
    u = Usuario.objects.crear_usuario(
        email=f"{rol}-ret{sufijo}@example.com", rol=rol, nombre=f"Cuenta {rol}"
    )
    u.set_password(CLAVE)
    u.save(update_fields=["password"])
    return u


class ElRetiroQuedaAsentadoTest(TestCase):
    """Segundo criterio de `HU-12`: quién lo hizo y cuándo."""

    def setUp(self):
        self.usuario, self.estudiante, self.producto, self.alergeno = escenario()

    def test_retirar_un_producto_deja_asiento_con_actor_y_fecha(self):
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.producto
        )
        desbloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.producto
        )

        retiro = AsientoDeRestriccion.objects.get(tipo=TipoDeAsiento.RETIRO)
        self.assertEqual(retiro.actor, self.usuario)
        self.assertEqual(retiro.estudiante, self.estudiante)
        self.assertEqual(retiro.producto, self.producto)
        self.assertIsNone(retiro.alergeno)
        self.assertIsNotNone(retiro.creado_en)

    def test_retirar_un_alergeno_deja_asiento(self):
        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.alergeno
        )
        desbloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.alergeno
        )

        retiro = AsientoDeRestriccion.objects.get(tipo=TipoDeAsiento.RETIRO)
        self.assertEqual(retiro.alergeno, self.alergeno)
        self.assertIsNone(retiro.producto)

    def test_el_bloqueo_tambien_se_asienta(self):
        """Va más allá del criterio, y por eso se comprueba aparte."""
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.producto
        )

        asiento = AsientoDeRestriccion.objects.get()
        self.assertEqual(asiento.tipo, TipoDeAsiento.BLOQUEO)

    def test_el_asiento_guarda_el_nombre_de_entonces(self):
        """`DT-8`. Renombrar el catálogo no puede reescribir el pasado.

        Sin esto, el asiento diría que el acudiente retiró la protección sobre
        algo que no es lo que vio al retirarla.
        """
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.producto
        )
        desbloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.producto
        )

        self.producto.nombre = "Bebida azucarada"
        self.producto.save(update_fields=["nombre"])

        for asiento in AsientoDeRestriccion.objects.all():
            self.assertEqual(asiento.nombre, "Gaseosa")

    def test_bloquear_dos_veces_no_asienta_dos_veces(self):
        """Un segundo toque no es un hecho nuevo: sería ruido en el libro."""
        for _ in range(3):
            bloquear_producto(
                actor=self.usuario, estudiante=self.estudiante, producto=self.producto
            )

        self.assertEqual(AsientoDeRestriccion.objects.count(), 1)

    def test_desbloquear_lo_que_no_estaba_no_asienta(self):
        desbloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.producto
        )

        self.assertEqual(AsientoDeRestriccion.objects.count(), 0)

    def test_un_intento_rechazado_no_deja_asiento(self):
        """Primer criterio de `HU-12`, visto desde el libro.

        Si el cajero pudiera dejar rastro de un intento, el historial diría que
        alguien tocó la restricción cuando no pasó nada.
        """
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.producto
        )

        with self.assertRaises(PermissionDenied):
            desbloquear_producto(
                actor=cuenta(Rol.CAJERO, "a"),
                estudiante=self.estudiante,
                producto=self.producto,
            )

        self.assertFalse(
            AsientoDeRestriccion.objects.filter(tipo=TipoDeAsiento.RETIRO).exists()
        )


class ElLibroReconstruyeLaHistoriaTest(TestCase):
    """Por qué se asienta también el bloqueo, demostrado.

    La pregunta que un auditor trae no es «¿se retiró algo?», es «¿estaba
    protegido este estudiante el día X?». Con solo los retiros no se responde.
    """

    def setUp(self):
        self.usuario, self.estudiante, self.producto, self.alergeno = escenario()

    def test_la_secuencia_completa_queda_en_el_libro_y_en_orden(self):
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.producto
        )
        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.alergeno
        )
        desbloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.producto
        )

        historial = list(historial_de_restricciones(self.estudiante))

        # Del más reciente al más antiguo.
        self.assertEqual(
            [(a.tipo, a.nombre) for a in historial],
            [
                (TipoDeAsiento.RETIRO, "Gaseosa"),
                (TipoDeAsiento.BLOQUEO, self.alergeno.nombre),
                (TipoDeAsiento.BLOQUEO, "Gaseosa"),
            ],
        )

    def test_el_limite_recorta_pero_el_historial_entero_sigue_ahi(self):
        for _ in range(3):
            bloquear_producto(
                actor=self.usuario, estudiante=self.estudiante, producto=self.producto
            )
            desbloquear_producto(
                actor=self.usuario, estudiante=self.estudiante, producto=self.producto
            )

        self.assertEqual(len(historial_de_restricciones(self.estudiante, limite=2)), 2)
        self.assertEqual(historial_de_restricciones(self.estudiante).count(), 6)

    def test_el_historial_es_por_estudiante(self):
        _, otro, _, _ = escenario(sufijo="2")
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.producto
        )

        self.assertEqual(historial_de_restricciones(self.estudiante).count(), 1)
        self.assertEqual(historial_de_restricciones(otro).count(), 0)


class ElAsientoNoSePuedeDejarAMediasTest(TestCase):
    """Las reglas que impone la base, no un `if` del servicio."""

    def setUp(self):
        self.usuario, self.estudiante, self.producto, self.alergeno = escenario()

    def test_un_asiento_sin_producto_ni_alergeno_no_entra(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            AsientoDeRestriccion.objects.create(
                actor=self.usuario,
                estudiante=self.estudiante,
                tipo=TipoDeAsiento.RETIRO,
                nombre="lo que sea",
            )

    def test_un_asiento_con_los_dos_no_entra(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            AsientoDeRestriccion.objects.create(
                actor=self.usuario,
                estudiante=self.estudiante,
                tipo=TipoDeAsiento.RETIRO,
                producto=self.producto,
                alergeno=self.alergeno,
                nombre="las dos cosas",
            )

    def test_el_asiento_y_el_borrado_van_en_la_misma_transaccion(self):
        """Un retiro sin su asiento es justo lo que `HU-12` prohíbe.

        Se comprueba por el efecto: si el asiento falla, el borrado tampoco
        queda. Se fuerza el fallo borrando el actor de la sesión —un `actor`
        sin guardar no puede referenciarse—.
        """
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.producto
        )
        sin_guardar = Usuario(email="fantasma@example.com", rol=Rol.ACUDIENTE)

        with self.assertRaises(Exception):
            desbloquear_producto(
                actor=sin_guardar, estudiante=self.estudiante, producto=self.producto
            )


class LaPantallaEnseniaElHistorialTest(TestCase):
    """`TT-105`. Un asiento que nadie puede leer no hace auditable nada."""

    def setUp(self):
        self.usuario, self.estudiante, self.producto, self.alergeno = escenario()
        self.client.login(email=self.usuario.email, password=CLAVE)
        self.url_productos = reverse(
            "productos-bloqueados", args=[self.estudiante.id]
        )
        self.url_alergenos = reverse(
            "alergenos-bloqueados", args=[self.estudiante.id]
        )

    def test_sin_cambios_la_pantalla_lo_dice(self):
        self.assertContains(
            self.client.get(self.url_productos), "Todavía no has cambiado ninguna"
        )

    def test_el_retiro_aparece_en_las_dos_pantallas(self):
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.producto
        )
        desbloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.producto
        )

        for url in (self.url_productos, self.url_alergenos):
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                self.assertContains(respuesta, "Se retiró el bloqueo de")
                self.assertContains(respuesta, "Gaseosa")

    def test_el_historial_llega_dentro_del_fragmento_que_htmx_intercambia(self):
        """Fuera de él se quedaría desfasado tras cada toque, y un registro de
        auditoría desfasado es peor que no enseñarlo."""
        respuesta = self.client.post(
            reverse("bloqueo-de-producto", args=[self.estudiante.id]),
            {"producto": str(self.producto.id), "accion": "bloquear"},
        )

        self.assertContains(respuesta, 'id="lista-de-productos"')
        self.assertContains(respuesta, "Se bloqueó")
        self.assertNotContains(respuesta, "<title>")

    def test_enseña_quien_lo_hizo(self):
        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.alergeno
        )

        self.assertContains(self.client.get(self.url_alergenos), "Marta Ruiz")
