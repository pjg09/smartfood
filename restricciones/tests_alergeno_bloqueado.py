"""`TT-100` … `TT-103`. Bloqueo por alérgeno (`HU-11`, **`INV-5`**).

**Este es el fichero que vigila la invariante más fácil de romper del proyecto.**

`INV-5` dice que el bloqueo por alérgeno se aplica sobre la **condición** y no
sobre una lista fija de productos. La forma de romperla no es un descuido: es una
optimización razonable. Alguien mira la consulta que cruza tres tablas, decide
materializar «los productos que hoy llevan maní» en `RestriccionProducto`, y todo
sigue funcionando. Las pruebas pasan. La pantalla enseña lo mismo.

Y semanas después la cafetería añade un brownie con maní, y el estudiante
alérgico puede comprarlo.

Por eso la clase que importa es `UnProductoPosteriorQuedaCubiertoTest`: **crea el
producto después del bloqueo**. Ninguna prueba que use productos creados antes
puede detectar la materialización; ésta sí, y falla en el mismo commit que la
introduzca.

Los tres criterios de `HU-11`:

1. El bloqueo se aplica sobre la condición, no sobre una lista fija.
2. Un producto incorporado **después** queda cubierto si declara ese alérgeno.
3. Depende de que el catálogo declare alérgenos por producto (`HU-26`), que
   existe desde el Sprint 1.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Alergeno, Categoria, Producto, ProductoAlergeno
from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from restricciones.models import RestriccionAlergeno, RestriccionProducto
from restricciones.selectors import (
    alergenos_que_bloquean,
    identificadores_de_alergenos_bloqueados,
    productos_cubiertos_por_alergeno,
)
from restricciones.services import bloquear_alergeno, desbloquear_alergeno

CLAVE = "clave-de-prueba-2026"


def acudiente_con_estudiantes(sufijo="1", estudiantes=1):
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente-al{sufijo}@example.com", rol=Rol.ACUDIENTE, nombre="Marta"
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
    ficha = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"6351234{sufijo}"
    )
    hijos = [
        Estudiante.objects.create(
            nombre=f"Estudiante A{sufijo}{i}",
            documento=f"600{sufijo}00{i}",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        for i in range(estudiantes)
    ]
    return usuario, ficha, hijos


def cuenta(rol, sufijo):
    usuario = Usuario.objects.crear_usuario(
        email=f"{rol}-al{sufijo}@example.com", rol=rol, nombre=f"Cuenta {rol}"
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
    return usuario


def producto_con(nombre, *alergenos, precio="3000"):
    categoria, _ = Categoria.objects.get_or_create(nombre="Prueba")
    p = Producto.objects.create(
        nombre=nombre, precio=Decimal(precio), categoria=categoria
    )
    for a in alergenos:
        ProductoAlergeno.objects.create(producto=p, alergeno=a)
    return p


class UnProductoPosteriorQuedaCubiertoTest(TestCase):
    """**`TT-103`. La red de `INV-5`, y la razón de ser de este fichero.**

    Segundo criterio de `HU-11`. Todo lo que se crea aquí se crea **después** del
    bloqueo, que es la única forma de distinguir una condición evaluada de una
    lista materializada: para los productos anteriores las dos se comportan
    igual.
    """

    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiantes()
        self.mani = Alergeno.objects.create(nombre="Maní")
        # Se bloquea con el catálogo VACÍO de ese alérgeno: no hay nada que
        # materializar ni aunque alguien quisiera.
        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
        )

    def test_un_producto_creado_despues_queda_cubierto(self):
        brownie = producto_con("Brownie con maní", self.mani)

        self.assertIn(brownie, productos_cubiertos_por_alergeno(self.estudiante))

    def test_un_producto_que_declara_el_alergeno_despues_queda_cubierto(self):
        """El otro camino, y se rompe con la misma optimización.

        El producto ya existía y no declaraba nada; la cafetería corrige su ficha
        y le añade el maní. Queda cubierto en ese mismo instante, sin que nadie
        toque la restricción del acudiente.
        """
        galleta = producto_con("Galleta")
        self.assertNotIn(galleta, productos_cubiertos_por_alergeno(self.estudiante))

        ProductoAlergeno.objects.create(producto=galleta, alergeno=self.mani)

        self.assertIn(galleta, productos_cubiertos_por_alergeno(self.estudiante))

    def test_retirar_la_declaracion_lo_descubre_en_el_acto(self):
        """La simétrica. La verdad vive en `ProductoAlergeno`, en un solo sitio."""
        torta = producto_con("Torta", self.mani)
        self.assertIn(torta, productos_cubiertos_por_alergeno(self.estudiante))

        ProductoAlergeno.objects.filter(producto=torta, alergeno=self.mani).delete()

        self.assertNotIn(torta, productos_cubiertos_por_alergeno(self.estudiante))

    def test_bloquear_un_alergeno_no_escribe_ningun_producto(self):
        """La comprobación directa: **no se materializa nada**.

        Si alguien añade al servicio un bucle que cree una `RestriccionProducto`
        por cada producto con ese alérgeno, esto falla aquí y no seis semanas
        después en la caja.
        """
        producto_con("Torta de chocolate", self.mani)
        otro = Alergeno.objects.create(nombre="Lactosa")

        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=otro
        )

        self.assertEqual(RestriccionProducto.objects.count(), 0)
        self.assertEqual(RestriccionAlergeno.objects.count(), 2)

    def test_se_puede_bloquear_un_alergeno_que_nadie_declara_todavia(self):
        """El acudiente declara la alergia de su hijo, no el menú de la cafetería."""
        sesamo = Alergeno.objects.create(nombre="Sésamo")

        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=sesamo
        )
        pan = producto_con("Pan de sésamo", sesamo)

        self.assertIn(pan, productos_cubiertos_por_alergeno(self.estudiante))


class ElBloqueoEsSobreLaCondicionTest(TestCase):
    """Primer criterio: alcanza a todo lo que declare el alérgeno, no a una lista."""

    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiantes()
        self.mani = Alergeno.objects.create(nombre="Maní")
        self.lactosa = Alergeno.objects.create(nombre="Lactosa")
        self.torta = producto_con("Torta de chocolate", self.mani)
        self.galleta = producto_con("Galleta de maní", self.mani)
        self.leche = producto_con("Leche", self.lactosa)
        self.agua = producto_con("Agua")

    def test_bloquear_el_alergeno_cubre_todos_los_que_lo_declaran(self):
        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
        )

        cubiertos = set(productos_cubiertos_por_alergeno(self.estudiante))
        self.assertEqual(cubiertos, {self.torta, self.galleta})

    def test_no_alcanza_a_los_que_no_lo_declaran(self):
        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
        )

        cubiertos = productos_cubiertos_por_alergeno(self.estudiante)
        self.assertNotIn(self.leche, cubiertos)
        self.assertNotIn(self.agua, cubiertos)

    def test_un_producto_con_dos_alergenos_bloqueados_sale_una_sola_vez(self):
        combinado = producto_con("Postre", self.mani, self.lactosa)
        for a in (self.mani, self.lactosa):
            bloquear_alergeno(
                actor=self.usuario, estudiante=self.estudiante, alergeno=a
            )

        cubiertos = list(productos_cubiertos_por_alergeno(self.estudiante))

        self.assertEqual(cubiertos.count(combinado), 1)

    def test_dice_cual_es_el_alergeno_que_bloquea(self):
        """Para que la caja pueda decir por qué, y no solo que no."""
        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
        )

        self.assertEqual(
            list(alergenos_que_bloquean(self.estudiante, self.torta)), [self.mani]
        )
        self.assertEqual(list(alergenos_que_bloquean(self.estudiante, self.agua)), [])

    def test_desbloquear_descubre_todo_lo_que_cubria(self):
        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
        )

        retirado = desbloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
        )

        self.assertTrue(retirado)
        self.assertEqual(list(productos_cubiertos_por_alergeno(self.estudiante)), [])


class ElBloqueoDeAlergenoNoEsElDeProductoTest(TestCase):
    """Las dos restricciones son independientes, y hay que poder demostrarlo.

    `HU-10` es una lista y `HU-11` una condición. Se guardan en tablas distintas
    y se consultan por separado; retirar una no toca la otra.
    """

    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiantes()
        self.mani = Alergeno.objects.create(nombre="Maní")
        self.torta = producto_con("Torta de chocolate", self.mani)

    def test_bloquear_el_alergeno_no_crea_bloqueos_de_producto(self):
        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
        )

        self.assertEqual(RestriccionProducto.objects.count(), 0)

    def test_desbloquear_el_alergeno_no_toca_el_bloqueo_de_producto(self):
        from restricciones.selectors import identificadores_de_productos_bloqueados
        from restricciones.services import bloquear_producto

        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
        )
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.torta
        )

        desbloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
        )

        self.assertIn(
            self.torta.id, identificadores_de_productos_bloqueados(self.estudiante)
        )


class LaListaEsPorEstudianteTest(TestCase):
    def setUp(self):
        self.usuario, _, self.hijos = acudiente_con_estudiantes(estudiantes=2)
        self.mani = Alergeno.objects.create(nombre="Maní")
        producto_con("Galleta de maní", self.mani)

    def test_bloquear_a_un_hijo_no_bloquea_al_otro(self):
        uno, otro = self.hijos
        bloquear_alergeno(actor=self.usuario, estudiante=uno, alergeno=self.mani)

        self.assertEqual(len(productos_cubiertos_por_alergeno(uno)), 1)
        self.assertEqual(list(productos_cubiertos_por_alergeno(otro)), [])


class SoloElAcudienteBloqueaAlergenosTest(TestCase):
    """`INV-4` sobre la fila «Configurar y retirar restricciones» de `[S11]`."""

    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiantes()
        self.mani = Alergeno.objects.create(nombre="Maní")

    def _rechaza(self, actor):
        with self.assertRaises(PermissionDenied):
            bloquear_alergeno(
                actor=actor, estudiante=self.estudiante, alergeno=self.mani
            )
        self.assertEqual(identificadores_de_alergenos_bloqueados(self.estudiante), set())

    def test_el_cajero_no_bloquea(self):
        self._rechaza(cuenta(Rol.CAJERO, "a"))

    def test_la_administracion_de_la_cafeteria_no_bloquea(self):
        self._rechaza(cuenta(Rol.ADMINISTRADOR, "a"))

    def test_la_institucion_educativa_no_bloquea(self):
        self._rechaza(cuenta(Rol.INSTITUCION, "a"))

    def test_otro_acudiente_no_bloquea_a_un_hijo_ajeno(self):
        ajeno, _, _ = acudiente_con_estudiantes(sufijo="2")
        self._rechaza(ajeno)

    def test_sin_cuenta_identificada_no_se_bloquea(self):
        self._rechaza(None)

    def test_la_cafeteria_tampoco_desbloquea_lo_que_puso_la_familia(self):
        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
        )

        for rol in (Rol.CAJERO, Rol.ADMINISTRADOR, Rol.INSTITUCION):
            with self.subTest(rol=rol):
                with self.assertRaises(PermissionDenied):
                    desbloquear_alergeno(
                        actor=cuenta(rol, f"d{rol}"),
                        estudiante=self.estudiante,
                        alergeno=self.mani,
                    )

        self.assertIn(
            self.mani.id, identificadores_de_alergenos_bloqueados(self.estudiante)
        )


class BloquearDosVecesNoEsBloquearMasTest(TestCase):
    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiantes()
        self.mani = Alergeno.objects.create(nombre="Maní")

    def test_el_servicio_es_idempotente(self):
        uno = bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
        )
        otro = bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
        )

        self.assertEqual(uno.id, otro.id)
        self.assertEqual(RestriccionAlergeno.objects.count(), 1)

    def test_desbloquear_lo_que_no_estaba_no_es_un_error(self):
        self.assertFalse(
            desbloquear_alergeno(
                actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
            )
        )

    def test_la_base_impide_el_duplicado(self):
        RestriccionAlergeno.objects.create(
            estudiante=self.estudiante, alergeno=self.mani
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            RestriccionAlergeno.objects.create(
                estudiante=self.estudiante, alergeno=self.mani
            )


class LaPantallaDeAlergenosTest(TestCase):
    """`TT-102`. La pantalla del acudiente (`INT-1`)."""

    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiantes()
        self.mani = Alergeno.objects.create(nombre="Maní")
        self.lactosa = Alergeno.objects.create(nombre="Lactosa")
        self.torta = producto_con("Torta de chocolate", self.mani)
        self.url = reverse("alergenos-bloqueados", args=[self.estudiante.id])
        self.url_bloqueo = reverse("bloqueo-de-alergeno", args=[self.estudiante.id])

    def _entrar(self):
        self.client.login(email=self.usuario.email, password=CLAVE)

    def test_el_acudiente_ve_los_alergenos(self):
        self._entrar()
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Maní")
        self.assertContains(respuesta, "Lactosa")

    def test_sin_sesion_se_redirige_al_acceso(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("acceso"), respuesta["Location"])

    def test_el_cajero_recibe_403(self):
        cajero = cuenta(Rol.CAJERO, "pant")
        self.client.login(email=cajero.email, password=CLAVE)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_un_estudiante_ajeno_es_un_404(self):
        _, _, (ajeno,) = acudiente_con_estudiantes(sufijo="2")
        self._entrar()
        self.assertEqual(
            self.client.get(reverse("alergenos-bloqueados", args=[ajeno.id])).status_code,
            404,
        )

    def test_el_interruptor_bloquea_y_devuelve_la_lista(self):
        self._entrar()
        respuesta = self.client.post(
            self.url_bloqueo, {"alergeno": str(self.mani.id), "accion": "bloquear"}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(
            self.mani.id, identificadores_de_alergenos_bloqueados(self.estudiante)
        )
        self.assertContains(respuesta, 'id="lista-de-alergenos"')
        self.assertNotContains(respuesta, "<title>")

    def test_el_interruptor_desbloquea(self):
        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
        )
        self._entrar()

        self.client.post(
            self.url_bloqueo, {"alergeno": str(self.mani.id), "accion": "desbloquear"}
        )

        self.assertEqual(identificadores_de_alergenos_bloqueados(self.estudiante), set())

    def test_el_cajero_no_puede_bloquear_por_la_url(self):
        cajero = cuenta(Rol.CAJERO, "post")
        self.client.login(email=cajero.email, password=CLAVE)

        respuesta = self.client.post(
            self.url_bloqueo, {"alergeno": str(self.mani.id), "accion": "bloquear"}
        )

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(identificadores_de_alergenos_bloqueados(self.estudiante), set())

    def test_un_alergeno_inventado_es_un_404(self):
        self._entrar()
        respuesta = self.client.post(
            self.url_bloqueo,
            {"alergeno": "01a05e10-0000-7000-8000-000000000000", "accion": "bloquear"},
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_la_pantalla_dice_que_cubre_lo_que_llegue_despues(self):
        """Sin esa frase, el acudiente de un niño alérgico marca productos uno a
        uno y cree que ha terminado. Es la diferencia entre `HU-10` y `HU-11`."""
        self._entrar()
        cuerpo = self.client.get(self.url).content.decode()

        self.assertIn("después", cuerpo)
        self.assertIn("condición", cuerpo)

    def test_enseña_cuantos_productos_lo_declaran_hoy(self):
        self._entrar()
        self.assertContains(self.client.get(self.url), "Hoy lo declaran")

    def test_el_recuento_de_cubiertos_no_suma_dos_veces_el_mismo_producto(self):
        """Un producto con dos alérgenos bloqueados cuenta una vez."""
        producto_con("Postre", self.mani, self.lactosa)
        for a in (self.mani, self.lactosa):
            bloquear_alergeno(
                actor=self.usuario, estudiante=self.estudiante, alergeno=a
            )
        self._entrar()

        respuesta = self.client.get(self.url)

        # Torta (maní) y Postre (maní + lactosa) = 2 productos, no 3.
        self.assertEqual(respuesta.context["productos_cubiertos"], 2)

    def test_la_ficha_del_panel_cuenta_las_dos_restricciones_por_separado(self):
        bloquear_alergeno(
            actor=self.usuario, estudiante=self.estudiante, alergeno=self.mani
        )
        self._entrar()

        respuesta = self.client.get(reverse("mis-estudiantes"))

        self.assertContains(respuesta, "alérgeno")
        self.assertContains(respuesta, self.url)
        self.assertContains(
            respuesta, reverse("productos-bloqueados", args=[self.estudiante.id])
        )
