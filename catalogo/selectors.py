"""Lecturas del dominio de productos, categorías y alérgenos.

**Toda lectura no trivial pasa por aquí** (`DT-15`). Como los servicios, estos
selectores no conocen `request`: reciben lo que necesitan como argumentos y
devuelven objetos del ORM o datos, nunca respuestas HTTP.
"""

from catalogo.models import Producto


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
