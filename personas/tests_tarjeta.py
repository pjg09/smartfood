"""`TT-36` y `TT-37`. El código vigente, en pantalla y en papel (`HU-45`).

`ENT-02` es una prueba de concepto **con tarjetas físicas y un lector**. Eso
cambia lo que significa probar esto: no basta con que la página se vea bien, el
símbolo tiene que estar bien codificado y salir del papel con el ancho correcto.

**Lo que estas pruebas no pueden hacer es escanear.** No hay lector en el
ejecutor de pruebas, así que la lectura real queda para `ENT-02`, en el Sprint 2.
Lo que sí se comprueba aquí es todo lo que se puede comprobar sin él, y en
particular lo que fallaría en silencio: que el patrón de módulos que se dibuja
sigue siendo un mensaje Code 128 válido para ese código, con su suma de control
correcta, y que las zonas mudas están donde tienen que estar.
"""

import re

from barcode.charsets.code128 import CODES, START_CODES, STOP
from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from cuentas.models import Rol
from cuentas.services import crear_cuenta, sincronizar_grupos_y_permisos
from personas.models import Acudiente, Estudiante
from personas.selectors import estudiante_para_la_institucion
from personas.services import crear_estudiante, dar_de_alta_la_institucion
from personas.tarjeta import (
    ALTO_DE_BARRAS_MM,
    ANCHO_DE_MODULO_MM,
    ZONA_MUDA_MODULOS,
    ancho_mm,
    patron_de_modulos,
    svg_del_codigo,
)

CLAVE = "clave-de-prueba-2026"
CODIGO = "N4DVVN9BZBQCB3"

MODULOS_POR_SIMBOLO = 11

# El cierre de Code 128 son **trece** módulos: el patrón de parada de once más la
# barra de terminación de dos. La constante `STOP` de la biblioteca solo trae los
# once primeros, así que aquí se completa.
TERMINACION = STOP + "11"


def _valores_del_patron(patron):
    """Traduce el patrón de módulos a los valores de Code 128 que representa.

    Es el camino inverso al del codificador, y por eso vale como comprobación:
    parte de lo que **se va a dibujar** y reconstruye lo que significa. Si el
    dibujo perdiera un módulo, invirtiera el orden o comiera una barra al
    agrupar tramos, aquí dejaría de cuadrar.

    Se apoya en la tabla de la norma que trae la biblioteca —107 patrones que no
    tiene sentido volver a teclear— pero **la lectura y la suma de control son
    de aquí**, que es donde puede estar el error propio.
    """
    if not patron.endswith(TERMINACION):
        raise AssertionError("el símbolo no termina con el patrón de parada")

    cuerpo = patron[: -len(TERMINACION)]
    if len(cuerpo) % MODULOS_POR_SIMBOLO:
        raise AssertionError(
            f"el cuerpo mide {len(cuerpo)} módulos, que no es múltiplo de "
            f"{MODULOS_POR_SIMBOLO}"
        )

    valores = []
    for inicio in range(0, len(cuerpo), MODULOS_POR_SIMBOLO):
        trozo = cuerpo[inicio : inicio + MODULOS_POR_SIMBOLO]
        if trozo not in CODES:
            raise AssertionError(f"«{trozo}» no es un símbolo de Code 128")
        valores.append(CODES.index(trozo))
    return valores


class ElSimboloEsUnCode128ValidoTest(SimpleTestCase):
    """Lo que no se ve en pantalla y rompe la demostración en papel."""

    def test_empieza_con_el_arranque_del_subconjunto_b(self):
        """Subconjunto B: el que codifica dígitos y mayúsculas (`DT-22`)."""
        valores = _valores_del_patron(patron_de_modulos(CODIGO))
        self.assertEqual(valores[0], START_CODES["B"])

    def test_los_datos_son_exactamente_el_codigo(self):
        valores = _valores_del_patron(patron_de_modulos(CODIGO))
        datos = valores[1:-1]

        # En el subconjunto B, el valor de un carácter imprimible es su código
        # ASCII menos 32.
        self.assertEqual("".join(chr(v + 32) for v in datos), CODIGO)

    def test_la_suma_de_control_cuadra(self):
        """Módulo 103, ponderada por la posición. Es lo que el lector verifica.

        Un símbolo con la suma mal se lee como basura o no se lee: es
        exactamente el fallo que no se ve hasta que las tarjetas están impresas.
        """
        valores = _valores_del_patron(patron_de_modulos(CODIGO))
        datos, control = valores[:-1], valores[-1]

        esperada = (datos[0] + sum(i * v for i, v in enumerate(datos[1:], start=1))) % 103
        self.assertEqual(control, esperada)

    def test_codigos_distintos_dan_simbolos_distintos(self):
        self.assertNotEqual(patron_de_modulos(CODIGO), patron_de_modulos("ZZZZZZZZZZZZZZ"))


