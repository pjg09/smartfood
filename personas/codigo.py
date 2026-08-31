"""Generador del código de tarjeta (`TT-30`).

**Sostiene `INV-7`**: «el código de la tarjeta se genera de forma aleatoria y no
secuencial». `ALC-IN-12` dice por qué importa: el código **opera como credencial
de acceso al saldo del estudiante**, así que deducir el de otro es entrar a su
billetera.

Módulo aparte y sin dependencias —ni modelos, ni base de datos, ni HTTP— porque
la propiedad que hay que probar es del generador, no del sistema alrededor.

Lo que **no** puede ser el código, y está prohibido por escrito:

- **Ni una secuencia**, ni nada derivado del identificador del estudiante o de
  otro campo suyo (`DT-9`, `ALC-IN-12`).
- **Ni un UUIDv7**, que es la clave primaria de todo lo demás (`DT-17`). UUIDv7
  lleva un prefijo de marca de tiempo: va ordenado por construcción, y dos
  estudiantes cargados en la misma tanda tendrían códigos casi contiguos. Eso es
  exactamente lo que `INV-7` prohíbe.
"""

import secrets

# Alfabeto de Crockford: los 10 dígitos y 22 letras mayúsculas, sin `I`, `L`,
# `O` ni `U`.
#
# **Mayúsculas y dígitos** porque el código tiene que poder imprimirse como
# código de barras (tercer criterio de `HU-43`), y ese es el juego que Code 39
# admite sin extensiones; Code 128 lo admite también.
#
# **Sin `I`, `L`, `O` ni `U`** porque el código lo va a leer y teclear una
# persona cuando el lector falle: `I` y `1`, `O` y `0` se confunden a simple
# vista, y `U` se retira para no formar palabras desafortunadas por azar.
#
# Quitar cuatro símbolos no debilita nada: quedan 32, que son 5 bits exactos por
# carácter.
ALFABETO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Catorce caracteres, dentro del rango de 12 a 16 que fija `DT-17`.
#
# Con 32 símbolos son **70 bits de aleatoriedad**: adivinar un código concreto es
# 1 entre 10^21, y el cumpleaños sobre un colegio de 2.000 estudiantes deja una
# probabilidad de colisión del orden de 10^-15. La longitud no la decide la
# estética: la decide que el código es una credencial.
LONGITUD = 14


def generar_codigo_de_tarjeta():
    """Devuelve un código nuevo. Aleatorio, no secuencial, imprimible.

    Usa `secrets`, que es el generador **criptográfico** de la biblioteca
    estándar (`DT-9`). No `random`: ese es un Mersenne Twister determinista y
    observar unos cuantos códigos bastaría para reconstruir su estado y predecir
    los siguientes. Para un número de la lotería da igual; para una credencial de
    acceso a un saldo, no.

    No comprueba unicidad —no toca la base de datos—. De eso se encargan el
    índice único y el reintento de `personas.services` (`DT-9`).
    """
    return "".join(secrets.choice(ALFABETO) for _ in range(LONGITUD))
