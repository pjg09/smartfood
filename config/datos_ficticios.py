"""Los datos ficticios del prototipo (`TT-08`, `DT-14`).

**Ningún dato de aquí corresponde a una persona real.** No es una preferencia:
`ALC-OUT-07` lo exige y `ALC-OUT-08` explica por qué —el tratamiento de datos
personales de menores requiere autorización de sus titulares conforme a la Ley
1581 de 2012—. Los nombres están compuestos a partir de listas de nombres y
apellidos comunes, los documentos son secuencias inventadas y **todos los
correos son `@example.com`**, dominio que la RFC 2606 reserva y que nadie puede
registrar: ningún correo dirigido ahí llega a un buzón de nadie.

Vive en `config/` porque siembra `personas` y `catalogo` por igual, y ninguna de
las dos lo posee.

**Determinista.** El generador va con semilla fija, así que dos entornos
sembrados con los mismos parámetros tienen los mismos datos y una captura de
pantalla sigue valiendo mañana. Lo único que **no** es determinista, y no puede
serlo, es el código de tarjeta: lo sortea `secrets` porque es una credencial
(`INV-7`, `DT-9`).
"""

import random
import unicodedata
from decimal import Decimal

NOMBRES = [
    "Ana Sofía", "Tomás", "Valeria", "Samuel", "Isabella", "Matías", "Salomé",
    "Emiliano", "Luciana", "Santiago", "Mariana", "Nicolás", "Antonella",
    "Sebastián", "Camila", "Alejandro", "Julieta", "Martín", "Gabriela", "Simón",
]
NOMBRES_ADULTOS = [
    "Marta", "Andrés", "Luisa", "Carlos", "Beatriz", "Jorge", "Patricia",
    "Ricardo", "Claudia", "Fernando", "Adriana", "Óscar",
]
APELLIDOS = [
    "Restrepo", "Ospina", "Cardona", "Mejía", "Ruiz", "Vélez", "Arango",
    "Zapata", "Betancur", "Gaviria", "Hoyos", "Uribe", "Quintero", "Salazar",
]

CATEGORIAS = ["Panadería", "Bebidas", "Frutas", "Snacks", "Almuerzo"]

ALERGENOS = [
    "Lactosa", "Gluten", "Maní", "Nueces", "Huevo", "Soya", "Mariscos", "Pescado",
]

# Cada producto: nombre, categoría, precio, alérgenos y su información
# nutricional **por porción vendible**, como fija `TT-44`.
PRODUCTOS = [
    ("Pan de queso", "Panadería", 2500, ["Lactosa", "Gluten"],
     dict(porcion="unidad de 80 g", energia_kcal=250, proteinas_g="8.00",
          carbohidratos_g="28.00", azucares_g="2.00", grasas_totales_g="11.00",
          grasas_saturadas_g="6.00", sodio_mg=380)),
    ("Croissant", "Panadería", 3200, ["Lactosa", "Gluten", "Huevo"],
     dict(porcion="unidad de 60 g", energia_kcal=270, proteinas_g="5.00",
          carbohidratos_g="26.00", azucares_g="6.00", grasas_totales_g="16.00",
          grasas_saturadas_g="9.00", sodio_mg=310)),
    ("Empanada de carne", "Almuerzo", 3000, ["Gluten"],
     dict(porcion="unidad de 90 g", energia_kcal=290, proteinas_g="9.00",
          carbohidratos_g="30.00", azucares_g="1.00", grasas_totales_g="15.00",
          grasas_saturadas_g="5.00", sodio_mg=450)),
    ("Arepa de choclo", "Panadería", 2800, ["Lactosa"],
     dict(porcion="unidad de 100 g", energia_kcal=230, proteinas_g="6.00",
          carbohidratos_g="34.00", azucares_g="9.00", grasas_totales_g="8.00",
          grasas_saturadas_g="4.00", sodio_mg=290)),
    ("Sándwich de pollo", "Almuerzo", 7500, ["Gluten", "Huevo"],
     dict(porcion="unidad de 180 g", energia_kcal=390, proteinas_g="24.00",
          carbohidratos_g="38.00", azucares_g="4.00", grasas_totales_g="14.00",
          grasas_saturadas_g="4.00", sodio_mg=720)),
    ("Bandeja del día", "Almuerzo", 12000, [],
     dict(porcion="porción de 450 g", energia_kcal=680, proteinas_g="32.00",
          carbohidratos_g="78.00", azucares_g="6.00", grasas_totales_g="24.00",
          grasas_saturadas_g="8.00", sodio_mg=980)),
    ("Jugo de mora", "Bebidas", 3500, [],
     dict(porcion="vaso de 250 ml", energia_kcal=120, proteinas_g="1.00",
          carbohidratos_g="29.00", azucares_g="26.00", grasas_totales_g="0.50",
          grasas_saturadas_g="0.10", sodio_mg=15)),
    ("Leche saborizada", "Bebidas", 3800, ["Lactosa"],
     dict(porcion="caja de 200 ml", energia_kcal=160, proteinas_g="6.00",
          carbohidratos_g="24.00", azucares_g="22.00", grasas_totales_g="4.00",
          grasas_saturadas_g="2.50", sodio_mg=120)),
    ("Agua sin gas", "Bebidas", 2000, [],
     dict(porcion="botella de 500 ml", energia_kcal=0, proteinas_g="0.00",
          carbohidratos_g="0.00", azucares_g="0.00", grasas_totales_g="0.00",
          grasas_saturadas_g="0.00", sodio_mg=2)),
    ("Banano", "Frutas", 1500, [],
     dict(porcion="unidad de 120 g", energia_kcal=105, proteinas_g="1.30",
          carbohidratos_g="27.00", azucares_g="14.00", grasas_totales_g="0.40",
          grasas_saturadas_g="0.10", sodio_mg=1)),
    ("Ensalada de frutas", "Frutas", 5500, ["Lactosa"],
     dict(porcion="vaso de 250 g", energia_kcal=180, proteinas_g="3.00",
          carbohidratos_g="38.00", azucares_g="30.00", grasas_totales_g="2.00",
          grasas_saturadas_g="1.00", sodio_mg=40)),
    ("Mandarina", "Frutas", 1200, [], dict(porcion="unidad de 100 g")),
    ("Barra de granola", "Snacks", 2600, ["Maní", "Nueces", "Gluten"],
     dict(porcion="unidad de 40 g", energia_kcal=180, proteinas_g="4.00",
          carbohidratos_g="24.00", azucares_g="11.00", grasas_totales_g="7.00",
          grasas_saturadas_g="2.00", sodio_mg=95)),
    ("Galletas de avena", "Snacks", 2200, ["Gluten", "Huevo", "Soya"],
     dict(porcion="paquete de 45 g", energia_kcal=210, proteinas_g="3.00",
          carbohidratos_g="30.00", azucares_g="12.00", grasas_totales_g="9.00",
          grasas_saturadas_g="4.00", sodio_mg=160)),
    ("Maní salado", "Snacks", 2400, ["Maní"],
     dict(porcion="paquete de 30 g", energia_kcal=180, proteinas_g="8.00",
          carbohidratos_g="5.00", azucares_g="1.00", grasas_totales_g="15.00",
          grasas_saturadas_g="2.00", sodio_mg=230)),
    ("Yogur con cereal", "Snacks", 4200, ["Lactosa", "Gluten"],
     dict(porcion="vaso de 200 g", energia_kcal=220, proteinas_g="9.00",
          carbohidratos_g="32.00", azucares_g="24.00", grasas_totales_g="5.00",
          grasas_saturadas_g="3.00", sodio_mg=110)),
]

