# SmartFood — Plan de Pull Requests del Sprint 1

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-PR-SPRINT1 |
| titulo | Agrupación de las 55 tareas del Sprint 1 en Pull Requests, y estado de cada tarea |
| documentos_fuente | `./sprint-1-backlog.md` (`[S3]`, `[S4]`, `[S5]`, `ANEXO C`); `./convenciones-de-git.md` (`[S1]`) |
| tipo_documento | Documento derivado de planificación. **No es un artefacto de Scrum** |
| tareas cubiertas | 55 de 55 (`TT-01` … `TT-55`) |
| pull requests | 24 (`PR-01` … `PR-24`) |
| idioma | es-CO |
| version | 1.0 |

### [S0.1] Qué es este documento y qué no es

`main` está protegida: nada entra por `push` directo (`[S1]` de `./convenciones-de-git.md`).
Este documento responde a una sola pregunta operativa: **¿hasta dónde desarrollo antes de
parar, abrir un PR y seguir?**

**No reordena ni modifica ninguna tarea.** El orden de `./sprint-1-backlog.md` es el orden
de construcción verificado en su `ANEXO C`, y aquí se respeta carácter por carácter. Lo
único que este documento añade son **cortes**.

> **Este es el único sitio donde vive el estado de las tareas.** El sprint backlog es el
> plan y no se toca; el tablero de `TT-47` es la vista de la Daily. Si hay discrepancia,
> manda este documento.

---

## [S1] La regla de corte

Todo PR es un **bloque contiguo** del orden del sprint backlog. Sin huecos, sin saltos,
sin adelantar tareas.

De ahí sale la única propiedad que importa, y es demostrable:

> El `ANEXO C` verifica que el orden de las 55 tareas es un orden topológico del grafo de
> dependencias: **ninguna tarea aparece antes de algo que la bloquea**. Si cada PR es un
> bloque contiguo de ese orden, entonces toda dependencia de cualquier tarea de `PR-k`
> está, o en `PR-k`, o en un PR anterior. **Nunca en uno posterior.**

Consecuencia práctica: **integrar los PR en orden numérico no puede romperse.** Al abrir
`PR-k`, `main` ya contiene todo lo que sus tareas necesitan.

Los cortes se eligieron con tres criterios, en este orden:

1. **Un PR cierra algo demostrable.** `DoD-4` de `./definicion-de-terminado.md` exige demostrar
   la funcionalidad en el entorno desplegado. Un PR que deja una historia a medias no se
   puede demostrar.
2. **Un PR se revisa de una sentada.** Entre 1 y 4 tareas. Ninguno pasa de 4.
3. **Un PR no mezcla asuntos.** El correo no viaja con los buckets aunque sean contiguos.

---

## [S2] Cómo se marca una tarea como finalizada

> ⏸ **`DoD-4` está suspendido desde el 2026-08-30** y con él la verificación en el
> entorno desplegado. Una tarea se marca finalizada con los otros cinco criterios más la
> verificación local declarada. Ver `[S5]` de `./definicion-de-terminado.md`.

Una tarea pasa a **☑ Finalizada** cuando su PR está **integrado en `main`**, no cuando el
código funciona en local. Antes de eso es **☐ Pendiente**.

**El marcado va dentro del propio PR**, en su último commit antes de pedir revisión: se
editan sus filas de `[S4]`, su fila `Estado`, el contador de `[S3]` y la columna `Estado`
de `./sprint-1-backlog.md`. Si el PR no se integra, el marcado nunca llega a `main` y no
hay nada que deshacer. Un PR ya integrado que se olvidó de marcarse se pone al día en el
PR siguiente.

**El estado vive en dos documentos y deben coincidir**: aquí y en la columna `Estado` de
`./sprint-1-backlog.md`. Es duplicación deliberada —el sprint backlog es lo que se enseña
en la Sprint Review— y por eso hay que actualizar los dos a la vez. Si divergen, manda
este documento.

| Símbolo | Significado |
|---|---|
| ☑ | Finalizada — integrada en `main` |
| ☐ | Pendiente |
| ◆ | Marca del sprint backlog: se reduce a declarar el modelo en el admin (`DT-2`) |

---

