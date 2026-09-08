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
    """

    ruta: str
    etiqueta: str
    icono: str


# El inicio lo ve todo el mundo, incluido quien no ha entrado.
INICIO = Entrada("inicio", "Inicio", "i-inicio")

# Administración es el admin de Django: `INT-3` no lleva plantillas propias
# (`DT-2`), y para el personal de la cafetería y la institución es donde está su
# trabajo, no un enlace secundario.
ADMINISTRACION = Entrada("admin:index", "Administración", "i-ajustes")

# `USR-3` cobra en el punto de venta (`INT-2`). El icono es un escáner y no la
# tarjeta: la tarjeta es la credencial del estudiante, y lo que el cajero
# reconoce de su pantalla es el lector.
PUNTO_DE_VENTA = Entrada("punto-de-venta", "Punto de venta", "i-escaner")

MENU_POR_ROL = {
    # `USR-2` entra desde el teléfono (`INT-1`) y a lo suyo: sus estudiantes.
    Rol.ACUDIENTE: (INICIO, Entrada("mis-estudiantes", "Mis estudiantes", "i-estudiantes")),
    # `USR-5` carga el padrón (`HU-01`) y administra estudiantes y personal.
    Rol.INSTITUCION: (
        INICIO,
        Entrada("carga-de-estudiantes", "Cargar estudiantes", "i-cargar"),
        ADMINISTRACION,
    ),
    # `USR-4` administra el catálogo desde `INT-3`.
    Rol.ADMINISTRADOR: (INICIO, ADMINISTRACION),
    Rol.CAJERO: (INICIO, PUNTO_DE_VENTA, ADMINISTRACION),
}

# La barra del punto de venta. **Es una lista aparte y hoy tiene una sola
# entrada**, que es exactamente lo que el Sprint 2 construyó: entregas, cierre
# de caja y cocina no existen todavía y no se dibujan huecos por adelantado.
#
# Va separada de `MENU_POR_ROL[Rol.CAJERO]` porque son dos sitios distintos: en
# la barra de la aplicación el cajero necesita poder salir del punto de venta, y
# en el punto de venta necesita justo lo contrario — `INT-2` pide atender toda
# la demanda del descanso en veinte minutos, y un menú ahí solo son sitios a los
# que llegar por error con cola delante.
MENU_DEL_PUNTO_DE_VENTA = (PUNTO_DE_VENTA,)


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
        "entradas": entradas,
        "ruta_actual": getattr(coincidencia, "view_name", None),
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
        "entradas": MENU_DEL_PUNTO_DE_VENTA,
        "ruta_actual": getattr(coincidencia, "view_name", None),
        "colapsable": False,
        "siempre_colapsada": True,
    }
