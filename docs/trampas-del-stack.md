# SmartFood — Trampas de este stack, ya pagadas

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-TRAMPAS |
| titulo | Lo que falla en silencio en Django, Tailwind, HTMX, el admin y los contenedores |
| tipo_documento | Documento derivado. Registro de diagnósticos ya pagados |
| documentos_fuente | La sección «Trampas de este stack» de `../CLAUDE.md`, de donde sale |
| responsable | Pedro (desarrollo) |
| idioma | es-CO |
| version | 1.1 |

**Una trampa entra aquí si costó una ronda de diagnóstico.** Casi todas fallan en
silencio: no dan error y lo que sale es plausible. Lo que revienta con un mensaje claro no
necesita línea — lo dice el error.

**Este documento salió de `CLAUDE.md`** cuando la sección llegó a 223 líneas: son ~4.000
tokens que se cargaban en cada sesión. Allí quedan **las cinco que se tropiezan a diario**
y un puntero a este fichero. El resto está aquí, agrupado por dónde muerde.

> **Ojo con esta separación.** Una trampa que no está en el prompt no se evita sola: hay
> que acordarse de venir a leerla. Si una de estas vuelve a costar una ronda, el sitio
> donde debe estar es `CLAUDE.md`, no aquí.

---

## [S1] Plantillas, estilos y HTMX


- **En plantillas, `{# … #}` solo comenta dentro de una línea.** Un bloque de varias líneas se
  sirve al navegador como texto. Usa `{% comment %}`; hay prueba que lo vigila.
- **Un `Decimal` en un `<input type="number">` necesita `|unlocalize`.** En `es-CO`
  Django escribe «8000,00» y el navegador **pinta el campo vacío, sin error**: quien entra
  a cambiar un valor cree que no había ninguno.
- **El mes ya llega en minúscula, y eso lo sostiene un parche.** Django traduce los doce
  meses capitalizados en su catálogo `es_CO` —el que manda con `LANGUAGE_CODE = "es-co"`—, y
  `locale/es_CO/` los corrige. Por eso `{{ x|date:"F" }}` y `{% now "F" %}` responden
  «septiembre» y no «Septiembre». El `|lower` de las plantillas **se conserva** a propósito:
  ese parche está pensado para borrarse cuando Django lo arregle, y las fechas del producto
  no deben depender de él. La inicial de una frase se pone con `first-letter:uppercase`,
  nunca cortando la cadena — con acentos se rompe.
- **`tailwind watch` muere en cuanto su stdin no es una terminal**, y no lo dice: arranca,
  escribe «Stopped watching for changes» y deja de compilar **con el proceso aún vivo**. Pasa
  al lanzarlo desde un agente, desde un script o con la salida redirigida — en una terminal
  normal no se ve nunca. La salida es darle un stdin que no se cierre:

  ```bash
  tail -f /dev/null | ./.tailwind/tailwindcss-linux-x64-4.3.3 \
    -i estilos/fuente.css -o assets/css/tailwind.css --watch
  ```

  Dos detalles del modo `--watch` que confunden el diagnóstico: **no reescribe la hoja si el
  CSS resultante no cambia** —un comentario nuevo no la toca, así que mirar la fecha del
  fichero no prueba nada— y **no purga las clases que dejan de usarse** dentro de una misma
  sesión. Para lo segundo, `tailwind build --force`.
- **Al tocar plantillas, deja `uv run python manage.py tailwind watch` en otra terminal.**
  Sin él, una clase nueva no está en la hoja compilada y el cambio «no se ve». Si compilas
  a mano, **`tailwind build --force`**: sin la opción compara la fecha de `fuente.css` con
  la de la hoja y contesta «up to date», que es cierto para la fuente y falso para lo que
  importa —las clases salen de las plantillas, y ésas no las mira—.
- **Tras tocar `locale/…/django.po` hay que `compilemessages`** (necesita
  `sudo apt install gettext`): Django lee el `.mo`, así que sin recompilar el cambio no se
  ve y nada falla. **Son dos catálogos y no se eligen al azar**: `locale/es/` parchea lo que
  Django deja sin traducir, y `locale/es_CO/` corrige lo que traduce mal. Una corrección
  escrita en `es` no gana — con `LANGUAGE_CODE = "es-co"` el catálogo que manda es el
  `es_CO` y el `es` solo es la reserva, así que la pisa el de Django.
