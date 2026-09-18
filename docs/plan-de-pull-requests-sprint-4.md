# SmartFood — Plan de Pull Requests del Sprint 4

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-PR-SPRINT4 |
| plan anterior | `./plan-de-pull-requests-sprint-3.md` — cerrado, documento de archivo |
| titulo | Agrupación de las 18 tareas del Sprint 4 en Pull Requests, y estado de cada tarea |
| documentos_fuente | `./sprint-4-backlog.md` (`[S3]`, `[S4]`, `[S5]`, `ANEXO C`); `./convenciones-de-git.md` (`[S1]`); `./definicion-de-terminado.md`; `./despliegue.md`; `./decisiones-de-alcance.md` (`DEC-15`) |
| tipo_documento | Documento derivado de planificación. **No es un artefacto de Scrum** |
| sprint | 4 de 5 · semanas 12 – 13 · **Avance 2 · semana 14** (`EVA-4`) |
| tareas cubiertas | 18 de 18 (`TT-137` … `TT-154`) |
| pull requests | 7 (`PR-01` … `PR-07`) |
| idioma | es-CO |
| version | 1.1 |

### [S0.1] Qué es este documento y qué no es

`main` está protegida: nada entra por `push` directo (`[S1]` de `./convenciones-de-git.md`).
Este documento responde a una sola pregunta operativa: **¿hasta dónde desarrollo antes de
parar, abrir un PR y seguir?**

**No reordena ni modifica ninguna tarea.** El orden de `./sprint-4-backlog.md` es el orden
de construcción verificado en su `ANEXO C`, y aquí se respeta carácter por carácter. Lo
único que este documento añade son **cortes**.

> **Este es el único sitio donde vive el estado de las tareas.** El sprint backlog es el
> plan y no se toca; el tablero de `TT-152` es la vista de la Daily. Si hay discrepancia,
> manda este documento.

> **Hay un plan por sprint y se conservan todos.** Los de los Sprints 1 a 3 están en
> `./plan-de-pull-requests-sprint-1.md`, `-2` y `-3`, cerrados.

---

## [S1] La regla de corte

Todo PR es un **bloque contiguo** del orden del sprint backlog. Sin huecos, sin saltos,
sin adelantar tareas.

De ahí sale la única propiedad que importa, y es demostrable:

> El `ANEXO C` verifica que el orden de las 18 tareas es un orden topológico del grafo de
> dependencias: **ninguna tarea aparece antes de algo que la bloquea**. Si cada PR es un
> bloque contiguo de ese orden, entonces toda dependencia de cualquier tarea de `PR-k`
> está, o en `PR-k`, o en un PR anterior. **Nunca en uno posterior.**

Consecuencia práctica: **integrar los PR en orden numérico no puede romperse.**

Los cortes se eligieron con tres criterios, en este orden:

1. **Un PR cierra algo demostrable**, y este sprint desemboca en el Avance 2.
2. **Un PR se revisa de una sentada.** Entre 1 y 4 tareas. Ninguno pasa de 4.
3. **Un PR no mezcla asuntos.** El inventario no viaja con los pedidos anticipados.

---

## [S2] Cómo se marca una tarea como finalizada

1. Se cumplen los criterios de la Definición de Terminado que aplican al PR.
   **`DoD-4` volvió a aplicar con `PR-01`**, en su forma nueva: demostrar ejecutándolo,
   con la salida real del comando. Del `PR-02` en adelante se cumple como cualquier otro.
2. El PR se integra en `main` por revisión cruzada, nunca por `push` directo.
3. Se marca `☑` **en los dos documentos**: aquí y en `./sprint-4-backlog.md`.
4. Si el PR cierra una historia, se marca también en la tabla `[S4]` de
   `./backlog-historias-de-usuario.md`.

---

## [S3] Avance del Sprint 4

| | Tareas | Pull Requests |
|---|---|---|
| **Finalizadas** | **12** de 18 | **5** de 7 |
| Pendientes | 6 | 2 |

