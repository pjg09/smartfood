"""`DEC-26`, `DT-52`. Los alérgenos del catálogo, en `/alergenos/`.

Lo que se sostiene aquí:

1. **Un alérgeno no se elimina, ni vacío.** No hay ruta, ni botón, ni servicio;
   y el admin, que tampoco lo dejaba, ya no lo tiene registrado.
2. **El nombre es único sin distinguir mayúsculas, y lo impone la base**:
   «Maní» y «maní» serían dos condiciones, y el bloqueo de una no alcanzaría al
   producto que declara la otra.
3. **Renombrar no cambia a quién protege**: el bloqueo sigue al alérgeno, el
   historial conserva el nombre de entonces, y la modal lo dice antes con las
   dos cifras.
4. **Solo la administración** la alcanza (`[S11]`), por la ruta y por el servicio.
"""

import uuid
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from catalogo import services
from catalogo.models import Alergeno, Categoria, Producto, ProductoAlergeno
from catalogo.selectors import alergenos_del_catalogo
from catalogo.services import crear_alergeno, editar_alergeno, retirar_del_catalogo
from cuentas.models import Rol
from cuentas.services import crear_cuenta
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from restricciones.models import AsientoDeRestriccion
from restricciones.selectors import alergenos_que_bloquean
from restricciones.services import bloquear_alergeno


