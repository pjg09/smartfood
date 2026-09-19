"""Los valores de referencia nutricional de la autoridad sanitaria (`TT-162`).

═══════════════════════════════════════════════════════════════════════════
**FUENTE — Resolución 810 de 2021 del Ministerio de Salud y Protección Social
de Colombia**, del 16 de junio de 2021 (Diario Oficial 51.707), **artículo 15**,
`Tabla 9` (VRN-N) y `Tabla 10` (VRN-ENT), columna **«Niños mayores de 4 años y
adultos»**. Modificada por la Resolución 2492 de 2022 y corregida por la 254 de
2023; el artículo 15 no lleva nota de modificación en el texto compilado.

El contrato entero —qué se comprobó, qué no se pudo comprobar y las tres
salvedades— está en `docs/valores-de-referencia-nutricional.md`. **Si un número
de aquí y uno de allí discrepan, manda el documento.**
═══════════════════════════════════════════════════════════════════════════

── POR QUÉ LA COLUMNA DEL ETIQUETADO Y NO UNA RECOMENDACIÓN POR EDAD ───────
La Resolución 3803 de 2016 da recomendaciones de ingesta **por grupo de edad y
sexo**, y es más fina. Por eso mismo no se usa: elegir la fila según la edad y el
sexo del estudiante individualiza la referencia, y comparar contra un
requerimiento personal es **valoración nutricional individualizada** —
exactamente lo que `ALC-OUT-20` excluye y `INV-9` obliga a no hacer.

El VRN del etiquetado es el mismo para toda la población mayor de cuatro años y
no afirma lo que un niño necesita. **Estos 2000 kcal no son lo que el estudiante
necesita**, y la pantalla lo dice: es el valor que la norma manda imprimir en
cualquier etiqueta. Está razonado en `[S3]` del documento.
─────────────────────────────────────────────────────────────────────────────

Como `reglas.py`, este módulo es puro: ni consulta, ni escribe, ni sabe de HTTP.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


class ClaseDeReferencia:
    """Un valor de referencia y un techo **no significan lo mismo**.

    `Tabla 9` son necesidades —66 g de grasa es contra lo que se compara— y
    `Tabla 10` son máximos: la norma los rotula «Máx.». Enseñar los siete como
    si fueran lo mismo haría leer «el 80 % del sodio» igual que «el 80 % de la
    energía», y son dos frases distintas.
    """

    NECESIDAD = "necesidad"
    MAXIMO = "maximo"


@dataclass(frozen=True)
class ValorDeReferencia:
    """Un renglón de la tabla, con de dónde sale.

    `campo` es el nombre del campo congelado en `ventas.LineaVenta`, que es lo
    que ata esta tabla a la instantánea de `DT-8` sin repetir nombres por ahí.
    """

    campo: str
    etiqueta: str
    unidad: str
    valor: Decimal
    clase: str
    tabla: str
    # Con cuántos decimales se enseña el promedio diario. **Cero para las
    # unidades grandes** —kcal y mg—: «388,89 kcal» no le dice a nadie más que
    # «389 kcal», y dos decimales en una columna de cifras la vuelven ilegible.
    # Uno para los gramos, donde la décima sí distingue.
    decimales: int = 0
    nota: str = ""


# Los siete que el catálogo declara (`TT-44`), cada uno con su valor. **No falta
# ninguno**: los siete campos capturados tienen referencia en la norma.
#
# El orden es el de lectura de una etiqueta —energía primero, los críticos al
# final— y es fijo: la pantalla no ordena nada por su cuenta.
REFERENCIA_DIARIA = (
    ValorDeReferencia(
        campo="energia_kcal",
        etiqueta="Energía",
        unidad="kcal",
        valor=Decimal("2000"),
        clase=ClaseDeReferencia.NECESIDAD,
        tabla="Tabla 9",
    ),
    ValorDeReferencia(
        campo="proteinas_g",
        etiqueta="Proteínas",
        unidad="g",
        decimales=1,
        valor=Decimal("50"),
        clase=ClaseDeReferencia.NECESIDAD,
        tabla="Tabla 9",
    ),
    ValorDeReferencia(
        campo="carbohidratos_g",
        etiqueta="Carbohidratos",
        unidad="g",
        decimales=1,
        valor=Decimal("300"),
        clase=ClaseDeReferencia.NECESIDAD,
        tabla="Tabla 9",
    ),
    ValorDeReferencia(
        campo="grasas_totales_g",
        etiqueta="Grasas totales",
        unidad="g",
        decimales=1,
        valor=Decimal("66"),
        clase=ClaseDeReferencia.NECESIDAD,
        tabla="Tabla 9",
    ),
    ValorDeReferencia(
        campo="azucares_g",
        etiqueta="Azúcares",
        unidad="g",
        decimales=1,
        valor=Decimal("50"),
        clase=ClaseDeReferencia.MAXIMO,
        tabla="Tabla 10",
        # `[S4.1]`. La salvedad se guarda **con el dato**, no en la plantilla:
        # el día que esto se enseñe en otro sitio, la salvedad viaja con él.
        nota=(
            "La referencia oficial es de azúcares añadidos y el catálogo declara "
            "azúcares totales, así que esta cifra señala de más, nunca de menos."
        ),
    ),
    ValorDeReferencia(
        campo="grasas_saturadas_g",
        etiqueta="Grasas saturadas",
        unidad="g",
        decimales=1,
        valor=Decimal("20"),
        clase=ClaseDeReferencia.MAXIMO,
        tabla="Tabla 10",
    ),
    ValorDeReferencia(
        campo="sodio_mg",
        etiqueta="Sodio",
        unidad="mg",
        valor=Decimal("2000"),
        clase=ClaseDeReferencia.MAXIMO,
        tabla="Tabla 10",
    ),
)


@dataclass(frozen=True)
class Comparacion:
    """Lo que aportó un día de cafetería frente a la referencia diaria.

    `promedio_diario` es `None` cuando **ningún renglón del periodo declaró ese
    nutriente**, y eso no es un cero: es que no se sabe (`TT-44`, `[S4.3]`).
    Quien lo pinte tiene que distinguirlo — un cero afirmaría que no aportó
    nada, y nadie lo afirmó.
    """

    referencia: ValorDeReferencia
    total: Decimal | None
    promedio_diario: Decimal | None
    porcentaje: int | None

    @property
    def declarado(self):
        return self.promedio_diario is not None

    @property
    def es_maximo(self):
        return self.referencia.clase == ClaseDeReferencia.MAXIMO

    @property
    def ancho_de_la_barra(self):
        """El porcentaje recortado a 100, para dibujar la barra.

        Se recorta **aquí y no en la plantilla** porque una plantilla de Django
        no compara ni calcula. Y se recorta solo la barra: **el porcentaje se
        enseña entero**, aunque pase de 100. Una barra llena y un «140 %» al
        lado dicen la verdad; recortar también la cifra la escondería.
        """
        if self.porcentaje is None:
            return 0
        return min(self.porcentaje, 100)


def comparar(totales, dias_con_consumo):
    """Las siete comparaciones, en el orden de `REFERENCIA_DIARIA`.

    `totales` es `{campo: suma del periodo}` con **solo los nutrientes que algún
    renglón declaró**; lo que no está no se compara. `dias_con_consumo` es el
    divisor: la referencia es diaria, así que lo comparable es un día de
    cafetería (`[S5]` del documento).

    **Se divide entre los días con consumo y no entre los 14 de la ventana.** Un
    promedio sobre días en los que no se compró nada daría una cifra más baja y
    sin significado: la pregunta es cuánto aporta un día de cafetería.

    Sin días con consumo devuelve la lista vacía: no hay nada que promediar, y
    un cero aquí sería inventado.

    El redondeo es `ROUND_HALF_UP` y va al entero, declarado aquí para que el
    resultado sea **reproducible** (segundo criterio de `HU-32`): el redondeo por
    defecto de Python es al par más cercano, así que dejarlo implícito haría que
    `2,5` y `3,5` se redondearan en direcciones distintas sin que nadie lo
    esperara.
    """
    if not dias_con_consumo:
        return []

    dias = Decimal(dias_con_consumo)
    comparaciones = []

    for referencia in REFERENCIA_DIARIA:
        total = totales.get(referencia.campo)
        if total is None:
            comparaciones.append(
                Comparacion(
                    referencia=referencia,
                    total=None,
                    promedio_diario=None,
                    porcentaje=None,
                )
            )
            continue

        total = Decimal(total)
        promedio = (total / dias).quantize(
            Decimal(1).scaleb(-referencia.decimales), rounding=ROUND_HALF_UP
        )
        # **El porcentaje sale del total, no del promedio ya redondeado.** Si
        # saliera de él, la cifra que se enseña y la que se compara serían dos
        # redondeos encadenados, y el porcentaje cambiaría según con cuántos
        # decimales se decidiera pintar el promedio.
        porcentaje = (total / (dias * referencia.valor) * 100).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        comparaciones.append(
            Comparacion(
                referencia=referencia,
                total=total,
                promedio_diario=promedio,
                porcentaje=int(porcentaje),
            )
        )

    return comparaciones
