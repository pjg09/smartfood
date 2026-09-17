"""`TT-111` y `TT-112`. Consulta de restricciones por los cuatro roles (`HU-38`).

Los dos criterios de `HU-38`:

1. **Los cuatro roles de `[S11]` pueden consultar restricciones.** Cada uno por su
   interfaz: el acudiente en `INT-1`, el cajero al identificar en `INT-2` y la
   cafetería y la institución en `INT-3`. `LosCuatroRolesConsultanTest` recorre
   los cuatro caminos reales, no una tabla.
2. **Ninguno salvo el acudiente puede configurarlas ni retirarlas** (`HU-13`). Los
   servicios ya lo cumplen (`restricciones/tests_permisos.py`); lo que se
   comprueba aquí es que **la consulta nueva no abre un camino de escritura**: el
   proxy no tiene más permiso que `view` y el admin niega las tres escrituras.
"""

from decimal import Decimal

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from billetera.templatetags.dinero import dinero
from catalogo.models import Alergeno, Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from restricciones.admin import RestriccionesDelEstudianteAdmin
from restricciones.models import (
    LimiteDiario,
    RestriccionAlergeno,
    RestriccionesDelEstudiante,
    RestriccionProducto,
)
from restricciones.selectors import (
    estudiantes_con_sus_restricciones,
    restricciones_precargadas,
    restricciones_vigentes,
)
from restricciones.services import (
    bloquear_alergeno,
    bloquear_producto,
    fijar_limite_diario,
)
from ventas.selectors import informacion_de_cobro

LISTADO = "admin:restricciones_restriccionesdelestudiante_changelist"
FICHA = "admin:restricciones_restriccionesdelestudiante_change"
ALTA = "admin:restricciones_restriccionesdelestudiante_add"
BORRADO = "admin:restricciones_restriccionesdelestudiante_delete"


