"""`TT-106` … `TT-108`. Permisos sobre las restricciones (`HU-13`, **`INV-4`**).

`HU-13` dice que ni el cajero, ni la administración de la cafetería, ni la
institución educativa pueden desactivar lo que el acudiente configuró. **Este
fichero lo comprueba por los dos caminos por los que podría no ser cierto**, y
los dos hacen falta:

1. **Los servicios**, llamados directamente con cada rol. Es donde vive la regla
   (`DT-15`), y un `PermissionDenied` aquí vale para cualquier vista que llame,
   presente o futura.
2. **Los permisos por modelo** (`DT-11`). Un servicio protege el camino que pasa
   por él; lo que impide que aparezca un segundo camino —el admin— es que el
   permiso no exista.

Ocultar el botón en la plantilla no es cumplir `INV-4`, es aparentarlo. Por eso
aquí no se mira ni una pantalla.

**`HU-13` no se cierra con este PR**: su primer criterio pide que el cajero **vea**
las restricciones al cobrar, y ese bloque es `TT-109`, en `PR-06`. Lo que queda
demostrado aquí es la otra mitad — que no puede tocarlas.
"""

from decimal import Decimal

from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from catalogo.models import Alergeno, Categoria, Producto
from cuentas.models import Rol, Usuario
from cuentas.permisos import (
    APPS_SIN_ESCRITURA_PARA_NINGUN_ROL,
    ESCRITURA_PROHIBIDA,
    nombre_del_grupo,
)
from cuentas.services import sincronizar_grupos_y_permisos
from personas.codigo import generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from restricciones.selectors import restricciones_vigentes
from restricciones.services import (
    bloquear_alergeno,
    bloquear_producto,
    desbloquear_alergeno,
    desbloquear_producto,
    fijar_limite_diario,
    retirar_limite_diario,
)

CLAVE = "clave-de-prueba-2026"
# Los tres roles que `INV-4` deja fuera. El acudiente no está: es el único que sí.
ROLES_SIN_ESCRITURA = (Rol.CAJERO, Rol.ADMINISTRADOR, Rol.INSTITUCION)


def escenario():
    usuario = Usuario.objects.crear_usuario(
        email="acudiente-perm@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz"
    )
    usuario.set_password(CLAVE)
    usuario.save(update_fields=["password"])
    ficha = Acudiente.objects.create(
        usuario=usuario, nombre="Marta Ruiz Ochoa", documento="9990012345"
    )
    estudiante = Estudiante.objects.create(
        nombre="Ana Sofía Restrepo Ruiz",
        documento="1009990001",
        acudiente=ficha,
        codigo_tarjeta=generar_codigo_de_tarjeta(),
    )
    categoria, _ = Categoria.objects.get_or_create(nombre="Prueba")
    producto, _ = Producto.objects.get_or_create(
        nombre="Gaseosa", defaults={"precio": Decimal("2500"), "categoria": categoria}
    )
    alergeno, _ = Alergeno.objects.get_or_create(nombre="Maní")
    return usuario, estudiante, producto, alergeno


def cuenta(rol):
    u = Usuario.objects.crear_usuario(
        email=f"{rol}-perm@example.com", rol=rol, nombre=f"Cuenta {rol}"
    )
    u.set_password(CLAVE)
    u.save(update_fields=["password"])
    return u


