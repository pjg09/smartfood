# SmartFood — Decisiones técnicas y modelo de datos

## [S0] Bloque de control del documento

### [S0.1] Metadatos

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-TEC |
| titulo | Decisiones técnicas, arquitectura y modelo de datos del prototipo |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./smartfood.md` (`S9`, `S10`, `S11`); `./decisiones-de-alcance.md` (`DEC-1` … `DEC-7`, `INVD-1` … `INVD-5`); `./backlog-historias-de-usuario.md`; `./sprint-1-backlog.md` |
| tipo_documento | Registro de decisiones de arquitectura |
| procedencia | Copia de trabajo. El maestro estaba en el corpus documental de la asignatura (repositorio `tic1`, local). **A partir del traslado, este fichero es el vigente**: no editar la copia del corpus. |
| corresponde_a | `ENT-03` de `./smartfood.md` — «modelo de datos, diagrama de arquitectura, matriz de roles y permisos, y las decisiones de diseño con su justificación» |
| fecha_decisiones | 2026-08-29; `DT-22` el 2026-08-31; `DT-23` y `DT-24` el 2026-09-01; `DT-25` el 2026-09-08; `DT-26` el 2026-09-12; `DT-27` el 2026-09-15; `DT-28` el 2026-09-15; `DT-29` el 2026-09-16; `DT-30` y `DT-31` el 2026-09-17; `DT-32` y `DT-33` el 2026-09-18; `DT-34` el 2026-09-18; `DT-35` el 2026-09-19; `DT-37` el 2026-09-30; `DT-38` el 2026-10-01; `DT-39` el 2026-10-02; `DT-40` el 2026-10-01, ampliada el 2026-10-02 con el alta; `DT-41` y `DT-42` el 2026-10-03; `DT-43` … `DT-46` el 2026-10-12; `DT-47` y `DT-48` el 2026-10-13; `DT-49` … `DT-52` el 2026-10-14; `DT-53` y `DT-54` el 2026-10-15; `DT-55` … `DT-59` el 2026-10-17; `DT-60` y `DT-61` el 2026-10-26 |
| decidido_por | Equipo SmartFood |
| decisiones | 61 (`DT-1` … `DT-61`) |
| entidades_modelo | 18 |
| clave_primaria | UUIDv7 en todas las tablas, con una excepción declarada (`DT-17`) |
| idioma | es-CO |
| version | 2.0 |

### [S0.2] Instrucciones de lectura para el agente

1. Documento **derivado**: no reexpresa ningún original y no lleva texto verbatim.
2. **Ninguna decisión introduce alcance.** Cada una declara **qué la obliga**: la invariante, la historia o el elemento del alcance del que se deriva. Una decisión técnica sin esa columna es una preferencia disfrazada y debe cuestionarse.
3. Distinguir dos clases de decisión: las **forzadas** por una invariante —donde no hay libertad real y desviarse rompe un requisito— y las **de conveniencia**, donde había alternativas legítimas y se eligió una. `[S1]` las separa.
4. `[S2]` es el modelo de datos núcleo. Es un boceto de diseño, no un esquema final: los nombres y los campos se ajustarán al implementar, pero **la forma no** —los libros de movimientos y la relación producto–alérgeno son las decisiones que sostienen las invariantes—.
5. Los identificadores `[DT-n]` son estables y citables.

### [S0.3] Mapa de secciones

| ID | Sección | Contenido |
|---|---|---|
| S1 | Decisiones técnicas | `DT-1` … `DT-61`, separadas en forzadas y de conveniencia |
| S2 | Modelo de datos núcleo | 17 entidades y su forma |
| S3 | Cómo se sostiene cada invariante | Trazabilidad invariante → decisión |
| S4 | Lo que no se construye | Descartes explícitos |
| ANEXO A | Efecto sobre el Sprint Backlog | Tareas que cambian al fijar el stack |
| ANEXO B | Puntos abiertos | Lo que esta decisión no resuelve |
| ANEXO C | Nota de procedencia | Cómo se decidió |

---

## [S1] Decisiones técnicas

### Decisiones forzadas por una invariante

Aquí no hay libertad de diseño: desviarse rompe un requisito del anteproyecto.

#### `[DT-1]` Base de datos relacional con transacciones ACID: PostgreSQL

**Obliga:** `HU-21` exige descontar saldo y existencias **en la misma operación**. `INV-1` prohíbe que ninguna venta deje saldo negativo bajo cualquier combinación de operaciones concurrentes. `INV-2` e `INV-3` exigen reconstruir saldo y existencias desde el historial.

Con 2 a 5 cajeros cobrando en la misma ventana de veinte a treinta minutos (`USR-3`, `INT-2`), hay concurrencia real sobre las mismas filas. Se necesita bloqueo pesimista dentro de una transacción.

**Descartado:** bases documentales (MongoDB y similares). Obligarían a reimplementar a mano la atomicidad y el aislamiento que `INV-1` exige, con cuatro invariantes encima. Es el error de arquitectura más caro que este proyecto podría cometer.

#### `[DT-4]` La billetera es un libro de movimientos, no un campo de saldo

**Obliga:** `INV-2` — «el saldo debe poder reconstruirse siempre a partir del historial de movimientos» — y su prueba `TST-3`.

El saldo **se calcula** como la suma de los movimientos de la billetera. No existe una columna `saldo` que se actualice. Así `INV-2` y `TST-3` son ciertas **por construcción**, no porque se prueben: no puede haber discrepancia entre el saldo mostrado y el historial porque son el mismo dato.

**Descartado:** columna `saldo` actualizada en cada venta con el historial como registro paralelo. Es lo habitual y es exactamente lo que `INV-2` prohíbe: crea dos fuentes de verdad que pueden divergir. Si el volumen lo exigiera se podría desnormalizar dentro de la misma transacción, pero el prototipo no lo necesita.

#### `[DT-5]` El inventario es un libro de movimientos

**Obliga:** `INV-3`, `INV-8` y `TST-4`. Mismo razonamiento que `DT-4`. Las existencias son la suma de los movimientos del producto.

El motivo es **obligatorio** en toda disminución manual (`INV-8`), lo que se impone con una restricción en la base de datos, no con una validación de formulario.

#### `[DT-6]` La venta es una transacción única con bloqueo pesimista

**Obliga:** `HU-21` e `INV-1`.

Dentro de una sola transacción: se bloquean la billetera y los productos implicados, se evalúan restricciones, saldo y límite diario, y solo entonces se insertan los movimientos de billetera e inventario. Si cualquier validación falla, no se escribe nada.

El orden importa: **validar dentro del bloqueo, no antes.** Validar fuera y escribir después abre la ventana en la que dos cajeros cobran a la vez y ambos ven saldo suficiente.

#### `[DT-7]` Los alérgenos son una relación evaluada en el momento de la venta

**Obliga:** `INV-5` — «el bloqueo por alérgeno se aplica sobre la condición, no sobre una lista fija de productos».

Dos tablas: `producto_alergeno` y `restriccion_alergeno`. El rechazo de `HU-18` es una consulta que cruza ambas en el momento del cobro. Un producto que se agregue al catálogo mañana queda cubierto automáticamente si declara ese alérgeno.

**Descartado:** materializar la lista de productos bloqueados por estudiante. Es más rápido de consultar y **rompe `INV-5`**: los productos futuros no quedarían cubiertos, que es justo lo que la invariante protege.

#### `[DT-8]` La información nutricional se copia en la línea de venta

**Obliga:** `HU-22` y `ALC-IN-20` — el historial muestra la información nutricional «tal como estaba declarada al momento de la venta».

La línea de venta guarda una instantánea de los valores nutricionales y del precio. No referencia al producto para esos datos.

**Descartado:** referenciar el producto actual. Editar un producto reescribiría el pasado y `HU-22` dejaría de cumplirse.

#### `[DT-9]` El código de tarjeta se genera con un generador criptográfico

**Obliga:** `INV-7` — aleatorio y no secuencial, porque «opera como una credencial de acceso al saldo del estudiante».

Generación con la primitiva criptográfica del lenguaje, índice único y reintento ante colisión.

**Descartado:** secuencia, identificador del estudiante, o cualquier valor derivado de otro campo. `ALC-IN-12` lo prohíbe explícitamente: no debe poder deducirse a partir de otro.

#### `[DT-10]` No existen rutas de registro; el acceso se establece por token de invitación

**Obliga:** `INV-6` e `INVD-1` — ninguna cuenta con acceso a datos de menores se crea por autorregistro, y eso vale para los cuatro roles (`DEC-2`, `DEC-3`).

El usuario se crea sin contraseña utilizable y recibe un token de un solo uso y con caducidad. Las rutas de registro no se ocultan: **no existen**.

#### `[DT-11]` Los permisos se aplican en la capa de datos, no en la interfaz

**Obliga:** `INV-4` — las restricciones no pueden ser desactivadas por el personal de la cafetería ni por la institución.

La matriz `[S11]` se traduce a permisos por rol sobre cada modelo. El cajero **no tiene** permiso de escritura sobre restricciones. Ocultar el botón en la plantilla no es cumplir `INV-4`: es aparentarlo.

#### `[DT-12]` El estado del estudiante es una máquina de estados explícita

**Obliga:** `INVD-2`, `INVD-3`, `DEC-5` y `DEC-7`.

Tres estados: `activo`, `desactivado`, `baja`. La desactivación la aplican institución o acudiente; **la reactivación solo la institución**, con independencia de quién desactivó. La baja es un estado distinto y conserva íntegro el historial.

**Descartado:** un booleano `activo`. No distinguiría «perdió la tarjeta» de «se retiró del colegio», que `DEC-7` exige separar.

#### `[DT-17]` UUIDv7 como clave primaria, **excepto** el código de tarjeta

**Obliga (la excepción):** `INV-7` — el código de tarjeta debe ser aleatorio y **no secuencial**, «de forma que no pueda deducirse a partir de otro».

Todas las tablas usan **UUIDv7** como clave primaria: al llevar un prefijo de marca de tiempo, va ordenado y conserva la localidad de los índices B-tree, que es justo lo que UUIDv4 destruye. Se genera **en la aplicación**, no en la base de datos, para no depender de la versión de PostgreSQL y para que las pruebas no necesiten conexión.

**El `codigo_tarjeta` no puede ser un UUIDv7.** UUIDv7 es ordenado por construcción y filtra el instante de creación: dos estudiantes cargados en la misma tanda tendrían códigos casi contiguos, que es exactamente lo que `INV-7` prohíbe. El código se genera con la primitiva criptográfica del lenguaje (`DT-9`), con 12 a 16 caracteres alfanuméricos e índice único.

Hay además una razón práctica: un código de barras Code 128 con los 36 caracteres de un UUID produce una etiqueta larga y más lenta de escanear, y `INT-2` tiene una ventana de veinte a treinta minutos.

> **Efecto lateral declarado:** con UUIDv7 como clave de `Estudiante`, el identificador filtra cuándo se matriculó. Es irrelevante en un prototipo con datos ficticios, pero debe recogerse como limitación en `ENT-06`.

#### `[DT-20]` Las imágenes se re-codifican en el servidor y se les retira el EXIF

**Obliga:** `DEC-8` y `ALC-OUT-08`.

Toda imagen se sube **a través de la aplicación**, nunca del navegador directamente al bucket. Antes de almacenarse se abre, se redimensiona a un máximo y se vuelve a codificar a JPEG o WebP. Solo se aceptan `image/jpeg`, `image/png` y `image/webp`, **validados por contenido y no por la extensión del nombre**.

Dos razones, y la segunda es la que pesa:

1. **Superficie de ataque.** Una imagen servida tal como se subió es un vector de XSS: un SVG admite `<script>`, y existen ficheros políglotos que el navegador interpreta como HTML. Re-codificar los neutraliza.
2. **El EXIF de una fotografía tomada con un móvil contiene coordenadas GPS.** Sin retirarlo, el sistema almacenaría y serviría **el lugar donde se fotografió a un menor**. Con `ALC-OUT-08` invocando la Ley 1581 de 2012, eso deja de ser un detalle técnico. El re-encodado descarta el EXIF de paso.

**Descartado:** subida directa del navegador al bucket con política firmada. Con el volumen del prototipo no aporta rendimiento y traslada al cliente una validación que debe ser del servidor.

### Decisiones de conveniencia

Aquí sí había alternativas legítimas. Cada una declara la que se descartó y por qué.

#### `[DT-2]` Django como framework de aplicación

**Razón:** con 2 desarrolladores y 10 semanas para 56 historias, lo que decide el proyecto es cuánto código **no** se escribe. Django resuelve de fábrica tres cosas que están en el camino crítico:

| Necesidad | Qué la cubre |
|---|---|
| `INT-3` — catálogo, inventario, reportes y carga de estudiantes | El admin generado |
| `HU-03`, `HU-39`, `HU-41` — invitación por correo y contraseña propia | El flujo de token de restablecimiento |
| Matriz `[S11]` — permisos por rol | Grupos y permisos por modelo |

Además `select_for_update()` y el manejo de transacciones son de primera clase, que es lo que `DT-6` necesita.

**Honestidad sobre el descarte:** el equipo domina Python, TypeScript, PHP y Java, así que ninguna opción quedaba fuera por desconocimiento.

- **Laravel + Filament es co-equivalente.** Filament genera un panel administrativo tan bueno como el admin de Django y cubre las mismas tres necesidades. El desempate es débil: Django trae el admin en el núcleo sin dependencia extra, y Python le sirve a Alejandro para prototipar las reglas de recomendación contra los mismos modelos. **Si el equipo prefiere PHP, cambiar a Laravel + Filament no degrada el proyecto.**
- **Next.js + Prisma** obliga a construir el panel administrativo y la autenticación por invitación a mano. Son semanas que no sobran.
- **Spring Boot + React** es el más verboso y son dos aplicaciones que integrar. Descartado por plazo, no por calidad.

#### `[DT-3]` Monolito con plantillas y HTMX, sin API

**Razón:** decisión del equipo. Una sola aplicación, un repositorio, un despliegue, cero coste de integración. El reparto de `[S12]` se mantiene limpio: Pedro posee modelos, servicios y transacciones; Carlos posee plantillas, estilos y el punto de venta.

**Descartado:** API + SPA. Es mejor arquitectura y le daría a Carlos un frontend propio, pero duplica el trabajo de las tres interfaces y añade una API que mantener. **Si en algún momento el punto de venta (`INT-2`) resulta demasiado lento con plantillas, la salida es introducir React solo ahí**, no reescribir las tres interfaces.

#### `[DT-15]` Monolito modular por dominio, con capa de servicios

**Razón:** separar dónde vive cada cosa sin añadir capas que no compran nada.

Una app de Django por dominio —`cuentas`, `personas`, `catalogo`, `billetera`, `inventario`, `ventas`, `restricciones`, `reportes`— y dentro de cada una la misma forma:

`restricciones` no estaba en la lista original y **se añadió por decisión, no por costumbre**: la razón por la que no cabía en ninguna de las siete está en `DT-28`.

| Archivo | Responsabilidad |
|---|---|
| `models.py` | Estructura e invariantes de datos (`CheckConstraint`, `UniqueConstraint`). Sin lógica de negocio |
| `services.py` | **Toda escritura.** Funciones, no clases; cada una abre su `transaction.atomic()` |
| `selectors.py` | **Toda lectura** no trivial. No conocen `request` |
| `views.py` | HTTP: parsear, delegar, renderizar. **Cero lógica de negocio** |

Tres reglas lo sostienen:

1. **Una vista nunca escribe directamente**: llama a un servicio. Así `vender()` es una sola función invocable desde la vista, desde una prueba y desde el shell, y `DT-6` vive en un único sitio auditable.
2. **La invariante que la base pueda imponer, la impone la base.** `INV-8` es un `CheckConstraint`, no un `if`: un `if` se olvida en el siguiente camino de escritura, una restricción no.
3. **Los servicios no saben de HTTP.**

**Descartado:** arquitectura hexagonal con puertos y adaptadores, patrón repositorio envolviendo el ORM, e interfaces abstractas «por si cambiamos de base de datos». Añaden indirección sin comprar nada: `DT-1` fija PostgreSQL como requisito, no como opción. Con 2 desarrolladores y 10 semanas, pelearse con el framework cuesta velocidad.

#### `[DT-16]` Frontend renderizado en servidor con HTMX

**Razón:** `DT-3`. Tres bases de plantilla, una por interfaz (`INT-1`, `INT-2`, `INT-3`), y fragmentos en `partials/`.

**Regla que lo mantiene limpio:** una vista HTMX devuelve **un fragmento**, nunca una página. Si un mismo endpoint devuelve a veces una cosa y a veces la otra, en pocas semanas nadie sabe cuál. Se separan: `venta_pagina` y `venta_fragmento`.

**El punto de venta (`INT-2`) se diseña aparte**, porque es la única interfaz con exigencia real —toda la demanda en veinte a treinta minutos—:

- Un campo oculto con foco permanente que lo recupera al perderlo. El lector es un teclado: teclea el código y envía Enter, lo que dispara la petición.
- La respuesta reemplaza el panel del estudiante: fotografía (`HU-58`), saldo, consumo del día y restricciones (`HU-17`).
- **Sin diálogos de confirmación.** Cada uno cuesta un clic y un segundo por venta.
- Todo navegable con teclado: el cajero no debería tocar el ratón.
- **Sin JavaScript de estado**: el carrito vive en la sesión y cada gesto devuelve un fragmento (`DT-26`, que corrige la previsión de Alpine.js de esta misma decisión). En acudiente y administración, HTMX solo.

`INT-3` lo cubre el admin (`DT-2`), **con una excepción declarada**: el padrón de la institución tiene pantalla propia porque es la que secretaría abre a diario y la única que responde quién sigue sin activar su cuenta (`DT-27`). Tailwind se compila con su CLI, sin CDN.

#### `[DT-13]` Despliegue en PaaS con PostgreSQL gestionado

**Razón:** `ENT-01` exige un prototipo «desplegado en un entorno de pruebas», y la Definición de Terminado del Sprint 1 exige que cada historia se demuestre en el entorno desplegado, no solo en local. Un PaaS (Railway, Render o equivalente) lo resuelve en una tarde.

**Descartado:** servidor propio o contenedores orquestados. `ALC-OUT-06` excluye el despliegue en una institución real; no hay ningún requisito que justifique esa complejidad.

#### `[DT-18]` Almacenamiento de objetos para las imágenes

**Obliga:** `DEC-8` — fotografía del estudiante e imagen del producto.

Bucket compatible con S3. La base de datos guarda **la clave del objeto, nunca el binario**.

**Descartado:** el sistema de archivos del servidor. En un PaaS el disco es efímero (`DT-13`) y las imágenes se perderían en cada despliegue.

**Dos buckets, no uno**, porque las políticas de acceso son opuestas:

| Bucket | Contenido | Política |
|---|---|---|
| `smartfood-privado` | Fotografías de estudiantes | Privado; se sirve con URL firmada de caducidad corta |
| `smartfood-publico` | Imágenes de productos | Lectura pública |

La fotografía de un menor no puede quedar accesible por una URL adivinable (`DEC-8`, `ALC-OUT-08`). La imagen de un producto no es sensible, y firmar cincuenta URL para pintar la lista del punto de venta es coste sin contrapartida. Con un solo bucket habría que sostener políticas distintas por prefijo; con dos, la separación queda explícita en el código.

**En local, MinIO en el mismo `docker compose` que PostgreSQL.** `TT-02` pide un entorno «reproducible» y el equipo son cuatro personas en sistemas posiblemente distintos; PostgreSQL ya tiene que estar ahí, así que MinIO son unas líneas más.

El motivo de usar MinIO y no el sistema de archivos **no es la paridad de API** —`django-storages` hace que el código sea idéntico y `foto.url` funcione en ambos— sino la **paridad de control de acceso**. Con almacenamiento local todo es público por defecto: se escribe la etiqueta de imagen, funciona, y nadie nota nada. En producción esa misma URL tiene que ir firmada y caducar. Desarrollar contra el sistema de archivos significa que la primera prueba del comportamiento real de acceso ocurre en el entorno desplegado, sobre fotografías de menores. Es donde menos conviene descubrirlo tarde.

> **Plan B declarado:** si a algún integrante Docker le resulta un obstáculo, el ajuste `STORAGES` por variable de entorno le permite trabajar con sistema de archivos local. Diverge solo en el comportamiento de las URL firmadas. **No es el modo por defecto**, pero es preferible a bloquear a alguien un día.

En producción, el bucket del propio PaaS, para no añadir un segundo proveedor. `DT-18` no fija cuál a propósito.

`INVD-6` es una regla de operación, no de esquema: **ninguna fotografía del prototipo corresponde a una persona real.** Se garantiza en el generador de datos ficticios (`DT-14`), que produce avatares.

---

#### `[DT-21]` Un bucket con dos prefijos, y ninguno público

**Corrige:** `DT-18`, que preveía **dos** buckets con políticas opuestas —uno privado y otro de lectura pública—.

**El hecho que lo obliga:** el proveedor del entorno de pruebas (`DT-13`) **no ofrece buckets públicos en ningún plan**. Su documentación es explícita: *«Buckets are private; there are no public bucket URLs»* y *«there is no public-bucket mode to accidentally enable»*. No es un límite del plan gratuito que se resuelva pagando: no existe la funcionalidad. El plan gratuito añade, además, un tope de **un bucket por proyecto**.

**Decidido:**

- **Un bucket**, con dos prefijos: `privado/` para las fotografías de estudiantes y `publico/` para las imágenes de producto.
- En el código siguen existiendo **dos almacenamientos lógicos** de Django, `privado` y `publico`. Que apunten a un bucket con prefijos o a dos buckets es **configuración**, no diseño: pasar a dos es cambiar dos rutas.
- **La misma topología en local**, sobre MinIO, aunque MinIO sí soporte políticas públicas.
- Las **fotografías de estudiantes** se sirven con URL firmada de caducidad corta, como preveía `DT-18`. Esto no cambia.
- Las **imágenes de producto** las sirve la aplicación, leyéndolas del bucket y devolviéndolas con una cabecera de caché larga.

**Por qué la misma topología en local.** `DT-18` justificó MinIO —en vez del sistema de archivos— por la **paridad de control de acceso**: que el comportamiento real de acceso se pruebe en el portátil y no por primera vez en el entorno desplegado, sobre fotografías de menores. Un bucket público en local y ninguno desplegado rompería exactamente esa paridad: se escribe la etiqueta de imagen, funciona en local, y falla desplegada. La divergencia se descubriría donde `DT-18` quería evitar descubrirla.

**Por qué la aplicación sirve las imágenes de producto y no se firman.** `DT-18` descartó firmar las imágenes de producto porque *«firmar cincuenta URL para pintar la lista del punto de venta es coste sin contrapartida»*. Ese argumento **está mal medido**: firmar es un HMAC local, del orden de microsegundos, y cincuenta firmas no se notan.

El problema real de la URL firmada es otro: **caduca, así que cambia en cada pintado**, y una URL que cambia no la puede cachear el navegador. `INT-2` debe atender toda la demanda en veinte a treinta minutos; descargar el catálogo de imágenes entero en cada refresco es justo lo que no puede permitirse. Servirlas desde la aplicación da una **URL estable y cacheable**: el navegador las pide una vez. Es también el patrón que el proveedor documenta para este caso.

El coste es que los bytes pasan por el proceso de la aplicación la primera vez. Con un catálogo de decenas de productos y caché de navegador, es asumible; si dejara de serlo, la salida es una caché delante, no volver a firmar.

**Lo que no cambia de `DT-18`:** la base guarda **la clave del objeto, nunca el binario**; la fotografía de un menor no queda accesible por una URL adivinable; y `INVD-6` sigue vigente.

> **Sobre el nombre `publico`.** En este proyecto significa **«no sensible»**, no «accesible sin credenciales». Ningún objeto del prototipo es accesible sin credenciales. Conviene recordarlo al leer el código: el alias engaña si se lee con la definición de `DT-18`.

---

#### `[DT-14]` Datos ficticios generados programáticamente

**Razón:** `ALC-OUT-07` exige datos ficticios y `ALC-OUT-08` explica por qué: el tratamiento de datos personales de menores exige autorización de sus titulares conforme a la Ley 1581 de 2012. **Ningún dato real de ningún estudiante entra en el repositorio ni en el entorno de pruebas.**

#### `[DT-19]` Tercera forma normal, con una aparente excepción que no lo es

**Obliga:** decisión del equipo, y coincide con lo que las invariantes ya exigían.

El esquema está en 3NF. Conviene notar que **`DT-4` y `DT-5` son consecuencia de ello**: un saldo o unas existencias almacenadas serían un valor derivable de la suma de un libro de movimientos, es decir, precisamente la redundancia que 3NF elimina. La exigencia de normalización y las invariantes `INV-2` e `INV-3` empujan en la misma dirección.

**La instantánea de `DT-8` parece una desnormalización y no lo es.** «La información nutricional que este producto declara hoy» y «la que declaraba cuando se vendió» son **dos hechos distintos**. El segundo depende funcionalmente de la clave de la línea de venta, no de la del producto, así que almacenarlo no es redundancia sino registrar un hecho que ninguna otra tabla contiene. Normalizarlo referenciando al producto actual haría que editar un producto reescribiera el pasado, y `HU-22` dejaría de cumplirse.

#### `[DT-22]` Code 128 generado en el servidor, en SVG y con medidas en milímetros

**Razón:** `TT-37` exige una vista imprimible y `ENT-02` es una prueba de concepto **con tarjetas físicas y un lector**. Esto cierra el punto abierto que el `ANEXO B` registraba: faltaba decidir la simbología y dónde se genera.

**Simbología: Code 128, subconjunto B.** Codifica dígitos y mayúsculas, que es el alfabeto del código de tarjeta (`DT-9`), y es lo que todo lector USB trae activado de fábrica. Con 14 caracteres produce un símbolo de 189 módulos: **69 mm impreso**, zonas mudas incluidas, que cabe con margen en una tarjeta de 85,6 mm.

**Descartado `EAN-13`**, que era la otra candidata. Son trece **dígitos** con dígito de control, asignados por GS1 para identificar productos de venta al público. Nuestro código es alfanumérico y es un identificador interno: no hay prefijo de empresa que pedir ni catálogo global en el que registrarlo. Usarlo obligaría a cambiar el código de tarjeta a numérico y a perder entropía justo donde `INV-7` la pide.

**Descartado `Code 39`**, que también admite el alfabeto: produce un símbolo un tercio más ancho para el mismo contenido, y no aporta nada a cambio.

**Generado en el servidor, no en el navegador.** Un código de barras rasterizado a la resolución de la pantalla se imprime borroso y deja de leerse. El SVG lleva el ancho en milímetros y sale del papel con la medida que se le pidió, sea cual sea la pantalla. Generarlo en el navegador obligaría además a vendorizar una biblioteca de JavaScript y a que la página imprimible dependiera de que ese script corriera.

**Ancho de módulo 0,33 mm y zona muda de 10 módulos.** La norma admite bajar a 0,19 mm, pero eso es impresión industrial y lectores de gama alta; `ENT-02` va a tener una impresora de oficina y un lector económico. La zona muda no es margen estético: sin ella el lector no encuentra dónde empieza el símbolo.

**La codificación la hace `python-barcode`; el dibujo es nuestro.** Escribir a mano el codificador de Code 128 —tres subconjuntos, suma de control en base 103, patrón de parada de trece módulos— es la clase de código que `DT-2` dice que no hay que escribir: un error sutil no se ve en pantalla, se ve cuando las tarjetas ya están impresas y el lector no las lee. El dibujo sí es nuestro, porque el SVG tiene que ir **en línea** en la página y con las medidas de arriba.

**Nada se almacena.** El símbolo se genera en cada petición a partir del campo del estudiante. Es lo que sostiene el segundo criterio de `HU-45`: una imagen guardada seguiría enseñando un código correcto después de que `HU-46` lo reasignara, y esa tarjeta impresa ya no abre ningún saldo (`INVD-4`).

#### `[DT-23]` El sistema visual se adopta entero de un producto ya validado, no se diseña aquí

**Razón:** decisión del equipo, tomada el 2026-09-01. No la obliga ninguna invariante: `DT-16` fija el stack de la interfaz (Tailwind y HTMX) pero no dice de qué color es nada, y hasta aquí la paleta era una elección provisional del andamiaje de `TT-05`.

**Qué se adopta.** La paleta de marca (marino `#1A375C`, teal `#278FA2`, verde agua `#5BADA4`, verde bosque `#3C755D`), la tipografía (Poppins para titulares, Inter para cuerpo), la escala de espaciado y tamaños, los tres puntos de ruptura con nombre (`tablet`, `escritorio`, `amplio`) y la estructura de pantalla: barra superior flotante, barra lateral oscura que se colapsa, y pantallas de puerta a dos columnas con panel de marca.