## [S3] Avance del Sprint 1

| | Tareas | Pull Requests |
|---|---|---|
| **Finalizadas** | **15** de 55 | **9** de 24 |
| Pendientes | 40 | 15 |

| Responsable | Finalizadas | Total |
|---|---|---|
| Pedro | 9 | 25 |
| Carlos | 3 | 16 |
| Alejandro | 1 | 9 |
| Naomi | 2 | 5 |

### [S3.1] Estado de los 24 Pull Requests

| PR | Tareas | Qué cierra | Estado |
|---|---|---|---|
| `PR-01` | `TT-01` | Gobernanza del repositorio | ☑ `#1` |
| `PR-02` | `TT-02`–`TT-03` | Entorno local y esqueleto | ☑ `#2` |
| `PR-03` | `TT-04` | Despliegue → `ENT-01` | ☑ `#3` |
| `PR-04` | `TT-05` | Plantilla base | ☑ `#4` |
| `PR-05` | `TT-06` | Correo | ☑ `#5` |
| `PR-06` | `TT-07` | Definición de Terminado | ☑ `#6` |
| `PR-07` | `TT-50`, `TT-55` | Almacenamiento de objetos | ☑ `#7` |
| `PR-08` | `TT-09`–`TT-12` | `HU-39` | ☑ `#8` |
| `PR-09` | `TT-13`–`TT-14` | `HU-05` · `INV-6`, `INVD-1` | ☑ `#13` |
| `PR-10` | `TT-15`–`TT-18` | `HU-40` + `HU-41` · base de `INV-4` | ☐ |
| `PR-11` | `TT-19`–`TT-20` | `HU-42` | ☐ |
| `PR-12` | `TT-21`–`TT-24` | `HU-01` | ☐ |
| `PR-13` | `TT-25`–`TT-27` | `HU-02` | ☐ |
| `PR-14` | `TT-28`–`TT-29` | `HU-03` + `HU-04` | ☐ |
| `PR-15` | `TT-30`–`TT-32` | `HU-14` + `HU-43` · `INV-7` | ☐ |
| `PR-16` | `TT-33`–`TT-35` | `HU-44` | ☐ |
| `PR-17` | `TT-36`–`TT-37` | `HU-45` → `ENT-02` | ☐ |
| `PR-18` | `TT-38`–`TT-40` | `HU-46` · `INVD-4` | ☐ |
| `PR-19` | `TT-41`–`TT-42` | `HU-51` | ☐ |
| `PR-20` | `TT-51`–`TT-52` | `HU-57` | ☐ |
| `PR-21` | `TT-43`–`TT-46` | `HU-26` · `INV-5` | ☐ |
| `PR-22` | `TT-53`–`TT-54` | `HU-59` | ☐ |
| `PR-23` | `TT-08` | Datos ficticios · `INVD-6` | ☐ |
| `PR-24` | `TT-47`–`TT-49` | Gestión del sprint | ☐ |

---

## [S4] Los 24 Pull Requests

### Habilitación — `PR-01` … `PR-07`

Corresponden a `[S3]` del sprint backlog. Las nueve tareas de habilitación, en su orden.
Ninguna historia se puede construir antes de que estas siete estén integradas.

---

#### `PR-01` — Gobernanza del repositorio