- **La paleta de fábrica de Tailwind no existe**: `--color-*: initial` la borra. `bg-slate-500`
  no pinta nada **y no da ningún error**; lo mismo `sm:` y `lg:`, que se sustituyen por
  `tablet:`, `escritorio:` y `amplio:`. Hay prueba que vigila las dos cosas
  (`config/tests_plantillas.py`). **Y tampoco pinta un alias inventado que suene a los que sí
  hay** —`bg-superficie-hundida` frente a `bg-superficie-hover`—: los alias son los de
  `estilos/tokens.css` y no se deducen.
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
- **El cliente de pruebas de Django no aplica CSRF, así que un `hx-post` sin token pasa todas
  las pruebas y falla solo en el navegador.** El catálogo del punto de venta estuvo así hasta
  el 2026-09-21: sus botones llevan `hx-post` y no cuelgan de ningún `<form>` —de donde HTMX
  saca el token—, así que añadir un producto respondía `403` con la suite entera en verde.
  El token va en `hx-headers` del `<body>` de `base.html` —el único `<body>` del proyecto, del
  que heredan los cuatro armazones—, y cubre cualquier `hx-post` presente o futuro sin
  envolverlo en un formulario. Lo vigila `ventas/tests_csrf.py` con
  `Client(enforce_csrf_checks=True)`: **con el cliente de siempre no hay prueba posible**, y
  es justo por lo que esto vivió medio proyecto. Sus seis casos cubren las tres mitades —la
  pantalla entrega el token, la petición no pasa sin él, y el catálogo sigue sin `<form>`—,
  porque comprobar solo la última dejaría el atributo sin vigilancia.
- **Una ruta que devuelve un fragmento no se abre a mano.** `/mis-estudiantes/<id>/` y las de
  `…/tabla/` responden un trozo de HTML sin `<head>`: abiertas directamente salen **sin
  estilos** —`document.styleSheets.length` es 0— y parece que Tailwind está roto. No lo está:
  hay que llegar a ellas por el clic que las pide. Cuenta al tomar capturas y al probar a mano.
- **`htmx-indicator` oculta con `opacity`, no con `display`.** Un «Guardando…» en su propia
  fila reserva su alto siempre y deja un hueco permanente. Va en la línea de un rótulo o
  del título, nunca solo.
- **El dinero se escribe en un solo sitio**, `billetera/templatetags/dinero.py`: `$25.000`,
  sin espacio, y `{{ x|dinero:"COP" }}` cuando la cifra es grande. No lo formatees en
  JavaScript ni en una plantilla — con dos formateadores, el día que cambie el formato la
  misma pantalla enseña dos monedas.
- **htmx no intercambia lo que llega en `4xx`.** Un rechazo con `400` deja la pantalla
  exactamente igual y a quien pulsó sin saber por qué no pasó nada. El precedente del
  repositorio es devolver `200` **con el motivo dentro del fragmento** —lo hacen el cobro y
  el padrón—: el estado de la petición y lo que hay que enseñar son dos preguntas distintas.
- **Los acentos graves de Markdown no son nada en una plantilla.** `` `HU-25` `` se sirve con
  las comillas puestas. Dentro de `{% comment %}` da igual; en el texto visible, no.

---

## [S2] El admin de Django

Las de `DT-36` —envolver el admin sin reescribirlo— van aquí: son de CSS y de plantillas,
pero solo muerden dentro del admin.


- **Ocultar un campo del admin no se hace borrándolo del formulario.** El admin arma sus
  secciones desde `base_fields`, antes de que exista instancia: un `del self.fields[...]`
  revienta al renderizar. Se decide en `get_fields()` / `get_fieldsets()`.
- **Un `ManyToMany` con `through` no se edita desde el admin**, y el campo del formulario que
  lo sustituya **no puede llamarse igual** que el del modelo: la comprobación `E013` mira el
  modelo, no el formulario.
