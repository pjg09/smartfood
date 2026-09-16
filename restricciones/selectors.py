"""Lecturas del control parental (`DT-15`).

Como los servicios, estos selectores no conocen `request`: reciben lo que
necesitan como argumentos y devuelven datos, nunca respuestas HTTP.
"""

from restricciones.models import LimiteDiario


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
