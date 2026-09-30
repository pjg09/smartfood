"""Etiquetas de plantilla del armazón de la interfaz (`DT-23`).

**Presentación, no permisos.** Lo que se decide aquí es qué enlaces se dibujan,
y eso no protege nada: quien conozca la ruta la escribe igual. Quién puede
entrar lo deciden el servicio y el selector, que responden `PermissionDenied`
aunque el enlace nunca se haya visto (`DT-11`, `DT-15`) — `INV-4` se sostiene en
la capa de datos, **no escondiendo botones**.

Existe para que el HTML de un enlace de la barra se escriba una sola vez: la
misma lista se pinta en la barra lateral y en el cajón de móvil, y con dos
copias la segunda se queda atrás al primer ajuste.
"""

from dataclasses import dataclass

from django import template
from django.utils import timezone

from cuentas.models import Rol

register = template.Library()


@dataclass(frozen=True)
class Entrada:
    """Una entrada del menú.

    `ruta` es el nombre de la URL, no la URL: se resuelve en la plantilla con
    `{% url %}`, que es lo que hace que renombrar una ruta no deje aquí un
    enlace roto y silencioso.

    `familia` marca la entrada como actual también en las rutas que cuelgan de
    ella. Hace falta por el admin: un modelo no es una ruta sino seis —listado,
    añadir, editar, borrar, historial— y quien está editando un producto sigue
    estando en «Productos». Sin esto, la barra se queda sin ninguna entrada
    marcada en cuanto se pulsa «Editar», que es la mitad del tiempo.
    """

    ruta: str
    etiqueta: str
    icono: str
    familia: str = ""


def _es_la_actual(entrada, ruta_actual):
    """Si esta entrada es donde está quien mira."""
    if not ruta_actual:
        return False
    if entrada.familia:
        return ruta_actual.startswith(entrada.familia)
    return entrada.ruta == ruta_actual


def _pintables(entradas, ruta_actual):
    """Las entradas con su estado ya resuelto.

    Se calcula aquí y no en la plantilla porque `startswith` no existe en el
    lenguaje de plantillas, y porque el estado de la barra es una decisión, no
    una condición de presentación repetida cuatro veces en el HTML.
    """
    return [
        {
            "ruta": e.ruta,
            "etiqueta": e.etiqueta,
            "icono": e.icono,
            "activa": _es_la_actual(e, ruta_actual),
        }
        for e in entradas
    ]


# El inicio es la portada pública. **Ya no está en el menú de ningún rol**
# (`DEC-16`): quien tiene sesión no la ve —`/` lo reparte a su panel—, así que
# una entrada «Inicio» prometía una pantalla y llevaba a otra. Se conserva como
# destino de reserva para un rol sin menú propio.
INICIO = Entrada("inicio", "Inicio", "i-inicio")


def _del_admin(modelo, etiqueta, icono):
    """Una sección que vive dentro del admin (`INT-3`, `DT-2`).

    `DEC-16`: cada rol es **un** dashboard, así que llegar a «Productos» no
    puede exigir salir a otra aplicación y buscarlo en un índice. La entrada es
    normal; lo único propio es la `familia`, el prefijo que comparten las seis
    rutas de un modelo.
    """
    return Entrada(
        f"admin:{modelo}_changelist", etiqueta, icono, familia=f"admin:{modelo}_"
    )


# `USR-3` cobra en el punto de venta (`INT-2`). El icono es un escáner y no la
# tarjeta: la tarjeta es la credencial del estudiante, y lo que el cajero
# reconoce de su pantalla es el lector.
PUNTO_DE_VENTA = Entrada("punto-de-venta", "Punto de venta", "i-escaner")

# `HU-24`. La cola de reservas pendientes, que **comparten los dos roles de la
# cafetería** (`USR-3` y `USR-4`): quien prepara y quien entrega no tienen que
# ser la misma persona (`FUN-5`). Por eso la entrada aparece en los dos menús y
# no en uno.
RESERVAS = Entrada("reservas", "Reservas", "i-cafeteria")

# `HU-55`, `DEC-6`. El cuadre del efectivo de la jornada, que es **solo del
# cajero**: la administración consulta los cierres (`HU-56`), no los hace. Por
# eso esta entrada está en los dos sitios donde está el cajero y en ninguno más.
CIERRE_DE_CAJA = Entrada("cierre-de-caja", "Cierre de caja", "i-efectivo")

