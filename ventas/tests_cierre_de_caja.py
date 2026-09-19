"""`TT-171` … `TT-174`. El cierre de caja diario (`HU-55`, `DEC-6`, `INVD-5`).

Los seis criterios de la historia, y cuál los sostiene:

1. **El esperado se calcula desde las ventas registradas.** `efectivo_esperado_de`
   suma el libro; no hay tabla de recaudo que mantener.
2. **El cajero registra lo contado y la base.** El formulario pide esas dos
   cifras y ninguna más.
3. **El sistema calcula y registra la diferencia.** Sale de las tres columnas de
   la fila, así que queda registrada sin ser una columna (`DT-19`).
4. **Diferencia ≠ 0 exige motivo.** Lo comprueba el servicio y **lo garantiza la
   base** — las dos cosas, y se prueban por separado.
5. **Las transferencias no entran.** Ese dinero nunca pasó por el cajón.
6. **No hay apertura de turno: el cuadre es diario.** Una restricción de
   unicidad sobre la fecha.

La prueba que vigila `INVD-5` es `ElEsperadoNoSeDigitaTest`, y es de **ausencia**:
fija que no hay forma de que la cifra entre desde fuera. Lleva su contraprueba,
porque una prueba de ausencia pasa sola el día que deja de proteger.
"""

import inspect
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from ventas.models import CierreDeCaja, LineaVenta, MedioDePago, Venta
from ventas.selectors import efectivo_esperado_de, informacion_del_cierre
from ventas.services import (
    CierreSinMotivo,
    JornadaYaCerrada,
    cerrar_caja,
    efectivo_esperado_de as efectivo_esperado_importado_en_el_servicio,
)


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


def producto(nombre="Empanada", precio=3500):
    categoria, _ = Categoria.objects.get_or_create(nombre="Panadería")
    return Producto.objects.create(nombre=nombre, precio=precio, categoria=categoria)


def venta(*, medio, importe, quien=None, cuando=None, el_cajero=None):
    """Una venta ya asentada, con un renglón que suma `importe`.

    Se escribe directamente y no por `registrar_venta` a propósito: lo que estas
    pruebas leen es **el libro**, y montar existencias y saldo para cada caso
    metería en el camino tres invariantes que ya tienen sus propias pruebas.

    `creado_en` es `auto_now_add` y no se puede fijar al crear, así que se
    corrige después con `update()` — la receta que `CLAUDE.md` deja escrita para
    las pruebas de ventana.
    """
    fila = Venta.objects.create(
        cajero=el_cajero or cajero(f"cajero{Venta.objects.count()}@example.com"),
        estudiante=quien,
        medio_pago=medio,
    )
    LineaVenta.objects.create(
        venta=fila,
        producto=producto(f"Producto {LineaVenta.objects.count()}"),
        cantidad=1,
        precio_unitario=Decimal(importe),
    )
    if cuando is not None:
        Venta.objects.filter(pk=fila.pk).update(creado_en=cuando)
    return fila


def a_las_diez(fecha):
    """Un instante dentro de la jornada, en hora local.

    Las diez de la mañana y no medianoche: un `datetime` en el borde del día se
    desplaza al convertirlo de zona y la prueba empezaría a depender de en qué
    huso corre.
    """
    return timezone.make_aware(
        timezone.datetime.combine(fecha, timezone.datetime.min.time())
    ) + timedelta(hours=10)


