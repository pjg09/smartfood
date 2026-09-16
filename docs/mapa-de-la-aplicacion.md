# SmartFood — Mapa de la aplicación

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-MAPA |
| titulo | Qué pantallas existen, quién alcanza cada una y con qué cuenta se entra |
| tipo_documento | Documento operativo. **No es un artefacto de Scrum ni un entregable** |
| documentos_fuente | `config/urls.py`; `./smartfood.md` (`S11`, `S5`); `./decisiones-tecnicas.md` (`DT-2`, `DT-16`, `DT-23`, `DT-25`); `./desarrollo.md` |
| actualizado | 2026-09-08; adopción visual completada pantalla por pantalla (`DT-25`) |
| idioma | es-CO |
| version | 1.2 |

### [S0.1] Qué responde este documento

**Qué hay construido, por dónde se entra y qué ve cada rol.** `./desarrollo.md` dice cómo
levantar el entorno y con qué credenciales; esto dice qué encuentras una vez dentro.

**Cada código de respuesta de `[S2]` y `[S3]` se comprobó ejecutando**, con los cuatro roles
y con un anónimo, contra el entorno local sembrado. No hay ninguno supuesto.

---

## [S1] Por dónde se entra

**`/login/` es la puerta de los cuatro roles** (`TT-56`, `DEC-12`). Es la única por la que
puede entrar el acudiente: `/admin/login/` exige `is_staff` y lo rechaza siempre, porque
`INT-1` no es el admin (`DT-2`).

`/admin/` también acepta a la institución y al personal de la cafetería, y es donde
trabajan: `INT-3` es el admin de Django y no lleva plantillas propias.

**Las credenciales locales están en `[S2.1]` de `./desarrollo.md`.** No se repiten aquí para
que no envejezcan en dos sitios. Las cuentas que siembra `manage.py sembrar --estudiantes N`
son `institucion@example.com`, `administracion@example.com`, `cajero@example.com` y una por
acudiente ficticio.

---

## [S2] Las catorce rutas

Pantallas propias, con Tailwind y HTMX. Todo lo demás vive en el admin (`[S3]`), que habla
los mismos colores desde `DT-23`.