**De dónde sale.** De un producto en producción del mismo dominio —gestión de cafeterías escolares— cuyos contrastes están medidos uno a uno y cuya interfaz ya pasó por usuarios reales. **La alternativa era diseñar un sistema visual desde cero para un prototipo de cinco sprints**, con dos personas desarrollando, y llegar a la sustentación con una paleta que nadie ha comprobado. Adoptar uno validado no ahorra trabajo: ahorra el riesgo de que la interfaz sea el eslabón sin verificar de un proyecto donde todo lo demás está justificado.

**Lo que NO se adopta: la identidad.** SmartFood no lleva el logotipo, el nombre ni la marca de ese producto. El logotipo es tipográfico —la palabra, con «Food» en el acento— y se genera desde la propia hoja de estilos. Un prototipo académico firmado con la marca de una empresa cuenta algo que no es cierto sobre quién lo hizo y para quién.

**Un solo fichero con colores literales: `estilos/fuente.css`.** Todo lo demás usa **alias de intención** (`superficie`, `texto`, `primario`, `acento`, `error`), nunca la paleta cruda ni la de fábrica de Tailwind, que se borra entera con `--color-*: initial`. Dos plantillas quedan fuera y las dos por el mismo motivo —no cargan la hoja, así que un token ahí no resolvería a nada—: el correo de invitación (los clientes de correo descartan las variables CSS) y `admin/base_site.html` (incluir Tailwind en el admin traería su `preflight` y desarmaría `INT-3`). `config/tests_plantillas.py` vigila las dos reglas: ni un hexadecimal suelto, ni una clase de la paleta de fábrica —que, borrada la paleta, **no pinta nada y tampoco da error**.

**Dos temas, claro y oscuro, y el oscuro no es el claro invertido.** El primario deja de ser el marino y pasa a ser el teal, el texto que va encima pasa a ser oscuro (el blanco sobre teal se queda en 3,79 y no cumple AA), y la elevación la da el color en vez de la sombra. Hay además cuatro constantes que **no cambian entre temas** —`sobre-oscuro`, `accion-clara`, `acento-claro` y las de papel—, porque el héroe es marino y el papel es blanco en los dos temas: ahí los alias que siguen al tema dejarían tinta casi negra sobre marino, o una hoja impresa casi en blanco.

**El tema oscuro no se imprime.** Se apaga en el origen, acotando los dos bloques oscuros a `@media screen`, y no persiguiendo tokens dentro de `@media print`: así la impresión cae sola en el tema claro y cualquier pantalla imprimible que se añada mañana ya sale bien. Lo que se imprime hoy es la tarjeta de `TT-37`, que es papel de verdad (`ENT-02`).

**`INT-3` se tematiza, no se reescribe.** El admin de Django ya está escrito contra sus propias variables CSS (`--primary`, `--header-bg`, …), así que hablar el idioma de la marca cuesta un `admin/base_site.html` que las redefine — y desde `DT-27`, también la composición: píldoras en la barra lateral, títulos en el tipo de display y tabla con la cabecera tintada, todo con CSS sobre las clases que Django ya emite. Rehacer sus plantillas sería construir a mano justo lo que `DT-2` decidió no construir; la única pantalla que sí se construyó, y por qué, está en `DT-27`.

**Consecuencia sobre `DT-16`.** Sigue vigente y sin cambios: una vista HTMX devuelve un fragmento, nunca una página. Lo que `DT-23` añade es que hay **tres armazones** —`base-publica.html`, `base-acceso.html` y `base-aplicacion.html`— colgando de una base común, y que `INT-2` tendrá el suyo en el Sprint 2.

#### `[DT-24]` Los dos libros de movimientos tienen un único punto de asiento

**Obliga:** `INV-2`, `INV-3` e `INVD-2`, y la forma en que `DT-4` y `DT-5` las sostienen.

`DT-4` y `DT-5` dicen que el saldo y las existencias **son** la suma de su historial. Eso hace ciertas `INV-2` e `INV-3` por construcción, pero deja abierta la otra mitad del problema: **quién puede escribir en esos libros y qué comprueba antes**.

Ninguna función escribe un `MovimientoBilletera` ni un `MovimientoInventario` por su cuenta. Las dos apps exponen una función `asentar()` y **todo movimiento pasa por ella**: la recarga de `HU-06`, el ingreso de `HU-27`, la venta de `HU-21` y lo que venga después.

**El problema que resuelve no es la duplicación, es el olvido.** `INVD-2` —ni desactivado ni de baja se compra ni se recarga— estaba escrita desde el Sprint 1, y `recargar` la llamaba. Pero eso solo protege a los servicios que se acuerden de llamarla, y el servicio de venta (`TT-80`) se escribe dos semanas después, por otra persona y en otra app. Una regla que depende de la memoria de quien escriba el siguiente servicio no es una regla: es una costumbre.

**Qué comprueba `asentar()` y qué no.** Comprueba lo que es igual venga de donde venga: la forma del movimiento —signo según tipo, cantidad distinta de cero, motivo obligatorio en la merma (`INV-8`)— y, en la billetera, que el estudiante esté en condiciones de operar (`INVD-2`). **No comprueba quién es el actor**, y eso es deliberado: cada operación tiene su propia regla de quién puede —recargar es del acudiente (`HU-06`), cobrar es del cajero (`[S11]`), ingresar mercancía es de la administración (`HU-27`)— y la aplican los servicios de arriba. Meter un `actor` en `asentar()` obligaría a inventar uno en la venta, donde quien opera es el cajero sobre la billetera de un tercero.

**La devolución no opera, corrige.** En la billetera, `TIPOS_QUE_OPERAN` deja fuera la devolución: un estudiante que se retiró del colegio con una venta mal cobrada tiene derecho a que se le corrija, y bloquear esa corrección dejaría su historial diciendo algo que no pasó — justo lo que `INV-2` existe para evitar. `HU-52` prohíbe **comprar y recargar** sobre el saldo congelado; no, corregir.

**Esto no sustituye a las restricciones de la base.** El signo y el motivo los impone además una `CheckConstraint` (`DT-15`, segunda regla): `asentar()` comprueba antes para dar un mensaje que se entienda, no para reemplazarla. Si algún día alguien escribe un movimiento con el ORM directamente, la base sigue diciendo que no.

**Descartado: señales de Django (`post_save`) para la comprobación.** Funcionaría y sería invisible, que es el problema — una regla que se dispara desde un fichero que nadie está leyendo es imposible de seguir cuando falla. La función con nombre se ve en la traza y se lee desde el servicio que la llama.

---

#### `[DT-25]` La adopción del sistema visual se completa pantalla por pantalla, no solo en los tokens

**Razón:** decisión del equipo, tomada el 2026-09-08. **Corrige el alcance de `DT-23`, no su contenido**: aquella decidió *qué* sistema visual se adopta y trajo la paleta, la tipografía y los tres armazones; esta declara que adoptarlo incluye también las **composiciones** —cómo se arma una pantalla con esas piezas— y no solo los valores.

**Qué obligó a declararlo.** Con los tokens puestos, cada pantalla nueva seguía inventando su propia disposición: una lista donde la referencia usa tabla, un botón sólido donde usa un enlace, un campo de archivo desnudo donde usa una zona de arrastre. El resultado eran ocho pantallas con la misma paleta y ocho gramáticas distintas, que es exactamente el problema que `DT-23` vino a evitar, un escalón más arriba.

**Las composiciones que quedan fijadas.** Son las que ya usan dos o más pantallas, no un catálogo por si acaso:

| Composición | Dónde | Cómo es |
|---|---|---|
| Tarjeta de resumen | panel del acudiente, portada | Franja de serie arriba, icono en pastilla, rótulo, cifra en `font-display`, texto de apoyo y **enlace de acento** pegado abajo con `mt-auto` |
| Tabla de datos | movimientos del acudiente | Cabecera tintada con icono por columna, filas alternas, importe a la derecha. **Fichas por debajo de `tablet`** |
| Encabezado de sección | portada | Antetítulo en versalitas y acento, título en `font-display`, entradilla, todo centrado |
| Pastilla de sesión | barra de la aplicación y del punto de venta | Nombre y rol con borde, **nunca el correo** |
| Grupo de modos | punto de venta, selector de tema | Botones con `aria-pressed`, icono sobre etiqueta cuando la columna es estrecha |
| Bloque punteado | huecos y estados vacíos | Borde discontinuo, icono en pastilla, qué falta y qué historia lo trae |

**Un hueco no se dibuja como una acción apagada.** Un botón deshabilitado promete que un día hará algo, no dice cuándo ni de qué depende, y en la caja invita a pulsarlo esperando que reaccione. El bloque punteado con el identificador de la historia dice las dos cosas. `ventas/tests_acceso.py` lo vigila.

**Lo que se copia de la referencia se copia; lo que afirmaría algo falso, no.** La pantalla de recarga es el caso: se adopta su distribución de dos columnas y sus atajos de importe, y se descartan su línea de costo de servicio —aquí no hay pasarela (`ALC-OUT-01`), y un «Servicio $0» sugiere que algún día la habrá— y su total vivo recalculado en el navegador, que exigiría un segundo formateador de dinero y rompería la regla de `TT-64`. Copiar una forma no puede traerse una afirmación que en este sistema no es cierta.

**El separador de los títulos de pestaña es una barra vertical.** `Entrar | SmartFood`, no `Entrar · SmartFood`. El punto medio se sigue usando dentro del texto —donde separa ideas de una misma frase—, pero en el título compite con el nombre del producto y en una pestaña estrecha, truncado, deja «Entrar ·» sin decir de qué. La barra es lo que usa el admin de Django, así que las dos mitades del sistema titulan igual.

**El formato del dinero pasa a `$25.000`, sin espacio, con la divisa opcional detrás.** El espacio no salía de ninguna decisión y dejaba el símbolo suelto en una columna alineada a la derecha. `{{ saldo|dinero:"COP" }}` añade el código, y **solo se usa en las cifras grandes**: repetirlo en quince filas de una tabla donde todo son pesos es ruido.

**La ruta de acceso pasa a ser `/login/`.** Es una URL que la gente lee y teclea, y `login` es la palabra que espera de un producto web; el resto de las rutas siguen en español porque nombran cosas del dominio (`/carga/`, `/mis-estudiantes/`, `/punto-de-venta/`). **El nombre interno sigue siendo `acceso`**, que es lo que leen `LOGIN_URL`, doce `{% url %}` y once pruebas: ahí manda la convención del repositorio, y renombrarlo no habría cambiado nada en pantalla. `DEC-12` conserva `/acceso/` porque un registro de decisión no se reescribe; la ruta vigente es la de aquí.