| | |
|---|---|
| Título del PR | `chore(infra): establecer la gobernanza del repositorio` |
| Rama | `chore/TT-01-gobernanza-del-repositorio` |
| Responsable | Naomi |
| Historia | — (habilitación) |
| Invariantes | ninguna |
| Estado | ☑ **Integrado en `main`** (#1) |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-01` | Repositorio, estrategia de ramas y convención de commits | Naomi | ☑ |

Entrega `.gitignore`, `.releaserc.json`, los workflows de release y de validación del
título del PR, la plantilla de PR y `./convenciones-de-git.md`.

> **Queda un paso manual fuera del repositorio:** activar la protección de `main` en la
> configuración de GitHub —prohibir `push` directo, exigir PR y exigir que
> `Convención de commits` esté en verde—. Sin eso, la convención es una recomendación.

---

#### `PR-02` — Entorno local y esqueleto de la aplicación

| | |
|---|---|
| Título del PR | `build(infra): levantar el entorno local y el esqueleto de la aplicación` |
| Rama | `build/TT-02-entorno-local` |
| Responsable | Pedro |
| Historia | — (habilitación) |
| Invariantes | ninguna |
| Estado | ☑ **Integrado en `main`** (#2) |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-02` | Entorno local reproducible: `docker compose` con PostgreSQL y MinIO | Pedro | ☑ |
| `TT-03` | Esqueleto de la aplicación y conexión a la base de datos | Pedro | ☑ |

Van juntas porque por separado no se demuestra nada: un `compose` sin aplicación no se
prueba, y una aplicación sin base de datos no arranca. Incluye `.env.example`.

---

#### `PR-03` — Despliegue en el entorno de pruebas

| | |
|---|---|
| Título del PR | `ci(infra): desplegar en el entorno de pruebas` |
| Rama | `ci/TT-04-despliegue-entorno-de-pruebas` |
| Responsable | Pedro |
| Historia | — (habilitación) |
| Invariantes | ninguna |
| Estado | ☑ **Integrado en `main`** (#3) |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-04` | Despliegue en entorno de pruebas con base de datos gestionada | Pedro | ☑ |

Solo, porque toca credenciales del PaaS y no se valida leyendo el diff: se valida abriendo
la URL — **https://web-production-3db23.up.railway.app**. **Habilita `ENT-01` y con él la Definición de Terminado entera**: hasta que este PR
no esté integrado, ninguna historia puede darse por terminada.

---

#### `PR-04` — Plantilla base y hoja de estilos

| | |
|---|---|
| Título del PR | `feat(plantillas): añadir plantilla base y layout adaptable a móvil` |
| Rama | `feat/TT-05-plantilla-base` |
| Responsable | Carlos |
| Historia | — (habilitación) |
| Invariantes | ninguna |
| Estado | ☑ **Integrado en `main`** (#4) |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-05` | Plantilla base, layout adaptable a móvil y hoja de estilos | Carlos | ☑ |

Habilita `INT-1` e `INT-3`. Tailwind por CLI, sin CDN (`DT-16`). **No depende de `PR-03`**:
ver `[S5]`.

---

#### `PR-05` — Envío de correo

| | |
|---|---|
| Título del PR | `feat(correo): configurar el envío de correo` |
| Rama | `feat/TT-06-envio-de-correo` |
| Responsable | Pedro |
| Historia | — (habilitación) |
| Invariantes | ninguna |
| Estado | ☑ **Integrado en `main`** (#5) |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-06` | Configuración del envío de correo | Pedro | ☑ |

Habilita `HU-39`, `HU-03` y `HU-41`: las tres invitaciones salen por aquí. Este PR
registra además `DEC-9`, que surgió al configurarlo: la carga masiva genera las
invitaciones pero no las entrega.

---

#### `PR-06` — Definición de Terminado

| | |
|---|---|
| Título del PR | `docs(docs): acordar la Definición de Terminado` |
| Rama | `docs/TT-07-definicion-de-terminado` |
| Responsable | Naomi |
| Historia | — (habilitación) |
| Invariantes | ninguna |
| Estado | ☑ **Integrado en `main`** (#6) |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-07` | Redacción y acuerdo de la Definición de Terminado (`COM-3`) | Naomi | ☑ |

PR de una sola tarea documental. Es un `docs`: no publica versión.

Extrae la Definición de Terminado a `./definicion-de-terminado.md` con identificadores
citables (`DoD-1` … `DoD-6`) y la reescribe con **criterios condicionales**, porque la
redacción original hablaba de historias y **12 de las 55 tareas del sprint no cuelgan de
ninguna** — incluidos los cinco PR ya integrados.

---

#### `PR-07` — Almacenamiento de objetos

| | |
|---|---|
| Título del PR | `feat(almacenamiento): crear los buckets y la canalización de subida` |
| Rama | `feat/TT-50-almacenamiento-de-objetos` |
| Responsable | Pedro |
| Historia | — (habilitación) |
| Invariantes | ninguna directamente; sostiene `DT-18`, `DT-20` y `DT-21` |
| Estado | ☑ **Integrado en `main`** (#7) |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-50` | Dos buckets —privado y público— con sus políticas y credenciales (`DT-18`) | Pedro | ☑ |
| `TT-55` | Canalización de subida: validación por contenido, re-codificación y retirada del EXIF (`DT-20`) | Pedro | ☑ |

Los buckets sin canalización de subida no se prueban, y la canalización sin buckets no
tiene dónde escribir. Este PR registra además **`DT-21`**, que corrige `DT-18`: el
proveedor no ofrece buckets públicos en ningún plan, así que es **un bucket con dos
prefijos y ninguno público**. **La base guarda la clave del objeto, nunca el binario.** El PR debe
demostrar que la URL del bucket privado va firmada y caduca: es una fotografía de un menor
(`DEC-8`, `ALC-OUT-08`).

---

### Historias — `PR-08` … `PR-22`

Corresponden a `[S4]` del sprint backlog, en su orden.

---

#### `PR-08` — `HU-39` Alta de la institución educativa por seed

| | |
|---|---|
| Título del PR | `feat(cuentas): dar de alta la institución educativa por seed` |
| Rama | `feat/TT-09-institucion-por-seed` |
| Responsables | Pedro y Carlos |
| Historia | `HU-39` |
| Invariantes | empieza a sostener `INV-6`, `INVD-1` |
| Estado | ☑ **Integrado en `main`** (#8) |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-09` | Modelo de usuario con rol, y modelo de institución educativa | Pedro | ☑ |
| `TT-10` | Rutina de seed que crea la institución de referencia y dispara su invitación | Pedro | ☑ |
| `TT-11` | Pantalla de definición de contraseña a partir del token de invitación | Carlos | ☑ |
| `TT-12` | Plantilla del correo de invitación | Carlos | ☑ |

Las cuatro cierran la primera historia del sprint y hay que integrarlas juntas: una
invitación que no se puede aceptar no se demuestra. `TT-11` y `TT-12` los reutilizan
después `HU-03` y `HU-41` (`DEC-3`).

> Aquí se monta también **el esqueleto** de `TT-08` —el comando de seed y su invocación—,
> tal como indica `[S4]` del sprint backlog. **No cierra `TT-08`**, que se termina en
> `PR-23`.

---

#### `PR-09` — `HU-05` Autorregistro bloqueado

| | |
|---|---|
| Título del PR | `feat(cuentas): eliminar toda ruta de autorregistro` |
| Rama | `feat/TT-13-autorregistro-bloqueado` |
| Responsables | Pedro y Alejandro |
| Historia | `HU-05` |
| Invariantes | **`INV-6`, `INVD-1`** |
| Estado | ☑ **Integrado en `main`** (#13) |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-13` | Eliminar toda ruta de registro; el usuario se crea sin contraseña utilizable | Pedro | ☑ |
| `TT-14` | Caso de prueba: intento de autorregistro desde cada una de las tres interfaces | Alejandro | ☑ |

La invariante y su prueba van en el mismo PR: la Definición de Terminado lo exige. Las
rutas de registro **no existen**, no se ocultan (`DT-10`).

`TT-13` cerró además un agujero que no era evidente: un `Usuario` creado **sin pasar por
el manager** —el formulario de alta del admin— quedaba con la contraseña vacía, y Django
considera **usable** una contraseña vacía. Esa cuenta habría reportado tener contraseña
definida y no se habría podido invitar nunca. Lo impide ahora una restricción de la base.

---

#### `PR-10` — `HU-40` y `HU-41` Cuentas de personal e invitación

| | |
|---|---|
| Título del PR | `feat(cuentas): dar de alta cuentas de personal por invitación` |
| Rama | `feat/TT-15-cuentas-de-personal` |
| Responsables | Pedro y Carlos |
| Historias | `HU-40`, `HU-41` |
| Invariantes | base de **`INV-4`** |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-15` | Roles y permisos por modelo según la matriz `[S11]` | Pedro | ☐ |
| `TT-16` | Servicio de alta de cuenta de personal que dispara la invitación | Pedro | ☐ |
| `TT-17` ◆ | Vista de gestión de cuentas de personal para la institución | Carlos | ☐ |
| `TT-18` | Token de invitación de un solo uso y con caducidad | Pedro | ☐ |

`HU-41` aporta una sola tarea y el resto lo cubren `TT-11` y `TT-12`, ya integrados: no
merece PR propio. `TT-15` es donde se decide `INV-4` —el cajero no tiene permiso de
escritura sobre restricciones—, y se decide **en la capa de datos**, no ocultando un botón
en el Sprint 3 (`DT-11`).

---

#### `PR-11` — `HU-42` Desactivación y reactivación de cuentas

| | |
|---|---|
| Título del PR | `feat(cuentas): desactivar y reactivar cuentas de personal` |
| Rama | `feat/TT-19-desactivacion-de-cuentas` |
| Responsables | Pedro y Carlos |
| Historia | `HU-42` |
| Invariantes | ninguna |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-19` | Estado de la cuenta y bloqueo del inicio de sesión si está inactiva | Pedro | ☐ |
| `TT-20` ◆ | Acciones de desactivar y reactivar en la vista de cuentas | Carlos | ☐ |

Candidato número uno a moverse al Sprint 2 si el sprint desborda: `ANEXO A` del sprint
backlog. Ninguna historia posterior depende de él.

---

#### `PR-12` — `HU-01` Carga masiva de estudiantes y acudientes

| | |
|---|---|
| Título del PR | `feat(personas): cargar estudiantes y acudientes desde un archivo` |
| Rama | `feat/TT-21-carga-masiva` |
| Responsables | Pedro, Alejandro y Carlos |
| Historia | `HU-01` |
| Invariantes | ninguna directamente |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-21` | Modelos de estudiante y acudiente, con vínculo de uno a varios (`ALC-IN-04`) | Pedro | ☐ |
| `TT-22` | Definición del formato del archivo: columnas, tipos y obligatoriedad | Alejandro | ☐ |
| `TT-23` | Lector del archivo y servicio de carga dentro de una transacción | Pedro | ☐ |
| `TT-24` | Pantalla de carga con selección de archivo y resultado | Carlos | ☐ |

El PR más cargado del sprint junto con `PR-21`. `TT-22` es análisis y no depende de nada:
Alejandro puede tenerlo escrito antes de que Pedro llegue a `TT-23`, aunque se integren en
el mismo PR.

---

#### `PR-13` — `HU-02` Validación del archivo antes de escribir

| | |
|---|---|
| Título del PR | `feat(personas): validar el archivo completo antes de escribir` |
| Rama | `feat/TT-25-validacion-todo-o-nada` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-02` |
| Invariantes | ninguna; el «todo o nada» es criterio de aceptación |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-25` | Validador que acumula errores por fila y **no escribe nada si hay alguno** | Pedro | ☐ |
| `TT-26` | Pantalla de reporte de errores de validación | Carlos | ☐ |
| `TT-27` | Archivos de prueba: uno válido, uno con errores y uno mixto | Alejandro | ☐ |

Se separa de `PR-12` para que cada uno se revise de una sentada, no porque sean
independientes. El archivo **mixto** de `TT-27` es el que prueba la atomicidad: si escribe
las filas buenas, el PR no pasa.

---

#### `PR-14` — `HU-03` y `HU-04` Acudientes

| | |
|---|---|
| Título del PR | `feat(personas): invitar al acudiente y permitirle elegir estudiante` |
| Rama | `feat/TT-28-acudientes` |
| Responsables | Pedro y Carlos |
| Historias | `HU-03`, `HU-04` |
| Invariantes | ninguna |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-28` | Disparo de una invitación por acudiente al completarse la carga | Pedro | ☐ |
| `TT-29` | Consulta de estudiantes a cargo y selector de estudiante en la interfaz del acudiente | Carlos | ☐ |

Dos historias de una tarea cada una, contiguas y del mismo asunto: el acudiente entra y ve
a los suyos. El modelo ya lo resolvió `TT-21`.

> **`DEC-9` cambia lo que `TT-28` tiene que construir.** La carga **genera** la invitación
> de cada acudiente —token de un solo uso y con caducidad— pero **no la entrega por
> correo**: las direcciones cargadas son ficticias (`ALC-OUT-07`) y no corresponden a
> ningún buzón. No hay que implementar envío masivo ni preocuparse por su latencia.
> `HU-03` se demuestra tomando el enlace de un acudiente cargado y definiendo la
> contraseña con él.

---

#### `PR-15` — `HU-14` y `HU-43` Código de tarjeta

| | |
|---|---|
| Título del PR | `feat(personas): generar y asignar el código de tarjeta` |
| Rama | `feat/TT-30-codigo-de-tarjeta` |
| Responsables | Pedro y Alejandro |
| Historias | `HU-14`, `HU-43` |
| Invariantes | **`INV-7`** |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-30` | Generador criptográfico del código, con índice único y reintento ante colisión | Pedro | ☐ |
| `TT-31` | Caso de prueba: unicidad y no secuencialidad sobre un lote grande de códigos | Alejandro | ☐ |
| `TT-32` | Asignación del código al dar de alta al estudiante, por carga masiva y por alta individual | Pedro | ☐ |

`TT-30` es una función pura, no depende de nada y se presta a escribir la prueba antes que
la implementación: **el mejor primer commit del sprint**. **Nunca secuencia, nunca derivado
del identificador del estudiante, nunca UUIDv7** —lleva timestamp y va ordenado
(`DT-9`, `DT-17`)—: el código opera como credencial de acceso al saldo.

---

#### `PR-16` — `HU-44` Vista de administración de estudiantes

| | |
|---|---|
| Título del PR | `feat(personas): administrar estudiantes desde la institución` |
| Rama | `feat/TT-33-administracion-de-estudiantes` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-44` |
| Invariantes | ninguna |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-33` | Servicios de alta individual y de edición de estudiante | Pedro | ☐ |
| `TT-34` ◆ | Vista de listado, búsqueda, alta individual y edición | Carlos | ☐ |
| `TT-35` | Recorrido de experiencia de usuario de la vista de administración | Alejandro | ☐ |

`TT-34` es la vista sobre la que se apoyan `PR-17`, `PR-19` y `PR-20`. Integrarla pronto
desbloquea tres PR posteriores.

---

#### `PR-17` — `HU-45` Consulta del código de tarjeta vigente

| | |
|---|---|
| Título del PR | `feat(personas): mostrar e imprimir el código de tarjeta vigente` |
| Rama | `feat/TT-36-codigo-vigente` |
| Responsable | Carlos |
| Historia | `HU-45` |
| Invariantes | ninguna |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-36` | Exposición del código vigente en la ficha del estudiante | Carlos | ☐ |
| `TT-37` | Vista imprimible del código de barras | Carlos | ☐ |

**Habilita `ENT-02`.** Sin tarjetas impresas no hay prueba de concepto del lector en el
Sprint 2: no es un adorno, es el insumo físico de la siguiente demostración.

---

#### `PR-18` — `HU-46` Reasignación del código de tarjeta

| | |
|---|---|
| Título del PR | `feat(personas): reasignar el código de tarjeta invalidando el anterior` |
| Rama | `feat/TT-38-reasignacion-de-codigo` |
| Responsables | Pedro, Carlos y Alejandro |
| Historia | `HU-46` |
| Invariantes | **`INVD-4`** |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-38` | Servicio de reasignación que invalida el código anterior de forma definitiva | Pedro | ☐ |
| `TT-39` | Acción de reasignar en la ficha, con confirmación | Carlos | ☐ |
| `TT-40` | Caso de prueba: el código anterior deja de identificar a nadie | Alejandro | ☐ |

Si el código anterior sigue siendo válido, `HU-47` y `HU-48` del Sprint 2 no protegen nada.
`TT-40` es la prueba que lo impide y va en este PR, no después.

---

#### `PR-19` — `HU-51` Baja lógica del estudiante retirado

| | |
|---|---|
| Título del PR | `feat(personas): dar de baja al estudiante conservando su historial` |
| Rama | `feat/TT-41-baja-logica` |
| Responsables | Pedro y Carlos |
| Historia | `HU-51` |
| Invariantes | protege **`INV-2`** |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-41` | Estado de baja en el estudiante, conservando íntegro su historial | Pedro | ☐ |
| `TT-42` ◆ | Acción de dar de baja en la ficha del estudiante | Carlos | ☐ |

Baja **lógica**. Un `DELETE` destruiría el historial del que se reconstruye el saldo
(`INV-2`, `DT-4`). Si el PR contiene un borrado físico, no se integra.

---

#### `PR-20` — `HU-57` Fotografía del estudiante

| | |
|---|---|
| Título del PR | `feat(personas): cargar la fotografía del estudiante` |
| Rama | `feat/TT-51-fotografia-del-estudiante` |
| Responsables | Pedro y Carlos |
| Historia | `HU-57` |
| Invariantes | ninguna; se apoya en `DT-18` y `DT-20` |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-51` | Campo de clave de objeto en el estudiante y servicio de carga y reemplazo de la fotografía | Pedro | ☐ |
| `TT-52` ◆ | Carga de la fotografía desde la ficha del estudiante | Carlos | ☐ |

Bucket **privado**, URL firmada de caducidad corta. La fotografía **no es obligatoria**: su
ausencia no puede impedir ninguna operación, y el PR tiene que demostrarlo.

---

#### `PR-21` — `HU-26` Administración del catálogo

| | |
|---|---|
| Título del PR | `feat(catalogo): administrar productos, categorías y alérgenos` |
| Rama | `feat/TT-43-catalogo` |
| Responsables | Pedro, Alejandro y Carlos |
| Historia | `HU-26` |
| Invariantes | **`INV-5`** |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-43` | Modelos de producto, categoría y alérgeno, con **relación** producto–alérgeno | Pedro | ☐ |
| `TT-44` | Definición de los campos nutricionales que consumirán las reglas de recomendación | Alejandro | ☐ |
| `TT-45` ◆ | Vista de gestión del catálogo | Carlos | ☐ |
| `TT-46` | Caso de prueba: el alérgeno se relaciona, no se copia como lista de productos | Alejandro | ☐ |

**El PR más delicado del sprint.** `TT-43` decide si `HU-11` del Sprint 3 se puede
construir o hay que rehacer el modelo. `INV-5` exige que el bloqueo por alérgeno se aplique
**sobre la condición**, evaluada en la venta, de modo que cubra productos que aún no
existen. Si el alérgeno se modela como una lista materializada de productos bloqueados, el
PR se rechaza aunque las pruebas pasen: `TT-46` existe precisamente para detectarlo.

Revisión obligatoria de los dos desarrolladores, no de uno.

---

#### `PR-22` — `HU-59` Imagen del producto

| | |
|---|---|
| Título del PR | `feat(catalogo): cargar la imagen del producto` |
| Rama | `feat/TT-53-imagen-del-producto` |
| Responsables | Pedro y Carlos |
| Historia | `HU-59` |
| Invariantes | ninguna |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-53` | Campo de clave de objeto en el producto y servicio de carga de la imagen | Pedro | ☐ |
| `TT-54` ◆ | Carga de la imagen desde la ficha del producto | Carlos | ☐ |

Bucket **público**: la imagen de un producto no es sensible y firmar cincuenta URL para
pintar la lista del punto de venta es coste sin contrapartida (`DT-18`).

---

### Cierre — `PR-23` y `PR-24`

---

#### `PR-23` — Generador de datos ficticios

| | |
|---|---|
| Título del PR | `feat(seed): completar el generador de datos ficticios con avatares` |
| Rama | `feat/TT-08-datos-ficticios` |
| Responsable | Alejandro |
| Historia | — (transversal) |
| Invariantes | **`INVD-6`**; `ALC-OUT-07` |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-08` | Generador de datos ficticios para pruebas, con avatares (`ALC-OUT-07`, `INVD-6`) | Alejandro | ☐ |

**Es la única tarea del sprint que crece por partes.** Su esqueleto se monta en `PR-08` y
se amplía a lo largo del sprint; este PR es donde **queda terminada**, cuando ya existen
los tres bloques que tiene que sembrar:

| Se puede sembrar… | Disponible desde |
|---|---|
| Cuentas de usuario e institución | `PR-08` (`TT-09`) |
| Estudiantes y acudientes, con sus avatares | `PR-12` (`TT-21`), con `PR-07` ya integrado |
| Catálogo: productos, categorías y alérgenos | `PR-21` (`TT-43`) |

`INVD-6` es una regla de operación: **ninguna fotografía corresponde a una persona real.**
Los avatares se generan; no se descargan de ningún sitio.

---

#### `PR-24` — Gestión del Sprint

| | |
|---|---|
| Título del PR | `docs(docs): registrar el tablero, los riesgos y el cierre del sprint` |
| Rama | `docs/TT-47-gestion-del-sprint` |
| Responsable | Naomi |
| Historia | — (gestión, `[S5]`) |
| Invariantes | ninguna |
| Estado | ☐ Pendiente |

| Tarea | Descripción | Resp. | Estado |
|---|---|---|---|
| `TT-47` | Tablero Kanban con las tareas del sprint y su estado | Naomi | ☐ |
| `TT-48` | Registro de riesgos del sprint y seguimiento en las Daily | Naomi | ☐ |
| `TT-49` | Preparación de la Sprint Review y de la Retrospective | Naomi | ☐ |

Va el último **por número, no por fecha**: las tres empiezan el primer día y ninguna
depende de nada. El PR recoge lo que de ellas queda en el repositorio —el registro de
riesgos y el material de cierre—; el tablero de `TT-47` vive en su herramienta y aquí solo
se enlaza.

---

## [S5] Qué se puede solapar

El orden de integración es estricto, pero **el trabajo no es una fila india.** Estos PR no
dependen entre sí y pueden estar abiertos a la vez:

| PR | Puede ir en paralelo con | Porque |
|---|---|---|
| `PR-04` (plantilla base, Carlos) | `PR-03` (despliegue, Pedro) | `TT-05` no necesita el entorno desplegado |
| `PR-06` (Definición de Terminado, Naomi) | cualquiera | `TT-07` no depende de nada |
| `PR-24` (gestión, Naomi) | cualquiera | `TT-47`, `TT-48` y `TT-49` no dependen de nada |

Y hay tareas **raíz** —sin dependencias— que se pueden trabajar desde el primer día aunque
su PR se integre más tarde: `TT-22` (`PR-12`), `TT-30` (`PR-15`), `TT-35` (`PR-16`) y
`TT-44` (`PR-21`). Cuatro de ellas son de Alejandro, que en este sprint tiene holgura
(`ANEXO A`).

**Regla al solapar:** ramifica siempre desde `main`, nunca desde la rama del otro. Si tu PR
necesita algo del PR de al lado, no es paralelo: espera a que se integre.

---

## [S6] Advertencias sobre este plan

1. **24 PR en dos semanas son más de dos al día.** Es lo normal en trunk based
   development, pero exige que la revisión sea rápida. Un PR que espera dos días revisión
   convierte la rama corta en rama larga y el plan se cae. Acordad un tiempo máximo de
   respuesta en la Daily.
2. **Con dos desarrolladores y revisión cruzada obligatoria, Pedro y Carlos se revisan el
   uno al otro.** Alejandro y Naomi pueden revisar los PR documentales y los de pruebas,
   pero no cubren backend. Si Pedro es el único que entiende `PR-21`, la revisión de ese PR
   es un trámite: por eso se pide revisión de los dos.
3. **`PR-03` bloquea la Definición de Terminado, no la construcción.** Se puede seguir
   desarrollando sin él, pero **ninguna historia se puede dar por terminada** hasta que el
   entorno desplegado exista. Retrasarlo acumula historias «casi hechas», que es
   exactamente el fallo que `ANEXO A` advierte para el día 10.
4. **Si el sprint desborda**, la salida 2 de `ANEXO A` mueve `HU-42`, `HU-46` y `HU-51` al
   Sprint 2. En este plan eso es sacar `PR-11`, `PR-18` y `PR-19`: quedan 21 PR y 48
   tareas. Ninguno de los tres bloquea a los demás, y por eso son los candidatos.
5. **Este plan no reordena nada.** Si alguien propone mover una tarea de PR, hay que
   comprobar el `ANEXO C` antes: el orden es un orden topológico verificado, y romperlo
   introduce un bloqueo que no se ve hasta que alguien está a mitad de la tarea.