| Ruta | Qué es | Quién | Tarea |
|---|---|---|---|
| `/` | Portada; reparte según el rol de quien mira | Todos | `TT-05` |
| `/login/` | Entrar. Redirige si ya hay sesión | Todos | `TT-56` |
| `/salir/` | Cerrar sesión. **Solo POST**: un `GET` responde `405` | Todos | `TT-56` |
| `/invitacion/<uid>/<token>/` | Definir la contraseña propia desde la invitación | Quien tenga el enlace | `TT-11` |
| `/invitacion/lista/` | Confirmación de que quedó definida | — | `TT-11` |
| `/padron/` | Padrón: quién está matriculado y qué acudientes han activado su cuenta | Institución | `DT-27` |
| `/padron/tabla/` | Fragmento HTMX de la tabla del padrón, filtrada | Institución | `DT-27` |
| `/carga/` | Carga masiva de estudiantes y acudientes por CSV | Institución | `TT-24` |
| `/mis-estudiantes/` | Panel del acudiente con sus estudiantes | Acudiente | `TT-29` |
| `/mis-estudiantes/<id>/` | Fragmento HTMX del estudiante elegido | Acudiente, **solo los suyos** | `TT-29` |
| `/mis-estudiantes/<id>/recargar/` | Recargar la billetera de un estudiante a cargo | Acudiente, **solo los suyos** | `TT-61` |
| `/mis-estudiantes/<id>/limite/` | Fijar o cambiar el límite diario de gasto de un estudiante a cargo | Acudiente, **solo los suyos** | `TT-96` |
| `/mis-estudiantes/<id>/restricciones/productos/` | Catálogo con un interruptor por producto: qué no puede comprar | Acudiente, **solo los suyos** | `TT-99` |
| `/mis-estudiantes/<id>/restricciones/productos/lista/` | Fragmento HTMX de esa lista, filtrada por el buscador | Acudiente, **solo los suyos** | `TT-99` |
| `/mis-estudiantes/<id>/restricciones/productos/bloqueo/` | `POST`. Bloquea o desbloquea un producto y devuelve la lista | Acudiente, **solo los suyos** | `TT-99` |
| `/mis-estudiantes/<id>/restricciones/alergenos/` | Los alérgenos del catálogo con un interruptor: a qué es alérgico | Acudiente, **solo los suyos** | `TT-102` |
| `/mis-estudiantes/<id>/restricciones/alergenos/bloqueo/` | `POST`. Bloquea o desbloquea un alérgeno y devuelve la lista | Acudiente, **solo los suyos** | `TT-102` |
| `/estudiantes/<id>/tarjeta/` | Tarjeta imprimible con su código de barras | Institución | `TT-37` |
| `/punto-de-venta/` | Punto de venta: identificación, catálogo y venta | **Solo cajero** | `TT-57`, `TT-58` |
| `/punto-de-venta/identificacion/` | Fragmento HTMX del estudiante con su fotografía, su saldo y su consumo del día, por tarjeta o por documento | **Solo cajero** | `TT-71`, `TT-73`, `TT-75`, `TT-77` |
| `/punto-de-venta/cliente-generico/` | `POST`. Saca al estudiante de la venta en curso | **Solo cajero** | `TT-89` |
| `/punto-de-venta/carrito/` | `POST`. Monta la venta: añadir, descontar, quitar, vaciar | **Solo cajero** | `TT-81` |
| `/punto-de-venta/cobrar/` | `POST`. **La transacción**: descuenta saldo y existencias a la vez | **Solo cajero** | `TT-80`, `TT-81` |
| `/catalogo/imagenes/<clave>` | Imagen de un producto, con caché de un mes | **Cualquiera** | `TT-53` |
| `/salud/` | Sonda del despliegue | Cualquiera | `TT-04` |

**Comprobado ejecutando**, con cada rol identificado y con un anónimo:

| Ruta | Institución | Administración | Cajero | Acudiente | Anónimo |
|---|---|---|---|---|---|
| `/` | 200 | 200 | 200 | 200 | 200 |
| `/padron/` | **200** | 403 | 403 | 403 | 302 → acceso |
| `/carga/` | **200** | 403 | 403 | 403 | 302 → acceso |
| `/mis-estudiantes/` | 403 | 403 | 403 | **200** | 302 → acceso |
| `/mis-estudiantes/<id>/recargar/` | 403 | 403 | 403 | **200** | 302 → acceso |
| `/mis-estudiantes/<id>/limite/` | 403 | 403 | 403 | **200** | 302 → acceso |
| `/mis-estudiantes/<id>/restricciones/productos/` | 403 | 403 | 403 | **200** | 302 → acceso |
| `/mis-estudiantes/<id>/restricciones/productos/bloqueo/` (`POST`) | 403 | 403 | 403 | **200** | 302 → acceso |
| `/mis-estudiantes/<id>/restricciones/alergenos/` | 403 | 403 | 403 | **200** | 302 → acceso |
| `/mis-estudiantes/<id>/restricciones/alergenos/bloqueo/` (`POST`) | 403 | 403 | 403 | **200** | 302 → acceso |
| `/estudiantes/<id>/tarjeta/` | **200** | 403 | 403 | 403 | 302 → acceso |
| `/punto-de-venta/` | 403 | 403 | **200** | 403 | 302 → acceso |
| `/punto-de-venta/identificacion/` | 403 | 403 | **200** | 403 | 302 → acceso |
| `/catalogo/imagenes/<clave>` | 200 | 200 | 200 | 200 | **200** |

Cuatro filas piden explicación:

- **El acudiente recibe `403` en la tarjeta, también la de su propio hijo.** `HU-45` es de
  `USR-5`: quien produce la tarjeta es el colegio. Si algún día el acudiente tiene que
  verla, será con una historia que lo pida.
