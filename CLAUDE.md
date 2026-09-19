# CLAUDE.md

Guía de trabajo para Claude Code en este repositorio.

## Qué es esto

**SmartFood**: prototipo de plataforma de gestión para cafeterías escolares con control parental y
trazabilidad digital. Proyecto de la asignatura *Proyecto Aplicado en TIC 1* (UPB, 202601).

Equipo de 4, de los cuales **2 desarrollan**. Cinco sprints de dos semanas, semanas 6 a 15.

**Los Sprints 1, 2, 3 y 4 están cerrados** —56, 37, 43 y 18 tareas, todas integradas—. El 3 fue el del control parental y **creció de 37 a 43 tareas** con `HU-60` y `HU-61`, dos huecos que la planeación no vio. El 4 fue el de inventario trazable y pedidos anticipados: cerró `TST-4` y con él **los cuatro escenarios críticos de `ENT-05`**, y retiró el entorno desplegado del alcance (`DEC-15`). Las revisiones de cierre están en `[S7]` de cada plan de PR; la del 4 encontró dos defectos y los arregló antes de cerrar.

**Lo siguiente es el Avance 2** (`EVA-4`, 20 %), semana 14: lo que se enseña es lo que hay en `main`, y el guion está en `[S8]` de `./docs/plan-de-pull-requests-sprint-4.md`. Después, el **Sprint 5**: reportes y plan de pruebas, el más cargado de los dos que quedan.

## Antes de escribir código, lee esto

`docs/` no es documentación decorativa: es el contrato del proyecto. Orden de lectura:

| Documento | Para qué |
|---|---|
| `docs/smartfood.md` | Contexto: problema, objetivos, alcance (`S9`), solución (`S10`), matriz de permisos (`S11`), usuarios (`S5`) |
| `docs/decisiones-de-alcance.md` | Alcance acordado **después** del anteproyecto (`DEC-n`) |
| `docs/decisiones-tecnicas.md` | Arquitectura, stack y modelo de datos (`DT-n`) |
| `docs/backlog-historias-de-usuario.md` | Las historias con sus criterios de aceptación |
| `docs/sprint-4-backlog.md` | Las 18 tareas del Sprint 4 (`TT-137` … `TT-154`). **Cerrado** |
| `docs/plan-de-pull-requests-sprint-4.md` | Esas 18 tareas en 7 PR, su **revisión de cierre** (`[S7]`) y el guion del Avance 2 (`[S8]`) |
| `docs/sprint-3-backlog.md` y los anteriores, con sus planes de PR | Los sprints cerrados. Archivo, consulta histórica |
| `docs/sprint-1-backlog.md` y `docs/sprint-2-backlog.md`, con sus planes de PR | Los sprints 1 y 2, cerrados. Archivo, consulta histórica |
| `docs/definicion-de-terminado.md` | Los seis criterios de cierre (`DoD-1` … `DoD-6`) |
| `docs/despliegue.md` | **Por qué no hay entorno desplegado** (`DEC-15`), y qué costó el que hubo |
| `docs/desarrollo.md` | Reconstrucción local, credenciales y comandos del día a día |
| `docs/mapa-de-la-aplicacion.md` | Qué pantallas hay, quién alcanza cada una y el recorrido de demostración |
| `docs/sistema-visual.md` | **Qué composición copiar al construir una pantalla**, y de qué plantilla (`DT-25`) |
| `docs/reglas-de-la-venta.md` | **Qué comprueba la venta, en qué orden y por qué.** Léelo antes de añadir la séptima condición |
| `docs/reglas-del-pedido-anticipado.md` | **Qué mueve cada momento del pedido** —reservar, consultar, entregar— y las siete reglas que ninguna historia dice |
| `docs/formato-de-carga.md` | Contrato del archivo de carga de estudiantes (`TT-22`) |
| `docs/campos-nutricionales.md` | Qué declara cada producto y por qué esos campos (`TT-44`) |
| `docs/recorrido-de-administracion-de-estudiantes.md` | Recorrido UX de la vista de estudiantes y qué cambió por él (`TT-35`) |
| `docs/prueba-de-concepto-del-lector.md` | Guion de `TT-72`: tarjetas impresas y lector físico (`ENT-02`) |
| `docs/convenciones-de-git.md` | Ramas, convención de commits y publicación de versiones (`TT-01`) |

