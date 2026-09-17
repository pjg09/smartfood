# SmartFood — Plan de Pull Requests del Sprint 3

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-PR-SPRINT3 |
| plan anterior | `./plan-de-pull-requests-sprint-2.md` — cerrado, documento de archivo |
| titulo | Agrupación de las 37 tareas del Sprint 3 en Pull Requests, y estado de cada tarea |
| documentos_fuente | `./sprint-3-backlog.md` (`[S4]`, `[S5]`, `ANEXO C`); `./convenciones-de-git.md` (`[S1]`); `./definicion-de-terminado.md` |
| tipo_documento | Documento derivado de planificación. **No es un artefacto de Scrum** |
| sprint | 3 de 5 · semanas 10 – 11 |
| tareas cubiertas | 43 de 43 (`TT-94` … `TT-136`) |
| pull requests | 16 (`PR-01` … `PR-16`) |
| idioma | es-CO |
| version | 1.3 |

### [S0.1] Qué es este documento y qué no es

`main` está protegida: nada entra por `push` directo (`[S1]` de `./convenciones-de-git.md`).
Este documento responde a una sola pregunta operativa: **¿hasta dónde desarrollo antes de
parar, abrir un PR y seguir?**

**No reordena ni modifica ninguna tarea.** El orden de `./sprint-3-backlog.md` es el orden
de construcción verificado en su `ANEXO C`, y aquí se respeta carácter por carácter. Lo
único que este documento añade son **cortes**.

> **Este es el único sitio donde vive el estado de las tareas.** El sprint backlog es el
> plan y no se toca; el tablero de `TT-128` es la vista de la Daily. Si hay discrepancia,
> manda este documento.

> **Hay un plan por sprint y se conservan todos.** Los del Sprint 1 y 2 están en
> `./plan-de-pull-requests-sprint-1.md` y `./plan-de-pull-requests-sprint-2.md`, cerrados.

---

## [S1] La regla de corte

Todo PR es un **bloque contiguo** del orden del sprint backlog. Sin huecos, sin saltos,
sin adelantar tareas.

De ahí sale la única propiedad que importa, y es demostrable:

> El `ANEXO C` verifica que el orden de las 37 tareas es un orden topológico del grafo de
> dependencias: **ninguna tarea aparece antes de algo que la bloquea**. Si cada PR es un
> bloque contiguo de ese orden, entonces toda dependencia de cualquier tarea de `PR-k`
> está, o en `PR-k`, o en un PR anterior. **Nunca en uno posterior.**

Consecuencia práctica: **integrar los PR en orden numérico no puede romperse.** Al abrir
`PR-k`, `main` ya contiene todo lo que sus tareas necesitan.

Los cortes se eligieron con tres criterios, en este orden:

1. **Un PR cierra algo demostrable.** Un PR que deja una historia a medias no se puede
   enseñar en la Sprint Review.
2. **Un PR se revisa de una sentada.** Entre 1 y 4 tareas. Ninguno pasa de 4.
3. **Un PR no mezcla asuntos.** Las restricciones no viajan con el estado del estudiante
   aunque ambos acaben rechazando ventas.

---

## [S2] Cómo se marca una tarea como finalizada

1. Se cumplen los criterios de la Definición de Terminado que aplican al PR
   (`./definicion-de-terminado.md`). Consultar el estado de `DoD-4` antes del primer PR.
2. El PR se integra en `main` por revisión cruzada, nunca por `push` directo.
3. Se marca `☑` **en los dos documentos**: aquí, en `[S3.1]` y en la tabla del PR, y en
   `./sprint-3-backlog.md`.
4. Si el PR cierra una historia, se marca también en la tabla `[S4]` de
   `./backlog-historias-de-usuario.md`.

> ⚠ **Dos PR de este sprint cierran dos historias cada uno, y los dos están integrados.**
>
> - **`PR-06`**: además de `HU-13`, saldó `HU-17`, que el Sprint 2 dejó abierta.
> - **`PR-09`**: además de `HU-20`, saldó `HU-09`, que `PR-01` dejó con su tercer
>   criterio pendiente —evaluar el límite contra el consumo del día en cada venta es
>   `TT-116`—.
>
> Fueron cuatro marcas en el backlog de historias, no dos. Era la omisión más fácil del
> sprint y por eso queda anotada aquí: quien revise el avance cuenta cuatro.

---

## [S3] Avance del Sprint 3

| | Tareas | Pull Requests |
|---|---|---|
| **Finalizadas** | **33** de 43 | **12** de 16 |
| Pendientes | 10 | 4 |

| Responsable | Finalizadas | Total |
|---|---|---|
| Pedro | 15 | 18 |
| Carlos | 11 | 13 |
| Alejandro | 7 | 9 |
| Naomi | 0 | 3 |

### [S3.1] Estado de los 16 Pull Requests

