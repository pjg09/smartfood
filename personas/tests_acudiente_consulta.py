"""`DT-44`. La ficha del acudiente en solo lectura, y los retirados de la lista.

Lo que se vigila:

1. **Solo la institución** consulta a un acudiente, y la ficha **solo lee**.
2. **Trae a sus estudiantes, retirados incluidos**, y nada de su saldo (`[S11]`).
3. **Una familia que se fue no sale por defecto**, y sí con «Ver retirados». No
   son retirados el acceso cortado (`DEC-20`) ni el acudiente sin estudiantes.
4. **El acceso cortado se ve como tal**, en esta lista y en el padrón: cortarlo
   no borra la contraseña, y preguntando solo por ella se pintaba «Activa».
"""

import inspect
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from billetera.services import recargar
from billetera.templatetags.dinero import dinero
from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from personas import views
from personas.models import Acudiente
from personas.selectors import acudientes_de_la_institucion
from personas.services import crear_estudiante, dar_de_alta_la_institucion, dar_de_baja

CLAVE = "clave-de-prueba-2026"


class BaseDeAcudientes(TestCase):
    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo=CLAVE,
            )
        self.actor = institucion.usuario
        self.client.force_login(self.actor)

        self.marta = self.acudiente("Marta Ruiz Ochoa", "43512345")
        self.ana = self.estudiante("Ana Sofía Restrepo Ruiz", "1001234501", self.marta)
        self.url = reverse("consulta-del-acudiente", args=[self.marta.pk])

    def acudiente(self, nombre, documento, activa=True):
        usuario = crear_cuenta(
            email=f"{documento}@example.com",
            rol=Rol.ACUDIENTE,
            nombre=nombre,
            enviar_invitacion=False,
        )
        if activa:
            usuario.set_password(CLAVE)
            usuario.save(update_fields=["password"])
        return Acudiente.objects.create(usuario=usuario, nombre=nombre, documento=documento)

    def estudiante(self, nombre, documento, acudiente):
        return crear_estudiante(
            actor=self.actor, nombre=nombre, documento=documento, acudiente=acudiente
        )

    def cortar_el_acceso(self, acudiente):
        usuario = acudiente.usuario
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])

    def nombres_en_la_lista(self, **filtros):
        return [
            a.nombre for a in acudientes_de_la_institucion(actor=self.actor, **filtros)
        ]


