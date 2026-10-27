"""Lecturas del dominio de productos, categorías y alérgenos.

**Toda lectura no trivial pasa por aquí** (`DT-15`). Como los servicios, estos
selectores no conocen `request`: reciben lo que necesitan como argumentos y
devuelven objetos del ORM o datos, nunca respuestas HTTP.
"""

from django.core.exceptions import PermissionDenied
from django.db.models import Count

from catalogo.models import Alergeno, Categoria, Producto
from cuentas.models import Rol


def productos_con_alergeno(alergeno):
    """Los productos que declaran ese alérgeno, **ahora mismo**.

    **Es la consulta que sostiene `INV-5`, y su forma importa más que su
    contenido.** No devuelve una lista guardada en ninguna parte: la calcula
    cruzando `ProductoAlergeno` cada vez que se le pregunta. Por eso un producto
    que se agregue al catálogo mañana queda cubierto sin que nadie recalcule
    nada, que es literalmente lo que `HU-11` pide.

    Cuando llegue la restricción por estudiante (`HU-11`, Sprint 3), el rechazo
    de la venta (`HU-18`) es esta misma consulta cruzada con la del acudiente
    (`DT-7`). No hay que materializar nada por el camino.
    """
    return Producto.objects.filter(declaraciones__alergeno=alergeno)


def productos_en_el_catalogo():
    """Lo que hoy se puede vender.

    Los retirados siguen existiendo —el historial los referencia— pero no se
    ofrecen.
    """
    return Producto.objects.filter(activo=True).select_related("categoria")


def categorias_del_catalogo(*, actor):
    """Las categorías, de la A a la Z, cada una con `cuantos`: sus productos
    (`DT-51`).

    **Cuentan también los retirados del catálogo**: siguen existiendo y tienen
    historial, y son los que impiden eliminar la categoría (`PROTECT`). Una
    categoría que la pantalla diera por vacía y la base se negara a borrar
    sería un botón que siempre falla.

    Exige el rol antes de leer, como el resto de lo que gestiona la
    administración de la cafetería (`[S11]`, `HU-26`).
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Consultar las categorías exige identificarse.")
    if actor.rol != Rol.ADMINISTRADOR:
        raise PermissionDenied(
            "Las categorías solo las gestiona la administración de la cafetería."
        )
    if not actor.is_active:
        raise PermissionDenied(
            "Tu cuenta está desactivada. Pide a la institución educativa que la reactive."
        )

    return list(
        Categoria.objects.annotate(cuantos=Count("productos")).order_by("nombre")
    )


def alergenos_del_catalogo(*, actor):
    """Los alérgenos, de la A a la Z, cada uno con `cuantos_productos` —los que
    lo declaran— y `cuantos_estudiantes` —los que lo tienen bloqueado— (`DT-52`).

    **Cuentan también los productos retirados y los estudiantes de baja**: sus
    filas siguen existiendo y el `PROTECT` las sostiene. Se cuentan por las
    relaciones inversas, así que `catalogo` no importa `restricciones`.
    `distinct` porque son dos `JOIN` en la misma consulta: sin él, cada cifra
    saldría multiplicada por la otra.

    Exige el rol antes de leer, como las categorías (`[S11]`, `HU-26`).
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied("Consultar los alérgenos exige identificarse.")
    if actor.rol != Rol.ADMINISTRADOR:
        raise PermissionDenied(
            "Los alérgenos solo los gestiona la administración de la cafetería."
        )
    if not actor.is_active:
        raise PermissionDenied(
            "Tu cuenta está desactivada. Pide a la institución educativa que la reactive."
        )

    return list(
        Alergeno.objects.annotate(
            cuantos_productos=Count("declaraciones", distinct=True),
            cuantos_estudiantes=Count("bloqueos", distinct=True),
        ).order_by("nombre")
    )
