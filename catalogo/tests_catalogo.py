"""`TT-43`, `TT-44` y `TT-45`. Administración del catálogo (`HU-26`).

Los tres criterios de `HU-26`. El primero —«cada producto admite precio,
categoría, información nutricional y alérgenos declarados»— se prueba campo por
campo, porque es la lista que `TT-44` fijó y de la que dependen los reportes de
tres sprints más tarde: un campo que falte entonces no se reconstruye hacia
atrás, ya que lo vendido lleva copiado lo que había (`DT-8`).

Lo que sostiene `INV-5` está aparte, en `tests_alergenos.py` (`TT-46`).
"""

import re
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Alergeno, Categoria, Producto
from catalogo.selectors import productos_en_el_catalogo
from catalogo.services import crear_producto, editar_producto, retirar_del_catalogo
from cuentas.models import Rol
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos

NUTRICIONAL = {
    "porcion": "paquete de 30 g",
    "energia_kcal": 150,
    "proteinas_g": Decimal("3.20"),
    "carbohidratos_g": Decimal("18.00"),
    "azucares_g": Decimal("4.50"),
    "grasas_totales_g": Decimal("7.00"),
    "grasas_saturadas_g": Decimal("2.10"),
    "sodio_mg": 210,
}


class BaseDeCatalogo(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        self.actor = crear_cuenta(
            email="administracion@example.com",
            rol=Rol.ADMINISTRADOR,
            nombre="Administración de la cafetería",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.categoria = Categoria.objects.create(nombre="Panadería")
        self.lactosa = Alergeno.objects.create(nombre="Lactosa")

    def producto(self, nombre="Pan de queso", **extra):
        campos = {"precio": Decimal("2500"), "categoria": self.categoria, **extra}
        return crear_producto(actor=self.actor, nombre=nombre, **campos)


# --- Primer criterio: qué admite un producto -------------------------------


class UnProductoAdmiteLosCuatroTest(BaseDeCatalogo):
    def test_precio_y_categoria(self):
        producto = self.producto()

        self.assertEqual(producto.precio, Decimal("2500"))
        self.assertEqual(producto.categoria, self.categoria)

    def test_alergenos_declarados(self):
        producto = self.producto(alergenos=[self.lactosa])
        self.assertEqual([a.nombre for a in producto.alergenos.all()], ["Lactosa"])

    def test_los_ocho_campos_nutricionales_de_tt_44(self):
        producto = self.producto(**NUTRICIONAL)
        producto.refresh_from_db()

        for campo, valor in NUTRICIONAL.items():
            with self.subTest(campo=campo):
                self.assertEqual(getattr(producto, campo), valor)

    def test_el_precio_no_puede_ser_negativo(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Producto.objects.create(
                    nombre="Imposible",
                    precio=Decimal("-1"),
                    categoria=self.categoria,
                )

    def test_el_precio_es_decimal_y_no_coma_flotante(self):
        """Con dinero, 0.1 + 0.2 no es 0.3."""
        campo = Producto._meta.get_field("precio")
        self.assertEqual(campo.get_internal_type(), "DecimalField")


class LaInformacionNutricionalNoEsObligatoriaTest(BaseDeCatalogo):
    """`TT-44`, `[S2.2]`: vacío significa «no declarado», no cero."""

    def test_un_producto_sin_nada_declarado_se_crea(self):
        producto = self.producto()

        self.assertIsNone(producto.energia_kcal)
        self.assertFalse(producto.declara_informacion_nutricional)

    def test_con_un_solo_campo_ya_declara(self):
        producto = self.producto(energia_kcal=150)
        self.assertTrue(producto.declara_informacion_nutricional)

    def test_cero_es_un_valor_declarado_y_distinto_de_vacio(self):
        """La distinción de la que dependen los agregados de `HU-32`."""
        producto = self.producto(sodio_mg=0)

        self.assertEqual(producto.sodio_mg, 0)
        self.assertTrue(producto.declara_informacion_nutricional)


class LaBaseComprubaLoQuePuedeTest(BaseDeCatalogo):
    """`TT-44`, `[S2.3]`. Errores de captura que se ven sin saber del producto."""

    def test_las_saturadas_no_superan_a_las_totales(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Producto.objects.create(
                    nombre="Incoherente",
                    precio=Decimal("1000"),
                    categoria=self.categoria,
                    grasas_totales_g=Decimal("3"),
                    grasas_saturadas_g=Decimal("5"),
                )

    def test_los_azucares_no_superan_a_los_carbohidratos(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Producto.objects.create(
                    nombre="Incoherente",
                    precio=Decimal("1000"),
                    categoria=self.categoria,
                    carbohidratos_g=Decimal("10"),
                    azucares_g=Decimal("12"),
                )

    def test_si_uno_de_los_dos_falta_no_hay_nada_que_comparar(self):
        producto = self.producto(grasas_saturadas_g=Decimal("5"))
        self.assertEqual(producto.grasas_saturadas_g, Decimal("5"))

    def test_no_se_comprueba_la_coherencia_entre_energia_y_macronutrientes(self):
        """Deliberado: la energía de una etiqueta real no cuadra con los 4/4/9.

        Una restricción que rechaza etiquetas correctas obliga a inventarse los
        datos para poder guardarlos.
        """
        producto = self.producto(
            energia_kcal=1, proteinas_g=Decimal("50"), carbohidratos_g=Decimal("50")
        )
        self.assertEqual(producto.energia_kcal, 1)


# --- Retirar del catálogo, no borrar ---------------------------------------


class RetirarNoEsBorrarTest(BaseDeCatalogo):
    def test_el_producto_retirado_sigue_existiendo(self):
        producto = self.producto()
        retirar_del_catalogo(actor=self.actor, producto=producto)

        producto.refresh_from_db()
        self.assertFalse(producto.activo)
        self.assertTrue(Producto.objects.filter(pk=producto.pk).exists())

    def test_pero_deja_de_ofrecerse(self):
        producto = self.producto()
        self.assertEqual(productos_en_el_catalogo().count(), 1)

        retirar_del_catalogo(actor=self.actor, producto=producto)
        self.assertEqual(productos_en_el_catalogo().count(), 0)

    def test_editar_rechaza_un_campo_que_no_existe(self):
        producto = self.producto()
        with self.assertRaises(ValueError):
            editar_producto(actor=self.actor, producto=producto, inventado="x")


# --- `TT-45`, `DT-50`. La vista de gestión ------------------------------------
#
# Desde `DEC-25` el producto se crea, se edita y se retira en `/inventario/`, en
# una modal; el admin conserva las categorías y los alérgenos. Lo que estas
# pruebas protegían por el admin lo protegen ahora por la pantalla nueva.


class LaVistaDeGestionTest(BaseDeCatalogo):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.actor)

    def datos(self, **cambios):
        return {
            "nombre": "Pan de queso",
            "precio": "2500",
            "categoria": str(self.categoria.pk),
            "alergenos": [str(self.lactosa.pk)],
            "porcion": "unidad de 80 g",
            "energia_kcal": "220",
            **cambios,
        }

    def test_la_administracion_alcanza_las_tres_pantallas(self):
        for url in [
            reverse("inventario"),
            reverse("categorias"),
            reverse("alergenos"),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_el_producto_ya_no_esta_en_el_admin(self):
        """`DEC-25`: dos sitios para crear lo mismo acabarían pidiendo cosas distintas."""
        from django.urls import NoReverseMatch

        with self.assertRaises(NoReverseMatch):
            reverse("admin:catalogo_producto_changelist")

    def test_crea_un_producto_pasando_por_el_servicio(self):
        respuesta = self.client.post(reverse("producto-nuevo"), self.datos())

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'data-estado="creado"')
        self.assertEqual(respuesta["HX-Trigger"], "inventario-cambiado")
        producto = Producto.objects.get(nombre="Pan de queso")
        self.assertEqual(producto.energia_kcal, 220)
        self.assertEqual([a.nombre for a in producto.alergenos.all()], ["Lactosa"])

    def test_un_nombre_repetido_vuelve_con_su_error_y_no_crea_nada(self):
        self.producto(nombre="Pan de queso")

        respuesta = self.client.post(reverse("producto-nuevo"), self.datos(nombre="pan de QUESO"))

        self.assertContains(respuesta, "data-error-del-servidor")
        self.assertNotIn("HX-Trigger", respuesta)
        self.assertEqual(Producto.objects.filter(nombre__iexact="pan de queso").count(), 1)

    def test_las_saturadas_por_encima_de_las_totales_vuelven_con_su_error(self):
        """La `CheckConstraint` es la garantía; esto es el mensaje, en vez de un 500."""
        respuesta = self.client.post(
            reverse("producto-nuevo"),
            self.datos(grasas_totales_g="3", grasas_saturadas_g="5"),
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-error-del-servidor")
        self.assertFalse(Producto.objects.filter(nombre="Pan de queso").exists())

    def test_edita_los_alergenos(self):
        producto = self.producto(alergenos=[self.lactosa])
        mani = Alergeno.objects.create(nombre="Maní")

        self.client.post(
            reverse("edicion-del-producto", args=[producto.pk]),
            self.datos(nombre=producto.nombre, alergenos=[str(mani.pk)], activo="on"),
        )

        self.assertEqual({a.nombre for a in producto.alergenos.all()}, {"Maní"})

    def test_editar_sin_tocar_los_alergenos_no_los_borra(self):
        """El flanco de `INV-5` que está en la vista y no en el modelo.

        `declarar_alergenos` **reemplaza**, no acumula: recibe la lista completa
        y deja el producto declarando exactamente eso. Si la ficha no trajera
        marcados los que ya tiene, el navegador enviaría una selección vacía al
        cambiar cualquier otro campo, y editar el nombre de un producto le
        **borraría los alérgenos declarados**. `HU-11` dejaría de proteger a un
        estudiante alérgico sin que nada fallara.
        """
        producto = self.producto(alergenos=[self.lactosa])
        url = reverse("edicion-del-producto", args=[producto.pk])

        # Lo que el navegador ve marcado en la ficha.
        cuerpo = self.client.get(url).content.decode()
        marcados = re.findall(
            r'name="alergenos" value="([0-9a-f-]{36})"\s+checked', cuerpo
        )
        self.assertEqual(
            marcados, [str(self.lactosa.pk)],
            "la ficha no trae marcados los alérgenos que el producto ya declara",
        )

        # Y lo que el navegador devuelve al cambiar solo el nombre.
        self.client.post(
            url,
            {
                "nombre": "Pan de queso grande",
                "precio": "2500",
                "categoria": str(self.categoria.pk),
                "activo": "on",
                "alergenos": marcados,
            },
        )

        producto.refresh_from_db()
        self.assertEqual(producto.nombre, "Pan de queso grande")
        self.assertEqual(
            [a.nombre for a in producto.alergenos.all()], ["Lactosa"],
            "editar el nombre le borró los alérgenos declarados (INV-5)",
        )

    def test_guardar_la_ficha_tal_como_llega_no_falla_ni_cambia_nada(self):
        """Ida y vuelta: lo que la ficha pinta es lo que el formulario acepta.

        Se vio en la captura y no en ninguna prueba: el precio salía como
        «3450,00» —Django localiza un `Decimal` al pintarlo— y el formulario no
        entiende la coma, así que **guardar sin tocar el precio fallaba**. Las
        pruebas de arriba mandan sus propios datos y no podían verlo; esta manda
        lo que manda el navegador.
        """
        from html.parser import HTMLParser

        producto = self.producto(alergenos=[self.lactosa])
        editar_producto(
            actor=self.actor, producto=producto, precio=Decimal("3450.00"),
            grasas_totales_g=Decimal("3.20"), grasas_saturadas_g=Decimal("1.50"),
        )
        url = reverse("edicion-del-producto", args=[producto.pk])

        class LoQueEnviaElNavegador(HTMLParser):
            def __init__(self):
                super().__init__()
                self.datos, self._select, self._opcion = {}, None, None

            def handle_starttag(self, etiqueta, atributos):
                a = dict(atributos)
                nombre = a.get("name")
                if etiqueta == "input" and nombre and a.get("type") not in ("file",):
                    if a.get("type") in ("checkbox", "radio"):
                        if "checked" in a:
                            self.datos.setdefault(nombre, []).append(a.get("value", "on"))
                    else:
                        self.datos[nombre] = a.get("value", "")
                elif etiqueta == "select":
                    self._select = nombre
                elif etiqueta == "option" and self._select and "selected" in a:
                    self.datos[self._select] = a.get("value", "")

            def handle_endtag(self, etiqueta):
                if etiqueta == "select":
                    self._select = None

        lector = LoQueEnviaElNavegador()
        lector.feed(self.client.get(url).content.decode())

        respuesta = self.client.post(url, lector.datos)

        self.assertContains(respuesta, 'data-estado="guardado"')
        producto.refresh_from_db()
        self.assertEqual(producto.precio, Decimal("3450.00"))
        self.assertEqual(producto.grasas_totales_g, Decimal("3.20"))
        self.assertEqual(producto.grasas_saturadas_g, Decimal("1.50"))
        self.assertEqual([a.nombre for a in producto.alergenos.all()], ["Lactosa"])
        self.assertTrue(producto.activo)

    def test_el_alta_no_ofrece_quitar_una_imagen_que_no_existe(self):
        """`UX-1` del recorrido de `TT-35`, aplicado también aquí."""
        cuerpo = self.client.get(reverse("producto-nuevo")).content.decode()

        self.assertNotIn('name="quitar_imagen"', cuerpo)
        self.assertIn('name="imagen"', cuerpo)

    def test_el_alta_no_ofrece_sacarlo_del_catalogo(self):
        """Un producto nace a la venta; el interruptor es de la edición."""
        cuerpo = self.client.get(reverse("producto-nuevo")).content.decode()

        self.assertNotIn('name="activo"', cuerpo)

    def test_la_edicion_si_ofrece_el_catalogo(self):
        producto = self.producto()
        cuerpo = self.client.get(
            reverse("edicion-del-producto", args=[producto.pk])
        ).content.decode()

        self.assertIn('name="activo"', cuerpo)

    def test_retirar_pasa_por_el_servicio_y_no_borra(self):
        producto = self.producto()

        respuesta = self.client.post(reverse("retiro-del-producto", args=[producto.pk]))

        self.assertContains(respuesta, 'data-retiro-del-producto="hecho"')
        self.assertEqual(respuesta["HX-Trigger"], "inventario-cambiado")
        producto.refresh_from_db()
        self.assertFalse(producto.activo)

    def test_retirar_pide_confirmacion_antes(self):
        """El `GET` enseña la confirmación y no toca nada."""
        producto = self.producto()

        respuesta = self.client.get(reverse("retiro-del-producto", args=[producto.pk]))

        self.assertContains(respuesta, 'data-retiro-del-producto="pendiente"')
        producto.refresh_from_db()
        self.assertTrue(producto.activo)

    def test_devolver_al_catalogo(self):
        producto = self.producto()
        retirar_del_catalogo(actor=self.actor, producto=producto)

        respuesta = self.client.post(reverse("devolucion-al-catalogo", args=[producto.pk]))

        self.assertEqual(respuesta.status_code, 204)
        self.assertEqual(respuesta["HX-Trigger"], "inventario-cambiado")
        producto.refresh_from_db()
        self.assertTrue(producto.activo)


class ElCatalogoEsSoloDeLaCafeteriaTest(BaseDeCatalogo):
    """`[S11]`. Ni el cajero ni la institución educativa lo gestionan."""

    def rutas(self):
        producto = self.producto()
        return [
            ("get", reverse("inventario")),
            ("get", reverse("producto-nuevo")),
            ("post", reverse("producto-nuevo")),
            ("get", reverse("edicion-del-producto", args=[producto.pk])),
            ("post", reverse("retiro-del-producto", args=[producto.pk])),
            ("post", reverse("devolucion-al-catalogo", args=[producto.pk])),
        ]

    def test_ni_la_institucion_educativa_ni_el_cajero(self):
        """El catálogo es de quien lo vende. `USR-5` y `USR-3` no aparecen en esa fila."""
        rutas = self.rutas()
        for rol, email in [
            (Rol.INSTITUCION, "institucion@example.com"),
            (Rol.CAJERO, "cajero@example.com"),
        ]:
            usuario = crear_cuenta(
                email=email, rol=rol, accede_a_administracion=True, enviar_invitacion=False
            )
            self.client.force_login(usuario)
            for metodo, url in rutas:
                with self.subTest(rol=rol, url=url, metodo=metodo):
                    self.assertEqual(getattr(self.client, metodo)(url).status_code, 403)
        self.assertTrue(Producto.objects.get().activo)