**Consecuencia sobre `DT-16`.** Sigue vigente. Lo que `DT-25` añade es que los armazones son cuatro y no tres —`base-punto-de-venta.html` ya existe— y que el del punto de venta lleva una columna de iconos que **no se despliega**: no es la barra de `INT-1` con otro estado, es lo que esa barra es allí.

---

#### `[DT-26]` El carrito del punto de venta vive en el servidor, no en el navegador

**Corrige:** `DT-16`, que preveía **Alpine.js** «solo aquí, para el estado local del carrito». La decisión de `DT-16` sobre HTMX y sobre los fragmentos sigue entera; lo único que se retira es esa frase.

**El hecho que lo obliga: el dinero se escribe en un solo sitio.** Un carrito en el navegador tiene que pintar el importe de cada renglón y el total mientras el cajero los toca, y eso exige **un segundo formateador de dinero en JavaScript** junto al de `billetera/templatetags/dinero.py`. El día que cambie el formato —y ya cambió una vez, en `DT-25`— la misma pantalla enseña dos monedas.

No es una preocupación hipotética: **`DT-25` ya descartó exactamente esto por su nombre** al adoptar la pantalla de recarga, donde se rechazó «su total vivo recalculado en el navegador, que exigiría un segundo formateador de dinero y rompería la regla de `TT-64`». Lo que `DT-26` hace es aplicar esa misma regla donde más cifras hay.

**Decidido:**

- El carrito y el estudiante al que se le está cobrando viven en la **sesión** (`ventas/carrito.py`).
- Cada gesto —añadir, descontar, quitar, vaciar— es un `POST` que devuelve **el fragmento del ticket** (`DT-16`).
- **No se añade Alpine.js.** El proyecto sigue con HTMX y un único `interfaz.js` sin dependencias.

**Lo que cuesta y por qué se acepta.** Un viaje al servidor por toque, en lugar de ninguno. En la práctica es una petición que devuelve un fragmento pequeño contra un servidor en la misma red del colegio, mientras que la alternativa ahorra esos viajes y añade una segunda fuente de verdad —el carrito del navegador y el que el cobro valida— más un formateador duplicado. `INT-2` pide velocidad, y la petición que de verdad importa por su latencia es la del escaneo, que no cambia.

**Lo que gana además, y no estaba en el argumento original:** el carrito **sobrevive a un refresco**. En una caja, perder la venta montada porque alguien rozó `F5` es un error que se paga con la fila esperando.

**Lo que no cambia.** Nada de esto autoriza nada: `registrar_venta` vuelve a validarlo todo contra la base, dentro del bloqueo (`DT-6`). La sesión es comodidad de pantalla, no fuente de verdad.

---

#### `[DT-27]` El padrón tiene pantalla propia; el resto de `INT-3` sigue siendo el admin

**Corrige parcialmente:** `DT-2`, que decía que `INT-3` **no lleva plantillas propias**. Sigue siendo cierto para todo menos para una lectura, y esta decisión declara cuál y por qué, para que la excepción no crezca sola.

**El hecho que lo obliga.** Al comparar el producto con su referencia visual (`DT-23`) se vio que la institución tiene dos experiencias distintas: la pantalla de carga, que es del sistema visual, y el padrón, que es el admin de Django con nuestros colores — barra lateral de Django, breadcrumbs, «Escoja estudiante a modificar» y un desplegable de acciones. La institución abre el padrón **a diario**; es la pantalla que más ve y la única que no parece del producto.

Hay además una razón que no es de estética: **el admin no responde la pregunta que secretaría trae.** La carga masiva genera la invitación pero no la entrega (`DEC-9`), así que la pregunta diaria es «quién sigue sin activar su cuenta», y en el admin eso son dos filtros y una columna que no existe.

**Decidido:**

- `/padron/` es una pantalla propia, con el sistema visual: buscador sobre nombre, documento, tarjeta y acudiente; interruptor de retirados; tabla de datos; y el recuento de cuentas sin activar.
- **Solo lee.** Dar de alta, editar, dar de baja y reasignar la tarjeta siguen siendo del admin: cada fila enlaza allí. No hay servicio detrás ni formulario, y hay una prueba que comprueba que `POST` responde `405`.
- **Es la única excepción.** Acudientes, instituciones, catálogo, inventario y ventas siguen en el admin. Cuando alguien proponga la segunda, que traiga su razón: `DT-2` sigue vigente y el motivo por el que existe —no construir a mano lo que el admin ya hace— no ha cambiado.
- El admin, además, se acerca en **composición** y no solo en color: píldoras en la barra lateral, títulos en el tipo de display y tabla con la cabecera tintada. Todo con CSS sobre las clases que Django ya emite.
- **Una plantilla suya sí se sustituye, y es la excepción de la excepción**: `admin/search_form.html`, por una palabra. Django escribe `alt="Search"` sin marcar para traducir, y ese `alt` es el único contenido del `<label>` del buscador — es decir, **el nombre accesible del campo**, en inglés, en un admin en español. No hay ajuste, clase ni CSS que lo alcance. La copia queda anclada a la versión de Django y `cuentas/tests_traducciones.py` falla si la suya cambia; el día que la traduzcan, nuestro fichero se borra.

**Lo que no se copió de la referencia, y por qué.** «Exportar» no existe: no tenemos exportación y un botón que no exporta es peor que no tenerlo. «Reenviar invitaciones» tampoco: `DEC-9` decide que la carga masiva **no** entrega invitaciones porque las direcciones son ficticias, y una pantalla que ofreciera reenviarlas prometería un correo que no sale. Se enseña el recuento, que es el dato real.

**Descartado: rehacer también la edición.** Sería reescribir el formulario del estudiante con sus validaciones, y con él las reglas que `INV-4` obliga a tener en un solo sitio. La lectura no las toca; la escritura sí.

---

#### `[DT-28]` El control parental vive en una app propia, `restricciones`

**Amplía:** `DT-15`, que enumeró siete apps por dominio. Esta añade la octava y dice qué la obliga, para que la lista no crezca por costumbre.

**Razón:** decisión del equipo, tomada el 2026-09-15 al abrir el Sprint 3. La previó `[S3]` del `./sprint-3-backlog.md`, que pidió expresamente **registrarla con un `DT-` propio en el PR que creara la app** y no darla por supuesta.

**El hecho que lo obliga.** El límite diario, el producto bloqueado y el alérgeno bloqueado (`HU-09`, `HU-10`, `HU-11`) **no caben en ninguna de las siete apps declaradas**, y las dos colocaciones plausibles empeoran el diseño en sentidos opuestos:

- **En `personas`** el control parental cuelga del estudiante, que es donde vive — pero `RestriccionProducto` y `RestriccionAlergeno` referencian el catálogo, así que `personas` pasaría a importar de `catalogo`. El padrón de la institución acabaría dependiendo del menú de la cafetería.
- **En `catalogo`** ocurre lo simétrico y es peor: el catálogo es el dominio que **administra la cafetería**, y `INV-4` existe precisamente para que la cafetería no toque las restricciones. Meter las restricciones ahí las pone en la misma app cuyos permisos de escritura `[S11]` sí concede a `USR-4`, y la separación pasaría a depender de acordarse de no conceder, en lugar de la estructura.

**Decidido:**

- Una app `restricciones`, con la forma de `DT-15`: `models.py`, `services.py`, `selectors.py`, `views.py`. Depende de `personas` y de `catalogo`; **ninguna de las dos depende de ella**, así que la dirección del grafo de importaciones no cambia.
- **Ningún modelo suyo se registra en el admin**, y esa ausencia es deliberada. `[S11]` concede escribir restricciones solo a `USR-2`, y el acudiente no entra al admin —`INT-1` es su interfaz (`DT-2`)—. Un registro aquí no serviría a quien sí puede y abriría una puerta a quien no: es la mitad negativa de `INV-4` (`DT-11`).
- Las tres entidades que `[S2]` ya declaraba bajo «Control parental» —`LimiteDiario`, `RestriccionProducto`, `RestriccionAlergeno`— son las de esta app. **No es una entidad nueva ni un modelo nuevo**: es dónde vive el que ya estaba previsto.
- El límite diario es un `OneToOneField` sobre el estudiante y **no haber fila es no tener límite**. Un `monto = 0` diría lo contrario —«no puede comprar nada»—, así que una `CheckConstraint` lo impide y `HU-12` retirará la restricción borrando la fila.

**Lo que no cambia.** `DT-15` sigue vigente entero, incluidas sus tres reglas: los servicios reciben `actor` y no leen `request.user`, las invariantes que la base pueda imponer las impone la base, y las vistas no escriben. Y **`reportes` no se crea aquí**: cada app se crea en el sprint que la necesita, y la suya es el Sprint 5 (`TT-155`).

**Lo que esta decisión no autoriza.** Una app nueva por cada historia que no encaje a la primera. El criterio sigue siendo el de `DT-15` —una app por **dominio**—, y aquí el dominio existe: el control parental es de `USR-2`, tiene sus propias reglas de escritura y su propia invariante. La siguiente que se proponga tendrá que traer un argumento del mismo tipo.

---

#### `[DT-29]` El padrón desactiva; el resto de la escritura sigue en el admin

**Corrige parcialmente:** `DT-27`, que decidió que el padrón **solo lee** y que dar de alta, editar, dar de baja y reasignar la tarjeta seguían siendo del admin. Sigue siendo cierto para todo menos para **una** acción, y esta decisión declara cuál y por qué, para que la excepción no crezca sola.

**Razón:** decisión del equipo, tomada el 2026-09-16 al construir `PR-10`. `TT-119` y `TT-120` sitúan la desactivación «desde el padrón» y «en la ficha del padrón», y eso contradecía la parte de `DT-27` que reservaba la escritura al admin. El conflicto se resolvió antes de escribir código, no después.

**El hecho que lo obliga.** `HU-47` existe por una razón concreta y está en su propio texto: «bloquear su tarjeta **de inmediato** cuando se pierde en mitad de la jornada». La inmediatez no es un adorno de la historia, es su motivo. Y el padrón es la pantalla que secretaría tiene abierta a diario (`DT-27`): llegar desde ahí al admin son tres pantallas —listado, ficha o acción, confirmación— justo en el escenario que la historia describe, con el estudiante esperando en el mostrador.

**Decidido:**

- **Una sola acción escribe desde el padrón: desactivar** (`POST /padron/<id>/desactivar/`). Devuelve el fragmento de la tabla, como `/padron/tabla/`.
- **El alta, la edición, la baja y la reasignación siguen en el admin.** Cada fila sigue enlazando allí, y por lo mismo que decía `DT-27`: duplicar ese formulario sería duplicar las reglas que lo validan.
- **La ruta del padrón en sí no acepta escrituras.** `POST /padron/` sigue respondiendo `405`, y la prueba que lo vigila sigue en pie: lo que escribe es una ruta propia de la pantalla, no la pantalla.
- **La regla no se mueve de sitio.** La vista no escribe: llama a `personas.services.desactivar`, que comprueba el rol (`DT-15`, `DT-11`). Que la acción esté en una pantalla propia no cambia quién puede ejecutarla.
- **Lleva confirmación del navegador** (`hx-confirm`). La reactivación es exclusiva de la institución (`INVD-3`) y su pantalla llega con `HU-49`: hasta entonces un clic por error deja al estudiante sin poder comprar y sin vuelta desde ninguna pantalla.

**Qué haría falta para ampliarla otra vez.** El mismo tipo de argumento: una acción cuya **urgencia** sea parte del criterio de aceptación, no una que simplemente resulte cómoda de tener a mano. La edición no lo es —nadie corrige un apellido con el estudiante esperando— y por eso no entra aquí.

**Descartado: la acción en el admin, con el padrón enlazando.** Es lo que `DT-27` mandaba y no cuesta ninguna decisión nueva; se descartó porque convierte la acción urgente en tres pantallas y porque la ficha del admin no dice lo que secretaría necesita ver al desactivar —quién es el acudiente y si su cuenta está activa—, que es justo lo que el padrón sí enseña.

---

#### `[DT-30]` La reactivación también se hace desde el padrón

**Amplía:** `DT-29`, que abrió el padrón a **una sola** escritura —desactivar— y pidió que la siguiente trajera su razón. Esta es la siguiente, y la trae.

**Razón:** decisión del equipo, tomada el 2026-09-17 al construir `PR-12`. `PR-12` no tiene tarea de pantalla: sus dos tareas son el servicio (`TT-123`) y su caso de prueba (`TT-124`). Pero `PR-10` dejó en la fila del estudiante desactivado un hueco que declaraba «Reactivar: `HU-49`», y cerrar la historia sin llenarlo convertiría ese hueco en una afirmación falsa —anunciaría algo que ya llegó—. O se llena, o hay que quitarlo y dejar la reactivación sin ninguna pantalla.

**El hecho que lo obliga.** `DT-29` pedía «una acción cuya **urgencia** sea parte del criterio de aceptación». La de `HU-49` no es la urgencia sino la **presencia**: «el desbloqueo pasa siempre por una verificación presencial» (`INVD-3`). Y eso apunta al mismo sitio con más fuerza todavía: la familia está en el mostrador, y el padrón es lo que secretaría tiene delante. Mandarla al admin para desbloquear a alguien que está esperando de pie es el mismo error que `DT-29` evitó.

**Decidido:**

- **Dos acciones escriben desde el padrón, y son las dos caras del mismo estado**: desactivar y reactivar (`POST /padron/<id>/desactivar/` y `…/reactivar/`). Las dos devuelven el fragmento de la tabla y las dos pasan por su servicio.
- **La reactivación no existe en `INT-1`.** No hay ruta, ni servicio que el acudiente pueda llamar, ni botón: es `INVD-3`, y el acudiente que desactivó tiene que ir al colegio. Hay una prueba que recorre el mapa de rutas y falla si aparece una segunda ruta con «reactiv» en el nombre.
- **Reactivar no lleva confirmación y desactivar sí.** Una desactivación por error deja al estudiante sin comprar hasta que alguien vaya al colegio; una reactivación por error se deshace con el botón de al lado. Pedir confirmación donde no hace falta enseña a confirmarlo todo sin leer.
- El alta, la edición, la baja y la reasignación **siguen en el admin**, y `POST /padron/` sigue respondiendo `405`.

**Lo que esta decisión no autoriza.** Que el padrón acabe siendo el admin. Las dos acciones que tiene son las dos transiciones del mismo campo, las dos las ejecuta secretaría con alguien delante, y las dos caben en un botón sin formulario. Lo que necesite un formulario sigue al otro lado.

---

#### `[DT-31]` No hay PaaS: el prototipo se ejecuta en local

**Corrige:** `DT-13`, que decidió desplegar en un PaaS con PostgreSQL gestionado.

**Obliga:** `DEC-15` — la asignatura no exige entorno desplegado, y `ENT-01` se recorta para quitarle la condición de estarlo.

**La razón de `DT-13` desapareció, no se debilitó.** Esa decisión se apoyaba en dos hechos: que `ENT-01` exigía un prototipo «desplegado en un entorno de pruebas», y que la Definición de Terminado del Sprint 1 exigía demostrar cada historia allí. `DEC-15` retira el primero y `DoD-4` cambia con él. Sin ninguno de los dos, el PaaS deja de resolver ningún requisito.

**El hecho añadido.** `DT-13` calculaba que un PaaS «lo resuelve en una tarde». Costó bastante más: el plan gratuito del proveedor ni siquiera sostiene el entorno —la base gestionada se duerme y al despertar rechaza conexiones, y desactivarlo está prohibido en ese plan—, y `[S4]` de `./despliegue.md` registra siete trampas que hubo que pagar por el camino. La estimación era optimista y conviene que quede escrito junto a la decisión que la hizo.

**Decidido:**

- **No hay entorno desplegado.** El prototipo se ejecuta en local, con el `docker compose` que `TT-02` dejó reproducible.
- **`railway.json` se retira del repositorio**, junto con el bloque de `config/settings.py` que leía la variable de dominio del proveedor.
- **Lo que no era del proveedor se queda.** Los ajustes de seguridad que se activan con `DEBUG = False` —redirección a HTTPS, cookies seguras, HSTS— valen en cualquier ejecución que no sea de desarrollo y no se tocan. La sonda `/salud/` tampoco: comprueba que la base responde, que es útil con o sin PaaS.
- **El almacenamiento no cambia.** `DT-21` fija un bucket con los prefijos `privado/` y `publico/`; en local eso es MinIO en el mismo `docker compose`, que es lo que el equipo lleva usando desde `TT-02`. Lo que desaparece es la frase de `DT-18` «en producción, el bucket del propio PaaS», porque no hay producción.
- **El disco efímero deja de ser un argumento.** `DT-18` descartó el sistema de archivos porque en un PaaS el disco se pierde en cada despliegue. Ese motivo ya no aplica, **pero la decisión no cambia**: el motivo que la sostiene es la paridad de control de acceso, no la persistencia, y ese sigue intacto.

**Lo que esta decisión no hace.** No prohíbe desplegar más adelante. `[S5]` de `./despliegue.md` conserva los pasos de reconstrucción, y `DT-13` sigue siendo legible para saber por qué el código tiene la forma que tiene.

---

#### `[DT-32]` Una reserva es una `Venta` con otro origen, no otra tabla

**Obliga:** `HU-23` —«se paga en el momento de reservarse»— más las restricciones que ya existían: un movimiento de billetera de tipo `venta` **tiene** que señalar una `Venta` (`TT-78`, `INV-2`). Cobrar al reservar exige, por tanto, crear la venta al reservar.

**Decidido:**

- **La reserva se asienta como una `Venta` normal**, con sus `LineaVenta` y su instantánea de precios (`DT-8`). No hay una segunda tabla que guarde lo que se pidió y lo que costó.
- `Venta` estrena **`origen`**, con dos valores: `punto_de_venta` y `reserva`.
- **`cajero` pasa a ser opcional**, y una `CheckConstraint` le da sentido: origen `punto_de_venta` **exige** cajero; origen `reserva` **exige** que no lo haya, y además exige estudiante.
- `PedidoAnticipado` es una tabla aparte con **una sola cosa que la venta no tiene**: el estado de la entrega. Es `OneToOne` con la venta.

**Por qué el campo `origen` y no solo un cajero nulo.** Sin él, «venta sin cajero» no significaría nada: nada impediría que una venta del mostrador se guardara sin cajero por un error de código, y el cierre de caja de `HU-55` contaría mal sin que nada avisara. Con el origen declarado, la base rechaza las dos combinaciones que no deberían existir.

**Descartado: guardar al acudiente en `cajero`.** No cambia el modelo, y por eso es tentador. Pero el campo mentiría sobre quién cobró, y `HU-55` —cierre de caja por cajero y medio de pago— contaría como caja de alguien lo que nadie cobró en un mostrador.

**Descartado: una tabla de pedidos con sus propias líneas.** Duplicaría `LineaVenta` y su instantánea, y entonces habría dos definiciones de «lo que se pidió y a qué precio». Es lo que `DT-19` evita en el modelo y `DT-4` y `DT-5` en los dos libros.

---

#### `[DT-33]` La reserva cobra al reservarse; el inventario se mueve al entregar

**Obliga:** `HU-23` (segundo criterio) y `HU-25` (segundo criterio), y una decisión del equipo entre dos lecturas posibles del plan del Sprint 4, que se contradecían.

**Decidido:**

- **Al reservar** se descuenta **saldo** y no existencias.
- **Al entregar** (`HU-25`, `TT-149`) se descuentan las **existencias** y no se vuelve a tocar el saldo.
- La reserva valida contra **`existencias_sin_reservar`** —existencias menos lo apartado por pedidos pendientes— y no contra las existencias a secas.

