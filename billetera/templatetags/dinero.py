"""Cómo se escribe una cifra de dinero en este sistema (`TT-64`).

Un solo sitio, y por el mismo motivo que los colores tienen uno solo: si cada
plantilla formatea a su manera, la misma cifra sale «25000», «25.000,00» y
«$25000.0» en tres pantallas, y quien lo lee no sabe si son la misma.

**Formato colombiano**: punto para los miles y coma para los decimales. Los
centavos se muestran **solo si los hay**. El peso colombiano no los usa en la
práctica —una empanada cuesta 3.500, no 3.500,00— y arrastrar dos ceros en cada
importe hace más difícil comparar una columna de cifras. Pero si existen se
enseñan: ocultarlos convertiría 1.000,50 en 1.000 y el saldo dejaría de coincidir
con el historial a la vista, que es justo lo que `HU-07` promete.
"""

from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def dinero(monto):
    """`25000` → `$ 25.000` · `-3500.50` → `-$ 3.500,50` · `None` → `$ 0`.

    El signo va **delante del símbolo**, no entre el símbolo y la cifra: «-$ 500»
    se lee de un vistazo y «$ -500» hace dudar.
    """
    if monto is None:
        return "$ 0"

    monto = Decimal(monto)
    negativo = monto < 0
    entero, centavos = divmod(abs(monto).quantize(Decimal("0.01")), 1)

    # `,` como separador de miles y luego se cambia por punto: es la forma de
    # pedirle a Python el agrupamiento sin depender de la configuración regional
    # del sistema operativo, que en el servidor no tiene por qué ser la de aquí.
    texto = f"{int(entero):,}".replace(",", ".")
    if centavos:
        texto += "," + f"{int(centavos * 100):02d}"

    return f"{'-' if negativo else ''}$ {texto}"
