"""Validación del archivo de carga (`TT-25`, `HU-02`).

**Acumula.** No se detiene en el primer error: recorre el archivo entero y
devuelve todo lo que está mal. Un validador que corta al primer fallo obliga a
la institución a subir el archivo, corregir una línea, subirlo otra vez y
descubrir el siguiente error — con un colegio entero eso son decenas de vueltas.

**No escribe.** Ni aquí ni en ninguna rama. El primer criterio de `HU-02` no es
«si algo falla se deshace»: es que **la validación ocurre antes de escribir
cualquier dato**. Deshacer con una transacción y no llegar a escribir son cosas
distintas, y la historia pide la segunda.

Las reglas de formato salen de `./docs/formato-de-carga.md` (`TT-22`).
"""

import re
from dataclasses import dataclass

from personas.models import Acudiente, Estudiante

LONGITUD_DOCUMENTO = (5, 20)
LONGITUD_NOMBRE = (1, 200)

# Deliberadamente laxo: comprueba la forma, no la existencia del buzón. Una
# expresión estricta rechaza direcciones válidas y raras, y el coste de aceptar
# una dirección con forma correcta que no existe es cero — no se le envía nada
# (`DEC-9`).
FORMA_DE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class ErrorDeFila:
    """Un problema concreto, en un sitio concreto.

    `fila` es el número que el usuario ve en su editor. `None` significa que el
    problema es del archivo entero, no de una fila.
    """

    fila: int | None
    columna: str
    valor: str
    mensaje: str

    def __str__(self):
        donde = f"Fila {self.fila}" if self.fila else "Archivo"
        return f"{donde} · {self.columna}: {self.mensaje}"


class ArchivoInvalido(Exception):
    """El archivo se leyó, pero su contenido no se puede cargar."""

    def __init__(self, errores):
        self.errores = errores
        super().__init__(f"El archivo tiene {len(errores)} error(es) y no se cargó.")


def _texto(errores, fila, columna, valor, minimo, maximo, etiqueta):
    if not valor:
        errores.append(ErrorDeFila(fila.numero, columna, valor, f"{etiqueta} es obligatorio."))
    elif not (minimo <= len(valor) <= maximo):
        errores.append(
            ErrorDeFila(
                fila.numero, columna, valor,
                f"{etiqueta} debe tener entre {minimo} y {maximo} caracteres; tiene {len(valor)}.",
            )
        )


def validar(filas):
    """Devuelve la lista completa de errores. Vacía significa que se puede cargar."""
    errores = []

    documentos_de_estudiante = {}
    acudientes_por_correo = {}
    correos_por_documento = {}

    for fila in filas:
        _texto(errores, fila, "documento_estudiante", fila.documento_estudiante,
               *LONGITUD_DOCUMENTO, "El documento del estudiante")
        _texto(errores, fila, "nombre_estudiante", fila.nombre_estudiante,
               *LONGITUD_NOMBRE, "El nombre del estudiante")
        _texto(errores, fila, "documento_acudiente", fila.documento_acudiente,
               *LONGITUD_DOCUMENTO, "El documento del acudiente")
        _texto(errores, fila, "nombre_acudiente", fila.nombre_acudiente,
               *LONGITUD_NOMBRE, "El nombre del acudiente")

        correo = fila.correo_acudiente.lower()
        if not correo:
            errores.append(ErrorDeFila(
                fila.numero, "correo_acudiente", correo,
                "El correo del acudiente es obligatorio: es la identidad de su cuenta.",
            ))
        elif not FORMA_DE_CORREO.match(correo):
            errores.append(ErrorDeFila(
                fila.numero, "correo_acudiente", fila.correo_acudiente,
                "No tiene forma de correo electrónico.",
            ))

        # --- El mismo estudiante dos veces, dentro del archivo -------------
        if fila.documento_estudiante:
            anterior = documentos_de_estudiante.get(fila.documento_estudiante)
            if anterior is not None:
                errores.append(ErrorDeFila(
                    fila.numero, "documento_estudiante", fila.documento_estudiante,
                    f"Repetido: ya aparece en la fila {anterior}. "
                    "Un estudiante no puede estar dos veces en la misma carga.",
                ))
            else:
                documentos_de_estudiante[fila.documento_estudiante] = fila.numero

        # --- El archivo se contradice sobre un acudiente -------------------
        #
        # `[S3]` de docs/formato-de-carga.md: el correo identifica. Si el mismo
        # correo trae nombre o documento distintos, no sabemos cuál es el bueno,
        # y adivinar sobre datos de menores no es una opción.
        if correo and FORMA_DE_CORREO.match(correo):
            visto = acudientes_por_correo.get(correo)
            if visto is None:
                acudientes_por_correo[correo] = (
                    fila.numero, fila.nombre_acudiente, fila.documento_acudiente
                )
            else:
                numero, nombre, documento = visto
                if fila.documento_acudiente != documento:
                    errores.append(ErrorDeFila(
                        fila.numero, "documento_acudiente", fila.documento_acudiente,
                        f"El correo «{correo}» ya aparece en la fila {numero} con el "
                        f"documento «{documento}». El archivo se contradice.",
                    ))
                if fila.nombre_acudiente != nombre:
                    errores.append(ErrorDeFila(
                        fila.numero, "nombre_acudiente", fila.nombre_acudiente,
                        f"El correo «{correo}» ya aparece en la fila {numero} con el "
                        f"nombre «{nombre}». El archivo se contradice.",
                    ))

            # …y el caso simétrico: un documento con dos correos serían dos
            # cuentas para la misma persona.
            if fila.documento_acudiente:
                visto = correos_por_documento.get(fila.documento_acudiente)
                if visto is None:
                    correos_por_documento[fila.documento_acudiente] = (fila.numero, correo)
                elif visto[1] != correo:
                    errores.append(ErrorDeFila(
                        fila.numero, "correo_acudiente", fila.correo_acudiente,
                        f"El documento «{fila.documento_acudiente}» ya aparece en la fila "
                        f"{visto[0]} con el correo «{visto[1]}». Serían dos cuentas para "
                        "la misma persona.",
                    ))

    # --- Contra lo que ya está en el sistema ------------------------------
    if documentos_de_estudiante:
        ya_existen = set(
            Estudiante.objects.filter(
                documento__in=documentos_de_estudiante
            ).values_list("documento", flat=True)
        )
        for documento in sorted(ya_existen):
            errores.append(ErrorDeFila(
                documentos_de_estudiante[documento], "documento_estudiante", documento,
                "Ya existe un estudiante con ese documento en el sistema.",
            ))

    if correos_por_documento:
        documentos = {d for d in correos_por_documento}
        chocan = Acudiente.objects.filter(documento__in=documentos).exclude(
            usuario__email__in=[c for _, c in correos_por_documento.values()]
        )
        for acudiente in chocan:
            numero, correo = correos_por_documento[acudiente.documento]
            errores.append(ErrorDeFila(
                numero, "correo_acudiente", correo,
                f"Ya existe un acudiente con el documento «{acudiente.documento}» y el "
                f"correo «{acudiente.usuario.email}». No se puede cambiar por esta vía.",
            ))

    errores.sort(key=lambda e: (e.fila or 0, e.columna))
    return errores
