"""Representación imprimible del código de tarjeta (`TT-37`).

`ENT-02` es una **prueba de concepto con tarjetas físicas y un lector de código
de barras**. Lo que salga de aquí se imprime en papel y se pasa por un escáner:
si el ancho de barra es menor del que el lector resuelve, o si el símbolo está
mal codificado, la demostración del Sprint 2 no ocurre. De ahí las tres
decisiones de este módulo, todas registradas en `DT-22`.

**Code 128.** Es el juego que todo lector USB de los que se venden trae activado
de fábrica, y codifica nuestro alfabeto —dígitos y mayúsculas— en el subconjunto
B. `EAN-13` estaba sobre la mesa y no sirve: son trece **dígitos** con dígito de
control asignados por GS1 para productos de venta al público, no un
identificador interno alfanumérico.

**En el servidor y en SVG, no en el navegador.** Un código de barras rasterizado
a la resolución de la pantalla se imprime borroso y deja de escanearse; el SVG
lleva medidas en milímetros y sale del papel con el ancho que se le pidió.
Generarlo en el navegador obligaría además a vendorizar una biblioteca de
JavaScript y a que la página imprimible dependiera de que ese script corriera.

**La codificación la hace `python-barcode`; el dibujo, este módulo.** Escribir a
mano el codificador de Code 128 —con sus tres subconjuntos, su suma de control
en base 103 y su patrón de parada— es exactamente la clase de código que `DT-2`
dice que no hay que escribir: un error sutil no se ve en pantalla, se ve cuando
las tarjetas ya están impresas y el lector no las lee.
"""

from barcode import Code128

# Ancho de un módulo, la barra más estrecha del símbolo.
#
# La norma admite bajar hasta 0,19 mm, pero eso es para impresión industrial y
# lectores de gama alta. Con impresora de oficina y un lector económico —que es
# lo que `ENT-02` va a tener— 0,33 mm es el ancho que se lee sin acercar ni
# repetir. Bajarlo estrecha la tarjeta y empieza a costar lecturas.
ANCHO_DE_MODULO_MM = 0.33

# Alto de las barras. Un símbolo bajo obliga a apuntar con precisión; 15 mm
# admite el barrido descuidado de una fila de estudiantes en el descanso.
ALTO_DE_BARRAS_MM = 15.0

# Zona muda: el margen en blanco a cada lado, sin el cual el lector no encuentra
# dónde empieza el símbolo. La norma pide diez módulos como mínimo. **No es
# decoración y no se recorta para que la tarjeta quepa mejor.**
ZONA_MUDA_MODULOS = 10


def patron_de_modulos(codigo):
    """La secuencia de barras y espacios del símbolo, como texto de `0` y `1`.

    Un `1` es una barra de un módulo de ancho y un `0` un espacio del mismo
    ancho. Lo produce `python-barcode`, que es quien sabe de Code 128.
    """
    return Code128(codigo).build()[0]


def _tramos_de_barra(patron):
    """Agrupa los `1` consecutivos: una barra ancha es un rectángulo, no tres.

    Además de dar un SVG más pequeño, evita las costuras que dejan los
    rectángulos contiguos al renderizar, y que un lector puede leer como un
    espacio que no existe.
    """
    tramos, inicio = [], None
    for posicion, modulo in enumerate(patron):
        if modulo == "1" and inicio is None:
            inicio = posicion
        elif modulo == "0" and inicio is not None:
            tramos.append((inicio, posicion - inicio))
            inicio = None
    if inicio is not None:
        tramos.append((inicio, len(patron) - inicio))
    return tramos


def svg_del_codigo(codigo, alto_mm=ALTO_DE_BARRAS_MM):
    """Devuelve el símbolo como SVG en línea, listo para incrustar en la página.

    **Sin declaración XML ni DOCTYPE**: esto va dentro de un documento HTML, no
    es un fichero suelto.

    El `viewBox` va en módulos y el `width` en milímetros, así que el navegador
    hace la conversión y el símbolo sale del papel con el ancho físico que pide
    `ANCHO_DE_MODULO_MM`, independientemente de la resolución de la pantalla.

    **No lleva el texto del código.** La interpretación legible va en la página,
    con la tipografía de la página; meterla en el SVG la ataría al tamaño del
    símbolo.
    """
    patron = patron_de_modulos(codigo)
    total_modulos = len(patron) + 2 * ZONA_MUDA_MODULOS
    alto_modulos = round(alto_mm / ANCHO_DE_MODULO_MM)

    barras = "".join(
        f'<rect x="{ZONA_MUDA_MODULOS + inicio}" y="0" '
        f'width="{ancho}" height="{alto_modulos}"/>'
        for inicio, ancho in _tramos_de_barra(patron)
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Código de barras {codigo}" '
        f'width="{total_modulos * ANCHO_DE_MODULO_MM:.2f}mm" height="{alto_mm:.2f}mm" '
        f'viewBox="0 0 {total_modulos} {alto_modulos}" '
        f'preserveAspectRatio="xMidYMid meet">'
        f'<rect x="0" y="0" width="{total_modulos}" height="{alto_modulos}" fill="#fff"/>'
        f'<g fill="#000">{barras}</g>'
        f"</svg>"
    )


def ancho_mm(codigo):
    """Cuánto ocupa el símbolo impreso, zonas mudas incluidas.

    Sirve para comprobar que cabe en la tarjeta antes de mandar a imprimir.
    """
    return (len(patron_de_modulos(codigo)) + 2 * ZONA_MUDA_MODULOS) * ANCHO_DE_MODULO_MM
