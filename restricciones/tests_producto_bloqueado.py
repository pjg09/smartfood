"""`TT-97`, `TT-98`, `TT-99`. Bloqueo de un producto puntual (`HU-10`, `ALC-IN-08`).

Los dos criterios de `HU-10`, uno por uno:

1. **El bloqueo aplica a un producto identificado del catálogo.** Lo que queda
   escrito es una clave ajena, no un nombre: renombrar el producto mañana no
   desbloquea nada.
2. **Se distingue explícitamente del bloqueo por alérgeno (`HU-11`).** Aquí eso
   no es una etiqueta ni un comentario: es una tabla aparte y, sobre todo, un
   comportamiento distinto. `ElBloqueoDeProductoNoEsElDeAlergenoTest` lo
   comprueba donde se nota — dos productos que comparten alérgeno, uno
   bloqueado, y el otro **sigue comprable**.

La segunda clase es la que importa conservar. `INV-5` se rompe con una decisión
de modelado que parece una optimización —unificar las dos restricciones en una
tabla con un campo «tipo», y de ahí implementar el alérgeno como lista de
productos—, y cuando eso pase esta prueba será la que lo note: un bloqueo por
producto que arrastra a sus hermanos de alérgeno es exactamente el síntoma.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Alergeno, Categoria, Producto, ProductoAlergeno
from cuentas.models import Rol, Usuario
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from restricciones.models import RestriccionProducto
from restricciones.selectors import (
    identificadores_de_productos_bloqueados,
    productos_bloqueados_de,
)
from restricciones.services import bloquear_producto, desbloquear_producto

CLAVE = "clave-de-prueba-2026"


def acudiente_con_estudiantes(sufijo="1", estudiantes=1):
    """Un acudiente con su cuenta y `n` estudiantes a cargo."""
    usuario = Usuario.objects.crear_usuario(
        email=f"acudiente-p{sufijo}@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])

    acudiente = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento=f"7351234{sufijo}"
    )
    hijos = [
        Estudiante.objects.create(
            nombre=f"Estudiante P{sufijo}{i}",
            documento=f"700{sufijo}00{i}",
            acudiente=acudiente,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )
        for i in range(estudiantes)
    ]
    return usuario, acudiente, hijos


def cuenta(rol, sufijo):
    """Una cuenta de un rol cualquiera, para probar quién NO puede."""
    usuario = Usuario.objects.crear_usuario(
        email=f"{rol}-p{sufijo}@example.com", rol=rol, nombre=f"Cuenta {rol}"
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
    return usuario


def producto(nombre, precio="3500", categoria=None):
    categoria = categoria or Categoria.objects.get_or_create(nombre="Prueba")[0]
    return Producto.objects.create(
        nombre=nombre, precio=Decimal(precio), categoria=categoria
    )


class ElBloqueoEsDeUnProductoIdentificadoTest(TestCase):
    """Primer criterio de `HU-10`."""

    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiantes()
        self.empanada = producto("Empanada de carne")
        self.jugo = producto("Jugo de mora", "2500")

    def test_bloquear_deja_ese_producto_y_solo_ese(self):
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.empanada
        )

        bloqueados = identificadores_de_productos_bloqueados(self.estudiante)
        self.assertIn(self.empanada.id, bloqueados)
        self.assertNotIn(self.jugo.id, bloqueados)

    def test_el_bloqueo_sobrevive_a_un_cambio_de_nombre(self):
        """Lo que queda escrito es la clave ajena, no el nombre."""
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.empanada
        )

        self.empanada.nombre = "Empanada criolla"
        self.empanada.save(update_fields=["nombre"])

        self.assertIn(
            self.empanada.id, identificadores_de_productos_bloqueados(self.estudiante)
        )

    def test_desbloquear_retira_solo_ese_producto(self):
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.empanada
        )
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.jugo
        )

        retirado = desbloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.empanada
        )

        self.assertTrue(retirado)
        self.assertEqual(
            identificadores_de_productos_bloqueados(self.estudiante), {self.jugo.id}
        )


class LaListaEsPorEstudianteTest(TestCase):
    def setUp(self):
        self.usuario, _, self.hijos = acudiente_con_estudiantes(estudiantes=2)
        self.gaseosa = producto("Gaseosa")

    def test_bloquear_a_un_hijo_no_bloquea_al_otro(self):
        uno, otro = self.hijos

        bloquear_producto(actor=self.usuario, estudiante=uno, producto=self.gaseosa)

        self.assertIn(self.gaseosa.id, identificadores_de_productos_bloqueados(uno))
        self.assertEqual(identificadores_de_productos_bloqueados(otro), set())


class ElBloqueoDeProductoNoEsElDeAlergenoTest(TestCase):
    """Segundo criterio de `HU-10`, comprobado donde de verdad se distingue.

    **Esta es la prueba que hay que conservar entera.** No mira nombres de tabla:
    mira el comportamiento. Si algún día alguien unifica las dos restricciones y
    empieza a resolver el alérgeno como «los productos que hoy lo declaran»,
    bloquear uno arrastrará a sus hermanos y esto fallará.
    """

    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiantes()
        self.mani = Alergeno.objects.create(nombre="Maní")

        self.torta = producto("Torta de chocolate", "4000")
        self.galleta = producto("Galleta de maní", "1500")
        for p in (self.torta, self.galleta):
            ProductoAlergeno.objects.create(producto=p, alergeno=self.mani)

    def test_bloquear_un_producto_no_bloquea_a_los_que_comparten_alergeno(self):
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.torta
        )

        bloqueados = identificadores_de_productos_bloqueados(self.estudiante)
        self.assertIn(self.torta.id, bloqueados)
        self.assertNotIn(
            self.galleta.id,
            bloqueados,
            "bloquear un producto arrastró a otro que comparte alérgeno: las dos "
            "restricciones se están resolviendo como si fueran la misma, y eso es "
            "lo que INV-5 prohíbe (HU-10 segundo criterio, HU-11).",
        )

    def test_un_producto_nuevo_con_el_mismo_alergeno_no_queda_bloqueado(self):
        """Y **debe** ser así: cubrirlo es `HU-11`, no esta historia.

        Dicho de otro modo: que esto pase demuestra que `HU-10` no está haciendo
        el trabajo de `HU-11` por accidente. Cuando `TT-100` exista, el mismo
        escenario con una restricción de alérgeno tendrá que dar lo contrario
        —y esa es `TT-103`—.
        """
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.torta
        )

        brownie = producto("Brownie con maní", "3000")
        ProductoAlergeno.objects.create(producto=brownie, alergeno=self.mani)

        self.assertNotIn(
            brownie.id, identificadores_de_productos_bloqueados(self.estudiante)
        )


class SoloElAcudienteBloqueaTest(TestCase):
    """`INV-4` sobre la fila «Configurar y retirar restricciones» de `[S11]`.

    Se llama al **servicio** con cada rol, no se mira la pantalla: `DT-11` pone
    la regla en la capa de datos, y un botón oculto lo salta cualquiera que
    escriba la URL.
    """

    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiantes()
        self.gaseosa = producto("Gaseosa")

    def _rechaza_bloquear(self, actor):
        with self.assertRaises(PermissionDenied):
            bloquear_producto(
                actor=actor, estudiante=self.estudiante, producto=self.gaseosa
            )
        self.assertEqual(identificadores_de_productos_bloqueados(self.estudiante), set())

    def test_el_cajero_no_bloquea(self):
        self._rechaza_bloquear(cuenta(Rol.CAJERO, "a"))

    def test_la_administracion_de_la_cafeteria_no_bloquea(self):
        self._rechaza_bloquear(cuenta(Rol.ADMINISTRADOR, "a"))

    def test_la_institucion_educativa_no_bloquea(self):
        self._rechaza_bloquear(cuenta(Rol.INSTITUCION, "a"))

    def test_otro_acudiente_no_bloquea_a_un_hijo_ajeno(self):
        ajeno, _, _ = acudiente_con_estudiantes(sufijo="2")
        self._rechaza_bloquear(ajeno)

    def test_sin_cuenta_identificada_no_se_bloquea(self):
        self._rechaza_bloquear(None)

    def test_una_cuenta_de_acudiente_desactivada_no_bloquea(self):
        self.usuario.is_active = False
        self.usuario.save(update_fields=["is_active"])
        self._rechaza_bloquear(self.usuario)

    def test_la_cafeteria_tampoco_DESBLOQUEA_lo_que_puso_la_familia(self):
        """`INV-4` en su forma literal: la cafetería no desactiva la restricción."""
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.gaseosa
        )

        for rol in (Rol.CAJERO, Rol.ADMINISTRADOR, Rol.INSTITUCION):
            with self.subTest(rol=rol):
                with self.assertRaises(PermissionDenied):
                    desbloquear_producto(
                        actor=cuenta(rol, f"d{rol}"),
                        estudiante=self.estudiante,
                        producto=self.gaseosa,
                    )

        self.assertIn(
            self.gaseosa.id, identificadores_de_productos_bloqueados(self.estudiante)
        )


class BloquearDosVecesNoEsBloquearMasTest(TestCase):
    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiantes()
        self.gaseosa = producto("Gaseosa")

    def test_el_servicio_es_idempotente(self):
        uno = bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.gaseosa
        )
        otro = bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.gaseosa
        )

        self.assertEqual(uno.id, otro.id)
        self.assertEqual(productos_bloqueados_de(self.estudiante).count(), 1)

    def test_desbloquear_lo_que_no_estaba_no_es_un_error(self):
        self.assertFalse(
            desbloquear_producto(
                actor=self.usuario, estudiante=self.estudiante, producto=self.gaseosa
            )
        )

    def test_la_base_impide_el_duplicado_aunque_nadie_pase_por_el_servicio(self):
        RestriccionProducto.objects.create(
            estudiante=self.estudiante, producto=self.gaseosa
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            RestriccionProducto.objects.create(
                estudiante=self.estudiante, producto=self.gaseosa
            )


class LaPantallaDeProductosBloqueadosTest(TestCase):
    """`TT-99`. La pantalla del acudiente (`INT-1`)."""

    def setUp(self):
        self.usuario, _, (self.estudiante,) = acudiente_con_estudiantes()
        self.empanada = producto("Empanada de carne")
        self.jugo = producto("Jugo de mora", "2500")
        self.url = reverse("productos-bloqueados", args=[self.estudiante.id])
        self.url_bloqueo = reverse("bloqueo-de-producto", args=[self.estudiante.id])

    def _entrar(self):
        self.client.login(email=self.usuario.email, password=CLAVE)

    def test_el_acudiente_ve_el_catalogo(self):
        self._entrar()
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Empanada de carne")
        self.assertContains(respuesta, "Jugo de mora")

    def test_sin_sesion_se_redirige_al_acceso(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("acceso"), respuesta["Location"])

    def test_el_cajero_recibe_403(self):
        cajero = cuenta(Rol.CAJERO, "pantalla")
        self.client.login(email=cajero.email, password=CLAVE)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_un_estudiante_ajeno_es_un_404(self):
        _, _, (ajeno,) = acudiente_con_estudiantes(sufijo="2")
        self._entrar()
        respuesta = self.client.get(reverse("productos-bloqueados", args=[ajeno.id]))
        self.assertEqual(respuesta.status_code, 404)

    def test_el_interruptor_bloquea_y_devuelve_la_lista(self):
        self._entrar()
        respuesta = self.client.post(
            self.url_bloqueo, {"producto": str(self.empanada.id), "accion": "bloquear"}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(
            self.empanada.id, identificadores_de_productos_bloqueados(self.estudiante)
        )
        # Devuelve el fragmento, no la página (`DT-16`).
        self.assertContains(respuesta, 'id="lista-de-productos"')
        self.assertNotContains(respuesta, "<title>")

    def test_el_interruptor_desbloquea(self):
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.empanada
        )
        self._entrar()

        self.client.post(
            self.url_bloqueo,
            {"producto": str(self.empanada.id), "accion": "desbloquear"},
        )

        self.assertEqual(identificadores_de_productos_bloqueados(self.estudiante), set())

    def test_el_cajero_no_puede_bloquear_por_la_url(self):
        cajero = cuenta(Rol.CAJERO, "post")
        self.client.login(email=cajero.email, password=CLAVE)

        respuesta = self.client.post(
            self.url_bloqueo, {"producto": str(self.empanada.id), "accion": "bloquear"}
        )

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(identificadores_de_productos_bloqueados(self.estudiante), set())

    def test_un_producto_inventado_es_un_404(self):
        self._entrar()
        respuesta = self.client.post(
            self.url_bloqueo,
            {"producto": "01a05e10-0000-7000-8000-000000000000", "accion": "bloquear"},
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_el_buscador_filtra_y_devuelve_solo_la_lista(self):
        self._entrar()
        respuesta = self.client.get(
            reverse("productos-bloqueados-lista", args=[self.estudiante.id]),
            {"busqueda": "empanada"},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Empanada de carne")
        self.assertNotContains(respuesta, "Jugo de mora")
        self.assertNotContains(respuesta, "<title>")

    def test_un_producto_retirado_del_catalogo_no_se_ofrece(self):
        self.jugo.activo = False
        self.jugo.save(update_fields=["activo"])
        self._entrar()

        respuesta = self.client.get(self.url)

        self.assertContains(respuesta, "Empanada de carne")
        self.assertNotContains(respuesta, "Jugo de mora")

    def test_la_pantalla_avisa_de_que_esto_no_cubre_alergenos_y_enlaza_alli(self):
        """Sin ese aviso, bloquear «Torta de chocolate» se lee como protección
        frente al maní.

        **Y el aviso enlaza la otra pantalla**, que es lo que se corrigió en la
        revisión del Sprint 3: hasta entonces anunciaba el bloqueo por alérgeno
        como algo que «llega con `HU-11`», y `HU-11` se cerró en `PR-03`. Un
        aviso que nombra una historia pendiente que ya llegó manda al acudiente
        a esperar lo que puede hacer ahora mismo.
        """
        self._entrar()
        respuesta = self.client.get(self.url)

        self.assertContains(respuesta, "data-enlace-a-alergenos")
        self.assertContains(
            respuesta, reverse("alergenos-bloqueados", args=[self.estudiante.id])
        )
        self.assertNotContains(respuesta, "HU-11")

    def test_la_ficha_del_panel_cuenta_los_bloqueados(self):
        """Se afirma sobre la cifra y la URL, no sobre el texto del botón.

        La primera versión de esta prueba buscaba «Cambiar los productos» y se
        rompió en cuanto `TT-102` reescribió la tarjeta para meter también los
        alérgenos. La copia cambia; el recuento en el contexto y la ruta a la
        pantalla, no. Es la misma regla de `CLAUDE.md` que pide buscar un
        `data-*` propio en vez de un trozo de texto.
        """
        bloquear_producto(
            actor=self.usuario, estudiante=self.estudiante, producto=self.empanada
        )
        self._entrar()

        respuesta = self.client.get(reverse("mis-estudiantes"))

        self.assertEqual(respuesta.context["productos_bloqueados"], 1)
        self.assertContains(respuesta, self.url)

    def test_sin_bloqueos_la_ficha_lo_dice_y_ofrece_bloquear(self):
        self._entrar()
        respuesta = self.client.get(reverse("mis-estudiantes"))

        self.assertEqual(respuesta.context["productos_bloqueados"], 0)
        self.assertContains(respuesta, "Ninguna")
        # La puerta a la pantalla sigue ahí aunque no haya nada bloqueado.
        self.assertContains(respuesta, self.url)