**El alcance vigente es `[S9.1]` de `smartfood.md` MÁS `[S1]` de `decisiones-de-alcance.md`.**
**Nueve** decisiones amplían el anteproyecto (`DEC-1` … `DEC-8` y `DEC-13`) y **dos lo recortan**
(`DEC-14`, `DEC-15`); ninguna está incorporada a él. Para responder qué hace o no hace el sistema
hay que mirar los dos, y `[S3]` de `decisiones-de-alcance.md` dice cuál hace qué.

Las referencias con prefijo `corpus:` apuntan a documentos del corpus de la asignatura que **no
están en este repositorio** (material de clase, Guía de Scrum, el DOCX original). No son rutas rotas.

## Las invariantes no se negocian

Dieciséis reglas que el sistema debe cumplir siempre. Están en `[S10.2]` de `smartfood.md` (`INV-1` …
`INV-9`) y en `[S2]` de `decisiones-de-alcance.md` (`INVD-1` … `INVD-7`). Las que más
condicionan el código:

| | Regla | Cómo se sostiene |
|---|---|---|
| `INV-1` | Ninguna venta deja saldo negativo | Validar **dentro** del bloqueo pesimista, nunca antes (`DT-6`) |
| `INV-2` | El saldo se reconstruye desde el historial | **No existe columna `saldo`**: es la suma de los movimientos (`DT-4`) |
| `INV-3` | Las existencias se explican desde el historial | **No existe columna `existencias`** (`DT-5`) |
| `INV-4` | Las restricciones no las desactiva la cafetería | Permisos en la capa de datos, **no ocultando botones** (`DT-11`) |
| `INV-5` | El bloqueo por alérgeno es sobre la condición | Relación evaluada en la venta, **nunca lista materializada** (`DT-7`) |
| `INV-6`, `INVD-1` | Ninguna cuenta por autorregistro | Las rutas de registro **no existen** (`DT-10`) |
| `INV-7` | Código de tarjeta aleatorio y no secuencial | Generador criptográfico. **Nunca UUIDv7**: lleva timestamp y va ordenado (`DT-9`, `DT-17`) |
| `INV-8` | Toda disminución manual lleva motivo | `CheckConstraint`, no un `if` (`DT-5`) |
| `INVD-6` | Ninguna fotografía es de una persona real | Avatares generados en el seed (`DT-14`) |
| `INVD-7` | Desactivado o de baja tampoco **recibe recargas** | Una sola puerta en `personas` para las dos direcciones del dinero (`DEC-14`) |

Si una tarea parece exigir romper una invariante, **no la rompas: dilo.** Es señal de que la tarea
está mal entendida o de que falta una decisión.

## Stack y arquitectura

**Django + PostgreSQL + HTMX + Tailwind.** Monolito, un repositorio y **sin despliegue**: se
ejecuta en local (`DEC-15`, `DT-31`). UUIDv7 como clave primaria en todas las tablas (generado en
la aplicación), **excepto el código de tarjeta**.

Una app por dominio, **y cada una se crea en el sprint que la necesita**: hoy existen
`cuentas`, `personas`, `catalogo`, `billetera`, `inventario`, `ventas` y `restricciones`
—esta última no la previó `DT-15` y la declara `DT-28`—; `reportes` no.
Dentro de cada una:

| Archivo | Responsabilidad |
|---|---|
| `models.py` | Estructura e invariantes de datos (`CheckConstraint`, `UniqueConstraint`). Sin lógica de negocio |
| `services.py` | **Toda escritura.** Funciones, no clases; cada una abre su `transaction.atomic()` |
| `selectors.py` | **Toda lectura** no trivial. No conocen `request` |
| `views.py` | HTTP: parsear, delegar, renderizar. **Cero lógica de negocio** |

Tres reglas (`DT-15`):

