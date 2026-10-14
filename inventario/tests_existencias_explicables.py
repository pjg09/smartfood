"""`TT-141`, `TT-142`. Las existencias se explican desde el historial (`HU-29`).

**`TST-4`**, el último de los cuatro escenarios críticos que `ENT-05` exige
demostrar con evidencia de ejecución:

    «Comparación entre existencias e historial de inventario →
     correspondencia exacta.»

Con `TST-3` (Sprint 2) y `TST-1` y `TST-2` (Sprint 3), al integrar esto **el plan
de pruebas queda completo**.

Los dos criterios de `HU-29`:

1. **Todo movimiento de inventario queda asentado con su motivo.** El de una
   salida por venta **es** la venta, y por eso ese movimiento la señala en vez de
   escribir un texto (`TT-78`); el del ingreso y la merma es su motivo, y en la
   merma es obligatorio (`INV-8`, `HU-28`).
2. **Las existencias mostradas coinciden exactamente con el historial.**
   *Mostradas*: no basta con que `existencias_de` cuadre consigo mismo. Por eso
   `LaPantallaEnsenaLaExplicacionTest` compara contra lo que llega a la pantalla.

**Esta prueba no sobra por ser cierta por construcción.** Que hoy no exista una
columna `existencias` hace la correspondencia inevitable; lo que estas pruebas
detectan es el día en que alguien meta un atajo —una caché, un contador, un campo
«para no recalcular»— y las dos cifras empiecen a separarse. Ese día, esto falla.
Es el mismo razonamiento de `TST-3` en `billetera/tests_saldo.py`, aplicado al
otro libro.
"""

from decimal import Decimal
from random import Random

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from billetera.services import recargar
from catalogo.models import Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from inventario.models import MovimientoInventario, TipoDeMovimientoDeInventario
from inventario.selectors import existencias_de, historial_de
from inventario.services import ingresar_mercancia, registrar_merma
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from ventas.services import registrar_venta


def producto(nombre="Empanada de carne", precio="3500"):
    categoria, _ = Categoria.objects.get_or_create(nombre="Comidas")
    return Producto.objects.create(
        nombre=nombre, precio=Decimal(precio), categoria=categoria
    )


def usuario_con_rol(rol, email):
    return Usuario.objects.crear_usuario(email=email, rol=rol, nombre="Persona")


def acudiente_con_estudiante(sufijo="1"):
    usuario = usuario_con_rol(Rol.ACUDIENTE, f"acudiente{sufijo}@example.com")
    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"4351234{sufijo}"
    )
    estudiante = Estudiante.objects.create(
        nombre=f"Estudiante {sufijo}",
        documento=f"100{sufijo}0001",
        acudiente=acudiente,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )
    return usuario, estudiante


def suma_en_python(producto_):
    """Las existencias reconstruidas a mano, movimiento a movimiento.

    Deliberadamente ingenuo: si esto usara `Sum` estaría comparando la base
    consigo misma y `TST-4` no probaría nada. La gracia es que las dos cifras
    salgan de caminos distintos — `existencias_de` agrega en PostgreSQL, esto
    recorre el historial en Python.
    """
    total = 0
    for movimiento in historial_de(producto_):
        total += movimiento.cantidad
    return total


