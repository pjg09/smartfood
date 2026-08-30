# SmartFood — Sprint Backlog del Sprint 1

## [S0] Bloque de control del documento

### [S0.1] Metadatos

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-SPRINT1 |
| titulo | Sprint Backlog del Sprint 1 — Registro, perfiles, vinculación y catálogo |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./backlog-historias-de-usuario.md` (`[S5]`, Sprint 1); `./decisiones-de-alcance.md`; `./smartfood.md` (`S11`, `S12`); `corpus:guia-de-scrum-2020.md` (`ART-2`, `COM-2`, `COM-3`); `corpus:semana-5-gestion-de-proyectos-con-metodologias-agiles.md` (`D07`, `CUR-1`, `CUR-3`) |
| tipo_documento | Sprint Backlog (`ART-2` de la Guía de Scrum) |
| procedencia | Copia de trabajo. El maestro estaba en el corpus documental de la asignatura (repositorio `tic1`, local). **A partir del traslado, este fichero es el vigente**: no editar la copia del corpus. |
| sprint | 1 de 5 |
| semanas | 6 – 7 |
| historias | 18 — las 16 iniciales más `HU-57` y `HU-59`, derivadas de `DEC-8` |
| tareas | 55 (`TT-01` … `TT-55`) |
| stack | Django + PostgreSQL + HTMX (`DT-2`, `DT-3` de `./decisiones-tecnicas.md`) |
| idioma | es-CO |
| version | 1.2 |

### [S0.2] Instrucciones de lectura para el agente

1. Documento **derivado**: no reexpresa ningún original y no lleva texto verbatim.
2. Es el **Sprint Backlog** en el sentido de `ART-2` de la Guía de Scrum: el Objetivo del Sprint, las historias seleccionadas y **el plan para entregarlas**. Las tareas técnicas son ese plan.
3. **Ninguna tarea introduce alcance nuevo.** Cada una se deriva de una historia de `./backlog-historias-de-usuario.md` o es trabajo de habilitación sin el cual esas historias no pueden construirse. Las tareas de habilitación se declaran como tales.
4. **Las tareas se nombran de forma neutral** (modelo, migración, servicio, vista, plantilla) porque se redactaron antes de fijar el stack. El stack ya está decidido en `./decisiones-tecnicas.md` (`DT-2`): Django + PostgreSQL + HTMX. Las cinco marcadas con **`◆`** —`TT-17`, `TT-20`, `TT-34`, `TT-42` y `TT-45`, todas de Carlos— se reducen a declarar el modelo en el admin generado; ver el `ANEXO A` de ese documento.
5. Los responsables salen de la matriz de roles `[S12]` de `./smartfood.md`. La Guía de Scrum asigna el trabajo a los **Developers** de forma auto-organizada: este reparto es una previsión de Sprint Planning (`EVT-1`), no una asignación rígida.
6. Los identificadores `[TT-nn]` son estables y citables.
7. **La columna `Estado` marca el avance.** `☑` es finalizada —integrada en `main`—, `☐` es pendiente. El
   plan no cambia: la columna se añade sin reordenar ni modificar ninguna tarea.
8. El estado se lleva **también** en `./plan-de-pull-requests.md`, que agrupa estas 55 tareas en 24 Pull
   Requests y añade el PR de cada una. Los dos documentos deben coincidir; si divergen, manda el plan de
   Pull Requests, porque es donde se marca al integrar. Las convenciones de ramas y commits están en
   `./convenciones-de-git.md` (`TT-01`).

### [S0.3] Mapa de secciones

| ID | Sección | Contenido |
|---|---|---|
| S1 | Objetivo del Sprint | `COM-2` |
| S2 | Definición de Terminado | Puntero a `./definicion-de-terminado.md` (`COM-3`) |
| S3 | Tareas de habilitación | `TT-01` … `TT-08`, sin historia asociada |
| S4 | Tareas por historia | `TT-09` … `TT-46` |
| S5 | Tareas de gestión del Sprint | `TT-47` … `TT-49` |
| S6 | Reparto por responsable | Carga de cada integrante |
| ANEXO A | Riesgo de sobrecarga | Análisis de capacidad y qué hacer |
| ANEXO B | Nota de procedencia | Cómo se derivó |
| ANEXO C | Verificación del orden de construcción | Grafo de dependencias |

---

## [S1] Objetivo del Sprint `[COM-2]`

> Que la institución educativa pueda entrar al sistema, dar de alta al personal de la cafetería y cargar a sus estudiantes con sus acudientes vinculados, su código de tarjeta y su fotografía, y que la cafetería tenga su catálogo de productos cargado con sus imágenes.

Al cerrar el Sprint 1 existe **con quién** operar (cuentas), **sobre quién** operar (estudiantes y acudientes) y **qué** vender (catálogo). Nada se vende todavía: eso es el Sprint 2.

---

## [S2] Definición de Terminado `[COM-3]`

**Vive en `./definicion-de-terminado.md`** (`TT-07`). Aquí solo queda el puntero: es el
compromiso del Incremento y gobierna los cinco sprints, así que no puede vivir dentro
del artefacto de uno solo —el backlog del Sprint 2 tendría que duplicarlo, y entonces
divergen—.

| | Criterio | Cuándo aplica |
|---|---|---|
| `DoD-1` | Los criterios de aceptación se cumplen | Si cierra historias; si no, declara qué habilita |
| `DoD-2` | Está integrado en la rama principal | **Siempre** |
| `DoD-3` | Las migraciones están escritas y aplicadas | Si cambia el esquema |
| `DoD-4` | Se demuestra en el entorno desplegado (`ENT-01`) | **Siempre** |
| `DoD-5` | Cada invariante que sostiene tiene su prueba | Si sostiene alguna |
| `DoD-6` | Todos los datos son ficticios (`ALC-OUT-07`) | **Siempre** |

Un criterio que no aplica **se declara**, no se salta. El detalle de cada uno, y qué
cambió respecto de la redacción original, están en el documento.

---

## [S3] Tareas de habilitación

Trabajo sin el cual ninguna historia del sprint puede construirse. **No provienen de ninguna historia** porque el Product Backlog recoge valor para el usuario, no infraestructura. Se declaran aquí para que no queden invisibles en la planeación.

| ID | Tarea | Responsable | Habilita | Estado |
|---|---|---|---|---|
| `TT-01` | Repositorio, estrategia de ramas y convención de commits | Naomi | Todo | ☑ |
| `TT-02` | Entorno local reproducible: `docker compose` con PostgreSQL y MinIO | Pedro | Todo | ☑ |
| `TT-03` | Esqueleto de la aplicación y conexión a la base de datos | Pedro | Todo | ☑ |
| `TT-04` | Despliegue en entorno de pruebas con base de datos gestionada | Pedro | `ENT-01`, Definición de Terminado | ☑ |
| `TT-05` | Plantilla base, layout adaptable a móvil y hoja de estilos | Carlos | `INT-1`, `INT-3` | ☑ |
| `TT-06` | Configuración del envío de correo | Pedro | `HU-39`, `HU-03`, `HU-41` | ☑ |
| `TT-07` | Redacción y acuerdo de la Definición de Terminado (`COM-3`) | Naomi | Todo | ☑ |
| `TT-50` | Dos buckets —privado y público— con sus políticas y credenciales (`DT-18`) | Pedro | `HU-57`, `HU-59` | ☑ |
| `TT-55` | Canalización de subida: validación por contenido, re-codificación y retirada del EXIF (`DT-20`) | Pedro | `HU-57`, `HU-59` | ☑ |

**Las nueve se pueden hacer de entrada**, en el orden en que están: ninguna depende de nada que venga después. `TT-08`, el generador de datos ficticios, era la décima y se movió al final de `[S4]`, porque necesita que existan los modelos.

> Estas nueve tareas **no requieren esperar a la semana 6.** Ver `ANEXO A`.

---

## [S4] Tareas por historia

**El orden en que están escritas es el orden en que se pueden desarrollar.** Cada tarea puede empezarse cuando llegas a ella, porque todo lo que la bloquea ya quedó atrás. Sin excepciones: basta con ir de arriba abajo. El `ANEXO C` lo verifica y lista las dependencias que cruzan de una historia a otra.

### `[HU-39]` Alta de la institución educativa por seed

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-09` | Modelo de usuario con rol, y modelo de institución educativa | Pedro | ☑ |
| `TT-10` | Rutina de seed que crea la institución de referencia y dispara su invitación | Pedro | ☑ |
| `TT-11` | Pantalla de definición de contraseña a partir del token de invitación | Carlos | ☑ |
| `TT-12` | Plantilla del correo de invitación | Carlos | ☑ |