1. **Una vista nunca escribe directamente**: llama a un servicio.
2. **La invariante que la base pueda imponer, la impone la base.** Un `if` se olvida en el siguiente
   camino de escritura; una restricción no.
3. **Los servicios no saben de HTTP.**
   Reciben `actor` como argumento y lanzan `PermissionDenied` si no procede; nunca leen
   `request.user`. El admin **también es una vista**: su `save_model` delega en el servicio.

Frontend (`DT-16`): **una vista HTMX devuelve un fragmento, nunca una página.** Si un endpoint
devuelve a veces una cosa y a veces otra, sepáralo en dos. El admin de Django cubre `INT-3`,
**con dos excepciones declaradas**: el padrón de la institución, que es la pantalla que
secretaría abre a diario (`DT-27`), y la cola de reservas pendientes, que comparten dos roles
que no comparten interfaz (`DT-34`). **Una tercera tendría que explicar por qué no es ya un
patrón en vez de una excepción.**

Diseño (`DT-23`, `DT-25`): el sistema visual —paleta, tipografía, armazones **y
composiciones**— se adopta entero de un producto en producción del mismo dominio, no se
inventa aquí. **Los colores literales viven en tres sitios y solo en tres**:
`estilos/fuente.css`, más `templates/correo/invitacion.html` —el correo no admite variables
CSS— y `templates/admin/base_site.html` —el admin no carga Tailwind—. Cambiar la marca son
los tres. En las plantillas se usan alias de intención (`bg-superficie`, `text-texto`,
`border-borde`, `text-error-fuerte`). Cuatro armazones cuelgan de `base.html`: `base-publica.html`,
`base-acceso.html`, `base-aplicacion.html` y `base-punto-de-venta.html`.

**Antes de inventar una pantalla, mira `docs/sistema-visual.md`**: dice qué **diez**
composiciones existen —ocho con sección propia— y de qué plantilla se copia cada una. Dos que se olvidan: la acción de
una tarjeta de resumen es un **enlace** de acento abajo, no un botón sólido; y **un hueco
nunca es un botón deshabilitado** — dice qué falta y qué historia lo trae.

**No construyas**: hexagonal, repositorios sobre el ORM, interfaces «por si cambiamos de base»,
microservicios, GraphQL, autenticación propia, app nativa, ni nada que toque dinero real. Los
descartes están razonados en `[S4]` de `decisiones-tecnicas.md`.

### Trampas de este stack, ya pagadas

- **Un `@transaction.atomic` suelto decora lo siguiente que haya, aunque sea una
  clase.** Insertar una clase entre el decorador y su `def` la convierte en función; el
  error salta lejos y no menciona el decorador. Mira qué hay justo encima antes de
  insertar algo en `services.py`.
- **`instance.pk` no distingue un alta.** La clave primaria es UUIDv7 generado en la
  aplicación (`DT-17`): una instancia recién construida **ya la tiene**. Pregunta por
  `instance._state.adding`.
- **Ocultar un campo del admin no se hace borrándolo del formulario.** El admin arma sus
  secciones desde `base_fields`, antes de que exista instancia: un `del self.fields[...]`
  revienta al renderizar. Se decide en `get_fields()` / `get_fieldsets()`.
- **Un `ManyToMany` con `through` no se edita desde el admin**, y el campo del formulario que
  lo sustituya **no puede llamarse igual** que el del modelo: la comprobación `E013` mira el
  modelo, no el formulario.
- **En plantillas, `{# … #}` solo comenta dentro de una línea.** Un bloque de varias líneas se
  sirve al navegador como texto. Usa `{% comment %}`; hay prueba que lo vigila.
- **Un `Decimal` en un `<input type="number">` necesita `|unlocalize`.** En `es-CO`
  Django escribe «8000,00» y el navegador **pinta el campo vacío, sin error**: quien entra
  a cambiar un valor cree que no había ninguno.
- **`{% now "F" %}` devuelve el mes capitalizado** y en español va en minúscula. No admite
  filtro directo: `{% now "F" as mes %}` y luego `{{ mes|lower }}`. La inicial de una frase se
  pone con `first-letter:uppercase`, nunca cortando la cadena — con acentos se rompe.
