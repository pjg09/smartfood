"""`HU-44`, primer criterio, desde el padrón (`DT-40`): matricular a uno solo.

Lo que se vigila:

1. **Solo la institución**, y se pregunta antes de pintar la ficha.
2. **El código lo pone el sistema** (`HU-43`, `INV-7`): la ficha no tiene el campo
   y lo que llegue con ese nombre se ignora.
3. **Todo o nada**: si la fotografía no vale, no queda nadie matriculado a medias.
4. **El acudiente se elige entre los que existen**; el buscador no devuelve la
   lista entera.
5. **El navegador y el servidor piden lo mismo**: las longitudes que el script
   usa para avisar salen del formulario, y este de `personas.validacion`.
"""

from django.test import override_settings
from django.urls import reverse

from cuentas.models import Rol, Usuario
from cuentas.services import crear_cuenta
from personas.codigo import ALFABETO, LONGITUD
from personas.models import Acudiente, Estudiante
from personas.tests_ficha import BaseDeFicha
from personas.tests_fotografia import EN_MEMORIA, archivo, imagen
from personas.validacion import LONGITUD_DOCUMENTO
from personas.views import ACUDIENTES_EN_EL_BUSCADOR, AltaDeEstudianteForm


@override_settings(STORAGES=EN_MEMORIA)
class BaseDeAlta(BaseDeFicha):
    def setUp(self):
        super().setUp()
        self.alta = reverse("alta-de-estudiante")
        self.buscar = reverse("acudientes-para-matricular")

    def datos_de_alta(self, **cambios):
        base = {
            "nombre": "Julián Restrepo Ruiz",
            "documento": "1001234502",
            "acudiente": str(self.acudiente.pk),
        }
        base.update(cambios)
        return {clave: valor for clave, valor in base.items() if valor is not None}

    def matricular(self, **cambios):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.alta, self.datos_de_alta(**cambios))

    def matriculados(self):
        return Estudiante.objects.filter(documento="1001234502")


class SoloLaInstitucionMatriculaTest(BaseDeAlta):
    def test_la_institucion_abre_la_ficha_de_alta(self):
        respuesta = self.client.get(self.alta)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data-formulario-de-alta")
        self.assertNotContains(respuesta, "<html")

    def test_ningun_otro_rol_la_abre_ni_matricula(self):
        for rol in [Rol.ACUDIENTE, Rol.CAJERO, Rol.ADMINISTRADOR]:
            with self.subTest(rol=rol):
                otro = Usuario.objects.crear_usuario(email=f"{rol}@example.com", rol=rol)
                self.client.force_login(otro)
                self.assertEqual(self.client.get(self.alta).status_code, 403)
                self.assertEqual(self.client.post(self.alta, self.datos_de_alta()).status_code, 403)
                self.assertEqual(
                    self.client.get(self.buscar, {"buscar_acudiente": "Marta"}).status_code, 403
                )
        self.assertFalse(self.matriculados().exists())

    def test_sin_sesion_va_a_la_pantalla_de_acceso(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.alta).status_code, 302)

    def test_el_padron_ofrece_matricular_a_uno_solo(self):
        cuerpo = self.client.get(reverse("padron")).content.decode()
        self.assertIn("data-matricular-estudiante", cuerpo)
        self.assertIn(f'hx-get="{self.alta}"', cuerpo)


class MatricularTest(BaseDeAlta):
    def test_matricula_con_su_codigo_y_su_acudiente(self):
        respuesta = self.matricular()

        estudiante = self.matriculados().get()
        self.assertEqual(estudiante.nombre, "Julián Restrepo Ruiz")
        self.assertEqual(estudiante.acudiente, self.acudiente)
        self.assertEqual(len(estudiante.codigo_tarjeta), LONGITUD)
        self.assertTrue(set(estudiante.codigo_tarjeta) <= set(ALFABETO))
        self.assertTrue(estudiante.puede_operar)

        self.assertContains(respuesta, "data-estudiante-matriculado")
        self.assertContains(respuesta, estudiante.codigo_tarjeta)
        self.assertEqual(respuesta["HX-Trigger"], "padron-cambiado")

    def test_vuelve_vacia_para_el_siguiente(self):
        respuesta = self.matricular()
        self.assertFalse(respuesta.context["formulario"].is_bound)

    def test_y_sale_en_el_padron(self):
        self.matricular()
        cuerpo = self.client.get(reverse("padron-tabla")).content.decode()
        self.assertIn("Julián Restrepo Ruiz", cuerpo)

    def test_un_codigo_enviado_se_ignora(self):
        """`INV-7`: el código no se escribe, ni aunque alguien lo mande."""
        self.assertNotIn("codigo_tarjeta", AltaDeEstudianteForm.base_fields)
        self.matricular(codigo_tarjeta="AAAAAAAAAAAAAA")
        self.assertNotEqual(self.matriculados().get().codigo_tarjeta, "AAAAAAAAAAAAAA")


