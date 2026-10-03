"""`DT-40`. La ficha del estudiante, en la modal del padrón.

Sustituye a la pantalla del admin de estudiantes, y lo que se vigila es lo que
no podía perderse por el camino:

1. **Solo la institución**, decidido por el selector antes de escribir nada.
2. **El código de tarjeta no es un campo** (`INV-7`, `INVD-4`): se reasigna con
   su propia acción y el anterior deja de existir.
3. **Un «Guardar» es una sola transacción**: si el documento choca o la imagen no
   vale, no queda nada a medias.
4. **La baja solo se pide, nunca se deshace** (`DEC-7`), y a un retirado no se
   le dibuja el interruptor.
5. **La ficha devuelve la ficha** (`DT-16`) y avisa a la tabla con un evento.
"""

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from personas.models import Acudiente, EstadoDelEstudiante, Estudiante
from personas.services import crear_estudiante, dar_de_alta_la_institucion, dar_de_baja
from personas.tests_fotografia import EN_MEMORIA, archivo
from personas.views import FichaDelEstudianteForm

CLAVE = "clave-de-prueba-2026"


@override_settings(STORAGES=EN_MEMORIA)
class BaseDeFicha(TestCase):
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
        self.url = reverse("ficha-del-estudiante", args=[self.estudiante.pk])
        self.client.force_login(self.actor)

    def datos(self, **cambios):
        """Lo que la ficha envía sin tocar nada: los dos interruptores encendidos."""
        base = {
            "nombre": self.estudiante.nombre,
            "documento": self.estudiante.documento,
            "matriculado": "on",
            "acceso_del_acudiente": "on",
        }
        base.update(cambios)
        return {clave: valor for clave, valor in base.items() if valor is not None}

    def guardar(self, **cambios):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url, self.datos(**cambios))


class SoloLaInstitucionAbreLaFichaTest(BaseDeFicha):
    def test_la_institucion_la_abre(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_ningun_otro_rol_la_abre_ni_la_guarda(self):
        for rol in [Rol.ACUDIENTE, Rol.CAJERO, Rol.ADMINISTRADOR]:
            with self.subTest(rol=rol):
                otro = Usuario.objects.crear_usuario(
                    email=f"{rol}@example.com", rol=rol, nombre="Otro"
                )
                self.client.force_login(otro)
                self.assertEqual(self.client.get(self.url).status_code, 403)
                respuesta = self.client.post(self.url, self.datos(nombre="Cambiado"))
                self.assertEqual(respuesta.status_code, 403)

        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.nombre, "Ana Sofía Restrepo Ruiz")

    def test_ni_el_acudiente_sobre_su_propio_hijo(self):
        self.client.force_login(self.acudiente.usuario)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_sin_sesion_va_a_la_pantalla_de_acceso(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_un_estudiante_que_no_existe_es_un_404(self):
        url = reverse("ficha-del-estudiante", args=["01900000-0000-7000-8000-000000000000"])
        self.assertEqual(self.client.get(url).status_code, 404)


class LaFichaEsUnFragmentoTest(BaseDeFicha):
    """`DT-16`: lo que devuelven `GET`, `POST` y la reasignación es la ficha."""

    def test_no_es_una_pagina(self):
        cuerpo = self.client.get(self.url).content.decode()
        self.assertIn("data-ficha-del-estudiante", cuerpo)
        self.assertNotIn("<html", cuerpo)

    def test_guardar_tambien_devuelve_la_ficha(self):
        cuerpo = self.guardar(nombre="Ana Sofía Restrepo").content.decode()
        self.assertIn("data-ficha-del-estudiante", cuerpo)
        self.assertNotIn("<html", cuerpo)

    def test_guardar_avisa_a_la_tabla(self):
        self.assertEqual(self.guardar()["HX-Trigger"], "padron-cambiado")

    def test_un_error_no_avisa_a_la_tabla(self):
        """Nada cambió: la tabla no tiene por qué volver a pedirse."""
        respuesta = self.guardar(nombre="")
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("HX-Trigger", respuesta)

    def test_el_padron_abre_la_ficha_de_cada_fila(self):
        cuerpo = self.client.get(reverse("padron")).content.decode()
        self.assertIn("data-editar-estudiante", cuerpo)
        self.assertIn(f'hx-get="{self.url}"', cuerpo)
        self.assertIn("data-modal-ficha", cuerpo)

    def test_el_buscador_vuelve_a_pedir_la_tabla_cuando_algo_cambia(self):
        """Con los filtros que tenía: el evento lo escucha el formulario del buscador."""
        cuerpo = self.client.get(reverse("padron")).content.decode()
        self.assertIn("padron-cambiado from:body", cuerpo)


class ElCodigoNoEsUnCampoTest(BaseDeFicha):
    """`INV-7`, `HU-43`, `HU-46`. El código lo genera el sistema."""

    def test_el_formulario_no_lo_tiene(self):
        self.assertNotIn("codigo_tarjeta", FichaDelEstudianteForm.base_fields)

    def test_la_ficha_lo_ensena_sin_un_input(self):
        cuerpo = self.client.get(self.url).content.decode()
        self.assertIn("data-codigo-vigente", cuerpo)
        self.assertIn(self.estudiante.codigo_tarjeta, cuerpo)
        self.assertNotIn('name="codigo_tarjeta"', cuerpo)
        # Contraprueba: los campos que sí lo son se dibujan con su `name`.
        self.assertIn('name="nombre"', cuerpo)

    def test_enviar_un_codigo_no_lo_cambia(self):
        anterior = self.estudiante.codigo_tarjeta
        self.guardar(codigo_tarjeta="AAAAAAAAAAAAAA")
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.codigo_tarjeta, anterior)

    def test_la_ficha_enlaza_la_tarjeta_imprimible(self):
        """`HU-45`. Con el admin, el enlace se había quedado sin ningún sitio."""
        cuerpo = self.client.get(self.url).content.decode()
        self.assertIn(reverse("tarjeta-del-estudiante", args=[self.estudiante.pk]), cuerpo)


