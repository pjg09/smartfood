"""Lector del archivo de carga (`TT-23`).

Solo **lee y normaliza**. No valida reglas de negocio, no escribe y no sabe de
HTTP: convierte bytes en filas con los campos recortados, y nada más. La
validación que acumula errores y decide si se escribe es `HU-02` (`TT-25`), y la
escritura es `personas.services`.

El formato es el contrato de `./docs/formato-de-carga.md` (`TT-22`).
"""

import csv
import io
from dataclasses import dataclass

COLUMNAS = (
    "documento_estudiante",
    "nombre_estudiante",
    "documento_acudiente",
    "nombre_acudiente",
    "correo_acudiente",
)


class ArchivoIlegible(Exception):
    """El archivo no se puede leer siquiera como CSV."""


@dataclass(frozen=True)
class Fila:
    """Una fila del archivo, ya recortada. `numero` es el de la hoja: la
    primera fila de datos es la 2, porque la 1 es el encabezado. Un reporte de
    errores que no coincida con lo que ve el usuario en su editor no sirve."""

    numero: int
    documento_estudiante: str
    nombre_estudiante: str
    documento_acudiente: str
    nombre_acudiente: str
    correo_acudiente: str


def leer(archivo):
    """Devuelve `list[Fila]`. Lanza `ArchivoIlegible` si ni siquiera es un CSV.

    Acepta bytes o un fichero abierto. Tolera el BOM que Excel antepone al
    exportar en UTF-8: sin eso, la primera columna se llamaría
    `﻿documento_estudiante` y el archivo se rechazaría por «falta una
    columna» que está a la vista.
    """
    datos = archivo.read() if hasattr(archivo, "read") else archivo
    if isinstance(datos, bytes):
        try:
            texto = datos.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ArchivoIlegible(
                "El archivo no está codificado en UTF-8. Vuelve a exportarlo con esa "
                "codificación."
            ) from error
    else:
        texto = datos.lstrip("﻿")

    if not texto.strip():
        raise ArchivoIlegible("El archivo está vacío.")

    lector = csv.DictReader(io.StringIO(texto))
    encabezado = [c.strip() for c in (lector.fieldnames or [])]

    faltantes = [c for c in COLUMNAS if c not in encabezado]
    if faltantes:
        raise ArchivoIlegible(
            "Al archivo le faltan columnas obligatorias: "
            + ", ".join(faltantes)
            + f". Se esperan: {', '.join(COLUMNAS)}."
        )

    filas = []
    for numero, cruda in enumerate(lector, start=2):
        filas.append(
            Fila(
                numero=numero,
                **{c: (cruda.get(c) or "").strip() for c in COLUMNAS},
            )
        )

    if not filas:
        raise ArchivoIlegible("El archivo tiene encabezado pero ninguna fila de datos.")

    return filas