- **Un acudiente que pide la recarga o el límite de un estudiante ajeno recibe `404`, no
  `403`.** Comprobado ejecutando. Es la misma regla del fragmento HTMX: los dos casos —no
  existe y no es tuyo— se responden igual a propósito, porque un `403` le confirmaría
  a un desconocido que ese estudiante existe. Los otros tres roles reciben `403` antes de
  que se mire ningún identificador: el rol se rechaza primero.
- **La administración de la cafetería recibe `403` en el punto de venta.** No es un
  olvido: `[S11]` concede «registrar ventas en el punto de venta» al cajero y a nadie
  más. Quien administra el catálogo no cobra.
- **La imagen del producto se sirve sin sesión, a propósito** (`DT-21`). «Público» significa
  *no sensible*: es la fotografía de una empanada. Exigir sesión no protegería nada y
  rompería la caché que `INT-2` necesita. La clave no se adivina: la genera el servidor.

### [S2.1] De qué armazón cuelga cada pantalla

Tres armazones sobre una base común (`DT-23`, `DT-16`). Cuál usa una pantalla no es
decoración: decide si lleva barra lateral, si la cabecera puede ir sobre un bloque oscuro y
qué pasa al imprimirla.

| Armazón | Qué pinta | Pantallas |
|---|---|---|
| `base-publica.html` | Cabecera flotante que se opaca al bajar, y pie | `/` |
| `base-acceso.html` | Dos columnas: panel de marca y formulario | `/login/`, `/invitacion/…`, `/invitacion/lista/` |
| `base-aplicacion.html` | Barra superior flotante, barra lateral oscura y cajón de móvil | `/mis-estudiantes/`, `/carga/`, la tarjeta de `TT-37` |
| `base-punto-de-venta.html` | Pantalla completa, sin diálogos, con foco permanente y una **columna de iconos que no se despliega** | `/punto-de-venta/` |
| `admin/base_site.html` | `INT-3` con los colores de la marca, sin tocar sus plantillas | todo `/admin/` |

**El punto de venta (`INT-2`) ya tiene el suyo** (`TT-57`): se opera con teclado y lector,
así que no lleva diálogos y el foco vuelve solo al campo del modo activo. Su columna
lateral es de iconos y **no se despliega**: no hay botón que lo intente, porque los 280 px
de las etiquetas saldrían de la zona donde el cajero pulsa. Hoy tiene una sola entrada
—esta misma pantalla—, así que sirve para situarse y para salir, no para navegar.

**Los dos modos de identificación son pestañas**, y los dos campos existen siempre en el
documento: la pestaña enseña uno y esconde el otro, no los crea. Eso es lo que mantiene una
sola ruta para las dos vías (`HU-16`, primer criterio) sin que nadie tenga que mantenerlo
así. El panel de documento nace oculto con el atributo `hidden`, de modo que sin JavaScript
la pantalla sigue sirviendo para escanear, que es lo que se hace casi siempre.

**El tema —claro, oscuro o el del sistema— es una preferencia del navegador de cada
persona, no de su cuenta.** No se guarda en la base y no viaja entre aparatos. El del admin
es el suyo propio: Django lo resuelve con su botón y su atributo, y no se fuerzan a
coincidir porque dejaría media pantalla en cada tema.

---

## [S3] Qué ve cada rol en el admin

| Modelo | Institución | Administración | Cajero | Acudiente |
|---|---|---|---|---|
| `personas.estudiante` | **200** | 403 | 403 | 302 |
| `personas.acudiente` | **200** (solo consulta) | 403 | 403 | 302 |
| `personas.institucion` | **200** | 403 | 403 | 302 |
| `cuentas.usuario` | **200** | 403 | 403 | 302 |
| `catalogo.producto` | 403 | **200** | 403 | 302 |
| `catalogo.categoria` | 403 | **200** | 403 | 302 |
| `catalogo.alergeno` | 403 | **200** | 403 | 302 |
| `inventario.movimientoinventario` | 403 | **200** | 403 | 302 |
| `auth.group` | **403** | 403 | 403 | 302 |

