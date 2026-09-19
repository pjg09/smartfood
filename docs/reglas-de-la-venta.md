# SmartFood — Las reglas de la venta

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-REGLAS-VENTA |
| titulo | Qué comprueba la venta, en qué orden y por qué |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./smartfood.md` (`INV-1`, `INV-3`, `INV-5`, `ALC-IN-09`); `./decisiones-de-alcance.md` (`INVD-2`, `INVD-7`); `./decisiones-tecnicas.md` (`DT-6`, `DT-15`, `DT-24`); `./backlog-historias-de-usuario.md` (`HU-18` … `HU-21`, `HU-50`, `HU-60`); `ventas/services.py` |
| tipo_documento | Documento operativo. **No es un artefacto de Scrum ni un entregable** |
| creado | 2026-09-17, al cerrar el Sprint 3 |
| idioma | es-CO |
| version | 1.0 |

### [S0.1] Qué responde este documento

**Una sola pregunta: qué tiene que pasar para que una venta se registre, y qué se le dice al
cajero cuando no pasa.**

Existe porque `registrar_venta` acumula ya **seis comprobaciones dentro de una misma
transacción**, puestas por seis historias distintas a lo largo de dos sprints. El orden entre
ellas **no es casual y no está en ninguna historia**: es una decisión que se tomó tres veces,
cada una en el PR que añadía una condición nueva, y hasta ahora solo vivía en los comentarios
del código y repartida entre cuatro planes de PR.

**Se escribió antes de que el Sprint 4 tocara esta misma transacción, y sirvió.** Los
pedidos anticipados (`HU-23` … `HU-25`) llegaron, retiran mercancía y pasan por la misma
puerta de `INVD-2` — y **no añadieron ninguna comprobación**: la reserva valida por esta
misma lista (`[S7]`). Siguen siendo seis.

Quien vaya a tocar este servicio necesita saber qué hay aquí dentro **antes** de añadir la
séptima.

> **El código manda.** Este documento describe `ventas/services.py`; si algún día discrepan,
> el equivocado es este. Lo que aquí se fija son **las razones**, que el código no puede
> demostrar por sí solo.

**Su gemelo es `./reglas-del-pedido-anticipado.md`**, para el otro flujo transaccional: qué
mueve cada momento de un pedido y qué no. La reserva valida por esta misma lista, así que los
dos documentos se leen juntos al tocar `ventas/services.py`.

---

## [S1] El orden es la invariante

`DT-6` lo dice en tres palabras y el cuerpo de `registrar_venta` se lee de arriba abajo:

```
1. BLOQUEAR   select_for_update() sobre la billetera y sobre los productos
2. VALIDAR    las seis comprobaciones, leyendo DENTRO del bloqueo
3. ESCRIBIR   la venta, sus líneas y los dos libros
```

Todo dentro de **una** `transaction.atomic()`. Si algo falla —una validación o la propia
escritura a medio camino— **no queda nada**: ni venta, ni líneas, ni movimientos. Eso es el
primer criterio de `HU-21`.

**Validar antes del bloqueo daría el mismo resultado en cualquier prueba secuencial** y
rompería `INV-1` en producción con dos cajas cobrando a la vez. Es la peor clase de error: el
que pasa las pruebas. Por eso hay pruebas que no miran el resultado sino **el orden de las
consultas emitidas** —el `SELECT … FOR UPDATE` antes de la lectura que decide—, en
`ventas/tests_rechazo_por_alergeno.py` y `ventas/tests_rechazo_por_limite.py`.

**Los productos se bloquean ordenados por identificador.** Dos ventas simultáneas que
compartan dos productos podrían bloquearlos en orden distinto y esperarse para siempre. Un
orden total y fijo hace imposible el ciclo.

---

## [S2] Las seis comprobaciones, en orden

| # | Comprueba | Rechaza con | Historia | Se arregla… |
|---|---|---|---|---|
| 1 | Que el estudiante **pueda comprar** | `EstudianteNoPuedeComprar` · `estudiante-no-opera` | `HU-50` | …en secretaría (`HU-49`), no en la caja |
| 2 | Que ningún producto declare un **alérgeno bloqueado** | `AlergenoBloqueado` · `alergeno-bloqueado` | `HU-18` (`TST-1`) | …solo si el acudiente retira el bloqueo |
| 3 | Que ningún producto esté en la **lista de bloqueados** | `ProductoBloqueado` · `producto-bloqueado` | `HU-60` | …solo si el acudiente retira el bloqueo |
| 4 | Que haya **existencias** | `ExistenciasInsuficientes` · `existencias-insuficientes` | ninguna — ver `[S4]` | …quitando el renglón |
| 5 | Que quepa en el **cupo del día** | `LimiteDiarioSuperado` · `limite-diario` | `HU-20` (`TST-2`) | …quitando renglones, o mañana |
| 6 | Que alcance el **saldo** | `SaldoInsuficiente` · `saldo-insuficiente` | `HU-19` (`TST-2`) | …recargando |

Antes de las seis hay dos comprobaciones que no son del estudiante y por eso no están en la
tabla: **quién cobra** —`[S11]` da «registrar ventas» solo al cajero— y **que el carrito
tenga algo**. Las dos ocurren fuera del bloqueo, porque no dependen de ningún dato que pueda
cambiar debajo.

### [S2.1] Por qué ese orden, y no otro

**La regla, en una frase: lo que no se arregla en el mostrador va delante.**

El cajero tiene una fila esperando y una sola oportunidad de decirle al estudiante qué pasa.
Si el sistema contesta el motivo equivocado, manda a la familia a hacer algo que no va a
funcionar:

- **«No alcanza el saldo» sobre una tarjeta bloqueada** manda al acudiente a recargar para
  que la venta se rechace igual, esta vez sin explicación nueva.
- **«Se acabó el cupo» sobre un alérgeno bloqueado** invita a esperar a mañana, cuando lo que
  hay es una condición de salud que no cambia con el día.
- **«Lo bloqueó tu acudiente» sobre un producto con maní** invita a pedirle al acudiente que
  lo levante, y con una alergia de por medio esa conversación no puede empezar en la caja.

De ahí los tres cortes del orden:

1. **El estado del estudiante va primero** (`HU-50`). Con la tarjeta bloqueada da igual lo que
   lleve el carrito: ningún otro motivo describe lo que pasa.
2. **El alérgeno va antes que el producto bloqueado** (`HU-18` antes que `HU-60`). Un producto
   puede caer por las dos; cuando pasa, lo que hay que decir es la alergia.
3. **Las restricciones van antes que el saldo.** Son sobre el mundo; el saldo es sobre el
   estado de hoy.

El cupo va **después de las existencias y antes del saldo**: «de eso quedan dos» se resuelve
en el acto quitando el renglón, y «se acabó el cupo» no lo arregla ninguna recarga.

### [S2.2] El motivo es una etiqueta, no una frase

Cada rechazo lleva `motivo`, una etiqueta estable que llega al HTML del ticket como
`data-motivo`. Lo estrenó `TT-132` y lo reutilizan los cuatro que vinieron después.

**Las pruebas preguntan por la etiqueta, nunca por el texto.** Una prueba que busque «No
alcanza» se rompe en cuanto alguien mejora la redacción, en un PR que no tenía nada que ver.

**Una sola etiqueta para desactivado y de baja**, con el mensaje diciendo cuál: para la venta
son lo mismo —no se cobra y no hay nada que hacer en el mostrador—, y dos etiquetas
obligarían a toda pantalla futura a separar dos casos que se pintan igual.

---

## [S3] Lo que la venta NO puede hacer

- **No hay forma de forzarla.** Ningún argumento, ninguna variante del servicio, ningún
  permiso. `INV-4` dice que las restricciones no las desactiva la cafetería y el primer
  criterio de `HU-13` precisa que el cajero no dispone de **ninguna acción para omitirlas**;
  un aviso descartable sería exactamente esa acción. Hay pruebas que pasan `forzar=True` y
  exigen un `TypeError`: vigilan una ausencia.
- **No cobra «lo que sí se puede».** Un renglón rechazado tumba la venta entera. Cobrar el
  resto en silencio dejaría al estudiante creyendo que se llevó lo que pidió; el mensaje dice
  qué quitar, y quitarlo lo decide quien está en la caja.
- **No escribe nada al rechazar.** Ni saldo, ni existencias, ni venta. Y **el carrito se queda
  montado**: arreglar el motivo y volver a pulsar es todo lo que hace falta.
- **No consulta restricciones cuando no hay estudiante.** Una venta a cliente genérico
  (`DEC-1`, `HU-53`) no tiene a quién consultarle nada: descuenta inventario y no toca ninguna
  billetera.

---

## [S4] Las existencias, que no salen de ninguna historia

**Ninguna historia dice «rechaza la venta si no hay existencias».** Se aplica igualmente, y
conviene que quede escrito por qué:

- `DT-6` manda bloquear «los productos implicados». Un bloqueo que no protege ninguna lectura
  no protege nada.
- Sin ella, vender cien empanadas de las tres que hay deja el inventario en −97. `INV-3`
  seguiría cumpliéndose —la suma explica el número— pero lo que explicaría es un disparate.

Si el equipo prefiere permitir la venta sin existencias, esto se quita y se registra como
decisión. Lo que no se puede es dejarlo sin decidir.

> **La merma aplica la misma regla, por el mismo motivo** (`TT-138`, `HU-28`).
> `registrar_merma` rechaza la que dejaría el inventario en negativo, y también lee **dentro
> del bloqueo**. Tampoco sale de ninguna historia: los dos criterios de `HU-28` son sobre el
> motivo. Si algún día se decide permitir una de las dos, conviene mirar la otra — el
> argumento es el mismo y las dos deberían moverse juntas.

---

## [S5] Qué pasa al escribir

Tres cosas, en la misma transacción:

1. **La venta y sus líneas.** Cada línea **congela el precio y los nutrientes** que el
   producto declaraba en ese momento (`HU-22`, `DT-8`): editar el catálogo mañana no reescribe
   lo que se cobró hoy, que es lo que hace del historial de `HU-30` un historial y no una
   proyección del catálogo de hoy sobre el pasado.
2. **El libro de inventario**, por su único punto de asiento (`DT-24`). También en la venta
   genérica.
3. **El libro de la billetera**, solo si hay estudiante. Ahí vuelve a comprobarse `INVD-2`:
   es la red por si algún día alguien escribe por otro camino.

Ninguno de los dos libros tiene columna de total: el saldo y las existencias **son** la suma
de sus movimientos (`INV-2`, `INV-3`).

---

## [S6] Si vas a añadir la séptima comprobación

Lo que hay que preguntarse, en este orden:

1. **¿De qué historia sale?** Si no sale de ninguna, para: es alcance, y se registra antes de
   construirse. Pasó con `HU-60`.
2. **¿La regla ya existe en otro sitio?** `INVD-2` vive en `personas.services` y la venta la
   **llama**, no la copia. Una regla copiada es una regla que un día divergirá. El retiro de
   pedidos de `HU-25` llama a esa misma puerta, y por eso no tuvo que acordarse de nada.
3. **¿Dónde va en el orden?** Aplica la regla de `[S2.1]`: cuanto menos se arregle en el
   mostrador, más adelante va.
4. **¿Lee algo que pueda cambiar debajo?** Entonces va dentro del bloqueo, y hace falta una
   prueba que lo fije mirando el orden de las consultas.
5. **¿Su motivo se distingue de los seis?** Etiqueta nueva, y una prueba que compare el
   conjunto entero.

---

## [S7] La reserva valida por aquí, y lo que eso deja abierto

`HU-23` añadió un segundo camino que llega a estas seis comprobaciones: la reserva
anticipada del acudiente. **No las reimplementa** — `reservar` y `registrar_venta` llaman a
la misma función, `_bloquear_y_validar` (`TT-144`).

Que sea la misma no es higiene: `HU-23` **no menciona ninguna de las seis**. Con un flujo
propio, un acudiente no podría comprarle a su hijo en la caja algo con un alérgeno
bloqueado, pero sí reservárselo la noche anterior — y el control parental entero tendría una
puerta trasera. `ventas/tests_reserva.py` ejercita las seis sobre la reserva.

**Lo único que cambia es qué cuenta como disponible.** La venta del mostrador mira las
existencias; la reserva mira `existencias_sin_reservar`, que les resta lo apartado por
pedidos pendientes. Es consecuencia de `DT-33`: la reserva cobra pero no descuenta
inventario hasta la entrega, así que sin restar lo apartado dos reservas del último paquete
pasarían las dos.

> ### ✅ Hueco resuelto por `HU-25`, y las comprobaciones siguen siendo seis
>
> **La caja mira las existencias reales, así que puede vender unidades apartadas para una
> reserva ya pagada.** Eso no cambia, y es deliberado: cerrarlo aquí habría sido la séptima
> comprobación, y en una caja con fila el cajero leería «no hay existencias» de algo que
> tiene delante en la vitrina, porque está apartado para otro.
>
> Lo que se decidió es **qué hace la entrega cuando pasa**, que era la pregunta que este
> documento remitió a `HU-25`: la entrega **se registra igual** y el libro puede quedar en
> negativo (`DT-35`). El compromiso ya se adquirió y se cobró; rechazarla dejaría al
> estudiante sin lo suyo y con el dinero pagado, y el sistema no sabe devolver (`ALC-OUT-01`).
>
> El negativo no se esconde: es el descuadre que `HU-29` existe para auditar, y la pantalla
> del historial lo enseña con la venta que lo originó.
>
> **Y la caja no es la única vía.** `registrar_merma` valida contra las existencias reales,
> así que **también puede dar de baja unidades apartadas** — se dañó la bandeja con las
> empanadas de una reserva, y el libro baja igual. La consecuencia es la misma y la salida
> también: la entrega se registra, el libro queda en negativo y el descuadre se audita. No se
> cierra por lo mismo que en la caja: exigiría que la merma supiera de reservas, y ninguna
> historia lo pide. Se anotó al revisar el cierre del Sprint 4.

---

## [ANEXO A] De dónde salió cada comprobación

| Comprobación | Tarea | PR | Sprint |
|---|---|---|---|
| Saldo suficiente | `TT-80` | `PR-12` | 2 |
| Existencias | `TT-80` | `PR-12` | 2 |
| Producto bloqueado | `TT-131` | `PR-15` | 3 |
| Alérgeno bloqueado | `TT-113` | `PR-08` | 3 |
| Cupo del día | `TT-116` | `PR-09` | 3 |
| Estudiante que no opera | `TT-125` | `PR-13` | 3 |

El `ANEXO A` del `./sprint-3-backlog.md` avisó del riesgo acumulado: **tres PR seguidos
tocando el mismo servicio transaccional**. El orden sobrevivió a los tres, y cada uno dejó su
prueba. Lo que sí se rompió una vez fue otra cosa —autorizar después de escribir, en el
padrón—, y lo cazó una prueba de un PR anterior.
