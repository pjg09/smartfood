"""Las reglas determinísticas de frecuencia de consumo (`TT-158`, `TT-159`).

**El contrato está en `docs/reglas-de-frecuencia-de-consumo.md`**, y este módulo
lo ejecuta. Si los números de aquí y los de allí discrepan, manda el documento:
los umbrales son una decisión de análisis (`[S12]`), no de implementación.

── POR QUÉ ESTO NO ES UN SELECTOR NI UN SERVICIO ───────────────────────────
No lee la base y no escribe nada: recibe un recuento ya hecho y devuelve el
veredicto. Es el mismo sitio que ocupan `personas/codigo.py`,
`personas/validacion.py` o `ventas/carrito.py` — lógica pura, al lado de la app
a la que pertenece (`DT-15` reparte lo que habla con la base, no todo lo demás).

Que sea pura no es un lujo: es lo que permite comprobar los umbrales **sin
sembrar catorce días de ventas**, y lo que hace que la regla se pueda leer
entera en una pantalla cuando alguien pregunte por qué avisó.
─────────────────────────────────────────────────────────────────────────────

**Nada de modelos probabilísticos** (`OBJ-E3`, `ALC-IN-21`): aquí se cuenta y se
compara con un número fijo. Tampoco tendría con qué entrenarse — los datos son
ficticios (`ALC-OUT-07`).
"""

from dataclasses import dataclass

# La ventana, en días naturales y con el de hoy incluido (`[S2.2]`).
#
# **Días naturales y no lectivos**: el sistema no conoce el calendario escolar
# —no sabe qué días hay clase, ni los festivos, ni las vacaciones— y suponerlo
# movería el umbral sin que nadie lo notara. Catorce naturales son diez lectivos
# típicos, y de ahí salen los dos umbrales de abajo.
DIAS_DE_LA_VENTANA = 14

# Los dos umbrales, en **días distintos con al menos una compra** de la misma
# categoría dentro de la ventana (`[S2]`).
#
# Cinco es la mitad de los diez días lectivos del periodo; ocho son cuatro de
# cada cinco. **El mismo número para todas las categorías**, y esa es la
# decisión de fondo: un umbral por categoría exigiría clasificarlas por lo
# saludables que son, que es la valoración nutricional que `ALC-OUT-20` excluye
# (`[S3]` del documento).
UMBRAL_FRECUENCIA_ALTA = 5
UMBRAL_FRECUENCIA_MUY_ALTA = 8


class NivelDeFrecuencia:
    """Los dos niveles, y **no hay un tercero para «normal»**.

    Publicar «esta categoría está en su punto» sería una valoración tan
    individualizada como la contraria (`ALC-OUT-20`, `[S1]`). Lo que está por
    debajo del umbral no genera nada: no se dice.

    No es un `TextChoices` porque no se guarda en ninguna tabla — nada de esto
    se persiste, se calcula al pedir la pantalla.
    """

    ALTA = "alta"
    MUY_ALTA = "muy_alta"


@dataclass(frozen=True)
class AlertaDeFrecuencia:
    """Un patrón observado en una categoría. **Un hecho, no un consejo.**

    Lleva el umbral con el que se comparó, y no por adorno: es lo que permite
    al acudiente **comprobar la alerta contra el historial que tiene debajo**
    (`ANEXO A`). Una alerta que no se puede comprobar es indistinguible de una
    opinión, y `OBJ-E3` pide justo lo contrario.

    `dias` son días distintos, nunca unidades ni importe (`[S2.1]`).
    """

    categoria: str
    dias: int
    umbral: int
    nivel: str
    ventana: int = DIAS_DE_LA_VENTANA

    @property
    def es_muy_alta(self):
        return self.nivel == NivelDeFrecuencia.MUY_ALTA


def evaluar(dias_por_categoria):
    """Las alertas que salen de un recuento `{categoría: días}`.

    Recibe lo que `reportes.selectors.dias_de_consumo_por_categoria` cuenta en la
    base y devuelve la lista ordenada de alertas. **Sin efectos y sin consultas**:
    la misma entrada da siempre la misma salida, que es lo que `OBJ-E3` pide al
    decir «determinísticas».

    El orden es de más días a menos y, a igual número, alfabético por categoría
    (`[S2.5]`). No es cosmética: dejar que lo decida la base convertiría dos
    consultas idénticas en dos pantallas distintas.

    Una categoría por debajo de `UMBRAL_FRECUENCIA_ALTA` **no produce nada**, ni
    siquiera una alerta de nivel «normal» — ver `NivelDeFrecuencia`.
    """
    alertas = []

    for categoria, dias in dias_por_categoria.items():
        if dias >= UMBRAL_FRECUENCIA_MUY_ALTA:
            nivel, umbral = NivelDeFrecuencia.MUY_ALTA, UMBRAL_FRECUENCIA_MUY_ALTA
        elif dias >= UMBRAL_FRECUENCIA_ALTA:
            nivel, umbral = NivelDeFrecuencia.ALTA, UMBRAL_FRECUENCIA_ALTA
        else:
            continue

        alertas.append(
            AlertaDeFrecuencia(
                categoria=categoria, dias=dias, umbral=umbral, nivel=nivel
            )
        )

    # `-dias` primero y el nombre después: el menos invierte solo la cifra, y
    # así el desempate alfabético queda ascendente, que es como se lee una lista.
    alertas.sort(key=lambda alerta: (-alerta.dias, alerta.categoria))
    return alertas