class LaCafeteriaYElColegioNoEscribenRestriccionesTest(TestCase):
    """`TT-108`. Los seis servicios, con los tres roles. Dieciocho puertas.

    Se llama al **servicio**, no a la vista: `DT-15` pone la regla ahí para que
    no dependa de por dónde se entre, y probarla en la vista solo demostraría que
    esa vista la respeta.
    """

    def setUp(self):
        self.acudiente, self.estudiante, self.producto, self.alergeno = escenario()
        # Se deja todo configurado por su acudiente: lo que se comprueba es que
        # nadie más pueda **quitarlo**, que es literalmente `HU-13`.
        fijar_limite_diario(
            actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("8000")
        )
        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.producto
        )
        bloquear_alergeno(
            actor=self.acudiente, estudiante=self.estudiante, alergeno=self.alergeno
        )

    def _escrituras(self, actor):
        return {
            "fijar_limite_diario": lambda: fijar_limite_diario(
                actor=actor, estudiante=self.estudiante, monto=Decimal("99000")
            ),
            "retirar_limite_diario": lambda: retirar_limite_diario(
                actor=actor, estudiante=self.estudiante
            ),
            "bloquear_producto": lambda: bloquear_producto(
                actor=actor, estudiante=self.estudiante, producto=self.producto
            ),
            "desbloquear_producto": lambda: desbloquear_producto(
                actor=actor, estudiante=self.estudiante, producto=self.producto
            ),
            "bloquear_alergeno": lambda: bloquear_alergeno(
                actor=actor, estudiante=self.estudiante, alergeno=self.alergeno
            ),
            "desbloquear_alergeno": lambda: desbloquear_alergeno(
                actor=actor, estudiante=self.estudiante, alergeno=self.alergeno
            ),
        }

    def test_ninguno_de_los_tres_roles_escribe_ninguna_restriccion(self):
        for rol in ROLES_SIN_ESCRITURA:
            actor = cuenta(rol)
            for nombre, escribir in self._escrituras(actor).items():
                with self.subTest(rol=rol, servicio=nombre):
                    with self.assertRaises(PermissionDenied):
                        escribir()

    def test_y_lo_configurado_sigue_en_pie_despues_de_intentarlo(self):
        """La comprobación que de verdad importa: **no se movió nada**.

        Un `PermissionDenied` por servicio demuestra que cada puerta cierra;
        esto demuestra el efecto, que es lo que `HU-13` promete al acudiente.
        """
        for rol in ROLES_SIN_ESCRITURA:
            actor = cuenta(rol)
            for escribir in self._escrituras(actor).values():
                with self.assertRaises(PermissionDenied):
                    escribir()

        vigentes = restricciones_vigentes(self.estudiante)
        self.assertEqual(vigentes.limite.monto, Decimal("8000.00"))
        self.assertEqual(vigentes.productos.count(), 1)
        self.assertEqual(vigentes.alergenos.count(), 1)

    def test_el_acudiente_si_puede(self):
        """El contraste. Sin esto, la prueba de arriba pasaría con un servicio
        que rechazara a todo el mundo."""
        self.assertTrue(
            retirar_limite_diario(actor=self.acudiente, estudiante=self.estudiante)
        )


class NingunRolTienePermisoDeAdminSobreRestriccionesTest(TestCase):
    """`TT-107`. La segunda mitad de `INV-4`, en la capa de datos (`DT-11`).

    Un servicio protege el camino que pasa por él. Lo que impide que aparezca un
    segundo camino —registrar los modelos en el admin y concederlos— es que el
    permiso no exista.
    """

    def setUp(self):
        sincronizar_grupos_y_permisos()

    def _permisos_de(self, rol):
        grupo = Group.objects.get(name=nombre_del_grupo(rol))
        return {
            f"{p.content_type.app_label}.{p.codename}" for p in grupo.permissions.all()
        }

    def test_ningun_rol_escribe_sobre_la_app_restricciones(self):
        """Por **prefijo de app**, no por lista de modelos.

        Un modelo nuevo dentro de `restricciones` —el asiento de `TT-104` lo
        fue— queda cubierto sin que nadie se acuerde de añadirlo aquí.
        """
        for app in APPS_SIN_ESCRITURA_PARA_NINGUN_ROL:
            for rol in Rol:
                with self.subTest(app=app, rol=rol):
                    culpables = {
                        p
                        for p in self._permisos_de(rol)
                        if p.startswith(f"{app}.")
                        and any(a in p for a in ("add_", "change_", "delete_"))
                    }
                    self.assertEqual(
                        culpables,
                        set(),
                        f"«{rol}» escribe sobre {app}: {culpables}. El control "
                        "parental es del acudiente y no se toca desde el admin "
                        "(INV-4, HU-13, DT-11).",
                    )

    def test_la_institucion_esta_declarada_en_escritura_prohibida(self):
        """`INV-4` nombra a la institución y el tercer criterio de `HU-13` también.

        Faltaba: el diccionario solo tenía los dos roles de la cafetería, así que
        media invariante estaba declarada y la otra media no.
        """
        self.assertIn(Rol.INSTITUCION, ESCRITURA_PROHIBIDA)
        self.assertIn(
            "restricciones alimentarias", ESCRITURA_PROHIBIDA[Rol.INSTITUCION]
        )

    def test_los_modelos_de_restricciones_existen_de_verdad(self):
        """Si la app se renombrara, la prueba de arriba pasaría sin proteger nada.

        Es la trampa de comprobar una ausencia: se cumple sola cuando no hay
        nada que comprobar.
        """
        modelos = {
            p.content_type.model
            for p in Permission.objects.filter(
                content_type__app_label="restricciones"
            )
        }
        self.assertTrue(
            {"limitediario", "restriccionproducto", "restriccionalergeno"} <= modelos,
            f"faltan modelos de restricciones en los permisos: {modelos}",
        )


