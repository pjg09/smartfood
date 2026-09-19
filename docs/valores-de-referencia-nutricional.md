# SmartFood — Los valores de referencia nutricional

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-REFERENCIA-NUTRICIONAL |
| titulo | Qué tabla de la autoridad sanitaria colombiana se usa como referencia, de dónde sale y qué no dice |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./smartfood.md` (`ALC-IN-21`, `ALC-OUT-20`, `INV-9`, `FUN-7`); `./backlog-historias-de-usuario.md` (`HU-32`); `./campos-nutricionales.md` (`[S2]`, `[S3]`); **Resolución 810 de 2021 del Ministerio de Salud y Protección Social de Colombia** |
| tipo_documento | Documento derivado. **Investigación documental y definición de datos** |
| cubre | `TT-162` — Localizar y registrar los valores de referencia de la autoridad sanitaria colombiana, con su fuente |
| responsable | Alejandro (análisis), `[S12]` |
| creado | 2026-09-19, con `PR-03` del Sprint 5 |
| idioma | es-CO |
| version | 1.0 |

### [S0.1] Qué decide este documento

**Contra qué cifras se comparan los agregados nutricionales de `HU-32`, y con qué autoridad.**

El primer criterio de la historia es exigente: *«la referencia es la publicada por la
autoridad sanitaria colombiana»*. No vale una tabla de internet ni un valor razonable. Si en
la sustentación preguntan de dónde salen estas cifras, **este documento es la respuesta**, y
por eso trae la norma, el artículo, la tabla y la columna.

`[S3]` de `./campos-nutricionales.md` dejó esta tarea señalada como pendiente y **avisó de
no dar por confirmada ninguna norma sin leerla**. Se leyó. Qué se comprobó y cómo está en
`[S1.1]`.

---

## [S1] La fuente

> **Resolución 810 de 2021** del **Ministerio de Salud y Protección Social**, del
> **16 de junio de 2021**, publicada en el **Diario Oficial No. 51.707**.
> *«Por la cual se establece el reglamento técnico sobre los requisitos de etiquetado
> nutricional y frontal que deben cumplir los alimentos envasados o empacados para consumo
> humano»*.
>
> **Artículo 15 — «Valores diarios de referencia de nutrientes»**, `Tabla 9` (VRN-N) y
> `Tabla 10` (VRN-ENT).
> Columna **«Niños mayores de 4 años y adultos»**.

Modificada por la **Resolución 2492 de 2022** y corregida por la **Resolución 254 de 2023**.
El texto compilado que se consultó ya las incorpora, y el artículo 15 no lleva nota de
modificación.

### [S1.1] Qué se comprobó, y qué no se pudo comprobar

**Las cifras se leyeron en dos compilaciones oficiales independientes** —la del Invima y la
de la Superintendencia Nacional de Salud— y coinciden entre sí. El PDF del Ministerio es un
documento escaneado y sus tablas no son legibles como texto; la copia de la Alcaldía de
Bogotá trae las tablas como imagen. Por eso la lectura se hizo sobre los normogramas, que
son los que publican el texto compilado.

**Lo que no se pudo confirmar, y hay que decirlo:** en **abril de 2026** el Ministerio puso
en consulta pública un proyecto de resolución que **derogaría** la 810 y unificaría el
reglamento —añadiendo, entre otras cosas, una advertencia de ultraprocesado—. A la fecha de
este documento los normogramas oficiales siguen compilando la 810 como vigente, pero **no se
pudo verificar si el proyecto ya se expidió**. Se registra como está: es más útil que
afirmar una vigencia que no se comprobó.

> **Cómo se mitiga:** los siete valores viven en **un solo sitio del código**,
> `reportes/referencia.py`, con esta misma cita al lado. Actualizarlos el día que cambie la
> norma es cambiar una tabla y una prueba, no buscar cifras repartidas por las pantallas.

---

## [S2] La tabla que se usa

Columna **«Niños mayores de 4 años y adultos»**, que es la que cubre a un estudiante de
colegio. La norma da **una sola columna** para toda esa población: ver `[S3]`.

### [S2.1] De `Tabla 9` — VRN-N, valores de *necesidades*

| Nutriente | Referencia diaria |
|---|---|
| Energía | **2000 kcal** |
| Grasa total | **66 g** |
| Carbohidratos totales | **300 g** |
| Proteínas | **50 g** |

### [S2.2] De `Tabla 10` — VRN-ENT, valores *máximos*

Son los de enfermedades no transmisibles, y la norma los rotula «Máx.». **Los tres coinciden
con los nutrientes críticos** que `[S2]` de `./campos-nutricionales.md` eligió capturar, que
es la señal de que aquella decisión apuntaba a la tabla correcta.

| Nutriente | Máximo diario |
|---|---|
| Sodio | **2000 mg** |
| Grasa saturada | **20 g** |
| Azúcares añadidos | **50 g** |

### [S2.3] Lo que la norma trae y aquí no se usa

`Tabla 9` incluye fibra dietaria (28 g), vitaminas y minerales; `Tabla 10`, grasas trans y
colesterol. **Nada de eso se compara**, porque el catálogo no lo captura: `ANEXO A` de
`./campos-nutricionales.md` se quedó corto a propósito, y una comparación sin dato de origen
no es una comparación.

Los siete campos que el producto sí declara tienen, cada uno, su valor en esta tabla. **No
falta ninguno.**

---

## [S3] Por qué la columna de etiquetado y no una recomendación por edad

Es la decisión de fondo de `TT-162`, y va con su argumento entero porque parece la peor
opción y es la correcta.

**La alternativa** sería la Resolución 3803 de 2016, que establece las Recomendaciones de
Ingesta de Energía y Nutrientes para la población colombiana **por grupo de edad y sexo**.
Es más fina: no es lo mismo un niño de 7 años que uno de 16.

**Y justamente por eso no se usa.** Elegir la fila según la edad y el sexo del estudiante es
individualizar la referencia, y una comparación individualizada contra un requerimiento
personal es **valoración nutricional individualizada** — lo que `ALC-OUT-20` excluye por
constituir un acto profesional del área de la salud, y lo que `INV-9` obliga a no hacer.

El VRN del etiquetado no tiene ese problema **por su propia naturaleza**: es el valor que la
norma manda imprimir en cualquier etiqueta, el mismo para toda la población mayor de cuatro
años. No afirma lo que un niño necesita. Comparar contra él es decir *«esto es tanto por
ciento de lo que la etiqueta de cualquier producto usa como referencia»*, que es una regla de
tres pública y comprobable, no un diagnóstico.

> **Consecuencia que hay que asumir y decir en pantalla:** estos 2000 kcal **no son** lo que
> el estudiante necesita. Es el valor de referencia del etiquetado. Si algún día el proyecto
> quisiera comparar contra el requerimiento real de un menor, eso es otra historia, otra
> norma y —seguramente— un profesional de la salud de por medio.

---

## [S4] Las tres salvedades, y por qué se declaran en vez de taparse

### [S4.1] El catálogo declara azúcares **totales**; la referencia es de azúcares **añadidos**

No son lo mismo: los totales incluyen los que el alimento trae de por sí —la fruta, la
leche—, y los añadidos son los que se le pusieron. `Tabla 10` dice «Azúcares añadidos, Máx.»,
y `./campos-nutricionales.md` capturó «azúcares» a secas.

**La comparación se hace igual, y se declara.** Dos razones:

1. El azúcar es el nutriente crítico más visible del etiquetado frontal; no compararlo
   dejaría el reporte ciego justo donde más se mira.
2. **El error va del lado seguro.** Los azúcares totales son siempre mayores o iguales que
   los añadidos, así que el porcentaje que se muestra es **más alto** que el real frente a
   ese máximo. Señala de más, nunca de menos.

Cambiar el campo del catálogo a «azúcares añadidos» sería más correcto y **no se hace aquí**:
reescribiría el significado de un dato que las ventas ya congelaron (`DT-8`). Si alguna vez
se hace, es una migración, una recaptura del catálogo y una decisión registrada.

### [S4.2] La cafetería no es toda la dieta

El sistema solo ve lo que se compra en el colegio. El desayuno, el almuerzo de casa y la
comida no pasan por aquí, y **no hay forma de saber cuánto falta**.

Por eso la pantalla dice «esto aportó lo comprado en la cafetería», nunca «esto comió». Un
porcentaje bajo no significa que el estudiante coma poco.

### [S4.3] Un producto sin ficha nutricional queda fuera del agregado, y se dice cuántos

Es una instrucción literal de `[S2.2]` de `./campos-nutricionales.md`: **la regla debe
excluir del agregado los productos sin declarar y decir cuántos excluyó.**

Sumar un producto sin ficha como si aportara cero da una cifra más baja que la real y la
presenta como un hecho. Se excluye y se dice — que es la misma decisión que el historial
toma al pintar un hueco en vez de una fila de ceros (`HU-30`).

---

## [S5] Cómo se calcula, en una frase

> **Se suma lo consumido en los últimos 14 días, se divide entre los días en que hubo
> consumo, y ese promedio se compara con la referencia diaria.**

- **La ventana es la misma que la de las alertas de frecuencia** (`./reglas-de-frecuencia-de-consumo.md`),
  y también lo es la definición de «consumido»: la reserva sin recoger no cuenta y la
  entregada cuenta el día en que se recogió. Dos periodos distintos en la misma pantalla
  serían dos pantallas.
- **Se divide entre los días con consumo, no entre 14.** La referencia es diaria, así que lo
  comparable es un día de cafetería, no el promedio de un periodo en el que muchos días no
  se compró nada. Dividir entre 14 daría una cifra más baja y sin significado.
- **Determinístico y reproducible** (segundo criterio de `HU-32`): son sumas y una división,
  con redondeo declarado y sin ninguna fuente de azar. La misma consulta, el mismo día, da
  el mismo número.

---

## [S6] Lo que este documento NO decide

- **Qué es mucho y qué es poco.** Aquí no hay umbrales: el porcentaje se enseña y quien lo
  interpreta es la familia. Los umbrales del proyecto son los de frecuencia (`TT-158`), y
  esos no miran ni un nutriente.
- **Los campos del catálogo.** Son de `TT-44` y no se tocan: esta tabla se adapta a lo que el
  producto declara, no al revés.
- **El aviso de `INV-9`.** Es `TT-161`, ya construido: la comparación se publica dentro del
  mismo bloque que lo lleva, así que no hay forma de enseñarla sin descargo.

---

## [ANEXO A] Dónde viven estas cifras en el código

`reportes/referencia.py`, en una sola tabla, con la cita de `[S1]` en el docstring y la clase
de cada valor —necesidad o máximo— al lado, porque no significan lo mismo: 66 g de grasa es
un valor de referencia y 20 g de grasa saturada es un techo.

`reportes/tests_referencia.py` fija los siete números contra este documento. Si alguien
cambia uno sin pasar por aquí, falla.