| PR | Tareas | Qué cierra | Estado |
|---|---|---|---|
| `PR-01` | `TT-94`–`TT-96` | app `restricciones` (`DT-28`) · `HU-09` **salvo su tercer criterio** | ☑ |
| `PR-02` | `TT-97`–`TT-99` | `HU-10` | ☑ |
| `PR-03` | `TT-100`–`TT-103` | `HU-11` · **`INV-5`** | ☑ |
| `PR-04` | `TT-104`–`TT-105` | `HU-12` | ☑ |
| `PR-05` | `TT-106`–`TT-108` | Permisos de `HU-13` · **`INV-4`** | ☑ |
| `PR-06` | `TT-109`–`TT-110` | `HU-13` **y `HU-17`** | ☑ |
| `PR-07` | `TT-111`–`TT-112` | `HU-38` | ☑ |
| `PR-08` | `TT-113`–`TT-115` | `HU-18` · **`TST-1`** | ☑ |
| `PR-09` | `TT-116`–`TT-118` | `HU-20` **y `HU-09`** · **`TST-2`** | ☑ |
| `PR-10` | `TT-119`–`TT-120` | `HU-47` · `DT-29` | ☑ |
| `PR-11` | `TT-121`–`TT-122` | `HU-48` | ☐ |
| `PR-12` | `TT-123`–`TT-124` | `HU-49` · `INVD-3` | ☐ |
| `PR-13` | `TT-125`–`TT-127` | `HU-50` · `INVD-2` | ☐ |
| `PR-14` | `TT-128`–`TT-130` | Gestión del sprint | ☐ |
| `PR-15` | `TT-131`–`TT-133` | `HU-60` · **historia añadida durante el sprint** | ☑ |
| `PR-16` | `TT-134`–`TT-136` | `HU-61` · `DEC-13` · **historia añadida durante el sprint** | ☑ |

---

## [S4] Los 16 Pull Requests

### Configuración del control parental — `PR-01` … `PR-04`

#### `PR-01` — `HU-09` Límite diario de gasto

| | |
|---|---|
| Título del PR | `feat(restricciones): fijar el límite diario de gasto del estudiante` |
| Rama | `feat/TT-94-limite-diario` |
| Responsables | Pedro y Carlos |
| Historia | `HU-09` — **no la cerró**: su tercer criterio es `TT-116`, y la cerró `PR-09` |
| Invariantes | ninguna directamente; habilita `HU-20` |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-94` | App `restricciones` y modelo de límite diario por estudiante | Pedro | ☑ |
| `TT-95` | Servicio para fijar y modificar el límite, solo por el acudiente | Pedro | ☑ |
| `TT-96` | Pantalla del límite diario en la interfaz del acudiente | Carlos | ☑ |

> **Este PR creó una app que `DT-15` no previó**, y la desviación quedó registrada como
> **`DT-28`** en `./decisiones-tecnicas.md`, como se hizo con `DT-24` … `DT-27` en el
> Sprint 2.

> ⚠ **`PR-01` no cierra `HU-09`, y el plan lo daba por hecho.** Cumple sus dos primeros
> criterios —el límite se define por estudiante, y solo su acudiente lo fija o lo
> modifica—, pero el tercero dice «el límite se evalúa contra el consumo del día en cada
> venta», que es la validación dentro del bloqueo de la transacción: `TT-116`, de `PR-09`.
> Es la misma frase que da sentido a `HU-20`. **`HU-09` quedó marcada en
> `./backlog-historias-de-usuario.md` al integrar `PR-09`**, junto con `HU-20`. Fue el
> segundo caso del proyecto tras `HU-17`, y el aviso se conserva porque explica por qué
> una historia del primer PR del sprint se cerró ocho PR más tarde.

---

#### `PR-02` — `HU-10` Bloqueo de un producto puntual

| | |
|---|---|
| Título del PR | `feat(restricciones): bloquear un producto del catálogo` |
| Rama | `feat/TT-97-bloqueo-de-producto` |
| Responsables | Pedro y Carlos |
| Historia | `HU-10` — **cerrada** |
| Invariantes | ninguna |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-97` | Modelo de restricción por producto, distinto del de alérgeno | Pedro | ☑ |
| `TT-98` | Servicio de bloqueo y desbloqueo de un producto | Pedro | ☑ |
| `TT-99` | Selección de productos a bloquear en la interfaz del acudiente | Carlos | ☑ |

Los dos tipos de restricción se modelan **por separado**. Unificarlos en una tabla con un
campo «tipo» invita a implementar el alérgeno como lista de productos, que es lo que
`INV-5` prohíbe y lo que `PR-03` tiene que evitar.

> ⚠ **Hallazgo de este PR: ninguna historia rechaza una venta por producto bloqueado.**
> `HU-10` cierra —sus dos criterios se cumplen y ninguno habla de la venta—, pero
> `ALC-IN-09` pide aplicar las restricciones **en el momento de la venta** y no hay
> historia que lo haga para esta lista: las cuatro de rechazo son `HU-18` (alérgeno),
> `HU-19` (saldo), `HU-20` (límite) y `HU-50` (desactivado). Queda declarado en el
> `ANEXO A` del sprint backlog, punto 5, para que lo resuelva la Sprint Review. **No se
> corrige en un PR**: crear una historia es alcance.

---

#### `PR-03` — `HU-11` Bloqueo por alérgeno

