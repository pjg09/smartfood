"""`TT-43`, `TT-44` y `TT-45`. Administración del catálogo (`HU-26`).

Los tres criterios de `HU-26`. El primero —«cada producto admite precio,
categoría, información nutricional y alérgenos declarados»— se prueba campo por
campo, porque es la lista que `TT-44` fijó y de la que dependen los reportes de
tres sprints más tarde: un campo que falte entonces no se reconstruye hacia
atrás, ya que lo vendido lleva copiado lo que había (`DT-8`).

Lo que sostiene `INV-5` está aparte, en `tests_alergenos.py` (`TT-46`).
"""

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


# --- `TT-45`. La vista de gestión -------------------------------------------


class LaVistaDeGestionTest(BaseDeCatalogo):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.actor)

    def test_la_administracion_alcanza_las_tres_pantallas(self):
        for ruta in [
            "admin:catalogo_producto_changelist",
            "admin:catalogo_categoria_changelist",
            "admin:catalogo_alergeno_changelist",
        ]:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(reverse(ruta)).status_code, 200)

    def test_crea_un_producto_desde_el_admin_pasando_por_el_servicio(self):
        respuesta = self.client.post(
            reverse("admin:catalogo_producto_add"),
            {
                "nombre": "Pan de queso",
                "precio": "2500",
                "categoria": str(self.categoria.pk),
                "activo": "on",
                "alergenos_declarados": [str(self.lactosa.pk)],
                "porcion": "unidad de 80 g",
                "energia_kcal": "220",
            },
        )
        self.assertEqual(respuesta.status_code, 302)

        producto = Producto.objects.get(nombre="Pan de queso")
        self.assertEqual(producto.energia_kcal, 220)
        self.assertEqual([a.nombre for a in producto.alergenos.all()], ["Lactosa"])

    def test_edita_los_alergenos_desde_el_admin(self):
        producto = self.producto(alergenos=[self.lactosa])
        mani = Alergeno.objects.create(nombre="Maní")

        self.client.post(
            reverse("admin:catalogo_producto_change", args=[producto.pk]),
            {
                "nombre": producto.nombre,
                "precio": "2500",
                "categoria": str(self.categoria.pk),
                "activo": "on",
                "alergenos_declarados": [str(mani.pk)],
            },
        )

        self.assertEqual({a.nombre for a in producto.alergenos.all()}, {"Maní"})

    def test_no_ofrece_borrar_ninguno_de_los_tres(self):
        producto = self.producto()
        for ruta, argumentos in [
            ("admin:catalogo_producto_delete", [producto.pk]),
            ("admin:catalogo_categoria_delete", [self.categoria.pk]),
            ("admin:catalogo_alergeno_delete", [self.lactosa.pk]),
        ]:
            with self.subTest(ruta=ruta):
                self.assertEqual(
                    self.client.get(reverse(ruta, args=argumentos)).status_code, 403
                )

    def test_la_accion_de_retirar_pasa_por_el_servicio(self):
        producto = self.producto()

        self.client.post(
            reverse("admin:catalogo_producto_changelist"),
            {"action": "accion_retirar", "_selected_action": [str(producto.pk)]},
        )

        producto.refresh_from_db()
        self.assertFalse(producto.activo)


class ElCatalogoEsSoloDeLaCafeteriaTest(BaseDeCatalogo):
    """`[S11]`. Ni el cajero ni la institución educativa lo gestionan."""

    def test_ni_la_institucion_educativa_lo_ve(self):
        """El catálogo es de quien lo vende. `USR-5` no aparece en esa fila."""
        institucion = crear_cuenta(
            email="institucion@example.com",
            rol=Rol.INSTITUCION,
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.client.force_login(institucion)

        self.assertEqual(
            self.client.get(reverse("admin:catalogo_producto_changelist")).status_code,
            403,
        )

    def test_ni_el_cajero(self):
        cajero = crear_cuenta(
            email="cajero@example.com",
            rol=Rol.CAJERO,
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.client.force_login(cajero)

        self.assertEqual(
            self.client.get(reverse("admin:catalogo_producto_add")).status_code, 403
        )