**El hecho que obliga a lo tercero.** Como las unidades reservadas siguen en el libro hasta la entrega, dos reservas del último paquete pasarían las dos: las existencias dicen «queda 1» las dos veces, porque ninguna lo ha descontado. Quien reservó segundo habría pagado por algo que no va a recibir. `existencias_sin_reservar` lo cierra **sin tocar `INV-3`**: no hay columna ni caché, las existencias siguen siendo la suma del historial y esto es otra cifra que se lee al lado.

**Lo que esta decisión deja abierto, y hay que decidir en `HU-25`.** La venta del mostrador sigue mirando las existencias reales, así que **el cajero puede vender unidades apartadas para una reserva ya pagada**. Cuando eso pase, el estudiante llegará a recoger algo que no está. `HU-25` es quien tiene que decidir qué hace la entrega en ese caso, porque es la historia que tiene el problema delante. Está anotado en `[S6]` de `./reglas-de-la-venta.md`.

**La alternativa que se descartó** era descontar existencias al reservar. Cierra ese hueco por construcción —lo apartado sale del libro y la caja no puede venderlo— y hace la entrega trivial. Se descartó porque el inventario físico no se mueve hasta que el producto sale del mostrador, y el equipo prefirió que el libro dijera eso.

**Lo que no cambia:** la reserva pasa por la misma validación que el cobro (`_bloquear_y_validar`), así que hereda las cuatro reglas de rechazo de los Sprints 2 y 3. Eso no es negociable y no depende de esta decisión.

---

#### `[DT-34]` La cola de reservas tiene pantalla propia: segunda excepción a `INT-3`

**Amplía:** `DT-27`, que abrió **una** excepción al admin —el padrón de la institución— y pidió que la siguiente se registrara. Esta es la siguiente, y la trae.

**Obliga:** `HU-24` —«las reservas pendientes son consultables desde la cafetería»— con sus **dos actores**, `USR-3` y `USR-4`, y `FUN-5`, que separa a quien prepara de quien entrega.

**El hecho que lo obliga.** Los dos actores de esta historia **no comparten interfaz**:

| Rol | Dónde trabaja | Qué pasa en la otra |
|---|---|---|
| `USR-3` cajero | `INT-2`, el punto de venta | **No tiene `is_staff`**: el admin lo manda a su pantalla de acceso |
| `USR-4` administración | `INT-3`, el admin | **`403`** en el punto de venta |

Dejar la cola solo en el admin deja fuera al cajero, que es quien la prepara y quien va a entregarla. Dejarla solo en el punto de venta deja fuera a la administración. Y construir las dos es mantener **dos pantallas del mismo dato**, que es como acaban divergiendo.

**Decidido:**

- **Una sola pantalla**, `/reservas/`, sobre el armazón de la aplicación (`base-aplicacion.html`), que es el que los dos roles pueden abrir.
- **La entrada aparece en los dos menús**: en `MENU_POR_ROL` para cajero y administración, y en la columna de iconos del punto de venta, que es lo que el cajero tiene delante mientras cobra.
- **La autorización vive en el selector**, `reservas_pendientes`, no en la vista: es el único camino por el que la cola llega a una pantalla, y así la regla se aplica entre por donde entre (`DT-11`, `DT-15`).
- **`PedidoAnticipado` no se registra en el admin.** Con la pantalla compartida, hacerlo sería la segunda copia que esta decisión evita.

**Por qué no dentro de `INT-2`.** El punto de venta es una pantalla de tres columnas sin scroll, dimensionada para cobrar en 1024 × 600 con una fila delante (`base-punto-de-venta.html`). Una lista que crece con el día no cabe ahí sin quitarle sitio a lo que se pulsa en cada venta. Y no hace falta que esté: la cola se consulta **antes** del descanso; durante, lo que el cajero necesita es el pedido del estudiante que tiene delante, y eso llega al identificar (`HU-25`).

**Lo que esta decisión no amplía.** `INT-3` sigue siendo el admin para todo lo demás de la administración de la cafetería: catálogo, inventario y mermas. Lo que sale del admin es **una consulta**, no una escritura, y sale porque la comparte un rol que no puede entrar allí.

> **Van dos excepciones y conviene contarlas.** `DT-27` el padrón, `DT-34` la cola de reservas. Las dos por la misma razón de fondo: un rol que no vive en el admin necesita ese dato a diario. Una tercera tendría que explicar por qué no es ya un patrón en vez de una excepción.

---

#### `[DT-35]` La entrega de un pedido pagado no se rechaza por falta de existencias

**Cierra:** el hueco que `DT-33` dejó abierto y que `[S7]` de `./reglas-de-la-venta.md` remitió a `HU-25`.

**El hecho que lo obliga.** `DT-33` decidió que la reserva cobra pero no descuenta inventario hasta la entrega. La reserva se protege a sí misma —valida contra `existencias_sin_reservar`—, pero **la caja sigue mirando las existencias reales y puede vender lo apartado**. Cuando pasa, el estudiante llega a recoger algo que ya no está, con el dinero cobrado.

**Decidido:**

- **La entrega se registra siempre.** `entregar` no comprueba existencias: asienta las salidas y cambia el estado.
- **El libro puede quedar en negativo**, y esa cifra se conserva tal cual.
- **La caja no cambia.** No se añade una comprobación que reste lo reservado.

**Por qué del lado del estudiante.** El compromiso ya se adquirió y se cobró. Rechazar la entrega lo deja sin lo suyo **y** con el dinero pagado, y el sistema no sabe devolver dinero (`ALC-OUT-01`): el rechazo no tendría salida. Un descuadre de inventario sí la tiene — se mira, se explica y se corrige con un ingreso o una merma.

**El negativo es información, no un fallo.** Dice que salió mercancía que el libro no tenía registrada, que es exactamente el descuadre que `HU-29` existe para auditar. `INV-3` se sigue cumpliendo —las existencias son la suma del historial— y la pantalla de `TT-141` lo enseña renglón a renglón, con la venta que lo originó. **El sistema no lo esconde: lo deja visible donde alguien lo mira.**

**Descartado: cerrar el hueco en la caja.** Que `registrar_venta` restara lo reservado evitaría el caso. Se descarta por tres cosas:

1. Sería **la séptima comprobación** de la venta, y `[S6]` de `./reglas-de-la-venta.md` existe para que ninguna se añada sin que una historia la pida. Ninguna la pide.
2. En una caja con fila, el cajero leería «no hay existencias» de algo que tiene **delante en la vitrina**, porque está apartado para otro. Ese mensaje no se puede explicar en el mostrador.
3. No elimina el caso, solo lo adelanta: si la mercancía se rompe o se merma después de reservada, la entrega vuelve a encontrarse sin existencias.

**Descartado también: descontar el inventario al reservar.** Es la alternativa que `DT-33` ya había descartado, por decisión del equipo. Cerraría el hueco por construcción, y sigue siendo la salida si algún día se revisa `DT-33`.

**Lo que esta decisión no toca.** Un estudiante desactivado o de baja **tampoco retira** (`INVD-2`, segundo criterio de `HU-50`): eso no es una cuestión de existencias y la entrega lo comprueba por la puerta única de `personas`.

---

## [S2] Modelo de datos núcleo

Dieciocho entidades, todas con **clave primaria UUIDv7** (`DT-17`). Los nombres se ajustarán al implementar; **la forma no**.

### Cuentas e identidad

| Entidad | Campos clave | Sostiene |
|---|---|---|
| `Usuario` | rol, activo, contraseña (no utilizable al crearse) | `DT-10`, `DT-11`, `HU-42` |
| `Institucion` | nombre | `HU-39`, `ALC-OUT-10` (una sola) |
| `Acudiente` | usuario | `HU-03` |
| `Estudiante` | acudiente, **estado** (`activo`/`desactivado`/`baja`), **codigo_tarjeta** (único, **no UUID**), documento, foto_clave | `DT-9`, `DT-12`, `DT-17`, `DT-18`, `HU-04`, `HU-57` |

`Estudiante` **no** tiene usuario: `USR-1` no inicia sesión (`S10.1`).

### Billetera

| Entidad | Campos clave | Sostiene |
|---|---|---|
| `Billetera` | estudiante (uno a uno) | `ALC-IN-06` |
| `MovimientoBilletera` | billetera, tipo (`recarga`/`venta`/`devolucion`), monto **con signo**, venta, creado_en | `DT-4`, `INV-2`, `DT-24` |

**Sin columna `saldo`.** Saldo = suma de movimientos.

### Catálogo

| Entidad | Campos clave | Sostiene |
|---|---|---|
| `Categoria` | nombre | `HU-31` (alertas por categoría) |
| `Alergeno` | nombre | `DT-7` |
| `Producto` | nombre, precio, categoría, campos nutricionales, imagen_clave | `ALC-IN-15`, `HU-59` |
| `ProductoAlergeno` | producto, alérgeno | `DT-7`, `INV-5` |

### Inventario

| Entidad | Campos clave | Sostiene |
|---|---|---|
| `MovimientoInventario` | producto, tipo (`ingreso`/`venta`/`merma`), cantidad **con signo**, **motivo**, venta, creado_en | `DT-5`, `INV-3`, `INV-8`, `DT-24` |

**Sin columna `existencias`.** Existencias = suma de movimientos.

Vive en la app `inventario` y no en `catalogo`, aunque cuelgue de un producto: es un
dominio propio —`DT-15` da una app por dominio— y la venta escribirá en él sin tocar el
catálogo. El motivo es obligatorio en la merma, que es **la disminución manual** de
`INV-8`; la venta no lo exige porque su motivo es la venta misma.

### Control parental

| Entidad | Campos clave | Sostiene |
|---|---|---|
| `RestriccionProducto` | estudiante, producto, **únicos juntos** | `HU-10`, `DT-28` |
| `RestriccionAlergeno` | estudiante, alérgeno, **únicos juntos** · **ningún producto** | `HU-11`, `INV-5`, `DT-28` |
| `LimiteDiario` | estudiante (uno a uno), monto **positivo** | `HU-09`, `DT-28` |
| `AsientoDeRestriccion` | estudiante, **actor**, tipo (`bloqueo`/`retiro`), **sobre** (`producto`/`alergeno`/`limite_diario`), producto **o** alérgeno **o** ninguno, **nombre de entonces**, creado_en | `HU-12`, `HU-61`, `ALC-IN-19`, `DT-8`, `DT-24` |

Las tres son escribibles **solo** por el acudiente (`DT-11`, `INV-4`) y viven en la app `restricciones` (`DT-28`).

`RestriccionProducto` existe desde `TT-97` y es **una lista**: filas de productos señalados uno a uno. `RestriccionAlergeno` existe desde `TT-100` y es **una condición**: dos columnas y ninguna más. Qué productos cubre **no es un dato**, es el resultado de cruzarla con `ProductoAlergeno` en cada consulta (`restricciones.selectors.productos_cubiertos_por_alergeno`), y de ahí sale que un producto añadido después quede cubierto sin que nadie recalcule nada.

Son dos tablas y no una con un campo «tipo» precisamente por eso: unificarlas convierte «resolver el alérgeno como la lista de los productos que hoy lo llevan» en algo que parece una optimización, y eso es exactamente lo que `INV-5` prohíbe. El fallo sería además silencioso — no rompe nada el día que se introduce, rompe semanas después, en la caja.

`AsientoDeRestriccion` es **la entidad dieciocho y la única que no estaba prevista**: la trajo `TT-104` al construir `HU-12`. Es un libro más, con el patrón que `DT-24` fijó para la billetera y el inventario —un único punto de asiento por el que pasan todos los servicios— y con el de `DT-8` para el nombre, que se congela como estaba. No lleva `DT-` propio porque no se desvía de ninguna decisión: la aplica.

Anota el bloqueo además del retiro, aunque `HU-12` solo pedía el segundo. Con solo los retiros no se responde «¿estaba protegido este estudiante el día X?», que es la pregunta por la que la historia existe.

`LimiteDiario` existe desde `TT-94`. **Se puede retirar del todo desde `TT-134`**, y hasta entonces no: `[S11]` ataba «retirar» a la fila de las restricciones alimentarias y la del límite decía únicamente «fijar». `DEC-13` amplió esa fila y `HU-61` lo construyó. Retirar es **borrar la fila**, nunca poner el monto en cero — un cupo de cero significa «no puede gastar nada», que es lo contrario, y la `CheckConstraint` lo impide.

El campo `sobre` del asiento llegó con eso: producto y alérgeno traen su clave ajena, el límite diario no tiene ninguna a la que apuntar, y dejar que «ninguna de las dos puesta» significara «límite» sería adivinar en vez de decir. **No hay fila cuando no hay límite**, y por eso el monto lleva una `CheckConstraint` que exige que sea positivo: un cero significaría «no puede comprar nada», que es lo contrario de «no configuré ninguno».

### Venta

| Entidad | Campos clave | Sostiene |
|---|---|---|
| `Venta` | **cajero (solo si es del mostrador)**, **estudiante (opcional)**, medio_pago (`billetera`/`efectivo`/`transferencia`), **origen** (`punto_de_venta`/`reserva`), creado_en | `DEC-1`, `HU-53`, `HU-54`, `DT-32` |
| `LineaVenta` | venta, producto, cantidad, **precio e información nutricional copiados** | `DT-8`, `HU-22` |
| `PedidoAnticipado` | **venta (uno a uno)**, estado (`pendiente`/`entregado`), entregado_en, entregado_por | `ALC-IN-10`, `HU-23`, `HU-25`, `DT-32` |
| `CierreCaja` | fecha, cajero, base, efectivo_contado, ventas_efectivo, diferencia, motivo | `DEC-6`, `INVD-5`, `HU-55` |

`Venta.estudiante` **opcional** es lo que habilita la venta a cliente genérico de `DEC-1`: una venta sin estudiante es una venta a `USR-6`.

`Venta.origen` y `Venta.cajero` se implican mutuamente y lo impone una `CheckConstraint` (`DT-32`): la del mostrador **tiene** cajero; la reserva **no** —la cobra el acudiente— y exige estudiante, porque no hay reserva de un cliente genérico.

**`PedidoAnticipado` no guarda ni lo que se pidió ni lo que costó**: eso vive en la `Venta` y sus `LineaVenta`, como en cualquier otra venta. Lo único que añade es el estado de la entrega, y por eso es tan corto.

---

## [S3] Cómo se sostiene cada invariante

| Invariante | Decisión que la sostiene | Cómo |
|---|---|---|
| `INV-1` Sin saldo negativo | `DT-1`, `DT-6` | Validación dentro del bloqueo pesimista |
| `INV-2` Saldo reconstruible | `DT-4`, `DT-24` | El saldo **es** la suma del historial, y todo movimiento entra por un único asentador |
| `INV-3` Existencias explicables | `DT-5`, `DT-24` | Las existencias **son** la suma del historial, y todo movimiento entra por un único asentador |
| `INV-4` Restricciones no desactivables | `DT-11`, `DT-28` | Ningún rol tiene permiso de escritura **sobre las restricciones**: la administración escribe su catálogo (`HU-26`) y nada más. Viven en una app propia y **sin admin**, así que no hay dónde concederlo por descuido |
| `INV-5` Bloqueo por condición | `DT-7` | Relación evaluada en la venta, no lista materializada |
| `INV-6` Sin autorregistro | `DT-10` | Las rutas de registro no existen |
| `INV-7` Código aleatorio | `DT-9` | Generador criptográfico con índice único |
| `INV-8` Motivo obligatorio | `DT-5` | Restricción en la base de datos |
| `INV-9` Recomendaciones orientativas | — | Es de interfaz (`HU-34`), no de modelo |
| `INVD-1` Ninguna cuenta por autorregistro | `DT-10` | Mismo mecanismo para los cuatro roles |
| `INVD-2` Desactivado no compra | `DT-12`, `DT-6`, `DT-24` | Estado evaluado en el asentador, por donde pasa **todo** movimiento de billetera |
| `INVD-3` Solo la institución reactiva | `DT-11`, `DT-12` | Transición de estado permitida solo a ese rol |
| `INVD-4` Reasignar invalida el anterior | `DT-9` | El código vigente es un único valor por estudiante |
| `INVD-5` Efectivo explicable | `DT-5` | Cierre calculado desde ventas registradas |
| `INVD-6` Ninguna foto real | `DT-14`, `DT-18` | Avatares generados por el seed |
| — (`DEC-8`, `ALC-OUT-08`) | `DT-20`, `DT-60` | Re-codificación que retira el EXIF y neutraliza formatos políglotos; la lista de formatos limita los decodificadores que leen el fichero |

---

## [S4] Lo que no se construye

| No se construye | Por qué |
|---|---|
| Pasarela de pago, facturación electrónica | `ALC-OUT-01`, `ALC-OUT-02`, `ALC-OUT-03` |
| Aplicación móvil nativa | `ALC-OUT-19` |
| Multi-institución | `ALC-OUT-10` |
| Recetas, insumos, costo de producción | `ALC-OUT-11`, `ALC-OUT-12`, `ALC-OUT-13` |
| Proveedores, compras, predicción de demanda | `ALC-OUT-14`, `ALC-OUT-16` |
| Modelos de aprendizaje automático | `ALC-IN-21` y `OBJ-E3` exigen **reglas determinísticas** |
| Microservicios, GraphQL, autenticación propia | Ningún requisito los justifica; `DT-2` y `DT-3` |
| Hexagonal, repositorios sobre el ORM, interfaces «por si acaso» | `DT-15`; `DT-1` fija PostgreSQL como requisito, no como opción |

### Sobre la ausencia de ciencia de datos

El curso sirve también a **Ingeniería en Ciencia de Datos** (ver `programa` en `corpus:semana-1-introduccion-al-curso-y-esquema-de-evaluacion.md`) y `[S12]` asigna a un integrante el rol de **analista de datos**. Conviene tener preparada la respuesta a por qué el prototipo no incorpora ningún modelo, porque es una pregunta previsible en la sustentación.

**No es una omisión: está excluido tres veces y por motivos distintos.**

| Exclusión | Motivo declarado |
|---|---|
| `OBJ-E3` y `ALC-IN-21` exigen **reglas determinísticas** | Las recomendaciones son informativas, no un modelo probabilístico |
| `ALC-OUT-16` excluye la predicción de demanda | «Requiere series históricas de las que el prototipo no dispondrá» |
| `ALC-OUT-20` excluye la valoración nutricional individualizada | «Constituye un acto profesional del área de la salud» |

El segundo motivo es el técnicamente sólido: un prototipo de diez semanas con datos ficticios (`ALC-OUT-07`) no tiene serie temporal que modelar. Un modelo entrenado sobre ese conjunto aprendería el generador de datos del propio equipo, no el comportamiento de una cafetería.

**El argumento a favor, que es el que conviene sostener:** `ALC-OUT-16` no se limita a excluir —añade que los reportes «entregan, no obstante, la información que la haría posible en una fase posterior»—. Eso es exactamente lo que producen `DT-4`, `DT-5` y `DT-8`: cada venta queda asentada con su producto, su información nutricional congelada, su medio de pago y su marca de tiempo, en libros de movimientos que no se sobrescriben. **La trazabilidad que exigen `INV-2` e `INV-3` es, en la práctica, el conjunto de datos** que una fase posterior necesitaría.

Dicho de otro modo: el proyecto no hace predicción porque no tiene series históricas; **construye el sistema que las genera.**

El trabajo de datos del prototipo es real aunque no lleve modelos: definir los umbrales de las alertas de frecuencia (`HU-31`), localizar y aplicar los valores de referencia de la autoridad sanitaria colombiana (`HU-32`), diseñar los agregados nutricionales y de gasto (`HU-33`) y los reportes de operación (`HU-35` … `HU-37`).

---

## [ANEXO A] Efecto sobre el Sprint Backlog del Sprint 1

`./sprint-1-backlog.md` se escribió con el stack sin decidir y marca con `◆` las tareas dependientes de esa decisión. Hoy son **siete** —`DEC-8` añadió `TT-52` y `TT-54`—. Con `DT-2` fijado:

| Tarea | Efecto |
|---|---|
| `TT-17` Vista de cuentas de personal | Se reduce a declarar el modelo en el admin |
| `TT-20` Desactivar y reactivar cuentas | Acción del admin |
| `TT-34` Listado, búsqueda, alta y edición de estudiantes | Se reduce a declarar el modelo en el admin |
| `TT-42` Dar de baja en la ficha | Acción del admin |
| `TT-45` Gestión del catálogo | Se reduce a declarar el modelo en el admin |
| `TT-52` Carga de la fotografía del estudiante | Campo de imagen del admin |
| `TT-54` Carga de la imagen del producto | Campo de imagen del admin |

Las siete son de Carlos. **Su carga en el Sprint 1 baja de 16 tareas a un equivalente de 10 u 11**, lo que le libera tiempo para el layout adaptable (`TT-05`), la vista imprimible del código de barras (`TT-37`) y el punto de venta, que sí son trabajo de interfaz real.

Además, `TT-06` (envío de correo) y `TT-15` (permisos según `[S11]`) se apoyan en mecanismos que Django ya trae, aunque siguen requiriendo configuración y decisiones.

**Esto no cambia el reparto de historias del sprint**, solo su coste. El riesgo de sobrecarga registrado en el `ANEXO A` de ese documento sigue vigente para Pedro, cuyas 24 tareas no se reducen: el modelo de datos, los servicios transaccionales y el motor de reglas hay que escribirlos igual.

---

## [ANEXO B] Puntos abiertos

- ~~**Presentación del código de barras.**~~ **Resuelto en `DT-22`** (2026-08-31, `PR-17`): Code 128 subconjunto B, generado en el servidor como SVG con medidas en milímetros. Se conserva la línea porque el punto estuvo abierto y la decisión se tomó después, no en la redacción original.
- **Códigos de tarjeta retirados.** `INVD-4` dice que reasignar invalida el anterior «de forma inmediata y definitiva», y lo primero se cumple por construcción: el código deja de existir. Lo segundo tiene un flanco. El generador es aleatorio y **no lleva memoria de lo retirado**, así que podría devolver algún día un código que ya se retiró y asignárselo a otro estudiante; la tarjeta vieja identificaría entonces a otra persona. Es una entre 10^21 por sorteo —sobre diez mil códigos en toda la vida del sistema, del orden de 10^-17— y por eso no se cerró. Cerrarlo cuesta una entidad más, la decimoctava: los códigos retirados con su fecha, y una comprobación adicional en el sorteo. Decía «decidirlo antes del Sprint 2», que es cuando el punto de venta empezó a identificar por código (`HU-15`). **El Sprint 2 pasó sin decidirlo y el punto sigue abierto al entrar en la entrega**, así que ya no es una tarea pendiente de este sprint: es una **limitación conocida** y su sitio es `ENT-06` (`HU-37`, informe final), con la cifra de probabilidad que está arriba.
- **Cálculo del saldo con el historial creciendo.** `DT-4` calcula el saldo por agregación. Para el volumen del prototipo sobra, pero conviene medirlo antes del Avance 2 y dejar registrada la cifra en `ENT-06` como limitación conocida.
- **Estrategia de pruebas automatizadas.** La Definición de Terminado exige un caso de prueba por invariante, pero **no se ha decidido formalmente** si son pruebas automatizadas o guiones manuales. Alejandro es dueño del plan de pruebas (`[S12]`).
  **Resuelto de hecho, no de derecho:** al cerrar el Sprint 1, lo construido lleva **416 pruebas automáticas** con el ejecutor de Django, y `DoD-5` se ha venido cumpliendo con ellas. El punto sigue abierto porque una práctica no es una decisión: falta que el dueño del plan de pruebas la adopte —o la cambie— y quede escrita. Mientras tanto, `DoD-5` dice «caso de prueba» sin adjetivo, a propósito (`[S2]` de `./definicion-de-terminado.md`).
- **Caducidad de las URL firmadas.** `DT-18` fija que la fotografía se sirve firmada, no cuántos minutos dura la firma.
- **PaaS concreto.** `DT-13` fijaba el tipo de despliegue, no el proveedor. **Cerrado por desaparición del asunto:** `DT-31` retira el despliegue, así que no hay proveedor que elegir. El bucket con dos prefijos de `DT-21` sigue vigente, sobre MinIO en local.

---

## [ANEXO C] Nota de procedencia

Decisiones tomadas por el equipo el 2026-08-29, tras revisar qué exigen las invariantes del anteproyecto (`INV-1` … `INV-9`) y las derivadas de las decisiones de alcance (`INVD-1` … `INVD-5`).

#### `[DT-36]` El admin se envuelve, no se reescribe: dos hojas y un solo juego de tokens

**Cierra:** cómo se cumple `DEC-16` —un solo dashboard por rol— sin construir a mano las 89 pantallas que `DT-2` decidió no construir.

**El hecho que lo obliga.** `DEC-16` pide que lo que vive en el admin se alcance desde la misma barra que el resto y se parezca al resto. Hasta ahora eso era imposible por una razón concreta: **el admin no podía cargar la hoja de la aplicación**, porque `@import "tailwindcss"` trae `preflight` —el reset de márgenes, tipos y tablas— y eso desarma los estilos con los que Django pinta sus pantallas. La salida que había era copiar los colores a mano en `admin/base_site.html`, que por eso era el tercer sitio del proyecto con valores literales.

**Decidido:**

- **Hay dos hojas y comparten los tokens.** `estilos/tokens.css` guarda la paleta cruda, los temas y el bloque `@theme`; lo importan `estilos/fuente.css` (la aplicación) y `estilos/admin.css` (el admin). **Un color de la marca está escrito una sola vez en todo el proyecto**, y `admin/base_site.html` deja de tener ninguno.
- **La hoja del admin es Tailwind sin `preflight`**, importando solo `theme` y `utilities`:

  ```css
  @layer theme;
  @import "tailwindcss/theme.css" layer(theme);
  @import "tailwindcss/utilities.css";
  ```

- **Las utilidades van FUERA de capa, y no es un descuido.** El admin trae `.hidden { display: none !important }` sin capa, y una regla sin capa gana a cualquier regla dentro de una **por mucho que venga después**. Con las utilidades en `@layer utilities`, la barra lateral no se pintaba.
- **Se compila con `manage.py estilos_del_admin`**, porque `tailwind build` solo conoce la hoja que declara `TAILWIND_CLI_SRC_CSS`.
- **El cromo del admin toma sus valores de los tokens**: sus variables (`--primary`, `--header-bg`…) se redefinen contra `var(--color-…)`.
- **Crear y editar abren una modal** sobre la pantalla, con el formulario que el admin ya sirve en modo `_popup`. El título de la modal es el `<h1>` del admin, subido desde el contenido: dejarlo dentro pintaba dos encabezados.
- **Lo que Django genera se viste con CSS, no reescribiéndolo.** El listado toma la tabla de `[S2.2]` —cabecera en `primario-suave`, `px-4 py-3`, filas alternas—, el panel lateral la barra de filtros de `[S2.5]`, y «Añadir» deja de ser un sólido: `[S2.1]` dice que en una pantalla cuya pieza principal es la tabla, un botón relleno se lleva la mirada por delante de los datos, y el padrón ya lo resolvía con superficie y borde. Las medidas son las suyas, no unas nuevas.

**Lo que NO se decide aquí.** No se reescribe ninguna pantalla del admin: dentro de la modal el formulario sigue siendo el suyo, con su HTML y sus estilos. `DT-2` sigue entero.

**Tres trampas que costaron una ronda cada una**, y las tres fallan en silencio:

1. **La especificidad del `:not()` es la de su argumento más específico.** El admin subraya enlaces con `a:not([role="button"], #header a, #nav-sidebar a, #content-main.app-list a, .object-tools a)`, que pesa (1,1,2) por ese `#content-main.app-list a`. `.armazon a` y `#container .armazon a` perdían: la regla estaba escrita, compilada y servida, y no hacía nada.
2. **`hidden` de Tailwind choca con el `.hidden` del admin**, que es `!important`. La barra salía con su degradado y su `z-index` correctos y `display: none`. La salida es `max-tablet:hidden`, que esquiva el nombre en vez de pelear.
3. **`formulario.action` no devuelve cadena vacía cuando el atributo falta**: devuelve la URL del documento. Al guardar desde la modal, el POST iba al listado, que responde `200` con la tabla, y la modal se llenaba consigo misma. Se lee el atributo, no la propiedad.

**Consecuencia asumida.** Envolver no es reescribir: el parecido llega hasta donde llega sin tocar las 89 pantallas, y quien mire dentro de un formulario verá el del admin. A cambio, la navegación deja de tener dos mitades y el trabajo cabe en las semanas que quedan.


El documento separa deliberadamente las decisiones **forzadas** de las **de conveniencia**. Once de las catorce son forzadas: no son preferencias del equipo sino la única forma de cumplir un requisito ya acordado. Las tres de conveniencia —framework, arquitectura de interfaz y despliegue— llevan declarada su alternativa descartada y el motivo.

`[S2]` cubre el «modelo de datos» que `ENT-03` exige. Falta el «diagrama de arquitectura» y la reexpresión de la «matriz de roles y permisos», que ya existe en `[S11]` de `./smartfood.md` y no se duplica aquí.

**Ninguna decisión introduce alcance.** No hay entidad en `[S2]` que soporte una funcionalidad que no esté en una historia, y `[S3]` permite comprobar que cada invariante tiene una decisión que la sostiene.

#### `[DT-37]` La aplicación también corre en el `docker compose`: un solo comando levanta el stack

**Corrige:** la premisa de `TT-02`, escrita en la cabecera de `compose.yaml`, de que la aplicación corre en el host con uv y el compose solo levanta la infraestructura.

**Obliga:** que el prototipo se demuestre en local (`DEC-15`, `DT-31`) desde **cualquier** máquina del equipo. Con la aplicación en el host, levantar el proyecto eran siete comandos —copiar el `.env`, levantar la infraestructura, `uv sync`, `migrate`, `sembrar`, `runserver` y `tailwind watch` en otra terminal—, más `estilos_del_admin` y `sincronizar_permisos` según el caso. Cada uno se podía olvidar, y dos de los olvidos fallaban en silencio (`[S1]` de `./trampas-del-stack.md`).

**La razón de `TT-02` era real, y se conserva.** Meter la aplicación en un contenedor añadía una reconstrucción a cada cambio. No la añade si el código **no está en la imagen**: el repositorio va montado encima de `/app`, `runserver` recarga al guardar y la imagen solo aporta lo que el repositorio no tiene —el entorno de Python de `uv.lock` y el binario de Tailwind—.

**Decidido:**

- **`docker compose up` levanta el stack entero** —PostgreSQL, el almacenamiento de objetos con su bucket (`DT-38`), la aplicación y el compilador de estilos— desde un clon limpio, **sin `.env`**: las variables de la aplicación están en `compose.yaml`, con valores ficticios que solo valen contra esos contenedores.
- **El arranque de la aplicación es un script, no una lista de comandos** (`docker/arrancar-aplicacion.sh`): migra, sincroniza la matriz de permisos, siembra —`sembrar` es idempotente (`TT-08`)— y recopila los estáticos antes de servir.
- **Las dos hojas de Tailwind (`DT-36`) tienen su propio servicio**, `estilos`, que las compila y se queda vigilando las plantillas. La aplicación no arranca hasta que las dos existen: sin ellas respondería `200` y saldría sin estilos.
- **La imagen se reconstruye en cada `up`** (`pull_policy: build`). Con la caché de capas son segundos, y es lo que impide levantar una imagen anterior a un `uv.lock` nuevo. Para que eso no recree los contenedores sin motivo, la imagen **no copia el código** y **solo la construye un servicio**: dos servicios con la misma imagen la etiquetaban cada uno con su nombre, y la que ganaba cambiaba de un `up` a otro.
- **Compose 2.20 o posterior.** El fichero no usa nada más nuevo, y la CI lo valida con esa versión además de con la del runner.
- **Las URL firmadas se firman contra la dirección que ve el navegador** (`config/almacenamiento.py`). Dentro del compose, Django alcanza el almacenamiento en `seaweedfs:8333` y el navegador en `localhost:9000`; la firma incluye el host, así que ni sirve la interna ni se puede reescribir después. `custom_domain` de `django-storages` cambiaría el host pero **quita la firma**, y la fotografía de un menor no sale sin ella (`DEC-8`, `DT-18`).
- **Los contenedores escriben con el usuario del host**, no como root: las hojas compiladas y los estáticos quedan en el repositorio y tienen que poder sobrescribirse después desde `uv run`.
- **El compose no se queda atrás.** `config/tests_contenedor.py` vigila con la suite lo que se ve sin Docker —una variable obligatoria nueva en los ajustes que el compose no da, la versión de Python, un comando renombrado que el arranque llama—, y el flujo `integracion-continua` de la CI levanta el stack desde cero en cada PR y comprueba que sirve.

**Lo que esta decisión no hace.** No despliega nada: la imagen es de desarrollo —`runserver`, `DEBUG`— y no funciona sin el repositorio montado. `DT-31` sigue entero. Tampoco prohíbe el camino anterior: con la infraestructura del compose levantada, `uv run` en el host funciona igual que antes contra los puertos publicados.

**Consecuencia asumida.** Hay un servicio más que mantener, y la regla de que lo mantenga quien cambie la infraestructura está escrita en `CLAUDE.md`. Lo que la sostiene de verdad no es la regla sino las dos comprobaciones: una regla se olvida en el siguiente PR; una prueba que falla, no.

#### `[DT-38]` SeaweedFS sustituye a MinIO como almacenamiento local

**Corrige:** `DT-18` en su elección de MinIO para el entorno local —«En local, MinIO en el mismo `docker compose` que PostgreSQL»—, y la inicialización del bucket con `mc` que describe `DT-21`.

**Obliga:** que el stack se levante desde cualquier máquina (`DT-37`, `DEC-15`). **Las imágenes oficiales de MinIO dejaron de poder descargarse**: `minio/minio` y `minio/mc` responden «pull access denied» en Docker Hub —también la etiqueta `latest`— y en quay.io las etiquetas fijadas no existen y el registro pide autenticación. Ningún clon nuevo podía levantar ni siquiera la infraestructura que `TT-02` dejó reproducible; las máquinas del equipo funcionaban porque las tenían en caché. Lo destapó la primera ejecución del trabajo `pruebas` de la CI, en un runner sin caché. La única imagen que seguía publicada era `bitnamilegacy/minio`, un archivo congelado y sin mantenimiento.

**Lo que `DT-18` decidió de verdad no cambia.** Su argumento era la **paridad de control de acceso**, no MinIO: que en local la fotografía de un menor también exija URL firmada y caduque. Eso lo da cualquier servidor S3 con firma SigV4 y sin acceso anónimo, y se comprobó con SeaweedFS antes de cambiar nada: con la clase de almacenamiento del proyecto, la URL firmada abre aunque se firme contra otro host (`DT-37`), y sin firma, con credenciales ajenas, caducada, o al listar el bucket, la respuesta es `403`.

**Decidido:**

- **SeaweedFS 4.48** (`chrislusf/seaweedfs`, Apache 2.0, publicado para amd64 y arm64), en un solo proceso que hace de maestro, volumen, filer y API S3.
- **La identidad se escribe al arrancar** a partir de `S3_ACCESS_KEY_ID` y `S3_SECRET_ACCESS_KEY`, las mismas variables que lee Django. **No hay identidad anónima**, así que el bucket es privado sin una política aparte: lo que antes hacía `mc anonymous set none`.
- **El bucket lo crea `weed shell`** desde la propia imagen, de forma idempotente, y no un cliente aparte: el compose deja de depender de dos imágenes para el almacenamiento.
- **El API S3 se publica en el host en el puerto 9000**, el de antes, así que `S3_ENDPOINT_URL` en el `.env` del modo sin contenedor no cambia. **No hay consola web**: la interfaz del filer de SeaweedFS no pide credenciales, y publicarla dejaría las fotografías al alcance de cualquiera con el puerto.
- **El código no cambia.** `django-storages` habla S3 y no sabe con qué servidor; los ajustes `STORAGES`, los prefijos `privado/` y `publico/` de `DT-21` y la firma de `DT-37` son los mismos.

**Consecuencia asumida.** Una base que ya tenía fotografías en el volumen de MinIO queda con claves que apuntan a objetos que SeaweedFS no tiene: hay que empezar de cero (`docker compose down -v`) para que `sembrar` vuelva a generarlas. Los datos son ficticios (`ALC-OUT-07`) y se resiembran solos al levantar.

#### `[DT-39]` La CI ya no corre pruebas: solo publica la versión

**Corrige:** `DT-37` en «el flujo `integracion-continua` de la CI levanta el stack desde cero en cada PR y comprueba que sirve», y la regla de `[S3.0]` de `./convenciones-de-git.md`, «sin pruebas en verde no hay versión».

**Razón:** decisión del equipo, tomada el 2026-10-02. El trabajo `pruebas` tardaba unos veinte minutos por integración —levantar el stack desde cero y pasar la suite completa—, y con dos personas desarrollando en el último sprint esa espera se volvió el cuello de botella. El equipo prefiere ese tiempo a la red de seguridad.

**Decidido:**

- **Se retira el trabajo `pruebas`.** El workflow pasa a llamarse `publicar-version.yml` y solo tiene el trabajo `release`: `semantic-release` en cada push a `main`, sin depender de nada.
- **Se conserva `convencion-de-commits.yml`**, que valida el título del PR en unos segundos: el release calcula la versión a partir de ese título (`[S2.5]` de `./convenciones-de-git.md`), y un título mal escrito no publica la versión que toca.
- **Las comprobaciones pasan a local, y no desaparecen.** Los tres comandos de antes de cada PR —`check`, `makemigrations --check` y la suite— siguen siendo obligatorios. **Y cuando el cambio toca la infraestructura**, `docker/comprobar-desde-cero.sh` hace lo que hacía el trabajo retirado, con los mismos pasos: validar el compose con el mínimo, levantar desde cero, comprobar páginas, hojas, fotografías firmadas y correo, y correr los tres comandos dentro (`[S5.3]` de `./desarrollo.md`). Además pregunta al registro por cada imagen, que es lo que el runner de GitHub hacía sin querer al empezar sin caché.

**Consecuencia asumida.** **Que una versión se publique ya no dice que la suite pase**: lo dice quien la corrió antes de integrar. Y nada externo detecta que el stack deja de levantar en una máquina limpia: lo vigilan `config/tests_contenedor.py`, en la suite, y el script, si alguien lo corre. Es la condición de que el prototipo se pueda demostrar (`DEC-15`), así que conviene correr el script antes de cada entrega aunque no se haya tocado la infraestructura.

**Lo que no lo obligaba.** Las reglas de GitHub sobre `main` —`main` y `main-protected`— están desactivadas a fecha de esta decisión, así que el trabajo `pruebas` nunca bloqueó una integración: la espera la imponía el propio equipo. Retirarlo no cambia qué se puede integrar, sino qué se comprueba antes.

#### `[DT-40]` La ficha del estudiante se edita en una modal del padrón

**Corrige:** `DT-27`, `DT-29` y `DT-30` en lo que dejaban en el admin —«la edición, la baja y la reasignación siguen en el admin»—. **Aplica** `DEC-16`, que decidió que editar abre una modal sobre la pantalla en la que se está, y `DEC-17`, que puso la ficha del estudiante entre las pantallas de la institución que se construyen.

**Razón:** decisión del equipo, tomada el 2026-10-01. El admin de estudiantes (`/admin/personas/estudiante/`) se retiró, y lo que hacía vuelve donde secretaría lo busca: en la fila del padrón.

