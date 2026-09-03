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

MENU_POR_ROL = {
    # `USR-2` entra desde el teléfono (`INT-1`) y a lo suyo: sus estudiantes.
    Rol.ACUDIENTE: (INICIO, Entrada("mis-estudiantes", "Mis estudiantes", "i-estudiantes")),
    # `USR-5` carga el padrón (`HU-01`) y administra estudiantes y personal.
    Rol.INSTITUCION: (
        INICIO,
        Entrada("carga-de-estudiantes", "Cargar estudiantes", "i-cargar"),
        ADMINISTRACION,
    ),
    # `USR-4` administra el catálogo. `USR-3` todavía no tiene pantalla propia:
    # el punto de venta es del Sprint 2 (`HU-15`), y hasta entonces su menú es
    # corto a propósito en vez de llevar a sitios donde recibiría un 403.
    Rol.ADMINISTRADOR: (INICIO, ADMINISTRACION),
    Rol.CAJERO: (INICIO, ADMINISTRACION),
}


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