| Responsable | Finalizadas | Total |
|---|---|---|
| Pedro | 5 | 6 |
| Carlos | 4 | 5 |
| Alejandro | 3 | 4 |
| Naomi | 0 | 3 |

### [S3.1] Estado de los 7 Pull Requests

| PR | Tareas | Qué cierra | Estado |
|---|---|---|---|
| `PR-01` | `TT-137` | **Retira** el entorno desplegado → `DEC-15`, `DT-31`; restablece `DoD-4` | ☑ |
| `PR-02` | `TT-138`–`TT-140` | `HU-28` · `INV-8` | ☑ |
| `PR-03` | `TT-141`–`TT-142` | `HU-29` · `INV-3`, **`TST-4`** — cierra `ENT-05` | ☑ |
| `PR-04` | `TT-143`–`TT-146` | `HU-23` · `DT-32`, `DT-33` | ☑ |
| `PR-05` | `TT-147`–`TT-148` | `HU-24` · `DT-34` | ☑ |
| `PR-06` | `TT-149`–`TT-151` | `HU-25` | ☐ |
| `PR-07` | `TT-152`–`TT-154` | Gestión del sprint y Avance 2 | ☐ |

---

## [S4] Los 7 Pull Requests

### Habilitación — `PR-01`

#### `PR-01` — Retirada del entorno desplegado