class ElEfectivoEsperadoSaleDeLasVentasTest(TestCase):
    """Primer criterio de `HU-55` e `INVD-5`: se calcula, no se captura aparte."""

    def setUp(self):
        self.hoy = timezone.localdate()

    def test_suma_las_ventas_en_efectivo_de_la_jornada(self):
        venta(medio=MedioDePago.EFECTIVO, importe=3500, cuando=a_las_diez(self.hoy))
        venta(medio=MedioDePago.EFECTIVO, importe=2500, cuando=a_las_diez(self.hoy))

        self.assertEqual(efectivo_esperado_de(self.hoy), Decimal("6000.00"))

    def test_la_transferencia_no_entra_en_el_cuadre(self):
        """`DEC-6`: ese dinero nunca pasó por la caja.

        Es la condición que más fácil se pierde, y la que haría que todo cierre
        diera un faltante igual a lo transferido.
        """
        venta(medio=MedioDePago.EFECTIVO, importe=3500, cuando=a_las_diez(self.hoy))
        venta(medio=MedioDePago.TRANSFERENCIA, importe=90000, cuando=a_las_diez(self.hoy))

        self.assertEqual(efectivo_esperado_de(self.hoy), Decimal("3500.00"))

    def test_la_compra_de_un_estudiante_tampoco_entra(self):
        """`HU-54`: sale de su billetera, no del cajón."""
        venta(medio=MedioDePago.EFECTIVO, importe=3500, cuando=a_las_diez(self.hoy))
        venta(
            medio=MedioDePago.BILLETERA,
            importe=12000,
            quien=estudiante(),
            cuando=a_las_diez(self.hoy),
        )

        self.assertEqual(efectivo_esperado_de(self.hoy), Decimal("3500.00"))

    def test_las_ventas_de_otra_jornada_no_entran(self):
        ayer = self.hoy - timedelta(days=1)
        venta(medio=MedioDePago.EFECTIVO, importe=3500, cuando=a_las_diez(self.hoy))
        venta(medio=MedioDePago.EFECTIVO, importe=7000, cuando=a_las_diez(ayer))

        self.assertEqual(efectivo_esperado_de(self.hoy), Decimal("3500.00"))
        self.assertEqual(efectivo_esperado_de(ayer), Decimal("7000.00"))

    def test_una_jornada_sin_efectivo_espera_cero(self):
        """Y aquí el cero **sí** es un cero: la caja tenía que tener cero.

        No es el hueco de `[S2.4]` —«todavía no existe»—, es una cifra cierta: no
        se cobró nada en efectivo, así que no debería haber nada que contar.
        """
        self.assertEqual(efectivo_esperado_de(self.hoy), Decimal("0.00"))


class ElEsperadoNoSeDigitaTest(TestCase):
    """`INVD-5` en su forma más fuerte: **no hay por dónde escribirlo**.

    Una prueba de ausencia pasa sola el día que deja de proteger, así que lleva
    su contraprueba: que el servicio sí usa el selector que lo calcula.
    """

    def test_cerrar_caja_no_recibe_el_efectivo_esperado(self):
        parametros = inspect.signature(cerrar_caja).parameters

        self.assertNotIn("efectivo_esperado", parametros)
        # Lo que sí recibe, para que la ausencia signifique algo.
        self.assertIn("efectivo_contado", parametros)
        self.assertIn("base", parametros)

    def test_pasarlo_como_argumento_es_un_error(self):
        with self.assertRaises(TypeError):
            cerrar_caja(
                actor=cajero(),
                base=0,
                efectivo_contado=0,
                efectivo_esperado=Decimal("999999"),
            )

    def test_el_servicio_llama_al_selector_que_lo_calcula(self):
        """La contraprueba. Mira el **bytecode**, no el fuente: el docstring
        habla del selector, y buscarlo en el texto encontraría la explicación en
        vez del uso."""
        usados = inspect.unwrap(cerrar_caja).__code__.co_names

        self.assertIn("efectivo_esperado_de", usados)
        # Y es el mismo objeto que el selector, no otra función con ese nombre.
        self.assertIs(efectivo_esperado_importado_en_el_servicio, efectivo_esperado_de)


class LaDiferenciaExigeMotivoTest(TestCase):
    """Cuarto criterio de `HU-55`, con el mismo criterio de `ALC-IN-18`.

    Se comprueba **en los dos sitios**: el servicio da el mensaje y la base da la
    garantía (`DT-15`, regla 2). Son dos pruebas porque son dos protecciones, y
    la de la base es la que cubre los caminos que todavía no existen.
    """

    def setUp(self):
        self.cajero = cajero()
        self.hoy = timezone.localdate()
        venta(
            medio=MedioDePago.EFECTIVO,
            importe=10000,
            cuando=a_las_diez(self.hoy),
            el_cajero=self.cajero,
        )

    def test_sin_diferencia_no_hace_falta_motivo(self):
        cierre = cerrar_caja(
            actor=self.cajero, base=Decimal("20000"), efectivo_contado=Decimal("30000")
        )

        self.assertEqual(cierre.efectivo_esperado, Decimal("10000.00"))
        self.assertEqual(cierre.diferencia, Decimal("0.00"))
        self.assertTrue(cierre.cuadra)
        self.assertEqual(cierre.motivo, "")

    def test_con_diferencia_y_sin_motivo_el_servicio_rechaza(self):
        with self.assertRaises(CierreSinMotivo):
            cerrar_caja(
                actor=self.cajero,
                base=Decimal("20000"),
                efectivo_contado=Decimal("28000"),
            )

        # **No se escribió nada**: el rechazo no deja un cierre a medias.
        self.assertFalse(CierreDeCaja.objects.exists())

    def test_con_diferencia_y_motivo_queda_registrado(self):
        cierre = cerrar_caja(
            actor=self.cajero,
            base=Decimal("20000"),
            efectivo_contado=Decimal("28000"),
            motivo="Faltó un billete de $2.000",
        )

        self.assertEqual(cierre.diferencia, Decimal("-2000.00"))
        self.assertFalse(cierre.cuadra)

    def test_un_sobrante_tambien_exige_motivo(self):
        """La diferencia es simétrica: sobrar dinero tampoco se deja sin explicar."""
        with self.assertRaises(CierreSinMotivo):
            cerrar_caja(
                actor=self.cajero,
                base=Decimal("20000"),
                efectivo_contado=Decimal("35000"),
            )

    def test_la_base_lo_impone_aunque_alguien_se_salte_el_servicio(self):
        """**La violación se introduce a propósito**, que es lo que `DoD-5` pide.

        Se escribe la fila directamente con el ORM, saltándose `cerrar_caja`. Si
        la restricción no existiera, esto pasaría sin decir nada y el reporte de
        `HU-56` enseñaría un descuadre sin explicación.
        """
        with self.assertRaises(IntegrityError), transaction.atomic():
            CierreDeCaja.objects.create(
                fecha=self.hoy,
                cajero=self.cajero,
                base=Decimal("20000"),
                efectivo_contado=Decimal("28000"),
                efectivo_esperado=Decimal("10000"),
                motivo="",
            )

    def test_tres_espacios_no_son_un_motivo(self):
        """`TT-140` en la merma costó descubrir que «   » no es la cadena vacía.

        Aquí la restricción nace con `\\S` puesto, y esta prueba es lo que impide
        que alguien la relaje a `!= ""` sin enterarse.
        """
        with self.assertRaises(IntegrityError), transaction.atomic():
            CierreDeCaja.objects.create(
                fecha=self.hoy,
                cajero=self.cajero,
                base=Decimal("20000"),
                efectivo_contado=Decimal("28000"),
                efectivo_esperado=Decimal("10000"),
                motivo="   ",
            )


