"""`DT-51`. Las categorías del catálogo, en `/categorias/`.

Lo que se sostiene aquí:

1. **Solo se elimina una categoría vacía**, contando los productos retirados.
   El servicio da el mensaje y la base, la garantía (`PROTECT`); la pantalla no
   pinta un botón que siempre fallaría.
2. **El nombre es único sin distinguir mayúsculas**: «bebidas» y «Bebidas»
   partirían en dos las alertas de `HU-31`.
3. **Solo la administración** la alcanza (`[S11]`), por la ruta.
"""

import uuid
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from catalogo.models import Categoria, Producto
from catalogo.selectors import categorias_del_catalogo
from catalogo.services import (
    crear_categoria,
    editar_categoria,
    eliminar_categoria,
    retirar_del_catalogo,
)
from cuentas.models import Rol
from cuentas.services import crear_cuenta


class BaseDeCategorias(TestCase):
    def setUp(self):
        self.actor = crear_cuenta(
            email="admin-categorias@example.com",
            rol=Rol.ADMINISTRADOR,
            nombre="Lucía Gómez",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.bebidas = crear_categoria(actor=self.actor, nombre="Bebidas", descripcion="Jugos y agua")
        self.vacia = crear_categoria(actor=self.actor, nombre="Postres")
        self.agua = Producto.objects.create(nombre="Agua", precio=Decimal("2000"), categoria=self.bebidas)
        self.client.force_login(self.actor)


class EliminarSoloLoVacioTest(BaseDeCategorias):
    def test_una_vacia_se_elimina(self):
        eliminar_categoria(actor=self.actor, categoria=self.vacia)

        self.assertFalse(Categoria.objects.filter(pk=self.vacia.pk).exists())

    def test_una_con_productos_no_y_no_toca_nada(self):
        with self.assertRaises(ValidationError):
            eliminar_categoria(actor=self.actor, categoria=self.bebidas)

        self.assertTrue(Categoria.objects.filter(pk=self.bebidas.pk).exists())
        self.assertEqual(Producto.objects.get().categoria, self.bebidas)

    def test_cuentan_tambien_los_retirados(self):
        """Un retirado sigue existiendo y tiene historial: no se queda sin grupo."""
        retirar_del_catalogo(actor=self.actor, producto=self.agua)

        with self.assertRaises(ValidationError):
            eliminar_categoria(actor=self.actor, categoria=self.bebidas)

    def test_la_base_lo_impide_aunque_se_salte_el_servicio(self):
        """La garantía no es el `if`: es el `PROTECT` de `Producto.categoria`."""
        with self.assertRaises(ProtectedError):
            self.bebidas.delete()

    def test_la_modal_no_pinta_el_boton_si_hay_productos(self):
        respuesta = self.client.get(reverse("eliminacion-de-categoria", args=[self.bebidas.pk]))

        self.assertContains(respuesta, 'data-eliminacion-de-categoria="bloqueada"')
        self.assertNotContains(respuesta, "data-confirmar-eliminacion")

    def test_la_modal_si_lo_pinta_si_esta_vacia_y_el_post_elimina(self):
        url = reverse("eliminacion-de-categoria", args=[self.vacia.pk])
        self.assertContains(self.client.get(url), "data-confirmar-eliminacion")

        respuesta = self.client.post(url)

        self.assertContains(respuesta, 'data-eliminacion-de-categoria="hecha"')
        self.assertEqual(respuesta["HX-Trigger"], "categorias-cambiado")
        self.assertFalse(Categoria.objects.filter(pk=self.vacia.pk).exists())

    def test_forzar_el_post_con_productos_vuelve_con_su_motivo(self):
        respuesta = self.client.post(reverse("eliminacion-de-categoria", args=[self.bebidas.pk]))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'role="alert"')
        self.assertNotIn("HX-Trigger", respuesta)
        self.assertTrue(Categoria.objects.filter(pk=self.bebidas.pk).exists())


