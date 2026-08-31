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
| fecha_decisiones | 2026-08-29; `DT-22` el 2026-08-31 |
| decidido_por | Equipo SmartFood |
| decisiones | 22 (`DT-1` … `DT-22`) |
| entidades_modelo | 17 |
| clave_primaria | UUIDv7 en todas las tablas, con una excepción declarada (`DT-17`) |
| idioma | es-CO |
| version | 1.1 |

### [S0.2] Instrucciones de lectura para el agente

1. Documento **derivado**: no reexpresa ningún original y no lleva texto verbatim.
2. **Ninguna decisión introduce alcance.** Cada una declara **qué la obliga**: la invariante, la historia o el elemento del alcance del que se deriva. Una decisión técnica sin esa columna es una preferencia disfrazada y debe cuestionarse.
3. Distinguir dos clases de decisión: las **forzadas** por una invariante —donde no hay libertad real y desviarse rompe un requisito— y las **de conveniencia**, donde había alternativas legítimas y se eligió una. `[S1]` las separa.
4. `[S2]` es el modelo de datos núcleo. Es un boceto de diseño, no un esquema final: los nombres y los campos se ajustarán al implementar, pero **la forma no** —los libros de movimientos y la relación producto–alérgeno son las decisiones que sostienen las invariantes—.
5. Los identificadores `[DT-n]` son estables y citables.

### [S0.3] Mapa de secciones

| ID | Sección | Contenido |
|---|---|---|
| S1 | Decisiones técnicas | `DT-1` … `DT-22`, separadas en forzadas y de conveniencia |
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

Una app de Django por dominio —`cuentas`, `personas`, `catalogo`, `billetera`, `inventario`, `ventas`, `reportes`— y dentro de cada una la misma forma:

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
- **Alpine.js solo aquí**, para el estado local del carrito. En acudiente y administración, HTMX solo.

`INT-3` no lleva plantillas propias: lo cubre el admin (`DT-2`). Tailwind se compila con su CLI, sin CDN.

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

---

## [S2] Modelo de datos núcleo

Diecisiete entidades, todas con **clave primaria UUIDv7** (`DT-17`). Los nombres se ajustarán al implementar; **la forma no**.

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
| `MovimientoBilletera` | billetera, tipo (`recarga`/`venta`/`devolucion`), monto, venta, creado_en | `DT-4`, `INV-2` |

**Sin columna `saldo`.** Saldo = suma de movimientos.

### Catálogo

| Entidad | Campos clave | Sostiene |
|---|---|---|
| `Categoria` | nombre | `HU-31` (alertas por categoría) |
| `Alergeno` | nombre | `DT-7` |
| `Producto` | nombre, precio, categoría, campos nutricionales, imagen_clave | `ALC-IN-15`, `HU-59` |
| `ProductoAlergeno` | producto, alérgeno | `DT-7`, `INV-5` |
| `MovimientoInventario` | producto, tipo (`ingreso`/`venta`/`merma`), cantidad, **motivo**, venta, creado_en | `DT-5`, `INV-3`, `INV-8` |

**Sin columna `existencias`.** Existencias = suma de movimientos.

### Control parental

| Entidad | Campos clave | Sostiene |
|---|---|---|
| `RestriccionProducto` | estudiante, producto | `HU-10` |
| `RestriccionAlergeno` | estudiante, alérgeno | `HU-11`, `INV-5` |
| `LimiteDiario` | estudiante, monto | `HU-09` |

Las tres son escribibles **solo** por el acudiente (`DT-11`, `INV-4`).

### Venta

| Entidad | Campos clave | Sostiene |
|---|---|---|
| `Venta` | cajero, **estudiante (opcional)**, medio_pago (`billetera`/`efectivo`/`transferencia`), creado_en | `DEC-1`, `HU-53`, `HU-54` |
| `LineaVenta` | venta, producto, cantidad, **precio e información nutricional copiados** | `DT-8`, `HU-22` |
| `PedidoAnticipado` | estudiante, estado, venta | `ALC-IN-10`, `HU-23` |
| `CierreCaja` | fecha, cajero, base, efectivo_contado, ventas_efectivo, diferencia, motivo | `DEC-6`, `INVD-5`, `HU-55` |

`Venta.estudiante` **opcional** es lo que habilita la venta a cliente genérico de `DEC-1`: una venta sin estudiante es una venta a `USR-6`.

---