| | |
|---|---|
| Título del PR | `feat(restricciones): bloquear un alérgeno sobre la condición` |
| Rama | `feat/TT-100-bloqueo-por-alergeno` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-11` — **cerrada** |
| Invariantes | **`INV-5`** |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-100` | Modelo de restricción por alérgeno, sobre la condición y no sobre una lista | Pedro | ☑ |
| `TT-101` | Servicio de bloqueo y desbloqueo de un alérgeno | Pedro | ☑ |
| `TT-102` | Selección de alérgenos a bloquear en la interfaz del acudiente | Carlos | ☑ |
| `TT-103` | Caso de prueba: producto creado **después** del bloqueo queda cubierto | Alejandro | ☑ |

> 🔴 **El PR de mayor riesgo del sprint.** `INV-5` exige que el bloqueo se aplique sobre el
> alérgeno, de modo que cubra productos futuros. La comprobación es un cruce con la tabla
> `ProductoAlergeno` que ya existe. **Si alguien materializa la lista de productos
> bloqueados —porque consulta más rápido— `INV-5` se rompe y no se nota hasta que la
> cafetería añade un producto nuevo.**
>
> `TT-103` es la red: crea el producto **después** de la restricción. Revisad `TT-100` con
> esa prueba delante.

**Cómo quedó.** `RestriccionAlergeno` tiene **dos columnas y ninguna más**: estudiante y
alérgeno. Qué productos cubre no es un dato, es el resultado de
`productos_cubiertos_por_alergeno`, que cruza con `ProductoAlergeno` en cada llamada. El
servicio no recorre el catálogo ni escribe una sola `RestriccionProducto` — hay prueba que
lo afirma contando filas. `TT-103` ejercita los tres caminos por los que la
materialización se notaría: producto creado después, producto que declara el alérgeno
después, y declaración retirada.

---

#### `PR-04` — `HU-12` Retiro de una restricción

| | |
|---|---|
| Título del PR | `feat(restricciones): retirar una restricción dejando asiento` |
| Rama | `feat/TT-104-retiro-de-restriccion` |
| Responsables | Pedro y Carlos |
| Historia | `HU-12` — **cerrada** |
| Invariantes | `ALC-IN-19`: el retiro se asienta |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-104` | Servicio de retiro que deja asiento auditable | Pedro | ☑ |
| `TT-105` | Acción de retirar en la interfaz del acudiente | Carlos | ☑ |

El retiro se asienta porque es una acción sobre la seguridad alimentaria de un menor:
tiene que poder reconstruirse quién la hizo y cuándo.

**Cómo quedó.** `AsientoDeRestriccion` es un libro más, con el patrón de `DT-24`: un único
`_asentar` por el que pasan los cuatro servicios. Entra en la misma transacción que el
cambio que anota —o quedan los dos o no queda ninguno— y guarda el nombre tal como estaba
(`DT-8`), para que renombrar el catálogo no reescriba el pasado.

**Anota también el bloqueo, y el criterio solo pedía el retiro.** Es una decisión
declarada: un registro con solo los retiros no reconstruye nada. «Se retiró el bloqueo de
maní el día 3» no dice si el niño estuvo protegido antes ni desde cuándo, que es justo la
pregunta que una auditoría trae.

`TT-105` no añadió la acción de retirar —ya existía como el interruptor de `TT-99` y
`TT-102`—, sino **lo que faltaba para que fuera auditable**: el historial visible en las
dos pantallas, dentro del fragmento que HTMX intercambia para que no se quede desfasado.

---

### Aplicación y consulta — `PR-05` … `PR-07`

#### `PR-05` — Permisos de `HU-13`

| | |
|---|---|
| Título del PR | `feat(restricciones): impedir que la cafetería toque las restricciones` |
| Rama | `feat/TT-106-permisos-de-restricciones` |
| Responsables | Pedro y Alejandro |
| Historia | `HU-13` — **no la cierra**, la cierra `PR-06` |
| Invariantes | **`INV-4`** |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-106` | Selector de las restricciones vigentes de un estudiante | Pedro | ☑ |
| `TT-107` | Permisos: ni cajero, ni administración, ni institución escriben restricciones | Pedro | ☑ |
| `TT-108` | Caso de prueba: los tres roles no tienen escritura sobre restricciones | Alejandro | ☑ |

`INV-4` se sostiene **en la capa de datos**, con permisos por modelo (`DT-11`). Ocultar el
botón en la plantilla no es cumplirla, es aparentarlo: `TT-108` llama al servicio con cada
rol, no mira la pantalla.

**Cómo quedó.** Dieciocho puertas comprobadas —seis servicios por tres roles— y, además del
`PermissionDenied` de cada una, que **lo configurado sigue en pie** después de intentarlo:
es lo que `HU-13` le promete al acudiente. La prohibición del admin se declara ahora **por
prefijo de app** y no por lista de modelos, así que un modelo nuevo dentro de
`restricciones` queda cubierto sin que nadie se acuerde de añadirlo.

