# CLAUDE.md

Guía de trabajo para Claude Code en este repositorio.

## Qué es esto

**SmartFood**: prototipo de plataforma de gestión para cafeterías escolares con control parental y
trazabilidad digital. Proyecto de la asignatura *Proyecto Aplicado en TIC 1* (UPB, 202601).

Equipo de 4, de los cuales **2 desarrollan**. Cinco sprints de dos semanas, semanas 6 a 15.

**Los Sprints 1, 2, 3 y 4 están cerrados** —56, 37, 43 y 18 tareas, todas integradas—. El 3 fue el del control parental y **creció de 37 a 43 tareas** con `HU-60` y `HU-61`, dos huecos que la planeación no vio. El 4 fue el de inventario trazable y pedidos anticipados: cerró `TST-4` y con él **los cuatro escenarios críticos de `ENT-05`**, y retiró el entorno desplegado del alcance (`DEC-15`). Las revisiones de cierre están en `[S7]` de cada plan de PR; la del 4 encontró dos defectos y los arregló antes de cerrar.

**Estamos en el Sprint 5, el último**, semanas 14 y 15: reportes de consumo, cierre de caja y **el cierre del proyecto**. La **entrega final** (`EVA-5`, 30 % de la nota) es la semana 16.

**El producto está terminado.** Con `PR-09` quedaron cerradas **las 61 historias** del backlog —24 de las 33 tareas, 9 de los 13 PR—, y lo que falta (`PR-10` … `PR-13`) **no toca el código**: plan de pruebas, arquitectura, artefactos de gestión, informe final y cierre del sprint. **Lo que sí lo tocó, después y fuera del backlog, fue el rediseño de la navegación** (`DEC-16`, `DT-36`, `DEC-17`; PR #359 a #362) **y el correo local con la recuperación de contraseña** (`DEC-18`, `DEC-19`): la segunda trajo **`HU-62`, la historia 62**, y devolvió a `HU-03` el criterio que `DEC-9` recortó. Las dos se registraron como alcance **antes** de construirlas. Si una tarea propone tocar el producto sin un `DEC-n` detrás, sigue siendo señal de que está mal entendida.

Es el primer sprint cuyo backlog incluye tareas que no salen de ninguna historia: `ENT-05`, `ENT-06` y `ENT-07` son entregables declarados en `[S9.3]` del anteproyecto que ningún sprint había planificado. Ver `[S5]` de `./docs/sprint-5-backlog.md`.

## Antes de escribir código, lee esto

`docs/` no es documentación decorativa: es el contrato del proyecto. Orden de lectura:

| Documento | Para qué |
|---|---|
| `docs/smartfood.md` | Contexto: problema, objetivos, alcance (`S9`), solución (`S10`), matriz de permisos (`S11`), usuarios (`S5`) |
| `docs/decisiones-de-alcance.md` | Alcance acordado **después** del anteproyecto (`DEC-n`) |
| `docs/decisiones-tecnicas.md` | Arquitectura, stack y modelo de datos (`DT-n`) |
| `docs/backlog-historias-de-usuario.md` | Las historias con sus criterios de aceptación |
| `docs/sprint-5-backlog.md` | **Las 33 tareas del sprint en curso** (`TT-155` … `TT-187`), con responsable. Incluye `[S5]`, el cierre del proyecto |
| `docs/plan-de-pull-requests-sprint-5.md` | Esas 33 tareas en 13 PR y el estado de cada una —**el estado manda aquí** |
| `docs/sprint-4-backlog.md` y los anteriores, con sus planes de PR | Los sprints cerrados. Archivo, consulta histórica |
| `docs/sprint-1-backlog.md` y `docs/sprint-2-backlog.md`, con sus planes de PR | Los sprints 1 y 2, cerrados. Archivo, consulta histórica |
| `docs/definicion-de-terminado.md` | Los seis criterios de cierre (`DoD-1` … `DoD-6`) |
| `docs/despliegue.md` | **Por qué no hay entorno desplegado** (`DEC-15`), y qué costó el que hubo |
| `docs/desarrollo.md` | Reconstrucción local, credenciales y comandos del día a día |
| `docs/mapa-de-la-aplicacion.md` | Qué pantallas hay, quién alcanza cada una y el recorrido de demostración |
| `docs/sistema-visual.md` | **Qué composición copiar al construir una pantalla**, y de qué plantilla (`DT-25`) |
| `docs/reglas-de-la-venta.md` | **Qué comprueba la venta, en qué orden y por qué.** Léelo antes de añadir la séptima condición |
| `docs/reglas-del-pedido-anticipado.md` | **Qué mueve cada momento del pedido** —reservar, consultar, entregar— y las siete reglas que ninguna historia dice |
| `docs/reglas-del-cierre-de-caja.md` | **Qué entra en el cuadre de la caja y qué no**, y por qué el efectivo esperado no se digita (`INVD-5`) |
| `docs/reglas-de-frecuencia-de-consumo.md` | **Qué alerta de frecuencia se publica y con qué umbral**, y por qué el umbral es el mismo para todas las categorías (`ALC-OUT-20`) |
| `docs/valores-de-referencia-nutricional.md` | **Contra qué cifras se comparan los agregados**, con la norma que las publica y las tres salvedades declaradas (`TT-162`) |
| `docs/formato-de-carga.md` | Contrato del archivo de carga de estudiantes (`TT-22`) |
| `docs/campos-nutricionales.md` | Qué declara cada producto y por qué esos campos (`TT-44`) |
| `docs/recorrido-de-administracion-de-estudiantes.md` | Recorrido UX de la vista de estudiantes y qué cambió por él (`TT-35`) |
| `docs/prueba-de-concepto-del-lector.md` | Guion de `TT-72`: tarjetas impresas y lector físico (`ENT-02`) |
| `docs/trampas-del-stack.md` | **Las sesenta trampas que ya costaron una ronda**, por dónde muerden. Lo primero que mirar cuando algo «no se ve» o da una cifra rara |
| `docs/convenciones-de-git.md` | Ramas, convención de commits y publicación de versiones (`TT-01`) |

**El alcance vigente es `[S9.1]` de `smartfood.md` MÁS `[S1]` de `decisiones-de-alcance.md`.**
**Diez** decisiones amplían el anteproyecto (`DEC-1` … `DEC-8`, `DEC-13` y `DEC-19`) y **dos lo
recortan** (`DEC-14`, `DEC-15`); `DEC-18` devuelve lo que `DEC-9` recortó. Ninguna está
incorporada a él. Para responder qué hace o no hace el sistema
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
ejecuta en local, con un solo `docker compose up` (`DEC-15`, `DT-31`, `DT-37`). UUIDv7 como clave primaria en todas las tablas (generado en
la aplicación), **excepto el código de tarjeta**.

Una app por dominio, **y cada una se creó en el sprint que la necesitó**. Con `reportes`
(`TT-155`) están **las ocho** y no queda ninguna por crear: `cuentas`, `personas`,
`catalogo`, `billetera`, `inventario`, `ventas`, `restricciones` —esta no la previó `DT-15`
y la declara `DT-28`— y `reportes`, que entra **sin modelos y sin migraciones** porque un
reporte es una lectura de hechos que otro dominio ya asentó.
Dentro de cada una:

| Archivo | Responsabilidad |
|---|---|
| `models.py` | Estructura e invariantes de datos (`CheckConstraint`, `UniqueConstraint`). Sin lógica de negocio |
| `services.py` | **Toda escritura.** Funciones, no clases; cada una abre su `transaction.atomic()` |
| `selectors.py` | **Toda lectura** no trivial. No conocen `request` |
| `views.py` | HTTP: parsear, delegar, renderizar. **Cero lógica de negocio** |

**No todo cabe en esos cuatro.** La lógica pura —sin base y sin HTTP— vive en su propio
módulo al lado: `personas/codigo.py`, `personas/validacion.py`, `ventas/carrito.py`,
`reportes/reglas.py` y `reportes/referencia.py`. Es lo que permite comprobar un umbral o una
tabla de referencia **sin sembrar catorce días de ventas**, y leer la regla entera de un
vistazo cuando alguien pregunte por qué avisó.

Tres reglas (`DT-15`):

1. **Una vista nunca escribe directamente**: llama a un servicio.
2. **La invariante que la base pueda imponer, la impone la base.** Un `if` se olvida en el siguiente
   camino de escritura; una restricción no.
3. **Los servicios no saben de HTTP.**
   Reciben `actor` como argumento y lanzan `PermissionDenied` si no procede; nunca leen
   `request.user`. El admin **también es una vista**: su `save_model` delega en el servicio.

Frontend (`DT-16`): **una vista HTMX devuelve un fragmento, nunca una página.** Si un endpoint
devuelve a veces una cosa y a veces otra, sepáralo en dos. El admin de Django cubre `INT-3`,
**con cuatro pantallas propias fuera de él**: el padrón de la institución, que es la que
secretaría abre a diario (`DT-27`), la cola de reservas pendientes, que comparten dos roles
que no comparten interfaz (`DT-34`), y —desde `DEC-17`— los acudientes y las restricciones.
**`DEC-17` puso la raya que antes faltaba**: una pantalla propia sustituye a una del admin
solo cuando alguien la usa a diario; el resto se queda envuelto (`DT-36`).

**Los reportes de la cafetería no son una tercera excepción**: los cuatro viven dentro del
admin, por el camino que `TT-141` abrió para el historial de existencias y repiten `TT-168`
(ventas), `TT-170` (inventario) y `TT-176` (cierres de caja) — el admin pone listado, filtros
y fechas, y lo que se añade es el consolidado **del listado que se está mirando**, calculado
sobre el mismo `QuerySet` que pinta la tabla.

**Dos no tienen modelo, y por eso son las únicas con ruta propia**: la auditoría
(`TT-178`), que cruza cuatro tablas, y el panel de la cafetería (`DEC-16`), donde aterriza
`USR-4`. Las dos van registradas en `config/urls.py` **antes** de `admin.site.urls` —Django
resuelve en orden— y usan el armazón del admin, así que no son excepciones a `DT-2`: las
excepciones son las que viven *fuera* de él.

Diseño (`DT-23`, `DT-25`): el sistema visual —paleta, tipografía, armazones **y
composiciones**— se adopta entero de un producto en producción del mismo dominio, no se
inventa aquí. **Los colores literales viven en dos sitios y solo en dos**: `estilos/tokens.css`
—la paleta y los temas, que comparten las **dos** hojas: la de la aplicación y la del admin
(`DT-36`)— y `templates/correo/base.html`, la cáscara de los correos, que no admiten variables CSS.
`templates/admin/base_site.html` **ya no es el tercero**: el admin carga `estilos/admin.css`,
que es Tailwind sin `preflight`, y toma los tokens como todo lo demás. En las plantillas se usan alias de intención (`bg-superficie`, `text-texto`,
`border-borde`, `text-error-fuerte`). Cuatro armazones cuelgan de `base.html`: `base-publica.html`,
`base-acceso.html`, `base-aplicacion.html` y `base-punto-de-venta.html`.

**Antes de inventar una pantalla, mira `docs/sistema-visual.md`**: dice qué **doce**
composiciones existen —diez con sección propia— y de qué plantilla se copia cada una. Tres que
se olvidan: la acción de una tarjeta de resumen es un **enlace** de acento abajo, no un botón
sólido; **un hueco nunca es un botón deshabilitado** —dice qué falta y qué historia lo trae—;
y un medidor **recorta la barra a 100, nunca el número**.

**No construyas**: hexagonal, repositorios sobre el ORM, interfaces «por si cambiamos de base»,
microservicios, GraphQL, autenticación propia, app nativa, ni nada que toque dinero real. Los
descartes están razonados en `[S4]` de `decisiones-tecnicas.md`.

### Las cinco trampas que se tropiezan a diario

**Las sesenta están en `docs/trampas-del-stack.md`**, agrupadas por dónde muerden:
plantillas y estilos, el admin, el ORM, pruebas y capturas, y contenedores. Casi todas **fallan en
silencio** —no dan error y lo que sale es plausible—, así que cuando algo «no se ve», «sale
raro» o «da una cifra rara», ese documento es el primer sitio donde mirar.

Aquí se quedan las cinco que alcanzan a casi cualquier tarea:

- **La paleta de fábrica de Tailwind no existe**: `--color-*: initial` la borra.
  `bg-slate-500` no pinta nada **y no da ningún error**; lo mismo `sm:` y `lg:`, que se
  sustituyen por `tablet:`, `escritorio:` y `amplio:`. **Y tampoco pinta un alias inventado
  que suene a los que sí hay** —`bg-superficie-hundida` frente a `bg-superficie-hover`—: los
  alias son los de `estilos/tokens.css` y no se deducen. Hay prueba que vigila las dos
  primeras cosas (`config/tests_plantillas.py`).
- **En plantillas, `{# … #}` solo comenta dentro de una línea.** Un bloque de varias líneas
  se sirve al navegador como texto. Usa `{% comment %}`; hay prueba que lo vigila.
- **Un `order_by()` explícito entra en el `GROUP BY` de un `values().annotate()`**, y el
  `ordering` del `Meta` ya no (Django lo dejó de hacer en 3.1). Una fila por venta, todas con
  un uno, **y el total de al lado correcto**: no se ve en las pruebas ni en el código. Limpia
  con `.order_by()` antes de agrupar. Su gemela —lo anotado **antes** de un `values()`
  también entra— y las demás de agregación están en `[S3]` del documento.
- **El dinero se escribe en un solo sitio**, `billetera/templatetags/dinero.py`: `$25.000`,
  sin espacio, y `{{ x|dinero:"COP" }}` cuando la cifra es grande. No lo formatees en
  JavaScript ni en una plantilla — con dos formateadores, el día que cambie el formato la
  misma pantalla enseña dos monedas.
- **Si el cambio «no se ve», casi siempre es que no se compiló.** Con el compose, el servicio
  `estilos` recompila las dos hojas solo: si no lo hace, `docker compose logs estilos`. Sin
  él, deja `uv run python manage.py tailwind watch` en otra terminal; a mano, **`tailwind build
  --force`** (sin la opción contesta «up to date», que es falso para lo que importa). Si la
  plantilla es del admin, el comando es otro: **`manage.py estilos_del_admin`** —son dos
  hojas (`DT-36`)— y después `collectstatic`. **El `watch` muere en cuanto su stdin no es una
  terminal**, sin decirlo: el detalle y la salida están en `[S1]` del documento.

## Cómo ejecutar

**Todo el stack con un comando**, desde un clon limpio y sin `.env` (`DT-37`):

```bash
docker compose up -d
```

Levanta PostgreSQL, SeaweedFS con su bucket (`DT-38`), Mailpit (`DEC-18`), la aplicación en <http://localhost:8000> y el
servicio `estilos`, que compila las dos hojas y se queda vigilando las plantillas. El
arranque de la aplicación migra, sincroniza los permisos, **siembra** —con
`smartfood-local-2026` y 12 estudiantes— y recopila los estáticos. El código va montado:
guardar recarga, y no hay que reconstruir nada salvo que cambien las dependencias, cosa que
el propio `up` hace.

Un comando de Django, dentro del contenedor o en el host —los dos valen—:

```bash
docker compose exec app python manage.py <lo que sea>

set -a && source .env && set +a            # en el host: infraestructura del compose,
uv run python manage.py <lo que sea>       # aplicación con uv (`[S1.0.2]` de desarrollo.md)
```

**No arranques un `runserver` en el host con `app` levantado**: se pelean por el puerto 8000.
**El correo no sale de la máquina**: lo atrapa Mailpit y se lee en <http://localhost:8025>
(`DEC-18`) —invitaciones, carga masiva y recuperación de contraseña—.

**`sembrar` no crea existencias ni saldo**, así que el punto de venta no puede cobrar recién
sembrado: hay que ingresar mercancía (`inventario.services.ingresar_mercancia`) y recargar
alguna billetera (`billetera.services.recargar`). El atajo está en `docs/desarrollo.md`.

Se entra por `/login/`, que es la puerta de los cuatro roles. Las credenciales locales y el
recorrido de cada rol están en `docs/desarrollo.md`.

Al sacar una rama ajena, **`migrate` antes de nada**: una migración sin aplicar no falla al
arrancar, falla al abrir la pantalla que la usa. Con el compose basta `docker compose up -d`
—o `restart app`—, que migra al arrancar.

### El compose vive al día

**`docker compose up` tiene que levantar el stack en cualquier máquina, siempre.** Es la
condición de que el prototipo se pueda demostrar (`DEC-15`), y se rompe sin tocar
`compose.yaml`: basta cambiar otra cosa y no acordarse de él.

**Un PR que cambie la infraestructura actualiza en el mismo PR** `compose.yaml`, el
`Dockerfile` o los scripts de `docker/`. Cuenta como infraestructura —la tabla completa está
en `[S5.3]` de `docs/desarrollo.md`—:

- una variable que `config/settings.py` lee **sin `default=`**;
- una dependencia que necesita una librería del sistema, o un cambio de versión de Python,
  uv o Tailwind;
- un paso que haya que dar antes de servir, o un comando que el arranque llama y cambia de
  nombre u opciones;
- un servicio nuevo, o una hoja de estilos nueva.

**Y lo comprueba levantando desde cero**, con otro nombre de proyecto para no tocar la base
de trabajo: la receta está en `[S5.3]` de `docs/desarrollo.md`. «Me levanta a mí» no vale: a
ti te levanta con tus volúmenes, tu imagen y tu `.env`.

Dos comprobaciones lo sostienen, y son lo que de verdad cuenta —una regla se olvida en el
siguiente PR—: **`config/tests_contenedor.py`** en la suite, y **el flujo
`integracion-continua`** de la CI, que levanta el stack desde cero en cada PR. **Un PR con
ese flujo en rojo no se integra**, aunque el cambio «no tenga nada que ver»: si no levanta en
la CI, no levanta en la máquina del siguiente.

Para mirar el esquema: `uv run python manage.py dbshell`, y dentro `\dt` o
`\d billetera_movimientobilletera` —ahí se leen las `CheckConstraint` tal cual las impone
Postgres, que es donde viven las invariantes—.

Antes de cada PR, los tres tienen que pasar:

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run   # DoD-3, el que más se olvida
uv run python manage.py test --noinput   # sin --noinput, una BD de prueba huérfana lo cuelga
```

Con el compose, lo mismo con `docker compose exec app python manage.py …`. **En un clon
recién hecho, en el host, la suite necesita antes un `collectstatic`**: el ejecutor fuerza
`DEBUG=False` y sin manifiesto salen 285 errores (`[S4]` de `docs/trampas-del-stack.md`). El
arranque del contenedor ya lo hace.

**La CI corre los tres en cada PR y en cada push a `main`**, dentro del stack de
`docker compose` levantado desde cero (`integracion-continua.yml`), y **la versión solo se
publica si pasan** (`[S3.0]` de `docs/convenciones-de-git.md`). Córrelos igual antes de
subir: la CI tarda más de diez minutos en decirte lo que aquí sabes en cinco. La suite no se
enumera en ninguna parte —una prueba nueva entra sola—, siempre que el fichero se llame
`tests_<tema>.py` y su carpeta tenga `__init__.py`: si no, **no se ejecuta nunca y nada
avisa**, salvo `config/tests_descubrimiento.py`. Tampoco hay linter ni formateador configurados.

La suite completa son **1.572 pruebas** y **tarda entre tres y seis minutos**: por encima del tiempo
de espera por defecto de muchas herramientas. Si se corta a los 120 s no es que falle, es que no
le dio tiempo — dale margen o corre solo la app que tocaste. Y si el resumen dice bastantes
menos de esas 1.572, no corrió entera.

**Antes de afirmar `DoD-5`, introduce la violación a propósito** y comprueba que la prueba
falla. Una prueba que exige una ausencia —«ningún rol escribe aquí», «no existe tal
servicio»— pasa sola el día que deja de proteger.

**La salida de la suite son nueve líneas**, y leerla en la terminal basta: `sembrar` respeta
`verbosity` desde `#359`. Mandarla a un fichero sigue siendo cómodo para revisarla con
calma, pero ya no es obligatorio para encontrar el `Ran N tests`.

Lo que no cambió: una ejecución interrumpida **sigue viva** y retiene `test_smartfood`, así
que la siguiente falla con «is being accessed by other users» — que no es un fallo de las
pruebas.

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

**Una prueba de ventana o de periodo recibe la fecha, no la lee del reloj.** El selector
toma `hoy=` y las filas se fechan a mano sobre una jornada fija: si mira `timezone.now()`,
falla sola una madrugada y nadie sabe por qué. Y `creado_en` es `auto_now_add` —no se puede
fijar al crear—: se corrige después con `update()`.

**Para fijar «no hay forma de pintar A sin B», renderiza el FRAGMENTO, no la página.**
`render_to_string` sobre el `partial`, con y sin datos. Si alguien separa los dos bloques en
dos plantillas, la página seguiría trayendo los dos y la prueba pasaría igual — así es como
se sostiene `INV-9`, y así falla cuando se rompe.

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

**Y `response.context` es `None` fuera del runner de pruebas.** La puebla la señal
`template_rendered`, que solo se conecta con `django.test.utils.setup_test_environment()`.
Sin esa llamada la respuesta llega con `200`, y leerla revienta con un
`TypeError: 'NoneType' object is not subscriptable` que no menciona la causa.

**Para mirar una pantalla de verdad** sin navegador manual: la receta —renderizar con
`django.test.Client` y fotografiar con Chrome sin interfaz— está en `[S5.2]` de
`docs/desarrollo.md`, con los tres detalles sin los cuales **la captura miente**.
**Hazlo siempre que toques una pantalla.** En el Sprint 4, mirarla encontró cuatro defectos
que la suite no vio: un título duplicado, acentos graves literales, el mes capitalizado y
`|dinero:"COP"` en cifras pequeñas. Ninguno rompía una prueba; los cuatro se veían.

En el Sprint 5 lleva **once**, y **dos eran de cifras**: un desglose que decía «1 venta» en cada
fila con catorce en la tabla —con el total de al lado correcto— y cuatro columnas de dinero
crudas, «31500,00», junto a una ya formateada. Los otros nueve: columnas tituladas «method», el
documento de un menor en una ficha, **el correo de un cajero en la barra de filtros**, dos
cabeceras pegadas, unas migas montadas sobre la barra lateral, una barra de color que se leía
como una alarma, un «consúltalas con quien **lo** atiende» que nombraba en masculino a una
estudiante, y dos rechazos por rol que citaban otra historia. **Ninguno rompía una prueba.**

**Las pruebas que tocan imágenes no hablan con el almacenamiento:** usan `override_settings(STORAGES=…)`
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
- **Varias ramas que insertan en el MISMO punto de una lista de este fichero conflictúan en
  el segundo merge**, aunque el contenido sea compatible: git no puede decidir el orden. La
  lista de trampas no lo tiene, así que basta con que cada rama ancle tras una entrada
  distinta. Se comprueba antes de subir, mergeando las ramas en una temporal.
- **El conteo de pruebas se actualiza en el ÚLTIMO PR de la tanda.** Puesto en cada uno es la
  misma línea cambiada en todos: conflicto seguro.
- Al repartir por temáticas, los ficheros que **toca casi cualquier PR** y hay que despiezar a
  mano son `config/urls.py`, `cuentas/templatetags/interfaz.py`, `assets/js/interfaz.js`,
  `docs/decisiones-de-alcance.md` y este.
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
   **Escribir un `.md` que registra cómo funciona algo no es alcance nuevo**: es parte de
   construirlo, y varias tareas del proyecto son exactamente eso (`TT-44`, `TT-158`, `TT-162`).
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

**Una cifra que viene de una norma externa se lee en la norma, y en dos fuentes oficiales
independientes.** Se cita norma, artículo, tabla y columna —`TT-162` lo hizo con la
Resolución 810 de 2021—, **lo que no se pudo confirmar se declara** en vez de suponerse, y
los valores viven en un solo sitio del código para que actualizarlos sea una tabla y una
prueba. No se cita una norma que no se ha leído.

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
