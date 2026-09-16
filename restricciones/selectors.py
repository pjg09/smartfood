"""Lecturas del control parental (`DT-15`).

Como los servicios, estos selectores no conocen `request`: reciben lo que
necesitan como argumentos y devuelven datos, nunca respuestas HTTP.
"""

from restricciones.models import LimiteDiario, RestriccionProducto


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
