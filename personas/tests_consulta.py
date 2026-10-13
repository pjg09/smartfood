"""`DT-43`. La ficha del estudiante en solo lectura, al pulsar su fila del padrón.

Lo que se vigila:

1. **Solo la institución**, por el mismo selector que la ficha de edición.
2. **Solo lee**: responde a `GET` y a nada más, y no trae ningún campo.
3. **Enseña lo que la institución ya podía ver**: foto, datos, código, acudiente
   y restricciones (`HU-38`).
4. **Y nada de lo que `[S11]` no le concede**: ni el saldo ni los consumos.
5. **Es un fragmento** (`DT-16`), y cada fila del padrón lleva el control que lo pide.
"""

import inspect
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from billetera.services import recargar
from billetera.templatetags.dinero import dinero
from catalogo.models import Alergeno, Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from personas import views
from personas.models import Acudiente
from personas.services import (
    crear_estudiante,
    dar_de_alta_la_institucion,
    dar_de_baja,
    desactivar,
    reactivar,
)
from personas.tests_fotografia import EN_MEMORIA
from restricciones.services import (
    bloquear_alergeno,
    bloquear_producto,
    fijar_limite_diario,
)

CLAVE = "clave-de-prueba-2026"


@override_settings(STORAGES=EN_MEMORIA)
class BaseDeConsulta(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo=CLAVE,
            )
        self.actor = institucion.usuario

        cuenta = crear_cuenta(
            email="marta.ruiz@example.com",
            rol=Rol.ACUDIENTE,
            nombre="Marta Ruiz Ochoa",
            enviar_invitacion=False,
        )
        self.acudiente = Acudiente.objects.create(
            usuario=cuenta, nombre="Marta Ruiz Ochoa", documento="43512345"
        )
        self.estudiante = crear_estudiante(
            actor=self.actor,
            nombre="Ana Sofía Restrepo Ruiz",
            documento="1001234501",
            acudiente=self.acudiente,
        )
        self.url = reverse("consulta-del-estudiante", args=[self.estudiante.pk])
        self.client.force_login(self.actor)

    def cuerpo(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.content.decode()


class SoloLaInstitucionConsultaTest(BaseDeConsulta):
    def test_la_institucion_la_abre(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_ningun_otro_rol_la_abre(self):
        for rol in [Rol.ACUDIENTE, Rol.CAJERO, Rol.ADMINISTRADOR]:
            with self.subTest(rol=rol):
                otro = Usuario.objects.crear_usuario(
                    email=f"{rol}@example.com", rol=rol, nombre="Otro"
                )
                self.client.force_login(otro)
                self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_ni_el_acudiente_sobre_su_propio_hijo(self):
        self.client.force_login(self.acudiente.usuario)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_sin_sesion_va_a_la_pantalla_de_acceso(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_un_estudiante_que_no_existe_es_un_404(self):
        url = reverse("consulta-del-estudiante", args=["01900000-0000-7000-8000-000000000000"])
        self.assertEqual(self.client.get(url).status_code, 404)


class SoloLeeTest(BaseDeConsulta):
    def test_no_admite_escribir(self):
        respuesta = self.client.post(self.url, {"nombre": "Cambiado"})
        self.assertEqual(respuesta.status_code, 405)
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.nombre, "Ana Sofía Restrepo Ruiz")

    def test_no_trae_ningun_campo(self):
        cuerpo = self.cuerpo()
        self.assertNotIn("<form", cuerpo)
        self.assertNotIn("<input", cuerpo)
        self.assertNotIn("<textarea", cuerpo)
        self.assertNotIn("<select", cuerpo)

    def test_contraprueba_la_ficha_de_edicion_si_los_trae(self):
        """Sin esto, una búsqueda mal escrita pasaría la prueba de arriba sola."""
        edicion = self.client.get(reverse("ficha-del-estudiante", args=[self.estudiante.pk]))
        cuerpo = edicion.content.decode()
        self.assertIn("<form", cuerpo)
        self.assertIn("<input", cuerpo)

    def test_editar_pide_la_ficha_de_edicion(self):
        self.assertIn(
            f'hx-get="{reverse("ficha-del-estudiante", args=[self.estudiante.pk])}"',
            self.cuerpo(),
        )


class EnsenaLoQueLaInstitucionYaVeiaTest(BaseDeConsulta):
    def test_los_datos_del_estudiante_y_de_su_acudiente(self):
        cuerpo = self.cuerpo()
        for dato in [
            self.estudiante.nombre,
            self.estudiante.documento,
            self.estudiante.codigo_tarjeta,
            self.acudiente.nombre,
            self.acudiente.usuario.email,
        ]:
            with self.subTest(dato=dato):
                self.assertIn(dato, cuerpo)
        self.assertIn(reverse("tarjeta-del-estudiante", args=[self.estudiante.pk]), cuerpo)

    def test_la_foto_si_la_tiene_y_la_inicial_si_no(self):
        self.assertNotIn("data-foto-de-la-consulta", self.cuerpo())
        self.estudiante.foto_clave = "estudiantes/ana.webp"
        self.estudiante.save(update_fields=["foto_clave"])
        self.assertIn("data-foto-de-la-consulta", self.cuerpo())

    def test_las_tres_restricciones(self):
        self.assertIn("data-consulta-sin-restricciones", self.cuerpo())

        mani, _ = Alergeno.objects.get_or_create(nombre="Maní")
        categoria, _ = Categoria.objects.get_or_create(nombre="Prueba")
        gaseosa = Producto.objects.create(
            nombre="Gaseosa de prueba", precio=Decimal("3000"), categoria=categoria
        )
        usuario = self.acudiente.usuario
        bloquear_alergeno(actor=usuario, estudiante=self.estudiante, alergeno=mani)
        bloquear_producto(actor=usuario, estudiante=self.estudiante, producto=gaseosa)
        fijar_limite_diario(actor=usuario, estudiante=self.estudiante, monto=Decimal("8000"))

        respuesta = self.client.get(self.url)
        cuerpo = respuesta.content.decode()
        self.assertNotIn("data-consulta-sin-restricciones", cuerpo)
        self.assertTrue(respuesta.context["restricciones"].hay_alguna)
        self.assertEqual(
            [r.alergeno for r in respuesta.context["restricciones"].alergenos], [mani]
        )
        self.assertEqual(
            [r.producto for r in respuesta.context["restricciones"].productos], [gaseosa]
        )
        self.assertIn(dinero(Decimal("8000")), cuerpo)

    def test_los_hermanos_sin_el_propio(self):
        crear_estudiante(
            actor=self.actor,
            nombre="Tomás Restrepo Ruiz",
            documento="1001234502",
            acudiente=self.acudiente,
        )
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.context["hermanos"], ["Tomás Restrepo Ruiz"])

    def test_el_estado_dicho_entero(self):
        self.assertIn("data-consulta-activo", self.cuerpo())

        desactivar(actor=self.actor, estudiante=self.estudiante)
        self.assertIn("data-consulta-desactivado", self.cuerpo())

        reactivar(actor=self.actor, estudiante=self.estudiante)
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)
        self.assertIn("data-consulta-retirado", self.cuerpo())

    def test_el_acceso_cortado_del_acudiente(self):
        usuario = self.acudiente.usuario
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        self.assertIn("data-consulta-acceso-cortado", self.cuerpo())