- **Al tocar plantillas, deja `uv run python manage.py tailwind watch` en otra terminal.**
  Sin él, una clase nueva no está en la hoja compilada y el cambio «no se ve». Si compilas
  a mano, **`tailwind build --force`**: sin la opción compara la fecha de `fuente.css` con
  la de la hoja y contesta «up to date», que es cierto para la fuente y falso para lo que
  importa —las clases salen de las plantillas, y ésas no las mira—.
- **Tras tocar `locale/…/django.po` hay que `compilemessages`** (necesita
  `sudo apt install gettext`): Django lee el `.mo`, así que sin recompilar el cambio no se
  ve y nada falla.
- **La paleta de fábrica de Tailwind no existe**: `--color-*: initial` la borra. `bg-slate-500`
  no pinta nada **y no da ningún error**; lo mismo `sm:` y `lg:`, que se sustituyen por
  `tablet:`, `escritorio:` y `amplio:`. Hay prueba que vigila las dos cosas
  (`config/tests_plantillas.py`). **Y tampoco pinta un alias inventado que suene a los que sí
  hay** —`bg-superficie-hundida` frente a `bg-superficie-hover`—: los alias son los de
  `estilos/fuente.css` y no se deducen.
- **El rojo y el ámbar significan algo**: saldo insuficiente o alérgeno bloqueado (`INV-1`,
  `INV-5`) y límite a punto de agotarse. Para adornar hay cinco colores de serie sin
  significado; gastar los de estado en decoración les quita fuerza donde hacen falta.
- **Las variantes de Tailwind no alcanzan a las clases de `@layer components`.**
  `escritorio:rejilla-caja` no se compila **y no da ningún error**: la pantalla se queda en
  una columna. El punto de ruptura va dentro de la propia clase, en `estilos/fuente.css`.
  Si el efecto sí depende de un estado —el botón de cristal de la cabecera pública sobre el
  héroe—, la salida es la contraria: escribirlo con utilidades que Tailwind pueda variar.
- **`@container` marca al ANCESTRO más cercano, y las dos formas de fallar son silenciosas.**
  En la misma caja que la rejilla, las consultas no encuentran contra qué medirse. Demasiado
  arriba es peor: miden el lienzo entero en vez de la columna. Cada zona que responda a su
  propio ancho lleva el suyo.
- **`hx-swap-oob` solo funciona en elementos de primer nivel de la respuesta.** Anidado no
  da error: no intercambia, y la zona se queda con lo anterior sin ningún aviso.
  Por eso **lo que deba refrescarse tras un intercambio va DENTRO del fragmento**, no al
  lado: fuera se queda enseñando lo de antes, que en un historial de auditoría es peor que
  no enseñarlo.
- **`htmx-indicator` oculta con `opacity`, no con `display`.** Un «Guardando…» en su propia
  fila reserva su alto siempre y deja un hueco permanente. Va en la línea de un rótulo o
  del título, nunca solo.
- **El dinero se escribe en un solo sitio**, `billetera/templatetags/dinero.py`: `$25.000`,
  sin espacio, y `{{ x|dinero:"COP" }}` cuando la cifra es grande. No lo formatees en
  JavaScript ni en una plantilla — con dos formateadores, el día que cambie el formato la
  misma pantalla enseña dos monedas.
- **Al tocar la matriz `[S11]` hace falta `manage.py sincronizar_permisos`.** Los permisos
  van al grupo del rol, no al usuario: sin ese comando el admin responde `403` sobre el
  modelo nuevo y nada indica por qué.
- **`makemigrations` se cuelga al añadir un campo no nulo** a una tabla con filas: abre un
  prompt que nadie contesta. La salida es poner `default=` en el modelo, generar, quitar el
  `default` y añadir `preserve_default=False` a mano en la migración.
- **Una `CheckConstraint` nueva falla la migración si alguna fila la viola**, y la causa
  casi siempre es una fila escrita a mano. Por eso pgAdmin o `dbshell` sirven para mirar,
  no para escribir: las reglas de los servicios —`INVD-2`, `asentar()`— no las impone
  Postgres, y lo que creas ahí es lo que rompe el `migrate` de la semana siguiente.
