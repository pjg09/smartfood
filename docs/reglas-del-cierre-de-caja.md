# SmartFood — Las reglas del cierre de caja

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-REGLAS-CIERRE |
| titulo | Qué entra en el cuadre, qué no, y por qué el efectivo esperado no se digita |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./smartfood.md` (`PA-7`, `ALC-IN-18`, `ALC-IN-22`, `S11`); `./decisiones-de-alcance.md` (`DEC-1`, `DEC-6`, `INVD-5`); `./decisiones-tecnicas.md` (`DT-4`, `DT-5`, `DT-8`, `DT-15`, `DT-19`); `./backlog-historias-de-usuario.md` (`HU-53`, `HU-54`, `HU-55`, `HU-56`); `ventas/models.py`, `ventas/services.py`, `ventas/selectors.py` |
| tipo_documento | Documento operativo. **No es un artefacto de Scrum ni un entregable** |
| creado | 2026-09-19, con `PR-07` del Sprint 5 |
| idioma | es-CO |
| version | 1.0 |

### [S0.1] Qué responde este documento

**Contra qué cifra se cuenta el dinero del cajón, de dónde sale esa cifra y qué se queda
fuera.**

Es el tercero de la serie, después de `./reglas-de-la-venta.md` y
`./reglas-del-pedido-anticipado.md`, y existe por lo mismo: el cuadre acumula **seis reglas
que `HU-55` no menciona** y que se pierden en cuanto nadie las escribe. La que más —que el
efectivo esperado se guarda **congelado** y no se recalcula al leerlo— no es visible desde
ninguna pantalla, y es la que decide si un cierre firmado en septiembre sigue diciendo lo
mismo en noviembre.

> **El código manda.** Este documento describe `ventas/models.py`, `ventas/services.py` y
> `ventas/selectors.py`; si algún día discrepan, el equivocado es este. Lo que aquí se fija
> son **las razones**, que el código no puede demostrar por sí solo.

---

## [S1] Qué es un cierre de caja

Una fila de `ventas.CierreDeCaja`, y **una sola por jornada**:

| Campo | De dónde sale | Quién lo pone |
|---|---|---|
| `fecha` | La jornada que se cuadra | La pantalla, o quien llame al servicio |
| `cajero` | Quién contó el dinero | El `actor` del servicio |
| `efectivo_esperado` | **Suma de las ventas en efectivo de esa jornada** | El servicio, calculándolo (`INVD-5`) |
| `efectivo_contado` | Lo que hay en el cajón, con la base incluida | El cajero |
| `base` | Lo que había para dar cambio | El cajero |
| `motivo` | Por qué no cuadra | El cajero, **obligatorio si hay diferencia** |

Y una cifra que **no es un campo**:

```
diferencia = efectivo_contado − base − efectivo_esperado
```

Positiva es **sobrante**; negativa, **faltante**.

---

## [S2] La regla que da sentido a la historia

`PA-7` describe lo que la cafetería hace hoy: cuadra el efectivo recaudado contra **su
estimación** de lo vendido. `HU-55` no automatiza esa estimación: **la sustituye**.

`INVD-5` lo dice como invariante —«el efectivo esperado del día debe poder explicarse a
partir de las ventas en efectivo registradas»— y en el código no se sostiene con un cálculo
bien hecho, sino con **una ausencia**:

- `cerrar_caja` **no tiene parámetro** para el efectivo esperado.
- `CierreDeCajaForm` **no tiene campo** para él.
- El único camino que escribe un `CierreDeCaja` es ese servicio.

Por eso la prueba que lo vigila es de ausencia (`ElEsperadoNoSeDigitaTest`), y lleva su
contraprueba: que el servicio **sí** llama al selector que lo calcula. Una prueba de ausencia
sin contraprueba pasa sola el día que deja de proteger.

**Si algún día alguien añade un argumento para «corregir» el esperado, la historia deja de
significar algo.** No sería una mejora de usabilidad: sería volver a `PA-7` con otra
pantalla.

---

## [S3] Qué entra en el cuadre y qué no

Entra `MedioDePago.EFECTIVO`. Nada más.

| Medio | ¿Entra? | Por qué |
|---|---|---|
| **Efectivo** | **Sí** | Es lo que está en el cajón |
| **Transferencia** | **No** | Va de la app bancaria del cliente a la cuenta de la cafetería (`DEC-1`): ese dinero **nunca pasó por la caja** |
| **Billetera** | **No** | La compra de un estudiante descuenta saldo, no billetes (`HU-54`) |

**La exclusión de la transferencia es la condición que más fácil se pierde**, y su
consecuencia se nota enseguida: sumarla haría que todo cierre diera un faltante igual a lo
transferido, y el motivo obligatorio se llenaría de «faltan las transferencias» hasta dejar
de significar nada.

**Las reservas no necesitan una regla propia.** Una reserva es siempre de un estudiante, así
que es siempre de billetera —lo impone `venta_medio_de_pago_segun_el_cliente`—, y el filtro
por efectivo las deja fuera sin que nadie lo escriba. Que sea consecuencia y no excepción es
lo que hace que siga siendo cierto si mañana cambia algo del pedido anticipado.

---

## [S4] Por qué el esperado se guarda, si es una suma de otra tabla

Parece la columna `saldo` que `DT-4` prohíbe y la columna `existencias` que `DT-5` prohíbe.
**No lo es**: es la misma figura que `DT-8` con el precio congelado de la línea de venta.

Lo que se guarda no es «lo que suman hoy las ventas de aquel día», sino **contra qué cifra se
contó el dinero aquella tarde**.

La diferencia se nota con **una venta registrada tarde**. Si el esperado se recalculara al
leerlo, un cobro asentado después del cuadre movería la diferencia de un cierre ya firmado: el
descuadre de $2.000 que alguien explicó por escrito pasaría a ser otro, o a no existir, sin
que nadie tocara nada. Un asiento no se reescribe (`INV-2`, `INV-3`), y esto lo es.

`INVD-5` sigue en pie: la cifra **se explica** yendo al reporte de ventas del día filtrado
por efectivo (`HU-35`). Lo que la invariante prohíbe es que salga de otro sitio, no que quede
escrita.

**Y por la misma razón la diferencia no es columna.** Sale de tres columnas de la misma fila
que ya no se mueven, así que guardarla sería la desnormalización que `DT-19` evita: dos
cifras que tienen que coincidir siempre acaban un día no coincidiendo. Es el caso de
`LineaVenta.importe`, que tampoco es columna. `HU-55` pide «calcular y registrar la
diferencia», y queda registrada: los tres sumandos están escritos y la resta no admite otro
resultado.

---

## [S5] El motivo obligatorio, en dos capas

Cuarto criterio de `HU-55`, con el mismo criterio que `ALC-IN-18` aplica a la merma:

- **El servicio** lanza `CierreSinMotivo` y da el mensaje que el cajero lee.
- **La base** lo garantiza con `cierre_de_caja_diferencia_con_motivo`.

No es duplicación: es `DT-15`, regla 2. Un `if` protege el camino que lo tiene; la
restricción protege los que todavía no existen — un comando, una tarea programada, una
consola con prisa. Cuando se escribió esta línea el ejemplo era el reporte de `HU-56`, que
llegó dos PR después; el siguiente camino tampoco se sabe cuál será.

Y se escribe con `\S`, no con `!= ""`, por lo que costó descubrirlo en la merma (`TT-140`):
tres espacios no son la cadena vacía y tampoco son un motivo.

---

## [S6] Un cierre por jornada, y no uno por cajero

`DEC-6` lo dice dos veces: «el cuadre es **diario**» y «**no hay apertura formal de turno**».
Lo impone `cierre_de_caja_uno_por_jornada`, una restricción de unicidad sobre la fecha.

**Un cierre por cajero sería un turno con otro nombre**, y además obligaría a declarar una
base al empezar, que es justo lo que la decisión descarta. Con dos cajeros en la misma
jornada el cuadre sigue siendo uno, y `cajero` dice **quién contó el dinero**, no de quién son
las ventas.

> **Es una simplificación declarada, no un descuido.** Con dos personas turnándose en un solo
> cajón, un descuadre no se puede atribuir a ninguna de las dos. Resolverlo es un módulo de
> turnos, y `DEC-6` lo deja fuera a propósito: no incide en el problema que el proyecto ataca.

---

## [S7] Las seis reglas que ninguna historia dice

1. **El esperado no tiene por dónde entrar digitado.** Ni parámetro, ni campo (`INVD-5`).
2. **La transferencia queda fuera del cuadre**, y la billetera también.
3. **El esperado se congela al cerrar**, como el precio de una línea de venta (`DT-8`).
4. **La diferencia no es una columna**: se calcula de la fila (`DT-19`).
5. **La base se resta de lo contado antes de comparar.** Sin restarla, todo cierre daría un
   sobrante igual a la base y el motivo obligatorio dejaría de significar algo.
6. **Un cierre no se edita ni se repite.** No hay `change` ni `delete` en ninguna parte: es
   un asiento, como los de los otros dos libros.

---

## [S8] Quién puede

| Acción | Quién | Dónde |
|---|---|---|
| **Cuadrar la caja** (`HU-55`) | **Solo el cajero** (`USR-3`) | `/punto-de-venta/cierre/` |
| **Consultar los cierres** (`HU-56`) | **Solo la administración** (`USR-4`) | `INT-3`, `/admin/ventas/cierredecaja/` |

Son dos filas distintas y dos pantallas distintas, como `[S11]` separa registrar ventas de
consultar sus reportes. La autorización de la primera vive en
`ventas.selectors.informacion_del_cierre` y en `ventas.services.cerrar_caja`, no en la vista:
es el único camino por el que el recaudo en efectivo del día llega a una pantalla, y responde
`PermissionDenied` aunque alguien escriba la URL (`DT-11`, `INV-4`).

El reporte de cierres añade dos cosas que el listado no da solo, y las dos salen de `[S7]`:

- **Dos cifras de descuadre**, porque la suma con signo se compensa sola. `HU-56` pide
  detectar un **patrón**, y con la neta un periodo con veinte descuadres se lee como uno que
  cuadró.
- **Un enlace por cierre a las ventas en efectivo de su jornada.** Es el tercer criterio de
  la historia hecho comprobable: `INVD-5` dice que el esperado «se explica» desde las ventas
  registradas, y una cifra que no se puede abrir no explica nada.

**El cierre alimenta la auditoría de `ALC-IN-22`** (`DEC-6`), que es `HU-37` y llega con
`PR-09`.

---

## [ANEXO A] De dónde salió cada regla

| Regla | Origen |
|---|---|
| El esperado se calcula, no se digita | `INVD-5`, `DEC-6`, `PA-7` |
| La transferencia no entra en el cuadre | `DEC-6`, `DEC-1` |
| La billetera tampoco | `HU-54`, segundo criterio |
| Motivo obligatorio si hay diferencia | `HU-55`, cuarto criterio; `ALC-IN-18` |
| Un cierre por jornada, sin apertura de turno | `DEC-6` |
| El esperado se congela | `DT-8`, `INV-2`, `INV-3` — decidido en `TT-171` |
| La diferencia no es columna | `DT-19`; precedente de `LineaVenta.importe` |
| La regla la impone la base, no un `if` | `DT-15`, regla 2; precedente de `INV-8` en la merma |