| | |
|---|---|
| Título del PR | `docs(infra): retirar el entorno desplegado y restablecer DoD-4` |
| Rama | `docs/TT-137-retirar-el-entorno-desplegado` |
| Responsable | Pedro |
| Historia | ninguna — habilitación |
| Invariantes | ninguna; **recorta `ENT-01`** (`DEC-15`) |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-137` | Restaurar el entorno desplegado y levantar la suspensión de `DoD-4` | Pedro | ☑ |

**Se cerró con la decisión contraria a la que el plan preveía.** La consulta con la
docente —condición de caducidad escrita en la propia caja de `DoD-4`— se resolvió: la
asignatura **no exige** entorno desplegado. Restaurarlo habría costado dinero para
satisfacer un requisito que no existe, así que se retira.

**Qué habilita y cómo se comprueba:** desbloquea `DoD-4`, que llevaba suspendido desde el
2026-08-30 y ningún trabajo del equipo podía satisfacer. `DoD-1` exige declararlo porque
este PR no cierra ninguna historia. Se comprueba con la suite completa y `check` sobre el
repositorio ya sin `railway.json` ni el bloque de `config/settings.py` que leía la
variable de dominio del proveedor: si algo dependía de él, falla ahí.

> **Lo que el plan decía y no era cierto.** Esta ficha presentaba el obstáculo como el
> bloqueo horario de 8:00 a 20:00 del plan gratuito. `[S1]` de `./despliegue.md` registraba
> desde agosto que el entorno no se sostenía por otras dos causas —la base gestionada se
> duerme y desactivarlo está prohibido en ese plan, y `/app/staticfiles/` no existe en
> ejecución— y que la única salida era pagar. La ventana horaria era la tercera
> restricción. **El dato estaba escrito y la planeación no lo leyó**; queda anotado porque
> es el tipo de error que se repite.

**Qué cambia para los seis PR siguientes.** `DoD-4` vuelve a aplicar, en su forma nueva:
demostrar ejecutándolo, con la salida real del comando. Es lo que los PR venían declarando
durante la suspensión, así que en la práctica no cambia nada de cómo se trabaja.

**Lo que queda fuera del repositorio:** eliminar el proyecto en la consola del proveedor.
Es una acción manual, no la hace este PR, y está anotada en `[S0.1]` de `./despliegue.md`.

---

### Inventario trazable — `PR-02` … `PR-03`

#### `PR-02` — `HU-28` Registro de merma con motivo obligatorio

| | |
|---|---|
| Título del PR | `feat(inventario): registrar la merma con su motivo` |
| Rama | `feat/TT-138-registro-de-merma` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-28` |
| Invariantes | **`INV-8`** |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-138` | Servicio de registro de merma, sobre el primitivo `asentar` que ya existe | Pedro | ☑ |
| `TT-139` | Registro de merma desde la interfaz administrativa | Carlos | ☑ |
| `TT-140` | Caso de prueba: la merma sin motivo la rechaza la **base de datos** | Alejandro | ☑ |

> **Ojo: esto es menos trabajo del que parece.** `TT-67` del Sprint 2 ya dejó el tipo
> `MERMA`, la `CheckConstraint` de motivo obligatorio y el primitivo `asentar`, que además
> valida que una merma traiga motivo. Lo que falta es el servicio de cara al usuario
> —equivalente a `ingresar_mercancia`—, la pantalla y la prueba. **No rehagas el modelo.**

`TT-140` comprueba `INV-8` **saltándose el formulario**: si la prueba pasa llamando al ORM
directamente, la invariante está donde `DT-5` dice que debe estar.

**Dos cosas se decidieron al construirlo, y ninguna estaba en el plan:**

1. **La restricción de `INV-8` tenía un agujero y se endureció.** `~Q(motivo="")` rechazaba
   la cadena vacía y dejaba pasar «   »: tres espacios no son un motivo, pero tampoco son la
   cadena vacía. Pasa a ser `Q(motivo__regex=r"\S")`. El servicio nunca escribía eso —`asentar`
   hace `strip()`—, y esa es justamente la razón de subirlo a la base: una restricción que solo
   rechaza lo que el servicio ya rechazaba no protege ningún camino nuevo, y `DT-5` la pone
   para los caminos que todavía no existen.
2. **La merma no deja existencias negativas.** No sale de `HU-28` —sus dos criterios son sobre
   el motivo— y se aplica por el mismo razonamiento con el que la venta rechaza por existencias
   insuficientes: `[S4]` de `./reglas-de-la-venta.md`, que registró aquella como regla sin
   historia. Mermar diez de las tres que hay deja el inventario en −7; `INV-3` seguiría
   cumpliéndose y lo que explicaría sería un disparate. Se lee **dentro del bloqueo** (`DT-6`),
   como en la venta.

**La merma tiene entrada propia en el admin**, un proxy de `MovimientoInventario` (`Merma`).
No es una segunda pantalla fuera del admin —`DT-27` sigue siendo la única excepción—: es el
admin con dos entradas. El motivo es obligatorio en la merma y opcional en el ingreso, y un
único formulario tendría que exigirlo **solo a veces**, según lo que el usuario eligiera arriba.
Sus permisos son `add` y `view`; `change` y `delete` **no existen** (`default_permissions`), que
es más fuerte que no concederlos.

---

#### `PR-03` — `HU-29` Existencias explicables · **`TST-4`**

| | |
|---|---|
| Título del PR | `feat(inventario): explicar las existencias desde su historial` |
| Rama | `feat/TT-141-historial-de-existencias` |
| Responsables | Carlos y Alejandro |
| Historia | `HU-29` |
| Invariantes | `INV-3` · escenario crítico **`TST-4`** |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-141` | Vista del historial de movimientos de un producto, con tipo y motivo | Carlos | ☑ |
| `TT-142` | Caso de prueba `TST-4`: existencias = suma del historial, tras ingreso, venta y merma | Alejandro | ☑ |

**No lleva tarea de backend.** `existencias_de` e `historial_de` existen desde `TT-67`, e
`INV-3` se cumple por construcción porque no hay columna de existencias (`DT-5`). Lo que
falta es que un humano pueda **ver** la explicación, y la prueba que la ejercita.