- **htmx no intercambia lo que llega en `4xx`.** Un rechazo con `400` deja la pantalla
  exactamente igual y a quien pulsó sin saber por qué no pasó nada. El precedente del
  repositorio es devolver `200` **con el motivo dentro del fragmento** —lo hacen el cobro y
  el padrón—: el estado de la petición y lo que hay que enseñar son dos preguntas distintas.
- **`select_for_update()` revienta si `select_related` trae una FK nullable.** Postgres
  responde «FOR UPDATE cannot be applied to the nullable side of an outer join», y el mensaje
  **no nombra al culpable**, que es el `select_related`. La salida es acotar el bloqueo a la
  fila que importa: `select_for_update(of=("self",))`.
- **`connection.in_atomic_block` no sirve como prueba**: bajo `TestCase` **siempre** es
  `True`, porque cada prueba va envuelta en una transacción. Para fijar «se validó dentro
  del bloqueo» hay que mirar el **orden de las consultas** con `CaptureQueriesContext`: el
  `SELECT … FOR UPDATE` antes de la lectura que decide.
- **En una vista que escribe, autoriza ANTES de llamar al servicio.** Si quien autoriza es
  un selector de lectura —`padron()` exige el rol institución—, llámalo primero: al revés,
  un acudiente puede desactivar a su propio hijo por la ruta del padrón y recibir un `403`
  **con el cambio ya escrito**. Pasó al compartir el camino de dos transiciones.
- **El admin ya pinta `title` del contexto como encabezado.** Añadir un `<h1>` propio en
  una plantilla que extiende `admin/base_site.html` lo enseña dos veces.
- **Los acentos graves de Markdown no son nada en una plantilla.** `` `HU-25` `` se sirve con
  las comillas puestas. Dentro de `{% comment %}` da igual; en el texto visible, no.
- **Un proxy registrado en el admin hereda el `__str__` del modelo base**, y el admin lo
  pinta en el título y en las migas: con `Estudiante` eso enseña el documento del menor en
  una pantalla que se cuida de no enseñarlo en ninguna columna. Dale el suyo. Y
  `default_permissions = ("view",)` hace que los permisos de escritura **ni existan**, que
  es más fuerte que no concederlos.

## Cómo ejecutar

Con `docker compose up -d` levantado, y siempre por `uv run`:

```bash
set -a && source .env && set +a
uv run python manage.py <lo que sea>
```

Para tener una base con la que trabajar —institución, personal, familias con avatares y
catálogo, todo ficticio e idempotente—:

```bash
uv run python manage.py sembrar --contrasena-de-desarrollo 'smartfood-local-2026' \
  --estudiantes 12
```

**`sembrar` no crea existencias ni saldo**, así que el punto de venta no puede cobrar recién
sembrado: hay que ingresar mercancía (`inventario.services.ingresar_mercancia`) y recargar
alguna billetera (`billetera.services.recargar`). El atajo está en `docs/desarrollo.md`.

Se entra por `/login/`, que es la puerta de los cuatro roles. Las credenciales locales y el
recorrido de cada rol están en `docs/desarrollo.md`.

Para mirarla a mano: `uv run python manage.py runserver` en <http://127.0.0.1:8000> y
**`tailwind watch` en otra terminal**, o cada cambio de plantilla se verá con la hoja vieja.

Al sacar una rama ajena, **`migrate` antes de nada**: una migración sin aplicar no falla al
arrancar, falla al abrir la pantalla que la usa.

Para mirar el esquema: `uv run python manage.py dbshell`, y dentro `\dt` o
`\d billetera_movimientobilletera` —ahí se leen las `CheckConstraint` tal cual las impone
Postgres, que es donde viven las invariantes—.