**Decidido:**

- **«Editar», en cada fila, abre la ficha en un `<dialog>`**: fotografía, nombre, documento, código vigente, matrícula y la cuenta del acudiente. `GET /padron/<id>/ficha/` la devuelve y `POST` a la misma ruta guarda. Las dos responden **el fragmento de la ficha y nada más** (`DT-16`), con los errores o con el resultado dentro.
- **Un solo «Guardar» es una sola transacción** (`personas.services.guardar_ficha`). Si el documento ya es de otro o la fotografía no se puede procesar, no se guarda nada y la ficha vuelve con lo escrito y el motivo. El admin hacía lo contrario —un fallo de la fotografía no deshacía la edición—, y con varios cambios en un solo envío eso dejaría la mitad aplicada sin que quien guardó supiera cuál.
- **La tabla se entera por un evento, no por la respuesta.** Cuando algo cambió, la respuesta lleva `HX-Trigger: padron-cambiado`, y el formulario del buscador vuelve a pedir `/padron/tabla/` **con los filtros que tenía**. Así la ficha no devuelve dos cosas a la vez.
- **El código de tarjeta no es un campo**: se enseña y se reasigna con su propia acción, `POST /padron/<id>/reasignar/`, con confirmación del navegador (`HU-46`, `INVD-4`, `INV-7`). Al lado va el enlace a la tarjeta imprimible (`HU-45`), que con el admin se había quedado sin ningún enlace.
- **La matrícula es un interruptor que solo se apaga.** Apagarlo es la baja (`HU-51`), que no tiene vuelta (`DEC-7`), y por eso pide confirmación al guardar. A un retirado no se le dibuja el interruptor sino desde cuándo lo está: un control que la base va a rechazar no se pinta (`[S4]` de `./sistema-visual.md`).
- **Desactivar y reactivar siguen en la fila**, fuera de la modal (`DT-29`, `DT-30`): su razón de ser es que estén a un clic.
- **Del acudiente solo es editable el acceso** (`DEC-20`, `HU-63`). Nombre y correo se enseñan; editarlos sigue fuera de `[S11]`.
- **`POST /padron/` sigue respondiendo `405`**: lo que escribe son rutas propias de la pantalla, no la pantalla.
- **El alta individual va en la misma modal** (primer criterio de `HU-44`): «Cargar un solo estudiante», arriba del padrón, abre la ficha **vacía** (`GET`/`POST /padron/matricular/`). Pide fotografía —opcional—, nombre, documento y acudiente; el código lo genera el sistema al guardar (`HU-43`, `INV-7`) y se nace matriculado. Es una sola transacción (`personas.services.matricular_estudiante`): si la imagen no vale, no queda nadie matriculado a medias. Al matricular, la ficha vuelve vacía con el código generado y el enlace para imprimirlo, y la tabla se entera por el mismo `HX-Trigger`.
- **El acudiente se elige, no se crea.** Se busca por nombre, documento o correo (`/padron/matricular/acudientes/`, que sin búsqueda no devuelve a nadie y con ella, ocho como mucho). Crear uno sería dar de alta una cuenta, y eso solo lo hace la carga masiva (`HU-01`): la institución, sobre el acudiente, solo consulta (`[S11]`). **Una familia nueva entra por la carga.**
- **Las dos fichas avisan antes de enviar.** Mientras un campo obligatorio esté vacío o no cumpla su longitud, dice en rojo qué le falta y el botón de guardar está deshabilitado; el de matricular **nace** deshabilitado. Es una comodidad, no la regla (`DT-15`): las longitudes llegan al navegador desde el propio campo del formulario, y este las toma de `personas.validacion` —las mismas de la carga masiva—, así que el aviso y el rechazo del servidor no pueden pedir cosas distintas. La ficha de edición pasa con ello a exigir lo mismo que la carga: un documento de entre 5 y 20 caracteres.
- **La carga masiva no desaparece**: su botón deja el padrón, pero sigue en la barra lateral.

#### `[DT-41]` Se integra empujando directo a `main`, sin ramas ni Pull Requests

**Corrige:** `[S1]` de `./convenciones-de-git.md` (`TT-01`), que pedía ramas cortas, Pull Request con revisión del otro desarrollador y squash merge para todo lo que entrara en `main`; y `DT-39` en que la validación del título del PR siga cubriendo el mensaje que decide la versión.

**Razón:** decisión del equipo, tomada el 2026-10-03, por tiempo. Abrir rama, abrir PR, esperar y integrar cada cambio se volvió inmanejable para dos personas desarrollando en el último sprint. **El equipo la toma sabiendo lo que pierde y asume las consecuencias.**

**Decidido:**

- **Se commitea y se empuja directo a `main`**: `git pull --rebase` antes de cada `push`, y **nunca `push --force`** sobre `main`, que borraría lo que el otro ya empujó.
- **Antes de empujar, los tres comandos en verde** (`[S5]` de `./desarrollo.md`), y el script de `[S5.3]` si el cambio toca la infraestructura. Si el `pull --rebase` trae commits del otro, se vuelven a correr.
- **Cada commit cumple la convención** (`[S2]` de `./convenciones-de-git.md`): sin squash, `semantic-release` analiza cada uno tal cual.
- **La Definición de Terminado sigue entera**, aplicada a lo que se empuja junto en lugar de a un PR (`[S5]` de `./definicion-de-terminado.md`).
- **Los `PR-nn` de los planes de sprint siguen siendo la unidad de entrega**, ahora como un conjunto de commits.
- **Abrir un Pull Request sigue siendo posible** cuando convenga, con el flujo de siempre: squash, título validado y plantilla.

**Consecuencia asumida.** **Nadie revisa un cambio antes de que llegue a `main`**: ni el otro desarrollador, ni la CI (`DT-39`), ni GitHub, porque `main` no tiene protección activa. **El mensaje de cada commit tampoco se valida**: `convencion-de-commits.yml` solo corre en Pull Requests, y un tipo mal escrito no da error, simplemente no cuenta para la versión o cuenta como otra cosa. **Y una nota `BREAKING CHANGE:`, `BREAKING-CHANGE:` o `CAMBIO INCOMPATIBLE:` en el cuerpo de un commit ahora sí publica una versión mayor**, porque el cuerpo llega a `main` (`noteKeywords` de `.releaserc.json`). A cambio, el cuerpo de cada commit —con sus `Refs:` y la evidencia de `DoD-4`— queda en el historial, cosa que el squash descartaba.

#### `[DT-42]` Los buscadores de los listados del admin buscan mientras se escribe

**Extiende** `[S2.5]` de `./sistema-visual.md` —«el buscador pide a cada tecla, con 400 ms de espera»— a los listados del admin, que eran los únicos buscadores que esperaban Enter. **No amplía el alcance**: los listados, sus campos de búsqueda y lo que encuentran son los mismos; cambia cuándo se pide.

**Razón:** decisión del equipo, tomada el 2026-10-03. Con dos comportamientos, quien pasa del padrón a los productos escribe, espera y no ve nada.

**Decidido:**

- **Los once listados con `search_fields` —diez de los dominios y los grupos de `auth`— piden con 400 ms de espera tras la última tecla**, y Enter pide en el acto. Es la espera de las pantallas propias; pedir de verdad con cada tecla lanzaría una consulta por letra, y una respuesta lenta podría pintar la búsqueda de hace dos letras. Por eso, además, solo cuenta la última petición: la anterior se aborta.
- **Se pide la página entera y se trasplanta `#changelist`**, con `fetch` desde `assets/js/interfaz.js`, como ya hace la modal del admin con el formulario (`DEC-16`). No es una excepción a `DT-16`: no hay ninguna vista HTMX nueva; el admin sigue sirviendo su página, y lo que cambia es que el navegador no la recarga. Entra con el listado todo lo que vive dentro de él: los filtros, el recuento y los consolidados de `TT-168`, `TT-170` y `TT-176`, que se calculan sobre el mismo `QuerySet`.
- **El campo no se reemplaza: se muda** al listado nuevo, con su foco y su cursor. Reemplazarlo perdería lo tecleado mientras viajaba la petición.
- **Lo que el admin enlaza al cargar se vuelve a enlazar**: las casillas de las acciones masivas (`admin/js/actions.js`) y el plegado de los filtros (`admin/js/filters.js`), que además se conserva.
- **La URL cambia con `replaceState`**, así que recargar o compartir conserva la búsqueda, y el botón de volver no acumula una entrada por pausa.
- **`templates/admin/search_form.html` no se toca**: es una copia anclada a Django que `cuentas/tests_traducciones.py` compara con el original. Sin JavaScript, o si la petición falla, buscar es lo de siempre: el formulario se envía y el admin responde.
- **El punto de venta queda fuera**, a propósito. Sus dos campos —código de tarjeta y documento— no filtran una lista: identifican a **un** estudiante, se vacían tras cada búsqueda (`TT-71`) y el lector termina cada código con Enter. Buscar con un documento a medio escribir podría poner delante del cajero a otro estudiante, al que se le cobraría.
- **Los campos numéricos tampoco son filtros**: el monto de la recarga y del límite, las cantidades de la reserva y el efectivo del cierre son datos de un formulario que se envía.

**Consecuencia asumida.** **Cada pausa al teclear es una página completa del admin**, con su consulta del listado, sus filtros y su consolidado: más trabajo para el servidor que el fragmento de las pantallas propias. Con los volúmenes del prototipo no se nota. **Y la conducta no la vigila la suite**: es JavaScript, que las pruebas de Django no ejecutan; se comprobó con Playwright contra el stack (`[S3.1]` de `./desarrollo.md`).

#### `[DT-43]` La fila del padrón abre la ficha del estudiante en solo lectura

**Extiende** `DT-40`: la modal del padrón, que solo se abría para editar o matricular, también enseña al estudiante sin campos. **No amplía el alcance ni toca `[S11]`**: reúne lo que la institución ya veía repartido entre la fila, la ficha de edición y la consulta de restricciones (`HU-38`, `DEC-17`). Por eso no lleva historia ni `DEC`.

**Razón:** decisión del equipo, tomada el 2026-10-12. Para mirar a un estudiante, secretaría tenía que abrir la ficha de edición —con sus interruptores de baja y de acceso a mano— o ir a otra pantalla a ver sus restricciones.

**Decidido:**

- **`GET /padron/<id>/` devuelve la ficha en solo lectura**, y solo `GET`: `POST` responde `405`. Es un fragmento (`DT-16`) que cae en el mismo `<dialog>` que la de edición. Quién pasa lo decide el mismo selector, `estudiante_para_la_institucion` (`DT-15`).
- **Enseña**: la foto en grande —o la inicial—, nombre, documento, estado dicho entero (activo, desactivado, retirado desde cuándo), código de tarjeta con su enlace para imprimirla (`HU-45`), desde cuándo está en el padrón, el acudiente con el estado de su cuenta —activa, sin activar o con el acceso cortado (`DEC-20`)— y los demás estudiantes a su cargo, y las tres restricciones juntas (`RestriccionesVigentes`, `HU-38`).
- **No enseña el saldo, los consumos ni las recargas.** En `[S11]`, «Consultar saldo de un estudiante» es `–` para la institución. La vista no llama a `billetera` ni a `reportes`, y `personas/tests_consulta.py` lo vigila sobre el bytecode y sobre lo pintado.
- **Ni un solo campo**, ni siquiera deshabilitado: un control con borde se lee como editable. **Editar**, en el pie, pide la ficha de edición al mismo cuerpo de la modal.
- **El nombre de cada fila es un botón y la fila, un atajo.** Pulsar en cualquier parte de la fila pulsa ese botón (`assets/js/interfaz.js`): un `<tr>` no se enfoca con teclado ni lo anuncia un lector de pantalla. Lo que ya es un control —«Editar», «Desactivar», «Reactivar»— hace lo suyo y no abre la consulta, y arrastrar para seleccionar un documento tampoco.

**Consecuencia asumida.** **El clic en la fila no lo vigila la suite**: es JavaScript; se comprobó con Playwright contra el stack, en claro, oscuro y a 390 px. Lo que sí vigila es que cada fila lleve el botón con su ruta.

#### `[DT-44]` La fila de un acudiente abre su ficha en solo lectura, y las familias que se fueron no salen por defecto

**Extiende** `DT-43` a la pantalla de acudientes (`DEC-17`), con la misma modal y el mismo código, y le da el interruptor **Ver retirados** del padrón (`DT-27`). **No amplía el alcance ni toca `[S11]`**: sobre el acudiente la institución consulta, y esto es consulta.

**Razón:** decisión del equipo, tomada el 2026-10-12. Para saber de qué estudiantes responde un acudiente había que buscarlo en el padrón por su nombre; y la lista mezclaba con las familias de hoy a las que ya no tienen a nadie en el colegio.

**Decidido:**

- **`GET /acudientes/<id>/` devuelve la ficha en solo lectura**, y solo `GET`. Fragmento (`DT-16`); quién pasa lo decide `acudiente_para_la_institucion`, con la misma regla que la lista (`DT-15`). Enseña nombre, documento, correo, el estado de su cuenta, cuándo se creó y **sus estudiantes, retirados incluidos**, cada uno con foto, documento, código y estado. **Sin saldo ni consumos de ninguno** (`[S11]`) y **sin acciones**: el acceso se corta desde la ficha de edición del estudiante (`DEC-20`), y la ficha lo dice.
- **La fila pulsa el botón del nombre**, como en el padrón: el atajo de `assets/js/interfaz.js` es ya el mismo para las dos pantallas, que marcan la fila con `data-fila-consultable` y el botón con `data-consultar`.
- **Un acudiente no se retira: se retiran sus estudiantes** (`HU-51`), y su cuenta sigue viva para el historial y el saldo congelado (`HU-52`). En esta lista, **retirado es la familia que tiene estudiantes y ninguno matriculado**. No sale por defecto; **Ver retirados** la trae, con la marca «Retirado». **No son retirados**, y salen siempre: el **acceso cortado** (`DEC-20`), porque esa familia sigue en el colegio, y el **acudiente sin ningún estudiante**, que no se fue de ninguna parte y es justo lo que conviene ver.
- **El buscador del alta individual sí encuentra a las familias que se fueron** (`DT-40`): un hermano menor que entra al colegio se matricula con el acudiente que ya existe.
- **El «de N» del recuento es el total sin la búsqueda**, con el mismo filtro de retirados. Se contaba sobre lo encontrado, y decía siempre lo mismo que el número de al lado.
- **«Acceso cortado» es un estado de la cuenta**, en rojo, en esta lista, en el padrón y en las dos fichas. Cortar el acceso no borra la contraseña, y el estado solo preguntaba por ella: desde `DEC-20`, una cuenta cortada se pintaba **«Activa»** en las dos tablas.

**Consecuencia asumida.** **La marca «Retirado» no se vio sobre la base de trabajo**: haría falta una baja, que no tiene vuelta. Se miró con Playwright sirviendo al navegador los fragmentos que Django pintó dentro de una transacción deshecha; el resto, contra el stack. Las pruebas son `personas/tests_acudiente_consulta.py`.

#### `[DT-45]` `/usuarios/`: el personal de la cafetería, con la composición del padrón

**Aplica** `DEC-17`, que puso «usuarios» entre las pantallas propias de la institución. **Sustituye**, en su menú, al listado `cuentas.usuario` del admin. **No amplía el alcance ni toca `[S11]`**: alta (`HU-40`), invitación (`HU-41`) y acceso (`HU-42`) siguen siendo los mismos y los mismos servicios.

**Razón:** decisión del equipo, tomada el 2026-10-12. El listado del admin mezclaba al personal con **todos los acudientes y con la propia cuenta de la institución**: para encontrar a los dos o tres cajeros había que filtrar entre cientos de familias, y se le ofrecían acciones sobre cuentas que no son de personal y que los servicios rechazan.

**Decidido:**

- **`/usuarios/` lista solo `ROLES_DE_PERSONAL`** —cajero y administración—, los mismos que aceptan los servicios de alta y acceso. Lo decide `cuentas.selectors.personal_de_la_cafeteria`, que exige la institución (`DT-11`). Las cuentas desactivadas salen siempre, con su estado.
- **La composición es la del padrón y los acudientes** (`DT-25`, `DT-27`): buscador en vivo por nombre y correo, recuento «N de M», tabla con rol, último acceso y estado de la cuenta, y fichas por debajo de `tablet`.
- **«Crear usuario» abre la modal de alta**, la misma `<dialog>` y el mismo código que el alta del padrón (`DT-40`): nombre, correo y rol en dos tarjetas, validados en vivo, y **ningún campo de contraseña** (`HU-41`, `DEC-3`). Un correo repetido, sin distinguir mayúsculas, se rechaza. Al crear, la modal vuelve vacía con el resultado y la tabla se entera por `HX-Trigger: personal-cambiado`.
- **Las tres acciones del admin pasan a la fila**: desactivar —con confirmación—, reactivar y reenviar la invitación, esta solo a quien no la ha usado. Devuelven la tabla con la búsqueda que había, como el padrón (`DT-29`). Se lee la lista antes de escribir, así que una cuenta que no es de personal da `404`.
- **`reenviar_invitacion` no recibía `actor`**: su único camino era el admin, que la protegía con su permiso. `reenviar_invitacion_de_personal` le pone la puerta —la institución, sobre personal— y es la que llama la pantalla (`DT-15`).
- **El admin de usuarios no se retira**: sale del menú y sigue respondiendo por su URL, como el de acudientes tras `DEC-17`.

**Consecuencia asumida.** **Es una excepción a la raya de `DEC-17`**, que solo sustituye una pantalla del admin cuando alguien la usa a diario, y el alta de personal no es diaria: se acepta porque la del admin no servía para lo que se usa, no por la frecuencia. Editar el nombre y el correo llega con `DT-46`. Y **el alta con éxito no se probó en el navegador sobre la base de trabajo**, porque una cuenta creada no se borra desde la aplicación: se sirvió al navegador la respuesta que Django dio dentro de una transacción deshecha; el resto, contra el stack. Las pruebas son `cuentas/tests_usuarios.py`.

#### `[DT-46]` El nombre y el correo del personal se editan en `/usuarios/`, por un servicio

**Completa** `DT-45`: lo único que el admin de usuarios hacía y la pantalla nueva no. **No amplía el alcance**: la institución ya podía editar esas cuentas (`cuentas.usuario`, `change`).

**Razón:** decisión del equipo, tomada el 2026-10-12. Sin esto, corregir una errata en el nombre de un cajero obligaba a volver al admin por una URL que ya no está en el menú.

**Decidido:**

- **«Editar», en cada fila, abre la modal** con nombre y correo —los mismos campos que el alta, en un parcial compartido— y el rol y el estado de solo lectura. `GET` y `POST` de `/usuarios/<id>/editar/` devuelven la modal (`DT-16`); al guardar, la tabla se entera por `HX-Trigger: personal-cambiado`.
- **Pasa por `editar_cuenta_de_personal`**, con la puerta del resto del personal (`DT-15`). El admin escribía estos cambios directamente, sin servicio.
- **El rol no se edita.** Arrastra el grupo de permisos y el acceso al admin, que se deciden al dar de alta; un `rol` enviado a mano se ignora.
- **Un correo de otra cuenta se rechaza**, sin distinguir mayúsculas, en el formulario y otra vez en el servicio.
- **Cambiar el correo de quien no ha definido su contraseña lo vuelve a invitar.** El token de Django incluye el correo **exacto**, así que la invitación ya enviada deja de valer —también si solo cambia una mayúscula—, y sin otra la cuenta no la podría activar nadie. A quien ya tiene contraseña no se le escribe: el correo nuevo es, desde ese momento, con lo que inicia sesión.