> **Hallazgo de `TT-107`, con su tamaño exacto.** `ESCRITURA_PROHIBIDA` solo declaraba los
> dos roles de la cafetería. `INV-4` dice «ni el personal de la cafetería **ni la
> institución**» y el tercer criterio de `HU-13` lo repite. **Nada estuvo nunca expuesto**:
> la institución no tenía permiso sobre esos modelos, que además no existían hasta este
> sprint. Lo que faltaba era la declaración que lo habría detectado si alguien se lo
> concediera.

**La prueba negativa se verificó introduciendo la violación a propósito**: con un permiso
de `change` sobre `restricciones.limitediario` concedido al cajero, fallan tres pruebas.
Sin esa comprobación, una prueba que exige una ausencia pasa sola el día que deja de
proteger.

---

#### `PR-06` — `HU-13` y **`HU-17`**

| | |
|---|---|
| Título del PR | `feat(pos): mostrar las restricciones vigentes en el panel de cobro` |
| Rama | `feat/TT-109-restricciones-al-cobrar` |
| Responsables | Carlos y Alejandro |
| Historias | `HU-13` **y `HU-17`** — **las dos cerradas** |
| Invariantes | `INV-4` |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-109` | Bloque de restricciones vigentes en el panel de cobro | Carlos | ☑ |
| `TT-110` | Caso de prueba: `HU-17` completa — saldo, consumo del día y restricciones | Alejandro | ☑ |

> ⚠ **Salda la deuda del Sprint 2.** `HU-17` quedó abierta porque su tercer criterio exige
> mostrar las restricciones vigentes y no existían. Este PR añade ese bloque al panel que
> construyó `TT-75`. **Al integrarlo hay que marcar DOS historias** en
> `./backlog-historias-de-usuario.md`: `HU-13` y `HU-17`. Es el error más fácil de cometer
> en todo el sprint.

El cajero **ve** las restricciones y no dispone de ninguna acción para desactivarlas. Lo
segundo ya lo garantiza `PR-05` en la capa de datos.

**Cómo quedó.** El bloque nombra cada restricción —un recuento no sirve en una caja: el
cajero necesita saber cuál— y dice, por línea, **si la caja la hace cumplir**. Cuando se
escribió, la caja solo rechazaba el producto bloqueado (`HU-60`), así que el alérgeno y el
cupo llevaban una marca temporal: un cajero que crea que el sistema frena el maní puede
vender el maní. **Las dos marcas se retiraron**, con `PR-08` y `PR-09`, y las pruebas que
las exigían ahora exigen su ausencia.

Y una frase que cambió de signo: hasta este PR la pantalla **no podía** escribir «sin
restricciones», porque el sistema no guardaba ninguna y eso habría sido «no sé»
disfrazado de «no tiene». Con las tres tablas existiendo, es una afirmación que la base
sostiene — la prueba del Sprint 2 que exigía lo contrario se invirtió, con su motivo
escrito.

---

#### `PR-07` — `HU-38` Consulta por los cuatro roles

| | |
|---|---|
| Título del PR | `feat(restricciones): permitir consultar las restricciones a los cuatro roles` |
| Rama | `feat/TT-111-consulta-de-restricciones` |
| Responsables | Pedro y Carlos |
| Historia | `HU-38` — **cerrada** |
| Invariantes | `INV-4`, matriz `S11` |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-111` | Consulta habilitada a los cuatro roles, sobre el selector de `TT-106` | Pedro | ☑ |
| `TT-112` | Consulta de restricciones en la interfaz administrativa | Carlos | ☑ |

`HU-38` y `HU-13` son las dos caras de la misma fila de `S11`: los cuatro **consultan**,
solo el acudiente **configura**.

**Cómo quedó.** Dos de los cuatro roles ya consultaban antes de este PR: el acudiente en
su panel (`TT-99`, `TT-102`) y el cajero al identificar (`TT-109`). Lo que faltaba era la
administración de la cafetería y la institución, que trabajan en el admin (`DT-2`) y no
tenían dónde verlas. Ahora tienen *Restricciones por estudiante*: el listado con el
límite, los productos y los alérgenos bloqueados de cada uno, y su ficha.

**Es un proxy de `Estudiante` cuyo único permiso es `view`** (`default_permissions`).
Django no crea `add_`, `change_` ni `delete_` para él, así que no hay permiso de escritura
que conceder por error: la matriz solo puede dar lo que existe (`DT-11`). Las tres tablas
de restricciones siguen **sin registrarse** en el admin. La matriz le da `view` a los dos
roles, el selector `estudiantes_con_sus_restricciones` exige el rol y el `ModelAdmin` lo
repite y niega las tres escrituras: la prueba se verificó quitando las dos
comprobaciones de rol a propósito, y con solo una de ellas el cajero sigue recibiendo
`403`.

**La consulta enseña restricciones, no la ficha del estudiante.** Ni el documento, ni el
código de tarjeta —la credencial del saldo (`FUN-4`)—, ni el acudiente. El documento **se
busca pero no se enseña**, y solo completo: una búsqueda por subcadena dejaría recorrer
documentos tecleando cifras.