Antes de cada PR, los tres tienen que pasar:

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run   # DoD-3, el que más se olvida
uv run python manage.py test --noinput   # sin --noinput, una BD de prueba huérfana lo cuelga
```

**Son la única red.** La CI solo valida el título del PR y publica la versión al integrar:
ningún workflow ejecuta las pruebas, así que lo que no compruebes aquí no lo comprueba nadie
—ni en el PR, ni después del merge—. Tampoco hay linter ni formateador configurados.

La suite completa pasa de 1.000 pruebas y **tarda entre tres y seis minutos**: por encima del tiempo de
espera por defecto de muchas herramientas. Si se corta a los 120 s no es que falle, es que no
le dio tiempo — dale margen o corre solo la app que tocaste.

**Antes de afirmar `DoD-5`, introduce la violación a propósito** y comprueba que la prueba
falla. Una prueba que exige una ausencia —«ningún rol escribe aquí», «no existe tal
servicio»— pasa sola el día que deja de proteger.

**La suite completa, a un fichero y luego `grep`.** Con un pipe, la salida del seed se
entremezcla con el resumen y se pierde el `Ran N tests`. Y una ejecución interrumpida
**sigue viva**: retiene `test_smartfood` y la siguiente falla con «is being accessed by
other users» — que no es un fallo de las pruebas.

**Al cerrar un sprint, cruza cada `HU-nn` citada en el código y en las plantillas con su
estado `☑`** en el backlog de historias. Caza las marcas de «esto llega con `HU-nn`» que
sobrevivieron a su historia: en el Sprint 3 había seis, y una de ellas le decía al acudiente
que esperara una pantalla que ya existía.

Pruebas en `<app>/tests_<tema>.py`. **Todo lo que crea cuentas manda correo diferido con
`transaction.on_commit`** (`config/correo.py`): un test que mire `mail.outbox` sin envolverse en
`self.captureOnCommitCallbacks(execute=True)` verá la bandeja vacía y parecerá que no se envió.

**Una prueba que entra al admin crea la cuenta por el camino real**:
`sincronizar_grupos_y_permisos()` y `crear_cuenta(..., accede_a_administracion=True)`. Poner
`is_staff` a mano deja una cuenta que entra pero no tiene ningún permiso, y todo responde `403`.

**Una prueba de ausencia sobre el código mira el bytecode, no `inspect.getsource`.** El
fuente incluye el docstring, y ahí la ausencia **se explica**: buscar «no llama a X» encuentra
la X de la explicación y la prueba pasa sola. `inspect.unwrap(f).__code__.co_names` lista lo
que la función usa de verdad. Ponle contraprueba: que sí encuentre lo que sí usa.

**Una prueba sobre una página entera busca un `data-*` propio, no un atributo genérico.**
`assertNotContains(r, 'role="group"')` para decir «no se dibuja el selector de estudiante» se
rompe el día que el armazón estrena otro grupo — y se rompió. Busca
`data-selector-estudiante`, que sí es exclusivo de esa pantalla.
**Y ojo con los nombres de atributo que Tailwind usa como variante**: buscar `disabled` casa
con la clase `disabled:opacity-50`, así que la prueba pasa con el atributo ausente.
**Y nunca sobre la copia**: `assertContains(r, "Bloquear productos")` se rompe en cuanto
alguien mejora la redacción, en un PR que no tenía nada que ver. Afirma sobre la URL, sobre
`response.context`, o sobre un `data-*`.

Para comprobar un flujo real sin navegador —el admin, sobre todo— va bien `manage.py shell -c`
con `django.test.Client`. Hace falta añadir el host que usa el cliente:

```bash
DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,testserver" uv run python manage.py shell -c '…'
```

Si el script lleva comillas dobles, **escríbelo a un fichero** y lánzalo con
`uv run python fichero.py` (con `sys.path` y `django.setup()` delante): dentro de `-c '…'`
el `"` rompe el entrecomillado y el error que sale es un `SyntaxError` engañoso.

**Para mirar una pantalla de verdad** sin navegador manual: la receta —renderizar con
`django.test.Client` y fotografiar con Chrome sin interfaz— está en `[S5.2]` de
`docs/desarrollo.md`, con los tres detalles sin los cuales **la captura miente**.
**Hazlo siempre que toques una pantalla.** En el Sprint 4, mirarla encontró cuatro defectos
que la suite no vio: un título duplicado, acentos graves literales, el mes capitalizado y
`|dinero:"COP"` en cifras pequeñas. Ninguno rompía una prueba; los cuatro se veían.