`TT-11` y `TT-12` los reutilizan `HU-03` y `HU-41`: el mecanismo de acceso es el mismo para los cuatro roles (`DEC-3`).

### `[HU-05]` Autorregistro bloqueado

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-13` | Eliminar toda ruta de registro; el usuario se crea sin contraseña utilizable | Pedro | ☑ |
| `TT-14` | Caso de prueba: intento de autorregistro desde cada una de las tres interfaces | Alejandro | ☑ |

Sostiene `INV-6` e `INVD-1`. Va temprano porque es una restricción del módulo de cuentas, no una verificación posterior.

### `[HU-40]` Alta de cuentas de cajero y administrador

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-15` | Roles y permisos por modelo según la matriz `[S11]` | Pedro | ☑ |
| `TT-16` | Servicio de alta de cuenta de personal que dispara la invitación | Pedro | ☑ |
| `TT-17` ◆ | Vista de gestión de cuentas de personal para la institución | Carlos | ☑ |

`TT-15` es la base de `INV-4`: el cajero no debe tener permiso de escritura sobre restricciones, y eso se decide aquí, no ocultando un botón en el Sprint 3.

### `[HU-41]` Contraseña por invitación para el personal

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-18` | Token de invitación de un solo uso y con caducidad | Pedro | ☑ |

El resto lo cubren `TT-11` y `TT-12`.

### `[HU-42]` Desactivación y reactivación de cuentas de personal

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-19` | Estado de la cuenta y bloqueo del inicio de sesión si está inactiva | Pedro | ☑ |
| `TT-20` ◆ | Acciones de desactivar y reactivar en la vista de cuentas | Carlos | ☑ |