Es la matriz `[S11]` en la capa de datos (`DT-11`), no botones escondidos. Tres lecturas que
conviene no perder:

- **El catálogo es de quien lo vende.** La institución recibe `403`: `[S11]` no le da el
  catálogo, y desde `UX-6` ya no es superusuario, así que la matriz la vincula de verdad.
- **Nadie alcanza los grupos de permisos.** Esos grupos **son** la matriz con la que `DT-11`
  sostiene `INV-4`; quien los edita puede concederle al cajero lo que la invariante prohíbe.
- **El cajero ya no entra al admin.** Su cuenta nace sin `is_staff` y no tiene la entrada en
  el menú: `[S11]` le concede registrar ventas, y eso ocurre entero en `INT-2`. Antes entraba
  y veía un índice sin un solo modelo — no era un agujero, porque `PERMISOS_POR_ROL` no le
  concede nada, pero sí una puerta que no llevaba a ninguna parte. La migración
  `cuentas.0004` se lo quitó también a las cuentas que ya existían.

---

## [S4] Lo que hace cada rol, pantalla por pantalla

### Institución educativa (`USR-5`)

**`/padron/` es su pantalla de todos los días** (`DT-27`). Dice quién está matriculado y, al
lado de cada estudiante, **si su acudiente ya activó la cuenta**: la carga masiva genera la
invitación pero no la entrega (`DEC-9`), así que sin esa columna nadie sabe quién sigue sin
poder entrar hasta que un niño se queda sin saldo. Se busca por nombre, documento, tarjeta y
acudiente —las cinco formas en que alguien pregunta en secretaría—, y los retirados no salen
salvo que se pidan: dar de baja es un estado (`HU-51`), pero el padrón responde «quién está
matriculado **hoy**».

**El padrón solo lee.** Cada fila enlaza al admin para editar, y ahí sigue estando todo lo que
escribe. Es la única excepción a `DT-2`, y está declarada.

Carga masiva en `/carga/`. En el admin: *Estudiantes* —listado con estado, código de tarjeta
y si tiene fotografía; búsqueda por nombre, documento, código o acudiente; alta individual
con autocompletado; acciones de **reasignar el código** y **dar de baja**, las dos con
confirmación—, *Acudientes* de solo consulta, y *Usuarios* para dar de alta al personal,
desactivarlo, reactivarlo y reenviarle la invitación.

### Administración de la cafetería (`USR-4`)

En el admin: productos con precio, categoría, ocho campos nutricionales por porción
(`./campos-nutricionales.md`), alérgenos declarados e imagen; categorías; alérgenos.
Acciones de retirar y devolver al catálogo. **Nada se borra**: retirar es un estado.

Desde `HU-27`, también el **inventario**: el listado de productos trae una columna de
existencias —calculada sumando el historial, no guardada (`INV-3`)— y *Movimientos de
inventario* registra el ingreso de mercancía por ajuste manual. Ese libro **se lee y se
le añaden asientos, pero no se edita ni se borra**: un asiento corregido a posteriori
deja unas existencias que ya no explican lo que pasó. Un error se corrige con otro
movimiento.

### Acudiente (`USR-2`)

`/mis-estudiantes/`, y desde ahí `recargar` la billetera de cada uno (`HU-06`): el pago
es simulado y la pantalla lo dice, pero **el movimiento queda asentado de verdad** en el
historial del que sale el saldo (`INV-2`). A un estudiante de baja o desactivado no se le
ofrece recargar, y el servicio lo rechaza igual aunque se escriba la URL (`INVD-2`).

Y desde ahí los **alérgenos bloqueados** (`HU-11`, `TT-102`), que es lo que hay que usar
para una alergia: lo que se marca es **la condición**, no los productos que hoy la llevan,
así que lo que la cafetería agregue el mes que viene queda fuera solo. La pantalla enseña
cuántos productos lo declaran **hoy** —y dice «hoy»— porque esa cifra describe el catálogo
actual y el bloqueo no depende de ella (`INV-5`). Se puede bloquear un alérgeno que
todavía no declara ningún producto: el acudiente declara la alergia de su hijo, no el
menú.