> **Hallazgo de este PR: el `__str__` de `Estudiante` lleva el documento.** El admin lo
> pinta en el título y en las migas de la ficha, así que con el proxy tal cual la
> cafetería habría leído el documento del menor en la cabecera de una pantalla que se
> cuida de no enseñarlo en ninguna columna. El proxy tiene su propio `__str__`, y hay
> prueba que falla si se hereda el otro.

Tras integrarlo, **`manage.py sincronizar_permisos`**: sin él, los dos roles reciben `403`
en la consulta nueva y nada indica por qué.

---

### Rechazos en la venta — `PR-08` … `PR-09`

#### `PR-08` — `HU-18` Venta rechazada por alérgeno

| | |
|---|---|
| Título del PR | `feat(ventas): rechazar la venta de un producto con alérgeno bloqueado` |
| Rama | `feat/TT-113-rechazo-por-alergeno` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-18` — **cerrada** |
| Invariantes | `INV-4`, `INV-5` · escenario crítico **`TST-1`** |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-113` | Validación del alérgeno **dentro** del bloqueo de la transacción | Pedro | ☑ |
| `TT-114` | Motivo de rechazo por alérgeno, distinguible en el punto de venta | Carlos | ☑ |
| `TT-115` | Caso de prueba `TST-1`: venta rechazada, sin vía para forzarla | Alejandro | ☑ |

**`TST-1` es el escenario que da sentido al proyecto**: un niño alérgico no puede comprar
lo que le hace daño. La validación va dentro del bloqueo que ya monta `registrar_venta`,
junto a las de saldo y existencias.

El cajero **no tiene** forma de forzar la venta: no es un aviso descartable.

**Cómo quedó, y `INV-5` es lo que decide la forma.** El rechazo no consulta ninguna lista
de productos prohibidos: cruza la condición que el acudiente bloqueó con lo que cada
producto declara, **en el momento de cobrar**. `alergenos_que_bloquean_entre` pregunta
solo por lo que hay en el carrito —un `IN`, una consulta, dentro del bloqueo— y devuelve
la pareja producto–alérgeno, porque el cajero necesita el **porqué**: «contiene maní» es
lo que le deja explicarlo.

De ahí salen las tres pruebas que de verdad vigilan la invariante en la caja: un producto
creado **después** del bloqueo se rechaza, uno que declara el alérgeno después también, y
retirar la declaración devuelve la venta a la normalidad. Con la lista materializada las
tres fallan y el resto del fichero sigue pasando — que es exactamente el fallo silencioso
contra el que avisa `PR-03`.

> **Decisión: el alérgeno se comprueba ANTES que el producto bloqueado.** Un producto
> puede caer por las dos. Cuando pasa, lo que el cajero tiene que poder decir es la
> alergia: «lo bloqueó tu acudiente» invita a pedirle al acudiente que lo quite, y con una
> alergia de por medio esa conversación no puede empezar en la caja. Hay prueba que lo fija.

**Se retiró la marca temporal del panel de cobro.** `PR-06` la puso porque la caja no
frenaba el maní y callarlo era peor; ahora afirma lo contrario, y una prueba exige que la
advertencia vieja ya **no** esté — una marca que sobrevive a su historia miente igual que
mentiría su ausencia. La del cupo sigue en pie hasta `PR-09`.

`TT-114` no estrenó mecanismo: reutiliza la etiqueta de motivo que montó `TT-132`
(`data-motivo="alergeno-bloqueado"`), que es para lo que se hizo.

**Y una prueba que se escribió mal y se corrigió.** La primera versión de «se valida dentro
de la transacción» miraba `connection.in_atomic_block`, que bajo `TestCase` es `True`
siempre: no podía fallar. La que quedó mira el orden real de las consultas —el
`SELECT … FOR UPDATE` antes del cruce— y falla si alguien consulta las restricciones antes
de bloquear, comprobado introduciendo esa versión a propósito.

---

#### `PR-09` — `HU-20` Venta rechazada por límite diario

