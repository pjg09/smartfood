"""Lecturas del control parental (`DT-15`).

Como los servicios, estos selectores no conocen `request`: reciben lo que
necesitan como argumentos y devuelven datos, nunca respuestas HTTP.
"""

from catalogo.models import Alergeno, Producto
from restricciones.models import (
    AsientoDeRestriccion,
    LimiteDiario,
    RestriccionAlergeno,
    RestriccionProducto,
)


def limite_diario_de(estudiante):
    """El `LimiteDiario` del estudiante, o `None` si no tiene ninguno (`HU-09`).

    **`None` es una respuesta legítima y la más frecuente al principio**: no hay
    fila significa que el acudiente no configuró cupo, que es distinto de un cupo
    de cero (ver `restricciones.models.LimiteDiario`). Devolver `Decimal("0")`
    para el caso sin configurar dejaría a quien llame sin forma de distinguir «no
    puede gastar nada» de «puede gastar lo que tenga», que son opuestos.

    **No autoriza a nadie, y es a propósito.** Un selector no sabe quién
    pregunta: quien llama decide si puede. En `INT-1` eso lo hace
    `estudiante_a_cargo`, que solo alcanza a los estudiantes propios (`DT-11`);
    en la venta lo hará el servicio de `TT-116`, donde no hay ningún acudiente a
    quien preguntarle. `[S11]` concede la **consulta** a los cuatro roles
    (`HU-38`), así que la restricción de lectura no vive aquí.

    Este es el selector de un dato; el de **las restricciones vigentes de un
    estudiante**, que compone el límite con los productos y alérgenos bloqueados,
    es `TT-106` y llega en `PR-05`.
    """
    return LimiteDiario.objects.filter(estudiante=estudiante).first()


def productos_bloqueados_de(estudiante):
    """Las `RestriccionProducto` vigentes del estudiante (`HU-10`).

    Devuelve un `QuerySet` sin evaluar, ordenado por nombre de producto —el
    orden lo fija el modelo y aquí no se repite porque no cambia—, con el
    producto y su categoría ya traídos: quien pinta la lista los necesita todos
    y sin esto serían tantas consultas como productos bloqueados.

    **Es una lista de verdad, y esa es la diferencia con `HU-11`.** Lo que hay
    aquí son los productos que el acudiente señaló uno a uno. El bloqueo por
    alérgeno no se responde desde esta función ni desde ninguna lista guardada:
    se evalúa cruzando la condición con lo que cada producto declara (`INV-5`,
    `DT-7`), y llega en `TT-100`.

    **No autoriza a nadie**, como el resto de selectores: quien llama decide si
    puede. `[S11]` concede la **consulta** de restricciones a los cuatro roles
    (`HU-38`).
    """
    return RestriccionProducto.objects.filter(
        estudiante=estudiante
    ).select_related("producto", "producto__categoria")


def identificadores_de_productos_bloqueados(estudiante):
    """Solo los `id` de los productos bloqueados, como conjunto.

    Existe para pintar la pantalla de `TT-99`, que recorre el catálogo entero y
    tiene que saber de cada producto si está bloqueado. Con esto es **una
    consulta**; preguntando producto a producto serían tantas como productos.

    Un `set` y no una lista: lo que se hace con esto es `in`.
    """
    return set(
        RestriccionProducto.objects.filter(estudiante=estudiante).values_list(
            "producto_id", flat=True
        )
    )


def bloqueos_entre(estudiante, productos):
    """De esos productos, los que este estudiante tiene bloqueados (`HU-60`).

    Devuelve las `RestriccionProducto` que coinciden, con su producto ya traído.
    Vacío si ninguno lo está.

    **Existe para la venta, y por eso pregunta solo por lo que se está
    cobrando.** `identificadores_de_productos_bloqueados` trae toda la lista del
    estudiante, que es lo que necesita la pantalla del acudiente; aquí la
    pregunta es otra —«¿alguno de estos cuatro?»— y se hace con un `IN` sobre lo
    que hay en el carrito. Es una consulta, dentro de una transacción con cola
    delante (`DT-6`).

    **No resuelve el bloqueo por alérgeno**, y no es un olvido: eso no se
    responde desde una lista sino cruzando la condición con lo que cada producto
    declara (`INV-5`, `DT-7`), y llega con `TT-100`. Meterlo aquí sería
    justamente materializar la lista que `INV-5` prohíbe.
    """
    return RestriccionProducto.objects.filter(
        estudiante=estudiante, producto__in=productos
    ).select_related("producto")