# Cada menú es **lo que ese rol alcanza, entero**, y el orden es el de su
# trabajo: primero lo que abre a diario, después lo que toca cuando algo cambia.
# Lo que no aparece aquí es lo que `[S11]` no le concede, y la barra no lo
# esconde por seguridad —eso lo hacen el servicio y el selector (`DT-11`)— sino
# porque un enlace a un `403` no es navegación.
MENU_POR_ROL = {
    # `USR-2` entra desde el teléfono (`INT-1`) y a lo suyo: sus estudiantes.
    Rol.ACUDIENTE: (Entrada("mis-estudiantes", "Mis estudiantes", "i-estudiantes"),),
    # `USR-5`: el padrón que secretaría abre a diario (`DT-27`), la carga de
    # principio de curso (`HU-01`) y las cuatro fichas que administra.
    Rol.INSTITUCION: (
        Entrada("padron", "Padrón", "i-estudiantes"),
        Entrada("carga-de-estudiantes", "Cargar estudiantes", "i-cargar"),
        _del_admin("personas_estudiante", "Estudiantes", "i-identificacion"),
        _del_admin("personas_acudiente", "Acudientes", "i-personas"),
        _del_admin("restricciones_restriccionesdelestudiante", "Restricciones", "i-restriccion"),
        _del_admin("cuentas_usuario", "Usuarios", "i-candado"),
        _del_admin("personas_institucion", "Institución", "i-colegio"),
    ),
    # `USR-4`: la cafetería. El catálogo y el inventario son lo que administra;
    # ventas, cierres y auditoría, lo que consulta. La cola de reservas no vive
    # en el admin (`DT-34`) y va con lo demás igualmente.
    Rol.ADMINISTRADOR: (
        Entrada("panel-de-la-cafeteria", "Panel", "i-grafica"),
        Entrada("reservas", "Reservas", "i-cafeteria"),
        _del_admin("catalogo_producto", "Productos", "i-manzana"),
        _del_admin("catalogo_categoria", "Categorías", "i-etiqueta"),
        _del_admin("catalogo_alergeno", "Alérgenos", "i-alerta"),
        _del_admin("inventario_movimientoinventario", "Inventario", "i-inventario"),
        _del_admin("inventario_merma", "Mermas", "i-restriccion"),
        _del_admin("ventas_venta", "Ventas", "i-recibo"),
        _del_admin("ventas_cierredecaja", "Cierres de caja", "i-efectivo"),
        _del_admin("restricciones_restriccionesdelestudiante", "Restricciones", "i-escudo"),
        Entrada("auditoria", "Auditoría", "i-documento"),
    ),
    # `USR-3` cobra, y cobrar ocurre entero en `INT-2`. **Sin entrada a la
    # administración**: no tiene un solo permiso sobre ningún modelo, así que
    # el admin le enseñaba un índice vacío. Un enlace a una pantalla sin nada
    # dentro es peor que no tenerlo — invita a buscar allí lo que está en su
    # propia caja.
    Rol.CAJERO: (PUNTO_DE_VENTA, RESERVAS, CIERRE_DE_CAJA),
}

# La barra del punto de venta. **Es una lista aparte**, y tiene tres entradas:
# la caja, la cola de reservas (`HU-24`) y el cierre de la jornada (`HU-55`). La
# cocina sigue sin existir y no se dibujan huecos por adelantado.
#
# Va separada de `MENU_POR_ROL[Rol.CAJERO]` porque son dos sitios distintos: en
# la barra de la aplicación el cajero necesita poder salir del punto de venta, y
# en el punto de venta necesita justo lo contrario — `INT-2` pide atender toda
# la demanda del descanso en veinte minutos, y un menú ahí solo son sitios a los
# que llegar por error con cola delante.
MENU_DEL_PUNTO_DE_VENTA = (PUNTO_DE_VENTA, RESERVAS, CIERRE_DE_CAJA)


@register.simple_tag
def saludo():
    """«Buenos días», «Buenas tardes» o «Buenas noches», según la hora.

    Usa `timezone.localtime`, no `datetime.now`: el proyecto corre con
    `USE_TZ`, así que la hora sin convertir es UTC y a las 20:00 de Colombia
    saludaría con «Buenos días».

    Los cortes son las 12 y las 19. No hay una regla universal para el segundo
    —según a quién se pregunte son las 19, las 20 o el anochecer— y lo que
    importa aquí es que no diga «buenas tardes» a las once de la noche.
    """
    hora = timezone.localtime().hour
    if hora < 12:
        return "Buenos días"
    if hora < 19:
        return "Buenas tardes"
    return "Buenas noches"


@register.filter
def nombre_de_pila(nombre):
    """El primer nombre, para saludar.

    `truncatewords:1` no sirve: añade puntos suspensivos, y «Hola, Andrés …»
    parece una frase a medio cargar. Cortar por el primer espacio es lo que se
    quiere decir, y en un nombre vacío devuelve vacío en vez de fallar.
    """
    return (nombre or "").strip().split(" ")[0]


@register.inclusion_tag("partials/navegacion.html", takes_context=True)
def menu_de_navegacion(context, colapsable=True):
    """Las entradas del rol de quien mira, con la actual marcada.

    `colapsable` distingue los dos sitios donde se pinta la misma lista: en la
    barra lateral las etiquetas desaparecen al colapsar, y en el cajón de móvil
    **nunca**, porque ahí no hay colapso que valga y un menú de iconos sueltos
    en un teléfono no se entiende.
    """
    usuario = context.get("user")
    entradas = ()
    if usuario is not None and usuario.is_authenticated:
        entradas = MENU_POR_ROL.get(usuario.rol, (INICIO,))

    # De qué ruta venimos, para marcar la entrada activa. `resolver_match` es
    # `None` en un 404 y en las páginas de error, así que no se da por hecho.
    peticion = context.get("request")
    coincidencia = getattr(peticion, "resolver_match", None)

    return {
        "entradas": _pintables(entradas, getattr(coincidencia, "view_name", None)),
        "colapsable": colapsable,
    }


@register.inclusion_tag("partials/navegacion.html", takes_context=True)
def menu_del_punto_de_venta(context):
    """La barra de iconos del punto de venta (`INT-2`).

    **Siempre colapsada**: la pantalla corre en 1024 x 600 y los 280 px del menú
    desplegado se los quita a la zona donde el cajero pulsa. No es un estado que
    se pueda alternar, así que tampoco se recuerda ni tiene botón.

    Pinta la misma plantilla que la barra de la aplicación, con la misma entrada
    activa y el mismo botón de salir. Con dos plantillas, la segunda se quedaría
    atrás al primer ajuste — que es el motivo por el que `menu_de_navegacion`
    existe.
    """
    peticion = context.get("request")
    coincidencia = getattr(peticion, "resolver_match", None)

    return {
        "entradas": _pintables(
            MENU_DEL_PUNTO_DE_VENTA, getattr(coincidencia, "view_name", None)
        ),
        "colapsable": False,
        "siempre_colapsada": True,
    }