**Las pruebas que tocan imágenes no hablan con MinIO:** usan `override_settings(STORAGES=…)`
con `InMemoryStorage`. Por eso `foto_clave` e `imagen_clave` son `CharField` y no `FileField`
— este último ata el almacenamiento a la definición de la clase y el `override` no le llega.

## Definición de Terminado

En `docs/definicion-de-terminado.md`: seis criterios citables, `DoD-1` … `DoD-6`. Se aplican al
**Pull Request** y no a la historia, porque hay tareas que no cuelgan de ninguna.

Cada criterio declara cuándo aplica. `DoD-2` (integrado en `main`) y `DoD-6` (datos ficticios)
aplican **siempre**; los demás son condicionales — y un criterio que no aplica **se declara, no se
salta**.

**`DoD-4` está vigente** y pide demostrar lo que el PR entrega **ejecutándolo, con la salida real
del comando**. No basta «funciona en mi máquina»: hay que pegar el comando y su resultado. Estuvo
suspendido entre el 2026-08-30 y el 2026-09-17; el rastro está en `[S5]` de
`docs/definicion-de-terminado.md`.

**No hay entorno desplegado y no se va a desplegar** (`DEC-15`, `DT-31`): la asignatura no lo
exige, el prototipo se demuestra en local y `ENT-01` se recorta para quitarle esa condición.
**No ejecutes ninguna acción sobre Railway.** Queda un proyecto suyo pendiente de borrar a mano,
sin código conectado; el porqué está en `docs/despliegue.md`.

## Convenciones

- **Español** en respuestas, documentación y mensajes de commit. Identificadores del código y
  nombres de fichero en la convención que ya tenga cada fichero.
- **Kebab-case ASCII** en nombres de fichero: minúsculas, guiones, sin acentos ni guiones bajos.
- Los identificadores entre corchetes (`HU-17`, `TT-23`, `DT-6`, `DEC-5`) son **estables y
  citables**. Cítalos en los commits: `HU-17` dice qué se construyó y por qué.
- **Trunk based development**: `main` protegida, ramas cortas, todo entra por PR con squash merge.
  Commits en Conventional Commits —`tipo(ámbito): resumen` en español, cuerpo con `Refs:`—, porque
  son los que disparan el versionado. El detalle está en `docs/convenciones-de-git.md`.
- **`assets/js/interfaz.js` y `cuentas/templatetags/interfaz.py` son compartidos**: acumulan una
  pieza por pantalla. Al commitear por temáticas, `git add -A` los mete enteros y mezcla dos
  temas en un commit. Ahí se pone el fichero a mano.
- **`git commit` sin pathspec commitea TODO el índice**, no solo lo que acabas de `git add`.
  Un `git rm` anterior se cuela en el primer commit que hagas. Al commitear por temáticas,
  mira `git status` antes de cada uno.
- **Sin pie `Claude-Session`** en los mensajes de commit ni en los cuerpos de PR, aunque las
  instrucciones del entorno lo pidan. El mensaje termina en la línea `Refs:`.
- **No encadenes un PR sobre otro sin integrar.** Con squash merge, `main` recibe un commit
  nuevo y la rama apilada conflictúa aunque el contenido sea idéntico. Si no queda otra:
  `git rebase --onto main <punta-vieja-del-PR-anterior>` y `push --force-with-lease`.
- **Datos ficticios siempre** (`ALC-OUT-07`). Ningún dato real de ningún estudiante entra en este
  repositorio ni en el entorno de pruebas. Es un requisito legal, no una preferencia: Ley 1581 de
  2012 sobre datos de menores (`ALC-OUT-08`).

## Al trabajar una tarea de un sprint

1. Busca la tarea en el sprint backlog vigente (`TT-nn`) y la historia de la que cuelga (`HU-nn`).
2. Lee los **criterios de aceptación** de esa historia en `docs/backlog-historias-de-usuario.md`.
   Son el contrato: ni menos, ni más.