Las dos pantallas de restricciones llevan debajo **el historial de cambios** (`HU-12`,
`TT-105`): qué se bloqueó, qué se retiró, cuándo y quién. Retirar una protección sobre la
alimentación de un menor es una acción auditable, y un asiento que nadie puede leer no
hace auditable nada. El historial mezcla productos y alérgenos porque el acudiente no
separa mentalmente sus dos listas — y guarda el nombre **tal como estaba**, así que
renombrar el catálogo no reescribe lo que vio al decidir (`DT-8`).

Y los **productos bloqueados** (`HU-10`, `TT-99`): el catálogo con un
interruptor por producto, buscador incluido. Lo que se marca aquí es una **lista de
productos identificados**, no una condición: bloquear «Torta de chocolate» no bloquea lo
demás que lleve maní, y la pantalla lo dice con todas las letras porque creerlo es
exactamente el malentendido que el control parental no puede permitirse — eso es `HU-11`.
Solo se ofrecen los productos que están en el catálogo; el servicio sí admite bloquear uno
retirado, para que la restricción siga ahí si el producto vuelve.

Y `limite`, el **cupo diario de gasto** de cada estudiante (`HU-09`,
`TT-96`). Es por estudiante y no de la cuenta: un acudiente con tres hijos fija tres cupos
distintos. **Lo escribe solo él**, entre por donde entre —`INV-4`—, y la pantalla dice sin
rodeos que el cupo todavía no rechaza ninguna venta: esa comprobación es `HU-20`, y hasta
entonces prometerla sería peor que no ofrecer el campo. A un estudiante de baja **sí** se
le puede configurar: fijar un cupo no mueve dinero, así que `INVD-2` no lo alcanza.

`/mis-estudiantes/`: sus estudiantes, con selector cuando tiene más de uno, **el saldo de
cada uno y sus últimos cinco movimientos** (`HU-07`). El saldo no es un campo guardado: se
calcula sumando el historial al pedir la página (`INV-2`), y el historial va debajo
precisamente para que la cifra se pueda comprobar. Si alguno está de baja, lo dice, y **su saldo sigue ahí**: congelado, sin poder recargarlo ni gastarlo, y con el aviso de que la devolución del dinero no se hace desde el sistema (`HU-52`, `ALC-OUT-01`). El saldo y el límite diario **son suyos y ya están** (`HU-07`, `HU-09`); las restricciones por
producto y por alérgeno llegan en este mismo sprint y su tarjeta declara dónde irán y
**cuándo**, en vez de enseñar un cero —un cupo de cero y un cupo que todavía no existe no
son lo mismo—.

Entra desde el teléfono (`INT-1`), así que la pantalla se diseña a 390 px primero: la barra
lateral no se colapsa ahí, se abre como un cajón sobre el contenido.

### Cajero (`USR-3`)

`/punto-de-venta/`, y **solo eso**: es su única pantalla y su menú tiene una sola entrada.
Cualquier otro rol recibe `403` aunque escriba la URL (`DT-11`), y él no entra al admin —
`[S11]` le concede registrar ventas, y registrar ventas ocurre entero aquí. La pantalla
coloca las tres zonas —quién compra, qué compra y cuánto es— y el campo donde escribe el
lector, que retiene el foco.

**Identificar ya funciona, por las dos vías.** El lector teclea el código y envía Enter
(`HU-15`), y quien no trae la tarjeta se busca por su documento (`HU-16`): **las dos
piden a la misma ruta y devuelven el mismo fragmento**, así que no pueden acabar en
resultados distintos. Un estudiante de baja o desactivado **se identifica igual**,
avisando de que no se le puede vender: decir «esa tarjeta no es de nadie» sería mentir y
dejaría al cajero repitiendo el escaneo.