**Consecuencia asumida.** **A quien ya entra no se le avisa** de que su usuario cambió: lo sabrá quien lo cambió, que es quien se lo tiene que decir. Es el mismo punto abierto que los demás avisos (`ANEXO B` de `./decisiones-de-alcance.md`).

#### `[DT-47]` La reserva no comprueba existencias: es un encargo

**Corrige:** `DT-33` en su tercer punto —«la reserva valida contra `existencias_sin_reservar`»—. Los dos primeros siguen en pie: se cobra al reservar y el inventario se mueve al entregar.

**Obliga:** `DEC-24`.

**Decidido:**

- **`_bloquear_y_validar` sigue siendo una sola para la caja y la reserva**, y lo que cambia es su argumento: `existencias_de_los=None` significa que **no se comprueban**. La venta del mostrador pasa `existencias_por_producto` de forma explícita; la reserva no pasa nada. Las otras cinco comprobaciones no dependen del argumento y se aplican igual a las dos.
- **`existencias_sin_reservar` y `unidades_reservadas_pendientes` se retiran.** Su único lector era la reserva, y una cifra de «lo apartado» que nadie consulta es un número que alguien acabará enseñando como si significara algo.
- **La pantalla de reserva no enseña existencias** ni limita el campo: ni «quedan», ni «sin existencias», ni `max`.

**Lo que no cambia.** La caja mira las existencias reales y la entrega no se rechaza por falta de ellas (`DT-35`). Lo que `DT-35` llamaba «vender lo apartado» deja de existir como caso, porque nada se aparta: lo reservado se prepara, y si no se puede preparar, se cancela (`DT-48`).

#### `[DT-48]` Cancelar un pedido es un tercer estado y una devolución en el libro

**Obliga:** `DEC-24`, `HU-65`, `HU-66` y `HU-67`.

**Decidido:**

- **`EstadoDelPedido` gana `cancelado`**, y el pedido gana quién, cuándo y el motivo. **Una sola `CheckConstraint` sustituye a `pedido_entrega_completa_o_ninguna`** y dice qué combinación vale en cada estado: pendiente sin entrega ni cancelación, entregado con su entrega y sin cancelación, cancelado con su cancelación y sin entrega. **El motivo tiene que tener algo que no sea espacio** (`\S`), como la merma (`INV-8`, `TT-140`).
- **La devolución es un `MovimientoBilletera` de tipo `devolucion`** por el importe íntegro de la venta, que apunta a ella. El tipo existía desde `TT-59` sin que nada lo asentara. **Una `UniqueConstraint` parcial impide dos devoluciones de la misma venta**: devolver dos veces es el gemelo de cobrar dos veces, y tampoco lo detecta ninguna invariante — el libro cuadraría con el doble.
- **Pasa por `billetera.services.asentar`, que no llama a la puerta de `INVD-2` e `INVD-7` para las devoluciones**: ya era así, porque esa puerta solo cubre la recarga y la venta. Es lo que hace cierto que un pedido de un estudiante que no opera se pueda cancelar.
- **Un solo servicio, `cancelar_pedido(actor, pedido, motivo)`, para los tres roles**: el acudiente sobre sus estudiantes, el cajero y la administración sobre cualquiera. Bloquea el pedido con `select_for_update(of=("self",))`, como `entregar`, así que una cancelación y una entrega simultáneas no pueden pasar las dos: la segunda lee el estado nuevo y se rechaza.
- **Un pedido cancelado deja de contar como venta y como consumo**, y la regla vive en `ventas.selectors`, una vez: el cupo del día (`consumo_del_dia`), el reporte de ventas del admin, los más vendidos y las últimas ventas del panel, la frecuencia y los agregados. **La auditoría sí lo enseña**, con la venta y con la cancelación, porque las dos ocurrieron.
- **El acudiente lo tiene todo en la pantalla de reserva**: los pedidos van debajo del catálogo, cada fila abre su detalle en la modal de ficha (`[S2.10]` de `./sistema-visual.md`) y la cancelación se hace dentro de ella. `GET` y `POST` devuelven la misma modal, y al cancelar la respuesta lleva `HX-Trigger: pedidos-cambiado`, que repinta la lista y el ticket —el saldo cambió— (`DT-16`, `DT-40`). **La cafetería**, en cambio, cancela desde la cola con una página de confirmación, `/reservas/<pedido>/cancelar/`: un `GET` enseña y un `POST` cancela y redirige.
- **`PedidoAnticipado` sigue fuera del admin** (`DT-34`): la cola es la pantalla compartida, y cancelar desde ella es la escritura que esa pantalla gana.

**Por qué el pedido y la venta no se borran.** La venta se cobró y la devolución se asentó: los dos movimientos tienen que poder explicarse (`INV-2`), y los dos apuntan a la venta con `PROTECT`.

#### `[DT-49]` La cafetería consulta los pedidos en un tablero y cancela desde la modal

**Obliga:** `HU-68`. **Corrige** a `DT-48` en un punto —la cafetería cancelaba desde una página de confirmación— y **amplía** `DT-34`, cuya pantalla compartida deja de ser solo la cola.

**El hecho que lo obliga.** La administración necesita ver también lo entregado y lo cancelado, con quién canceló y por qué, y lo que falta por preparar sumado; y la cola enseñaba lo que lleva cada pedido fila a fila, que es lo que la suma de arriba hace innecesario.

**Decidido:**

- **`/reservas/` sigue siendo una sola pantalla para los dos roles** (`DT-34`), y cada uno ve una parte. La administración: tres tarjetas —pedidos, por recoger y lo reservado sin lo devuelto— y un filtro por estado (todos, por recoger, entregados, cancelados). El cajero: lo que está por recoger. **Los dos**: lo que falta por entregar, sumado producto por producto, que es lo que `HU-24` existe para responder.
- **El filtro viaja en la URL** (`?ver=entregados`): las pestañas son enlaces, no peticiones de HTMX, así que el filtro sobrevive a recargar. Un filtro que no existe es un `404`, y uno que no le toca al rol, un `403`.
- **La autorización vive en los selectores**, `pedidos_de_la_cafeteria`, `pedido_de_la_cafeteria` y `tablero_de_reservas`, que sustituyen a `reservas_pendientes`. El cajero no alcanza un pedido cerrado ni escribiendo su URL.
- **El número de un pedido es el del acudiente**: cuenta entre los pedidos de su estudiante, como en `HU-65`. Numerar a todo el colegio seguido daría a la misma reserva dos números.
- **La fila no lleva lo que lleva el pedido**: abre su detalle en la modal de ficha (`[S2.10]` de `./sistema-visual.md`), **la misma plantilla que la del acudiente**, que solo cambia lo que depende de quién mira —quién canceló, a dónde va el formulario—.
- **La cafetería cancela desde esa modal**, como el acudiente: `POST /reservas/<pedido>/cancelar/` devuelve la modal —con el error o ya cancelada— y `HX-Trigger: pedidos-cambiado`, que repinta el tablero entero con su filtro (`DT-16`, `DT-40`). **La página de confirmación desaparece**; el `GET` de esa ruta responde `405`.

**Por qué no basta con la página de confirmación.** Llevaba al personal fuera de la lista para cada pedido y lo devolvía con una redirección, y la confirmación que daba —el pedido y lo que se devuelve antes de pedir el motivo— ya la da la modal. Dos maneras de cancelar el mismo pedido según quién cancele acabarían diciendo cosas distintas.

#### `[DT-50]` `/inventario/`: una pantalla propia sobre el armazón de la aplicación, con el libro firmado

**Obliga:** `DEC-25` y `HU-69`. **Amplía** `DT-34`: es otra pantalla propia de la administración fuera del admin, junto al padrón (`DT-27`), la cola de reservas, los acudientes y `/usuarios/` (`DT-45`).

**Decidido:**

- **La pantalla vive en `base-aplicacion.html` y no dentro del admin.** Sus modales necesitan el sistema visual entero —formularios, interruptores, botones—, y el admin carga Tailwind sin `preflight` (`DT-36`): cada campo pelearía con los estilos de Django. Las vistas están en `inventario/views.py`, con sus dos formularios, como el padrón tiene los suyos.
- **Ninguna vista escribe** (`DT-15`). Crear y editar llaman a `catalogo.services`; ingresar y mermar, a `inventario.services`. Las lecturas son selectores nuevos de `inventario.selectors` —`tablero_del_inventario`, `productos_del_inventario`, `historial_del_producto`—, que exigen el rol antes de leer.
- **Una escritura responde con la misma modal y `HX-Trigger: inventario-cambiado`**; las cifras y la lista lo escuchan y se vuelven a pedir con los filtros que haya (`DT-16`, `DT-40`). Devolver al catálogo responde `204` y deja que la lista se repinte sola.
- **`MovimientoInventario.registrado_por`**, clave ajena nula al usuario con `PROTECT`. **Nula solo por lo escrito antes**: no se puede imponer con una `CheckConstraint` sin inventar autores para esas filas, así que lo exige `asentar`, que es el único punto de escritura del libro, con el argumento sin valor por defecto. `ingresar_mercancia`, `registrar_merma`, `registrar_venta` y `entregar` le pasan su actor. En el historial, lo antiguo sin quién toma el cajero de la venta o quien entregó el pedido; un ingreso o una merma antiguos dicen «sin registrar».
- **La validación en vivo del padrón se reutiliza y se amplía** (`assets/js/interfaz.js`): `data-numero` —entero o decimal, sin signo—, `data-no-mas-que` —las saturadas dentro de las grasas totales, los azúcares dentro de los carbohidratos, las dos `CheckConstraint` de `Producto`—, `data-solo-digitos` para las cantidades, y **un campo vacío no se pinta en rojo hasta que se toca**, aunque «Guardar» siga apagado.
- **La ficha pinta los decimales sin localizar** (`3450`, `3.2`): Django localiza un `Decimal` al pintarlo —«3450,00»— y el formulario no acepta la coma de vuelta, así que guardar sin tocar el precio fallaba. Lo vigila una prueba que devuelve la ficha tal como llega.
- **El admin pierde `ProductoAdmin`, `MermaAdmin` y la vista de historial de `TT-141`**; `MovimientoInventarioAdmin` queda sin alta, edición ni borrado. El proxy `Merma` sigue en el modelo: sus permisos no cambian y una migración no se deshace por quitar una pantalla.
- **`UMBRAL_DE_EXISTENCIAS_BAJAS` se mueve a `inventario.selectors`**, de quien es el dato: lo usan el panel y esta pantalla, y dos umbrales acabarían avisando de cosas distintas.

**Por qué no un «ajuste» con signo.** El libro ya impone que el ingreso sume y la merma reste (`movimiento_inventario_signo_segun_tipo`). Un tercer tipo con signo libre sería una disminución manual que no es merma, y `INV-8` —toda disminución manual lleva motivo— tendría que repetirse en otra restricción para no abrir un camino sin ella.

#### `[DT-51]` `/categorias/`: las categorías fuera del admin, y solo se elimina la vacía

**Obliga:** `DEC-25`. Mismo camino que `DT-50`.

**Decidido:**

- **Una pantalla propia sobre `base-aplicacion.html`**, con dos cifras —cuántas hay y cuántas tienen productos— y una fila por categoría con su recuento, editar y eliminar. Alta y edición son la misma modal. Las vistas viven en `catalogo/views.py`; las escrituras, en `catalogo.services` (`crear_categoria`, `editar_categoria`, `eliminar_categoria`), y la lectura en `categorias_del_catalogo`, que exige el rol antes de leer. Tras escribir, `HX-Trigger: categorias-cambiado` repinta las cifras y la lista, que van en un solo fragmento porque cambian juntas.
- **`Categoria.descripcion`**, opcional, vacía y no nula. Solo la ve quien administra.
- **Se elimina solo una categoría vacía**, contando los productos retirados: siguen existiendo y tienen historial. La garantía es el `PROTECT` de `Producto.categoria`; el servicio da el mensaje, y la modal **no pinta el botón** cuando hay productos (`[S4]` del sistema visual). Los productos no se reasignan solos: a qué categoría van lo decide quien administra.
- **El nombre es único sin distinguir mayúsculas** en el formulario: «bebidas» y «Bebidas» partirían en dos las alertas de `HU-31`.
- **Renombrar alcanza a lo ya vendido, y la modal lo dice.** La línea de venta congela el precio y la nutrición (`DT-8`), no la categoría, y las alertas de frecuencia agrupan por la categoría de hoy. La referencia visual decía que las ventas registradas conservan el nombre; aquí no sería verdad.
- **`CategoriaAdmin` sale del admin.** `AlergenoAdmin` se queda.

#### `[DT-52]` `/alergenos/`: los alérgenos fuera del admin, sin eliminar

**Obliga:** `DEC-26`. **Corrige a `DT-51`** en su último punto: `AlergenoAdmin` tampoco se queda.

**Decidido:**

- **La composición de `/categorias/`, tal cual**: encabezado con «Nuevo alérgeno», dos cifras —cuántos hay y cuántos declara algún producto— y una fila por alérgeno con dos recuentos —productos que lo declaran y estudiantes que lo tienen bloqueado— y **una sola acción, editar**. Alta y edición son la misma modal. Las vistas viven en `catalogo/views.py`; las escrituras, en `catalogo.services` (`crear_alergeno`, `editar_alergeno`), y la lectura en `alergenos_del_catalogo`, que exige el rol antes de leer. Tras escribir, `HX-Trigger: alergenos-cambiado` repinta las cifras y la lista.
- **No hay botón, ruta ni servicio de eliminar.** No es un botón escondido: la acción no existe. Un hueco no se pinta como botón deshabilitado (`[S4]` del sistema visual).
- **Los recuentos cuentan también los productos retirados y los estudiantes de baja**: las filas siguen existiendo y el `PROTECT` las sostiene. Se cuentan por las relaciones inversas (`declaraciones`, `bloqueos`), así que `catalogo` no importa `restricciones`.
- **El aviso de renombrar lleva las dos cifras** del alérgeno que se edita, y dice que la protección sigue al alérgeno y no al nombre. Corregir la escritura es renombrar; cambiar de sustancia es crear otro.
- **`UniqueConstraint(Lower("nombre"))`** en `Alergeno`, además del `unique` que ya tenía. En la categoría bastó el formulario (`DT-51`) porque el fallo partía un reporte; aquí partiría un bloqueo, y la invariante que la base puede imponer la impone la base (`DT-15`). El formulario da el mensaje antes de llegar a ella.
- **`AlergenoAdmin` sale del admin**, y con él la aplicación `catalogo` del índice del admin. El permiso `catalogo.alergeno` se conserva, como los de producto y categoría.

#### `[DT-53]` El panel de la cafetería sale del admin, a `/cafeteria/`

**Obliga:** la raya de `DEC-17` —una pantalla propia sustituye a una del admin cuando alguien la usa a diario— y `DEC-26`. El panel es la pantalla donde aterriza `USR-4` cada vez que entra (`DEC-16`): la más diaria del rol.

**El hecho que lo obliga.** El panel se montó dentro del armazón del admin con un motivo: «quien la consulta ya trabaja ahí». Con `DT-50` … `DT-52` deja de ser cierto: todo lo que la administración escribe —inventario, categorías, alérgenos— y la cola de reservas viven fuera, y en el admin solo le quedan los reportes. Sentado en el admin, el panel pagaba el armazón ajeno: el título lo ponía el admin, más fino y más pequeño que el de las pantallas propias; el contenido arrancaba 8 px más a la derecha; las listas y los enlaces necesitaban un reset acotado (`:where(.armazon-panel)`) para que el admin no les pusiera viñetas, márgenes y subrayado, y cada cambio de estilo pasaba por la segunda hoja (`DT-36`).

**Decidido:**

- **`/cafeteria/` sobre `base-aplicacion.html`**, con el encabezado de las pantallas propias. El nombre de la ruta no cambia (`panel-de-la-cafeteria`), así que el reparto de `cuentas.views.panel` y la barra lateral no se tocan. `/admin/panel/` deja de existir: el admin responde su `404`.
- **Lo que enseña no cambia**: las cinco cifras de la jornada, el aviso de existencias, lo más vendido, las últimas ventas y el mes, del mismo selector (`reportes.selectors.panel_de_la_cafeteria`).
- **Se autoriza una vez, en el selector.** La comprobación de `is_staff` existía porque el armazón del admin no tiene sentido para quien no entra en él; fuera del admin sobra. El rol lo sigue exigiendo el selector (`[S11]`), y el anónimo va al acceso.
- **Los enlaces a los reportes siguen yendo al admin**: los reportes de la cafetería viven allí por decisión (`TT-168`, `TT-176`).
- **La auditoría no sale con él.** Es un reporte, no el aterrizaje, y se queda dentro del admin como los otros tres.
- **Las clases de las tarjetas siguen escritas enteras en `reportes/views.py`**, y por eso `reportes` entra en los `@source` de la hoja de la aplicación. El reset `:where(.armazon-panel)` sale de `estilos/admin.css`: no queda nada que lo use.

#### `[DT-54]` El reporte de ventas sale del admin, a `/ventas/`

**Obliga:** `HU-35`, sin ampliarla. **Corrige** el criterio de `TT-168` de que los reportes de la cafetería viven dentro del admin, **solo para el de ventas**: movimientos de inventario (`TT-170`), cierres de caja (`TT-176`) y auditoría (`TT-178`) se quedan.

**El hecho que lo obliga.** El listado del admin responde «qué ventas hay» y encima pone un total; lo que la administración pregunta es otra cosa —cuánto se vendió, de qué, cómo se pagó y qué días—, y eso son barras, tarjetas de resumen y una modal, composiciones que el admin no carga (`DT-36`). Es el motivo de `DT-51`, no la raya de `DEC-17`: el reporte no se abre a diario.

**Decidido:**

- **Una pantalla sobre `base-aplicacion.html`**, con el periodo arriba —siete, treinta o noventa días, todo, o dos fechas— y, del periodo, cuatro cifras (ingresos, ventas, unidades y productos distintos), los ingresos por categoría, cómo se paga, los más vendidos y los ingresos por día. **Cada día abre su modal** con las ventas de ese día: cliente, medio, quién cobró, renglones e importe. El periodo va en la URL: se puede volver a él y compartirlo.
- **Todo sale de `ventas_registradas`**, sin las reservas canceladas (`DEC-24`), y de las líneas congeladas (`DT-8`). Lo nuevo vive en `reportes.selectors.reporte_de_ventas`.
- **Las categorías y los nombres son los de hoy, y la pantalla lo dice.** La línea de venta congela precio y nutrición, no el nombre ni la categoría (`DT-8`, `DT-51`). La referencia visual afirmaba lo contrario; aquí no sería verdad.
- **Los medios de pago son tres** (`DEC-1`). El pedido anticipado es un origen, no un medio: se paga con la billetera al reservar, y la pantalla dice cuánto de la billetera vino de pedidos.
- **Sin ranking de gasto por estudiante.** `[S11]` le da a la cafetería los reportes de ventas e inventario; el consumo por estudiante es del acudiente, y los datos de los menores, de la institución (Ley 1581). El nombre del cliente se sigue viendo venta a venta, en la modal, como en el listado que sustituye.
- **`VentaAdmin` sale del admin**, y con él lo que colgaba de su listado:
  - el cierre de caja enlaza a `/ventas/dia/<fecha>/?medio=efectivo`, que abre la modal del día con las ventas en efectivo, las mismas que sumó el esperado (`INVD-5`);
  - la auditoría enlaza a `/ventas/venta/<id>/`, que abre la modal de esa venta **también si su pedido se canceló**, con quién lo canceló y por qué (`DT-48`);
  - el panel enlaza a `/ventas/`.