| | |
|---|---|
| Título del PR | `feat(ventas): rechazar la venta cuando se agotó el cupo del día` |
| Rama | `feat/TT-116-rechazo-por-limite` |
| Responsables | Pedro, Carlos y Alejandro |
| Historias | `HU-20` **y `HU-09`** — **las dos cerradas** |
| Invariantes | escenario crítico **`TST-2`**, ahora completo |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-116` | Validación del límite diario contra el consumo del día, dentro del bloqueo | Pedro | ☑ |
| `TT-117` | Motivo de rechazo por límite, distinguible del de saldo | Carlos | ☑ |
| `TT-118` | Caso de prueba `TST-2`: rechazo por cupo aunque haya saldo | Alejandro | ☑ |

> ⚠ **Salda también `HU-09`.** `PR-01` dejó el cupo configurable por estudiante y
> escribible solo por su acudiente, pero el tercer criterio de la historia —«el límite se
> evalúa contra el consumo del día en cada venta»— es exactamente lo que construye
> `TT-116`. **Al integrarlo hay que marcar DOS historias** en
> `./backlog-historias-de-usuario.md`: `HU-20` y `HU-09`.

Completa `TST-2`, cuya otra mitad cerró `HU-19` en el Sprint 2.

El caso a probar es el contraintuitivo: **hay saldo de sobra y la venta se rechaza igual**.
Si el mensaje dice «saldo insuficiente», el cajero le da al estudiante una explicación falsa.

**Cómo quedó.** La comprobación va en el paso 2, **antes del saldo y después de las
existencias**, y las dos cosas son deliberadas: antes del saldo porque «no alcanza»
mandaría al acudiente a recargar para que la venta se rechazara igual —el cupo no lo
arregla ninguna recarga—; después de las existencias porque «de eso quedan dos» es sobre
la vitrina y se resuelve en el acto. El mensaje lo dice con todas las letras: *recargar no
lo cambia*.

El consumo del día se lee **dentro del bloqueo** y del mismo libro que el saldo (`INV-2`):
no hay contador diario que pudiera discrepar del historial ni que alguien tenga que poner
a cero cada medianoche. La billetera está bloqueada desde el paso 1, así que dos cajas
simultáneas no pueden colar dos ventas que juntas pasan el cupo.

**El borde se decidió a favor de vender**: gastar exactamente el cupo es gastarlo, no
pasarse. Un límite de $8.000 que rechaza un almuerzo de $8.000 sería un límite de $7.999,
y nadie lo habría escrito así. Hay dos pruebas en ese filo — el cupo exacto se vende, un
peso por encima se rechaza— y la comparación `>` frente a `>=` las separa.

**Y se retiraron las tres marcas temporales del cupo**: la del panel de cobro (`PR-06`),
la de la pantalla del límite del acudiente y la de su tarjeta de resumen, que decían que
la caja todavía no lo aplicaba. Las pruebas que las exigían ahora exigen su ausencia. Con
esto **no queda ninguna marca de ese tipo en el sistema**: las tres restricciones se
configuran y las tres se hacen cumplir.

El aviso de la pantalla del límite dejó de ir en ámbar. El ámbar significa aquí «un límite
a punto de agotarse» (`[S1]`, regla 3) y ya no hay nada que advertir: lo que queda es
explicar cómo funciona el cupo, que es otra cosa.

---

### Estado del estudiante — `PR-10` … `PR-13`

#### `PR-10` — `HU-47` Desactivación por la institución

| | |
|---|---|
| Título del PR | `feat(personas): desactivar a un estudiante desde el padrón` |
| Rama | `feat/TT-119-desactivacion-institucion` |
| Responsables | Pedro y Carlos |
| Historia | `HU-47` — **cerrada** |
| Invariantes | `INVD-2` · registra **`DT-29`** |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-119` | Transición a `desactivado` desde el padrón de la institución | Pedro | ☑ |
| `TT-120` | Acción de desactivar en la ficha del padrón | Carlos | ☑ |

No hay modelo nuevo: `EstadoDelEstudiante` existe desde `HU-51` (Sprint 1). Hay una
transición nueva.

> ⚠ **Las dos tareas chocaban con `DT-27`, y se resolvió antes de construir.** `DT-27`
> había decidido que el padrón **solo lee** y que escribir era del admin; `TT-119` y
> `TT-120` sitúan la desactivación en el padrón. Se registró **`DT-29`**, que corrige esa
> parte de `DT-27` **solo para esta acción**: `HU-47` existe por la inmediatez —«bloquear
> su tarjeta de inmediato cuando se pierde en mitad de la jornada», dice su texto— y
> llegar al admin desde el padrón son tres pantallas. El alta, la edición, la baja y la
> reasignación siguen allí, y `POST /padron/` sigue respondiendo `405`: lo que escribe es
> una ruta propia de la pantalla, no la pantalla.

**Cómo quedó.** El servicio `desactivar` es la regla y la vista solo delega (`DT-15`):
comprueba el rol —hoy solo la institución; el acudiente llega con `HU-48`, que amplía esta
misma puerta—, es **idempotente** y **rechaza desactivar a un retirado**, porque de la baja
no se vuelve y un retirado marcado como desactivado se leería como reactivable.

**El efecto inmediato en la caja no hubo que construirlo**, y comprobarlo era el segundo
criterio: `INVD-2` se resuelve leyendo el estado y la venta ya pasa por esa puerta. La
prueba vende **antes** y **después** de desactivar con el mismo carrito. El motivo de
rechazo propio llega con `HU-50`.

**El rechazo del retirado vuelve en `200`, con su motivo dentro del fragmento.** Es el
precedente del cobro, y no es comodidad: htmx **no intercambia** lo que llega en `4xx`, así
que un `400` dejaría la pantalla igual y a secretaría sin saber por qué no pasó nada.

**El hueco de la reactivación se dice, no se deshabilita**: la fila de un desactivado
declara que reactivar es `HU-49`. Y la acción lleva confirmación del navegador, que hoy
pesa más que nunca — hasta `PR-12` un clic por error no tiene vuelta desde ninguna
pantalla.

---

#### `PR-11` — `HU-48` Desactivación por el acudiente