class CrearYEditarTest(BaseDeCategorias):
    def test_crea_desde_la_modal_y_avisa_al_tablero(self):
        respuesta = self.client.post(
            reverse("categoria-nueva"), {"nombre": "  Frutas ", "descripcion": "De temporada"}
        )

        self.assertContains(respuesta, 'data-estado="creada"')
        self.assertEqual(respuesta["HX-Trigger"], "categorias-cambiado")
        self.assertEqual(Categoria.objects.get(nombre="Frutas").descripcion, "De temporada")

    def test_un_nombre_repetido_sin_distinguir_mayusculas_no_entra(self):
        respuesta = self.client.post(reverse("categoria-nueva"), {"nombre": "BEBIDAS"})

        self.assertContains(respuesta, "data-error-del-servidor")
        self.assertNotIn("HX-Trigger", respuesta)
        self.assertEqual(Categoria.objects.filter(nombre__iexact="bebidas").count(), 1)

    def test_sin_nombre_no_entra(self):
        respuesta = self.client.post(reverse("categoria-nueva"), {"nombre": "   "})

        self.assertContains(respuesta, "data-error-del-servidor")
        self.assertEqual(Categoria.objects.count(), 2)

    def test_editar_renombra_y_los_productos_siguen_en_ella(self):
        url = reverse("edicion-de-categoria", args=[self.bebidas.pk])

        respuesta = self.client.post(url, {"nombre": "Bebidas frías", "descripcion": ""})

        self.assertContains(respuesta, 'data-estado="guardada"')
        self.bebidas.refresh_from_db()
        self.assertEqual(self.bebidas.nombre, "Bebidas frías")
        self.assertEqual(self.bebidas.descripcion, "")
        self.assertEqual(Producto.objects.get().categoria, self.bebidas)

    def test_editar_sin_cambiar_el_nombre_no_choca_consigo_misma(self):
        respuesta = self.client.post(
            reverse("edicion-de-categoria", args=[self.bebidas.pk]),
            {"nombre": "Bebidas", "descripcion": "Otra"},
        )

        self.assertContains(respuesta, 'data-estado="guardada"')

    def test_la_edicion_avisa_de_que_renombrar_alcanza_a_lo_vendido(self):
        """La línea de venta no copia la categoría: decirlo es lo honesto."""
        respuesta = self.client.get(reverse("edicion-de-categoria", args=[self.bebidas.pk]))

        self.assertContains(respuesta, "data-aviso-de-renombrar")


class ElTableroTest(BaseDeCategorias):
    def test_cuenta_productos_y_en_uso(self):
        categorias = {c.nombre: c.cuantos for c in categorias_del_catalogo(actor=self.actor)}

        self.assertEqual(categorias, {"Bebidas": 1, "Postres": 0})

    def test_la_pantalla_se_repinta_tras_escribir(self):
        respuesta = self.client.get(reverse("categorias"))

        self.assertEqual(respuesta.context["en_uso"], 1)
        self.assertContains(
            respuesta,
            f'hx-get="{reverse("tablero-de-categorias")}" hx-trigger="categorias-cambiado from:body"',
        )

    def test_el_tablero_es_un_fragmento(self):
        respuesta = self.client.get(reverse("tablero-de-categorias"))

        self.assertNotContains(respuesta, "<html")
        self.assertContains(respuesta, 'data-cuantos-productos="1"')

    def test_ya_no_esta_en_el_admin(self):
        with self.assertRaises(NoReverseMatch):
            reverse("admin:catalogo_categoria_changelist")


class SoloLaAdministracionTest(BaseDeCategorias):
    def rutas(self):
        return [
            ("get", reverse("categorias")),
            ("get", reverse("tablero-de-categorias")),
            ("get", reverse("categoria-nueva")),
            ("post", reverse("categoria-nueva")),
            ("get", reverse("edicion-de-categoria", args=[self.vacia.pk])),
            ("post", reverse("eliminacion-de-categoria", args=[self.vacia.pk])),
        ]

    def test_ningun_otro_rol(self):
        for rol in (Rol.CAJERO, Rol.INSTITUCION, Rol.ACUDIENTE):
            self.client.force_login(
                crear_cuenta(email=f"{rol}-cat@example.com", rol=rol, enviar_invitacion=False)
            )
            for metodo, url in self.rutas():
                with self.subTest(rol=rol, url=url, metodo=metodo):
                    self.assertEqual(getattr(self.client, metodo)(url).status_code, 403)
        self.assertTrue(Categoria.objects.filter(pk=self.vacia.pk).exists())

    def test_los_servicios_tambien_lo_exigen(self):
        cajero = crear_cuenta(email="cajero-cat@example.com", rol=Rol.CAJERO, enviar_invitacion=False)
        for llamada in (
            lambda: editar_categoria(actor=cajero, categoria=self.vacia, nombre="X"),
            lambda: eliminar_categoria(actor=cajero, categoria=self.vacia),
        ):
            with self.assertRaises(PermissionDenied):
                llamada()

    def test_una_que_no_existe_no_le_dice_a_otro_rol_que_no_existe(self):
        self.client.force_login(
            crear_cuenta(email="cajero-x-cat@example.com", rol=Rol.CAJERO, enviar_invitacion=False)
        )

        respuesta = self.client.get(reverse("edicion-de-categoria", args=[uuid.uuid4()]))

        self.assertEqual(respuesta.status_code, 403)