class BaseDeAlergenos(TestCase):
    def setUp(self):
        self.actor = crear_cuenta(
            email="admin-alergenos@example.com",
            rol=Rol.ADMINISTRADOR,
            nombre="Lucía Gómez",
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.mani = crear_alergeno(actor=self.actor, nombre="Maní")
        self.sesamo = crear_alergeno(actor=self.actor, nombre="Sésamo")
        categoria = Categoria.objects.create(nombre="Snacks")
        self.galleta = Producto.objects.create(
            nombre="Galleta de maní", precio=Decimal("2500"), categoria=categoria
        )
        ProductoAlergeno.objects.create(producto=self.galleta, alergeno=self.mani)

        self.acudiente = crear_cuenta(
            email="acudiente-alergenos@example.com",
            rol=Rol.ACUDIENTE,
            nombre="Marta",
            enviar_invitacion=False,
        )
        ficha = Acudiente.objects.create(
            usuario=self.acudiente, nombre="Marta Ruiz Ochoa", documento="63519876"
        )
        self.estudiante = Estudiante.objects.create(
            nombre="Tomás Ruiz",
            documento="1001234567",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        bloquear_alergeno(actor=self.acudiente, estudiante=self.estudiante, alergeno=self.mani)

        self.client.force_login(self.actor)


class NoSeEliminaTest(BaseDeAlergenos):
    def test_no_hay_servicio_que_borre(self):
        self.assertFalse(
            [nombre for nombre in services.__all__ if "alergeno" in nombre and "eliminar" in nombre]
        )
        self.assertFalse(hasattr(services, "eliminar_alergeno"))

    def test_no_hay_ruta_de_eliminar(self):
        for nombre in ("eliminacion-de-alergeno", "admin:catalogo_alergeno_delete"):
            with self.subTest(nombre=nombre), self.assertRaises(NoReverseMatch):
                reverse(nombre, args=[self.sesamo.pk])

    def test_ni_el_vacio_ofrece_eliminar(self):
        """`Sésamo` no lo declara nadie ni lo bloquea nadie, y aun así no."""
        tablero = self.client.get(reverse("tablero-de-alergenos")).content.decode()
        ficha = self.client.get(reverse("edicion-de-alergeno", args=[self.sesamo.pk])).content.decode()

        for cuerpo in (tablero, ficha):
            self.assertNotIn("eliminar", cuerpo.lower())
            self.assertNotIn("i-papelera", cuerpo)

    def test_la_base_lo_impide_si_alguien_lo_bloquea(self):
        with self.assertRaises(ProtectedError):
            self.mani.delete()
        self.assertTrue(Alergeno.objects.filter(pk=self.mani.pk).exists())

    def test_ya_no_esta_en_el_admin(self):
        with self.assertRaises(NoReverseMatch):
            reverse("admin:catalogo_alergeno_changelist")


class NombreUnicoTest(BaseDeAlergenos):
    def test_la_base_rechaza_el_mismo_nombre_con_otras_mayusculas(self):
        """La garantía no es el formulario: es la `UniqueConstraint` sobre `Lower`."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Alergeno.objects.create(nombre="MANÍ")

    def test_la_modal_lo_dice_junto_al_campo(self):
        respuesta = self.client.post(reverse("alergeno-nuevo"), {"nombre": "  maní "})

        self.assertContains(respuesta, "data-error-del-servidor")
        self.assertNotIn("HX-Trigger", respuesta)
        self.assertEqual(Alergeno.objects.filter(nombre__iexact="maní").count(), 1)

    def test_renombrar_a_uno_que_ya_existe_tampoco(self):
        respuesta = self.client.post(
            reverse("edicion-de-alergeno", args=[self.sesamo.pk]), {"nombre": "maní"}
        )

        self.assertContains(respuesta, "data-error-del-servidor")
        self.sesamo.refresh_from_db()
        self.assertEqual(self.sesamo.nombre, "Sésamo")

    def test_editar_sin_cambiar_el_nombre_no_choca_consigo_mismo(self):
        respuesta = self.client.post(
            reverse("edicion-de-alergeno", args=[self.mani.pk]), {"nombre": "Maní"}
        )

        self.assertContains(respuesta, 'data-estado="guardado"')


class CrearYRenombrarTest(BaseDeAlergenos):
    def test_crea_desde_la_modal_y_avisa_al_tablero(self):
        respuesta = self.client.post(reverse("alergeno-nuevo"), {"nombre": "  Mostaza "})

        self.assertContains(respuesta, 'data-estado="creado"')
        self.assertEqual(respuesta["HX-Trigger"], "alergenos-cambiado")
        self.assertTrue(Alergeno.objects.filter(nombre="Mostaza").exists())

    def test_sin_nombre_no_entra(self):
        respuesta = self.client.post(reverse("alergeno-nuevo"), {"nombre": "   "})

        self.assertContains(respuesta, "data-error-del-servidor")
        self.assertEqual(Alergeno.objects.count(), 2)

    def test_la_ficha_de_ida_y_vuelta_guarda_lo_mismo(self):
        """Se devuelve tal cual lo que pinta (`[S4]` de `escribir-pruebas.md`)."""
        url = reverse("edicion-de-alergeno", args=[self.mani.pk])
        pintado = self.client.get(url).context["formulario"]["nombre"].value()

        respuesta = self.client.post(url, {"nombre": pintado})

        self.assertContains(respuesta, 'data-estado="guardado"')
        self.mani.refresh_from_db()
        self.assertEqual(self.mani.nombre, "Maní")

    def test_renombrar_no_cambia_a_quien_protege(self):
        """El bloqueo sigue al alérgeno (`INV-5`), y el historial conserva el
        nombre que vio el acudiente al bloquear (`DT-8`)."""
        respuesta = self.client.post(
            reverse("edicion-de-alergeno", args=[self.mani.pk]), {"nombre": "Cacahuate"}
        )

        self.assertContains(respuesta, 'data-estado="guardado"')
        self.assertEqual(respuesta["HX-Trigger"], "alergenos-cambiado")
        self.assertEqual(
            [a.nombre for a in alergenos_que_bloquean(self.estudiante, self.galleta)],
            ["Cacahuate"],
        )
        self.assertEqual(
            AsientoDeRestriccion.objects.get(estudiante=self.estudiante).nombre, "Maní"
        )

    def test_la_edicion_avisa_con_las_dos_cifras(self):
        respuesta = self.client.get(reverse("edicion-de-alergeno", args=[self.mani.pk]))

        self.assertContains(respuesta, "data-aviso-de-renombrar")
        self.assertContains(respuesta, 'data-aviso-productos="1"')
        self.assertContains(respuesta, 'data-aviso-estudiantes="1"')

    def test_el_alta_no_lleva_el_aviso(self):
        self.assertNotContains(self.client.get(reverse("alergeno-nuevo")), "data-aviso-de-renombrar")


class ElTableroTest(BaseDeAlergenos):
    def test_cuenta_productos_y_estudiantes_sin_multiplicarlos(self):
        """Dos `JOIN` en la misma consulta: sin `distinct`, cada cifra saldría
        multiplicada por la otra. Con dos productos y un bloqueo, el bloqueo
        saldría dos veces."""
        otra = Producto.objects.create(
            nombre="Barra de maní", precio=Decimal("3000"), categoria=self.galleta.categoria
        )
        ProductoAlergeno.objects.create(producto=otra, alergeno=self.mani)

        cifras = {
            a.nombre: (a.cuantos_productos, a.cuantos_estudiantes)
            for a in alergenos_del_catalogo(actor=self.actor)
        }

        self.assertEqual(cifras, {"Maní": (2, 1), "Sésamo": (0, 0)})

    def test_cuentan_tambien_los_retirados(self):
        retirar_del_catalogo(actor=self.actor, producto=self.galleta)

        mani = alergenos_del_catalogo(actor=self.actor)[0]

        self.assertEqual(mani.cuantos_productos, 1)

    def test_la_pantalla_se_repinta_tras_escribir(self):
        respuesta = self.client.get(reverse("alergenos"))

        self.assertEqual(respuesta.context["declarados"], 1)
        self.assertContains(
            respuesta,
            f'hx-get="{reverse("tablero-de-alergenos")}" hx-trigger="alergenos-cambiado from:body"',
        )

    def test_el_tablero_es_un_fragmento(self):
        respuesta = self.client.get(reverse("tablero-de-alergenos"))

        self.assertNotContains(respuesta, "<html")
        self.assertContains(respuesta, 'data-cuantos-productos="1"')
        self.assertContains(respuesta, 'data-cuantos-estudiantes="1"')

    def test_esta_en_el_menu_de_la_administracion(self):
        self.assertContains(self.client.get(reverse("inventario")), f'href="{reverse("alergenos")}"')


class SoloLaAdministracionTest(BaseDeAlergenos):
    def rutas(self):
        return [
            ("get", reverse("alergenos")),
            ("get", reverse("tablero-de-alergenos")),
            ("get", reverse("alergeno-nuevo")),
            ("post", reverse("alergeno-nuevo")),
            ("get", reverse("edicion-de-alergeno", args=[self.sesamo.pk])),
            ("post", reverse("edicion-de-alergeno", args=[self.sesamo.pk])),
        ]

    def test_ningun_otro_rol(self):
        for rol in (Rol.CAJERO, Rol.INSTITUCION, Rol.ACUDIENTE):
            self.client.force_login(
                crear_cuenta(email=f"{rol}-al@example.com", rol=rol, enviar_invitacion=False)
            )
            for metodo, url in self.rutas():
                with self.subTest(rol=rol, url=url, metodo=metodo):
                    respuesta = getattr(self.client, metodo)(url, {"nombre": "Intruso"})
                    self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(Alergeno.objects.filter(nombre="Intruso").exists())
        self.sesamo.refresh_from_db()
        self.assertEqual(self.sesamo.nombre, "Sésamo")

    def test_los_servicios_tambien_lo_exigen(self):
        cajero = crear_cuenta(email="cajero-al@example.com", rol=Rol.CAJERO, enviar_invitacion=False)
        for llamada in (
            lambda: crear_alergeno(actor=cajero, nombre="X"),
            lambda: editar_alergeno(actor=cajero, alergeno=self.sesamo, nombre="X"),
        ):
            with self.assertRaises(PermissionDenied):
                llamada()

    def test_uno_que_no_existe_no_le_dice_a_otro_rol_que_no_existe(self):
        self.client.force_login(
            crear_cuenta(email="cajero-x-al@example.com", rol=Rol.CAJERO, enviar_invitacion=False)
        )

        respuesta = self.client.get(reverse("edicion-de-alergeno", args=[uuid.uuid4()]))

        self.assertEqual(respuesta.status_code, 403)

    def test_uno_que_no_existe_da_404_a_la_administracion(self):
        respuesta = self.client.get(reverse("edicion-de-alergeno", args=[uuid.uuid4()]))

        self.assertEqual(respuesta.status_code, 404)