### `[HU-01]` Carga masiva de estudiantes y acudientes

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-21` | Modelos de estudiante y acudiente, con vínculo de uno a varios (`ALC-IN-04`) | Pedro | ☐ |
| `TT-22` | Definición del formato del archivo: columnas, tipos y obligatoriedad | Alejandro | ☐ |
| `TT-23` | Lector del archivo y servicio de carga dentro de una transacción | Pedro | ☐ |
| `TT-24` | Pantalla de carga con selección de archivo y resultado | Carlos | ☐ |

`TT-22` es de Alejandro porque define el contrato de datos con el colegio, que es análisis, no implementación.

### `[HU-02]` Validación del archivo antes de escribir

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-25` | Validador que acumula errores por fila y **no escribe nada si hay alguno** | Pedro | ☐ |
| `TT-26` | Pantalla de reporte de errores de validación | Carlos | ☐ |
| `TT-27` | Archivos de prueba: uno válido, uno con errores y uno mixto | Alejandro | ☐ |

El «todo o nada» de `TT-25` es el criterio de aceptación de la historia, no un detalle: define si la carga es atómica.

### `[HU-03]` Invitación por correo y definición de contraseña

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-28` | Disparo de una invitación por acudiente al completarse la carga | Pedro | ☐ |

### `[HU-04]` Acudiente con varios estudiantes a cargo

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-29` | Consulta de estudiantes a cargo y selector de estudiante en la interfaz del acudiente | Carlos | ☐ |

El modelo ya lo resuelve `TT-21`; lo que falta es la interfaz.

### `[HU-14]` Generación aleatoria del código de la tarjeta

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-30` | Generador criptográfico del código, con índice único y reintento ante colisión | Pedro | ☐ |
| `TT-31` | Caso de prueba: unicidad y no secuencialidad sobre un lote grande de códigos | Alejandro | ☐ |

Sostiene `INV-7`. **No usar una secuencia ni derivar el código del identificador del estudiante**: el anteproyecto lo prohíbe explícitamente porque el código opera como credencial de acceso al saldo.

### `[HU-43]` Código de tarjeta asignado en la carga

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-32` | Asignación del código al dar de alta al estudiante, por carga masiva y por alta individual | Pedro | ☐ |

### `[HU-44]` Vista de administración de estudiantes

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-33` | Servicios de alta individual y de edición de estudiante | Pedro | ☐ |
| `TT-34` ◆ | Vista de listado, búsqueda, alta individual y edición | Carlos | ☐ |
| `TT-35` | Recorrido de experiencia de usuario de la vista de administración | Alejandro | ☐ |

### `[HU-45]` Consulta del código de tarjeta vigente

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-36` | Exposición del código vigente en la ficha del estudiante | Carlos | ☐ |
| `TT-37` | Vista imprimible del código de barras | Carlos | ☐ |