**Y al identificar aparece con qué se cobra** (`HU-17`): el saldo y el consumo del día,
en el mismo fragmento y en la misma petición. Sin saldo, la tarjeta se pinta en rojo y
dice qué hacer — es el «para» de la historia, *saber antes de cobrar si la venta va a
poder realizarse*. Las restricciones vigentes son el tercer dato y llegan con `HU-13`, en
el Sprint 3; hasta entonces su bloque **dice qué falta en vez de afirmar que no hay**,
porque «sin restricciones» se leería en una caja como *puede comprar cualquier cosa*.

**Y con la cara de quien debería estar presentando la tarjeta** (`HU-58`, `DEC-8`). Es un
control **preventivo** de suplantación: el código de la tarjeta opera como credencial de
acceso al saldo (`FUN-4`), y desactivarla (`HU-47`, `HU-48`) solo actúa desde que alguien
reporta la pérdida — la fotografía cierra las horas que van de una cosa a la otra. Si el
estudiante no tiene fotografía **la venta procede igual, y el hueco se dice**: un avatar
genérico haría creer que la comprobación se hizo. Ninguna es de una persona real: se
generan en el seed (`INVD-6`).

**Aquí, y solo aquí, ve el cajero un saldo.** `[S11]` se lo concede «solo al cobrar», y lo
que lo sostiene no es un rótulo: el selector que lo devuelve exige el rol cajero, y el
cajero recibe `403` en el panel del acudiente, en la ficha del estudiante y en la recarga
—las otras tres pantallas donde hay un saldo escrito—.

**Y con qué se paga ya está decidido** (`HU-54`, `TT-79`). La columna del ticket ofrece
**solo lo que la base va a aceptar**: con un estudiante identificado el medio es la
billetera y no hay nada que elegir —su compra sale de su saldo—; sin estudiante, efectivo o
transferencia, que son los medios de la venta a cliente genérico (`DEC-1`). No son tres
botones con uno apagado: lo que no aplica **no se ofrece**, y quien lo impone de verdad es
una `CheckConstraint`, no la pantalla.

**La transferencia no pasa por el sistema.** Va del banco del cliente al de la cafetería y
aquí solo queda constancia de que se pagó así (`ALC-OUT-01`). La pantalla lo dice, porque
quien lee «Transferencia» en una caja puede entender que el sistema la cobra o que recarga
algo.

**Y cobra** (`HU-21`, `TT-80`). El catálogo enseña precio y existencias, cada producto es un
botón, el ticket suma y el botón cobra **sin preguntar** —`INT-2` descarta los diálogos: un
modal roba el foco, y el foco es del lector—. Al confirmar, el saldo y las existencias se
descuentan **en la misma transacción**: o las dos cosas, o ninguna.

**Lo que impide que dos cajas cobren el mismo saldo es el orden** (`DT-6`): se bloquea,
luego se valida, luego se escribe. Validar antes daría el mismo resultado en una prueba
secuencial y dejaría la billetera en negativo con dos cajeros a la vez. Hay cuatro pruebas
de concurrencia que lo vigilan, y se comprobó que fallan si alguien invierte ese orden.

Tras cobrar, la caja queda lista para el siguiente: el carrito se vacía, el cliente se
olvida y el catálogo vuelve con las existencias de ahora.

Cada renglón **se queda con el precio y los nutrientes de ese momento** (`HU-22`, `DT-8`):
subir un precio o corregir una ficha nutricional no reescribe las ventas ya asentadas, que
es lo que hace que el historial de consumo de `HU-30` sea un historial y no una proyección
del catálogo de hoy sobre el pasado.

**Y se puede cobrar sin identificar a nadie** (`HU-53`, `DEC-1`). Un docente, alguien del
personal o un visitante compran sin estar registrados en ningún sitio: la venta descuenta
inventario como cualquier otra, **no toca ninguna billetera** y se paga en efectivo o por
transferencia. No hay modo que encender —una venta a cliente genérico **es** una venta sin
estudiante—, así que la columna del cliente lo dice cuando está vacía, y ofrece volver a
ella cuando hay alguien identificado, sin vaciar el carrito.