| | |
|---|---|
| Título del PR | `feat(personas): permitir al acudiente desactivar a su estudiante` |
| Rama | `feat/TT-121-desactivacion-acudiente` |
| Responsables | Pedro y Carlos |
| Historia | `HU-48` |
| Invariantes | `INVD-2`, `INVD-3` |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-121` | Transición a `desactivado` por el acudiente, **sin acción de reactivar** | Pedro | ☐ |
| `TT-122` | Acción de desactivar en la interfaz del acudiente | Carlos | ☐ |

Las dos vías cubren tiempos distintos (`DEC-5`): la institución bloquea de inmediato en
mitad de la jornada; el acudiente bloquea sin depender del horario de la secretaría.

---

#### `PR-12` — `HU-49` Reactivación exclusiva de la institución

| | |
|---|---|
| Título del PR | `feat(personas): reservar la reactivación a la institución` |
| Rama | `feat/TT-123-reactivacion-exclusiva` |
| Responsables | Pedro y Alejandro |
| Historia | `HU-49` |
| Invariantes | **`INVD-3`** |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-123` | Reactivación solo por la institución, con independencia de quién desactivó | Pedro | ☐ |
| `TT-124` | Caso de prueba: el acudiente que desactivó no puede reactivar | Alejandro | ☐ |

La asimetría tiene un motivo de seguridad: el desbloqueo pasa por una verificación
presencial, y eso impide que quien encontró la tarjeta consiga que se reactive.

---

#### `PR-13` — `HU-50` Venta rechazada por estudiante desactivado

| | |
|---|---|
| Título del PR | `feat(ventas): rechazar la venta a un estudiante desactivado` |
| Rama | `feat/TT-125-rechazo-por-desactivacion` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-50` |
| Invariantes | **`INVD-2`** |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-125` | Rechazo de venta y de retiro de pedido para desactivado o de baja | Pedro | ☐ |
| `TT-126` | Motivo de rechazo distinto de los de saldo, alérgeno y límite | Carlos | ☐ |
| `TT-127` | Caso de prueba: desactivado no compra pero **sí recibe recargas** | Alejandro | ☐ |

Al integrarse, la venta tiene **cuatro motivos de rechazo distintos**. Que se distingan no
es cosmética: el cajero tiene que poder decir qué pasa, y solo uno de los cuatro se
arregla recargando.

---

### Gestión — `PR-14`

#### `PR-14` — Gestión del sprint