`TT-37` habilita `ENT-02`: sin tarjetas impresas no hay prueba de concepto del lector en el Sprint 2.

### `[HU-46]` Reasignación del código de tarjeta

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-38` | Servicio de reasignación que invalida el código anterior de forma definitiva | Pedro | ☐ |
| `TT-39` | Acción de reasignar en la ficha, con confirmación | Carlos | ☐ |
| `TT-40` | Caso de prueba: el código anterior deja de identificar a nadie | Alejandro | ☐ |

Sostiene `INVD-4`. Si el código anterior sigue siendo válido, `HU-47` y `HU-48` no protegen nada.

### `[HU-51]` Baja lógica del estudiante retirado

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-41` | Estado de baja en el estudiante, conservando íntegro su historial | Pedro | ☐ |
| `TT-42` ◆ | Acción de dar de baja en la ficha del estudiante | Carlos | ☐ |

Baja **lógica**: borrar el registro destruiría el historial que sostiene `INV-2`.

### `[HU-57]` Fotografía del estudiante

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-51` | Campo de clave de objeto en el estudiante y servicio de carga y reemplazo de la fotografía | Pedro | ☐ |
| `TT-52` ◆ | Carga de la fotografía desde la ficha del estudiante | Carlos | ☐ |

La base guarda **la clave del objeto, nunca el binario** (`DT-18`). La fotografía **no es obligatoria**: su ausencia no impide ninguna operación. Los avatares del seed los produce `TT-08`, que sostiene `INVD-6`.

### `[HU-26]` Administración del catálogo

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-43` | Modelos de producto, categoría y alérgeno, con **relación** producto–alérgeno | Pedro | ☐ |
| `TT-44` | Definición de los campos nutricionales que consumirán las reglas de recomendación | Alejandro | ☐ |
| `TT-45` ◆ | Vista de gestión del catálogo | Carlos | ☐ |
| `TT-46` | Caso de prueba: el alérgeno se relaciona, no se copia como lista de productos | Alejandro | ☐ |

`TT-43` es la tarea más delicada del sprint. `INV-5` exige que el bloqueo por alérgeno se aplique **sobre la condición**, de modo que cubra productos futuros. Si el alérgeno se modela como una lista de productos bloqueados, `HU-11` del Sprint 3 queda rota y hay que rehacer el modelo. `TT-44` es de Alejandro porque él define las reglas de recomendación (`[S12]`) y esos campos son su insumo.

### `[HU-59]` Imagen del producto

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-53` | Campo de clave de objeto en el producto y servicio de carga de la imagen | Pedro | ☐ |
| `TT-54` ◆ | Carga de la imagen desde la ficha del producto | Carlos | ☐ |

### Tarea transversal: datos ficticios

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-08` | Generador de datos ficticios para pruebas, con avatares (`ALC-OUT-07`, `INVD-6`) | Alejandro | ☐ |

**Va aquí porque aquí es donde queda terminada**, no porque se empiece ahora. Es la única tarea del sprint que crece por partes, a medida que aparecen los modelos:

| Se puede sembrar… | En cuanto esté |
|---|---|
| Cuentas de usuario e institución | `TT-09` |
| Estudiantes y acudientes, con sus avatares | `TT-21` (más `TT-50` y `TT-55`, ya hechos) |
| Catálogo: productos, categorías y alérgenos | `TT-43` |

Conviene montar su esqueleto —el comando y su invocación— junto a `TT-09`, y ampliarlo en cada paso. Poblar la base desde temprano es lo que permite probar lo que se va construyendo. **Terminada cuando `TT-43` lo esté**, que es el criterio de la Definición de Terminado.

---

## [S5] Tareas de gestión del Sprint

No son técnicas, pero forman parte del plan del sprint y las exige el marco de trabajo del curso.

| ID | Tarea | Responsable | Origen | Estado |
|---|---|---|---|---|
| `TT-47` | Tablero Kanban con las tareas del sprint y su estado | Naomi | `CUR-3` | ☐ |
| `TT-48` | Registro de riesgos del sprint y seguimiento en las Daily | Naomi | `ENT-04` | ☐ |
| `TT-49` | Preparación de la Sprint Review y de la Retrospective | Naomi | `EVT-3`, `EVT-4` | ☐ |