# El personal de la cafetería. Dos cuentas, una por rol de `DEC-2`.
PERSONAL = [
    ("cajero@example.com", "cajero", "Beatriz Hoyos Salazar"),
    ("administracion@example.com", "administrador", "Ricardo Gaviria Uribe"),
]


def _sin_tildes(texto):
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def correo_de(nombre, indice):
    """`@example.com` **siempre**: la RFC 2606 lo reserva y nadie lo registra.

    Con cualquier otro dominio, un correo del prototipo podría llegarle a una
    persona de verdad.
    """
    partes = _sin_tildes(nombre).lower().split()
    return f"{partes[0]}.{partes[-1]}{indice}@example.com"


def familias(cuantos_estudiantes, semilla=20260901):
    """Genera acudientes con sus estudiantes. Determinista.

    Uno de cada cuatro acudientes tiene **dos** estudiantes a su cargo, que es
    el caso que `HU-04` describe y el que hay que poder demostrar: sin él, la
    pantalla del acudiente nunca enseña su selector.
    """
    azar = random.Random(semilla)
    generadas, estudiantes_creados = [], 0

    while estudiantes_creados < cuantos_estudiantes:
        indice = len(generadas)
        apellidos = f"{azar.choice(APELLIDOS)} {azar.choice(APELLIDOS)}"
        nombre_acudiente = f"{azar.choice(NOMBRES_ADULTOS)} {apellidos}"

        cuantos = 2 if indice % 4 == 0 else 1
        cuantos = min(cuantos, cuantos_estudiantes - estudiantes_creados)

        hijos = []
        for orden in range(cuantos):
            hijos.append(
                {
                    "nombre": f"{azar.choice(NOMBRES)} {apellidos}",
                    "documento": f"10{estudiantes_creados + orden:08d}",
                }
            )

        generadas.append(
            {
                "nombre": nombre_acudiente,
                "documento": f"43{indice:06d}",
                "correo": correo_de(nombre_acudiente, indice),
                "estudiantes": hijos,
            }
        )
        estudiantes_creados += cuantos

    return generadas


def productos():
    """Los productos con su nutricional, ya en `Decimal` donde toca."""
    for nombre, categoria, precio, alergenos, nutricional in PRODUCTOS:
        campos = {
            campo: Decimal(valor) if isinstance(valor, str) and campo != "porcion" else valor
            for campo, valor in nutricional.items()
        }
        yield nombre, categoria, Decimal(precio), alergenos, campos
