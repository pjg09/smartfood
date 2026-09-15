"""`DT-27`. El padrón de la institución.

**No es una tarea de sprint**: es trabajo sobre lo ya entregado, pedido al mirar
el producto contra su referencia visual (`DT-23`). Lo que sí trae es una
excepción declarada a `DT-2` —la única pantalla de `INT-3` construida a mano— y
eso es lo que estas pruebas vigilan, además de la pantalla:

1. **Solo la institución.** El padrón lleva nombre, documento y correo de los
   acudientes de menores matriculados. No es una lista que pueda ver la
   cafetería, y la regla vive en el selector, no en la vista (`DT-11`, `[S11]`).
2. **Solo lee.** No hay formulario, no hay servicio detrás y cada fila enlaza al
   admin. Si algún día aparece una escritura aquí, `INV-4` obliga a volver a
   mirar quién puede.
3. **Los retirados no salen por defecto**, y desactivado no es retirado.
"""

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, EstadoDelEstudiante, Estudiante
from personas.selectors import cuentas_sin_activar, padron
from personas.services import dar_de_baja


def familia(sufijo="1", nombre="Ana Sofía Restrepo Ruiz", con_contrasena=True):
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente{sufijo}@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
    )
    if con_contrasena:
        usuario.set_password("clave-de-prueba-2026")
        usuario.save(update_fields=["password"])
    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"4300000{sufijo}"
    )
    return Estudiante.objects.create(
        nombre=nombre,
        documento=f"100000000{sufijo}",
        acudiente=acudiente,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )


def institucion(email="institucion@example.com"):
    return Usuario.objects.crear_usuario(
        email=email, rol=Rol.INSTITUCION, nombre="Colegio"
    )


class ElPadronEsDeLaInstitucionTest(TestCase):
    """`[S11]`, `HU-44` tercer criterio, y en el selector (`DT-11`)."""

    def setUp(self):
        self.institucion = institucion()
        self.estudiante = familia()

    def test_la_institucion_ve_el_padron(self):
        self.assertIn(self.estudiante, padron(actor=self.institucion))

    def test_ningun_otro_rol_lo_ve(self):
        """Incluida la cafetería: el padrón es una lista de menores con el correo
        de sus acudientes, y `[S11]` no se la concede."""
        for rol in [Rol.ACUDIENTE, Rol.ADMINISTRADOR, Rol.CAJERO]:
            with self.subTest(rol=rol):
                actor = Usuario.objects.crear_usuario(
                    email=f"{rol}@example.com", rol=rol, nombre="Otro"
                )
                with self.assertRaises(PermissionDenied):
                    padron(actor=actor)

    def test_sin_sesion_tampoco(self):
        with self.assertRaises(PermissionDenied):
            padron(actor=None)

    def test_una_cuenta_desactivada_no_opera(self):
        self.institucion.is_active = False
        self.institucion.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            padron(actor=self.institucion)


class ElPadronDiceQuienEstaMatriculadoHoyTest(TestCase):
    def setUp(self):
        self.institucion = institucion()
        self.activo = familia("1", "Ana Sofía Restrepo Ruiz")
        self.desactivado = familia("2", "Bruno Gómez Lara")
        self.desactivado.estado = EstadoDelEstudiante.DESACTIVADO
        self.desactivado.save(update_fields=["estado"])
        self.retirado = familia("3", "Carla Ospina Díaz")
        dar_de_baja(actor=self.institucion, estudiante=self.retirado)

    def test_los_retirados_no_salen_por_defecto(self):
        """`HU-51`: la baja es un estado y conserva el historial, pero el padrón
        responde «quién está matriculado hoy»."""
        self.assertNotIn(self.retirado, padron(actor=self.institucion))

    def test_desactivado_no_es_retirado(self):
        """Un estudiante sin tarjeta (`HU-47`, `HU-48`) **sigue matriculado**.
        Confundirlos lo escondería del padrón justo cuando hay que arreglarlo."""
        self.assertIn(self.desactivado, padron(actor=self.institucion))

    def test_con_retirados_salen_todos(self):
        completo = padron(actor=self.institucion, incluir_retirados=True)

        self.assertIn(self.retirado, completo)
        self.assertIn(self.activo, completo)

    def test_se_busca_por_las_cinco_vias(self):
        """Nombre, documento, tarjeta, nombre del acudiente y su correo: las
        cinco formas en que alguien pregunta por un estudiante en secretaría."""
        casos = {
            "nombre": "Restrepo",
            "documento": self.activo.documento,
            "tarjeta": self.activo.codigo_tarjeta,
            "acudiente": "Ruiz Ochoa",
            "correo": self.activo.acudiente.usuario.email,
        }
        for via, termino in casos.items():
            with self.subTest(via=via):
                self.assertIn(
                    self.activo, padron(actor=self.institucion, busqueda=termino)
                )

    def test_la_busqueda_no_distingue_mayusculas(self):
        self.assertIn(self.activo, padron(actor=self.institucion, busqueda="rEsTrEpO"))

    def test_una_busqueda_vacia_devuelve_el_padron_entero(self):
        self.assertEqual(padron(actor=self.institucion, busqueda="   ").count(), 2)

    def test_cuenta_los_acudientes_sin_activar(self):
        """El dato que trae a secretaría: la carga genera la invitación pero no
        la entrega (`DEC-9`), así que alguien tiene que saber quién no puede
        entrar todavía."""
        familia("4", "Diana Peña Vera", con_contrasena=False)

        self.assertEqual(cuentas_sin_activar(list(padron(actor=self.institucion))), 1)