class ReasignarDesdeLaFichaTest(BaseDeFicha):
    """`HU-46`, `INVD-4`."""

    def setUp(self):
        super().setUp()
        self.reasignar = reverse("reasignacion-desde-el-padron", args=[self.estudiante.pk])

    def test_cambia_el_codigo_y_dice_cual_murio(self):
        anterior = self.estudiante.codigo_tarjeta
        respuesta = self.client.post(self.reasignar)

        self.estudiante.refresh_from_db()
        self.assertNotEqual(self.estudiante.codigo_tarjeta, anterior)
        self.assertFalse(Estudiante.objects.filter(codigo_tarjeta=anterior).exists())
        self.assertContains(respuesta, "data-codigo-reasignado")
        self.assertEqual(respuesta.context["codigo_retirado"], anterior)
        self.assertEqual(respuesta["HX-Trigger"], "padron-cambiado")

    def test_pide_confirmacion(self):
        cuerpo = self.client.get(self.url).content.decode()
        inicio = cuerpo.index("data-reasignar-codigo")
        self.assertIn("hx-confirm=", cuerpo[inicio:inicio + 600])

    def test_no_se_reasigna_con_un_get(self):
        self.assertEqual(self.client.get(self.reasignar).status_code, 405)

    def test_ningun_otro_rol(self):
        anterior = self.estudiante.codigo_tarjeta
        self.client.force_login(self.acudiente.usuario)
        self.assertEqual(self.client.post(self.reasignar).status_code, 403)
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.codigo_tarjeta, anterior)