- **Un campo de relación en el admin se pinta con el `__str__` del modelo apuntado.**
  `Estudiante.__str__` es «Nombre (documento)», así que una ficha que liste `estudiante`
  enseña el documento del menor aunque el listado se cuide de no hacerlo — y enlazado.
  Declara `fields` con un método propio que diga solo el nombre. Pasó en `TT-168`.
  **Y `list_filter` es la otra puerta, que no se arregla con la primera**: un
  `list_filter = ["cajero"]` pinta el `__str__` de cada uno en la barra lateral — el correo,
  con `Usuario` — por mucho que la columna diga el nombre. Ahí hace falta un
  `SimpleListFilter` propio. Pasó en `TT-176`.
- **En el admin, una columna de dinero sin `dinero` sale cruda.** El admin pinta un
  `DecimalField` tal cual —«31500,00»— y al lado una columna calculada sale «$31.500»: **dos
  formatos en la misma fila**, que es justo lo que el filtro existe para evitar. No falla y
  se ve bien hasta que se miran las dos juntas. Declara un método por cifra. Pasó en
  `TT-176`, y antes en `LineaVentaInline`.
- **Al tocar la matriz `[S11]` hace falta `manage.py sincronizar_permisos`.** Los permisos
  van al grupo del rol, no al usuario: sin ese comando el admin responde `403` sobre el
  modelo nuevo y nada indica por qué.
- **El admin ya pinta `title` del contexto como encabezado.** Añadir un `<h1>` propio en
  una plantilla que extiende `admin/base_site.html` lo enseña dos veces.
- **Las migas del admin son `<ol><li>`, no un `<div>`.** Django 6 las pinta así y su hoja
  estiliza **la lista**: un `{% block breadcrumbs %}` con `<div class="breadcrumbs">` deja el
  rótulo pegado al borde izquierdo, montado sobre la barra lateral, **sin ningún error**. Se
  vio comparando dos capturas (`TT-178`).
- **Un proxy registrado en el admin hereda el `__str__` del modelo base**, y el admin lo
  pinta en el título y en las migas: con `Estudiante` eso enseña el documento del menor en
  una pantalla que se cuida de no enseñarlo en ninguna columna. Dale el suyo. Y
  `default_permissions = ("view",)` hace que los permisos de escritura **ni existan**, que
  es más fuerte que no concederlos.
- **Una regla sin capa gana a cualquiera dentro de un `@layer`, venga después o no.**
  El admin trae `.hidden { display: none !important }` en `admin/css/base.css` sin capa, así
  que con las utilidades en `@layer utilities` la barra lateral salía con su degradado, su
  `z-index` y `display: none`. Por eso `estilos/admin.css` importa `utilities` **fuera de
  capa**, y por eso el armazón del admin usa `max-tablet:hidden` en vez de `hidden`: esquiva
  el nombre en lugar de pelear por especificidad (`DT-36`).
- **El admin pinta TODO `a` con `--link-fg`, y eso alcanza al armazón metido dentro.**
  No es solo el subrayado: es el color. En la barra lateral —oscura en los dos temas— las
  entradas salían en el azul oscuro de enlace y **desaparecían en tema claro**; en oscuro
  coincidían por casualidad, así que el defecto solo existía en la mitad de los casos. El
  color del armazón se declara por token con la misma especificidad alta que el subrayado.
- **Sustituir `{% block header %}` del admin se lleva por delante `usertools`**, y ahí vive
  su conmutador de tema. La pantalla sale bien y se queda clavada en lo que diga el sistema
  operativo, sin forma de cambiarlo. Lo cubre el selector de la aplicación, que desde
  `DEC-16` escribe **los dos idiomas del tema**: `data-tema` en español para los tokens y
  `data-theme` (`light`/`dark`/`auto`) más `localStorage.theme` para el cromo del admin. Con
  uno solo, la barra se quedaba en un tema y el listado en el otro.
- **La especificidad de un `:not()` es la de su argumento más específico.** El admin subraya
  con `a:not(…, #content-main.app-list a, …)`, que pesa (1,1,2): `.armazon a` y hasta
  `#container .armazon a` pierden. La regla se escribe, se compila, se sirve **y no hace
  nada**. Se vio preguntándole al navegador por `getComputedStyle`, no leyendo el CSS.