class ElDibujoConservaElSimboloTest(SimpleTestCase):
    """El SVG es donde puede colarse un error propio: agrupar tramos, contar mal
    las zonas mudas, redondear anchos."""

    def setUp(self):
        self.svg = svg_del_codigo(CODIGO)
        self.patron = patron_de_modulos(CODIGO)

    def _patron_dibujado(self):
        """Reconstruye el patrón leyendo los rectángulos negros del SVG."""
        total = int(re.search(r'viewBox="0 0 (\d+) ', self.svg).group(1))
        modulos = ["0"] * total

        negros = re.search(r'<g fill="#000">(.*?)</g>', self.svg, flags=re.S).group(1)
        for x, ancho in re.findall(r'<rect x="(\d+)" y="0" width="(\d+)"', negros):
            for posicion in range(int(x), int(x) + int(ancho)):
                modulos[posicion] = "1"
        return "".join(modulos)

    def test_los_rectangulos_reproducen_el_patron_exacto(self):
        dibujado = self._patron_dibujado()
        sin_zonas_mudas = dibujado[ZONA_MUDA_MODULOS : len(dibujado) - ZONA_MUDA_MODULOS]

        self.assertEqual(sin_zonas_mudas, self.patron)

    def test_las_zonas_mudas_estan_en_blanco(self):
        """Sin ellas el lector no encuentra dónde empieza el símbolo."""
        dibujado = self._patron_dibujado()

        self.assertEqual(dibujado[:ZONA_MUDA_MODULOS], "0" * ZONA_MUDA_MODULOS)
        self.assertEqual(dibujado[-ZONA_MUDA_MODULOS:], "0" * ZONA_MUDA_MODULOS)
        self.assertGreaterEqual(ZONA_MUDA_MODULOS, 10, "la norma pide diez módulos")

    def test_las_medidas_van_en_milimetros_y_no_en_pixeles(self):
        """Un símbolo medido en píxeles se imprime a la resolución que decida el
        navegador, y deja de leerse."""
        self.assertIn('width="68.97mm"', self.svg)
        self.assertIn(f'height="{ALTO_DE_BARRAS_MM:.2f}mm"', self.svg)
        self.assertNotIn("px", self.svg)

    def test_cabe_en_una_tarjeta(self):
        """85,6 mm es el ancho de una tarjeta bancaria, que es el formato."""
        self.assertLess(ancho_mm(CODIGO), 85.6 - 10, "no deja margen a los lados")

    def test_el_ancho_de_modulo_no_baja_del_minimo_util(self):
        """Con impresora de oficina y lector económico, por debajo se pierden
        lecturas (`DT-22`)."""
        self.assertGreaterEqual(ANCHO_DE_MODULO_MM, 0.25)

    def test_es_svg_en_linea_y_no_un_fichero_suelto(self):
        """Va dentro de un documento HTML: sin declaración XML ni DOCTYPE."""
        self.assertTrue(self.svg.startswith("<svg "))
        self.assertNotIn("<?xml", self.svg)
        self.assertNotIn("DOCTYPE", self.svg)

    def test_lleva_alternativa_textual(self):
        self.assertIn(f'aria-label="Código de barras {CODIGO}"', self.svg)


class BaseConEstudiante(TestCase):
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

    def _url(self, estudiante=None):
        return reverse(
            "tarjeta-del-estudiante", args=[(estudiante or self.estudiante).pk]
        )


class LaVistaImprimibleTest(BaseConEstudiante):
    """`TT-37`. Lo que se manda a la impresora."""

    def test_la_institucion_la_abre(self):
        self.client.force_login(self.actor)
        respuesta = self.client.get(self._url())

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "personas/tarjeta.html")

    def test_lleva_el_simbolo_y_el_codigo_legible(self):
        """Las dos cosas: el lector lee el símbolo, la persona lee el texto
        cuando el lector falla."""
        self.client.force_login(self.actor)
        cuerpo = self.client.get(self._url()).content.decode()

        self.assertIn("<svg ", cuerpo)
        self.assertIn(self.estudiante.codigo_tarjeta, cuerpo)
        self.assertIn("Ana Sofía Restrepo Ruiz", cuerpo)
        self.assertIn("1001234501", cuerpo)

    def test_el_simbolo_de_la_pagina_codifica_el_codigo_del_estudiante(self):
        """De extremo a extremo: lo que se imprime es lo que hay en la base."""
        self.client.force_login(self.actor)
        cuerpo = self.client.get(self._url()).content.decode()

        svg = re.search(r"<svg .*?</svg>", cuerpo, flags=re.S).group(0)
        self.assertEqual(svg, svg_del_codigo(self.estudiante.codigo_tarjeta))

    def test_avisa_de_imprimir_al_cien_por_ciento(self):
        """Si el navegador ajusta a la página, las barras se estrechan."""
        self.client.force_login(self.actor)
        cuerpo = self.client.get(self._url()).content.decode()

        self.assertIn("100 %", cuerpo)
        self.assertIn("Code 128", cuerpo)