class LoQueFaltaSeDiceTest(BaseDeAlta):
    def test_sin_nada_no_matricula_y_dice_que_falta(self):
        respuesta = self.client.post(self.alta, {})
        errores = respuesta.context["formulario"].errors
        for campo in ["nombre", "documento", "acudiente"]:
            with self.subTest(campo=campo):
                self.assertIn(campo, errores)
        self.assertEqual(Estudiante.objects.count(), 1)
        self.assertNotIn("HX-Trigger", respuesta)

    def test_un_documento_corto_no_entra(self):
        corto = "1" * (LONGITUD_DOCUMENTO[0] - 1)
        respuesta = self.matricular(documento=corto)
        self.assertIn("documento", respuesta.context["formulario"].errors)
        self.assertFalse(Estudiante.objects.filter(documento=corto).exists())

    def test_un_documento_ajeno_no_entra(self):
        respuesta = self.matricular(documento=self.estudiante.documento)
        self.assertIn("documento", respuesta.context["formulario"].errors)
        self.assertEqual(Estudiante.objects.filter(documento=self.estudiante.documento).count(), 1)

    def test_un_acudiente_que_no_existe_no_entra(self):
        respuesta = self.matricular(acudiente="01900000-0000-7000-8000-000000000000")
        self.assertIn("acudiente", respuesta.context["formulario"].errors)
        self.assertFalse(self.matriculados().exists())

    def test_un_acudiente_mal_escrito_tampoco(self):
        respuesta = self.matricular(acudiente="no-es-un-uuid")
        self.assertIn("acudiente", respuesta.context["formulario"].errors)

    def test_el_acudiente_elegido_vuelve_elegido(self):
        """Si falló otra cosa, no hay que volver a buscarlo."""
        respuesta = self.matricular(nombre="")
        self.assertEqual(respuesta.context["acudiente_elegido"], self.acudiente)
        self.assertContains(respuesta, "marta.ruiz@example.com")


@override_settings(STORAGES=EN_MEMORIA)
class LaFotografiaEnElAltaTest(BaseDeAlta):
    def test_con_fotografia_la_guarda(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.alta, {**self.datos_de_alta(), "fotografia": archivo()})
        self.assertTrue(self.matriculados().get().tiene_foto)

    def test_si_la_fotografia_no_vale_nadie_queda_matriculado(self):
        """Todo o nada: el formulario acepta el TIFF, `DT-20` no."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        tiff = SimpleUploadedFile("a.tiff", imagen(formato="TIFF"), content_type="image/tiff")
        respuesta = self.client.post(self.alta, {**self.datos_de_alta(), "fotografia": tiff})

        self.assertIn("fotografia", respuesta.context["formulario"].errors)
        self.assertFalse(self.matriculados().exists())


class ElBuscadorDeAcudientesTest(BaseDeAlta):
    def test_sin_busqueda_no_devuelve_a_nadie(self):
        respuesta = self.client.get(self.buscar)
        self.assertEqual(respuesta.context["acudientes"], [])

    def test_busca_por_nombre_documento_o_correo(self):
        for termino in ["Marta", "43512345", "marta.ruiz@"]:
            with self.subTest(termino=termino):
                respuesta = self.client.get(self.buscar, {"buscar_acudiente": termino})
                self.assertEqual(respuesta.context["acudientes"], [self.acudiente])
                self.assertContains(respuesta, f'data-elegir-acudiente="{self.acudiente.pk}"')

    def test_no_devuelve_mas_de_unos_pocos(self):
        for numero in range(ACUDIENTES_EN_EL_BUSCADOR + 3):
            cuenta = crear_cuenta(
                email=f"familia{numero}@example.com", rol=Rol.ACUDIENTE,
                nombre="Familia", enviar_invitacion=False,
            )
            Acudiente.objects.create(
                usuario=cuenta, nombre=f"Familia Gómez {numero}", documento=f"7000000{numero:02d}"
            )
        respuesta = self.client.get(self.buscar, {"buscar_acudiente": "Gómez"})
        self.assertEqual(len(respuesta.context["acudientes"]), ACUDIENTES_EN_EL_BUSCADOR)

    def test_sin_coincidencias_lo_dice(self):
        respuesta = self.client.get(self.buscar, {"buscar_acudiente": "Nadie"})
        self.assertContains(respuesta, "data-sin-acudientes")


class ElNavegadorPideLoMismoQueElServidorTest(BaseDeAlta):
    """Las longitudes del aviso rojo salen del formulario: no hay dos reglas."""

    def test_el_alta_lleva_las_longitudes_de_la_carga(self):
        cuerpo = self.client.get(self.alta).content.decode()
        self.assertIn(f'data-minimo="{LONGITUD_DOCUMENTO[0]}"', cuerpo)
        self.assertIn(f'data-maximo="{LONGITUD_DOCUMENTO[1]}"', cuerpo)

    def test_la_ficha_de_edicion_pide_lo_mismo(self):
        respuesta = self.guardar(documento="1" * (LONGITUD_DOCUMENTO[0] - 1))
        self.assertIn("documento", respuesta.context["formulario"].errors)
        cuerpo = self.client.get(self.url).content.decode()
        self.assertIn(f'data-minimo="{LONGITUD_DOCUMENTO[0]}"', cuerpo)

    def test_matricular_nace_deshabilitado_y_cada_campo_tiene_su_aviso(self):
        """El atributo, no la clase: `disabled:bg-borde` contiene la palabra y
        haría pasar la prueba con el atributo ausente (`[S3.6]` de
        `docs/escribir-pruebas.md`)."""
        cuerpo = self.client.get(self.alta).content.decode()
        self.assertIn("data-guardar-ficha disabled", cuerpo)
        # Contraprueba: la ficha de edición nace llena y no lo trae.
        edicion = self.client.get(self.url).content.decode()
        self.assertIn("data-guardar-ficha", edicion)
        self.assertNotIn("data-guardar-ficha disabled", edicion)
        self.assertEqual(cuerpo.count("data-validar"), 3)
        self.assertEqual(cuerpo.count("data-aviso-vacio="), 3)