- **`formulario.action` en JavaScript no devuelve cadena vacía cuando el atributo falta**:
  devuelve la URL del documento. El formulario del admin no lleva `action`, así que guardar
  desde la modal hacía `POST` al listado, que responde `200` con la tabla, y la modal se
  llenaba con el listado dentro de sí misma. Se lee `getAttribute("action")`.
- **Lo que una plantilla hija escribe fuera de un `{% block %}` no se renderiza.** Django lo
  descarta sin avisar: el `<dialog>` de la modal estaba en `admin/base_site.html`, se veía en
  el fichero, y `document.querySelector` no lo encontraba nunca.
- **Tras tocar plantillas del admin hay que `manage.py estilos_del_admin`**, no
  `tailwind build`: son dos hojas y aquel solo conoce la de `TAILWIND_CLI_SRC_CSS` (`DT-36`).
  Y después, `collectstatic`, o se sirve la anterior.

---

## [S3] ORM, consultas y transacciones

Las que mienten con cifras bien formadas. Ninguna falla: todas responden algo.


- **Un `@transaction.atomic` suelto decora lo siguiente que haya, aunque sea una
  clase.** Insertar una clase entre el decorador y su `def` la convierte en función; el
  error salta lejos y no menciona el decorador. Mira qué hay justo encima antes de
  insertar algo en `services.py`.
- **`instance.pk` no distingue un alta.** La clave primaria es UUIDv7 generado en la
  aplicación (`DT-17`): una instancia recién construida **ya la tiene**. Pregunta por
  `instance._state.adding`.
- **Un `order_by()` explícito entra en el `GROUP BY` de un `values().annotate()`**, y el
  `ordering` del `Meta` ya no (Django lo dejó de hacer en 3.1). El admin **siempre** ordena
  el listado explícitamente, así que un desglose calculado sobre `cl.queryset` se agrupa
  además por la fecha: una fila por venta, todas con un uno. **El total de al lado sigue
  bien** —`aggregate()` no arrastra el orden—, así que no se ve en las pruebas ni en el
  código: se vio en la captura, con catorce ventas en la tabla y tres desgloses de una.
  Limpia con `.order_by()` antes de agrupar.
- **Lo que se anota ANTES de un `values()` también entra en el `GROUP BY`.** Es la otra
  cara de lo anterior: `annotate(dia=…).values("categoria").annotate(Count(…))` agrupa por
  categoría **y por día** —una fila por día, todas con un uno—. `alias()` deja filtrar por
  la expresión sin seleccionarla, que es lo que hay que usar. **Y si lo que agrupa no es una
  columna** —«cuadró, sobró o faltó» es el signo de una resta—, la salida es contar con
  `Count(Case(When(…)))` en un solo `aggregate()`: sin `values()` no hay `GROUP BY` que envenenar.
- **Si una regla tiene que existir en Python y en SQL, hay prueba que las compara.**
  `CierreDeCaja.diferencia` resta una fila y `DIFERENCIA_DEL_CIERRE` resta el listado entero para
  ordenar y agregar: ahí `DT-19` no tiene salida —sumar en Python obligaría a traerse todos los
  cierres—, así que lo que se fija es que las dos dicen lo mismo. Sin eso, el listado ordena por
  una cifra y enseña otra, **las dos bien formadas**.
- **`aggregate()` rechaza un nombre que choque con un campo del modelo** («The annotation
  conflicts with a field»). Prefija: `total_energia_kcal`.
- **Un `Count` sobre un `QuerySet` que une con una tabla hija necesita `distinct=True`.**
  Sumar importes obliga a unir con las líneas, y sin él una venta de tres renglones cuenta
  como tres **con las cifras de dinero intactas**: solo miente el recuento.
- **`makemigrations` se cuelga al añadir un campo no nulo** a una tabla con filas: abre un
  prompt que nadie contesta. La salida es poner `default=` en el modelo, generar, quitar el
  `default` y añadir `preserve_default=False` a mano en la migración.