class GuardarTest(BaseDeFicha):
    """`HU-44`, segundo criterio: modificar los campos de uno ya cargado."""

    def test_cambia_nombre_y_documento(self):
        respuesta = self.guardar(nombre="Ana Sofía Restrepo", documento="1001234599")

        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.nombre, "Ana Sofía Restrepo")
        self.assertEqual(self.estudiante.documento, "1001234599")
        self.assertContains(respuesta, "data-ficha-guardada")

    def test_guardar_sin_tocar_nada_no_cambia_nada(self):
        self.guardar()
        self.estudiante.refresh_from_db()
        self.acudiente.usuario.refresh_from_db()
        self.assertEqual(self.estudiante.estado, EstadoDelEstudiante.ACTIVO)
        self.assertTrue(self.acudiente.usuario.is_active)

    def test_un_campo_vacio_se_devuelve_con_su_error(self):
        respuesta = self.guardar(nombre="")
        self.assertTrue(respuesta.context["formulario"].errors["nombre"])
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.nombre, "Ana Sofía Restrepo Ruiz")


@override_settings(STORAGES=EN_MEMORIA)
class TodoONadaTest(BaseDeFicha):
    """Un «Guardar» es una sola transacción (`DT-40`)."""

    def setUp(self):
        super().setUp()
        self.otro = crear_estudiante(
            actor=self.actor,
            nombre="Julián Restrepo Ruiz",
            documento="1001234502",
            acudiente=self.acudiente,
        )

    def test_un_documento_ajeno_no_deja_nada_a_medias(self):
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(self.url, {
                **self.datos(nombre="Nombre que no debe quedar", documento="1001234502"),
                "fotografia": archivo(),
            })

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["formulario"].errors["documento"])
        self.assertNotIn("HX-Trigger", respuesta)

        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.nombre, "Ana Sofía Restrepo Ruiz")
        self.assertEqual(self.estudiante.documento, "1001234501")
        self.assertEqual(self.estudiante.foto_clave, "")

    def test_una_imagen_que_no_vale_no_deja_nada_a_medias(self):
        roto = SimpleUploadedFile("avatar.jpg", b"no es una imagen", content_type="image/jpeg")
        respuesta = self.client.post(self.url, {
            **self.datos(nombre="Nombre que no debe quedar"),
            "fotografia": roto,
        })

        self.assertTrue(respuesta.context["formulario"].errors["fotografia"])
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.nombre, "Ana Sofía Restrepo Ruiz")

    def test_un_formato_que_el_servicio_rechaza_tampoco(self):
        """El formulario acepta cualquier imagen; `DT-20`, solo algunas. El
        rechazo del servicio también deshace lo demás."""
        from personas.tests_fotografia import imagen

        tiff = SimpleUploadedFile(
            "avatar.tiff", imagen(formato="TIFF"), content_type="image/tiff"
        )
        respuesta = self.client.post(self.url, {
            **self.datos(nombre="Nombre que no debe quedar"),
            "fotografia": tiff,
        })

        self.assertTrue(respuesta.context["formulario"].errors["fotografia"])
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.nombre, "Ana Sofía Restrepo Ruiz")