**Si el saldo no alcanza, la venta no se realiza y la pantalla dice cuánto falta** (`HU-19`,
`INV-1`): «No alcanza: el saldo es $5.000 y la venta suma $10.000. Faltan $5.000». No se
descuenta nada —ni saldo ni existencias— y **el carrito se queda montado**, porque lo que el
cajero necesita es quitar un renglón y volver a pulsar, no montar la venta otra vez con la
fila esperando.

**Lo que todavía no evalúa la venta** son las restricciones alimentarias y el límite diario
(`HU-18`, `HU-20`), del Sprint 3. Su sitio es el mismo punto donde hoy se lee el saldo.

---

## [S5] El recorrido de demostración

El orden en que se enseña lo construido. Cada paso se comprobó de extremo a extremo.

> **El recorrido crea las existencias y el saldo por su propio camino** —pasos 4 y 10—, así
> que enseñado entero no hace falta nada más. Para saltar directo al punto de venta, el atajo
> de `[S1.2]` de `./desarrollo.md` los siembra de una vez: sin existencias ni saldo, la
> demostración se queda en la pantalla de identificación.

1. **`/login/` como institución** → `/carga/`, subir un CSV con dos filas del mismo
   acudiente. `HU-01`, `HU-02`.
2. **`manage.py invitacion <correo del acudiente>`** → abrir el enlace, definir la
   contraseña. `HU-03`. **Tiene que ser un acudiente cargado por la pantalla**: a los que
   siembra `--estudiantes` se les asigna contraseña y el comando los rechaza (`DEC-11`).
3. **`/login/` con ese acudiente** → `/mis-estudiantes/`, con su selector. `HU-04`.
4. **Recargar la billetera** de uno de sus estudiantes. El saldo aparece en su ficha con el
   movimiento debajo: es la suma del historial, no una cifra guardada. `HU-06`, `HU-07`,
   `HU-08`, `INV-2`.
5. **Fijar su límite diario** desde la misma ficha. Con dos estudiantes a cargo se ve que
   el cupo es de uno y no del otro. La pantalla avisa de que todavía no frena la caja:
   eso llega con `HU-20`. `HU-09`.
6. **Bloquear un alérgeno** desde la tarjeta de restricciones. Luego, como administración,
   **crear un producto nuevo que lo declare**: queda cubierto sin volver a tocar nada. Es
   `INV-5` enseñada en vivo, y el paso que más conviene no saltarse en la Sprint Review.
   `HU-11`.
7. **Retirar uno de los bloqueos** y mirar «Cambios recientes» debajo: queda anotado
   quién lo retiró y cuándo, y el bloqueo anterior también está. `HU-12`.
8. **Bloquear un par de productos** desde la tarjeta de restricciones. El catálogo aparece
   con su interruptor; lo bloqueado se marca en rojo. Bloquear uno **no** arrastra a los
   que comparten alérgeno — eso es `HU-11`, y la pantalla lo advierte. `HU-10`.
   Más adelante, al cobrar, se intenta comprar uno de ellos: la venta se rechaza con
   saldo de sobra y sin forma de forzarla. `HU-60`, `INV-4`.
9. **Como institución, `/padron/`**: quién está matriculado y **qué acudientes no han
   activado su cuenta todavía**. Se busca por nombre, documento, tarjeta o acudiente, y se
   marca «Ver retirados» para ver a los dados de baja. `DT-27`, `HU-44`, `DEC-9`.
10. **Como institución**, *Estudiantes* → **Imprimir tarjeta**, al 100 %. `HU-43`, `HU-45`.
11. **Reasignar el código** y volver a imprimir: la tarjeta anterior deja de identificar a
   nadie en el mismo momento. `HU-46`, `INVD-4`.
12. **Dar de baja**: no borra nada, el acudiente lo ve en su panel, y en `/padron/` deja de
   salir salvo que se marque «Ver retirados». `HU-51`, `HU-52`.