class TST4LasExistenciasCoincidenConSuHistorialTest(TestCase):
    """**`TST-4`, `INV-3`, `HU-29`.** El escenario crítico, en seis formas."""

    def setUp(self):
        self.producto = producto()
        self.administracion = usuario_con_rol(Rol.ADMINISTRADOR, "admin@example.com")
        self.cajero = usuario_con_rol(Rol.CAJERO, "cajero@example.com")
        self.acudiente, self.estudiante = acudiente_con_estudiante("1")

    def test_sin_movimientos_las_dos_cifras_son_cero(self):
        self.assertEqual(existencias_de(self.producto), 0)
        self.assertEqual(suma_en_python(self.producto), 0)

    def test_tras_un_ingreso_real_las_dos_cifras_coinciden(self):
        """El ingreso entra por el servicio, no escribiendo el movimiento a mano:
        lo que se comprueba es el camino que usa la aplicación."""
        ingresar_mercancia(
            actor=self.administracion, producto=self.producto, cantidad=30
        )

        self.assertEqual(existencias_de(self.producto), 30)
        self.assertEqual(existencias_de(self.producto), suma_en_python(self.producto))

    def test_con_los_tres_tipos_de_movimiento(self):
        """**El escenario que `TST-4` describe**: ingreso, venta y merma.

        Los tres por su camino real —`ingresar_mercancia`, `registrar_venta` y
        `registrar_merma`—, no fabricando asientos: lo que se compara es lo que
        el sistema escribe cuando funciona, no lo que una prueba sabe escribir.
        """
        ingresar_mercancia(
            actor=self.administracion,
            producto=self.producto,
            cantidad=40,
            motivo="Pedido semanal",
        )
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000")
        )
        registrar_venta(
            actor=self.cajero,
            estudiante=self.estudiante,
            lineas={self.producto.id: 3},
        )
        registrar_merma(
            actor=self.administracion,
            producto=self.producto,
            cantidad=5,
            motivo="Se cayó la bandeja",
        )

        self.assertEqual(existencias_de(self.producto), 32)
        self.assertEqual(existencias_de(self.producto), suma_en_python(self.producto))

        tipos = {m.tipo for m in historial_de(self.producto)}
        self.assertEqual(
            tipos,
            {
                TipoDeMovimientoDeInventario.INGRESO,
                TipoDeMovimientoDeInventario.VENTA,
                TipoDeMovimientoDeInventario.MERMA,
            },
        )

    def test_todo_movimiento_queda_asentado_con_lo_que_lo_explica(self):
        """Primer criterio de `HU-29`.

        El de una salida por venta **es** la venta, así que se comprueba que la
        señala; el del ingreso y la merma es su motivo. Ninguno se queda sin
        nada que lo explique.
        """
        ingresar_mercancia(
            actor=self.administracion,
            producto=self.producto,
            cantidad=40,
            motivo="Pedido semanal",
        )
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000")
        )
        registrar_venta(
            actor=self.cajero, estudiante=self.estudiante, lineas={self.producto.id: 2}
        )
        registrar_merma(
            actor=self.administracion,
            producto=self.producto,
            cantidad=1,
            motivo="Caducada",
        )

        for movimiento in historial_de(self.producto):
            with self.subTest(tipo=movimiento.tipo):
                if movimiento.tipo == TipoDeMovimientoDeInventario.VENTA:
                    self.assertIsNotNone(movimiento.venta_id)
                else:
                    self.assertTrue(movimiento.motivo.strip())

    def test_con_un_historial_largo_y_desordenado(self):
        """Cien movimientos en un orden que no ayuda.

        La semilla es fija: una prueba que falla una vez de cada veinte no es una
        prueba, es una moneda. Se ingresa más de lo que se merma para que el
        historial sea posible — `registrar_merma` no deja existencias negativas,
        y un historial imposible no demostraría nada sobre el sistema real.
        """
        azar = Random(20260918)
        esperado = 0

        for _ in range(100):
            if azar.random() < 0.65 or esperado < 10:
                cantidad = azar.randrange(1, 50)
                ingresar_mercancia(
                    actor=self.administracion,
                    producto=self.producto,
                    cantidad=cantidad,
                    motivo="Pedido",
                )
                esperado += cantidad
            else:
                cantidad = azar.randrange(1, min(10, esperado) + 1)
                registrar_merma(
                    actor=self.administracion,
                    producto=self.producto,
                    cantidad=cantidad,
                    motivo="Rotura",
                )
                esperado -= cantidad

        self.assertEqual(existencias_de(self.producto), esperado)
        self.assertEqual(existencias_de(self.producto), suma_en_python(self.producto))

    def test_las_existencias_no_dependen_del_orden_en_que_se_lea(self):
        """Una suma no tiene orden, y las existencias tampoco pueden tenerlo.

        Si algún día se calcularan arrastrando un acumulado por el historial,
        leerlo al revés daría otra cifra. Aquí no.
        """
        ingresar_mercancia(
            actor=self.administracion, producto=self.producto, cantidad=20
        )
        registrar_merma(
            actor=self.administracion,
            producto=self.producto,
            cantidad=7,
            motivo="Caducadas",
        )

        al_derecho = sum(m.cantidad for m in historial_de(self.producto))
        al_reves = sum(m.cantidad for m in reversed(list(historial_de(self.producto))))

        self.assertEqual(al_derecho, al_reves)
        self.assertEqual(existencias_de(self.producto), al_derecho)