- **Una `CheckConstraint` nueva falla la migración si alguna fila la viola**, y la causa
  casi siempre es una fila escrita a mano. Por eso pgAdmin o `dbshell` sirven para mirar,
  no para escribir: las reglas de los servicios —`INVD-2`, `asentar()`— no las impone
  Postgres, y lo que creas ahí es lo que rompe el `migrate` de la semana siguiente.
- **`select_for_update()` revienta si `select_related` trae una FK nullable.** Postgres
  responde «FOR UPDATE cannot be applied to the nullable side of an outer join», y el mensaje
  **no nombra al culpable**, que es el `select_related`. La salida es acotar el bloqueo a la
  fila que importa: `select_for_update(of=("self",))`.
- **En una vista que escribe, autoriza ANTES de llamar al servicio.** Si quien autoriza es
  un selector de lectura —`padron()` exige el rol institución—, llámalo primero: al revés,
  un acudiente puede desactivar a su propio hijo por la ruta del padrón y recibir un `403`
  **con el cambio ya escrito**. Pasó al compartir el camino de dos transiciones.

---

## [S4] Pruebas, capturas y diagnóstico

Cómo mirar sin que lo que se mira engañe.


- **Chrome sin interfaz fotografía SIEMPRE en tema oscuro**, y hay defectos que solo existen
  en uno de los dos: el color de las entradas de la barra dentro del admin se veía bien en
  oscuro y **desaparecía en claro**, así que media docena de capturas no lo enseñaron. Para
  el otro tema hace falta Playwright con `color_scheme="light"`.
- **Con `file://` no se prueba nada que haga `fetch`**: ni una modal, ni un intercambio de
  HTMX, ni nada que pida al servidor. Esa receta sirve para **mirar** una pantalla, no para
  ejercitarla; para eso, Playwright contra `localhost` con sesión iniciada (`[S3.1]` de
  `docs/desarrollo.md`).
- **Si una regla CSS «no hace nada», pregúntale al navegador en vez de leer el CSS.** Un
  script que escriba `getComputedStyle(...)` en `document.title`, leído con `--dump-dom`, da
  la respuesta en un intento; leer la hoja compilada costó tres rondas y dos hipótesis falsas.
- **`self.style` de un comando colorea según el tty del PROCESO, no según el `stdout=` que
  recibe.** Django mira `sys.stdout.isatty()`, así que una prueba que pasa un `StringIO` y
  parsea la salida recibe códigos ANSI cuando la suite se corre a mano en la terminal, y
  ninguno cuando se redirige a un fichero: `startswith("contraseña")` deja de casar y la
  prueba **solo falla de forma interactiva**. Pásale `no_color=True` a `call_command`. Pasó
  con la línea de la contraseña de `sembrar`.
- **Un comando que no lee `verbosity` no calla aunque se lo pidan.** `BaseCommand` recibe la
  opción pero no la aplica: `self.stdout.write` escribe igual con `verbosity=0`, así que el
  registro del seed salía por la terminal en cada `setUp` y enterraba el resumen de la suite
  —de ahí la costumbre de mandarla a un fichero—. Toda escritura de `sembrar` pasa por
  `_informar`, que es el único sitio donde se decide callar.
- **`connection.in_atomic_block` no sirve como prueba**: bajo `TestCase` **siempre** es
  `True`, porque cada prueba va envuelta en una transacción. Para fijar «se validó dentro
  del bloqueo» hay que mirar el **orden de las consultas** con `CaptureQueriesContext`: el
  `SELECT … FOR UPDATE` antes de la lectura que decide.
- **Una comprobación de rol compartida acaba nombrando la función equivocada.** `_solo_el_cajero`
  contestaba «registrar ventas en el punto de venta» a quien intentó cuadrar la caja, y
  `_solo_la_administracion` decía «los reportes de ventas e inventario» a quien pidió la
  auditoría: el rol era el correcto y el mensaje citaba otra historia. Pásale **qué acción
  nombrar**, y redáctalo con el infinitivo delante —«Consultar X **es** de…»— o no concuerda con
  un sujeto singular. Las tres veces se vio ejecutándolo con cada rol, nunca en una prueba que
  solo espera `PermissionDenied`.
