"""`TT-46`. El alérgeno se **relaciona**, no se copia como lista de productos.

Esta es la prueba que el plan sitúa en `PR-21` con una instrucción explícita: si
el alérgeno se modela como una lista materializada de productos bloqueados, **el
PR se rechaza aunque las demás pruebas pasen**.

`INV-5` dice que el bloqueo se aplica sobre la **condición**. El segundo criterio
de `HU-11` explica qué significa eso en la práctica: «un producto incorporado al
catálogo **después** de configurado el bloqueo queda cubierto automáticamente si
declara ese alérgeno». Una lista guardada se calcula una vez; una relación se
evalúa cada vez.

**La restricción por estudiante es `HU-11`, del Sprint 3, y todavía no existe.**
Lo que se prueba aquí es lo que hace posible aquello: que la consulta sea una
consulta, que la respuesta cambie sola cuando cambia el catálogo, y que **no haya
en ninguna parte un sitio donde guardar la lista**.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import TestCase

from catalogo.models import Alergeno, Categoria, Producto, ProductoAlergeno
from catalogo.selectors import productos_con_alergeno
from catalogo.services import crear_producto, declarar_alergenos
from cuentas.models import Rol
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos


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
        self.mani = Alergeno.objects.create(nombre="Maní")

    def producto(self, nombre="Pan de queso", alergenos=(), **extra):
        return crear_producto(
            actor=self.actor,
            nombre=nombre,
            precio=Decimal("2500"),
            categoria=self.categoria,
            alergenos=alergenos,
            **extra,
        )


class ElAlergenoEsUnaCondicionYNoUnaListaTest(BaseDeCatalogo):
    """El corazón de `TT-46`."""

    def test_un_producto_agregado_despues_queda_cubierto_solo(self):
        """Segundo criterio de `HU-11`, que es lo que `INV-5` protege.

        Se consulta **antes** de que el producto exista, para que la consulta ya
        haya ocurrido una vez, y se vuelve a consultar después sin tocar nada.
        """
        self.producto("Pan de queso", alergenos=[self.lactosa])
        self.assertEqual(productos_con_alergeno(self.lactosa).count(), 1)

        # La cafetería agrega un producto nuevo. Nadie recalcula nada.
        self.producto("Torta de leche", alergenos=[self.lactosa])

        cubiertos = {p.nombre for p in productos_con_alergeno(self.lactosa)}
        self.assertEqual(cubiertos, {"Pan de queso", "Torta de leche"})

    def test_la_respuesta_es_una_consulta_y_no_un_valor_guardado(self):
        """Un `QuerySet` sin evaluar: se resuelve cuando se pregunta.

        Si esto devolviera una lista, la habría calculado alguien en algún
        momento, y el momento sería el problema.
        """
        from django.db.models import QuerySet

        self.assertIsInstance(productos_con_alergeno(self.lactosa), QuerySet)

    def test_no_existe_donde_guardar_la_lista(self):
        """La prueba estructural: `INV-5` en la forma del modelo.

        Si mañana alguien añade a `Alergeno` un campo con los productos
        bloqueados, o a `Producto` uno con los alérgenos copiados como texto,
        esto falla antes de que llegue a la venta.
        """
        del_alergeno = {c.name for c in Alergeno._meta.get_fields()}
        self.assertEqual(
            del_alergeno & {"productos_bloqueados", "productos_afectados", "bloqueados"},
            set(),
        )

        # Lo único que `Alergeno` conoce de los productos es la relación inversa.
        self.assertIn("declaraciones", del_alergeno)

        del_producto = {c.name for c in Producto._meta.get_fields()}
        self.assertEqual(
            del_producto & {"alergenos_texto", "alergenos_copiados", "lista_alergenos"},
            set(),
        )

    def test_el_cruce_pasa_por_la_tabla_de_relacion(self):
        """`DT-7`: dos tablas, y el rechazo de `HU-18` es un cruce entre ellas."""
        producto = self.producto(alergenos=[self.lactosa])

        declaracion = ProductoAlergeno.objects.get(producto=producto)
        self.assertEqual(declaracion.alergeno, self.lactosa)
        self.assertEqual(ProductoAlergeno.objects.count(), 1)

    def test_retirar_la_declaracion_deja_de_cubrirlo_al_instante(self):
        """La otra mitad: si el producto deja de llevarlo, deja de estar cubierto.

        Con una lista guardada habría que acordarse de recalcularla; aquí no hay
        nada que recalcular.
        """
        producto = self.producto(alergenos=[self.lactosa])
        self.assertEqual(productos_con_alergeno(self.lactosa).count(), 1)

        declarar_alergenos(actor=self.actor, producto=producto, alergenos=[])

        self.assertEqual(productos_con_alergeno(self.lactosa).count(), 0)

    def test_un_alergeno_sin_productos_no_es_un_error(self):
        self.assertEqual(productos_con_alergeno(self.mani).count(), 0)

    def test_un_producto_declara_varios(self):
        producto = self.producto(alergenos=[self.lactosa, self.mani])

        self.assertEqual(producto.alergenos.count(), 2)
        self.assertIn(producto, productos_con_alergeno(self.lactosa))
        self.assertIn(producto, productos_con_alergeno(self.mani))

    def test_no_se_declara_dos_veces_el_mismo(self):
        """Lo impone la base, no un `if` (`DT-15`)."""
        producto = self.producto(alergenos=[self.lactosa])

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductoAlergeno.objects.create(
                    producto=producto, alergeno=self.lactosa
                )

    def test_declarar_reemplaza_y_no_acumula(self):
        producto = self.producto(alergenos=[self.lactosa])
        declarar_alergenos(actor=self.actor, producto=producto, alergenos=[self.mani])

        self.assertEqual(
            {a.nombre for a in producto.alergenos.all()}, {"Maní"}
        )

    def test_borrar_un_alergeno_con_declaraciones_esta_protegido(self):
        """Borrarlo se llevaría por delante el bloqueo que protege a un alérgico."""
        self.producto(alergenos=[self.lactosa])

        with self.assertRaises(Exception):
            with transaction.atomic():
                self.lactosa.delete()


class ElCatalogoNoConfiguraBloqueosTest(BaseDeCatalogo):
    """`INV-4`, visto desde el catálogo.

    Declarar que un producto lleva lactosa **no bloquea nada**: el bloqueo lo
    configura el acudiente sobre el alérgeno (`HU-11`). Y al revés, retirar una
    declaración no desbloquea a nadie. La cafetería no puede tocar las
    restricciones ni queriendo, porque este dominio no escribe en esa tabla.
    """

    def test_el_catalogo_no_tiene_acceso_a_ninguna_restriccion(self):
        from catalogo import services

        fuente = (services.__doc__ or "") + " ".join(dir(services))
        self.assertNotIn("restriccion", fuente.lower())

    def test_la_matriz_no_le_da_al_administrador_ninguna_restriccion(self):
        from cuentas.permisos import PERMISOS_POR_ROL

        for etiqueta in PERMISOS_POR_ROL[Rol.ADMINISTRADOR]:
            self.assertTrue(etiqueta.startswith("catalogo."), etiqueta)
            self.assertNotIn("restriccion", etiqueta)


class SoloLaAdministracionGestionaElCatalogoTest(BaseDeCatalogo):
    """Tercer criterio de `HU-26`."""

    def test_ningun_otro_rol_crea_productos(self):
        for rol in [Rol.CAJERO, Rol.INSTITUCION, Rol.ACUDIENTE]:
            with self.subTest(rol=rol):
                otro = crear_cuenta(
                    email=f"{rol}@example.com", rol=rol, enviar_invitacion=False
                )
                with self.assertRaises(PermissionDenied):
                    crear_producto(
                        actor=otro,
                        nombre=f"Producto de {rol}",
                        precio=Decimal("1000"),
                        categoria=self.categoria,
                    )

    def test_ni_declara_alergenos(self):
        producto = self.producto()
        cajero = crear_cuenta(
            email="cajero@example.com", rol=Rol.CAJERO, enviar_invitacion=False
        )

        with self.assertRaises(PermissionDenied):
            declarar_alergenos(
                actor=cajero, producto=producto, alergenos=[self.lactosa]
            )

    def test_una_cuenta_desactivada_no_gestiona(self):
        self.actor.is_active = False
        self.actor.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            self.producto()