class NadaQueS11NoLeConcedaTest(BaseDeConsulta):
    """En `[S11]`, «Consultar saldo de un estudiante» es `–` para la institución."""

    MONTO = Decimal("48700")

    def test_el_saldo_no_aparece(self):
        recargar(actor=self.acudiente.usuario, estudiante=self.estudiante, monto=self.MONTO)
        self.assertNotIn(dinero(self.MONTO), self.cuerpo())
        self.assertNotIn(dinero(self.MONTO, "COP"), self.cuerpo())

    def test_contraprueba_el_monto_se_buscaria_bien_escrito(self):
        """La búsqueda de arriba encuentra el monto cuando sí está en la página."""
        fijar_limite_diario(
            actor=self.acudiente.usuario, estudiante=self.estudiante, monto=self.MONTO
        )
        self.assertIn(dinero(self.MONTO), self.cuerpo())

    def test_la_vista_no_lee_billetera_ni_reportes(self):
        """Sobre el bytecode y no el fuente: el docstring nombra lo que no usa."""
        usados = inspect.unwrap(views.consulta_del_estudiante).__code__.co_names
        for ajeno in ["saldo_de", "historial_de", "historial_de_consumo", "pedidos_pendientes_de"]:
            with self.subTest(ajeno=ajeno):
                self.assertNotIn(ajeno, usados)
        # Contraprueba: sí lee lo que enseña.
        self.assertIn("restricciones_vigentes", usados)


class EsUnFragmentoYLaFilaLoPideTest(BaseDeConsulta):
    def test_no_es_una_pagina(self):
        cuerpo = self.cuerpo()
        self.assertIn("data-consulta-del-estudiante", cuerpo)
        self.assertNotIn("<html", cuerpo)

    def test_cada_fila_del_padron_lleva_el_control(self):
        cuerpo = self.client.get(reverse("padron-tabla")).content.decode()
        # Dos: la tabla de escritorio y la ficha de móvil.
        self.assertEqual(cuerpo.count(f'hx-get="{self.url}"'), 2)
        self.assertEqual(cuerpo.count("data-consultar-estudiante"), 2)