> **`TST-4` es el último de los cuatro escenarios críticos de `ENT-05`.** Con `TST-3`
> (Sprint 2) y `TST-1` y `TST-2` (Sprint 3), al integrar este PR **el plan de pruebas queda
> completo**. Merece decirse en la Sprint Review.

`TT-142` depende de `PR-02` aunque sean historias distintas: `TST-4` exige ejercitar el
historial **con una merma**. Se ejercita con los tres tipos y los tres por su camino real
—`ingresar_mercancia`, `registrar_venta` y `registrar_merma`—, no fabricando asientos: lo que
se compara es lo que el sistema escribe cuando funciona.

**La pantalla es del admin y cuelga del producto**, no del libro: `/admin/catalogo/producto/
<id>/historial/`, y **la cifra de existencias del listado es el enlace que lleva a ella**. Es
el gesto que la historia pide — quien ve un número que no cuadra pincha el número, no busca
en un menú otra pantalla que quizá hable del mismo producto. No es una segunda excepción a
`DT-27`: es el admin, con una vista propia registrada en `get_urls()`, como ya hacen la baja
y la reasignación en `personas`.

**Lo que esa pantalla añade sobre el listado de movimientos que ya existía** (`TT-69`) es la
columna de **existencias tras cada movimiento**, y es lo que convierte «ver los asientos» en
«auditar un descuadre», que es lo que `HU-29` pide literalmente. Se calcula en Python al
pintar; el total de arriba es un `SUM` de la base. **Salen de caminos distintos a propósito**:
si divergieran, el último renglón no coincidiría con el total y se vería sin buscarlo. Es
`TST-4` puesto donde lo ve un humano, y `TT-142` el mismo escenario donde lo ve la suite.
**No se guarda ningún acumulado**: se calcula y se tira, porque un acumulado almacenado sería
la segunda fuente de verdad que `DT-5` evita.

---

### Pedidos anticipados — `PR-04` … `PR-06`

#### `PR-04` — `HU-23` Reserva y pago anticipado

| | |
|---|---|
| Título del PR | `feat(ventas): reservar y pagar por adelantado el consumo` |
| Rama | `feat/TT-143-reserva-anticipada` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-23` |
| Invariantes | hereda `INV-1`, `INV-2`, `INV-5`, `INVD-2` de la transacción de venta |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-143` | Modelo de pedido anticipado, con su estado y su vínculo a la venta | Pedro | ☑ |
| `TT-144` | Servicio de reserva que cobra **al reservar**, dentro de la transacción | Pedro | ☑ |
| `TT-145` | Pantalla de reserva en la interfaz del acudiente | Carlos | ☑ |
| `TT-146` | Caso de prueba: la reserva descuenta saldo al reservarse, no al entregarse | Alejandro | ☑ |

> 🔴 **Una reserva es una venta anticipada, no un apartado.** `TT-144` debe pasar por la
> **misma transacción con bloqueo** que `registrar_venta`. Si se implementa como un flujo
> propio, las cuatro reglas de rechazo que construyeron los Sprints 2 y 3 —saldo, límite
> diario, alérgeno y estudiante desactivado— **no se aplicarían a las reservas**, y quedaría
> una puerta trasera para saltarse el control parental entero.
>
> Es el riesgo de diseño más serio del sprint y no se ve mirando la historia: sus criterios
> no mencionan ninguna de las cuatro reglas.

Única historia del sprint que construye desde cero: no hay nada de pedidos en el código.

**El aviso se cumplió, y así se sostiene.** `reservar` y `registrar_venta` llaman a la misma
función, `_bloquear_y_validar`, extraída de la segunda al construir la primera. Las seis
comprobaciones viven ahí y en ningún otro sitio; `ventas/tests_reserva.py` las ejercita las
seis sobre la reserva, y una prueba estructural comprueba además que **ninguno de los dos
servicios las tiene escritas aparte** — una copia es como uno de los dos caminos se queda sin
el arreglo de la próxima.

**Dos cosas se decidieron al construirlo, y las dos están registradas:**