13. **`/login/` como administración** → el catálogo. `HU-26`, `HU-57`, `HU-59`.
14. **Ingresar mercancía** desde la administración: las existencias salen de la suma del
   historial, no de un contador. `HU-27`, `INV-3`.
15. **`/login/` como cajero** → `/punto-de-venta/`. Escanear la tarjeta: aparecen la
    fotografía, el saldo y el consumo del día. `HU-15`, `HU-17`, `HU-58`.
16. **Montar la venta** pulsando productos y **cobrar**. El saldo baja, las existencias
    bajan y las dos cifras siguen saliendo del historial. `HU-21`, `HU-54`, `INV-2`,
    `INV-3`.
17. **Volver a cobrar sin saldo suficiente**: la venta se rechaza diciendo cuánto falta y
    no se descuenta nada. Es el escenario crítico **`TST-2`** (`HU-19`, `INV-1`).
18. **«Cobrar sin identificar a nadie»** y cobrar en efectivo: la venta genérica descuenta
    inventario y no toca ninguna billetera. `HU-53`, `HU-54`, `DEC-1`.

---

## [S6] Lo que todavía no existe

Lo que cuelga del control parental (`HU-13`), los rechazos que dependen del
alérgeno y del cupo (`HU-18`, `HU-20`), la merma y las alertas de inventario
(`HU-28`, `HU-29`), reportes y recomendaciones (`HU-30`…`HU-34`) y cierre de caja
(`HU-55`, `HU-56`).

**Las tres restricciones se configuran; solo una frena la venta.** El producto bloqueado
la rechaza (`HU-60`); el alérgeno lo hará con `HU-18` y el cupo diario con `HU-20`. Hasta
entonces `HU-11` deja la condición escrita y consultable, pero la caja todavía no la mira.

**El producto bloqueado ya frena la venta; el límite diario todavía no.** `HU-10` deja la
lista escrita y `HU-60` la hace cumplir: cobrar algo bloqueado se rechaza dentro de la
transacción, sin descontar saldo ni existencias, y el cajero no tiene ninguna acción para
omitirlo (`INV-4`). El cupo de `HU-09` sigue sin comprobarse al cobrar — eso es `HU-20`.

`HU-60` no estaba en la planeación del sprint: se añadió al descubrirse, construyendo
`HU-10`, que `ALC-IN-09` pide aplicar las restricciones en la venta y ninguna historia lo
hacía para esa lista.

**El punto de venta vende.** Identifica por las dos vías (`HU-15`, `HU-16`), enseña la
fotografía (`HU-58`), el saldo y el consumo del día (`HU-17`), el medio de pago (`HU-54`), y
cobra descontando saldo y existencias en una sola transacción (`HU-21`). `HU-17` sigue
marcada como abierta aun con su panel construido: le falta el bloque de restricciones, que
es del Sprint 3.

**El dinero del acudiente está completo**: recargar (`HU-06`), el saldo derivado del
historial (`HU-08`, `TST-3`) y verlo en su panel (`HU-07`). Lo que falta es gastarlo, que
es la venta del punto de venta.

La app `reportes` **no está creada**: cada una se crea en el sprint que
la necesita (`[S3]` de `./decisiones-tecnicas.md`). `ventas` nació en `TT-57` para que la
pantalla tuviera dónde vivir y hoy tiene sus modelos (`TT-78`) y **su servicio** (`TT-80`):
la venta con su medio de pago y su estudiante opcional, la línea de venta, y la transacción
única que sostiene `INV-1`, `INV-2` e `INV-3` a la vez. La línea congela además el precio y los
nutrientes que el producto declaraba al venderse (`TT-84`, `HU-22`): editar el catálogo
mañana no reescribe lo que se cobró hoy. `billetera` e `inventario` tienen los suyos desde `TT-59` y
`TT-67`, y **ninguno es una columna `saldo` ni `existencias`**; desde `TT-78` los dos
señalan además la venta que origina cada movimiento.