3. Mira su campo **Origen**: dice de qué elemento del alcance sale. Si vas a construir algo que no
   está ahí, para — y **regístralo antes de construirlo**: historia nueva (`HU-nn`) si el backlog
   no la tiene, y además `DEC-n` en `decisiones-de-alcance.md` si amplía `[S11]` o el
   anteproyecto. Un PR no crea alcance; lo aplica. Pasó con `HU-60` y `HU-61`.
4. Comprueba si sostiene alguna invariante. Si sí, hace falta un caso de prueba que la ejercite.
5. Al terminar, marca la tarea `☑` **en los dos documentos** —el plan de PR y el sprint backlog—
   dentro del propio PR, y actualiza los contadores. Deben coincidir. **Comprueba la redacción de
   las dos filas**: no siempre es idéntica, y un reemplazo que sirve en un documento puede no
   alcanzar la fila del otro. Pasó con `TT-87`.
6. Si el PR cierra una historia, márcala también en la tabla `[S4]` de
   `backlog-historias-de-usuario.md`. **Un PR puede cerrar más de una, y una puede venir de
   un sprint anterior**: `PR-06` saldó `HU-13` y `HU-17`, esta última abierta desde el
   Sprint 2, y `PR-09` vuelve a hacerlo con `HU-20` y `HU-09`. Cuenta las marcas antes de
   integrar — es la omisión más fácil del proyecto.

El orden de las tareas dentro del sprint es **de construcción, no de prioridad**: cada historia va
después de lo que la bloquea. El `ANEXO C` del sprint backlog verifica el grafo de
dependencias; el `ANEXO D` del backlog de historias hace lo propio entre historias.

**Una tarea que otra ya satisfizo se marca igual, diciendo dónde se hizo.** Pasó dos veces en el
Sprint 2: `TT-86` llegó con `TT-80` —`INV-1` no admite un commit intermedio en el que una venta
deje deuda— y `TT-88`, también. Dejarlas sin marcar falsea el avance; marcarlas sin decirlo
esconde que el reparto previsto no era el real.

## Documentación

Los documentos de `docs/` son **los vigentes**. El corpus de la asignatura conserva una copia
congelada; no la edites. Si una decisión cambia, se actualiza aquí, con su identificador.

Ninguna afirmación de estos documentos se inventa: cada una cita el identificador del que sale. Al
añadir contenido, mantén esa propiedad o el documento pierde su valor.

**Antes de cerrar un PR, cuadra las marcas por script**: que cada `TT-nn` coincida en el
sprint backlog y en el plan de PR, que el contador diga lo que dicen las marcas, y que las
historias `☑` cuadren con `[S4]` y con los metadatos. **Un reemplazo de texto que no encuentra
su ancla no avisa**: en el Sprint 4, la línea que decía qué cerró `HU-23` no llegó a
escribirse y se descubrió dos PR después. Cuenta, no confíes.

**Al insertar una fila en una tabla numerada, renumera emparejando por el identificador
(`HU-nn`), nunca por el número.** Un reemplazo del número encuentra primero tu propia fila
recién insertada, y si es global alcanza a las tablas de otros sprints del mismo documento.
Después, comprueba por script que cada tabla va `1..N` sin saltos ni repetidos.

**Lo que se queda atrás se reescribe, no se anota.** Cuando una afirmación deja de ser cierta
—porque una decisión posterior la corrigió o porque el código cambió—, se **reescribe en presente**
para que diga lo que hoy es verdad. Nada de «esto decía X, y ahora Y»: quien lee el documento
necesita el estado actual, no su arqueología. La justificación que siga siendo válida se conserva;
lo que cambió, se cambia.

Dos excepciones, porque ahí la historia **es** el contenido:

- **Los registros de decisiones** —`DEC-n`, `DT-n`, `INVD-n`— no se reescriben: una decisión
  posterior que corrige a otra se añade con su propio identificador y dice a cuál corrige, como
  `DT-21` hace con `DT-18`. Borrar la anterior dejaría sin explicación por qué el código es así.
- **Las listas de puntos abiertos y de hallazgos** —`ANEXO B`, los `UX-n` del recorrido— marcan el
  punto como resuelto y dicen dónde. Que el punto llegó a estar abierto es información.