1. **`DT-32`: una reserva es una `Venta` con `origen = reserva`**, no otra tabla. Cobrar al
   reservar obliga a crear la venta entonces, porque un movimiento de billetera de tipo
   `venta` tiene que señalar una (`TT-78`). `cajero` pasa a opcional y una `CheckConstraint`
   le da sentido: la del mostrador lo exige, la reserva exige que no lo haya y que sí haya
   estudiante. `PedidoAnticipado` guarda **solo** el estado de la entrega.
2. **`DT-33`: la reserva cobra saldo y no descuenta inventario**; eso lo hace la entrega.
   Es una decisión del equipo entre dos lecturas del plan que se contradecían — `PR-04` pedía
   pasar por la misma transacción que el cobro, que descuenta las dos cosas, y `PR-06` decía
   que la entrega descuenta existencias.

> ⚠ **`DT-33` deja un hueco, y le toca a `PR-06` cerrarlo.** Como las unidades reservadas
> siguen en el libro hasta la entrega, **la caja puede vender lo que está apartado para una
> reserva ya pagada**, y el estudiante llegaría a recoger algo que no está.
>
> La reserva se protege a sí misma —valida contra `existencias_sin_reservar`, así que dos
> reservas del último paquete no pasan las dos—, pero la venta del mostrador sigue mirando
> las existencias reales. Cerrarlo ahí sería la **séptima comprobación** de la venta, y
> ninguna historia la pide: quien tiene el problema delante es `HU-25`, que decide qué hace
> la entrega cuando no hay lo suyo. Está anotado en `[S7]` de `./reglas-de-la-venta.md`.

---

#### `PR-05` — `HU-24` Consulta de reservas pendientes

| | |
|---|---|
| Título del PR | `feat(ventas): consultar las reservas pendientes desde la cafetería` |
| Rama | `feat/TT-147-reservas-pendientes` |
| Responsables | Pedro y Carlos |
| Historia | `HU-24` |
| Invariantes | ninguna |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-147` | Selector de reservas pendientes | Pedro | ☑ |
| `TT-148` | Consulta de reservas pendientes desde la cafetería | Carlos | ☑ |

**Una pantalla y no dos, y eso es `DT-34`.** `HU-24` nombra dos actores que **no comparten
interfaz**: el cajero no tiene `is_staff` y la administración recibe `403` en el punto de
venta. Dejarla solo en el admin deja fuera a quien la prepara; dejarla solo en `INT-2` deja
fuera a la administración; construir las dos es mantener dos pantallas del mismo dato. Se
resuelve con una sola, en el armazón de la aplicación, con la entrada en los dos menús.

Es la **segunda excepción a `DT-27`** y va registrada, que es lo que aquella decisión pidió
para la siguiente. Una tercera tendría que explicar por qué no es ya un patrón.

**La cola va del más antiguo al más reciente**, al revés que todos los historiales del
proyecto. No es un historial: es una cola de trabajo, y lo que el personal necesita saber es
qué lleva más tiempo esperando.

**No lleva el importe.** Para preparar un pedido hace falta quién y qué, no cuánto costó — ya
está pagado y nadie va a cobrarlo otra vez.

---

#### `PR-06` — `HU-25` Registro de la entrega

| | |
|---|---|
| Título del PR | `feat(pos): registrar la entrega de un pedido anticipado` |
| Rama | `feat/TT-149-entrega-de-pedido` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-25` |
| Invariantes | `INV-2`, `INV-3` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-149` | Servicio de entrega que **no vuelve a descontar saldo** ni admite entrega doble | Pedro | ☐ |
| `TT-150` | Registro de la entrega en el punto de venta | Carlos | ☐ |
| `TT-151` | Caso de prueba: entregar no descuenta saldo, y no se entrega dos veces | Alejandro | ☐ |

> ⚠ **El error a evitar es cobrar dos veces.** El pedido ya se pagó al reservarse (`DT-33`):
> la entrega cambia su estado y descuenta existencias, y **no vuelve a tocar el saldo**. Si reutiliza `registrar_venta` sin
> más, el estudiante paga dos veces e **`INV-2` sigue cuadrando** —el historial es
> consistente— pero el sistema está mal. Es el único fallo del sprint que no detecta
> ninguna invariante: solo lo detecta `TT-151`.
>
> **Y hereda un hueco de `PR-04`.** `DT-33` dejó que la caja pueda vender unidades apartadas
> para una reserva pagada. `TT-149` tiene que decidir qué hace la entrega cuando llega el
> estudiante y no hay lo suyo — está en `[S7]` de `./reglas-de-la-venta.md`, con las dos
> salidas posibles.

---

### Gestión — `PR-07`

#### `PR-07` — Gestión del sprint y Avance 2

| | |
|---|---|
| Título del PR | `docs(gestion): cerrar el Sprint 4 y preparar el Avance 2` |
| Rama | `docs/TT-152-gestion-del-sprint-4` |
| Responsable | Naomi |
| Historia | ninguna — gestión |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-152` | Tablero Kanban del Sprint 4 | Naomi | ☐ |
| `TT-153` | Registro de riesgos del Sprint 4 | Naomi | ☐ |
| `TT-154` | Preparación de la Sprint Review, la Retrospective y el **Avance 2** | Naomi | ☐ |