---

## [S6] Reparto por responsable

| Integrante | Rol `[S12]` | Tareas | Cuáles |
|---|---|---|---|
| **Pedro** | Desarrollador backend | **25** | `TT-02`, `TT-03`, `TT-04`, `TT-06`, `TT-09`, `TT-10`, `TT-13`, `TT-15`, `TT-16`, `TT-18`, `TT-19`, `TT-21`, `TT-23`, `TT-25`, `TT-28`, `TT-30`, `TT-32`, `TT-33`, `TT-38`, `TT-41`, `TT-43`, `TT-50`, `TT-51`, `TT-53`, `TT-55` |
| **Carlos** | Desarrollador frontend | **16** | `TT-05`, `TT-11`, `TT-12`, `TT-17`, `TT-20`, `TT-24`, `TT-26`, `TT-29`, `TT-34`, `TT-36`, `TT-37`, `TT-39`, `TT-42`, `TT-45`, `TT-52`, `TT-54` |
| **Alejandro** | Analista de datos y UX | **9** | `TT-08`, `TT-14`, `TT-22`, `TT-27`, `TT-31`, `TT-35`, `TT-40`, `TT-44`, `TT-46` |
| **Naomi** | Líder de proyecto | **5** | `TT-01`, `TT-07`, `TT-47`, `TT-48`, `TT-49` |

**Total: 55 tareas.**

---

## [ANEXO A] Riesgo de sobrecarga

El Sprint 1 concentra **18 de las 59 historias (31 %) en 2 de las 10 semanas (20 %)**, y además carga con las ocho tareas de habilitación que ninguna historia contabiliza. Es el sprint con menos velocidad del proyecto —el equipo aún está montando el entorno y aprendiendo el stack— y el que más trabajo tiene.

Sobre 2 desarrolladores, Pedro sale a **25 tareas en 10 días hábiles**. No es realista a tiempo parcial.

`DEC-8` empeoró el cuadro: añadió `HU-57` y `HU-59` con cinco tareas más. La contrapartida es que `DT-2` descarga a Carlos —siete de sus dieciséis tareas están marcadas `◆` y se reducen a declarar el modelo en el admin—, pero **ninguna de las de Pedro se reduce**.

**Tres salidas, en orden de preferencia:**

1. **Adelantar la habilitación.** `TT-01` … `TT-08` no dependen de ninguna historia y no tienen por qué esperar a la semana 6. El calendario del equipo arranca los sprints en la semana 6, pero el curso empezó en la 1. Hacer el montaje en las semanas 4–5 le devuelve al Sprint 1 unos tres días de los dos desarrolladores **sin tocar el plan**. Es la opción que recomiendo.
2. **Descargar el sprint.** `HU-42`, `HU-46` y `HU-51` pueden pasar al Sprint 2: ninguna es prerrequisito de otra historia del Sprint 1 y dos de las tres son `Should`. Deja el Sprint 1 en 15 historias y 48 tareas. El coste es que el Sprint 2 sube a 16 historias justo antes del Avance 1.
3. **Aceptar el desbordamiento y planificarlo.** Terminar el Sprint 1 con historias sin cerrar es normal en el primer sprint de un equipo nuevo. Lo que no es aceptable es descubrirlo el último día: si se elige esta vía, hay que revisar el avance en la Daily del día 5 y decidir entonces qué se mueve.

**No recomiendo** repartir tareas de backend a Carlos para equilibrar: duplicaría el trabajo de aprendizaje y ambos tocarían los mismos modelos en paralelo.

**Alejandro y Naomi tienen holgura en este sprint** (9 y 5 tareas). Es esperable —el Sprint 1 es de construcción y sus roles pesan más en los sprints 4 y 5— pero pueden absorber trabajo: la documentación técnica de `ENT-03` (modelo de datos y decisiones de diseño) se empieza mejor ahora, mientras el modelo se está decidiendo, que reconstruida al final.

---

## [ANEXO B] Nota de procedencia

Documento producido por el equipo el 2026-08-28. Es el **Sprint Backlog** en el sentido de `ART-2` de la Guía de Scrum: Objetivo del Sprint (`COM-2`), historias seleccionadas y plan para entregarlas.

