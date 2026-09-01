# SmartFood — Campos nutricionales del catálogo

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-NUTRICIONAL |
| titulo | Definición de los campos nutricionales del producto y de lo que las reglas consumirán |
| tipo_documento | Documento derivado. Definición de datos para análisis |
| documentos_fuente | `./backlog-historias-de-usuario.md` (`HU-22`, `HU-26`, `HU-30`, `HU-31`, `HU-32`, `HU-34`); `./smartfood.md` (`ALC-IN-15`, `ALC-IN-20`, `ALC-IN-21`, `ALC-OUT-20`, `INV-9`); `./decisiones-tecnicas.md` (`DT-8`) |
| cubre | `TT-44` — Definición de los campos nutricionales que consumirán las reglas de recomendación |
| responsable | Alejandro (análisis) |
| idioma | es-CO |
| version | 1.0 |

### [S0.1] Qué decide este documento

**Qué se le pide a la cafetería que declare de cada producto, y por qué esos campos y no
otros.** Lo escribe quien hace el análisis porque la lista no sale de lo que es cómodo
guardar, sino de lo que las reglas de `ALC-IN-21` van a tener que calcular tres sprints
más tarde. Un campo que falte entonces no se puede reconstruir hacia atrás: los productos
ya vendidos llevan copiada la información que había (`DT-8`), y lo que no se declaró no
estaba.

---

## [S1] Qué va a consumir estos campos

| Historia | Qué calcula | Qué campos necesita |
|---|---|---|
| `HU-22` | Congela la información nutricional en la línea de venta | **Todos**, copiados tal cual |
| `HU-30` | Historial de consumo con la información de cada venta | Los copiados en `HU-22` |
| `HU-31` | Alertas de frecuencia de consumo **por categoría** | Ninguno nutricional: la categoría |
| `HU-32` | Agregados frente a valores de referencia oficiales | Energía y los tres nutrientes críticos |
| `HU-33` | Gasto frente a saldo recargado | Ninguno: el precio |

`ALC-OUT-20` excluye toda valoración nutricional individualizada, e `INV-9` obliga a
declarar las recomendaciones como orientativas. **Eso acota la lista hacia abajo:** no hay
que declarar micronutrientes, índices ni nada que solo sirva para una valoración que el
sistema no puede hacer.

---

## [S2] Los campos

| Campo | Tipo | Obligatorio | Por qué está |
|---|---|---|---|
| `porcion` | texto | No | Qué es una unidad vendible: «paquete de 30 g», «vaso de 200 ml» |
| `energia_kcal` | entero | No | Es el agregado que `HU-32` compara primero |
| `proteinas_g` | decimal | No | Cierra el reparto de macronutrientes del historial (`HU-30`) |
| `carbohidratos_g` | decimal | No | Ídem, y es el continente de los azúcares |
| `azucares_g` | decimal | No | **Nutriente crítico** del etiquetado frontal |
| `grasas_totales_g` | decimal | No | Ídem, y es el continente de las saturadas |
| `grasas_saturadas_g` | decimal | No | **Nutriente crítico** |
| `sodio_mg` | entero | No | **Nutriente crítico** |

### [S2.1] Por porción vendible, no por 100 g

**Es la decisión que más consecuencias tiene, y va contra la costumbre de la etiqueta.**

Lo que se vende es una unidad: un paquete, un vaso, una empanada. La venta copia estos
valores (`DT-8`) y los reportes de `HU-32` los **suman** a lo largo de un periodo. Con
valores por 100 g, cada suma necesitaría además el peso de la porción y una
multiplicación; el día que a un producto le falte ese peso, el agregado sale **más bajo
que el real** y parece un dato en vez de un hueco.

Con valores por porción, sumar es sumar. El campo `porcion` queda como texto porque su
función es que una persona sepa a qué se refieren las cifras, no entrar en ningún cálculo.

> **Lo que esto le cuesta a la cafetería:** la etiqueta del proveedor suele venir por
> 100 g, así que alguien tiene que hacer la regla de tres una vez, al dar de alta el
> producto. Es preferible a hacerla en cada reporte, donde el error no se ve.

### [S2.2] Ninguno es obligatorio, y vacío no es cero

El primer criterio de `HU-26` dice que el producto **admite** información nutricional. No
dice que la exija, y con razón: una cafetería no tiene la ficha técnica de todo lo que
vende el primer día, y un catálogo que no se puede cargar sin ella no se carga.

**Vacío significa «no declarado».** Es distinto de cero y los agregados de `HU-32` tienen
que tratarlo distinto: sumar un producto sin declarar como si aportara cero da una cifra
más baja que la real y la presenta como un hecho. La regla, cuando se escriba, debe
**excluir** del agregado los productos sin declarar y **decir cuántos excluyó**.

El modelo expone `declara_informacion_nutricional` justamente para eso.

### [S2.3] Lo que la base comprueba

Dos restricciones, porque son errores de captura que se pueden ver sin saber nada del
producto:

- las **grasas saturadas** no pueden superar a las totales;
- los **azúcares** no pueden superar a los carbohidratos.

En ambos casos, si alguno de los dos está sin declarar, no hay nada que comparar y la
restricción no aplica.

**No se comprueba la coherencia entre energía y macronutrientes** —los 4/4/9 kcal por
gramo—, y es deliberado: la energía declarada en una etiqueta real no cuadra exactamente
con esa cuenta, y una restricción que rechaza etiquetas correctas obliga a inventarse los
datos para poder guardarlos.

---

## [S3] Lo que este documento NO decide

- **La tabla de valores de referencia de `HU-32`.** `ALC-IN-21` dice «los valores de
  referencia publicados por la autoridad sanitaria colombiana», y esa tabla es un dato
  externo con una fuente citable: hay que **fijar cuál es, con su norma y su fecha**,
  antes de escribir la regla. El candidato que el equipo debe verificar es la
  reglamentación de etiquetado nutricional frontal del Ministerio de Salud —de ahí salen
  los tres nutrientes críticos de `[S2]`—, pero **este documento no la da por confirmada**:
  no se cita una norma que no se ha leído.
- **Los umbrales de las alertas de `HU-31`.** Cuántas veces por semana en una categoría
  dispara un aviso es una regla determinística que hay que escribir, y no es un campo.
- **Qué se copia exactamente en la línea de venta.** `DT-8` fija que se copia; la lista de
  columnas de `LineaVenta` es del Sprint 2.

---

## [ANEXO A] Por qué esta lista es corta

La tentación es declarar todo lo que trae una etiqueta: fibra, colesterol, grasas trans,
vitaminas, sodio y potasio por separado. Se descartó por tres razones, en orden:

1. **`ALC-OUT-20` excluye la valoración nutricional individualizada.** Los campos que solo
   servirían para eso no tienen quién los consuma dentro del alcance.
2. **Cada campo es trabajo de captura para la cafetería**, producto a producto. Un catálogo
   con veinte campos por producto se llena mal o no se llena.
3. **Un campo que nadie lee es un campo que nadie corrige.** Aparecería en el historial de
   `HU-30` con datos equivocados y nadie se enteraría.

Añadir uno más adelante es una migración y volver a capturar; quitarlo cuando ya se copió
en ventas pasadas es reescribir el pasado, que es justo lo que `DT-8` impide. **Ante la
duda, este documento se quedó corto a propósito.**