---

## [S5] Qué se puede solapar

| PR | Puede ir en paralelo con | Porque |
|---|---|---|
| `PR-01` (entorno, Pedro) | cualquiera | `TT-137` no depende de nada del sprint |
| `PR-02` (inventario) | `PR-04` (reservas) | Dos frentes que solo se encuentran en `PR-06` |
| `PR-03` (historial, Carlos) | `PR-02` salvo `TT-142` | `TT-141` es una vista sobre selectores que ya existen |
| `PR-07` (gestión, Naomi) | cualquiera | `TT-152`–`TT-154` no dependen de nada |

**Siete raíces** sin dependencia dentro del sprint: `TT-137`, `TT-138`, `TT-141`, `TT-143`
y las tres de gestión.

**Regla al solapar:** ramifica siempre desde `main`, nunca desde la rama del otro.

---

## [S6] Advertencias sobre este plan

1. **7 PR y 18 tareas: la mitad que en los Sprints 2 y 3.** Es el sprint más ligero de los
   cinco y **no hay retraso que absorber**, porque los tres anteriores cerraron completos.
   La holgura es real. El `ANEXO A` del sprint backlog propone en qué gastarla, en orden:
   entorno desplegado, adelantar Sprint 5, o pulir lo que se enseña en el Avance 2. **Lo que
   no conviene es no decidirlo**, porque entonces se gasta sola. El primero de los tres ya
   no consume nada: `PR-01` lo resolvió retirando el entorno, no restaurándolo.
2. **`PR-04` es el de mayor riesgo de diseño.** Una reserva tiene que pasar por la
   transacción de venta o el control parental queda con una puerta trasera. La historia no
   lo dice: hay que saberlo.
3. **`PR-06` esconde el único fallo que ninguna invariante detecta.** Cobrar dos veces deja
   la base consistente. Solo lo caza `TT-151`.
4. **Al integrar `PR-03`, el plan de pruebas de `ENT-05` queda completo.** Los cuatro
   escenarios críticos cerrados. Es un hito del proyecto, no solo de este sprint.
5. **Tres de las cinco historias son `Should`.** `HU-23`, `HU-24` y `HU-25`. Si algo se
   cae, se caen ellas en ese orden inverso. `HU-28` y `HU-29` no pueden caerse: `HU-29`
   cierra `TST-4`.
6. **Este plan no reordena nada.** Si alguien propone mover una tarea de PR, hay que
   comprobar el `ANEXO C` del sprint backlog antes.