class ElSelectorCompuestoLeeLasTresTest(TestCase):
    """`TT-106`. Las tres restricciones juntas, porque juntas significan algo."""

    def setUp(self):
        self.acudiente, self.estudiante, self.producto, self.alergeno = escenario()

    def test_sin_nada_configurado_no_hay_ninguna(self):
        vigentes = restricciones_vigentes(self.estudiante)

        self.assertIsNone(vigentes.limite)
        self.assertEqual(list(vigentes.productos), [])
        self.assertEqual(list(vigentes.alergenos), [])
        self.assertFalse(vigentes.hay_alguna)

    def test_hay_alguna_es_cierto_con_cualquiera_de_las_tres(self):
        """Un `or` olvidado es una pantalla que dice «sin restricciones» sobre
        un niño alérgico."""
        casos = {
            "limite": lambda: fijar_limite_diario(
                actor=self.acudiente, estudiante=self.estudiante, monto=Decimal("8000")
            ),
            "producto": lambda: bloquear_producto(
                actor=self.acudiente, estudiante=self.estudiante, producto=self.producto
            ),
            "alergeno": lambda: bloquear_alergeno(
                actor=self.acudiente, estudiante=self.estudiante, alergeno=self.alergeno
            ),
        }
        for nombre, configurar in casos.items():
            with self.subTest(restriccion=nombre):
                self.assertFalse(restricciones_vigentes(self.estudiante).hay_alguna)
                configurar()
                self.assertTrue(restricciones_vigentes(self.estudiante).hay_alguna)
                # Se deshace para que cada caso se compruebe aislado.
                if nombre == "limite":
                    retirar_limite_diario(
                        actor=self.acudiente, estudiante=self.estudiante
                    )
                elif nombre == "producto":
                    desbloquear_producto(
                        actor=self.acudiente,
                        estudiante=self.estudiante,
                        producto=self.producto,
                    )
                else:
                    desbloquear_alergeno(
                        actor=self.acudiente,
                        estudiante=self.estudiante,
                        alergeno=self.alergeno,
                    )

    def test_devuelve_las_condiciones_y_no_los_productos_que_hoy_las_declaran(self):
        """`INV-5`. Meter esa lista aquí la convertiría en un dato."""
        bloquear_alergeno(
            actor=self.acudiente, estudiante=self.estudiante, alergeno=self.alergeno
        )

        vigentes = restricciones_vigentes(self.estudiante)

        self.assertEqual(
            [r.alergeno for r in vigentes.alergenos], [self.alergeno]
        )
        self.assertFalse(hasattr(vigentes, "productos_cubiertos"))

    def test_es_por_estudiante(self):
        bloquear_producto(
            actor=self.acudiente, estudiante=self.estudiante, producto=self.producto
        )
        otro = Estudiante.objects.create(
            nombre="Tomás Restrepo Ruiz",
            documento="1009990002",
            acudiente=self.estudiante.acudiente,
            codigo_tarjeta=generar_codigo_de_tarjeta(),
        )

        self.assertTrue(restricciones_vigentes(self.estudiante).hay_alguna)
        self.assertFalse(restricciones_vigentes(otro).hay_alguna)