class BaseDeConsulta(TestCase):
    """Un estudiante con las tres restricciones puestas por su acudiente, y otro sin ninguna."""

    def setUp(self):
        sincronizar_grupos_y_permisos()

        self.usuario_acudiente = Usuario.objects.crear_usuario(
            email="acudiente-consulta@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
        )
        ficha = Acudiente.objects.create(
            usuario=self.usuario_acudiente, nombre="Marta Ruiz Ochoa", documento="9990077001"
        )
        self.estudiante = Estudiante.objects.create(
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1009977001",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        self.sin_nada = Estudiante.objects.create(
            nombre="Tomás Restrepo Ruiz",
            documento="1009977002",
            acudiente=ficha,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )

        categoria, _ = Categoria.objects.get_or_create(nombre="Prueba")
        self.producto, _ = Producto.objects.get_or_create(
            nombre="Gaseosa", defaults={"precio": Decimal("2500"), "categoria": categoria}
        )
        self.alergeno, _ = Alergeno.objects.get_or_create(nombre="Maní")

        fijar_limite_diario(
            actor=self.usuario_acudiente, estudiante=self.estudiante, monto=Decimal("8000")
        )
        bloquear_producto(
            actor=self.usuario_acudiente, estudiante=self.estudiante, producto=self.producto
        )
        bloquear_alergeno(
            actor=self.usuario_acudiente, estudiante=self.estudiante, alergeno=self.alergeno
        )

        self.administracion = crear_cuenta(
            email="administracion-consulta@example.com",
            rol=Rol.ADMINISTRADOR,
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.institucion = crear_cuenta(
            email="institucion-consulta@example.com",
            rol=Rol.INSTITUCION,
            accede_a_administracion=True,
            enviar_invitacion=False,
        )
        self.cajero = crear_cuenta(
            email="cajero-consulta@example.com", rol=Rol.CAJERO, enviar_invitacion=False
        )

    def cuentas_de_la_administracion(self):
        return {Rol.ADMINISTRADOR: self.administracion, Rol.INSTITUCION: self.institucion}

    def fotografia_de_las_tres(self):
        """Lo configurado, contado en la base. Para afirmar que no se movió nada."""
        return (
            LimiteDiario.objects.get(estudiante=self.estudiante).monto,
            RestriccionProducto.objects.filter(estudiante=self.estudiante).count(),
            RestriccionAlergeno.objects.filter(estudiante=self.estudiante).count(),
        )


# --- Criterio 1: los cuatro consultan --------------------------------------


class LosCuatroRolesConsultanTest(BaseDeConsulta):
    """Primer criterio de `HU-38`, por el camino real de cada rol."""

    def test_el_acudiente_en_su_panel(self):
        self.client.force_login(self.usuario_acudiente)

        respuesta = self.client.get(reverse("mis-estudiantes"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["seleccionado"], self.estudiante)
        self.assertEqual(respuesta.context["productos_bloqueados"], 1)
        self.assertEqual(respuesta.context["alergenos_bloqueados"], 1)

    def test_el_cajero_al_identificar(self):
        restricciones = informacion_de_cobro(
            actor=self.cajero, estudiante=self.estudiante
        ).restricciones

        self.assertTrue(restricciones.hay_alguna)
        self.assertEqual([r.alergeno for r in restricciones.alergenos], [self.alergeno])

    def test_la_cafeteria_y_la_institucion_en_la_administracion(self):
        for rol, cuenta in self.cuentas_de_la_administracion().items():
            with self.subTest(rol=rol):
                self.client.force_login(cuenta)

                listado = self.client.get(reverse(LISTADO))
                ficha = self.client.get(reverse(FICHA, args=[self.estudiante.pk]))

                self.assertEqual(listado.status_code, 200)
                self.assertIn(self.estudiante, listado.context["cl"].result_list)
                self.assertEqual(ficha.status_code, 200)

    def test_y_la_entrada_esta_en_el_indice_de_los_dos(self):
        """Una consulta a la que solo se llega sabiendo la URL no está habilitada."""
        for rol, cuenta in self.cuentas_de_la_administracion().items():
            with self.subTest(rol=rol):
                self.client.force_login(cuenta)
                indice = self.client.get(reverse("admin:index"))

                modelos = {
                    modelo["object_name"]
                    for app in indice.context["app_list"]
                    for modelo in app["models"]
                }
                self.assertIn("RestriccionesDelEstudiante", modelos)


class LaPuertaDeLaAdministracionTest(BaseDeConsulta):
    """`TT-111`. El selector de `INT-3` decide quién llega, no el admin."""

    def test_la_cafeteria_y_la_institucion_ven_a_todos(self):
        for rol, cuenta in self.cuentas_de_la_administracion().items():
            with self.subTest(rol=rol):
                self.assertEqual(
                    set(estudiantes_con_sus_restricciones(actor=cuenta)),
                    {self.estudiante, self.sin_nada},
                )

    def test_el_acudiente_y_el_cajero_no_pasan_por_aqui(self):
        """Consultan, pero por su interfaz: esta puerta no les amplía el alcance.

        Al acudiente le daría los estudiantes ajenos, y eso no lo concede
        `[S11]`: consulta los suyos (`estudiante_a_cargo`).
        """
        for cuenta in [self.usuario_acudiente, self.cajero]:
            with self.subTest(rol=cuenta.rol):
                with self.assertRaises(PermissionDenied):
                    estudiantes_con_sus_restricciones(actor=cuenta)

    def test_sin_identificarse_o_desactivado_no(self):
        with self.assertRaises(PermissionDenied):
            estudiantes_con_sus_restricciones(actor=None)

        self.administracion.is_active = False
        self.administracion.save(update_fields=["is_active"])
        with self.assertRaises(PermissionDenied):
            estudiantes_con_sus_restricciones(actor=self.administracion)

    def test_lo_precargado_dice_lo_mismo_que_el_selector_de_tt_106(self):
        """Dos lecturas de lo mismo que discreparan serían dos pantallas que se contradicen."""
        consulta = estudiantes_con_sus_restricciones(actor=self.institucion)

        for estudiante in [self.estudiante, self.sin_nada]:
            with self.subTest(estudiante=estudiante.nombre):
                precargadas = restricciones_precargadas(consulta.get(pk=estudiante.pk))
                directas = restricciones_vigentes(estudiante)

                self.assertEqual(precargadas.limite, directas.limite)
                self.assertEqual(list(precargadas.productos), list(directas.productos))
                self.assertEqual(list(precargadas.alergenos), list(directas.alergenos))
                self.assertEqual(precargadas.hay_alguna, directas.hay_alguna)

    def test_sin_limite_es_none_y_no_cero(self):
        consulta = estudiantes_con_sus_restricciones(actor=self.institucion)

        self.assertIsNone(restricciones_precargadas(consulta.get(pk=self.sin_nada.pk)).limite)

    def test_el_listado_no_cuesta_una_consulta_por_estudiante(self):
        """Tres consultas: estudiantes con su límite, productos y alérgenos.

        Se añaden estudiantes con restricciones y la cifra no cambia; con una
        lectura por fila crecería con el colegio.
        """
        def leer_todo():
            for estudiante in estudiantes_con_sus_restricciones(actor=self.institucion):
                vigentes = restricciones_precargadas(estudiante)
                _ = (vigentes.limite, [r.producto.nombre for r in vigentes.productos],
                     [r.alergeno.nombre for r in vigentes.alergenos])

        with self.assertNumQueries(3):
            leer_todo()

        for i in range(3):
            otro = Estudiante.objects.create(
                nombre=f"Estudiante extra {i}",
                documento=f"10099780{i}",
                acudiente=self.estudiante.acudiente,
                codigo_tarjeta=generar_codigo_de_tarjeta(),
            )
            bloquear_alergeno(
                actor=self.usuario_acudiente, estudiante=otro, alergeno=self.alergeno
            )

        with self.assertNumQueries(3):
            leer_todo()


# --- Criterio 2: nadie más que el acudiente escribe ------------------------


class LaConsultaNoAbreEscrituraTest(BaseDeConsulta):
    """Segundo criterio de `HU-38`, sobre la puerta que este PR abre."""

    def test_el_proxy_solo_tiene_permiso_de_consulta(self):
        """El permiso que no existe no se puede conceder por error (`DT-11`)."""
        codenames = set(
            Permission.objects.filter(
                content_type__app_label="restricciones",
                content_type__model="restriccionesdelestudiante",
            ).values_list("codename", flat=True)
        )

        self.assertEqual(codenames, {"view_restriccionesdelestudiante"})

    def test_ni_alta_ni_borrado_desde_el_admin(self):
        for rol, cuenta in self.cuentas_de_la_administracion().items():
            with self.subTest(rol=rol):
                self.client.force_login(cuenta)

                self.assertEqual(self.client.get(reverse(ALTA)).status_code, 403)
                self.assertEqual(
                    self.client.post(
                        reverse(BORRADO, args=[self.estudiante.pk]), {"post": "yes"}
                    ).status_code,
                    403,
                )
                self.assertTrue(Estudiante.objects.filter(pk=self.estudiante.pk).exists())

    def test_la_ficha_es_de_solo_lectura_y_un_post_no_mueve_nada(self):
        antes = self.fotografia_de_las_tres()

        for rol, cuenta in self.cuentas_de_la_administracion().items():
            with self.subTest(rol=rol):
                self.client.force_login(cuenta)
                url = reverse(FICHA, args=[self.estudiante.pk])

                ficha = self.client.get(url)
                self.assertFalse(ficha.context["has_change_permission"])

                intento = self.client.post(url, {"nombre": "Otro nombre"})
                self.assertEqual(intento.status_code, 403)

        self.assertEqual(self.fotografia_de_las_tres(), antes)
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.nombre, "Ana Sofía Restrepo Ruiz")

    def test_el_admin_niega_la_escritura_aunque_hubiera_permiso(self):
        """La segunda de las dos comprobaciones: el `ModelAdmin` no se fía de la matriz."""
        modelo_admin = RestriccionesDelEstudianteAdmin(RestriccionesDelEstudiante, None)
        peticion = type("Peticion", (), {"user": self.institucion})()

        self.assertFalse(modelo_admin.has_add_permission(peticion))
        self.assertFalse(modelo_admin.has_change_permission(peticion, self.estudiante))
        self.assertFalse(modelo_admin.has_delete_permission(peticion, self.estudiante))


class QuienNoConsultaEnLaAdministracionTest(BaseDeConsulta):
    """El acudiente y el cajero consultan, pero no por `INT-3`."""

    def test_sin_acceso_al_admin_se_les_manda_a_entrar(self):
        for cuenta in [self.usuario_acudiente, self.cajero]:
            with self.subTest(rol=cuenta.rol):
                self.client.force_login(cuenta)
                respuesta = self.client.get(reverse(LISTADO))

                self.assertEqual(respuesta.status_code, 302)
                self.assertIn(reverse("admin:login"), respuesta["Location"])

    def test_un_permiso_concedido_por_error_no_basta_sin_el_rol(self):
        """Se le da al cajero `is_staff` y el permiso a mano: el rol lo sigue parando."""
        self.cajero.is_staff = True
        self.cajero.save(update_fields=["is_staff"])
        self.cajero.user_permissions.add(
            Permission.objects.get(codename="view_restriccionesdelestudiante")
        )
        self.client.force_login(self.cajero)

        self.assertEqual(self.client.get(reverse(LISTADO)).status_code, 403)
        self.assertEqual(
            self.client.get(reverse(FICHA, args=[self.estudiante.pk])).status_code, 403
        )


class LoQueEnsenaLaAdministracionTest(BaseDeConsulta):
    """`TT-112`. Qué se ve, y sobre todo qué no."""

    def test_no_enseña_el_codigo_de_tarjeta_ni_el_documento(self):
        """El código es la credencial del saldo (`FUN-4`); el documento, un dato del menor."""
        self.client.force_login(self.administracion)

        for url in [reverse(LISTADO), reverse(FICHA, args=[self.estudiante.pk])]:
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                self.assertNotContains(respuesta, self.estudiante.codigo_tarjeta)
                self.assertNotContains(respuesta, self.estudiante.documento)
                self.assertNotContains(respuesta, self.estudiante.acudiente.documento)

    def test_el_documento_se_busca_solo_completo(self):
        """Buscar por subcadena permitiría recorrer documentos tecleando cifras."""
        self.client.force_login(self.administracion)

        completo = self.client.get(reverse(LISTADO), {"q": self.estudiante.documento})
        parcial = self.client.get(reverse(LISTADO), {"q": self.estudiante.documento[:5]})

        self.assertEqual(list(completo.context["cl"].result_list), [self.estudiante])
        self.assertEqual(list(parcial.context["cl"].result_list), [])

    def test_las_tres_restricciones_por_estudiante(self):
        modelo_admin = RestriccionesDelEstudianteAdmin(RestriccionesDelEstudiante, None)
        consulta = estudiantes_con_sus_restricciones(actor=self.administracion)
        con_todo = consulta.get(pk=self.estudiante.pk)
        sin_nada = consulta.get(pk=self.sin_nada.pk)

        self.assertEqual(modelo_admin.cupo_diario(con_todo), dinero(Decimal("8000")))
        self.assertIn(self.producto.nombre, modelo_admin.productos(con_todo))
        self.assertIn(self.alergeno.nombre, modelo_admin.alergenos(con_todo))

        # Sin límite no es un cupo de cero: son opuestos (`HU-61`).
        self.assertNotEqual(modelo_admin.cupo_diario(sin_nada), dinero(0))
        self.assertNotIn(self.producto.nombre, modelo_admin.productos(sin_nada))
        self.assertNotIn(self.alergeno.nombre, modelo_admin.alergenos(sin_nada))