@override_settings(STORAGES=EN_MEMORIA)
class LaFotografiaDesdeLaFichaTest(BaseDeFicha):
    """`HU-57`. Se carga, se reemplaza y se quita desde la ficha."""

    def test_subirla_la_guarda(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url, {**self.datos(), "fotografia": archivo()})
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.tiene_foto)

    def test_quitarla_la_borra(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url, {**self.datos(), "fotografia": archivo()})
        self.guardar(quitar_foto="on")
        self.estudiante.refresh_from_db()
        self.assertFalse(self.estudiante.tiene_foto)

    def test_sin_fotografia_no_ofrece_quitarla_ni_pinta_un_src_vacio(self):
        cuerpo = self.client.get(self.url).content.decode()
        self.assertNotIn("data-quitar-foto", cuerpo)
        self.assertNotIn('src=""', cuerpo)
        self.assertIn("data-foto-inicial", cuerpo)

    def test_los_limites_salen_de_los_ajustes(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(
            respuesta.context["tamano_maximo_mb"],
            settings.IMAGEN_TAMANO_MAXIMO_BYTES // (1024 * 1024),
        )
        self.assertEqual(respuesta.context["lado_maximo"], settings.IMAGEN_LADO_MAXIMO)


class LaBajaDesdeLaFichaTest(BaseDeFicha):
    """`HU-51`, `DEC-7`. Apagar «Matriculado» es la baja, y no tiene vuelta."""

    def test_apagar_la_matricula_da_de_baja(self):
        self.guardar(matriculado=None)
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.estado, EstadoDelEstudiante.BAJA)
        self.assertIsNotNone(self.estudiante.dado_de_baja_en)

    def test_con_la_matricula_encendida_no(self):
        self.guardar()
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.estado, EstadoDelEstudiante.ACTIVO)

    def test_un_retirado_no_ve_el_interruptor_sino_desde_cuando(self):
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)
        cuerpo = self.client.get(self.url).content.decode()
        self.assertNotIn("data-matriculado", cuerpo)
        self.assertIn("data-ficha-retirado", cuerpo)

    def test_y_ninguna_ficha_lo_devuelve_a_la_matricula(self):
        """Ni con la casilla puesta a mano: no existe servicio que lo haga."""
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)
        fecha = Estudiante.objects.get(pk=self.estudiante.pk).dado_de_baja_en

        self.guardar(matriculado="on")

        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.estado, EstadoDelEstudiante.BAJA)
        self.assertEqual(self.estudiante.dado_de_baja_en, fecha)

    def test_a_un_retirado_se_le_sigue_pudiendo_corregir_el_nombre(self):
        """Que el interruptor falte no puede leerse como «retirar otra vez»."""
        dar_de_baja(actor=self.actor, estudiante=self.estudiante)
        respuesta = self.guardar(nombre="Ana Sofía Restrepo", matriculado=None)
        self.assertContains(respuesta, "data-ficha-guardada")
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.nombre, "Ana Sofía Restrepo")

    def test_la_confirmacion_la_pide_el_formulario_solo_al_apagar(self):
        """El texto viaja en el formulario y el script lo pide si la casilla se
        apagó (`assets/js/interfaz.js`). Un `hx-confirm` fijo preguntaría también
        al corregir un apellido."""
        cuerpo = self.client.get(self.url).content.decode()
        inicio = cuerpo.rfind("<form", 0, cuerpo.index("data-formulario-de-la-ficha"))
        formulario = cuerpo[inicio:cuerpo.index(">", inicio) + 1]
        self.assertIn("data-confirmar-baja=", formulario)
        self.assertNotIn("hx-confirm", formulario)


class ElAccesoDelAcudienteDesdeLaFichaTest(BaseDeFicha):
    """`HU-63`, `DEC-20`."""

    def test_apagarlo_le_corta_el_acceso(self):
        self.guardar(acceso_del_acudiente=None)
        self.acudiente.usuario.refresh_from_db()
        self.assertFalse(self.acudiente.usuario.is_active)

    def test_encenderlo_se_lo_devuelve(self):
        self.guardar(acceso_del_acudiente=None)
        self.guardar()
        self.acudiente.usuario.refresh_from_db()
        self.assertTrue(self.acudiente.usuario.is_active)

    def test_no_toca_al_estudiante(self):
        self.guardar(acceso_del_acudiente=None)
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.puede_operar)

    def test_dice_a_cuantos_estudiantes_alcanza(self):
        """Cuarto criterio de `HU-63`: antes de apagarlo, no después."""
        crear_estudiante(
            actor=self.actor,
            nombre="Julián Restrepo Ruiz",
            documento="1001234502",
            acudiente=self.acudiente,
        )
        respuesta = self.client.get(self.url)
        self.assertEqual(
            respuesta.context["estudiantes_del_acudiente"],
            ["Ana Sofía Restrepo Ruiz", "Julián Restrepo Ruiz"],
        )
        self.assertContains(respuesta, "data-alcance-del-acceso")
        self.assertContains(respuesta, "Julián Restrepo Ruiz")

    def test_el_nombre_y_el_correo_del_acudiente_no_son_campos(self):
        """`DEC-20` amplía el acceso, no los datos: siguen siendo de consulta."""
        cuerpo = self.client.get(self.url).content.decode()
        self.assertIn("marta.ruiz@example.com", cuerpo)
        self.assertNotIn('name="email"', cuerpo)
        self.assertNotIn('name="acudiente', cuerpo.replace('name="acceso_del_acudiente"', ""))
