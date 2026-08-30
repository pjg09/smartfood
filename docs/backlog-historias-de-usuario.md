# SmartFood — Backlog de historias de usuario

## [S0] Bloque de control del documento

### [S0.1] Metadatos

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-BACKLOG |
| titulo | Backlog de historias de usuario del prototipo SmartFood |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./smartfood.md` (`S4`, `S5`, `S9`, `S10`, `S11`); `./decisiones-de-alcance.md` (`DEC-1` … `DEC-9`, `INVD-1` … `INVD-6`); `corpus:semana-5-gestion-de-proyectos-con-metodologias-agiles.md` (`D07`, `D14`); `corpus:guia-de-scrum-2020.md` (`ART-1`, `COM-1`) |
| tipo_documento | Artefacto de gestión producido por el equipo |
| procedencia | Copia de trabajo. El maestro estaba en el corpus documental de la asignatura (repositorio `tic1`, local). **A partir del traslado, este fichero es el vigente**: no editar la copia del corpus. |
| corresponde_a | `ENT-04` de `./smartfood.md` — «backlog priorizado» |
| institucion | Universidad Pontificia Bolivariana (UPB) |
| asignatura | Proyecto Aplicado en TIC 1 |
| periodo | 202601 |
| historias | 59 (`HU-01` … `HU-59`) |
| epicas | 11 (`EPI-1` … `EPI-11`) |
| vacios_detectados | 6 (`VAC-1` … `VAC-6`) — **todos resueltos**, ver ANEXO B |
| idioma | es-CO |
| version | 2.2 |

### [S0.2] Instrucciones de lectura para el agente

1. Este documento **no es una reexpresión de un original**: es material producido por el equipo. No hay texto verbatim que preservar y no aplica la marca `[DERIVADO]`, porque el documento entero lo es.
2. **Ninguna historia introduce requisitos nuevos.** Cada una declara su **Origen**. Una afirmación sin origen citado es un error de este documento y debe corregirse, no propagarse.
2.1. Hay **dos clases de origen**, y la distinción importa: los identificadores de `./smartfood.md` (`ALC-IN-nn`, `FUN-n`, `INV-n`…) provienen del **anteproyecto**; los `DEC-n` e `INVD-n` provienen de `./decisiones-de-alcance.md`, que son **decisiones del equipo posteriores** y todavía **no incorporadas al anteproyecto**. Una historia con origen `DEC-n` describe alcance acordado que `[S9.1]` aún no recoge.
3. Los **criterios de aceptación** son reformulaciones verificables de lo ya declarado en el alcance, los objetivos o las invariantes. No añaden condiciones que la documentación no imponga.
4. Lo que la documentación **no cubre** no se rellena por cuenta propia: se registra en el `ANEXO B` como vacío `[VAC-n]`. Seis funciones que el prototipo necesitará no tienen respaldo documental hoy.
5. `[S5]` recoge el **calendario de sprints definido por el equipo** en su planeación del Entregable 2. El reparto de historias entre esos sprints no se deriva de la documentación: es planificación, revisable en Sprint Planning (`EVT-1`). Su último apartado registra las dependencias que el calendario no respeta y el ajuste mínimo que las resolvería.
6. Los identificadores `[HU-nn]`, `[EPI-n]` y `[VAC-n]` son estables y citables. No se renumeran; las adiciones van al final de la serie.
7. Las **estimaciones se dejan deliberadamente vacías**: son una decisión del equipo en Sprint Planning (`EVT-1`), no algo derivable de la documentación.

### [S0.3] Mapa de secciones

| ID | Sección | Contenido |
|---|---|---|
| S1 | Formato y convenciones | Plantilla del curso y campos de cada historia |
| S2 | Actores | Los seis usuarios y sus permisos |
| S3 | Historias por épica | `EPI-1` … `EPI-11`, con `HU-01` … `HU-56` |
| S4 | Backlog priorizado | Tabla única ordenada por prioridad |
| S5 | Reparto en sprints | 5 sprints de 2 semanas (sem. 6–15) con las 56 historias repartidas |
| ANEXO A | Trazabilidad alcance → historias | Cobertura de `ALC-IN-01..22` y `FUN-1..7` |
| ANEXO B | Vacíos detectados | `VAC-1` … `VAC-6`, todos resueltos |
| ANEXO C | Nota de procedencia | Cómo se construyó este documento |

---

## [S1] Formato y convenciones

La plantilla es la que enseña `D07` de Semana 5:

> **Como** (tipo de usuario) · **Quiero** (funcionalidad) · **Para** (beneficio o valor)

`D07` del original rotula el primer campo como «Cómo» en el recuadro de estructura y como «Como» en el ejemplo aplicado; la forma canónica es **Como**, tal como quedó registrado en el `[DERIVADO]` de esa diapositiva.

Cada historia lleva:

| Campo | Contenido |
|---|---|
| **Como / Quiero / Para** | La historia en el formato del curso |
| **Actor** | `USR-n` de `./smartfood.md` `[S5]` |
| **Criterios de aceptación** | Condiciones verificables, reformuladas del alcance |
| **Origen** | Identificadores de los que se deriva. Sin esto la historia no es admisible |
| **Prioridad** | `Must` / `Should` / `Could` (ver criterio abajo) |

**Criterio de prioridad**, anclado en la documentación y no en opinión:

- **Must** — la historia está en alguno de los flujos de extremo a extremo que `ENT-01` exige demostrar, o sostiene una invariante `INV-n`, o cubre un escenario crítico de prueba `TST-1..4`.
- **Should** — está dentro del alcance (`ALC-IN-nn`) pero no en la ruta que `ENT-01` enumera.
- **Could** — está en el alcance y aporta valor, pero el prototipo es demostrable sin ella.

Ninguna historia queda fuera del alcance: todo lo listado en `[S9.2]` (`ALC-OUT-01..20`) está excluido por decisión del anteproyecto y **no genera historias**.

---

## [S2] Actores

| Actor | Quién es | Canal |
|---|---|---|
| `USR-1` | Estudiante (5 a 17 años; no administra cuentas ni dispositivos) | Tarjeta física con código de barras |
| `USR-2` | Acudiente | Web adaptable a móvil (`INT-1`) |
| `USR-3` | Cajero de la cafetería | Punto de venta: escritorio + lector (`INT-2`) |
| `USR-4` | Administrador de la cafetería | Interfaz administrativa (`INT-3`) |
| `USR-5` | Institución educativa (secretaría o coordinación) | Interfaz administrativa (`INT-3`) |
| `USR-6` | Consumidor sin vínculo estudiantil (docente, personal, visitante) | Punto de venta — **ver `VAC-1`** |

`USR-1` es el usuario principal del servicio pero **no es usuario del software**: no inicia sesión, no configura nada. Por eso ninguna historia dice «Como estudiante, quiero configurar…». Su única interacción es presentar la tarjeta (`S10.1`). Confundir esto es el error de diseño que el anteproyecto se cuida de evitar.

---

## [S3] Historias por épica

### [EPI-1] Vinculación de perfiles bajo control institucional

*Origen: `ALC-IN-01..05`, `FUN-1`, `OBJ-E2`, `INV-6`*

#### `[HU-01]` Carga masiva de estudiantes y acudientes

> **Como** institución educativa
> **Quiero** cargar la lista de estudiantes matriculados y sus acudientes mediante un archivo estructurado
> **Para** dar de alta las cuentas del sistema sin que nadie ajeno a la institución intervenga en los datos de menores

- **Actor:** `USR-5` · **Prioridad:** Must
- **Criterios de aceptación:**
  - El sistema acepta un archivo estructurado con estudiantes y sus responsables.
  - La carga es una función exclusiva de la institución educativa: ningún otro rol puede ejecutarla.
  - Cada estudiante queda vinculado a un responsable.
  - Un mismo acudiente puede quedar a cargo de varios estudiantes.
- **Origen:** `ALC-IN-01`, `ALC-IN-04`, `FUN-1`, `OBJ-E2`, matriz `S11` (fila «Cargar estudiantes y crear cuentas de acudientes»)

#### `[HU-02]` Validación del archivo antes de escribir

> **Como** institución educativa
> **Quiero** que el sistema valide el archivo y me reporte los errores antes de escribir cualquier dato
> **Para** no dejar el sistema con registros a medias ni con datos de menores mal cargados

- **Actor:** `USR-5` · **Prioridad:** Must
- **Criterios de aceptación:**
  - La validación ocurre **antes** de escribir cualquier dato en el sistema.
  - Si hay errores, se reportan y **no** se escribe nada: la carga es todo o nada.
  - El reporte identifica los errores encontrados.
- **Origen:** `ALC-IN-02`, `FUN-1`, `OBJ-E2`

#### `[HU-03]` Invitación por correo y definición de contraseña

> **Como** acudiente
> **Quiero** recibir una invitación por correo con la que defino mi propia contraseña
> **Para** acceder a la cuenta de mi hijo sin que nadie más haya conocido nunca mi clave

- **Actor:** `USR-2` · **Prioridad:** Must
- **Criterios de aceptación:**
  - El sistema genera la invitación **automáticamente** tras la carga.
  - Se **genera** una invitación por cada acudiente cargado. **Su entrega por correo queda fuera del prototipo** (`DEC-9`): las direcciones de los acudientes son ficticias (`ALC-OUT-07`) y no corresponden a ningún buzón. La entrega real se demuestra en `HU-39` y `HU-41`, que son altas de una en una.
  - El acudiente define su propia contraseña mediante esa invitación. La invitación generada por la carga es utilizable: la historia se demuestra de extremo a extremo tomando el enlace de un acudiente cargado.
- **Origen:** `ALC-IN-03`, `FUN-1`, `OBJ-E2`, `DEC-9`

#### `[HU-04]` Acudiente con varios estudiantes a cargo

> **Como** acudiente con más de un hijo en el colegio
> **Quiero** ver y administrar desde una sola cuenta a todos los estudiantes a mi cargo
> **Para** no tener que manejar una cuenta distinta por cada hijo

- **Actor:** `USR-2` · **Prioridad:** Must
- **Criterios de aceptación:**
  - Una cuenta de acudiente puede tener varios estudiantes vinculados.
  - El saldo, el límite diario y las restricciones son **por estudiante**, no por acudiente.
- **Origen:** `ALC-IN-04`, `ALC-IN-06`, `FUN-1`

#### `[HU-05]` Autorregistro bloqueado

> **Como** institución educativa
> **Quiero** que nadie pueda crearse una cuenta por su cuenta
> **Para** que ninguna cuenta con acceso a datos de menores o a saldos exista sin control institucional

- **Actor:** `USR-5` · **Prioridad:** Must
- **Criterios de aceptación:**
  - No existe ningún camino de autorregistro en ninguna de las tres interfaces.
  - Toda cuenta de acudiente nace de la carga institucional (`HU-01`) más la invitación (`HU-03`).
- **Origen:** `ALC-IN-05`, `OBJ-E2`, `INV-6`

---

### [EPI-2] Billetera y saldo

*Origen: `ALC-IN-06`, `ALC-IN-17`, `ALC-IN-19`, `FUN-2`, `OBJ-E4`, `INV-1`, `INV-2`*

#### `[HU-06]` Recarga de la billetera

> **Como** acudiente
> **Quiero** recargar la billetera individual de mi hijo
> **Para** que pueda comprar en la cafetería sin llevar efectivo

- **Actor:** `USR-2` · **Prioridad:** Must
- **Criterios de aceptación:**
  - La billetera es individual por estudiante.
  - La recarga la ejecuta únicamente el acudiente.
  - La recarga queda asentada en el historial de movimientos.
  - El flujo de pago es **simulado**: no hay dinero real ni pasarela bancaria.
- **Origen:** `ALC-IN-06`, `FUN-2`, `S11`, `ALC-OUT-01`, `ALC-OUT-02`

#### `[HU-07]` Consulta de saldo por el acudiente

> **Como** acudiente
> **Quiero** consultar el saldo disponible de mi hijo
> **Para** saber si necesita una recarga antes de que se quede sin fondos

- **Actor:** `USR-2` · **Prioridad:** Must
- **Criterios de aceptación:**
  - El acudiente ve el saldo de cada estudiante a su cargo.
  - El saldo mostrado corresponde exactamente al historial de movimientos.
- **Origen:** `ALC-IN-06`, `ALC-IN-19`, `S11`, `INV-2`

#### `[HU-08]` Saldo reconstruible desde el historial

> **Como** equipo de desarrollo
> **Quiero** que el saldo de cualquier billetera pueda reconstruirse a partir de su historial de movimientos
> **Para** que el sistema tenga trazabilidad verificable y no un número que haya que creer

- **Actor:** `USR-2` (beneficiario) · **Prioridad:** Must
- **Criterios de aceptación:**
  - Todo movimiento que altere el saldo queda registrado.
  - La suma del historial coincide **exactamente** con el saldo mostrado (`TST-3`).
- **Origen:** `ALC-IN-19`, `OBJ-E4`, `INV-2`, `TST-3`

---

### [EPI-3] Control parental

*Origen: `ALC-IN-07..09`, `FUN-3`, `OBJ-E5`, `INV-4`, `INV-5`*

#### `[HU-09]` Límite diario de gasto

> **Como** acudiente
> **Quiero** fijar un límite diario de gasto para mi hijo
> **Para** que no gaste en un solo día el saldo de toda la semana

- **Actor:** `USR-2` · **Prioridad:** Must
- **Criterios de aceptación:**
  - El límite se define por estudiante.
  - Solo el acudiente puede fijarlo o modificarlo.
  - El límite se evalúa contra el consumo del día en cada venta.
- **Origen:** `ALC-IN-07`, `FUN-2`, `OBJ-E5`, `S11`

#### `[HU-10]` Bloqueo de un producto puntual

> **Como** acudiente
> **Quiero** bloquear un producto concreto del catálogo
> **Para** impedir que mi hijo lo compre aunque tenga saldo

- **Actor:** `USR-2` · **Prioridad:** Must
- **Criterios de aceptación:**
  - El bloqueo aplica a un producto identificado del catálogo.
  - Se distingue explícitamente del bloqueo por alérgeno (`HU-11`).
- **Origen:** `ALC-IN-08`, `FUN-3`, `OBJ-E5`

#### `[HU-11]` Bloqueo por alérgeno

> **Como** acudiente de un estudiante alérgico
> **Quiero** bloquear un alérgeno completo y no una lista de productos
> **Para** que mi hijo quede protegido también frente a los productos que la cafetería agregue después

- **Actor:** `USR-2` · **Prioridad:** Must
- **Criterios de aceptación:**
  - El bloqueo se aplica sobre la **condición** (el alérgeno), no sobre una lista fija de productos.
  - Un producto incorporado al catálogo **después** de configurado el bloqueo queda cubierto automáticamente si declara ese alérgeno.
  - Depende de que el catálogo declare alérgenos por producto (`HU-25`).
- **Origen:** `ALC-IN-08`, `FUN-3`, `OBJ-E5`, `INV-5`

#### `[HU-12]` Retiro de una restricción

> **Como** acudiente
> **Quiero** retirar una restricción que había configurado
> **Para** ajustarla cuando cambian las condiciones de mi hijo

- **Actor:** `USR-2` · **Prioridad:** Should
- **Criterios de aceptación:**
  - Solo el acudiente puede retirar una restricción.
  - El retiro queda asentado, por ser una acción auditable sobre la seguridad del estudiante.
- **Origen:** `S11` (fila «Configurar y **retirar** restricciones alimentarias»), `ALC-IN-19`

#### `[HU-13]` Restricciones no desactivables por la cafetería

> **Como** acudiente
> **Quiero** que ni el cajero ni la administración ni el colegio puedan desactivar las restricciones que configuré
> **Para** que el control parental sea realmente mío y no una sugerencia

- **Actor:** `USR-2` · **Prioridad:** Must
- **Criterios de aceptación:**
  - El cajero **ve** las restricciones vigentes al cobrar, pero no dispone de ninguna acción para desactivarlas ni omitirlas.
  - La administración de la cafetería tampoco puede modificarlas.
  - La institución educativa tampoco puede modificarlas.
- **Origen:** `ALC-IN-09`, `FUN-3`, `OBJ-E5`, `INV-4`, `S11`

---

### [EPI-4] Identificación física del estudiante

*Origen: `ALC-IN-11..13`, `FUN-4`, `INV-7`*

#### `[HU-14]` Generación aleatoria del código de la tarjeta

> **Como** equipo de desarrollo
> **Quiero** que el sistema genere el código de cada tarjeta de forma aleatoria y no secuencial
> **Para** que nadie pueda deducir el código de otro estudiante, dado que opera como credencial de acceso a su saldo

- **Actor:** `USR-1` (beneficiario) · **Prioridad:** Must
- **Criterios de aceptación:**
  - El código lo genera el sistema, no una persona.
  - La generación es aleatoria y **no** secuencial: un código no permite deducir otro.
- **Origen:** `ALC-IN-12`, `FUN-4`, `INV-7`

#### `[HU-15]` Identificación por escaneo de la tarjeta

> **Como** cajero
> **Quiero** identificar al estudiante escaneando su tarjeta con el lector de código de barras
> **Para** atender toda la fila en la ventana de veinte a treinta minutos del descanso

- **Actor:** `USR-3` · **Prioridad:** Must
- **Criterios de aceptación:**
  - El lector físico está integrado con el sistema.
  - El escaneo identifica al estudiante y trae su información de venta (`HU-17`).
  - La validación se realiza a escala reducida, con un número limitado de tarjetas (prueba de concepto).
- **Origen:** `ALC-IN-11`, `ALC-IN-13`, `FUN-4`, `ENT-02`, `ALC-OUT-05`

#### `[HU-16]` Identificación alternativa por documento

> **Como** cajero
> **Quiero** buscar al estudiante por su documento cuando no trae la tarjeta
> **Para** poder atenderlo igualmente sin romper el registro de la venta

- **Actor:** `USR-3` · **Prioridad:** Should
- **Criterios de aceptación:**
  - La búsqueda por documento es una alternativa al escaneo, con el mismo resultado.
  - Las restricciones, el saldo y el límite se aplican igual que en la vía con tarjeta.
- **Origen:** `FUN-4` («…escaneando su tarjeta **o buscándolo por documento**»)

---

### [EPI-5] Venta en el punto de venta

*Origen: `ALC-IN-14`, `ALC-IN-17`, `ALC-IN-19`, `FUN-4`, `OBJ-E4`, `TST-1..3`, `INV-1`*

#### `[HU-17]` Vista de cobro con saldo, consumo y restricciones

> **Como** cajero
> **Quiero** ver de inmediato el saldo disponible, el consumo del día y las restricciones vigentes al identificar al estudiante
> **Para** saber antes de cobrar si la venta va a poder realizarse

- **Actor:** `USR-3` · **Prioridad:** Must
- **Criterios de aceptación:**
  - Al identificar al estudiante se muestran los tres datos: saldo, consumo del día y restricciones.
  - El cajero ve el saldo **solo al cobrar**, no como consulta libre.
- **Origen:** `FUN-4`, `ALC-IN-09`, `S11` (fila «Consultar saldo de un estudiante» → cajero: «Solo al cobrar»)

#### `[HU-18]` Venta rechazada por alérgeno bloqueado

> **Como** acudiente de un estudiante alérgico
> **Quiero** que el sistema rechace la venta de un producto que contiene un alérgeno bloqueado
> **Para** que la restricción proteja a mi hijo en el momento en que importa

- **Actor:** `USR-2` (beneficiario) / `USR-3` (opera) · **Prioridad:** Must
- **Criterios de aceptación:**
  - La validación ocurre en tiempo real, en el momento de la venta.
  - La venta se **rechaza**; el cajero no dispone de una vía para forzarla.
  - Es el escenario crítico `TST-1` del plan de pruebas.
- **Origen:** `ALC-IN-14`, `ALC-IN-09`, `INV-4`, `INV-5`, `TST-1`, `ENT-05`

#### `[HU-19]` Venta rechazada por saldo insuficiente

> **Como** acudiente
> **Quiero** que ninguna venta pueda dejar la billetera de mi hijo en saldo negativo
> **Para** que el sistema no genere deudas que yo no autoricé

- **Actor:** `USR-2` (beneficiario) / `USR-3` (opera) · **Prioridad:** Must
- **Criterios de aceptación:**
  - Si los fondos son insuficientes, la venta no se realiza.
  - El saldo nunca queda negativo, bajo ninguna combinación de operaciones.
  - Es parte del escenario crítico `TST-2`.
- **Origen:** `ALC-IN-14`, `FUN-2`, `OBJ-E4`, `INV-1`, `TST-2`

#### `[HU-20]` Venta rechazada por límite diario superado

> **Como** acudiente
> **Quiero** que la venta se rechace cuando mi hijo ya alcanzó el límite diario que fijé
> **Para** que el límite sea efectivo y no meramente informativo

- **Actor:** `USR-2` (beneficiario) / `USR-3` (opera) · **Prioridad:** Must
- **Criterios de aceptación:**
  - El consumo del día se evalúa contra el límite en cada venta.
  - Si el cupo del día es insuficiente, la venta no se realiza, aunque haya saldo.
  - Es parte del escenario crítico `TST-2`.
- **Origen:** `ALC-IN-14`, `ALC-IN-07`, `FUN-2`, `TST-2`

#### `[HU-21]` Descuento simultáneo de saldo y existencias

> **Como** administrador de la cafetería
> **Quiero** que cada venta descuente a la vez el saldo del estudiante y las existencias del producto
> **Para** que el dinero y el inventario nunca queden descuadrados entre sí

- **Actor:** `USR-4` (beneficiario) / `USR-3` (opera) · **Prioridad:** Must
- **Criterios de aceptación:**
  - Ambos descuentos ocurren en la misma operación: no puede quedar uno sin el otro.
  - La venta queda asentada en el historial de movimientos de la billetera y del producto.
- **Origen:** `ALC-IN-17`, `ALC-IN-19`, `FUN-4`, `INV-2`, `INV-3`

#### `[HU-22]` Venta con información nutricional congelada

> **Como** acudiente
> **Quiero** que cada venta guarde la información nutricional del producto tal como estaba declarada en ese momento
> **Para** que el historial de consumo no cambie cuando la cafetería edite el producto después

- **Actor:** `USR-2` (beneficiario) · **Prioridad:** Must
- **Criterios de aceptación:**
  - La venta almacena la información nutricional vigente al momento de registrarse.
  - Una edición posterior del catálogo no altera las ventas ya asentadas.
- **Origen:** `ALC-IN-20` («…tal como estaba declarada al momento de la venta»), `OBJ-E3`

#### `[HU-58]` Fotografía visible al cobrar

> **Como** cajero
> **Quiero** ver la fotografía del estudiante al escanear su tarjeta
> **Para** darme cuenta en el momento de que quien la presenta no es su dueño

- **Actor:** `USR-3` · **Prioridad:** Must
- **Criterios de aceptación:**
  - La fotografía aparece en la vista de cobro (`HU-17`), junto al saldo, el consumo del día y las restricciones.
  - Si el estudiante no tiene fotografía, la venta procede igual.
  - Es un control **preventivo**: complementa la desactivación de `HU-47` y `HU-48`, que solo actúa una vez reportada la pérdida.
- **Origen:** `DEC-8`, `FUN-4`

---

### [EPI-6] Pedidos anticipados

*Origen: `ALC-IN-10`, `FUN-5`*

#### `[HU-23]` Reserva y pago anticipado

> **Como** acudiente
> **Quiero** reservar y pagar por adelantado el consumo de mi hijo
> **Para** asegurar que reciba lo que decidí, sin depender de lo que él elija en la fila

- **Actor:** `USR-2` · **Prioridad:** Should
- **Criterios de aceptación:**
  - El pedido se asocia al perfil del estudiante.
  - Se paga en el momento de reservarse (pago simulado).
  - Se gestiona desde la aplicación del acudiente.
- **Origen:** `ALC-IN-10`, `FUN-5`, `ALC-OUT-02`

#### `[HU-24]` Consulta de reservas pendientes

> **Como** personal de la cafetería
> **Quiero** consultar las reservas pendientes
> **Para** tenerlas preparadas antes de que lleguen los estudiantes

- **Actor:** `USR-3` / `USR-4` · **Prioridad:** Should
- **Criterios de aceptación:**
  - Las reservas pendientes son consultables desde la cafetería.
- **Origen:** `FUN-5`

#### `[HU-25]` Registro de la entrega del pedido

> **Como** cajero
> **Quiero** registrar la entrega de un pedido anticipado en el punto de venta
> **Para** que quede constancia de que se entregó y no se entregue dos veces

- **Actor:** `USR-3` · **Prioridad:** Should
- **Criterios de aceptación:**
  - La entrega se registra en el punto de venta.
  - El pedido ya pagado no vuelve a descontar saldo al entregarse.
- **Origen:** `ALC-IN-10`, `FUN-5`

---

### [EPI-7] Catálogo e inventario

*Origen: `ALC-IN-15`, `ALC-IN-16`, `ALC-IN-18`, `ALC-IN-19`, `FUN-6`, `OBJ-E6`, `INV-3`, `INV-8`*

#### `[HU-26]` Administración del catálogo

> **Como** administrador de la cafetería
> **Quiero** mantener el catálogo con precio, categoría, información nutricional y alérgenos declarados
> **Para** que el punto de venta cobre bien y las restricciones por alérgeno puedan aplicarse

- **Actor:** `USR-4` · **Prioridad:** Must
- **Criterios de aceptación:**
  - Cada producto admite precio, categoría, información nutricional y alérgenos declarados.
  - Es requisito previo del bloqueo por alérgeno (`HU-11`) y de los reportes nutricionales (`HU-31`).
  - Solo la administración de la cafetería gestiona el catálogo.
- **Origen:** `ALC-IN-15`, `FUN-6`, `S11`

#### `[HU-27]` Ingreso de mercancía por ajuste manual

> **Como** administrador de la cafetería
> **Quiero** registrar el ingreso de mercancía como un ajuste manual sobre unidades vendibles
> **Para** tener existencias actualizadas sin gestionar órdenes de compra ni proveedores

- **Actor:** `USR-4` · **Prioridad:** Must
- **Criterios de aceptación:**
  - El inventario opera sobre **unidades vendibles**, no sobre insumos ni recetas.
  - El aumento se registra como ajuste manual de la administración.
  - Un producto preparado en la cafetería entra como existencia mediante este ajuste, sin descomponerlo en insumos.
- **Origen:** `ALC-IN-16`, `FUN-6`, `ALC-OUT-11`, `ALC-OUT-12`, `ALC-OUT-15`

#### `[HU-28]` Registro de merma con motivo obligatorio

> **Como** administrador de la cafetería
> **Quiero** que toda disminución manual de inventario exija un motivo
> **Para** que ninguna unidad desaparezca del sistema sin explicación

- **Actor:** `USR-4` · **Prioridad:** Must
- **Criterios de aceptación:**
  - El motivo es **obligatorio**: sin él la disminución no se registra.
  - Aplica a toda disminución manual, no solo a la merma.
- **Origen:** `ALC-IN-16`, `ALC-IN-18`, `INV-8`

#### `[HU-29]` Existencias explicables desde el historial

> **Como** administrador de la cafetería
> **Quiero** que las existencias de cualquier producto puedan explicarse a partir de su historial de movimientos
> **Para** poder auditar un descuadre en lugar de tener que aceptarlo

- **Actor:** `USR-4` · **Prioridad:** Must
- **Criterios de aceptación:**
  - Todo movimiento de inventario queda asentado con su motivo.
  - Las existencias mostradas coinciden exactamente con el historial (`TST-4`).
- **Origen:** `ALC-IN-19`, `FUN-6`, `OBJ-E6`, `INV-3`, `TST-4`

#### `[HU-59]` Imagen del producto

> **Como** administrador de la cafetería
> **Quiero** asociar una imagen a cada producto del catálogo
> **Para** que el cajero lo reconozca de un vistazo y la fila avance más rápido

- **Actor:** `USR-4` · **Prioridad:** Should
- **Criterios de aceptación:**
  - La imagen se gestiona junto al resto del producto (`HU-26`).
  - No es obligatoria: un producto sin imagen se vende igual.
- **Origen:** `DEC-8`, `INT-2`

---

### [EPI-8] Reportes y recomendaciones

*Origen: `ALC-IN-20..22`, `FUN-7`, `OBJ-E3`, `INV-9`*

#### `[HU-30]` Historial de consumo para el acudiente

> **Como** acudiente
> **Quiero** consultar el historial de consumo de mi hijo con la información nutricional de cada producto
> **Para** saber qué está comiendo realmente en el colegio

- **Actor:** `USR-2` · **Prioridad:** Must
- **Criterios de aceptación:**
  - El historial muestra cada venta con la información nutricional registrada en ese momento (`HU-22`).
  - Solo el acudiente accede al consumo de los estudiantes a su cargo.
- **Origen:** `ALC-IN-20`, `FUN-7`, `OBJ-E3`, `S11`

#### `[HU-31]` Alertas de frecuencia de consumo

> **Como** acudiente
> **Quiero** recibir alertas sobre la frecuencia con que mi hijo consume cada categoría de producto
> **Para** detectar un patrón que no vería mirando compras sueltas

- **Actor:** `USR-2` · **Prioridad:** Should
- **Criterios de aceptación:**
  - Las alertas se generan por **reglas determinísticas**, no por un modelo probabilístico.
  - Se calculan sobre la frecuencia de consumo por categoría.
- **Origen:** `ALC-IN-21`, `FUN-7`, `OBJ-E3`

#### `[HU-32]` Comparación con valores de referencia

> **Como** acudiente
> **Quiero** ver los agregados nutricionales del consumo de mi hijo frente a los valores de referencia de la autoridad sanitaria colombiana
> **Para** interpretar las cifras con un punto de comparación oficial

- **Actor:** `USR-2` · **Prioridad:** Should
- **Criterios de aceptación:**
  - La referencia es la publicada por la autoridad sanitaria colombiana.
  - El cálculo es determinístico y reproducible.
- **Origen:** `ALC-IN-21`, `FUN-7`

#### `[HU-33]` Resumen de gasto frente a saldo recargado

> **Como** acudiente
> **Quiero** ver un resumen del gasto de mi hijo frente al saldo que recargué
> **Para** entender en qué se está yendo el dinero

- **Actor:** `USR-2` · **Prioridad:** Should
- **Criterios de aceptación:**
  - El resumen contrasta gasto contra saldo recargado en el periodo.
- **Origen:** `ALC-IN-21`, `FUN-7`

#### `[HU-34]` Aviso de carácter orientativo

> **Como** equipo de desarrollo
> **Quiero** que la interfaz declare explícitamente que las recomendaciones son orientativas
> **Para** no incurrir en valoración nutricional individualizada, que es un acto profesional del área de la salud

- **Actor:** `USR-2` (destinatario) · **Prioridad:** Must
- **Criterios de aceptación:**
  - El aviso aparece **en la interfaz**, junto a las recomendaciones.
  - Declara que no constituyen valoración médica ni nutricional individualizada.
- **Origen:** `ALC-IN-21`, `ALC-OUT-20`, `INV-9`

#### `[HU-35]` Reporte de ventas

> **Como** administrador de la cafetería
> **Quiero** consultar reportes de ventas a partir de las transacciones registradas
> **Para** conocer la actividad comercial real del servicio

- **Actor:** `USR-4` · **Prioridad:** Should
- **Criterios de aceptación:**
  - El reporte se construye sobre las transacciones registradas, no sobre datos capturados aparte.
  - Solo la administración de la cafetería accede.
- **Origen:** `ALC-IN-22`, `FUN-7`, `S11`

#### `[HU-36]` Reporte de movimientos de inventario

> **Como** administrador de la cafetería
> **Quiero** consultar los movimientos de inventario
> **Para** revisar entradas, ventas y mermas en un solo lugar

- **Actor:** `USR-4` · **Prioridad:** Should
- **Criterios de aceptación:**
  - El reporte cubre los movimientos registrados con su motivo.
- **Origen:** `ALC-IN-22`, `ALC-IN-19`, `FUN-7`

#### `[HU-37]` Reporte de auditoría

> **Como** administrador de la cafetería
> **Quiero** un reporte de auditoría de las operaciones registradas
> **Para** poder rastrear quién hizo qué cuando algo no cuadre

- **Actor:** `USR-4` · **Prioridad:** Should
- **Criterios de aceptación:**
  - El reporte se construye sobre las transacciones registradas.
- **Origen:** `ALC-IN-22`, `FUN-7`

#### `[HU-38]` Consulta de restricciones por los cuatro roles

> **Como** cajero, administrador o institución educativa
> **Quiero** consultar las restricciones vigentes de un estudiante
> **Para** operar el servicio conociéndolas, sin poder alterarlas

- **Actor:** `USR-3`, `USR-4`, `USR-5` · **Prioridad:** Must
- **Criterios de aceptación:**
  - Los cuatro roles de la matriz `S11` pueden **consultar** restricciones.
  - Ninguno salvo el acudiente puede configurarlas ni retirarlas (`HU-13`).
- **Origen:** `S11` (fila «Consultar restricciones de un estudiante»: Sí en las cuatro columnas), `INV-4`

---

### [EPI-9] Cuentas del personal y acceso al sistema

*Origen: `DEC-2`, `DEC-3`, `INVD-1`. Cierra `VAC-2` y `VAC-3`.*

#### `[HU-39]` Alta de la institución educativa por seed

> **Como** institución educativa
> **Quiero** que mi cuenta quede creada en la puesta en marcha y recibir una invitación por correo para definir mi contraseña
> **Para** poder empezar a operar el sistema sin que nadie me haya entregado una clave

- **Actor:** `USR-5` · **Prioridad:** Must
- **Criterios de aceptación:**
  - La cuenta de la institución se crea en el seed del sistema.
  - El seed dispara una invitación por correo.
  - La institución define su propia contraseña mediante esa invitación.
  - El prototipo opera sobre **una** institución de referencia.
- **Origen:** `DEC-3`, `INVD-1`, `ALC-OUT-10`

#### `[HU-40]` Alta de cuentas de cajero y administrador

> **Como** institución educativa
> **Quiero** dar de alta las cuentas de los cajeros y del administrador de la cafetería
> **Para** que el personal pueda operar el sistema sin que nadie se registre por su cuenta

- **Actor:** `USR-5` · **Prioridad:** Must
- **Criterios de aceptación:**
  - Solo la institución educativa puede crear cuentas de `USR-3` y `USR-4`.
  - No existe autorregistro para ningún rol del sistema.
  - El alta dispara la invitación por correo de `HU-41`.
- **Origen:** `DEC-2`, `DEC-3`, `INVD-1`, `ALC-IN-05`

#### `[HU-41]` Contraseña por invitación para el personal

> **Como** cajero o administrador de la cafetería
> **Quiero** recibir una invitación por correo con la que defino mi propia contraseña
> **Para** que quien creó mi cuenta no llegue a conocer nunca mi clave

- **Actor:** `USR-3`, `USR-4` · **Prioridad:** Must
- **Criterios de aceptación:**
  - La invitación se envía al dar de alta la cuenta.
  - El titular define su propia contraseña.
  - Ninguna contraseña del sistema es conocida por quien creó la cuenta.
- **Origen:** `DEC-3`, `INVD-1`

#### `[HU-42]` Desactivación y reactivación de cuentas de personal

> **Como** institución educativa
> **Quiero** desactivar y reactivar las cuentas del personal de la cafetería
> **Para** revocar el acceso de alguien que ya no trabaja allí sin tener que borrar su historial

- **Actor:** `USR-5` · **Prioridad:** Should
- **Criterios de aceptación:**
  - Una cuenta desactivada no puede iniciar sesión ni operar.
  - La institución puede reactivarla.
  - El historial de operaciones de esa cuenta se conserva.
- **Origen:** `DEC-2`

---

### [EPI-10] Administración de estudiantes y estado de la cuenta

*Origen: `DEC-4`, `DEC-5`, `DEC-7`, `INVD-2`, `INVD-3`, `INVD-4`. Cierra `VAC-4` y `VAC-5`.*

#### `[HU-43]` Código de tarjeta asignado en la carga

> **Como** institución educativa
> **Quiero** que al cargar un estudiante el sistema le asigne automáticamente su código de tarjeta
> **Para** poder imprimir su código de barras sin tener que generarlo aparte

- **Actor:** `USR-5` · **Prioridad:** Must
- **Criterios de aceptación:**
  - La asignación es automática al dar de alta al estudiante, sea por carga masiva o individual.
  - El código lo genera el sistema de forma aleatoria y no secuencial (`HU-14`).
  - El código queda listo para imprimirse como código de barras.
- **Origen:** `DEC-4`, `ALC-IN-12`, `INV-7`

#### `[HU-44]` Vista de administración de estudiantes

> **Como** institución educativa
> **Quiero** una vista donde administrar a todos los estudiantes: matricular uno individual y modificar sus campos
> **Para** mantener los datos al día durante el año, y no solo en la carga inicial

- **Actor:** `USR-5` · **Prioridad:** Must
- **Criterios de aceptación:**
  - Permite matricular un estudiante individual, además de la carga masiva de `HU-01`.
  - Permite modificar los campos de un estudiante ya cargado.
  - Es una función exclusiva de la institución educativa.
- **Origen:** `DEC-4`, `ALC-IN-01`, `S11`

#### `[HU-45]` Consulta del código de tarjeta vigente

> **Como** institución educativa
> **Quiero** consultar el código de tarjeta vigente de un estudiante
> **Para** poder producir la tarjeta que le corresponde

- **Actor:** `USR-5` · **Prioridad:** Must
- **Criterios de aceptación:**
  - La consulta se hace desde la vista de administración de estudiantes.
  - Muestra el código **vigente**; los códigos reemplazados no son válidos (`HU-46`).
- **Origen:** `DEC-4`, `ENT-02`

#### `[HU-46]` Reasignación del código de tarjeta

> **Como** institución educativa
> **Quiero** reasignar el código de tarjeta de un estudiante
> **Para** poder reponerle la tarjeta cuando la pierde, se deteriora o se sospecha que fue copiada

- **Actor:** `USR-5` · **Prioridad:** Must
- **Criterios de aceptación:**
  - La reasignación genera un código nuevo, aleatorio y no secuencial.
  - **El código anterior queda invalidado de inmediato** y no vuelve a ser válido nunca.
  - Una venta intentada con el código anterior no identifica a nadie.
- **Origen:** `DEC-4`, `INVD-4`, `INV-7`

#### `[HU-47]` Desactivación de un estudiante por la institución

> **Como** institución educativa
> **Quiero** desactivar a un estudiante en cualquier momento
> **Para** bloquear su tarjeta de inmediato cuando se pierde en mitad de la jornada y el acudiente aún no se ha enterado

- **Actor:** `USR-5` · **Prioridad:** Must
- **Criterios de aceptación:**
  - La institución puede desactivar en cualquier momento.
  - El efecto es inmediato en el punto de venta (`HU-50`).
- **Origen:** `DEC-5`, `INVD-2`

#### `[HU-48]` Desactivación de un estudiante por el acudiente

> **Como** acudiente
> **Quiero** desactivar a mi hijo yo mismo cuando me avisa de que perdió la tarjeta
> **Para** bloquearla sin depender del horario de la secretaría del colegio

- **Actor:** `USR-2` · **Prioridad:** Must
- **Criterios de aceptación:**
  - El acudiente puede desactivar en cualquier momento a los estudiantes a su cargo.
  - El acudiente **no** dispone de la acción de reactivar (`HU-49`).
- **Origen:** `DEC-5`, `INVD-2`, `INVD-3`

#### `[HU-49]` Reactivación exclusiva de la institución

> **Como** institución educativa
> **Quiero** ser la única que puede reactivar a un estudiante
> **Para** que el desbloqueo pase siempre por una verificación presencial y quien encontró la tarjeta no consiga reactivarla

- **Actor:** `USR-5` · **Prioridad:** Must
- **Criterios de aceptación:**
  - Solo la institución reactiva, **con independencia de quién haya desactivado**.
  - El acudiente que desactivó debe comunicarse con la institución para el desbloqueo.
- **Origen:** `DEC-5`, `INVD-3`

#### `[HU-50]` Venta rechazada por estudiante desactivado

> **Como** acudiente
> **Quiero** que la venta se rechace mientras mi hijo esté desactivado
> **Para** que la tarjeta perdida no le sirva a quien la encontró

- **Actor:** `USR-2` (beneficiario) / `USR-3` (opera) · **Prioridad:** Must
- **Criterios de aceptación:**
  - Un estudiante desactivado o dado de baja no puede comprar.
  - Tampoco puede retirar pedidos anticipados.
  - **Sí puede recibir recargas**, por ser inocuo.
  - El motivo del rechazo se distingue de los de `HU-18`, `HU-19` y `HU-20`.
- **Origen:** `DEC-5`, `DEC-7`, `INVD-2`

#### `[HU-51]` Baja lógica del estudiante retirado

> **Como** institución educativa
> **Quiero** dar de baja a un estudiante que se retiró del colegio
> **Para** cerrar su acceso sin destruir el historial que sostiene la trazabilidad

- **Actor:** `USR-5` · **Prioridad:** Should
- **Criterios de aceptación:**
  - La baja es **lógica**: el historial de consumo y el de movimientos se conservan íntegros.
  - Es un estado **distinto** de la desactivación de `HU-47`: «se retiró» no es «perdió la tarjeta».
  - Un estudiante de baja no puede comprar ni recargar.
- **Origen:** `DEC-7`, `INVD-2`, `INV-2`

#### `[HU-52]` Saldo congelado y consultable tras la baja

> **Como** acudiente
> **Quiero** seguir viendo el saldo que le quedaba a mi hijo cuando se retiró del colegio
> **Para** tener constancia de que ese dinero existió y poder reclamarlo

- **Actor:** `USR-2` · **Prioridad:** Should
- **Criterios de aceptación:**
  - El saldo remanente queda congelado y sigue siendo consultable.
  - No se puede comprar ni recargar sobre él.
  - **La devolución del dinero queda fuera del sistema** (`ALC-OUT-01`, `ALC-OUT-02`).
- **Origen:** `DEC-7`, `ALC-OUT-01`, `ALC-OUT-02`, `INV-2`

#### `[HU-57]` Fotografía del estudiante

> **Como** institución educativa
> **Quiero** cargar y actualizar la fotografía de cada estudiante
> **Para** que el cajero pueda comprobar que la tarjeta la presenta su dueño

- **Actor:** `USR-5` · **Prioridad:** Must
- **Criterios de aceptación:**
  - La fotografía se carga y actualiza desde la vista de administración de estudiantes (`HU-44`).
  - **No es obligatoria:** su ausencia no impide ninguna operación.
  - En el prototipo son avatares generados, nunca personas reales (`INVD-6`).
- **Origen:** `DEC-8`, `INVD-6`, `ALC-OUT-07`

---

### [EPI-11] Caja, medios de pago y venta a cliente genérico

*Origen: `DEC-1`, `DEC-6`, `INVD-5`. Cierra `VAC-1` y `VAC-6`.*

#### `[HU-53]` Venta a cliente genérico

> **Como** cajero
> **Quiero** registrar una venta a un cliente que no está identificado ni tiene vínculo estudiantil
> **Para** poder atender a docentes, personal y visitantes sin dejar esa venta fuera del sistema

- **Actor:** `USR-3` · **Prioridad:** Must
- **Criterios de aceptación:**
  - La venta no exige identificación ni registro previo del cliente.
  - **Descuenta inventario** como cualquier otra venta.
  - **No aplica restricciones alimentarias**: no hay acudiente que las haya configurado.
  - No descuenta ninguna billetera.
  - Queda registrada y entra en los reportes de ventas (`HU-35`).
- **Origen:** `DEC-1`, `S5` (`USR-6`), `ALC-IN-17`, `ALC-IN-22`

#### `[HU-54]` Medio de pago en toda venta

> **Como** administrador de la cafetería
> **Quiero** que cada venta registre con qué se pagó
> **Para** saber de dónde vino el dinero y poder cuadrar la caja

- **Actor:** `USR-4` · **Prioridad:** Must
- **Criterios de aceptación:**
  - Toda venta registra su medio de pago: `billetera`, `efectivo` o `transferencia`.
  - Las ventas de estudiante son siempre `billetera`.
  - La **transferencia** va de la app bancaria del cliente a la cuenta de la cafetería: **no pasa por el sistema y no es una recarga**; el sistema solo deja constancia.
  - Ninguna de las dos modalidades implica manejo de dinero real en el prototipo.
- **Origen:** `DEC-1`, `ALC-OUT-01`, `ALC-OUT-02`

#### `[HU-55]` Cierre de caja diario

> **Como** cajero
> **Quiero** que al cerrar la jornada el sistema me muestre cuánto efectivo recibí, para compararlo con lo que tengo contado
> **Para** cuadrar la caja contra ventas registradas y no contra una estimación

- **Actor:** `USR-3` · **Prioridad:** Should
- **Criterios de aceptación:**
  - El sistema calcula el total de ventas en **efectivo** del día a partir de las ventas registradas.
  - El cajero registra el efectivo contado y la base que dejó para dar cambio.
  - El sistema calcula y registra la diferencia.
  - **Si la diferencia es distinta de cero, el motivo es obligatorio** (mismo criterio que `ALC-IN-18`).
  - Las ventas por **transferencia no entran** en el cuadre: ese dinero nunca pasó por la caja.
  - No hay apertura formal de turno: el cuadre es diario.
- **Origen:** `DEC-6`, `INVD-5`, `ALC-IN-18`, `PA-7`

#### `[HU-56]` Reporte de cierres de caja

> **Como** administrador de la cafetería
> **Quiero** consultar los cierres de caja registrados con sus diferencias y motivos
> **Para** detectar un patrón de descuadres en lugar de enterarme suelto cada día

- **Actor:** `USR-4` · **Prioridad:** Should
- **Criterios de aceptación:**
  - Los cierres quedan registrados y son consultables.
  - El reporte alimenta la auditoría de `ALC-IN-22`.
  - El efectivo esperado de un día se explica a partir de sus ventas en efectivo registradas.
- **Origen:** `DEC-6`, `INVD-5`, `ALC-IN-22`

---

## [S4] Backlog priorizado

Orden: primero los `Must` que sostienen invariantes o escenarios críticos, después el resto de la ruta de `ENT-01`, después lo demás.

| # | ID | Historia | Épica | Actor | Prioridad |
|---|---|---|---|---|---|
| 1 | `HU-01` | Carga masiva de estudiantes y acudientes | EPI-1 | USR-5 | Must |
| 2 | `HU-02` | Validación del archivo antes de escribir | EPI-1 | USR-5 | Must |
| 3 | `HU-03` | Invitación por correo y contraseña | EPI-1 | USR-2 | Must |
| 4 | `HU-05` | Autorregistro bloqueado | EPI-1 | USR-5 | Must |
| 5 | `HU-04` | Acudiente con varios estudiantes | EPI-1 | USR-2 | Must |
| 6 | `HU-26` | Administración del catálogo | EPI-7 | USR-4 | Must |
| 7 | `HU-06` | Recarga de la billetera | EPI-2 | USR-2 | Must |
| 8 | `HU-08` | Saldo reconstruible desde el historial | EPI-2 | USR-2 | Must |
| 9 | `HU-07` | Consulta de saldo por el acudiente | EPI-2 | USR-2 | Must |
| 10 | `HU-09` | Límite diario de gasto | EPI-3 | USR-2 | Must |
| 11 | `HU-10` | Bloqueo de un producto puntual | EPI-3 | USR-2 | Must |
| 12 | `HU-11` | Bloqueo por alérgeno | EPI-3 | USR-2 | Must |
| 13 | `HU-13` | Restricciones no desactivables | EPI-3 | USR-2 | Must |
| 14 | `HU-14` | Código de tarjeta aleatorio | EPI-4 | USR-1 | Must |
| 15 | `HU-15` | Identificación por escaneo | EPI-4 | USR-3 | Must |
| 16 | `HU-17` | Vista de cobro | EPI-5 | USR-3 | Must |
| 17 | Fotografía visible al cobrar | EPI-11 | USR-3 | Must |
| 18 | `HU-21` | Descuento simultáneo saldo + existencias | EPI-5 | USR-4 | Must |
| 19 | `HU-18` | Venta rechazada por alérgeno (`TST-1`) | EPI-5 | USR-2 | Must |
| 20 | `HU-19` | Venta rechazada por saldo (`TST-2`) | EPI-5 | USR-2 | Must |
| 21 | `HU-20` | Venta rechazada por límite diario (`TST-2`) | EPI-5 | USR-2 | Must |
| 22 | `HU-22` | Información nutricional congelada en la venta | EPI-5 | USR-2 | Must |
| 23 | `HU-27` | Ingreso de mercancía por ajuste manual | EPI-7 | USR-4 | Must |
| 24 | `HU-28` | Merma con motivo obligatorio | EPI-7 | USR-4 | Must |
| 25 | `HU-29` | Existencias explicables (`TST-4`) | EPI-7 | USR-4 | Must |
| 26 | `HU-30` | Historial de consumo | EPI-8 | USR-2 | Must |
| 27 | `HU-34` | Aviso de carácter orientativo | EPI-8 | USR-2 | Must |
| 28 | `HU-38` | Consulta de restricciones por los cuatro roles | EPI-8 | USR-3/4/5 | Must |
| 29 | `HU-39` | Alta de la institución por seed | EPI-9 | USR-5 | Must |
| 30 | `HU-40` | Alta de cuentas de cajero y administrador | EPI-9 | USR-5 | Must |
| 31 | `HU-41` | Contraseña por invitación para el personal | EPI-9 | USR-3/4 | Must |
| 32 | `HU-43` | Código de tarjeta asignado en la carga | EPI-10 | USR-5 | Must |
| 33 | `HU-44` | Vista de administración de estudiantes | EPI-10 | USR-5 | Must |
| 34 | Fotografía del estudiante | EPI-10 | USR-5 | Must |
| 35 | `HU-45` | Consulta del código de tarjeta vigente | EPI-10 | USR-5 | Must |
| 36 | `HU-46` | Reasignación del código de tarjeta | EPI-10 | USR-5 | Must |
| 37 | `HU-47` | Desactivación por la institución | EPI-10 | USR-5 | Must |
| 38 | `HU-48` | Desactivación por el acudiente | EPI-10 | USR-2 | Must |
| 39 | `HU-49` | Reactivación exclusiva de la institución | EPI-10 | USR-5 | Must |
| 40 | `HU-50` | Venta rechazada por estudiante desactivado | EPI-10 | USR-2 | Must |
| 41 | `HU-53` | Venta a cliente genérico | EPI-11 | USR-3 | Must |
| 42 | `HU-54` | Medio de pago en toda venta | EPI-11 | USR-4 | Must |
| 43 | `HU-23` | Reserva y pago anticipado | EPI-6 | USR-2 | Should |
| 44 | `HU-24` | Consulta de reservas pendientes | EPI-6 | USR-3/4 | Should |
| 45 | `HU-25` | Registro de entrega del pedido | EPI-6 | USR-3 | Should |
| 46 | `HU-16` | Identificación por documento | EPI-4 | USR-3 | Should |
| 47 | `HU-12` | Retiro de una restricción | EPI-3 | USR-2 | Should |
| 48 | `HU-35` | Reporte de ventas | EPI-8 | USR-4 | Should |
| 49 | `HU-36` | Reporte de movimientos de inventario | EPI-8 | USR-4 | Should |
| 50 | `HU-37` | Reporte de auditoría | EPI-8 | USR-4 | Should |
| 51 | `HU-31` | Alertas de frecuencia | EPI-8 | USR-2 | Should |
| 52 | `HU-32` | Comparación con referencia sanitaria | EPI-8 | USR-2 | Should |
| 53 | `HU-33` | Resumen de gasto | EPI-8 | USR-2 | Should |
| 54 | `HU-42` | Desactivación y reactivación de cuentas de personal | EPI-9 | USR-5 | Should |
| 55 | `HU-51` | Baja lógica del estudiante retirado | EPI-10 | USR-5 | Should |
| 56 | `HU-52` | Saldo congelado tras la baja | EPI-10 | USR-2 | Should |
| 57 | `HU-55` | Cierre de caja diario | EPI-11 | USR-3 | Should |
| 58 | `HU-56` | Reporte de cierres de caja | EPI-11 | USR-4 | Should |
| 59 | Imagen del producto | EPI-7 | USR-4 | Should |

**42 Must · 17 Should · 0 Could.** De ellas, **38 provienen del anteproyecto** (`ALC-IN`, `FUN`) y **21 de las decisiones de alcance** (`DEC-1` … `DEC-8`), que todavía no están incorporadas a `[S9.1]`.

Sigue sin haber `Could`: todo lo que quedó dentro del alcance está en la ruta que `ENT-01` exige demostrar o la sostiene.

---

## [S5] Reparto en sprints

Calendario definido por el equipo en su planeación del Entregable 2: **cinco sprints de dos
semanas**, de la semana 6 a la 15. Cumple `CUR-1` (sprints de 1 a 2 semanas) y sitúa los hitos de
`EVA-3` y `EVA-4` justo al cerrar los sprints 2 y 4.

| Sprint | Semanas | Objetivo del Sprint | Historias | Hito |
|---|---|---|---|---|
| 1 | 6 – 7 | Registro, perfiles, vinculación acudiente–estudiante y catálogo | 18 | — |
| 2 | 8 – 9 | Billetera digital e identificación por tarjeta en el POS | 14 | **Avance 1 · sem. 10** (`EVA-3`) |
| 3 | 10 – 11 | Control parental: restricciones, alérgenos, límite de gasto | 12 | — |
| 4 | 12 – 13 | Inventario trazable y pedidos anticipados | 5 | **Avance 2 · sem. 14** (`EVA-4`) |
| 5 | 14 – 15 | Reportes de consumo y ejecución del plan de pruebas | 10 | Entrega final sem. 16 (`EVA-5`) |

Cada hito demuestra lo acumulado: el Avance 1 los sprints 1–2, el Avance 2 los sprints 1–4, y la
entrega final el sistema completo con el plan de pruebas ejecutado.

> **El catálogo (`HU-26`) se adelantó al Sprint 1 y el ingreso de mercancía (`HU-27`) al Sprint 2.**
> Sin productos ni existencias no hay venta que demostrar en el Avance 1. El Sprint 4 conserva su
> valor real —«inventario **trazable**», que son `HU-28` y `HU-29`— y por eso su título ya no dice
> «catálogo». **La diapositiva de la planeación hay que actualizarla en consecuencia.**

**El orden dentro de cada sprint es de construcción, no de prioridad.** Cada historia va después de
todo aquello que la bloquea. La columna «Depende de» lo hace explícito: una historia no puede
empezarse hasta que las suyas estén terminadas. `[ANEXO D]` verifica que no haya ninguna dependencia
hacia adelante.

### Sprint 1 · semanas 6–7 — Registro, perfiles, vinculación y catálogo

**18 historias.** Al cerrar existe una institución que da de alta personal y estudiantes, cada estudiante tiene su código de tarjeta y su fotografía, cada acudiente su cuenta, y la cafetería su catálogo de productos con sus imágenes.

| # | ID | Historia | Depende de | Prioridad |
|---|---|---|---|---|
| 1 | `HU-39` | Alta de la institución educativa por seed | — | Must |
| 2 | `HU-05` | Autorregistro bloqueado | — | Must |
| 3 | `HU-40` | Alta de cuentas de cajero y administrador | `HU-39` | Must |
| 4 | `HU-41` | Contraseña por invitación para el personal | `HU-40` | Must |
| 5 | `HU-42` | Desactivación y reactivación de cuentas de personal | `HU-40` | Should |
| 6 | `HU-01` | Carga masiva de estudiantes y acudientes | `HU-39` | Must |
| 7 | `HU-02` | Validación del archivo antes de escribir | `HU-01` | Must |
| 8 | `HU-03` | Invitación por correo y definición de contraseña | `HU-01` | Must |
| 9 | `HU-04` | Acudiente con varios estudiantes a cargo | `HU-01`, `HU-03` | Must |
| 10 | `HU-14` | Generación aleatoria del código de la tarjeta | — | Must |
| 11 | `HU-43` | Código de tarjeta asignado en la carga | `HU-01`, `HU-14` | Must |
| 12 | `HU-44` | Vista de administración de estudiantes | `HU-01` | Must |
| 13 | `HU-45` | Consulta del código de tarjeta vigente | `HU-43`, `HU-44` | Must |
| 14 | `HU-46` | Reasignación del código de tarjeta | `HU-43`, `HU-45` | Must |
| 15 | `HU-57` | Fotografía del estudiante | `HU-44` | Must |
| 16 | `HU-51` | Baja lógica del estudiante retirado | `HU-44` | Should |
| 17 | `HU-26` | Administración del catálogo | — | Must |
| 18 | `HU-59` | Imagen del producto | `HU-26` | Should |

`HU-05` va en segundo lugar porque es la regla que gobierna toda creación de cuenta: se implementa
con el módulo de cuentas, no se verifica al final. `HU-26` no depende de nada del resto del sprint
y puede desarrollarse **en paralelo** desde el primer día.

### Sprint 2 · semanas 8–9 — Billetera digital e identificación por tarjeta en el POS

**14 historias.** Al cerrar se recarga una billetera, se identifica al estudiante con su tarjeta —viendo su fotografía— y se le cobra descontando saldo y existencias. Es lo que se demuestra en el **Avance 1**.

| # | ID | Historia | Depende de | Prioridad |
|---|---|---|---|---|
| 1 | `HU-06` | Recarga de la billetera | `HU-03` | Must |
| 2 | `HU-08` | Saldo reconstruible desde el historial (`TST-3`) | `HU-06` | Must |
| 3 | `HU-07` | Consulta de saldo por el acudiente | `HU-06`, `HU-08` | Must |
| 4 | `HU-52` | Saldo congelado y consultable tras la baja | `HU-51`, `HU-06` | Should |
| 5 | `HU-27` | Ingreso de mercancía por ajuste manual | `HU-26` | Must |
| 6 | `HU-15` | Identificación por escaneo de la tarjeta | `HU-43` | Must |
| 7 | `HU-16` | Identificación alternativa por documento | `HU-01` | Should |
| 8 | `HU-17` | Vista de cobro con saldo, consumo y restricciones | `HU-15`, `HU-16`, `HU-07`, `HU-26` | Must |
| 9 | `HU-58` | Fotografía visible al cobrar | `HU-17`, `HU-57` | Must |
| 10 | `HU-54` | Medio de pago en toda venta | `HU-17` | Must |
| 11 | `HU-21` | Descuento simultáneo de saldo y existencias | `HU-17`, `HU-27`, `HU-54` | Must |
| 12 | `HU-22` | Venta con información nutricional congelada | `HU-21`, `HU-26` | Must |
| 13 | `HU-19` | Venta rechazada por saldo insuficiente (`TST-2`) | `HU-21` | Must |
| 14 | `HU-53` | Venta a cliente genérico | `HU-21`, `HU-54` | Must |

`HU-08` va antes que `HU-07` a propósito: el saldo se deriva del historial (`INV-2`), así que el
libro de movimientos se construye antes que la pantalla que lo muestra. `HU-54` va **antes** que la
venta: el medio de pago es un campo del asiento, y añadirlo después obliga a reescribir
transacciones ya registradas.

### Sprint 3 · semanas 10–11 — Control parental: restricciones, alérgenos, límite de gasto

**12 historias.** Al cerrar, el acudiente controla qué y cuánto consume su hijo y el punto de venta lo hace cumplir. Incluye el bloqueo de la tarjeta perdida, que es control parental ejercido sobre el acceso.

| # | ID | Historia | Depende de | Prioridad |
|---|---|---|---|---|
| 1 | `HU-09` | Límite diario de gasto | `HU-06` | Must |
| 2 | `HU-10` | Bloqueo de un producto puntual | `HU-26` | Must |
| 3 | `HU-11` | Bloqueo por alérgeno | `HU-26` | Must |
| 4 | `HU-12` | Retiro de una restricción | `HU-10`, `HU-11` | Should |
| 5 | `HU-13` | Restricciones no desactivables por la cafetería | `HU-10`, `HU-11`, `HU-17` | Must |
| 6 | `HU-38` | Consulta de restricciones por los cuatro roles | `HU-10`, `HU-11` | Must |
| 7 | `HU-18` | Venta rechazada por alérgeno bloqueado (`TST-1`) | `HU-11`, `HU-21` | Must |
| 8 | `HU-20` | Venta rechazada por límite diario superado (`TST-2`) | `HU-09`, `HU-21` | Must |
| 9 | `HU-47` | Desactivación de un estudiante por la institución | `HU-44` | Must |
| 10 | `HU-48` | Desactivación de un estudiante por el acudiente | `HU-47` | Must |
| 11 | `HU-49` | Reactivación exclusiva de la institución | `HU-47`, `HU-48` | Must |
| 12 | `HU-50` | Venta rechazada por estudiante desactivado | `HU-47`, `HU-21` | Must |

Las restricciones se configuran (`HU-09` … `HU-13`) antes de hacerse cumplir (`HU-18`, `HU-20`,
`HU-50`): no se puede probar un rechazo sin una regla que lo dispare. `HU-48` va después de `HU-47`
porque comparte el mismo estado del estudiante; lo que cambia es quién puede tocarlo.

### Sprint 4 · semanas 12–13 — Inventario trazable y pedidos anticipados

**5 historias.** Al cerrar, las existencias se explican desde su historial y funcionan los pedidos anticipados. Es lo que se suma en el **Avance 2**.

| # | ID | Historia | Depende de | Prioridad |
|---|---|---|---|---|
| 1 | `HU-28` | Registro de merma con motivo obligatorio | `HU-27` | Must |
| 2 | `HU-29` | Existencias explicables desde el historial (`TST-4`) | `HU-27`, `HU-28`, `HU-21` | Must |
| 3 | `HU-23` | Reserva y pago anticipado | `HU-06`, `HU-26` | Should |
| 4 | `HU-24` | Consulta de reservas pendientes | `HU-23` | Should |
| 5 | `HU-25` | Registro de la entrega del pedido | `HU-23`, `HU-24`, `HU-21` | Should |

Es el sprint más ligero de los cinco: el catálogo y el ingreso de mercancía se adelantaron, y lo que
queda es la trazabilidad del inventario más los pedidos anticipados. Ese margen es deliberado —
absorbe el retraso acumulado antes del Avance 2, que vale el 20 % (`EVA-4`).

### Sprint 5 · semanas 14–15 — Reportes de consumo y ejecución del plan de pruebas

**10 historias.** Al cerrar, el acudiente ve el consumo con recomendaciones y la cafetería tiene sus reportes. En paralelo se ejecutan los cuatro escenarios críticos `TST-1` … `TST-4` de `ENT-05`.

| # | ID | Historia | Depende de | Prioridad |
|---|---|---|---|---|
| 1 | `HU-30` | Historial de consumo para el acudiente | `HU-22` | Must |
| 2 | `HU-31` | Alertas de frecuencia de consumo | `HU-30` | Should |
| 3 | `HU-34` | Aviso de carácter orientativo | `HU-31` | Must |
| 4 | `HU-32` | Comparación con valores de referencia | `HU-31` | Should |
| 5 | `HU-33` | Resumen de gasto frente a saldo recargado | `HU-30`, `HU-06` | Should |
| 6 | `HU-35` | Reporte de ventas | `HU-21`, `HU-53`, `HU-54` | Should |
| 7 | `HU-36` | Reporte de movimientos de inventario | `HU-27`, `HU-28`, `HU-29` | Should |
| 8 | `HU-55` | Cierre de caja diario | `HU-54`, `HU-53` | Should |
| 9 | `HU-56` | Reporte de cierres de caja | `HU-55` | Should |
| 10 | `HU-37` | Reporte de auditoría | `HU-35`, `HU-36`, `HU-56` | Should |

`HU-34` va en tercer lugar, no al final: `INV-9` exige que el aviso de que las recomendaciones son
orientativas esté presente **desde la primera recomendación publicada**, no cuando se acaben todas.
`HU-37` cierra el sprint porque la auditoría consolida los tres reportes anteriores.

**Reparto: 18 + 14 + 12 + 5 + 10 = 59 historias.** Ninguna sin sprint, ninguna en dos.

## [ANEXO A] Trazabilidad alcance → historias

Cobertura de los 22 elementos del alcance incluido y de las 7 funciones del prototipo. Sirve para comprobar que ninguna historia se inventó y que ningún elemento del alcance quedó sin cubrir.

| Origen | Historias que lo cubren |
|---|---|
| `ALC-IN-01` Carga de estudiantes | `HU-01` |
| `ALC-IN-02` Validación previa | `HU-02` |
| `ALC-IN-03` Invitación por correo | `HU-03` |
| `ALC-IN-04` Perfiles vinculados | `HU-01`, `HU-04` |
| `ALC-IN-05` Restricción del autorregistro | `HU-05` |
| `ALC-IN-06` Billetera individual | `HU-06`, `HU-07`, `HU-04` |
| `ALC-IN-07` Límite diario | `HU-09`, `HU-20` |
| `ALC-IN-08` Restricciones alimentarias | `HU-10`, `HU-11` |
| `ALC-IN-09` Restricciones aplicadas en la venta | `HU-13`, `HU-17`, `HU-18` |
| `ALC-IN-10` Pedidos anticipados | `HU-23`, `HU-25` |
| `ALC-IN-11` Prueba del mecanismo de identificación | `HU-15` |
| `ALC-IN-12` Código aleatorio no secuencial | `HU-14` |
| `ALC-IN-13` Escaneo con lector físico | `HU-15` |
| `ALC-IN-14` Validación en tiempo real | `HU-18`, `HU-19`, `HU-20` |
| `ALC-IN-15` Catálogo con nutricional y alérgenos | `HU-26` |
| `ALC-IN-16` Existencias sobre unidades vendibles | `HU-27`, `HU-28` |
| `ALC-IN-17` Descuento simultáneo | `HU-21` |
| `ALC-IN-18` Motivo obligatorio en disminución manual | `HU-28` |
| `ALC-IN-19` Registro histórico de movimientos | `HU-08`, `HU-21`, `HU-29`, `HU-12`, `HU-36` |
| `ALC-IN-20` Historial de consumo con nutricional | `HU-30`, `HU-22` |
| `ALC-IN-21` Recomendaciones determinísticas | `HU-31`, `HU-32`, `HU-33`, `HU-34` |
| `ALC-IN-22` Reportes de la administración | `HU-35`, `HU-36`, `HU-37` |
| `FUN-1` Vinculación bajo control institucional | `HU-01`, `HU-02`, `HU-03`, `HU-04`, `HU-05` |
| `FUN-2` Saldo y límites | `HU-06`, `HU-09`, `HU-19` |
| `FUN-3` Restricciones alimentarias | `HU-10`, `HU-11`, `HU-13` |
| `FUN-4` Identificación y cobro | `HU-14`, `HU-15`, `HU-16`, `HU-17`, `HU-21` |
| `FUN-5` Pedidos anticipados | `HU-23`, `HU-24`, `HU-25` |
| `FUN-6` Catálogo e inventario | `HU-26`, `HU-27`, `HU-28`, `HU-29` |
| `FUN-7` Reportes y recomendaciones | `HU-30`, `HU-31`, `HU-32`, `HU-33`, `HU-34`, `HU-35`, `HU-36`, `HU-37` |

**Cobertura del anteproyecto: 22/22 elementos de `[S9.1]` y 7/7 funciones de `[S10.2]`.**

Cobertura de las decisiones de alcance (`./decisiones-de-alcance.md`):

| Origen | Historias que lo cubren |
|---|---|
| `DEC-1` Venta a cliente genérico y medios de pago | `HU-53`, `HU-54` |
| `DEC-2` Cuentas de personal creadas por la institución | `HU-40`, `HU-42` |
| `DEC-3` Acceso por invitación para todos los roles | `HU-39`, `HU-41` |
| `DEC-4` Código de tarjeta y vista de administración | `HU-43`, `HU-44`, `HU-45`, `HU-46` |
| `DEC-5` Desactivación asimétrica del estudiante | `HU-47`, `HU-48`, `HU-49`, `HU-50` |
| `DEC-6` Cierre de caja diario | `HU-55`, `HU-56` |
| `DEC-7` Baja lógica con saldo congelado | `HU-51`, `HU-52` |
| `DEC-8` Fotografía del estudiante e imagen del producto | `HU-57`, `HU-58`, `HU-59` |

**Cobertura de decisiones: 8/8.** Ninguna historia carece de origen.

Invariantes y su historia guardiana:

| Invariante | Historia |
|---|---|
| `INV-1` Sin saldo negativo | `HU-19` |
| `INV-2` Saldo reconstruible | `HU-08` |
| `INV-3` Existencias explicables | `HU-29` |
| `INV-4` Restricciones no desactivables | `HU-13`, `HU-38` |
| `INV-5` Bloqueo por condición, no por lista | `HU-11` |
| `INV-6` Sin autorregistro | `HU-05` |
| `INV-7` Código aleatorio | `HU-14` |
| `INV-8` Motivo obligatorio | `HU-28` |
| `INV-9` Recomendaciones orientativas | `HU-34` |

Invariantes derivadas de las decisiones:

| Invariante | Historia |
|---|---|
| `INVD-1` Ninguna cuenta se crea por autorregistro | `HU-39`, `HU-40`, `HU-41` |
| `INVD-2` Estudiante desactivado o de baja no puede comprar | `HU-50` |
| `INVD-3` Solo la institución reactiva | `HU-49` |
| `INVD-4` Reasignar código invalida el anterior | `HU-46` |
| `INVD-5` Efectivo esperado explicable desde las ventas | `HU-55`, `HU-56` |
| `INVD-6` Ninguna fotografía corresponde a una persona real | `HU-57` |

---

## [ANEXO B] Vacíos detectados

> **Estado: los seis vacíos están resueltos.** El equipo los cerró el 2026-08-28 con las decisiones `DEC-1` … `DEC-6` de `./decisiones-de-alcance.md`, y de ahí salieron 16 de las 18 historias nuevas de esta versión. Las otras dos (`HU-51`, `HU-52`) vienen de `DEC-7`, que responde a una pregunta abierta que este análisis destapó.
>
> **Los `VAC-n` se conservan con su descripción original**, no se borran: son identificadores citables y el registro de que el anteproyecto tenía estos huecos sigue siendo información útil —para el informe final (`ENT-06`) y para la próxima versión de `./smartfood.md`. Cada uno lleva ahora su resolución.

Funciones que el prototipo necesitará y que **ninguna sección del anteproyecto declaraba**. En la versión 1.0 de este backlog no se escribieron historias para ellas, porque hacerlo habría sido introducir requisitos nuevos.

#### `[VAC-1]` Ventas a consumidores sin vínculo estudiantil

`[S5]` define `USR-6` (docentes, personal, visitantes) y afirma que **sus transacciones también deben registrarse**, porque forman parte de las ventas totales y son necesarias para el cierre de caja y los reportes diarios. Pero **ningún `ALC-IN` cubre la venta sin perfil de estudiante**, y `USR-6` no aparece en la matriz de permisos `S11`.

Era la contradicción más seria del anteproyecto: un usuario declarado con una necesidad explícita, sin alcance que la respalde.

**Resuelto por `DEC-1`** → `HU-53`, `HU-54`. El punto de venta emite ventas a cliente genérico, pagadas en efectivo o por transferencia, y toda venta registra su medio de pago. `OBJ-GEN` ya acotaba la sustitución del efectivo a «una cuenta digital **por estudiante**», así que no hay contradicción con el objetivo.

#### `[VAC-2]` Creación de las cuentas de cajero y administrador

`ALC-IN-01` cubre la carga de **estudiantes y acudientes**. La matriz `S11` da permisos a `USR-3` (cajero) y `USR-4` (administrador), pero **nadie crea esas cuentas** en todo el alcance. Con `ALC-IN-05` prohibiendo el autorregistro, no existía camino documentado para que un cajero llegara a tener acceso al sistema.

**Resuelto por `DEC-2`** → `HU-40`, `HU-42`. Las crea la institución educativa, que también puede desactivarlas y reactivarlas.

#### `[VAC-3]` Autenticación de cajero, administrador e institución

`ALC-IN-03` describe cómo el **acudiente** define su contraseña. No hay equivalente para los otros tres roles. El sistema tenía una matriz de permisos por rol sin un mecanismo de acceso declarado para tres de sus cuatro roles.

**Resuelto por `DEC-3`** → `HU-39`, `HU-41`. La institución nace del seed y el personal del alta que ella hace; en los tres casos el acceso se establece por invitación por correo, igual que ya hacía el acudiente.

#### `[VAC-4]` Vinculación de la tarjeta física con el estudiante

`ALC-IN-12` cubre la **generación** del código y `ALC-OUT-04` excluye la producción masiva de tarjetas. Pero el acto de **asociar una tarjeta concreta a un estudiante concreto** —quién lo hace y desde qué interfaz— no está declarado. `ENT-02` exige demostrar la prueba de concepto con tarjetas reales, así que alguien tenía que ejecutarlo.

**Resuelto por `DEC-4`** → `HU-43`, `HU-44`, `HU-45`, `HU-46`. El código se asigna al cargar al estudiante, y la institución dispone de una vista donde consultarlo, reasignarlo y administrar estudiantes uno a uno.

#### `[VAC-5]` Pérdida, bloqueo o reposición de tarjeta

`FUN-4` dice que la tarjeta «opera como una credencial de acceso al saldo». Una credencial perdida es un riesgo directo sobre el dinero del estudiante, y no había nada en el alcance sobre bloquearla o reponerla.

**Resuelto por `DEC-5`** (bloqueo) y `DEC-4` (reposición) → `HU-46`, `HU-47`, `HU-48`, `HU-49`, `HU-50`. Institución y acudiente pueden desactivar; solo la institución reactiva.

#### `[VAC-6]` Cierre de caja

`[S5]` menciona el cierre de caja como justificación de por qué deben registrarse las ventas de `USR-6`, y `FIG-03` sitúa el «ajuste de caja» dentro del subsistema de la cafetería. Pero no hay `ALC-IN` de cierre de caja ni fila en `S11`. `ALC-IN-22` cubre reportes de ventas, que no es lo mismo.

**Resuelto por `DEC-6`** → `HU-55`, `HU-56`. Cuadre diario contra ventas registradas, sin apertura de turno. Adquirió urgencia al resolverse `VAC-1`: la venta a cliente genérico devuelve efectivo a la caja.

> **Puntos que siguen abiertos** tras estas decisiones —devolución del saldo congelado, notificación al acudiente, respaldo bibliográfico de la justificación de `DEC-1`, pedidos anticipados de un estudiante desactivado y alcance del seed— están registrados en el `ANEXO B` de `./decisiones-de-alcance.md`. Ninguno bloquea la construcción del prototipo.

---

## [ANEXO C] Nota de procedencia

Documento producido por el equipo el 2026-08-28. No reexpresa ningún original: es material derivado de las versiones estructuradas del corpus.

**Versión 2.1** — añade `HU-57`, `HU-58` y `HU-59`, derivadas de `DEC-8`. La 2.0 tenía 38 historias derivadas únicamente del anteproyecto y seis vacíos sin resolver. La 2.0 añade 18 historias (`HU-39` … `HU-56`) que derivan de `./decisiones-de-alcance.md`, el registro de las decisiones con que el equipo cerró esos vacíos. Las 38 historias originales **no se modificaron ni se renumeraron**.

Las 38 historias se obtuvieron recorriendo exhaustivamente `[S9.1]` (`ALC-IN-01` … `ALC-IN-22`) y `[S10.2]` (`FUN-1` … `FUN-7`) de `./smartfood.md`, reexpresando cada elemento del alcance desde el punto de vista del usuario que recibe su valor, según la plantilla de `D07` de `corpus:semana-5-gestion-de-proyectos-con-metodologias-agiles.md`. Los actores provienen de la tabla `USR-1..6` de `[S5]`; los permisos, de la matriz `[S11]`; las invariantes, del bloque `INV-1..9` de `[S10.2]`; los escenarios críticos, de `TST-1..4`.

**Ninguna historia introduce requisitos, cifras ni restricciones que no estén en el anteproyecto.** El `ANEXO A` permite comprobarlo elemento por elemento. Lo que la documentación no cubre se registró como vacío en el `ANEXO B` en vez de completarse por inferencia.

La única excepción declarada es `[S5]`, la agrupación en sprints, marcada `[PROPUESTA]`: es una decisión del equipo y no se deriva del anteproyecto. Su único parámetro documentado es la duración de sprint de 1 a 2 semanas (`CUR-1`).

**Nota sobre Scrum:** la Guía de Scrum 2020 (`corpus:guia-de-scrum-2020.md`) **no define las historias de usuario** como parte de Scrum; son una práctica complementaria, tal como advierte la regla 5 de su `[S0.2]`. Lo que sí es normativo es el **Product Backlog** (`ART-1`) y el **Objetivo del Producto** (`COM-1`). Este documento es el Product Backlog del proyecto, expresado en el formato de historia que enseña la asignatura.

---

## [ANEXO D] Verificación del orden de construcción

El grafo de dependencias de las 56 historias se comprobó por script sobre el orden de `[S5]`:

| Comprobación | Resultado |
|---|---|
| Historias colocadas | 59 de 59, ninguna repetida |
| Historias antes de algo de lo que dependen | **0** |
| Dependencias que cruzan de sprint hacia adelante | **0** |

Las dependencias entre sprints —todas hacia atrás— son:

| Historia | Sprint | Depende de | Sprint |
|---|---|---|---|
| `HU-06` Recarga | 2 | `HU-03` Invitación al acudiente | 1 |
| `HU-27` Ingreso de mercancía | 2 | `HU-26` Catálogo | 1 |
| `HU-15` Identificación por escaneo | 2 | `HU-43` Código en la carga | 1 |
| `HU-16` Identificación por documento | 2 | `HU-01` Carga masiva | 1 |
| `HU-17` Vista de cobro | 2 | `HU-26` Catálogo | 1 |
| `HU-22` Nutricional congelada | 2 | `HU-26` Catálogo | 1 |
| `HU-52` Saldo congelado tras la baja | 2 | `HU-51` Baja lógica | 1 |
| `HU-58` Fotografía visible al cobrar | 2 | `HU-57` Fotografía del estudiante | 1 |
| `HU-09` Límite diario | 3 | `HU-06` Recarga | 2 |
| `HU-10` Bloqueo de producto | 3 | `HU-26` Catálogo | 1 |
| `HU-11` Bloqueo por alérgeno | 3 | `HU-26` Catálogo | 1 |
| `HU-13` Restricciones no desactivables | 3 | `HU-17` Vista de cobro | 2 |
| `HU-18` Rechazo por alérgeno | 3 | `HU-21` Descuento simultáneo | 2 |
| `HU-20` Rechazo por límite | 3 | `HU-21` Descuento simultáneo | 2 |
| `HU-47` Desactivación por la institución | 3 | `HU-44` Vista de administración | 1 |
| `HU-50` Rechazo por desactivado | 3 | `HU-21` Descuento simultáneo | 2 |
| `HU-28` Merma con motivo | 4 | `HU-27` Ingreso de mercancía | 2 |
| `HU-29` Existencias explicables | 4 | `HU-21`, `HU-27` | 2 |
| `HU-23` Reserva anticipada | 4 | `HU-06` Recarga, `HU-26` Catálogo | 2, 1 |
| `HU-25` Entrega del pedido | 4 | `HU-21` Descuento simultáneo | 2 |
| `HU-30` Historial de consumo | 5 | `HU-22` Nutricional congelada | 2 |
| `HU-33` Resumen de gasto | 5 | `HU-06` Recarga | 2 |
| `HU-35` Reporte de ventas | 5 | `HU-21`, `HU-53`, `HU-54` | 2 |
| `HU-36` Movimientos de inventario | 5 | `HU-27`, `HU-28`, `HU-29` | 2, 4 |
| `HU-55` Cierre de caja | 5 | `HU-53`, `HU-54` | 2 |

**Las cuatro historias raíz** —sin ninguna dependencia— son `HU-39` (seed institucional), `HU-05`
(autorregistro bloqueado), `HU-14` (generación del código) y `HU-26` (catálogo). Son los cuatro
frentes por los que puede arrancarse el desarrollo en paralelo en la semana 6.

`HU-57` (fotografía) y `HU-59` (imagen de producto) dependen además del almacenamiento de objetos
(`DT-18` de `./decisiones-tecnicas.md`), que es tarea de habilitación y no una historia.