class UnCierrePorJornadaTest(TestCase):
    """`DEC-6`: el cuadre es diario y no hay apertura de turno."""

    def setUp(self):
        self.cajero = cajero()
        self.hoy = timezone.localdate()

    def test_la_segunda_vez_el_servicio_lo_dice(self):
        cerrar_caja(actor=self.cajero, base=0, efectivo_contado=0)

        with self.assertRaises(JornadaYaCerrada):
            cerrar_caja(actor=self.cajero, base=0, efectivo_contado=0)

    def test_otro_cajero_tampoco_abre_un_segundo_cierre(self):
        """Un cierre por cajero sería un turno con otro nombre, y `DEC-6` los
        descarta expresamente."""
        cerrar_caja(actor=self.cajero, base=0, efectivo_contado=0)

        with self.assertRaises(JornadaYaCerrada):
            cerrar_caja(actor=cajero("otro@example.com"), base=0, efectivo_contado=0)

    def test_la_base_lo_impone(self):
        cerrar_caja(actor=self.cajero, base=0, efectivo_contado=0)

        with self.assertRaises(IntegrityError), transaction.atomic():
            CierreDeCaja.objects.create(
                fecha=self.hoy,
                cajero=self.cajero,
                base=Decimal("0"),
                efectivo_contado=Decimal("0"),
                efectivo_esperado=Decimal("0"),
            )

    def test_cada_jornada_tiene_el_suyo(self):
        cerrar_caja(actor=self.cajero, base=0, efectivo_contado=0)
        cerrar_caja(
            actor=self.cajero,
            fecha=self.hoy - timedelta(days=1),
            base=0,
            efectivo_contado=0,
        )

        self.assertEqual(CierreDeCaja.objects.count(), 2)


class SoloElCajeroCuadraLaCajaTest(TestCase):
    """`HU-55` es de `USR-3`. La administración **consulta** los cierres
    (`HU-56`), que es otra historia y otra pantalla."""

    def test_los_otros_tres_roles_no_cierran(self):
        for rol in (Rol.ADMINISTRADOR, Rol.INSTITUCION, Rol.ACUDIENTE):
            with self.subTest(rol=rol):
                actor = Usuario.objects.crear_usuario(
                    email=f"{rol}@example.com", rol=rol, nombre="Persona"
                )
                with self.assertRaises(PermissionDenied):
                    cerrar_caja(actor=actor, base=0, efectivo_contado=0)

    def test_el_rechazo_nombra_el_cuadre_y_no_la_venta(self):
        """El rol exigido es el mismo que para vender, **y el mensaje no**.

        `cerrar_caja` reutiliza la comprobación de la venta, y sin decirle de qué
        habla contestaba «registrar ventas en el punto de venta es del rol
        cajero» a quien intentó cuadrar la caja: nombra otra función y otra
        regla. Se vio ejecutándolo, no en las pruebas.

        Se afirma sobre la regla citada —`HU-55`— y no sobre la redacción
        entera, que cualquiera puede mejorar en un PR que no tenga que ver.
        """
        administrador = Usuario.objects.crear_usuario(
            email="admin-mensaje@example.com", rol=Rol.ADMINISTRADOR, nombre="Admin"
        )

        with self.assertRaises(PermissionDenied) as capturado:
            cerrar_caja(actor=administrador, base=0, efectivo_contado=0)

        mensaje = str(capturado.exception)
        self.assertIn("HU-55", mensaje)
        self.assertNotIn("venta", mensaje.lower())

    def test_un_cajero_desactivado_no_opera(self):
        actor = cajero()
        actor.is_active = False
        actor.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            cerrar_caja(actor=actor, base=0, efectivo_contado=0)

    def test_el_selector_de_la_pantalla_exige_el_mismo_rol(self):
        """La autorización vive en el selector y no en la vista, como en
        `informacion_de_cobro`: es el único camino por el que el recaudo del día
        llega a una pantalla (`DT-11`, `INV-4`)."""
        administrador = Usuario.objects.crear_usuario(
            email="admin@example.com", rol=Rol.ADMINISTRADOR, nombre="Admin"
        )

        with self.assertRaises(PermissionDenied):
            informacion_del_cierre(actor=administrador)