class SoloMuestraElCodigoVigenteTest(BaseConEstudiante):
    """Segundo criterio de `HU-45`, y la razón de no guardar la imagen.

    Un SVG almacenado seguiría enseñando un código correcto después de que
    `HU-46` lo reasignara, y esa tarjeta impresa ya no abre ningún saldo
    (`INVD-4`).
    """

    def test_el_simbolo_se_rehace_cuando_el_codigo_cambia(self):
        self.client.force_login(self.actor)
        antes = self.client.get(self._url()).content.decode()

        nuevo = "ZZZZZZZZZZZZZZ"
        Estudiante.objects.filter(pk=self.estudiante.pk).update(codigo_tarjeta=nuevo)

        despues = self.client.get(self._url()).content.decode()

        self.assertIn(nuevo, despues)
        self.assertNotIn(self.estudiante.codigo_tarjeta, despues)
        self.assertNotEqual(antes, despues)

    def test_no_se_almacena_ninguna_imagen(self):
        """La tarjeta no tiene campo donde guardarla, y no debe tenerlo."""
        campos = {c.name for c in Estudiante._meta.get_fields()}

        for inventado in ["codigo_de_barras", "tarjeta_svg", "imagen_tarjeta"]:
            self.assertNotIn(inventado, campos)


class SoloLaInstitucionImprimeTest(BaseConEstudiante):
    """`HU-45` es de `USR-5`: quien produce la tarjeta es el colegio."""

    def _cuenta(self, rol, email):
        return crear_cuenta(
            email=email, rol=rol, accede_a_administracion=True, enviar_invitacion=False
        )

    def test_ningun_otro_rol_la_alcanza(self):
        for rol in [Rol.CAJERO, Rol.ADMINISTRADOR, Rol.ACUDIENTE]:
            with self.subTest(rol=rol):
                self.client.force_login(self._cuenta(rol, f"{rol}@example.com"))
                self.assertEqual(self.client.get(self._url()).status_code, 403)

    def test_el_acudiente_tampoco_para_su_propio_hijo(self):
        """No es suya: `HU-45` la escribe la institución para producir la tarjeta.

        Si algún día el acudiente tiene que verla, será con una historia que lo
        diga; no colándose por esta.
        """
        self.client.force_login(self.acudiente.usuario)
        self.assertEqual(self.client.get(self._url()).status_code, 403)

    def test_un_anonimo_va_a_la_pantalla_de_acceso(self):
        respuesta = self.client.get(self._url())
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.url.startswith(reverse("acceso")))

    def test_una_cuenta_desactivada_no_imprime(self):
        self.actor.is_active = False
        self.actor.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            estudiante_para_la_institucion(
                actor=self.actor, estudiante_id=self.estudiante.pk
            )

    def test_un_estudiante_que_no_existe_es_un_404(self):
        self.client.force_login(self.actor)
        respuesta = self.client.get(
            reverse("tarjeta-del-estudiante", args=["01a05974-2262-71e1-93f2-000000000000"])
        )
        self.assertEqual(respuesta.status_code, 404)


class ElCodigoVigenteEnLaFichaTest(BaseConEstudiante):
    """`TT-36`. Primer criterio de `HU-45`: se consulta desde la vista de
    administración de estudiantes."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.actor)

    def test_el_listado_muestra_el_codigo(self):
        respuesta = self.client.get(reverse("admin:personas_estudiante_changelist"))
        self.assertContains(respuesta, self.estudiante.codigo_tarjeta)

    def test_la_ficha_muestra_el_codigo_y_el_enlace_para_imprimirlo(self):
        respuesta = self.client.get(
            reverse("admin:personas_estudiante_change", args=[self.estudiante.pk])
        )
        self.assertContains(respuesta, self.estudiante.codigo_tarjeta)
        self.assertContains(respuesta, self._url())

    def test_el_codigo_sigue_sin_poder_escribirse(self):
        """`HU-14`: lo genera el sistema. Verlo no es poder editarlo."""
        cuerpo = self.client.get(
            reverse("admin:personas_estudiante_change", args=[self.estudiante.pk])
        ).content.decode()

        self.assertNotIn('name="codigo_tarjeta"', cuerpo)

    def test_se_busca_por_el_codigo(self):
        """La pregunta inversa, con una tarjeta suelta en la mano: ¿de quién es?"""
        otro = crear_estudiante(
            actor=self.actor,
            nombre="Tomás Restrepo Ruiz",
            documento="1001234502",
            acudiente=self.acudiente,
        )

        respuesta = self.client.get(
            reverse("admin:personas_estudiante_changelist"),
            {"q": self.estudiante.codigo_tarjeta},
        )
        self.assertContains(respuesta, "Ana Sofía Restrepo Ruiz")
        self.assertNotContains(respuesta, otro.nombre)