- **Las pruebas necesitan un `collectstatic` previo, y en un clon limpio no lo hay.** El
  ejecutor fuerza `DEBUG=False`, y con `CompressedManifestStaticFilesStorage` cada plantilla
  que cite una hoja pide su entrada del manifiesto: **285 errores** de «Missing staticfiles
  manifest entry». En una máquina de trabajo no se ve nunca, porque `staticfiles/` quedó de
  una captura anterior. Salió al correr la suite dentro del contenedor recién construido
  (`DT-37`); el arranque del compose lo hace ahora, y en el host hay que hacerlo a mano.

---

## [S5] Contenedores

Lo que costó meter la aplicación en el `docker compose` (`DT-37`). Casi todas fallan sin
error: el stack levanta y lo que sale está mal, o sale bien y tarda sin motivo, o se cae
veinte minutos después. La que sí da error lo da en la máquina de otro, no en la tuya.

- **`runserver` con conexiones persistentes agota PostgreSQL.** Atiende cada petición en un
  hilo nuevo, y con `CONN_MAX_AGE` distinto de cero cada hilo deja su conexión abierta al
  morir. En el host no se notaba —nadie hace cien peticiones—, pero el healthcheck del
  contenedor pide `/salud/` cada 5 s: en unos veinte minutos había **100 conexiones
  inactivas**, el máximo de PostgreSQL, y todo lo demás —las pruebas, `psql`— recibía «too
  many clients already». El compose fija `DJANGO_CONN_MAX_AGE=0`; lo avisa la propia
  documentación de Django, y `config/tests_contenedor.py` lo vigila.

- **Una URL firmada lleva el host dentro de la firma.** Django alcanza MinIO en
  `minio:9000` y el navegador en `localhost:9000`: firmada contra el primero, el navegador no
  resuelve el nombre; reescrita después al segundo, MinIO responde `403`. Y `custom_domain`
  de `django-storages` cambia el host **quitando la firma**. La salida es firmar contra la
  dirección pública desde el principio: `S3_ENDPOINT_URL_PUBLICO` y `config/almacenamiento.py`.
  Las imágenes de producto no lo notan —las sirve la aplicación—, así que el catálogo se ve
  bien y **solo fallan las fotografías de los estudiantes**.
- **Una clave que solo conoce el Compose nuevo rompe a todos los viejos, y en local no se
  ve.** `build.provenance` la entiende Compose 5; los Compose 2 —el del runner de GitHub, y
  cualquiera hasta el v2.33 al menos— rechazan el fichero **entero** con «Additional property
  provenance is not allowed», antes de construir nada. Así cayó la primera ejecución de la CI,
  a los nueve segundos. Y la clave ni siquiera hacía falta: se puso contra una recreación de
  contenedores que achacamos a la atestación de buildx, y la causa era la de la entrada
  siguiente. **La atestación cambia el ID del índice de la imagen en cada construcción, pero
  Compose no recrea por eso**: compara la imagen, no el índice que la envuelve. La CI valida
  ahora `compose.yaml` con el Compose mínimo declarado, v2.20.3.
- **Dos servicios con `build:` y la misma `image:` se pisan.** Cada uno etiqueta la imagen con
  su `com.docker.compose.service`, así que son dos imágenes distintas con el mismo nombre y
  gana la que termina última: el ID cambia de un `up` a otro y vuelve la recreación de arriba.
  Construye uno —`app`— y el otro la usa con `pull_policy: never`.
- **`COPY . .` en una imagen de desarrollo recrea los contenedores con cada edición.** El
  código ya llega montado, así que copiarlo no aporta nada y hace que tocar una plantilla
  cambie la imagen. La imagen copia solo `pyproject.toml`, `uv.lock` y lo mínimo para bajar
  Tailwind (`config/ajustes_de_construccion.py`).
- **Un proceso en segundo plano de un script recibe `/dev/null` como stdin**, y `tailwind
  watch` se para en cuanto su stdin se cierra (`[S1]`). La receta de `[S1]` —`tail -f
  /dev/null | …`— **no sirve con `&` y `wait`**: una tubería no termina hasta que termina
  `tail`, que no termina nunca, así que la muerte del vigilante no se ve. En
  `docker/vigilar-estilos.sh` va con `< <(tail -f /dev/null)`.