class LaPantallaDelCierreTest(TestCase):
    """`TT-173`. Lo que se puede hacer desde `/punto-de-venta/cierre/`."""

    def setUp(self):
        self.cajero = cajero()
        self.hoy = timezone.localdate()
        self.url = reverse("cierre-de-caja")

    def test_el_cajero_entra_y_los_demas_no(self):
        self.client.force_login(self.cajero)
        self.assertEqual(self.client.get(self.url).status_code, 200)

        for rol in (Rol.ADMINISTRADOR, Rol.INSTITUCION, Rol.ACUDIENTE):
            with self.subTest(rol=rol):
                self.client.force_login(
                    Usuario.objects.crear_usuario(
                        email=f"{rol}@example.com", rol=rol, nombre="Persona"
                    )
                )
                self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_sin_sesion_lleva_al_acceso(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("acceso"), respuesta["Location"])

    def test_cuadrar_la_caja_escribe_el_cierre_y_redirige(self):
        venta(
            medio=MedioDePago.EFECTIVO,
            importe=10000,
            cuando=a_las_diez(self.hoy),
            el_cajero=self.cajero,
        )
        self.client.force_login(self.cajero)

        respuesta = self.client.post(
            self.url, {"base": "20000", "efectivo_contado": "30000", "motivo": ""}
        )

        self.assertEqual(respuesta.status_code, 302)
        cierre = CierreDeCaja.objects.get()
        self.assertEqual(cierre.efectivo_esperado, Decimal("10000.00"))
        self.assertEqual(cierre.cajero, self.cajero)

    def test_una_diferencia_sin_motivo_no_escribe_nada(self):
        venta(
            medio=MedioDePago.EFECTIVO,
            importe=10000,
            cuando=a_las_diez(self.hoy),
            el_cajero=self.cajero,
        )
        self.client.force_login(self.cajero)

        respuesta = self.client.post(
            self.url, {"base": "20000", "efectivo_contado": "28000", "motivo": ""}
        )

        # `200` y no `302`: la pantalla vuelve con el motivo del rechazo dentro.
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(CierreDeCaja.objects.exists())

    def test_una_jornada_cerrada_no_vuelve_a_ofrecer_el_formulario(self):
        """Se afirma sobre un `data-*` propio y no sobre la copia ni sobre
        `<form>`, que la pantalla podría estrenar por otro motivo."""
        self.client.force_login(self.cajero)
        cerrar_caja(actor=self.cajero, base=0, efectivo_contado=0)

        respuesta = self.client.get(self.url)

        self.assertContains(respuesta, "data-cierre-registrado")
        self.assertNotContains(respuesta, "data-cierre-de-caja")

    def test_la_pantalla_dice_cuantas_ventas_componen_el_esperado(self):
        """`INVD-5` pide que el esperado se pueda **explicar**. Una cifra sola
        hay que creérsela; «de 2 ventas en efectivo» se puede ir a comprobar."""
        venta(
            medio=MedioDePago.EFECTIVO,
            importe=3500,
            cuando=a_las_diez(self.hoy),
            el_cajero=self.cajero,
        )
        venta(
            medio=MedioDePago.TRANSFERENCIA,
            importe=90000,
            cuando=a_las_diez(self.hoy),
            el_cajero=self.cajero,
        )
        self.client.force_login(self.cajero)

        informacion = self.client.get(self.url).context["informacion"]

        self.assertEqual(informacion.ventas_en_efectivo, 1)
        self.assertEqual(informacion.efectivo_esperado, Decimal("3500.00"))