| | |
|---|---|
| Título del PR | `docs(gestion): cerrar el Sprint 3` |
| Rama | `docs/TT-128-gestion-del-sprint-3` |
| Responsable | Naomi |
| Historia | ninguna — gestión |
| Estado | ☐ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-128` | Tablero Kanban del Sprint 3 | Naomi | ☐ |
| `TT-129` | Registro de riesgos del Sprint 3 | Naomi | ☐ |
| `TT-130` | Preparación de la Sprint Review y la Retrospective | Naomi | ☐ |

Va el último por número, no por fecha: las tres empiezan el primer día.

---

### Lo que el sprint no había previsto — `PR-15`

#### `PR-15` — `HU-60` Venta rechazada por producto bloqueado

| | |
|---|---|
| Título del PR | `feat(ventas): rechazar la venta de un producto bloqueado` |
| Rama | `feat/TT-131-rechazo-por-producto-bloqueado` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-60` — **añadida durante el sprint** |
| Invariantes | **`INV-4`** |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-131` | Validación del producto bloqueado dentro del bloqueo de la transacción | Pedro | ☑ |
| `TT-132` | Motivo de rechazo distinguible en el punto de venta | Carlos | ☑ |
| `TT-133` | Caso de prueba: rechazo con saldo de sobra, sin vía para forzarlo | Alejandro | ☑ |

> **Esta historia no estaba en la planeación, y por qué apareció importa.** Al construir
> `PR-02` se vio que `ALC-IN-09` pide aplicar las restricciones **en el momento de la
> venta** y que ninguna historia lo hacía para la lista de `HU-10`: las cuatro de rechazo
> cubrían alérgeno, saldo, límite y desactivación. Sin esto, el acudiente bloquea la
> gaseosa y la caja se la cobra igual. Está en el `ANEXO A` del sprint backlog, punto 5.

**Va el último por número y no por orden de construcción**, como `PR-14`. Solo depende de
`PR-02` y del Sprint 2, así que **puede integrarse en cuanto esté listo**: la propiedad que
`[S1]` demuestra —que toda dependencia de un PR esté en uno anterior— se cumple igual, y
así no hay que renumerar de `PR-03` a `PR-14`.

`TT-132` estrena el mecanismo de motivos que reutilizarán `TT-114`, `TT-117` y `TT-126`:
cada clase de rechazo lleva una etiqueta estable que llega al HTML del ticket. Con cuatro
motivos por delante, uno por historia habría sido cuatro maneras de decir lo mismo.

#### `PR-16` — `HU-61` Retiro del límite diario

| | |
|---|---|
| Título del PR | `feat(restricciones): retirar por completo el límite diario` |
| Rama | `feat/TT-134-retiro-del-limite-diario` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-61` — **añadida durante el sprint** (`DEC-13`) |
| Invariantes | `INV-4` · `ALC-IN-19`: el retiro se asienta |
| Estado | ☑ |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-134` | Servicio de retiro del límite diario, con asiento | Pedro | ☑ |
| `TT-135` | Acción de retirar en la pantalla del límite, con su historial | Carlos | ☑ |
| `TT-136` | Caso de prueba: retirado no es cero, y queda asentado | Alejandro | ☑ |

> **Esto amplía el alcance, y por eso lleva `DEC-13` delante.** `[S11]` daba al acudiente
> «**fijar** límite diario»; «retirar» estaba en la fila de las restricciones
> alimentarias, así que `HU-12` no alcanzaba al cupo. La única salida que quedaba era
> fijar una cifra tan alta que equivaliera a no tener tope — peor que no tenerlo, porque
> la pantalla seguiría diciendo que hay uno.

**Va el último por número y no por orden de construcción**, como `PR-14` y `PR-15`. Depende
de `PR-01` y de `PR-04`, las dos ya en `main`.

`TT-134` amplía el libro de `TT-104` con un campo `sobre`: el límite diario no tiene clave
ajena a la que apuntar, y dejar que «ninguna de las dos puesta» significara «límite» sería
la misma codificación implícita contra la que argumenta `LimiteDiario`.

---

## [S5] Qué se puede solapar

| PR | Puede ir en paralelo con | Porque |
|---|---|---|
| `PR-10` … `PR-13` (estado, Pedro) | `PR-01` … `PR-04` (restricciones, Pedro) | `TT-119` no depende de nada del sprint; son dos frentes que solo se encuentran en `PR-13` |
| `PR-14` (gestión, Naomi) | cualquiera | `TT-128`–`TT-130` no dependen de nada |

**Cinco raíces** sin dependencia dentro del sprint: `TT-94`, `TT-119` y las tres de gestión.

Carlos no tiene raíces: su primera tarea, `TT-96`, necesita `TT-95`. En el arranque del
sprint tiene un hueco de un día o dos — buen momento para adelantar la corrección del
defecto de `HU-11` que señala el `ANEXO A` del sprint backlog.

**Regla al solapar:** ramifica siempre desde `main`, nunca desde la rama del otro.

---

## [S6] Advertencias sobre este plan

1. **`PR-09` cerró dos historias, y una de ellas era de `PR-01`.** `HU-20` y `HU-09`:
   `PR-01` dejó el cupo configurable pero su tercer criterio —evaluarlo contra el consumo
   del día en cada venta— era `TT-116`. Las dos marcas están puestas, y la advertencia se
   conserva porque es el patrón que volverá a aparecer: una historia no se cierra donde se
   construye su pantalla, sino donde se cumple su último criterio.
2. **`PR-06` cierra dos historias.** `HU-13` y `HU-17`. Es la única vez en el proyecto que
   un PR salda una historia de un sprint anterior, y por eso es la marca más fácil de
   olvidar. Va anotada en `[S2]`, en `[S3.1]` y en el propio PR.
3. **`PR-03` es el de mayor riesgo.** `INV-5` se rompe con una decisión de modelado que
   parece una optimización. Revisadlo con `TT-103` delante.
4. **Tres PR seguidos tocan el mismo servicio transaccional.** `PR-08`, `PR-09` y `PR-13`
   añaden validaciones dentro del bloqueo que construyó `TT-80` en el Sprint 2. Cada una es
   sencilla; el riesgo es el acumulado. Comprobad que el orden bloqueo → validación →
   escritura sigue intacto **después del tercero**, no solo después de cada uno.
   **Van dos de tres.** Cada uno dejó su prueba de orden —`PR-08` sobre el cruce de
   alérgenos, `PR-09` sobre la lectura del consumo del día—, las dos mirando las consultas
   que la venta emite. `PR-13` hereda quien lo vigile, y con él toca repasar el orden
   completo: hoy es alérgeno → producto → existencias → cupo → saldo.
5. **Este sprint cierra `TST-1` y `TST-2`, y los dos están cerrados** (`PR-08` y
   `PR-09`). Son dos de los cuatro escenarios críticos que `ENT-05` exige demostrar;
   `TST-3` cerró en el Sprint 2 y `TST-4` es del Sprint 4: al acabar el 4, el plan de
   pruebas está completo.
6. **El sprint creció de 37 a 43 tareas, en dos pasos y por el mismo motivo**: construir
   el control parental destapó dos huecos que la planeación no vio. `HU-60` —ninguna
   historia rechazaba la venta de un producto bloqueado— y `HU-61` —el cupo se podía
   cambiar pero no retirar—. Las dos se registraron antes de construirse, la segunda con
   `DEC-13` porque amplía `[S11]`.
7. **Si el sprint desborda, ya no queda candidato cómodo.** Los dos que había —`PR-04` y
   `PR-07`— están integrados. **No se pueden mover** `PR-08`
   ni `PR-09` —son `TST-1` y `TST-2`— ni `PR-15` ni `PR-16`: sin ellas, lo ya construido
   promete una protección que no cumple.
8. **Este plan no reordena nada.** Si alguien propone mover una tarea de PR, hay que
   comprobar el `ANEXO C` del sprint backlog antes.