class LaPantallaDelPadronTest(TestCase):
    def setUp(self):
        self.institucion = institucion()
        self.estudiante = familia()
        self.sin_activar = familia("2", "Bruno Gómez Lara", con_contrasena=False)
        self.client.force_login(self.institucion)
        self.url = reverse("padron")
        self.tabla = reverse("padron-tabla")

    def test_la_pantalla_lista_a_los_estudiantes(self):
        cuerpo = self.client.get(self.url).content.decode()

        self.assertIn("Padrón de estudiantes", cuerpo)
        self.assertIn(self.estudiante.nombre, cuerpo)
        self.assertIn(self.estudiante.codigo_tarjeta, cuerpo)
        self.assertIn(self.estudiante.acudiente.usuario.email, cuerpo)

    def test_distingue_la_cuenta_activa_de_la_que_no(self):
        cuerpo = self.client.get(self.url).content.decode()

        self.assertIn("data-cuenta-activa", cuerpo)
        self.assertIn("data-cuenta-sin-activar", cuerpo)
        self.assertIn("1 sin activar", cuerpo)

    def test_cada_fila_enlaza_al_admin_para_editar(self):
        """**El padrón no edita.** Escribir sobre un estudiante sigue siendo de
        `INT-3` (`DT-2`); duplicar el formulario duplicaría sus reglas."""
        cuerpo = self.client.get(self.url).content.decode()

        self.assertIn(
            reverse("admin:personas_estudiante_change", args=[self.estudiante.id]),
            cuerpo,
        )

    def test_la_pantalla_no_escribe(self):
        """No hay `POST`, y no es un descuido: es lo que mantiene la excepción a
        `DT-2` acotada a una lectura."""
        self.assertEqual(self.client.post(self.url).status_code, 405)

    def test_la_tabla_es_un_fragmento_y_no_una_pagina(self):
        """`DT-16`. Dos rutas a la misma vista: lo que cambia es el envoltorio,
        no lo que se responde."""
        cuerpo = self.client.get(self.tabla, {"busqueda": ""}).content.decode()

        self.assertNotIn("<html", cuerpo)
        self.assertNotIn("<body", cuerpo)
        self.assertIn('id="padron-tabla"', cuerpo)

    def test_el_buscador_filtra_la_tabla(self):
        cuerpo = self.client.get(self.tabla, {"busqueda": "Restrepo"}).content.decode()

        self.assertIn("Ana Sofía Restrepo Ruiz", cuerpo)
        self.assertNotIn("Bruno Gómez Lara", cuerpo)

    def test_una_busqueda_sin_resultados_dice_que_hacer(self):
        """No «0 resultados» a secas: puede que se haya retirado, y eso se
        arregla marcando la casilla."""
        cuerpo = self.client.get(self.tabla, {"busqueda": "zzzzz"}).content.decode()

        self.assertIn("Ningún estudiante coincide", cuerpo)
        self.assertIn("Ver retirados", cuerpo)

    def test_el_recuento_dice_cuantos_de_cuantos(self):
        """«1 de 2» y no «1»: quien busca necesita saber que hay más."""
        cuerpo = self.client.get(self.tabla, {"busqueda": "Restrepo"}).content.decode()

        self.assertIn("data-recuento-del-padron", cuerpo)
        self.assertIn("de 2", cuerpo)

    def test_la_casilla_de_retirados_los_trae(self):
        retirado = familia("3", "Carla Ospina Díaz")
        dar_de_baja(actor=self.institucion, estudiante=retirado)

        sin = self.client.get(self.tabla).content.decode()
        con = self.client.get(self.tabla, {"retirados": "1"}).content.decode()

        self.assertNotIn("Carla Ospina Díaz", sin)
        self.assertIn("Carla Ospina Díaz", con)
        self.assertIn("Retirado", con)

    def test_ningun_otro_rol_llega_a_la_pantalla(self):
        for rol in [Rol.ACUDIENTE, Rol.ADMINISTRADOR, Rol.CAJERO]:
            with self.subTest(rol=rol):
                self.client.force_login(
                    Usuario.objects.crear_usuario(
                        email=f"{rol}@example.com", rol=rol, nombre="Otro"
                    )
                )
                self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_sin_sesion_manda_a_la_pantalla_de_acceso(self):
        self.client.logout()

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("acceso"), respuesta.headers["Location"])

    def test_el_padron_esta_en_el_menu_de_la_institucion(self):
        cuerpo = self.client.get(reverse("carga-de-estudiantes")).content.decode()

        self.assertIn(reverse("padron"), cuerpo)