class SoloLaInstitucionYSoloLeeTest(BaseDeAcudientes):
    def test_la_institucion_la_abre(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_ningun_otro_rol_la_abre(self):
        for rol in [Rol.ACUDIENTE, Rol.CAJERO, Rol.ADMINISTRADOR]:
            with self.subTest(rol=rol):
                otro = Usuario.objects.crear_usuario(
                    email=f"{rol}-otro@example.com", rol=rol, nombre="Otro"
                )
                self.client.force_login(otro)
                self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_ni_el_propio_acudiente(self):
        self.client.force_login(self.marta.usuario)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_sin_sesion_va_a_la_pantalla_de_acceso(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_un_acudiente_que_no_existe_es_un_404(self):
        url = reverse("consulta-del-acudiente", args=["01900000-0000-7000-8000-000000000000"])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_no_admite_escribir(self):
        self.assertEqual(self.client.post(self.url, {"nombre": "Otro"}).status_code, 405)
        self.marta.refresh_from_db()
        self.assertEqual(self.marta.nombre, "Marta Ruiz Ochoa")

    def test_es_un_fragmento_sin_campos(self):
        cuerpo = self.client.get(self.url).content.decode()
        self.assertIn("data-consulta-del-acudiente", cuerpo)
        self.assertNotIn("<html", cuerpo)
        self.assertNotIn("<form", cuerpo)
        self.assertNotIn("<input", cuerpo)

    def test_contraprueba_la_pagina_de_acudientes_si_trae_campos(self):
        """La búsqueda de arriba encuentra un campo cuando lo hay."""
        self.assertIn("<input", self.client.get(reverse("acudientes")).content.decode())


class SusDatosYSusEstudiantesTest(BaseDeAcudientes):
    def test_sus_datos(self):
        cuerpo = self.client.get(self.url).content.decode()
        for dato in ["Marta Ruiz Ochoa", "43512345", "43512345@example.com"]:
            with self.subTest(dato=dato):
                self.assertIn(dato, cuerpo)

    def test_sus_estudiantes_con_los_retirados_y_su_estado(self):
        tomas = self.estudiante("Tomás Restrepo Ruiz", "1001234502", self.marta)
        dar_de_baja(actor=self.actor, estudiante=tomas)

        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.context["estudiantes"], [self.ana, tomas])
        cuerpo = respuesta.content.decode()
        self.assertEqual(cuerpo.count("data-consulta-estudiante"), 2)
        self.assertEqual(cuerpo.count("data-estudiante-retirado"), 1)
        self.assertIn(self.ana.codigo_tarjeta, cuerpo)

    def test_no_trae_estudiantes_de_otros(self):
        otro = self.acudiente("Jorge Ospina", "43000002")
        self.estudiante("Luis Ospina", "1001234599", otro)
        self.assertNotIn("Luis Ospina", self.client.get(self.url).content.decode())


class NadaDeSuSaldoTest(BaseDeAcudientes):
    MONTO = Decimal("48700")

    def test_el_saldo_de_sus_estudiantes_no_aparece(self):
        recargar(actor=self.marta.usuario, estudiante=self.ana, monto=self.MONTO)
        cuerpo = self.client.get(self.url).content.decode()
        self.assertNotIn(dinero(self.MONTO), cuerpo)
        self.assertNotIn(dinero(self.MONTO, "COP"), cuerpo)

    def test_la_vista_no_lee_billetera_ni_reportes(self):
        """Sobre el bytecode y no el fuente: el docstring nombra lo que no usa."""
        usados = inspect.unwrap(views.consulta_del_acudiente).__code__.co_names
        for ajeno in ["saldo_de", "historial_de", "historial_de_consumo", "pedidos_pendientes_de"]:
            with self.subTest(ajeno=ajeno):
                self.assertNotIn(ajeno, usados)
        # Contraprueba: sí lee lo que enseña.
        self.assertIn("acudiente_para_la_institucion", usados)


class LosRetiradosTest(BaseDeAcudientes):
    def setUp(self):
        super().setUp()
        self.familia_ida = self.acudiente("Elena Gómez", "43000003")
        dar_de_baja(
            actor=self.actor,
            estudiante=self.estudiante("Pablo Gómez", "1001234503", self.familia_ida),
        )

    def test_la_familia_que_se_fue_no_sale_por_defecto(self):
        self.assertNotIn("Elena Gómez", self.nombres_en_la_lista())
        self.assertIn("Marta Ruiz Ochoa", self.nombres_en_la_lista())

    def test_ver_retirados_la_trae_marcada(self):
        self.assertIn("Elena Gómez", self.nombres_en_la_lista(incluir_retirados=True))

        tabla = self.client.get(reverse("acudientes-tabla"), {"retirados": "1"})
        cuerpo = tabla.content.decode()
        self.assertIn("Elena Gómez", cuerpo)
        # Dos marcas: la tabla de escritorio y la ficha de móvil.
        self.assertEqual(cuerpo.count("data-acudiente-retirado"), 2)

    def test_sin_el_interruptor_la_tabla_no_la_trae(self):
        cuerpo = self.client.get(reverse("acudientes-tabla")).content.decode()
        self.assertNotIn("Elena Gómez", cuerpo)
        self.assertNotIn("data-acudiente-retirado", cuerpo)

    def test_con_un_estudiante_matriculado_sigue_aunque_otro_se_fuera(self):
        tomas = self.estudiante("Tomás Restrepo Ruiz", "1001234502", self.marta)
        dar_de_baja(actor=self.actor, estudiante=tomas)
        self.assertIn("Marta Ruiz Ochoa", self.nombres_en_la_lista())

    def test_el_acceso_cortado_no_es_retirado(self):
        self.cortar_el_acceso(self.marta)
        self.assertIn("Marta Ruiz Ochoa", self.nombres_en_la_lista())

    def test_el_acudiente_sin_estudiantes_no_es_retirado(self):
        self.acudiente("Jorge Ospina", "43000002")
        self.assertIn("Jorge Ospina", self.nombres_en_la_lista())
        cuerpo = self.client.get(reverse("acudientes-tabla")).content.decode()
        self.assertNotIn("data-acudiente-retirado", cuerpo)

    def test_el_total_no_depende_de_la_busqueda(self):
        """El «de N» de «1 de N»: contado sobre lo encontrado, diría siempre lo mismo."""
        respuesta = self.client.get(reverse("acudientes-tabla"), {"busqueda": "Marta"})
        self.assertEqual(len(respuesta.context["acudientes"]), 1)
        self.assertEqual(respuesta.context["cuantos"], 1)  # Elena está fuera por defecto

        self.acudiente("Jorge Ospina", "43000002")
        respuesta = self.client.get(reverse("acudientes-tabla"), {"busqueda": "Marta"})
        self.assertEqual(respuesta.context["cuantos"], 2)

        con_retirados = self.client.get(
            reverse("acudientes-tabla"), {"busqueda": "Marta", "retirados": "1"}
        )
        self.assertEqual(con_retirados.context["cuantos"], 3)

    def test_matricular_encuentra_a_la_familia_que_se_fue(self):
        """Un hermano menor entra con el acudiente que ya existe."""
        respuesta = self.client.get(
            reverse("acudientes-para-matricular"), {"buscar_acudiente": "Elena"}
        )
        self.assertEqual([a.nombre for a in respuesta.context["acudientes"]], ["Elena Gómez"])


class ElAccesoCortadoSeVeTest(BaseDeAcudientes):
    def test_en_la_lista_de_acudientes(self):
        cuerpo = self.client.get(reverse("acudientes-tabla")).content.decode()
        self.assertNotIn("data-cuenta-cortada", cuerpo)

        self.cortar_el_acceso(self.marta)
        cuerpo = self.client.get(reverse("acudientes-tabla")).content.decode()
        self.assertIn("data-cuenta-cortada", cuerpo)
        self.assertNotIn("Activa", cuerpo)

    def test_en_el_padron(self):
        cuerpo = self.client.get(reverse("padron-tabla")).content.decode()
        self.assertIn("data-cuenta-activa", cuerpo)
        self.assertNotIn("data-cuenta-cortada", cuerpo)

        self.cortar_el_acceso(self.marta)
        cuerpo = self.client.get(reverse("padron-tabla")).content.decode()
        self.assertIn("data-cuenta-cortada", cuerpo)
        self.assertNotIn("data-cuenta-activa", cuerpo)

    def test_en_la_ficha_del_acudiente(self):
        self.cortar_el_acceso(self.marta)
        self.assertIn("data-cuenta-cortada", self.client.get(self.url).content.decode())


class CadaFilaLlevaSuControlTest(BaseDeAcudientes):
    def test_la_fila_pide_la_ficha(self):
        cuerpo = self.client.get(reverse("acudientes-tabla")).content.decode()
        # Dos: la tabla de escritorio y la ficha de móvil.
        self.assertEqual(cuerpo.count(f'hx-get="{self.url}"'), 2)
        self.assertEqual(cuerpo.count("data-fila-consultable"), 2)

    def test_la_pagina_trae_la_modal(self):
        self.assertIn("data-modal-ficha", self.client.get(reverse("acudientes")).content.decode())
