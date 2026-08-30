# SmartFood — Formato del archivo de carga

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-FORMATO-CARGA |
| titulo | Contrato de datos del archivo de carga de estudiantes y acudientes |
| tipo_documento | Documento derivado. Contrato de datos con la institución educativa |
| documentos_fuente | `./backlog-historias-de-usuario.md` (`HU-01`, `HU-02`); `./smartfood.md` (`ALC-IN-01`, `ALC-IN-04`, `ALC-OUT-07`) |
| cubre | `TT-22` — Definición del formato: columnas, tipos y obligatoriedad |
| responsable | Alejandro (análisis) |
| idioma | es-CO |
| version | 1.0 |

Esto no es documentación de una implementación: **es el contrato con el colegio**. Define
qué archivo se le pide a la institución educativa y qué se hace con cada columna. Por eso
lo escribe quien hace el análisis y no quien programa el lector.

---

## [S1] El archivo

**CSV codificado en UTF-8, separado por comas, con una fila de encabezado.**

CSV y no una hoja de cálculo porque cualquier sistema del colegio lo exporta, se abre en
un editor de texto cuando algo va mal, y no arrastra formatos, fórmulas ni macros. Un
`.xlsx` obligaría a interpretar celdas con tipo, y una fecha mal interpretada en un
archivo de menores es peor que un error de lectura.

**Una fila por estudiante.** Si un acudiente tiene tres hijos matriculados, aparece en
tres filas con los mismos datos. Es redundante a propósito: el colegio exporta desde su
sistema de matrícula, que también está organizado por estudiante.

---

## [S2] Columnas

| Columna | Tipo | Obligatoria | Regla |
|---|---|---|---|
| `documento_estudiante` | Texto, 5–20 caracteres | **Sí** | Identifica al estudiante. **Único en todo el sistema** |
| `nombre_estudiante` | Texto, 1–200 caracteres | **Sí** | Nombre completo |
| `documento_acudiente` | Texto, 5–20 caracteres | **Sí** | Identifica al acudiente |
| `nombre_acudiente` | Texto, 1–200 caracteres | **Sí** | Nombre completo |
| `correo_acudiente` | Correo electrónico | **Sí** | **Es la identidad de su cuenta.** Ver `[S3]` |

Los espacios sobrantes al principio y al final se recortan. Las columnas se identifican
**por su nombre en el encabezado**, no por su posición: el orden puede variar.

**No hay más columnas, y eso es deliberado.** El código de tarjeta lo genera el sistema y
no lo trae el archivo (`INV-7`, `HU-14`): un código que viniera del colegio sería
adivinable o secuencial, que es justo lo que la invariante prohíbe. La fotografía se carga
después, una por una (`HU-57`). El grado, el curso y la jornada no se piden porque ninguna
historia los usa; pedir datos de menores que no se van a usar contradice `ALC-OUT-08`.

---

## [S3] Cómo se agrupan los acudientes

**El correo identifica al acudiente.** Dos filas con el mismo `correo_acudiente` son la
misma persona, y sus estudiantes quedan a cargo de una sola cuenta (`ALC-IN-04`,
`HU-04`). Es la regla que hace cierto el cuarto criterio de `HU-01`.

Se usa el correo y no el documento porque **el correo es la identidad de la cuenta**: es
por donde llega la invitación y es con lo que inicia sesión. Si dos filas trajeran el
mismo documento y correos distintos, serían dos cuentas; y si trajeran el mismo correo y
documentos distintos, el archivo se contradice y `HU-02` lo rechaza.

> Cuando el mismo correo aparece con nombre o documento distintos en dos filas, **el
> archivo está mal**, no el sistema. Lo detecta la validación de `HU-02` y no se escribe
> nada.

---

## [S4] Ejemplo

```csv
documento_estudiante,nombre_estudiante,documento_acudiente,nombre_acudiente,correo_acudiente
1001234501,Ana Sofía Restrepo Ruiz,43512345,Marta Ruiz Ochoa,marta.ruiz@example.com
1001234502,Tomás Restrepo Ruiz,43512345,Marta Ruiz Ochoa,marta.ruiz@example.com
1001234503,Julián Ospina Vélez,71234567,Andrés Ospina Mesa,andres.ospina@example.com
```

Tres estudiantes, **dos acudientes**: Ana Sofía y Tomás quedan a cargo de la misma cuenta.

Todos los datos de todos los ejemplos son ficticios (`ALC-OUT-07`), y el dominio
`example.com` está reservado por la RFC 2606: nadie puede registrarlo.

---

## [S5] Lo que el sistema hace con el archivo

1. **Lee y valida entero, sin escribir nada** (`HU-02`).
2. Si hay un solo error, **no escribe ninguna fila**: la carga es todo o nada.
3. Si no hay errores, crea en una sola transacción los acudientes que falten, sus cuentas
   y los estudiantes, y los vincula.
4. La cuenta del acudiente nace **sin contraseña utilizable** (`INV-6`, `INVD-1`).

**El correo de invitación no se entrega en la carga masiva** (`DEC-9`): las direcciones
son ficticias y no corresponden a ningún buzón. La entrega real se demuestra con las altas
de una en una.

---

## [S6] Lo que este documento no decide

`HU-02` define **qué se valida y cómo se reporta**. Aquí solo se declara qué columnas hay,
de qué tipo y cuáles son obligatorias. La lista de comprobaciones —duplicados, correos
mal formados, filas contradictorias— y el reporte de errores son `TT-25` y `TT-26`, en
`PR-13`.
