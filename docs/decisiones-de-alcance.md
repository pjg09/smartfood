# SmartFood — Decisiones de alcance posteriores al anteproyecto

## [S0] Bloque de control del documento

### [S0.1] Metadatos

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-DEC |
| titulo | Decisiones de alcance posteriores al anteproyecto |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./smartfood.md`; `./backlog-historias-de-usuario.md` (`ANEXO B`, vacíos `VAC-1` … `VAC-6`) |
| tipo_documento | Registro de decisiones del equipo |
| procedencia | Copia de trabajo. El maestro estaba en el corpus documental de la asignatura (repositorio `tic1`, local). **A partir del traslado, este fichero es el vigente**: no editar la copia del corpus. |
| fecha_decisiones | 2026-08-28 (`DEC-1` … `DEC-7`); 2026-08-29 (`DEC-8`) |
| decidido_por | Equipo SmartFood |
| decisiones | 10 (`DEC-1` … `DEC-10`) |
| invariantes_nuevas | 6 (`INVD-1` … `INVD-6`) |
| idioma | es-CO |
| version | 1.2 |

### [S0.2] Instrucciones de lectura para el agente

1. Este documento **no es una reexpresión de un original** y no lleva texto verbatim. Registra decisiones tomadas por el equipo **después** de escrito el anteproyecto.
2. **Su contenido no está en `./smartfood.md` y no puede añadirse allí**: ese fichero es la reexpresión del DOCX original y su regla 1 prohíbe alterarlo. Ese es el motivo de que este documento exista por separado.
3. Cada decisión cierra un vacío `[VAC-n]` del `ANEXO B` de `./backlog-historias-de-usuario.md`, o responde a una pregunta abierta que ese análisis destapó.
4. Los identificadores `[DEC-n]` e `[INVD-n]` son estables y citables. `INVD-` son **invariantes derivadas**: reglas del sistema que nacen de estas decisiones, no del anteproyecto. Las invariantes `INV-1..9` del anteproyecto siguen vigentes y no se tocan.
5. Cada decisión distingue lo **decidido** (normativo) de su **justificación** (argumentación del equipo). La justificación no es fuente de requisitos.
6. **Estado frente al anteproyecto:** ninguna de estas decisiones está incorporada todavía a `./smartfood.md`. Este documento es la lista de lo que hay que integrar en la próxima versión del anteproyecto.

### [S0.3] Mapa de secciones

| ID | Sección | Contenido |
|---|---|---|
| S1 | Decisiones | `DEC-1` … `DEC-7` |
| S2 | Invariantes derivadas | `INVD-1` … `INVD-5` |
| S3 | Efecto sobre el alcance | Qué cambia respecto de `[S9]` del anteproyecto |
| ANEXO A | Trazabilidad decisión → vacío → historias | Cierre de `VAC-1` … `VAC-6` |
| ANEXO B | Puntos que siguen abiertos | Lo que estas decisiones no resuelven |
| ANEXO C | Nota de procedencia | Cómo se tomaron |

---

## [S1] Decisiones

### `[DEC-1]` Venta a cliente genérico en el punto de venta

*Cierra `VAC-1`.*

**Decidido:**

- El punto de venta puede emitir una venta a un **cliente genérico**, sin identificación y sin ningún vínculo estudiantil. El cliente no está registrado en el sistema.
- Los medios de pago de una venta genérica son **efectivo** y **transferencia**. La transferencia va directamente de la app bancaria del cliente a la cuenta bancaria de la cafetería: **no pasa por el sistema y no es una recarga**. El sistema únicamente deja constancia de que la venta se pagó así.
- Una venta genérica **descuenta inventario** como cualquier otra (`ALC-IN-17`) y **no aplica restricciones alimentarias**, porque no hay acudiente que las haya configurado.
- Toda venta —de estudiante o genérica— **registra su medio de pago**: `billetera`, `efectivo` o `transferencia`.

**Justificación del equipo:** el problema del efectivo que ataca el proyecto es **específico de los niños**, no del efectivo en sí. Un menor no maneja bien el dinero: además de comprar comida poco saludable, puede guardarlo y gastarlo fuera del colegio, donde el riesgo deja de ser alimentario. Para un docente, un administrativo o un visitante ese riesgo no existe, así que el efectivo es tolerable fuera del flujo de estudiantes.

Esto es **coherente con el anteproyecto y no una ampliación de su objetivo**: `OBJ-GEN` acota la sustitución del efectivo a «una cuenta digital **por estudiante**», y `[S5]` ya exigía registrar las ventas de `USR-6`.

> **Advertencia de sustentación:** la parte de la justificación referida al gasto fuera del colegio **no tiene respaldo bibliográfico en el anteproyecto**. `[S2]` sí cita a Chaux & Velásquez (2008) para el robo de efectivo (`EV-03`). Si este argumento se usa en la sustentación, necesita una fuente o debe presentarse explícitamente como supuesto del equipo.

### `[DEC-2]` Las cuentas de personal las crea y administra la institución educativa

*Cierra `VAC-2`.*

**Decidido:**

- **No hay autorregistro para ninguna cuenta**, tampoco para cajero ni administrador de cafetería. Se extiende a todos los roles lo que `ALC-IN-05` establecía para acudientes.
- Las cuentas de **cajero** (`USR-3`) y **administrador de cafetería** (`USR-4`) las da de alta la **institución educativa** (`USR-5`).
- La institución puede además **desactivar y reactivar** esas cuentas. Una cuenta desactivada no puede iniciar sesión ni operar.

**Justificación del equipo:** sin gestión posterior, una cuenta creada no podría cerrarse nunca; cuando un cajero deja de trabajar en la cafetería su acceso debe poder revocarse. La institución es quien la asume porque, conforme a la Ley 1581 de 2012 y a lo argumentado en `[S11]`, es la responsable del tratamiento de los datos de los menores y por tanto de quién accede a ellos.

### `[DEC-3]` Todo acceso se establece por invitación por correo

*Cierra `VAC-3`.*

**Decidido:**

- La cuenta de la **institución educativa** se crea en el **seed** del sistema (carga inicial técnica). El seed dispara una invitación por correo con la que la institución define su propia contraseña.
- **Cajero y administrador** reciben igualmente una invitación por correo cuando la institución da de alta su cuenta (`DEC-2`), y con ella definen su contraseña.
- El **acudiente** ya seguía este mecanismo (`ALC-IN-03`).
- En consecuencia: **ninguna contraseña del sistema es conocida por quien crea la cuenta.**

**Justificación del equipo:** unifica el mecanismo de acceso para los cuatro roles y evita el reparto de contraseñas iniciales, que es el punto donde en la práctica se filtran las credenciales.

### `[DEC-4]` Código de tarjeta asignado en la carga y administrable por la institución

*Cierra `VAC-4`.*

**Decidido:**

- Al cargar un estudiante, el sistema le **asigna automáticamente un código de tarjeta**, generado de forma aleatoria y no secuencial (`ALC-IN-12`, `INV-7`), listo para imprimirse como código de barras.
- La institución educativa dispone de una **vista de administración de estudiantes** donde puede: matricular un estudiante individual, modificar sus campos, **consultar el código de tarjeta vigente** para producir la tarjeta correspondiente, y **reasignar el código** ante cualquier situación.
- **Reasignar el código invalida el anterior de inmediato.** Un código reemplazado no vuelve a ser válido nunca.

**Justificación del equipo:** la carga masiva (`ALC-IN-01`) cubre el inicio del año, pero un colegio matricula estudiantes durante todo el periodo y corrige datos. La reasignación es el mecanismo de recuperación cuando una tarjeta se pierde, se deteriora o se sospecha que fue copiada.

### `[DEC-5]` Desactivación asimétrica del estudiante

*Cierra `VAC-5`.*

**Decidido:**

- La **institución educativa** puede desactivar y **reactivar** a un estudiante cuando quiera.
- El **acudiente** puede desactivar a su estudiante cuando quiera, pero **no puede reactivarlo**: debe comunicarse con la institución para que ella lo reactive.
- **La reactivación es exclusiva de la institución**, con independencia de quién haya desactivado.
- Un estudiante desactivado **no puede comprar** ni retirar pedidos anticipados. **Sí puede recibir recargas**, por ser inocuo.

**Justificación del equipo:** las dos vías cubren tiempos distintos. Si un estudiante pierde la tarjeta en mitad de la jornada, el acudiente puede no enterarse hasta la tarde, y la institución necesita poder bloquear de inmediato. Si es el hijo quien avisa a su padre, el padre necesita poder bloquear sin depender del horario de la secretaría. La reactivación se reserva a la institución para que el desbloqueo pase siempre por una verificación presencial: es lo que impide que quien encontró la tarjeta consiga que se reactive.

### `[DEC-6]` Cierre de caja diario, sin apertura de turno

*Cierra `VAC-6`.*

**Decidido:**

- Al cerrar la jornada, el sistema muestra al cajero el **total de ventas en efectivo del día**, calculado a partir de las ventas registradas.
- El cajero registra el **efectivo contado** y la **base** que dejó para dar cambio. El sistema calcula y registra la **diferencia**.
- Si la diferencia es distinta de cero, **el motivo es obligatorio**, con el mismo criterio que `ALC-IN-18` aplica al inventario.
- Las ventas por **transferencia no entran en el cuadre de efectivo**: el dinero nunca pasó por la caja.
- El cierre queda registrado y alimenta el reporte de auditoría de `ALC-IN-22`.
- **No hay apertura formal de turno.** El cuadre es diario y no exige declarar una base al abrir.

**Justificación del equipo:** es la versión mínima que cumple lo que `[S5]` ya prometía —registrar las ventas de `USR-6` «para que el cierre de caja y los reportes diarios reflejen con precisión la actividad comercial real»— sin construir un módulo de turnos que no incide en el problema identificado.

Tiene además valor argumental: `PA-7` describe que hoy la cafetería cuadra el efectivo «comparando el efectivo recaudado contra **su estimación** de lo vendido». Con el sistema, el cuadre se hace contra **ventas registradas**. Es una ruptura del proceso actual, no un añadido administrativo.

### `[DEC-7]` Baja lógica del estudiante retirado, con saldo congelado

*Responde a una pregunta abierta destapada por `DEC-4`; no cierra ningún `VAC`.*

**Decidido:**

- La institución puede dar de **baja** a un estudiante que se retira del colegio, desde la vista de administración de estudiantes (`DEC-4`).
- La baja es **lógica**: el historial de consumo y el de movimientos se conservan íntegros para auditoría.
- El **saldo remanente queda congelado y sigue siendo consultable**. No se puede comprar ni recargar sobre él.
- **La devolución del dinero queda fuera del sistema**, en coherencia con `ALC-OUT-01` y `ALC-OUT-02`: el prototipo no maneja dinero real.
- La baja es un estado **distinto** de la desactivación de `DEC-5`: «se retiró del colegio» no es lo mismo que «perdió la tarjeta».

**Justificación del equipo:** borrar al estudiante destruiría el historial que sostiene `INV-2` y la trazabilidad que es el objeto del proyecto. Congelar el saldo en lugar de anularlo mantiene el registro de que ese dinero existió, que es lo que permitiría auditarlo.

### `[DEC-8]` Fotografía del estudiante e imagen del producto

*No cierra ningún `VAC`. Decisión posterior, tomada al definir el almacenamiento del prototipo.*

**Decidido:**

- Cada estudiante puede tener una **fotografía** asociada, cargada y actualizada por la institución educativa desde su vista de administración (`DEC-4`).
- La fotografía **se muestra al cajero** al identificar al estudiante en el punto de venta, junto al saldo, el consumo del día y las restricciones (`FUN-4`).
- Cada producto del catálogo puede tener una **imagen**, gestionada por la administración de la cafetería.
- **En el prototipo, las fotografías de estudiantes son avatares generados**, no imágenes de personas reales, conforme a `ALC-OUT-07`.
- Ni la fotografía ni la imagen son obligatorias: su ausencia no impide ninguna operación.

**Justificación del equipo:** la fotografía es un **control preventivo de suplantación**, y cubre un hueco que `DEC-5` deja abierto.

`FUN-4` reconoce que el código de la tarjeta «opera como una credencial de acceso al saldo». `DEC-5` permite desactivar al estudiante cuando la tarjeta se pierde, pero es un control **reactivo**: solo funciona desde que alguien se entera de la pérdida. Entre que un niño pierde la tarjeta y que lo reporta pueden pasar horas, y en ese intervalo quien la encontró puede gastar el saldo. La fotografía en la pantalla de cobro cierra ese intervalo: el cajero ve a quién pertenece la tarjeta que le están presentando.

La imagen del producto es de otra naturaleza —no hay argumento de seguridad— y se justifica por la velocidad del punto de venta: `INT-2` debe atender toda la demanda en una ventana de veinte a treinta minutos, y reconocer un producto por su imagen es más rápido que leerlo en una lista.

> **Advertencia legal.** Son fotografías de menores de 5 a 17 años, el dato más sensible que este sistema tocaría. `ALC-OUT-08` declara que el tratamiento de datos personales de menores exige la autorización de sus titulares conforme a la Ley 1581 de 2012, y esa fue la razón para no desplegar en un colegio real (`ALC-OUT-06`). En el prototipo el riesgo se evita por `INVD-6`. **En una implementación real, esta funcionalidad exigiría autorización expresa de cada acudiente**, y así debe declararse en el informe final (`ENT-06`).

---

### `[DEC-9]` La carga masiva genera las invitaciones pero no las entrega

*No cierra ningún `VAC`. Decisión posterior, tomada al configurar el envío de correo del prototipo (`TT-06`).*

**Decidido:**

- La carga masiva (`HU-01`) **genera la invitación de cada acudiente cargado** —su token de un solo uso y con caducidad (`TT-18`)— exactamente igual que si fuera a enviarse. El mecanismo no se simula ni se salta.
- **El correo no se entrega** para los acudientes que entran por carga masiva.
- La entrega real de correo se demuestra con las altas **de una en una**: el seed de la institución (`HU-39`) y el alta de personal de la cafetería (`HU-41`).
- La invitación generada por la carga **sigue siendo utilizable**: `HU-03` se demuestra de extremo a extremo tomando el enlace de un acudiente cargado y definiendo la contraseña con él.
- La decisión afecta **solo al prototipo**. En una implementación real la entrega es obligatoria y sin ella `HU-03` no tendría sentido.

**Justificación del equipo:** los datos del prototipo son ficticios por obligación legal (`ALC-OUT-07`, `ALC-OUT-08`), y eso incluye las direcciones de correo de los acudientes. Esas direcciones **no corresponden a ningún buzón**. Enviarles correo no es difícil: es que no hay a quién entregarlo.

Y no es inocuo. Cada envío a una dirección inexistente produce un rebote, y una tasa de rebote alta degrada la reputación del remitente hasta que el proveedor suspende la cuenta. Una carga de prueba de doscientos acudientes ficticios podría dejar al equipo sin poder enviar **ningún** correo, incluidos los de `HU-39` y `HU-41`, que sí hacen falta para la demostración. La restricción protege la propia capacidad de demostrar el sistema.

El proveedor de correo del prototipo, en plan gratuito y sin dominio verificado, solo entrega a la dirección del titular de la cuenta, así que el envío masivo tampoco sería observable aunque se intentara.

`ALC-OUT-06` excluye el despliegue en una institución real, que es el único escenario en el que esas direcciones serían válidas. No existe, dentro del alcance, el caso que la entrega masiva serviría.

**Efecto sobre `HU-03`:** cambia su segundo criterio de aceptación, de «se envía una invitación a cada acudiente cargado» a «se **genera** una invitación por cada acudiente cargado». Los otros dos criterios no cambian: la generación sigue siendo automática tras la carga y el acudiente sigue definiendo su propia contraseña con esa invitación. La historia conserva su valor: lo que se retira es la entrega, no el mecanismo.

> **Advertencia.** Esta es la única decisión de este documento que **recorta** un criterio de aceptación ya escrito en lugar de añadir alcance. Se registra aquí precisamente por eso: sin identificador, la divergencia entre lo que `HU-03` pide y lo que el prototipo hace quedaría solo en una conversación, y en la Sprint Review la historia no se podría dar por cumplida. Debe declararse como limitación identificada en el informe final (`ENT-06`).

---

### `[DEC-10]` La cuenta institucional del prototipo se siembra con contraseña, sin invitación

*No cierra ningún `VAC`. Decisión posterior, tomada al sembrar el entorno desplegado.*

**Decidido:**

- La cuenta de la institución educativa se puede sembrar con una **contraseña conocida**, y en ese caso **no se envía invitación por correo**.
- Es una **opción explícita y con nombre** del comando de seed, no su comportamiento por defecto. Sin ella, el seed hace lo que `HU-39` describe: crea la cuenta sin contraseña utilizable y dispara la invitación.
- **Se limita a la cuenta institucional.** Las cuentas de acudiente (`HU-03`) y de personal (`HU-41`) se activan por invitación, sin excepción: ahí `INVD-1` sigue entero y quien crea la cuenta no conoce la clave.
- La contraseña **no está escrita en el código**: el comando genera una aleatoria y la muestra una sola vez, o acepta la que se le pase.

**Justificación del equipo:** la dirección de la cuenta institucional del prototipo no es de nadie. No hay ninguna persona que vaya a abrir esa invitación, así que el mecanismo de `HU-39` —recibir el correo y definir la contraseña— no tiene quien lo ejecute en el uso diario.

Y mandarla tiene coste. `DEC-9` ya razonó que un envío a una dirección inexistente produce un rebote, y que una tasa de rebote alta degrada la reputación del remitente hasta que el proveedor suspende la cuenta. Esa cuenta de correo hace falta intacta para lo único que sí se va a demostrar por correo: la activación de un acudiente. Sembrar la institución por invitación gastaría reputación en un correo que nadie va a leer, poniendo en riesgo el que sí importa.

**Efecto sobre `HU-39`:** ninguno en el texto. Sus cuatro criterios siguen siendo ciertos y demostrables, porque el comportamiento por defecto del seed no cambia. La demostración se hace dirigiendo la invitación a un buzón real:

```
manage.py sembrar --email-institucion <buzón real>
```

Lo que esta decisión añade es un segundo camino, para el uso diario, que **no** es el que `HU-39` describe. Por eso se registra: sin identificador, alguien que abriera el entorno desplegado vería una cuenta institucional con contraseña y concluiría que `INVD-1` no se cumple.

> **Advertencia.** `INVD-1` sigue vigente para todas las demás cuentas y no se relaja. Si esta excepción se extiende alguna vez a las cuentas de personal o de acudiente, deja de ser una excepción acotada y `HU-41` y `HU-03` dejan de cumplirse: su valor es precisamente que quien crea la cuenta no llega a conocer la clave.

---

## [S2] Invariantes derivadas

Reglas que nacen de estas decisiones. Se suman a `INV-1..9` del anteproyecto, que siguen vigentes sin cambios.

| ID | Invariante | Origen |
|---|---|---|
| `INVD-1` | Ninguna cuenta del sistema —acudiente, cajero, administrador o institución— se crea por autorregistro: toda cuenta nace de un alta hecha por otro actor más una invitación por correo | `DEC-2`, `DEC-3`; extiende `INV-6` |
| `INVD-2` | Un estudiante desactivado o dado de baja no puede comprar ni retirar pedidos anticipados | `DEC-5`, `DEC-7` |
| `INVD-3` | Solo la institución educativa puede reactivar a un estudiante, con independencia de quién lo haya desactivado | `DEC-5` |
| `INVD-4` | Reasignar el código de tarjeta invalida el anterior de forma inmediata y definitiva | `DEC-4` |
| `INVD-5` | El efectivo esperado del día debe poder explicarse a partir de las ventas en efectivo registradas | `DEC-6`; misma forma que `INV-2` e `INV-3` |
| `INVD-6` | Ninguna fotografía almacenada en el prototipo corresponde a una persona real | `DEC-8`; `ALC-OUT-07`, `ALC-OUT-08` |

---

## [S3] Efecto sobre el alcance

Lo que estas decisiones **añaden** respecto de `[S9.1]` del anteproyecto:

| Decisión | Añade al alcance |
|---|---|
| `DEC-1` | Venta a cliente genérico sin identificación; medio de pago en toda venta |
| `DEC-2` | Alta, desactivación y reactivación de cuentas de cajero y administrador por la institución |
| `DEC-3` | Seed de la cuenta institucional; invitación por correo para cajero y administrador |
| `DEC-4` | Asignación del código de tarjeta en la carga; vista de administración de estudiantes; reasignación de código |
| `DEC-5` | Desactivación y reactivación de estudiantes, con permisos asimétricos |
| `DEC-6` | Cierre de caja diario con efectivo contado, diferencia y motivo |
| `DEC-8` | Fotografía del estudiante mostrada al cobrar; imagen del producto en el catálogo |
| `DEC-7` | Baja lógica de estudiante retirado con saldo congelado |
| `DEC-9` | **No añade alcance: lo recorta.** Retira la entrega por correo de las invitaciones de la carga masiva |
| `DEC-10` | **No añade alcance.** Añade un camino alterno de seed para la cuenta institucional, fuera del que describe `HU-39` |

Lo que **no cambia**: los 20 elementos de `[S9.2]` (`ALC-OUT-01..20`) siguen excluidos. En particular, `DEC-1` **no** introduce manejo de dinero real: el efectivo y la transferencia se registran como dato de la venta, y la transferencia ocurre íntegramente fuera del sistema (`ALC-OUT-01`, `ALC-OUT-02`).

`ALC-OUT-14` excluye «la administración del personal de la cafetería». `DEC-2` **no** lo contradice: gestionar credenciales de acceso al sistema no es administrar personal (contratación, turnos, nómina), que sigue fuera.

---

## [ANEXO A] Trazabilidad decisión → vacío → historias

| Vacío | Estado | Decisión | Historias |
|---|---|---|---|
| `VAC-1` Ventas a consumidores sin vínculo estudiantil | **Resuelto** | `DEC-1` | `HU-53`, `HU-54` |
| `VAC-2` Creación de cuentas de cajero y administrador | **Resuelto** | `DEC-2` | `HU-40`, `HU-42` |
| `VAC-3` Autenticación de los demás roles | **Resuelto** | `DEC-3` | `HU-39`, `HU-41` |
| `VAC-4` Vinculación de la tarjeta con el estudiante | **Resuelto** | `DEC-4` | `HU-43`, `HU-44`, `HU-45`, `HU-46` |
| `VAC-5` Pérdida, bloqueo o reposición de tarjeta | **Resuelto** | `DEC-5` | `HU-47`, `HU-48`, `HU-49`, `HU-50` |
| `VAC-6` Cierre de caja | **Resuelto** | `DEC-6` | `HU-55`, `HU-56` |
| — (pregunta abierta) Baja del estudiante retirado | **Resuelto** | `DEC-7` | `HU-51`, `HU-52` |
| — (decisión posterior) Fotografías e imágenes | **Decidido** | `DEC-8` | `HU-57`, `HU-58`, `HU-59` |
| — (decisión posterior) Entrega de las invitaciones de la carga | **Decidido** | `DEC-9` | `HU-03` (criterio modificado) |
| — (decisión posterior) Seed de la cuenta institucional | **Decidido** | `DEC-10` | `HU-39` (sin cambios en el texto) |

---

## [ANEXO B] Puntos que siguen abiertos

Lo que estas decisiones **no** resuelven. Se registran en vez de completarse por inferencia, igual que se hizo con los `VAC-n`.

- **Devolución del saldo congelado.** `DEC-7` la deja fuera del sistema. Es coherente con `ALC-OUT-02`, pero en una implementación real habría que definirla; conviene decirlo así en el informe final (`ENT-06`) como limitación identificada.
- **Notificación al acudiente.** Cuando la institución desactiva o da de baja a un estudiante (`DEC-5`, `DEC-7`), el acudiente no recibe aviso. No se decidió si debe recibirlo.
- **Respaldo bibliográfico de la justificación de `DEC-1`.** Ver la advertencia en esa decisión.
- **Pedidos anticipados de un estudiante desactivado.** `INVD-2` impide retirarlos, pero no se decidió qué ocurre con un pedido ya pagado si el estudiante queda desactivado o de baja: si se devuelve el saldo, si queda pendiente indefinidamente o si se anula.
- **Retención y borrado de fotografías.** `DEC-8` no decide cuánto tiempo se conserva la fotografía de un estudiante dado de baja (`DEC-7`), ni si el acudiente puede exigir su eliminación. En una implementación real la Ley 1581 de 2012 lo exigiría.
- **Alcance del seed.** `DEC-3` lo menciona como carga inicial técnica. No se decidió si el seed forma parte de lo demostrable en `ENT-01` o es un paso de puesta en marcha fuera de la demo.

---

## [ANEXO C] Nota de procedencia

Decisiones tomadas por el equipo el 2026-08-28, en respuesta a los seis vacíos documentales registrados en el `ANEXO B` de `./backlog-historias-de-usuario.md` y a cuatro preguntas abiertas que ese análisis destapó.

El contenido de `[S1]` es **normativo para el proyecto** pero **no forma parte del anteproyecto**: `./smartfood.md` es la reexpresión estructurada del DOCX original y su regla 1 impide alterarlo. Por eso estas decisiones viven en un documento aparte con identificadores propios, y las historias que se derivan de ellas citan `DEC-n` en lugar de `ALC-IN-nn`. Así se distingue en todo momento qué proviene del anteproyecto y qué de una decisión posterior.

**Al preparar la próxima versión del anteproyecto, `[S3]` de este documento es la lista de lo que hay que incorporar a `[S9.1]`.** Mientras eso no ocurra, `./smartfood.md` y este documento se leen juntos.