## [S3] Cómo se sostiene cada invariante

| Invariante | Decisión que la sostiene | Cómo |
|---|---|---|
| `INV-1` Sin saldo negativo | `DT-1`, `DT-6` | Validación dentro del bloqueo pesimista |
| `INV-2` Saldo reconstruible | `DT-4` | El saldo **es** la suma del historial |
| `INV-3` Existencias explicables | `DT-5` | Las existencias **son** la suma del historial |
| `INV-4` Restricciones no desactivables | `DT-11` | Sin permiso de escritura para cajero, admin ni institución |
| `INV-5` Bloqueo por condición | `DT-7` | Relación evaluada en la venta, no lista materializada |
| `INV-6` Sin autorregistro | `DT-10` | Las rutas de registro no existen |
| `INV-7` Código aleatorio | `DT-9` | Generador criptográfico con índice único |
| `INV-8` Motivo obligatorio | `DT-5` | Restricción en la base de datos |
| `INV-9` Recomendaciones orientativas | — | Es de interfaz (`HU-34`), no de modelo |
| `INVD-1` Ninguna cuenta por autorregistro | `DT-10` | Mismo mecanismo para los cuatro roles |
| `INVD-2` Desactivado no compra | `DT-12`, `DT-6` | Estado evaluado dentro de la transacción de venta |
| `INVD-3` Solo la institución reactiva | `DT-11`, `DT-12` | Transición de estado permitida solo a ese rol |
| `INVD-4` Reasignar invalida el anterior | `DT-9` | El código vigente es un único valor por estudiante |
| `INVD-5` Efectivo explicable | `DT-5` | Cierre calculado desde ventas registradas |
| `INVD-6` Ninguna foto real | `DT-14`, `DT-18` | Avatares generados por el seed |
| — (`DEC-8`, `ALC-OUT-08`) | `DT-20` | Re-codificación que retira el EXIF y neutraliza formatos políglotos |

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
- **Cálculo del saldo con el historial creciendo.** `DT-4` calcula el saldo por agregación. Para el volumen del prototipo sobra, pero conviene medirlo antes del Avance 2 y dejar registrada la cifra en `ENT-06` como limitación conocida.
- **Estrategia de pruebas automatizadas.** La Definición de Terminado exige un caso de prueba por invariante, pero **no se ha decidido formalmente** si son pruebas automatizadas o guiones manuales. Alejandro es dueño del plan de pruebas (`[S12]`).
  **Resuelto de hecho, no de derecho:** lo construido hasta ahora lleva **114 pruebas automáticas** con el ejecutor de Django, y `DoD-5` se ha venido cumpliendo con ellas. El punto sigue abierto porque una práctica no es una decisión: falta que el dueño del plan de pruebas la adopte —o la cambie— y quede escrita. Mientras tanto, `DoD-5` dice «caso de prueba» sin adjetivo, a propósito (`[S2]` de `./definicion-de-terminado.md`).
- **Caducidad de las URL firmadas.** `DT-18` fija que la fotografía se sirve firmada, no cuántos minutos dura la firma.
- **PaaS concreto.** `DT-13` fija el tipo de despliegue, no el proveedor. **Resuelto en la práctica:** el entorno de pruebas está en Railway, y el bucket es el suyo (`DT-21`). La decisión sigue sin ser normativa: `DT-13` no obliga a ese proveedor.

---

## [ANEXO C] Nota de procedencia

Decisiones tomadas por el equipo el 2026-08-29, tras revisar qué exigen las invariantes del anteproyecto (`INV-1` … `INV-9`) y las derivadas de las decisiones de alcance (`INVD-1` … `INVD-5`).

El documento separa deliberadamente las decisiones **forzadas** de las **de conveniencia**. Once de las catorce son forzadas: no son preferencias del equipo sino la única forma de cumplir un requisito ya acordado. Las tres de conveniencia —framework, arquitectura de interfaz y despliegue— llevan declarada su alternativa descartada y el motivo.

`[S2]` cubre el «modelo de datos» que `ENT-03` exige. Falta el «diagrama de arquitectura» y la reexpresión de la «matriz de roles y permisos», que ya existe en `[S11]` de `./smartfood.md` y no se duplica aquí.

**Ninguna decisión introduce alcance.** No hay entidad en `[S2]` que soporte una funcionalidad que no esté en una historia, y `[S3]` permite comprobar que cada invariante tiene una decisión que la sostiene.