def alergenos_bloqueados_de(estudiante):
    """Las `RestriccionAlergeno` vigentes del estudiante (`HU-11`).

    Devuelve un `QuerySet` sin evaluar, con el alérgeno ya traído.

    **Esto es la lista de condiciones, no la de productos.** Lo que hay aquí son
    los alérgenos que el acudiente señaló; qué productos quedan fuera por su
    causa lo responde `productos_cubiertos_por_alergeno`, y lo responde
    calculándolo.
    """
    return RestriccionAlergeno.objects.filter(estudiante=estudiante).select_related(
        "alergeno"
    )


def identificadores_de_alergenos_bloqueados(estudiante):
    """Solo los `id` de los alérgenos bloqueados, como conjunto.

    Para pintar la pantalla de `TT-102`, que recorre el catálogo de alérgenos y
    tiene que saber de cada uno si está bloqueado. Con esto es **una** consulta.
    """
    return set(
        RestriccionAlergeno.objects.filter(estudiante=estudiante).values_list(
            "alergeno_id", flat=True
        )
    )


def productos_cubiertos_por_alergeno(estudiante):
    """Los productos que este estudiante no puede comprar **por su alérgeno**.

    ═══════════════════════════════════════════════════════════════════════
    **ESTA FUNCIÓN ES `INV-5`. SU FORMA IMPORTA MÁS QUE SU RESULTADO.**

    No lee ninguna lista guardada, porque no existe: cruza las restricciones de
    alérgeno del estudiante con `catalogo.ProductoAlergeno` **cada vez que se la
    llama**. De ahí salen las dos propiedades que `HU-11` pide y que ninguna
    lista materializada puede dar:

    · Un producto que la cafetería añada mañana declarando ese alérgeno queda
      cubierto **sin que nadie recalcule nada**.
    · Un producto que hoy existe y mañana declara el alérgeno queda cubierto en
      el mismo momento en que lo declara.

    Y la simétrica, que también importa: retirar la declaración de un producto lo
    descubre en el acto. La verdad vive en `ProductoAlergeno`, en un solo sitio.

    **Si alguien convierte esto en una tabla «porque consulta más rápido»,
    `INV-5` se rompe y no se nota.** No falla nada ese día: falla semanas
    después, en la caja, con un niño alérgico delante.
    ═══════════════════════════════════════════════════════════════════════

    `distinct()` no sobra: un producto que declare dos alérgenos bloqueados del
    mismo estudiante saldría dos veces del cruce.

    **No incluye los de `HU-10`.** Son dos restricciones distintas y se
    consultan por separado; quien necesite las dos —la pantalla de `TT-106`, la
    venta de `TT-113`— las junta arriba.
    """
    return Producto.objects.filter(
        declaraciones__alergeno__bloqueos__estudiante=estudiante
    ).distinct()


def alergenos_que_bloquean(estudiante, producto):
    """Qué alérgenos bloqueados de ese estudiante declara ese producto.

    Devuelve un `QuerySet` de `Alergeno`, vacío si ninguno. Es la pregunta que
    hará la venta en `TT-113` —«¿por qué no puede comprar esto?»— y la que
    permite decírselo al cajero con el nombre del alérgeno y no con un «está
    prohibido» sin explicación.

    Se calcula igual que `productos_cubiertos_por_alergeno`, mirando de un lado
    lo que el producto declara y del otro lo que el acudiente bloqueó. Ninguna
    de las dos es una lista guardada (`INV-5`).
    """
    return Alergeno.objects.filter(
        declaraciones__producto=producto, bloqueos__estudiante=estudiante
    ).distinct()


def historial_de_restricciones(estudiante, limite=None):
    """Lo que se hizo con las restricciones de un estudiante, lo último primero.

    Segundo criterio de `HU-12`: el retiro queda asentado, y asentado significa
    **legible**. Un registro que nadie puede leer no hace auditable nada; esta
    es la función que lo convierte en algo que se mira.

    Devuelve un `QuerySet` sin evaluar, con el actor, el producto y el alérgeno
    ya traídos: quien pinta el historial los necesita todos y sin esto serían
    tres consultas por fila.

    `limite` recorta para las pantallas que enseñan «los últimos cambios».
    **Sin él se devuelve el historial entero**, que es lo que una auditoría
    necesita: media lista no reconstruye nada.

    El orden lo fija el modelo —`-creado_en`— y se repite aquí explícito: quien
    lea esta función no tiene por qué ir al `Meta` a averiguarlo.
    """
    asientos = AsientoDeRestriccion.objects.filter(
        estudiante=estudiante
    ).select_related("actor", "producto", "alergeno").order_by("-creado_en")

    return asientos[:limite] if limite is not None else asientos