class CadaProductoExplicaSoloLoSuyoTest(TestCase):
    """Las existencias de un producto no se contaminan con las de otro.

    Parece obvio y es justo lo que un `filter` mal escrito rompe sin ruido: la
    suma seguiría cuadrando con *algún* historial, solo que con el que no es.
    """

    def test_dos_productos_no_se_mezclan(self):
        administracion = usuario_con_rol(Rol.ADMINISTRADOR, "admin2@example.com")
        empanada = producto("Empanada")
        jugo = producto("Jugo de mora", "2500")

        ingresar_mercancia(actor=administracion, producto=empanada, cantidad=30)
        ingresar_mercancia(actor=administracion, producto=jugo, cantidad=12)
        registrar_merma(
            actor=administracion, producto=jugo, cantidad=2, motivo="Se derramó"
        )

        self.assertEqual(existencias_de(empanada), 30)
        self.assertEqual(existencias_de(jugo), 10)
        self.assertEqual(existencias_de(empanada), suma_en_python(empanada))
        self.assertEqual(existencias_de(jugo), suma_en_python(jugo))


class LaPantallaEnsenaLaExplicacionTest(TestCase):
    """`TT-141`. El segundo criterio dice «las existencias **mostradas**».

    Que `existencias_de` cuadre con el historial es la mitad. La otra es que lo
    que llega a la pantalla sea esa misma cifra y venga con su desglose: un
    número correcto que nadie puede desglosar no explica nada.
    """

    def setUp(self):
        sincronizar_grupos_y_permisos()
        self.administracion = crear_cuenta(
            email="admin3@example.com",
            rol=Rol.ADMINISTRADOR,
            nombre="Administración de la cafetería",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.producto = producto()
        self.cajero = usuario_con_rol(Rol.CAJERO, "cajero2@example.com")
        self.acudiente, self.estudiante = acudiente_con_estudiante("2")
        self.client.force_login(self.administracion)

        ingresar_mercancia(
            actor=self.administracion,
            producto=self.producto,
            cantidad=40,
            motivo="Pedido semanal",
        )
        recargar(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("50000")
        )
        registrar_venta(
            actor=self.cajero, estudiante=self.estudiante, lineas={self.producto.id: 3}
        )
        registrar_merma(
            actor=self.administracion,
            producto=self.producto,
            cantidad=5,
            motivo="Se cayó la bandeja",
        )

    def url(self, producto=None):
        return reverse("historial-del-producto", args=[(producto or self.producto).pk])

    def test_la_cifra_que_se_muestra_es_la_del_historial(self):
        """**`TST-4` sobre lo mostrado**, que es lo que dice el criterio."""
        respuesta = self.client.get(self.url())

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["existencias"], 32)
        self.assertEqual(
            respuesta.context["existencias"], suma_en_python(self.producto)
        )

    def test_las_lineas_suman_la_cifra_total_y_no_hay_aviso(self):
        """Las dos cifras salen por caminos distintos a propósito: el `SUM` de la
        base y la cuenta de las líneas que se enseñan. Si divergieran, la modal
        lo diría — y esta prueba es la que lo dice antes que nadie."""
        respuesta = self.client.get(self.url())

        self.assertEqual(respuesta.context["suma"], respuesta.context["existencias"])
        self.assertNotContains(respuesta, "data-historial-descuadrado")

    def test_si_divergieran_la_modal_lo_diria(self):
        """La contraprueba de la anterior: sin ella, un aviso que nunca se pinta
        pasaría por una garantía."""
        from django.template.loader import render_to_string

        cuerpo = render_to_string(
            "inventario/partials/historial.html",
            {"producto": self.producto, "movimientos": [], "existencias": 32, "suma": 30},
        )

        self.assertIn("data-historial-descuadrado", cuerpo)

    def test_el_desglose_llega_del_mas_reciente_al_mas_antiguo(self):
        """Es el orden en que se lee un extracto."""
        respuesta = self.client.get(self.url())
        tipos = [movimiento.tipo for movimiento in respuesta.context["movimientos"]]

        self.assertEqual(
            tipos,
            [
                TipoDeMovimientoDeInventario.MERMA,
                TipoDeMovimientoDeInventario.VENTA,
                TipoDeMovimientoDeInventario.INGRESO,
            ],
        )

    def test_cada_linea_dice_quien(self):
        """`HU-69`: la merma y el ingreso, la administración; la venta, el cajero."""
        respuesta = self.client.get(self.url())
        quienes = {m.tipo: m.responsable for m in respuesta.context["movimientos"]}

        self.assertEqual(quienes[TipoDeMovimientoDeInventario.MERMA], "Administración de la cafetería")
        self.assertEqual(quienes[TipoDeMovimientoDeInventario.INGRESO], "Administración de la cafetería")
        self.assertEqual(quienes[TipoDeMovimientoDeInventario.VENTA], self.cajero.nombre or self.cajero.email)

    def test_una_entrega_anterior_a_hu_69_la_firma_quien_entrego_y_no_el_acudiente(self):
        """Lo escrito antes de que el libro guardara quién no tiene
        `registrado_por`. La entrega de un pedido lo saca de
        `PedidoAnticipado.entregado_por`: el acudiente que reservó no movió nada
        del inventario, y atribuírselo sería inventar un autor."""
        from ventas.services import entregar, reservar

        pedido = reservar(
            actor=self.acudiente, estudiante=self.estudiante, lineas={self.producto.id: 1}
        )
        entregar(actor=self.cajero, pedido=pedido)
        # Como estaba antes de `HU-69`: sin quién en el libro.
        MovimientoInventario.objects.filter(venta=pedido.venta).update(registrado_por=None)

        respuesta = self.client.get(self.url())
        (entrega,) = [m for m in respuesta.context["movimientos"] if m.venta_id == pedido.venta_id]

        self.assertEqual(entrega.responsable, self.cajero.nombre)

    def test_el_desglose_llega_entero_y_no_una_pagina(self):
        """`TST-4` compara contra el historial completo: una página no probaría
        nada, y un descuadre viejo se escondería en la segunda."""
        respuesta = self.client.get(self.url())

        self.assertEqual(
            len(respuesta.context["movimientos"]),
            historial_de(self.producto).count(),
        )

    def test_un_producto_sin_movimientos_dice_cero_y_no_un_hueco(self):
        vacio = producto("Arepa", "3000")

        respuesta = self.client.get(self.url(vacio))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["existencias"], 0)
        self.assertEqual(respuesta.context["movimientos"], [])

    def test_la_fila_del_producto_abre_su_explicacion(self):
        """El gesto que pide `HU-29`: desde la cifra, a su desglose. Se afirma
        sobre la URL y no sobre la copia."""
        respuesta = self.client.get(reverse("lista-del-inventario"))

        self.assertContains(respuesta, self.url())

    def test_un_producto_que_no_existe_da_404(self):
        respuesta = self.client.get(
            reverse("historial-del-producto", args=["01999999-9999-7999-8999-999999999999"])
        )

        self.assertEqual(respuesta.status_code, 404)