Las 49 tareas se derivaron de las 16 historias del Sprint 1 de `[S5]` de `./backlog-historias-de-usuario.md`, descomponiendo cada una en el trabajo necesario para satisfacer sus criterios de aceptación, según indica `D07` de `corpus:semana-5-gestion-de-proyectos-con-metodologias-agiles.md` («conlleva a definir las tareas técnicas derivadas del objetivo de la historia»). Las ocho tareas de habilitación y las tres de gestión no provienen de una historia y se declaran como tales en `[S3]` y `[S5]`.

Los responsables se asignaron según la matriz de roles `[S12]` de `./smartfood.md`. La Guía de Scrum establece que los Developers se auto-organizan: este reparto es la previsión de Sprint Planning (`EVT-1`) y se ajusta en las Daily.

**Ninguna tarea introduce alcance.** No hay tarea que implemente algo que no esté en una historia, y no hay historia del Sprint 1 sin tareas. El stack no está decidido, así que las tareas se nombran de forma neutral; las cinco marcadas `◆` deben revisarse al fijarlo, porque un framework con panel administrativo generado absorbe buena parte de ellas.

---

## [ANEXO C] Verificación del orden de construcción

El orden en que aparecen las 55 tareas se comprobó por script contra el grafo de dependencias derivado de lo que hace cada una:

| Comprobación | Resultado |
|---|---|
| Tareas colocadas | 55 de 55, ninguna repetida |
| Tareas situadas antes de algo que las bloquea | **0** |

**Se desarrolla de arriba abajo, sin excepciones.** Al llegar a cualquier tarea, todo lo que necesita ya está hecho.

`TT-08` (datos ficticios) figuraba antes entre las tareas de habilitación y era la única excepción: necesita `TT-09`, `TT-21`, `TT-43` y `TT-50`, que aparecen después. Se movió al final de `[S4]`, donde es donde queda terminada. Sigue siendo la única tarea que se construye por partes, y allí está explicado cómo.

### Dependencias entre tareas de historias distintas

Las que no son obvias mirando solo la historia a la que pertenece cada tarea:

| Tarea | Necesita | De la historia |
|---|---|---|
| `TT-11` Pantalla de contraseña | `TT-05` Plantilla base | Habilitación |
| `TT-16` Alta de cuenta de personal | `TT-15` Roles y permisos, `TT-06` Correo | `HU-40`, habilitación |
| `TT-23` Carga del archivo | `TT-21` Modelos, `TT-22` Formato | `HU-01` |
| `TT-28` Invitación al acudiente | `TT-23` Carga, `TT-06` Correo | `HU-01`, habilitación |
| `TT-32` Código en el alta | `TT-30` Generador, `TT-23` Carga | `HU-14`, `HU-01` |
| `TT-36` Código en la ficha | `TT-32` Asignación, `TT-34` Vista | `HU-43`, `HU-44` |
| `TT-38` Reasignación | `TT-30` Generador, `TT-32` Asignación | `HU-14`, `HU-43` |
| `TT-42` Acción de baja | `TT-41` Estado, `TT-34` Vista | `HU-51`, `HU-44` |
| `TT-51` Fotografía | `TT-55` Canalización de subida, `TT-21` Modelos | Habilitación, `HU-01` |
| `TT-53` Imagen de producto | `TT-55` Canalización, `TT-43` Modelos del catálogo | Habilitación, `HU-26` |
| `TT-54` Carga de imagen | `TT-53` Campo, `TT-45` Vista del catálogo | `HU-59`, `HU-26` |

### Trabajo en paralelo

Siete tareas técnicas **no dependen de nada** y pueden arrancarse el primer día: `TT-01` (repositorio), `TT-02` (entorno), `TT-07` (Definición de Terminado), `TT-22` (formato del archivo), `TT-30` (generador de código), `TT-35` (recorrido UX) y `TT-44` (campos nutricionales). A ellas se suman las tres de gestión de `[S5]` (`TT-47`, `TT-48`, `TT-49`), que tampoco dependen de nada: diez raíces en total.

Cuatro de las siete son de Alejandro y Naomi, que en este sprint tienen holgura (`ANEXO A`). Es el trabajo con el que pueden empezar sin esperar a nadie.

`TT-30` (generador del código de tarjeta) merece mención aparte: es una función pura, no depende de modelos ni de base de datos, sostiene `INV-7` y se presta a escribir su prueba antes que su implementación. Es un buen primer commit.