- **Una ruta de página y una de fragmento por modal** (`DT-16`): `/ventas/dia/<fecha>/` y `/ventas/venta/<id>/` son la pantalla con la modal ya abierta; sus `…/ficha/` son el fragmento.
- **Se pierde la búsqueda por nombre del estudiante y por correo de quien cobró**, que el listado del admin daba. Se acepta: el reporte es de la operación, no de personas.
- **Imprimir** es el del navegador, con la hoja de impresión que ya existe: sin barra, sin periodo y sin botones.

#### `[DT-55]` El reporte de cierres de caja sale del admin, a `/cierres/`

**Obliga:** `HU-56`, sin ampliarla. **Corrige a `DT-54`** en un punto: allí el reporte de cierres se quedaba en el admin. El de movimientos de inventario (`TT-170`) y la auditoría (`TT-178`) siguen dentro.

**El hecho que lo obliga.** Con el reporte de ventas fuera, el de cierres era la mitad de una pareja partida entre dos interfaces: su enlace «de dónde sale el esperado» ya llevaba de un armazón al otro. Y lo que `HU-56` pide —detectar un patrón de descuadres— se lee mejor con las composiciones del sistema visual que con las tablas en línea del admin.

**Decidido:**

- **Una pantalla sobre `base-aplicacion.html`**, con el periodo de `/ventas/` —siete, treinta o noventa días, todo, o dos fechas, **sobre la `fecha` de la jornada** y no sobre cuándo se registró—, los filtros que tenía el admin —resultado del cuadre, cajero y búsqueda en el motivo— y el orden por fecha o por **mayor descuadre**, que es como se encuentra el peor día. Todo va en la URL.
- **Las cifras de arriba son las del conjunto filtrado**, como en el admin: `resumen_de_cierres` recibe el mismo `QuerySet` que pinta la tabla. **La primera es el descuadre total**, no la neta: la neta se compensa sola y diría «la caja cuadra» de un mes con veinte descuadres. Sin cierres no se pinta un cero: se dice que el periodo no alcanzó ninguna jornada.
- **Tabla de datos** (`[S2.2]`): fichas por debajo de `tablet`, tabla desde ahí. La diferencia lleva el color de su estado —sobrante, faltante o sin diferencia—, porque ahí el estado existe. **La fila abre la modal del cierre**, con el enlace a las ventas en efectivo de esa jornada (`INVD-5`, `DT-54`).
- **El cajero, por su nombre**, en la tabla, en el filtro y en la modal: el correo es una credencial (`TT-176`). La búsqueda ya no busca por correo.
- **La invariante sigue a la vista**: cuántos cierres con diferencia no llevan motivo, que la base impide (`cierre_de_caja_diferencia_con_motivo`).
- **`CierreDeCajaAdmin` sale del admin**, con sus dos filtros. La auditoría enlaza a `/cierres/<id>/`, que es la pantalla con la modal de ese cierre abierta; `/cierres/<id>/ficha/` es el fragmento (`DT-16`).
- **El registro del cierre no se toca**: lo sigue haciendo el cajero en `/punto-de-venta/cierre/` (`HU-55`). Esta pantalla solo consulta, y sus rutas solo responden a `GET`.

#### `[DT-56]` La auditoría sale del admin, a `/auditoria/`

**Obliga:** `HU-37`, sin ampliarla. **Corrige a `DT-55`** en un punto: allí la auditoría se quedaba en el admin. Ahí solo queda el reporte de movimientos de inventario (`TT-170`).

**El hecho que lo obliga.** De los cuatro reportes de la cafetería, tres ya son pantallas propias y la auditoría enlaza a dos de ellos: abrir una venta o un cierre desde la línea de tiempo llevaba de un armazón al otro. La razón por la que vivía en el admin —«quien la consulta ya trabaja ahí»— dejó de ser cierta con `DT-50` … `DT-55`.

**Decidido:**

- **Una pantalla sobre `base-aplicacion.html`**, con el periodo de `/ventas/` y `/cierres/` —siete días por defecto, como hasta ahora—, una cifra por clase de operación que **filtra la línea de tiempo** al pulsarla, y la línea de tiempo agrupada por día: la hora, quién, qué, el detalle y el importe.
- **El filtro por clase va al selector**, no a la plantilla: `auditoria` recibe las clases y solo consulta esas. Filtrar después del tope de `OPERACIONES_MAXIMAS` dejaría fuera operaciones de la clase pedida sin decirlo.
- **Una venta o un cierre se abren en la modal de la propia auditoría**, con los fragmentos de `DT-54` y `DT-55`: quien rastrea no pierde la línea de tiempo. Un ingreso o una merma enlazan a su ficha del admin, que es donde sigue el libro de inventario.
- **Lo que ya decía, lo sigue diciendo**: el hueco de quién en los movimientos anteriores a `HU-69`, y que el tope recortó.
- **La ruta cambia y su nombre no**: `auditoria`. Los enlaces de los reportes y la barra no se tocan; `/admin/auditoria/` deja de existir y el admin responde su `404`. Sobra la comprobación de `is_staff`: el rol lo exige el selector.
- **No entran ni las recargas ni las restricciones**, como hasta ahora: `[S11]` no le da a la cafetería el saldo de las familias ni la escritura de las restricciones (`INV-4`), y la auditoría no es una puerta lateral a ninguno de los dos.

#### `[DT-57]` El cobro del punto de venta se confirma en dos modales, y el catálogo lleva foto

**Obliga:** `HU-21` e `INT-2`, sin ampliarlas. **Corrige** la tercera decisión del armazón del punto de venta (`TT-57`, `base-punto-de-venta.html`): «sin diálogos, ninguna acción del punto de venta se confirma con un modal». **Es una decisión del dueño del producto, tomada sabiendo lo que cuesta**, no una conclusión técnica.

**Lo que cuesta, dicho antes de construirlo:** dos gestos más por venta, también en la billetera —la venta más frecuente—, donde la primera modal no calcula nada. Con `INT-2` —toda la demanda del descanso en veinte a treinta minutos, con dos a cinco cajeros— ese es el presupuesto que se gasta.

**Decidido:**

- **El catálogo es de tarjetas con la foto del producto** (`HU-59`), su precio, sus calorías si las declara y sus existencias, que siguen sin autorizar (`DT-6`). Sin producto en la venta, la tarjeta ofrece «Añadir»; con él, «− n +». El ticket mantiene su «− +», y los dos se repintan juntos: cada gesto devuelve el ticket y, fuera de banda, la tarjeta de ese producto.
- **«Cobrar» abre la confirmación**: cliente, renglones, total y medio de pago, en los tres medios. **En efectivo lleva «Dinero recibido»**, una calculadora: la devuelta —o lo que falta— la calcula el servidor a cada tecla con el formateador del dinero, que es uno solo. **No se guarda**: la venta no tiene esa columna, y lo que el cliente entregó no es un hecho del sistema.
- **Al cobrar, la modal pasa a «Venta registrada»** con lo que se cobró de verdad —el total lo calcula el servidor con los precios del momento— y, en efectivo, la devuelta. El ticket, el cliente y el catálogo se repintan detrás, fuera de banda, como antes.
- **El foco sigue siendo del lector**, con las dos excepciones que la modal obliga a hacer: **Enter en «Dinero recibido» no cobra**, solo lleva el foco a «Cobrar» —un código leído por error dentro del campo no confirma la venta—, y al cerrar cualquier modal el foco vuelve al campo de la tarjeta. Escape cancela.
- **Riesgo que queda**: en billetera y transferencia el foco nace en «Cobrar», así que pasar una tarjeta con la modal abierta confirma la venta con su Enter. Se acepta: el cajero no escanea con la confirmación delante, y la venta queda en el ticket y en la auditoría.
- **El cliente se olvida al cobrar**, como hasta ahora: «Venta nueva» es la única salida de la segunda modal. Dejarlo puesto invitaría a cobrarle la siguiente venta a quien ya se fue.
- **Lo que la referencia traía y no entra**: el número de compra —las ventas no tienen número correlativo—, el filtro del catálogo por nombre y categoría, la lista de últimas ventas del turno y el nombre «Prepago», que aquí es la billetera.

#### `[DT-58]` El cajero entrega también desde `/reservas/`, con un panel y dos modales

**Obliga:** `HU-24` y `HU-25`, sin ampliarlas. **Amplía** `DT-34` —para el cajero, la pantalla compartida deja de ser solo de consulta— y **corrige** a `DT-49` en dos puntos: el cajero ya no abre el detalle en la modal de ficha, y lo que falta por entregar se le enseña plegado. **Es una decisión del dueño del producto**, como `DT-57`.

**El hecho que lo obliga.** Durante el descanso el cajero no lee cifras: busca un pedido y lo entrega. La pantalla le enseñaba una tarjeta de «Por recoger», la suma por producto y una lista cuyo detalle se abría en una modal **sin forma de entregar**: para eso había que volver al punto de venta y escanear la tarjeta. Un pedido que se busca por el nombre no tenía salida en la pantalla donde se busca.

**Decidido:**

- **La vista del cajero de `/reservas/` se llama «Entregas»**, en su menú y en la barra del punto de venta: un buscador, la lista de lo que está por recoger y, al lado, un panel con el pedido elegido —quién, qué lleva y lo pagado— y dos acciones, «Marcar como entregado» y «No se puede entregar: cancelar y devolver».
- **Entregar pide confirmación**, en una modal con la fotografía del estudiante, su nombre y lo que lleva. En el punto de venta no la pide (`TT-150`) y no es una contradicción: allí la tarjeta escaneada ya dijo quién es; aquí el pedido se elige de una lista, y la fotografía es el único control de que se entrega a quien lo reservó (`DEC-8`, `HU-58`).
- **Cancelar pide el motivo en una modal**, obligatorio, y nada más. El servicio es el mismo que en la modal de la administración (`cancelar_pedido`, `HU-67`).
- **El buscador filtra la lista**, y solo la lista: el código de una tarjeta escaneada y el documento se comparan **exactos**, como en la caja (`HU-16`) —una coincidencia parcial de documento sería un listado de menores—, y el nombre, por una parte.
- **Las dos escrituras responden con el panel** —entregado, cancelado o con el rechazo— y `HX-Trigger: pedidos-cambiado`; la modal se cierra al recibir la respuesta y la lista se repinta. Un rechazo —otra caja ya lo entregó, el estudiante no puede retirar (`INVD-2`)— vuelve al panel en `200`, como en el punto de venta: htmx no intercambia un `4xx`.
- **Un estudiante que no puede retirar no ofrece «Marcar como entregado»**: el panel dice por qué y deja solo cancelar. No es un botón deshabilitado (`[S2.4]` de `./sistema-visual.md`).
- **Lo que falta por entregar se queda, plegado** debajo de la lista. Es lo que `HU-24` existe para responder, y se mira antes del descanso, no durante.
- **La entrega del punto de venta se queda** tal cual y sin diálogo: escanear y entregar sigue siendo el camino rápido.
- **La administración no cambia**: cifras, pestañas y la modal de ficha. No entrega (`[S11]`).

**Lo que cuesta, dicho antes de construirlo.** Dos interfaces para cancelar el mismo pedido según quién lo haga, que es lo que `DT-49` evitaba; el servicio y el motivo son uno solo. Y dos caminos de entrega con distinta fricción: aquí hay un gesto más que en la caja, aceptado porque aquí no hay tarjeta.

**Lo que la referencia traía y no entra**: el cargo por servicio sobre el pedido, que aquí no existe, y la pantalla de cocina.

#### `[DT-59]` El cierre de caja sale de `/punto-de-venta/` a `/cierre-de-caja/`, con el sistema visual

**Obliga:** `HU-55`, sin ampliarla: ninguno de sus criterios sitúa el cuadre en el punto de venta. **Corrige** a `TT-173` en la ruta, y a `DT-55` en la línea que dice dónde cuadra el cajero. **Es una decisión del dueño del producto**, como `DT-57` y `DT-58`.

**El hecho que lo obliga.** El cierre ya vivía en el armazón de la aplicación, pero colgaba de `/punto-de-venta/` y llevaba arriba «← Punto de venta»: una miga hacia una pantalla de la que no viene necesariamente —el cajero llega desde su menú— y que ninguna otra pantalla del armazón lleva. Y era anterior a `DT-25`: tarjetas sin franja ni icono, la cifra esperada suelta y los campos con las flechas del navegador.

**Decidido:**

- **La ruta es `/cierre-de-caja/`**, con el mismo nombre, `cierre-de-caja`: los menús y las pruebas lo resuelven por nombre y no cambian. `/punto-de-venta/cierre/` deja de existir; no se redirige, porque sin despliegue (`DEC-15`) no hay enlaces guardados que proteger.
- **El encabezado es el de pantalla** (`[S2]` de `./sistema-visual.md`): título y frase, sin miga.
- **Sin cerrar**, el efectivo esperado es una **tarjeta de resumen** en la variante del panel de la cafetería —franja e icono de la misma serie, sin enlace— con la frase que dice de cuántas ventas sale (`INVD-5`); el formulario, una tarjeta con su cabecera, los dos importes lado a lado desde `tablet` y sin las flechas del campo numérico.
- **Ya cerrada**, cuatro tarjetas de resumen —esperado, base, contado y diferencia— y debajo el resultado, el motivo si lo hubo y quién lo cuadró. La franja de la diferencia es una serie, **no `aviso`**: el estado lo dice la pastilla, como en `/cierres/` (`[S2.1]`).
- **Lo que no cambia**: el formulario, el servicio, la redirección tras cuadrar y que el esperado no se pueda escribir (`INVD-5`).

#### `[DT-60]` Las imágenes entran en cinco formatos, salen en WEBP, y la lista limita los decodificadores

**Obliga:** `DEC-8` y `ALC-OUT-08`, como `DT-20`. **Corrige** a `DT-20` en dos frases: la lista de formatos de entrada y el formato de salida. Las dos razones de `DT-20` —la superficie de ataque y el EXIF— siguen intactas.

**El hecho que lo obliga.** `DT-20` admite solo `image/jpeg`, `image/png` e `image/webp`, y re-codifica «a JPEG o WebP». La canalización (`config/imagenes.py`, `TT-55`) acepta además **GIF y BMP** desde su primer commit, y re-codifica **siempre a WEBP**; las dos fichas que suben imágenes —la del estudiante (`HU-57`) y la del producto (`HU-59`)— los anuncian en su texto de ayuda. Nadie registró esa diferencia. Y al revisarla salió una segunda: la lista se comprobaba **después** de que Pillow abriera el fichero, así que un TIFF, un PSD o un ICO pasaban por su decodificador antes de rechazarse.

**Decidido:**

- **Se aceptan JPEG, PNG, WEBP, GIF y BMP.** Lo que `DT-20` protege es lo que se guarda y se sirve —un SVG con `<script>`, un políglota, el EXIF con el GPS—, y la re-codificación lo neutraliza igual en los cinco: la imagen se reconstruye desde sus píxeles. Quitar GIF y BMP le daría un error a quien suba uno sin ganar nada; la prueba de los políglotas, de hecho, usa un GIF.
- **La salida es siempre WEBP**, con transparencia cuando la hay. «JPEG o WebP» dejaba abierta una elección que el código ya hizo.
- **La lista se le pasa a `Image.open(…, formats=…)`**, en las dos aperturas. Así es la lista la que decide qué decodificadores leen un fichero de quien sea, que es donde está el riesgo de aceptar imágenes. Un formato fuera de ella llega como «no identificado», y el mensaje dice cuáles se aceptan.
- **SVG sigue fuera**, y no por la lista: Pillow no lo decodifica. Es la primera razón de `DT-20`.

**Lo que cuesta.** El mensaje ya no distingue «esto no es una imagen» de «es una imagen en un formato que no aceptamos»: Pillow no puede saberlo sin abrirla, y abrirla es justo lo que se evita. Y un GIF animado se queda en su primer fotograma.

#### `[DT-61]` El entorno de las exposiciones: una EC2 con el mismo `docker compose`, y Caddy delante

**Obliga:** `DEC-27`. **Corrige** a `DT-31`, que retiraba todo entorno desplegado; lo que `DT-31` conservaba —los ajustes de seguridad de `DEBUG = False` y la sonda `/salud/`— es justo lo que este entorno usa.

**El hecho que lo obliga.** `DEC-27` pide una URL con HTTPS durante las exposiciones, dentro de lo que permite un AWS Academy Learner Lab. Al revisar la cuenta, el laboratorio **deniega SES y CloudFront**, no tiene zonas de Route 53 ni certificados de ACM —que sin un dominio propio no sirven—, y sus credenciales **caducan en cada sesión**, así que no pueden ir en ningún fichero.

**Decidido:**

- **Una instancia EC2 `t3.medium`** (2 vCPU, 4 GB) con Ubuntu 24.04 en `us-east-1`, 30 GB de disco y una **IP elástica**, para que la dirección —y con ella el nombre— sobreviva a cada parada del laboratorio. La `t3.small` alcanzaba, pero justa al construir la imagen con PostgreSQL al lado; el coste por hora de la diferencia no pesa con sesiones de cuatro horas.
- **`compose.produccion.yaml`, al lado de `compose.yaml` y sin sustituirlo**: los mismos PostgreSQL, SeaweedFS y Mailpit, la misma imagen de la aplicación con el código montado, y **Caddy** delante. Las diferencias son las de estar en internet: `gunicorn` con `DEBUG = False` en vez de `runserver`, las hojas compiladas una vez al arrancar (`docker/arrancar-produccion.sh`) en vez del servicio `estilos`, y las credenciales desde el `.env` del servidor, **sin valor por defecto**: si falta una, el stack no arranca en vez de caer en las de desarrollo, que están publicadas.
- **Solo Caddy publica puertos**, el 80 y el 443; el 22 se abre únicamente a la IP de quien despliega, en el grupo de seguridad. PostgreSQL, SeaweedFS y Mailpit se alcanzan por la red de compose o a través de Caddy.
- **El nombre es de sslip.io**: `34-198-167-139.sslip.io` resuelve a `34.198.167.139` sin registrar nada, y lo mismo cualquier subdominio. Caddy pide un certificado de Let's Encrypt **por nombre**:
  - el dominio y un subdominio por rol —`institucion.`, `administracion.`, `cajero.`, `acudiente.`—, que llevan a la misma aplicación y guardan cookies distintas: un rol en cada pestaña, como `[S2.1.1]` de `./desarrollo.md`;
  - `s3.`, que lleva al API S3 de SeaweedFS. **Es un subdominio y no una ruta** porque la firma de las URL de las fotografías (`DT-21`) cubre el nombre del host: Caddy lo reenvía tal cual, y una ruta habría que reescribirla, rompiendo la firma;
  - `correo.`, que lleva a Mailpit **detrás de una contraseña** (`DEC-3`).
- **El código se copia, no se clona**: el contenido versionado del repositorio viaja por SSH a `~/smartfood`, y `app` se reinicia. En el servidor no hay credenciales de GitHub que gestionar.

**Descartado:**

- **RDS para la base.** Copias automáticas y «servicio gestionado», a cambio de crédito extra, otro recurso que el laboratorio para y arranca, y una red que configurar. Con datos ficticios que se vuelven a sembrar no aporta nada.
- **Un bucket de S3.** Funcionaría con el rol de la instancia, sin credenciales en ficheros, pero sería la única pieza que no es la de local (`DT-18` defiende esa paridad) y `DEC-27` eligió el contenedor.
- **Un balanceador con ACM, o CloudFront.** El primero necesita un dominio propio que validar; el segundo, el laboratorio lo deniega.

**Lo que cuesta.** Una sola máquina: si se borra la instancia, se pierden la base y las fotografías, que se recrean sembrando. Y el límite de Let's Encrypt de 50 certificados por semana se aplica a todo `sslip.io`, que **no está en la Public Suffix List**: lo comparten todos sus usuarios. Al montarlo los siete certificados salieron sin problema; si un día no salen, la salida es un nombre de DuckDNS, que sí está en la lista.