class SoloLaAdministracionVeElHistorialTest(TestCase):
    """`[S11]`: el inventario es de `USR-4` y de nadie más.

    La pantalla enseña el libro entero de un producto, así que se protege como
    el resto del inventario — y se comprueba por la ruta, no por el menú.
    """

    def setUp(self):
        sincronizar_grupos_y_permisos()
        self.producto = producto()
        administracion = usuario_con_rol(Rol.ADMINISTRADOR, "admin4@example.com")
        ingresar_mercancia(actor=administracion, producto=self.producto, cantidad=10)
        self.url = reverse("historial-del-producto", args=[self.producto.pk])

    def test_un_anonimo_no_llega(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 302)

    def test_la_institucion_no_ve_el_inventario(self):
        institucion = crear_cuenta(
            email="institucion@example.com",
            rol=Rol.INSTITUCION,
            nombre="Secretaría",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.client.force_login(institucion)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 403)

    def test_el_cajero_tampoco(self):
        cajero = crear_cuenta(
            email="cajero3@example.com",
            rol=Rol.CAJERO,
            nombre="Cajero",
            accede_a_administracion=False,
            enviar_invitacion=False,
        )
        self.client.force_login(cajero)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 403)

    def test_el_acudiente_tampoco(self):
        acudiente, _ = acudiente_con_estudiante("3")
        self.client.force_login(acudiente)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 403)
