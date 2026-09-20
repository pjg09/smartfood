# SmartFood — Mapa de la aplicación

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-MAPA |
| titulo | Qué pantallas existen, quién alcanza cada una y con qué cuenta se entra |
| tipo_documento | Documento operativo. **No es un artefacto de Scrum ni un entregable** |
| documentos_fuente | `config/urls.py`; `./smartfood.md` (`S11`, `S5`); `./decisiones-tecnicas.md` (`DT-2`, `DT-16`, `DT-23`, `DT-25`); `./desarrollo.md` |
| actualizado | 2026-09-19; `PR-06` del Sprint 5 — el reporte de consumo del acudiente completo (`HU-30` … `HU-34`) y los de ventas e inventario de la cafetería (`HU-35`, `HU-36`). Los códigos de `[S2]` y `[S3]` se volvieron a medir en la revisión de cierre del Sprint 3; los reportes se comprobaron ejecutando con los cinco perfiles |
| idioma | es-CO |
| version | 1.8 |

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

## [S2] Las treinta y nueve rutas

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
| `/padron/<id>/desactivar/` | `POST`. Desactiva a un estudiante: su tarjeta deja de comprar | Institución | `TT-120`, `DT-29` |
| `/padron/<id>/reactivar/` | `POST`. Lo devuelve a activo. **Solo la institución**, venga la desactivación de donde venga (`INVD-3`) | Institución | `TT-123`, `DT-30` |
| `/carga/` | Carga masiva de estudiantes y acudientes por CSV | Institución | `TT-24` |
| `/mis-estudiantes/` | Panel del acudiente con sus estudiantes | Acudiente | `TT-29` |
| `/mis-estudiantes/<id>/` | Fragmento HTMX del estudiante elegido | Acudiente, **solo los suyos** | `TT-29` |
| `/mis-estudiantes/<id>/recargar/` | Recargar la billetera de un estudiante a cargo | Acudiente, **solo los suyos** | `TT-61` |
| `/mis-estudiantes/<id>/consumo/` | Historial de consumo: qué compró, con la información nutricional **del día de la compra**, las alertas de frecuencia, el aporte frente a la referencia sanitaria y el gasto frente a lo recargado, con su descargo | Acudiente, **solo los suyos** | `TT-156`, `TT-160`, `TT-164`, `TT-166` |
| `/mis-estudiantes/<id>/desactivar/` | `POST`. Bloquea la tarjeta de un estudiante a cargo. **No hay ruta para reactivar** (`INVD-3`) | Acudiente, **solo los suyos** | `TT-122` |
| `/mis-estudiantes/<id>/limite/` | Fijar o cambiar el límite diario de gasto de un estudiante a cargo | Acudiente, **solo los suyos** | `TT-96` |
| `/mis-estudiantes/<id>/limite/retirar/` | `POST`. Quita del todo el límite diario | Acudiente, **solo los suyos** | `TT-135` |
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
| `/punto-de-venta/entregar/` | `POST`. Registra la entrega de un pedido anticipado. **No descuenta saldo**: ya se pagó al reservarse | **Solo cajero** | `TT-150` |
| `/punto-de-venta/cierre/` | Cierre de caja: el efectivo esperado de la jornada, calculado desde las ventas registradas, contra lo que el cajero cuenta | **Solo cajero** | `TT-173` |
| `/mis-estudiantes/<id>/reservar/` | Reserva anticipada: catálogo con cantidades, cobro al confirmar y reservas pendientes | **Solo su acudiente** | `TT-145` |
| `/reservas/` | Cola de reservas pendientes, de la más antigua a la más reciente | **Cajero y administración** | `TT-148` |
| `/catalogo/imagenes/<clave>` | Imagen de un producto, con caché de un mes | **Cualquiera** | `TT-53` |
| `/admin/catalogo/producto/<id>/historial/` | Las existencias de un producto y los movimientos que las explican | **Solo administración** | `TT-141` |
| `/admin/ventas/venta/` | Reporte de ventas: el libro filtrable con el consolidado del periodo que se mira | **Solo administración** | `TT-168` |
| `/admin/ventas/cierredecaja/` | Reporte de cierres de caja: el histórico de cuadres con su descuadre del periodo, y el enlace que explica cada esperado | **Solo administración** | `TT-176` |
| `/admin/auditoria/` | Reporte de auditoría: una línea de tiempo con las cuatro clases de operación, con quién hizo qué y cuándo | **Solo administración** | `TT-178` |
| `/admin/inventario/movimientoinventario/` | Movimientos de inventario: el libro con su consolidado —entradas, salidas y neto del periodo— | **Solo administración** | `TT-69`, `TT-170` |
| `/salud/` | Sonda de salud: responde 200 si la base de datos contesta, 503 si no | Cualquiera | `TT-04`, `DT-31` |

**Comprobado ejecutando**, con cada rol identificado y con un anónimo:

| Ruta | Institución | Administración | Cajero | Acudiente | Anónimo |
|---|---|---|---|---|---|
| `/` | 200 | 200 | 200 | 200 | 200 |
| `/padron/` | **200** | 403 | 403 | 403 | 302 → acceso |
| `/carga/` | **200** | 403 | 403 | 403 | 302 → acceso |
| `/mis-estudiantes/` | 403 | 403 | 403 | **200** | 302 → acceso |
| `/mis-estudiantes/<id>/recargar/` | 403 | 403 | 403 | **200** | 302 → acceso |
| `/mis-estudiantes/<id>/consumo/` | 403 | 403 | 403 | **200** | 302 → acceso |
| `/mis-estudiantes/<id>/limite/` | 403 | 403 | 403 | **200** | 302 → acceso |
| `/mis-estudiantes/<id>/limite/retirar/` (`POST`) | 403 | 403 | 403 | **200** | 302 → acceso |
| `/mis-estudiantes/<id>/restricciones/productos/` | 403 | 403 | 403 | **200** | 302 → acceso |
| `/mis-estudiantes/<id>/restricciones/productos/bloqueo/` (`POST`) | 403 | 403 | 403 | **200** | 302 → acceso |
| `/mis-estudiantes/<id>/restricciones/alergenos/` | 403 | 403 | 403 | **200** | 302 → acceso |
| `/mis-estudiantes/<id>/restricciones/alergenos/bloqueo/` (`POST`) | 403 | 403 | 403 | **200** | 302 → acceso |
| `/padron/<id>/desactivar/` (`POST`) | **200** | 403 | 403 | 403 | 302 → acceso |
| `/padron/<id>/reactivar/` (`POST`) | **200** | 403 | 403 | 403 | 302 → acceso |
| `/mis-estudiantes/<id>/desactivar/` (`POST`) | 403 | 403 | 403 | **200** | 302 → acceso |
| `/estudiantes/<id>/tarjeta/` | **200** | 403 | 403 | 403 | 302 → acceso |
| `/punto-de-venta/` | 403 | 403 | **200** | 403 | 302 → acceso |
| `/punto-de-venta/identificacion/` | 403 | 403 | **200** | 403 | 302 → acceso |
| `/punto-de-venta/cierre/` | 403 | 403 | **200** | 403 | 302 → acceso |
| `/admin/auditoria/` | 403 | **200** | 403 | 403 | 302 → acceso |
| `/catalogo/imagenes/<clave>` | 200 | 200 | 200 | 200 | **200** |

Cuatro filas piden explicación:

- **El acudiente recibe `403` en la tarjeta, también la de su propio hijo.** `HU-45` es de
  `USR-5`: quien produce la tarjeta es el colegio. Si algún día el acudiente tiene que
  verla, será con una historia que lo pida.
- **Un acudiente que pide la recarga, el límite o el consumo de un estudiante ajeno
  recibe `404`, no `403`.** Comprobado ejecutando. Es la misma regla del fragmento HTMX:
  los dos casos —no existe y no es tuyo— se responden igual a propósito, porque un `403`
  le confirmaría a un desconocido que ese estudiante existe. Los otros tres roles reciben `403` antes de
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
| `base-aplicacion.html` | Barra superior flotante, barra lateral oscura y cajón de móvil | `/mis-estudiantes/`, `/carga/`, la tarjeta de `TT-37`, `/reservas/`, `/punto-de-venta/cierre/` |
| `base-punto-de-venta.html` | Pantalla completa, sin diálogos, con foco permanente y una **columna de iconos que no se despliega** | `/punto-de-venta/` |
| `admin/base_site.html` | `INT-3` con los colores de la marca, sin tocar sus plantillas | todo `/admin/` |

**El punto de venta (`INT-2`) ya tiene el suyo** (`TT-57`): se opera con teclado y lector,
así que no lleva diálogos y el foco vuelve solo al campo del modo activo. Su columna
lateral es de iconos y **no se despliega**: no hay botón que lo intente, porque los 280 px
de las etiquetas saldrían de la zona donde el cajero pulsa. Tiene tres entradas —la caja,
la cola de reservas y el cierre de la jornada—, que son los tres sitios donde trabaja el
cajero y ninguno más.

**Dos de esas tres no viven dentro de este armazón**, y es deliberado: la cola de reservas
la comparte con la administración (`DT-34`) y el cierre se hace una vez, al final, con
billetes en la mano. La rejilla de tres zonas sin scroll está hecha para cobrar con una
fila delante; añadirle una cuarta zona sería romperla para dos pantallas que no la
necesitan.

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
| `personas.estudiante` | **200** | 403 | 302 | 302 |
| `personas.acudiente` | **200** (solo consulta) | 403 | 302 | 302 |
| `personas.institucion` | **200** | 403 | 302 | 302 |
| `cuentas.usuario` | **200** | 403 | 302 | 302 |
| `catalogo.producto` | 403 | **200** | 302 | 302 |
| `catalogo.categoria` | 403 | **200** | 302 | 302 |
| `catalogo.alergeno` | 403 | **200** | 302 | 302 |
| `inventario.movimientoinventario` | 403 | **200** | 302 | 302 |
| `inventario.merma` | 403 | **200** | 302 | 302 |
| `restricciones.restriccionesdelestudiante` | **200** (solo consulta) | **200** (solo consulta) | 302 | 302 |
| `ventas.venta` | 403 | **200** (solo consulta) | 302 | 302 |
| `ventas.cierredecaja` | 403 | **200** (solo consulta) | 302 | 302 |
| `/admin/auditoria/` (sin modelo) | 403 | **200** (solo consulta) | 403 | 403 |
| `auth.group` | **403** | 403 | 302 | 302 |

Es la matriz `[S11]` en la capa de datos (`DT-11`), no botones escondidos. Diez lecturas que
conviene no perder:

- **Las existencias del listado de productos son un enlace** (`HU-29`, `TT-141`). Llevan a
  `/admin/catalogo/producto/<id>/historial/`, que enseña la cifra y debajo los movimientos
  que la suman, con una columna de existencias tras cada uno. Es una vista propia del admin
  registrada en `get_urls()`, como la baja y la reasignación de `personas`: **no es una
  segunda excepción a `DT-27`**, que sigue siendo solo el padrón.
- **El reporte de ventas es el libro, con su consolidado encima** (`HU-35`, `TT-168`). El
  admin pone el listado, los filtros, la búsqueda y la navegación por fechas; lo que se añade
  es cuánto suma **lo que se está mirando**, porque se calcula sobre el mismo `QuerySet` que
  pinta la tabla. Si se calculara aparte, filtrar por «efectivo» dejaría arriba el total de
  todo y nadie lo notaría. **No es una tercera excepción a `DT-2`**: es el camino de
  `TT-141`, y aquí quien consulta ya vive en el admin.
  **Nadie lo escribe**, ni siquiera quien lo consulta: alta, edición y borrado responden
  `403`, y el permiso tampoco existe —`ventas` está en `APPS_SIN_ESCRITURA_PARA_NINGUN_ROL`—.
  Una venta se registra en el punto de venta, con su transacción, o no existe. Y **no enseña
  el documento del estudiante ni su código de tarjeta**, ni en el listado ni en la ficha: la
  cafetería consulta su actividad comercial, no el padrón.
- **El reporte de cierres de caja enseña dos cifras de descuadre, y esa es la historia**
  (`HU-56`, `TT-176`). La suma con signo se compensa sola: un sobrante de $2.000 el lunes y
  un faltante de $2.000 el martes dan cero, y un mes con veinte descuadres se leería como un
  mes que cuadra. Arriba va el **descuadre total** —lo que no se compensa—, y la neta se dice
  al lado. Es lo que convierte el reporte en lo que `HU-56` pide: **detectar un patrón** en
  vez de enterarse suelto cada día.
  **El tercer criterio no se cumple enseñando la cifra**: cada cierre enlaza al reporte de
  ventas de esa jornada, ya filtrado por efectivo. Es lo que hace comprobable `INVD-5` en dos
  clics, y hay una prueba que sigue el enlace y cuadra lo que trae contra el esperado.
  **El cajero no entra**, aunque sea quien escribe estas filas: cuadrar su caja es suyo
  (`HU-55`), leer el patrón de la cafetería es de quien administra el servicio. Y **nadie las
  edita**: el esperado quedó congelado contra el dinero que se contó aquella tarde.
- **El reporte de inventario es el mismo libro, con su consolidado encima** (`HU-36`,
  `TT-170`). No hay pantalla nueva: entradas, ventas y mermas ya estaban en un solo sitio
  desde `TT-69`, y lo que faltaba era acotar un periodo y decir cuánto suma lo que se mira —
  cuántas unidades entraron, cuántas salieron y el neto, con el desglose por tipo. **El neto
  de un periodo no son las existencias**, y la pantalla lo dice: sobre el libro entero sí lo
  son (`INV-3`), pero sobre unos días son lo que esos días movieron.
  Dice además **cuántas mermas van sin motivo**, que es siempre cero porque lo impone una
  `CheckConstraint` y no el formulario (`INV-8`): la invariante puesta donde se ve.
- **El reporte de auditoría es el único sin modelo, y por eso es el único con ruta propia**
  (`HU-37`, `TT-178`). Un `ModelAdmin` pinta el listado de *una* tabla, y la auditoría cruza
  cuatro —ventas, pedidos entregados, movimientos de inventario y cierres—, así que es una
  vista registrada en `config/urls.py` **antes** de `admin.site.urls`: Django resuelve en
  orden y `/admin/auditoria/` la atiende ella. **Sigue sin ser una tercera excepción a
  `DT-2`**: usa el armazón del admin, sus estilos y su barra; las dos excepciones declaradas
  son pantallas propias *fuera* de él.
  **No hay tabla de auditoría**, que es lo que su único criterio significa: ninguna operación
  se escribe dos veces —una en su libro y otra en un registro de eventos—, porque la segunda
  es la que nadie mira cuando falla (`DT-19`). Se leen los libros y se mezclan al leerlos.
  **Los movimientos de tipo venta no entran**: el cobro asienta la venta y su salida a la
  vez, así que incluirlos pondría cada venta dos veces. La **entrega** sí, porque mueve
  existencias en otro momento y la hace otra persona.
  **Y el ingreso y la merma no dicen quién**: el libro de inventario no guarda el actor. La
  pantalla lo declara con palabras en vez de dejar el hueco en blanco; está en el `ANEXO B`
  de `./decisiones-de-alcance.md`.
- **La merma tiene su propia entrada y es del mismo libro** (`HU-28`, `TT-139`). *Mermas* es
  un proxy de `inventario.movimientoinventario`, no una tabla nueva: existe porque el motivo
  es obligatorio en ella y opcional en el ingreso (`INV-8`), y un solo formulario tendría que
  exigirlo únicamente a veces. Sus permisos son `add` y `view`; `change` y `delete` **no
  existen**, así que un asiento no se reescribe (`INV-3`).
- **La cola de reservas no está en el admin, y es la segunda excepción declarada** (`HU-24`,
  `DT-34`). La comparten el cajero —que no tiene `is_staff`— y la administración —que recibe
  `403` en el punto de venta—, así que vive en `/reservas/`, sobre el armazón de la
  aplicación, con la entrada en los dos menús. La primera excepción es el padrón (`DT-27`).
- **Las restricciones se consultan en el admin y no se escriben en él** (`HU-38`, `INV-4`).
  La única entrada es *Restricciones por estudiante*, un proxy del estudiante **sin más
  permiso que `view`**: Django no crea los de escritura, así que no hay ninguno que
  conceder por error. Alta, edición y borrado responden `403` a los dos roles. Las tres
  tablas de restricciones siguen sin registrarse.

- **El catálogo es de quien lo vende.** La institución recibe `403`: `[S11]` no le da el
  catálogo, y desde `UX-6` ya no es superusuario, así que la matriz la vincula de verdad.
- **Nadie alcanza los grupos de permisos.** Esos grupos **son** la matriz con la que `DT-11`
  sostiene `INV-4`; quien los edita puede concederle al cajero lo que la invariante prohíbe.
- **El cajero ya no entra al admin, y por eso su columna es `302` y no `403`.** Sin
  `is_staff` no llega a la comprobación de permisos: el admin lo manda a su pantalla de
  acceso. Hasta la revisión del Sprint 3 esta tabla decía `403` en toda su columna —era el
  código de antes de que `cuentas.0004` le quitara `is_staff`, y nadie volvió a medirlo—.
  `[S11]` le concede registrar ventas, y eso ocurre entero en `INT-2`.
- **El acudiente responde `302` por el mismo motivo**, y ahí nunca fue de otra forma:
  `INT-1` no es el admin (`DT-2`).

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

**El padrón lee, y desactiva.** Cada fila enlaza al admin para editar, y ahí sigue
estando el alta, la edición, la baja y la reasignación. La desactivación es la única
escritura de la pantalla y está declarada en `DT-29`, que corrige esa parte de `DT-27`:
`HU-47` existe por la inmediatez —una tarjeta perdida en mitad de la jornada— y llegar al
admin desde aquí son tres pantallas. Un clic desactiva y la fila queda marcada en rojo;
otro la reactiva (`HU-49`, `DT-30`), y esa es la segunda escritura de la pantalla: el
desbloqueo pasa por una verificación presencial (`INVD-3`), así que ocurre con la familia
en el mostrador y el padrón delante. **Desactivar pide confirmación y reactivar no**: lo
primero deja al estudiante sin comprar hasta que alguien vaya al colegio, lo segundo se
deshace con el botón de al lado. `POST /padron/` sigue respondiendo `405`: lo que escribe
son dos rutas propias, no la pantalla.

Carga masiva en `/carga/`. En el admin: *Estudiantes* —listado con estado, código de tarjeta
y si tiene fotografía; búsqueda por nombre, documento, código o acudiente; alta individual
con autocompletado; acciones de **reasignar el código** y **dar de baja**, las dos con
confirmación—, *Acudientes* de solo consulta, y *Usuarios* para dar de alta al personal,
desactivarlo, reactivarlo y reenviarle la invitación.

Y *Restricciones por estudiante*, **solo consulta** (`HU-38`): la misma pantalla que ve la
administración de la cafetería. Las restricciones son del acudiente, también para el
colegio (`INV-4`, `HU-13`).

### Administración de la cafetería (`USR-4`)

En el admin: productos con precio, categoría, ocho campos nutricionales por porción
(`./campos-nutricionales.md`), alérgenos declarados e imagen; categorías; alérgenos.
Acciones de retirar y devolver al catálogo. **Nada se borra**: retirar es un estado.

*Restricciones por estudiante* (`HU-38`, `TT-112`): de cada estudiante, su límite diario,
los productos bloqueados y los alérgenos bloqueados. **Solo se consultan**: las configura
y las retira el acudiente (`INV-4`). Enseña el nombre y el estado, **no el documento, ni el
código de tarjeta, ni el acudiente** — la cafetería consulta restricciones, no administra
estudiantes. El documento se puede buscar, pero solo completo.

Desde `HU-27`, también el **inventario**: el listado de productos trae una columna de
existencias —calculada sumando el historial, no guardada (`INV-3`)— y *Movimientos de
inventario* registra el ingreso de mercancía por ajuste manual. Ese libro **se lee y se
le añaden asientos, pero no se edita ni se borra**: un asiento corregido a posteriori
deja unas existencias que ya no explican lo que pasó. Un error se corrige con otro
movimiento.

**Y los tres reportes de la operación**, los tres en el admin y los tres con la misma
forma: el listado de siempre con filtros y navegación por fechas, y encima **el consolidado
de lo que se está mirando**. Ventas (`HU-35`), movimientos de inventario (`HU-36`) y cierres
de caja (`HU-56`). Ninguno abre una pantalla nueva y ninguno se escribe desde ahí.

El de cierres es el que más conviene saber leer: enseña **el descuadre total** del periodo y
no solo la suma con signo, porque esa se compensa sola y un mes con veinte descuadres se
leería como un mes que cuadra. Y cada cierre **enlaza a las ventas en efectivo de su
jornada**, que es lo que permite comprobar de dónde sale su efectivo esperado (`INVD-5`) en
vez de creérselo.

**Y el cuarto reporte, que es el que se abre cuando algo no cuadra**: la auditoría
(`HU-37`), en `/admin/auditoria/`. Una sola línea de tiempo con las cuatro clases de
operación, con quién hizo qué y cuándo, y cada renglón enlazado a su propio reporte. Los tres
consolidados llevan el enlace, para no tener que saberse la URL.

### Acudiente (`USR-2`)

`/mis-estudiantes/`, y desde ahí `recargar` la billetera de cada uno (`HU-06`): el pago
es simulado y la pantalla lo dice, pero **el movimiento queda asentado de verdad** en el
historial del que sale el saldo (`INV-2`). **Ni al desactivado ni al de baja se les
recarga** (`DEC-14`, `INVD-7`, `HU-52`): la tarjeta desactivada está perdida y engordar su
saldo no es inocuo cuando el sistema no sabe devolver dinero (`ALC-OUT-01`); la del
retirado queda congelada como constancia. No se les ofrece, y el servicio lo rechaza igual
aunque se escriba la URL. La ficha dice lo que importa —**el saldo sigue siendo suyo**— para
que nadie lea el bloqueo como una pérdida.

Y **desactivar la tarjeta de su estudiante** (`HU-48`, `TT-122`), que es la otra vía de
`DEC-5`: el colegio bloquea de inmediato en mitad de la jornada, y el acudiente sin
depender del horario de secretaría. Solo alcanza a los suyos —un identificador ajeno es un
`404`, como en el resto de `INT-1`—, va con confirmación porque se usa desde el móvil, y
la ficha pasa a decir que la tarjeta está bloqueada y **a quién hay que pedirle que se
reactive**: eso es exclusivo de la institución (`INVD-3`) y no hay botón, ni ruta, ni
servicio que lo haga desde aquí. La asimetría es de seguridad —el desbloqueo pasa por una
verificación presencial— y es el segundo criterio de la historia. Quién desactivó **no se
guarda**: el criterio de `HU-49` dice «con independencia de quién», así que el dato no
cambiaría ninguna decisión y guardarlo invitaría a escribir algún día la regla contraria.

Y desde ahí los **alérgenos bloqueados** (`HU-11`, `TT-102`), que es lo que hay que usar
para una alergia: lo que se marca es **la condición**, no los productos que hoy la llevan,
así que lo que la cafetería agregue el mes que viene queda fuera solo. La pantalla enseña
cuántos productos lo declaran **hoy** —y dice «hoy»— porque esa cifra describe el catálogo
actual y el bloqueo no depende de ella (`INV-5`). Se puede bloquear un alérgeno que
todavía no declara ningún producto: el acudiente declara la alergia de su hijo, no el
menú.

Las **tres** pantallas del control parental llevan debajo **el historial de cambios** (`HU-12`,
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

Y `limite`, el **cupo diario de gasto** de cada estudiante (`HU-09`, `TT-96`), que desde
`HU-61` también se puede **retirar del todo** y no solo cambiar. Retirarlo borra la
restricción, nunca la pone en cero —un cupo de cero es «no puede gastar nada», lo
contrario— y queda asentado de cuánto era. La acción vive en su propio formulario y no
como un segundo botón del de guardar: en un formulario con dos envíos, el primero del DOM
es el que dispara Enter, y quien teclea una cifra se quedaría sin cupo en vez de
cambiarlo. Es por estudiante y no de la cuenta: un acudiente con tres hijos fija tres cupos
distintos. **Lo escribe solo él**, entre por donde entre —`INV-4`—, y **la caja lo hace cumplir**
desde `HU-20`: la compra que pase del cupo se rechaza aunque haya saldo. La pantalla lo
dice, y dice también lo que ahora hace falta saber —que el cupo cuenta lo gastado en el día
y vuelve a empezar al siguiente—; mientras no fue cierto, avisaba de lo contrario. A un estudiante de baja **sí** se
le puede configurar: fijar un cupo no mueve dinero, así que `INVD-2` no lo alcanza.

`/mis-estudiantes/`: sus estudiantes, con selector cuando tiene más de uno, **el saldo de
cada uno y sus últimos cinco movimientos** (`HU-07`). El saldo no es un campo guardado: se
calcula sumando el historial al pedir la página (`INV-2`), y el historial va debajo
precisamente para que la cifra se pueda comprobar. Si alguno está de baja, lo dice, y **su saldo sigue ahí**: congelado, sin poder recargarlo ni gastarlo, y con el aviso de que la devolución del dinero no se hace desde el sistema (`HU-52`, `ALC-OUT-01`). En la ficha están las seis cifras del estudiante, repartidas en cinco tarjetas —saldo,
cupo diario, productos bloqueados, alérgenos bloqueados, reservas sin recoger y compras
registradas— (`HU-07`, `HU-09`, `HU-10`, `HU-11`, `HU-23`, `HU-30`): **ya no queda ningún
hueco**. Lo que no hay se dice con palabras y nunca con un cero: «sin límite» y un
cupo de cero son lo contrario el uno del otro.

Y `consumo`, el **historial de consumo** de cada estudiante (`HU-30`, `TT-156`): qué compró,
cuándo, cuánto costó y **qué declaraba cada producto ese día**. Las cifras nutricionales salen
de la instantánea que la venta congeló (`DT-8`, `HU-22`), no del catálogo de hoy: corregir una
ficha o subir un precio no reescribe lo que un niño comió el mes pasado. Un producto sin ficha
técnica aparece como **hueco declarado** y nunca como una fila de ceros —el cero afirmaría que
no aporta nada, y nadie lo afirmó—. Las reservas entran en el historial porque **son ventas ya
pagadas** (`DT-32`), y las que siguen en el mostrador se marcan «sin recoger» para que no se
lean como consumidas.

En esa misma pantalla están las **alertas de frecuencia** (`HU-31`, `TT-160`): en cuántos
días distintos de los últimos catorce aparece cada categoría. **Se cuentan días, no
unidades** —dos compras del mismo martes son un día— y el umbral es el mismo para todas las
categorías, porque uno más bajo para `Snacks` que para `Frutas` sería afirmar que una
conviene menos, que es la valoración nutricional que `ALC-OUT-20` excluye. Las reservas
cuentan **el día en que se recogen**, no el día en que se pagan: la regla habla de consumo.
Cada alerta enseña su umbral para que se pueda comprobar contra el historial que tiene
debajo, que es lo que la hace determinística a ojos de quien la lee (`OBJ-E3`). Las reglas
y sus números están en `./reglas-de-frecuencia-de-consumo.md`.

Y debajo, el **aporte nutricional** (`HU-32`, `TT-164`): lo que aportó, en promedio, **un día
en que compró en la cafetería** —no el periodo entero, porque la referencia de la norma es
diaria— frente a la tabla del **artículo 15 de la Resolución 810 de 2021** del Ministerio de
Salud, columna «niños mayores de 4 años y adultos». Se usa esa columna y no la recomendación
por edad y sexo de la Resolución 3803 de 2016 **a propósito**: elegir la fila según la edad
del estudiante individualiza la referencia, y eso es `ALC-OUT-20`. La pantalla lo dice con
todas las letras —«no es lo que necesita: es el valor que la norma manda imprimir en
cualquier etiqueta»—, y declara las otras dos salvedades: que la cafetería no es toda la
dieta, y que los azúcares del catálogo son totales mientras la norma fija un máximo de
añadidos, así que la cifra señala de más y nunca de menos. Un producto sin ficha
**queda fuera del agregado y se dice cuántos renglones quedaron fuera**, porque un agregado
que se calla lo que excluyó se lee como si estuviera completo. La tabla, su fuente y lo que
no se pudo confirmar están en `./valores-de-referencia-nutricional.md`.

Y el **resumen de gasto** (`HU-33`, `TT-166`): lo recargado contra lo gastado en el mismo
periodo, sacado del libro de movimientos del que sale el saldo —no hay ningún dato nuevo que
capturar (`INV-2`, `DT-4`)—. **Sus fechas son las de los movimientos, no las del consumo**, y
esa es la única diferencia de calendario de la pantalla: el dinero de una reserva sale al
reservar y la comida se consume al recogerla, así que un pedido pagado el domingo es gasto
del domingo y consumo del lunes. El **saldo** que acompaña a las dos cifras no es del
periodo: es la suma de toda la vida de la billetera, y decirlo evita la resta mental que no
cuadra. Y si se gastó más de lo recargado en esos días, la pantalla aclara que **eso no es
una deuda**: `INV-1` no deja que una compra deje el saldo en negativo, así que lo que pasó es
que tiró del saldo que ya tenía.

Y con ellas el **aviso de carácter orientativo** (`HU-34`, `TT-161`, **`INV-9`**), que no es
un párrafo suelto: el descargo y las alertas son el mismo fragmento de plantilla, así que
quien enseñe las alertas en otro sitio se lo lleva con ellas. Se pinta **haya alertas o no**
—decir «ninguna categoría llega al umbral» sin él se leería como «todo está bien», que es
una valoración igual que la contraria—.

Entra desde el teléfono (`INT-1`), así que la pantalla se diseña a 390 px primero: la barra
lateral no se colapsa ahí, se abre como un cajón sobre el contenido.

### Cajero (`USR-3`)

`/punto-de-venta/`, más la cola de reservas (`HU-24`) y el cierre de caja de la jornada
(`HU-55`). Cualquier otro rol recibe `403` en el punto de venta aunque escriba la URL
(`DT-11`), y él no entra al admin — `[S11]` le concede registrar ventas, y registrar ventas
ocurre entero aquí. La pantalla
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

**Y rechaza lo que el acudiente prohibió** (`HU-60`, `HU-18`): el producto bloqueado y
cualquiera que declare un alérgeno bloqueado. El alérgeno se cruza **al cobrar** con lo
que cada producto declara, así que cubre lo que la cafetería agregó esta mañana sin que
nadie recalcule nada (`INV-5`). Se rechaza con saldo de sobra, no se descuenta nada y **el
cajero no tiene ninguna acción para omitirlo** (`INV-4`): la única salida es que el
acudiente retire la restricción, que deja asiento. Es el escenario crítico **`TST-1`**.

**Y no le vende a quien no puede comprar** (`HU-50`, `INVD-2`): un estudiante desactivado
o de baja se identifica igual —decir «esa tarjeta no es de nadie» sería mentir— pero la
venta se rechaza **lo primero**, antes de mirar restricciones o saldo, porque con la
tarjeta bloqueada da igual lo que lleve el carrito. Es el único motivo que no se arregla en
el mostrador: ni quitando un renglón ni recargando, hay que pasar por secretaría (`HU-49`).

**Y rechaza la compra que pase del cupo del día** (`HU-20`, `HU-09`): el consumo de la
jornada se compara con el límite **dentro del mismo bloqueo** donde se lee el saldo, y sale
del mismo libro (`INV-2`) — no hay contador diario que alguien tenga que poner a cero. Se
rechaza aunque haya saldo de sobra, y el motivo se distingue del de saldo porque se
arreglan de forma opuesta: una recarga no devuelve cupo. Es la otra mitad del escenario
crítico **`TST-2`**, cuya primera cerró `HU-19` en el Sprint 2.

**La venta evalúa ya todas sus reglas, en un orden que es una decisión**: puede comprar,
alérgeno, producto bloqueado, existencias, cupo del día y saldo — todas dentro de la misma
transacción. Lo que no se arregla en el mostrador va delante; lo que sí —quitar un renglón,
recargar— va detrás, para que el cajero lea el motivo que de verdad explica el rechazo.

**Y al terminar la jornada cuadra la caja** (`HU-55`, `DEC-6`). La pantalla le enseña **el
efectivo esperado calculado desde las ventas registradas** —y de cuántas ventas sale, para
que pueda ir a comprobarlo— y le pide lo que cuenta: el efectivo del cajón y la base que
dejó para dar cambio. Si la diferencia no es cero, **el motivo es obligatorio**, con el
mismo criterio que `ALC-IN-18` aplica a la merma.

**No hay campo para el efectivo esperado, y esa ausencia es `INVD-5`.** `PA-7` describe que
hoy la cafetería cuadra contra **su estimación** de lo vendido; si la cifra se pudiera
escribir, el sistema habría cambiado el papel por una pantalla y nada más. **Las
transferencias quedan fuera del cuadre**: ese dinero fue de banco a banco y nunca pasó por
el cajón. Y el cuadre es **uno por jornada**, no uno por cajero: un cierre por turno sería
el módulo de turnos que `DEC-6` descarta. Está todo en `./reglas-del-cierre-de-caja.md`.

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
   el cupo es de uno y no del otro. `HU-09`. Más adelante, en la caja, se intenta cobrar
   por encima de ese cupo **con saldo de sobra**: la venta se rechaza y el motivo dice que
   recargar no lo cambia. Es el escenario crítico **`TST-2`** (`HU-20`).
6. **Bloquear un alérgeno** desde la tarjeta de restricciones. Luego, como administración,
   **crear un producto nuevo que lo declare**: queda cubierto sin volver a tocar nada. Es
   `INV-5` enseñada en vivo, y el paso que más conviene no saltarse en la Sprint Review.
   `HU-11`. Desde el mismo admin, *Restricciones por estudiante* enseña ese alérgeno
   bloqueado, y la ficha no ofrece guardar nada. `HU-38`.
   **Y en la caja, intentar cobrar ese producto recién creado**: la venta se rechaza con
   saldo de sobra, diciendo qué alérgeno lo bloquea, y no hay forma de forzarla. Es el
   escenario crítico **`TST-1`** (`HU-18`), y es la demostración que cierra el argumento
   del paso anterior.
7. **Retirar uno de los bloqueos** y mirar «Cambios recientes» debajo: queda anotado
   quién lo retiró y cuándo, y el bloqueo anterior también está. `HU-12`.
   Desde la pantalla del cupo, **Retirar el límite** hace lo mismo con el límite diario y
   anota de cuánto era. `HU-61`, `DEC-13`.
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
19. **Como administración, registrar una merma** desde *Mermas*: se intenta **sin motivo** y
    no entra. Lo que hay que decir es que el rechazo no es del formulario, **es de la base de
    datos**: `TT-140` lo comprueba escribiendo por el ORM. `HU-28`, `INV-8`.
20. **Pinchar la cifra de existencias** de ese producto en el catálogo: sale su historial con
    una columna de existencias tras cada movimiento, y hay que seguirla hasta el total de
    arriba. Es el escenario crítico **`TST-4`**, y con él los cuatro de `ENT-05` quedan
    demostrados. `HU-29`, `INV-3`.
21. **Como acudiente, reservar** desde la tarjeta *Reservas* de su estudiante: se eligen
    cantidades y se paga. **El saldo baja al reservar**, no al recoger, y queda en el
    historial. `HU-23`.
    Antes de eso conviene **bloquear un producto y tratar de reservarlo**: la reserva se
    rechaza igual que la venta, porque pasa por la misma validación. Ninguno de los criterios
    de `HU-23` lo menciona, y es el punto que más dice del diseño.
22. **Como cajero, *Reservas***: la cola de lo que hay que preparar, de lo más antiguo a lo
    más reciente. `HU-24`.
23. **Escanear la tarjeta de ese estudiante** en el punto de venta: su pedido sale **antes
    del saldo**. Pulsar *Entregar* y comparar: **el saldo no se mueve** y las existencias sí.
    Intentarlo otra vez lo rechaza. `HU-25`.
24. **Volver a entrar como acudiente**, tarjeta *Consumo* → **Ver el historial**: ahí está
    todo lo comprado en los pasos anteriores, con lo que cada producto declaraba ese día.
    Para cerrar el argumento, **cambiarle el precio a un producto ya vendido** desde la
    administración y recargar la pantalla: la compra sigue diciendo lo que costó entonces.
    Es `DT-8` enseñada en vivo, y es lo que convierte el historial en un historial. `HU-30`,
    `HU-22`.
25. **Arriba, en esa misma pantalla, las alertas de frecuencia** (`HU-31`), el **aporte
    nutricional** (`HU-32`) y el **gasto frente a lo recargado** (`HU-33`). Con una demostración corta no saldrá ninguna alerta —hacen
    falta cinco días distintos de la misma categoría—, y eso también se enseña: la pantalla
    dice qué umbral no se alcanzó, **no dice que la alimentación vaya bien**. El aporte sí
    sale con una sola compra, con su porcentaje y **con la norma citada debajo**. Lo que
    está siempre es el descargo de `INV-9` (`HU-34`), con o sin recomendaciones. Para ver
    las alertas de verdad hay que sembrar el historial: el atajo está en `[S2.12]` de
    `./desarrollo.md`.
26. **Como cajero, *Cierre de caja***: la pantalla enseña el efectivo esperado de la jornada
    y **de cuántas ventas sale**. Conviene enseñarlo después del paso 18, que es el que mete
    efectivo en la caja — y comparar: **la venta por transferencia no está ahí dentro**, ni
    las compras de los estudiantes. Se cuenta un billete de menos a propósito: sin motivo, la
    pantalla no deja cuadrar. Es el paso que más dice del proyecto en la sustentación, porque
    `PA-7` describe que hoy la cafetería cuadra contra **su estimación** de lo vendido, y aquí
    no hay ninguna casilla donde escribirla. `HU-55`, `DEC-6`, `INVD-5`.
27. **Como administración, *Ventas* → «¿Algo no cuadra?» → la auditoría.** Sale la jornada
    entera en una línea de tiempo: quién cobró, quién reservó, quién entregó y quién cuadró
    la caja, cada renglón enlazado a su reporte. Es el paso que cierra el argumento del
    anterior — el descuadre se explica yendo a las operaciones, no preguntando—. Y conviene
    enseñar lo que **no** dice: el ingreso de mercancía y la merma no registran quién,
    porque el libro de inventario no guarda el actor, y la pantalla lo declara en vez de
    dejar el hueco en blanco. `HU-37`, `ALC-IN-22`.

---

## [S6] Qué está construido, y qué no lo estará

**Nada del producto.** Con `HU-37` quedan terminadas **las 61 historias del proyecto**: lo
que viene después del Sprint 5 es entrega, no desarrollo.

**El reporte de auditoría ya está** (`HU-37`, `TT-177`, `TT-178`): una línea de tiempo con
ventas, entregas de pedidos, movimientos de inventario y cierres, construida sobre los libros
que ya existen y **sin ninguna tabla de auditoría**. Con él, `ALC-IN-22` queda cubierto
entero — los tres reportes que nombra, más este.

**Lo que no puede decir, y lo dice**: quién registró un ingreso o una merma. El libro de
inventario no guarda el actor. Está declarado en el `ANEXO B` de
`./decisiones-de-alcance.md` y conviene recogerlo en `ENT-06` como limitación identificada.

**El cierre de caja ya está, y su reporte también** (`HU-55`, `HU-56`, `TT-171` … `TT-176`):
el cajero cuadra la jornada contra las ventas en efectivo registradas, con el esperado
**calculado y nunca digitado** (`INVD-5`), las transferencias fuera del cuadre y motivo
obligatorio si hay diferencia; y la administración consulta el histórico con el descuadre del
periodo y el enlace que explica cada cifra esperada.

**El de movimientos de inventario ya está** (`HU-36`, `TT-169`, `TT-170`): el mismo libro del
admin, ahora con navegación por fechas y el consolidado del periodo —entradas, salidas, neto
y desglose por tipo—, más el recuento de mermas sin motivo que hace visible `INV-8`.

**El reporte de ventas ya está** (`HU-35`, `TT-167`, `TT-168`): el libro filtrable en el
admin, con el consolidado del periodo que se mira y sus desgloses por medio de pago y por
origen. Incluye las ventas genéricas y las reservas, porque son actividad comercial del
servicio igual que las demás.

**`EPI-8` está cerrada para el acudiente**: qué compró, con qué frecuencia, cuánto aportó
frente a la referencia oficial y en qué se fue el dinero. Lo que falta de reportes es de la
cafetería, no de la familia.

**El historial de consumo ya está** (`HU-30`, `TT-155` … `TT-157`): el acudiente ve qué
compró su hijo, renglón a renglón, **con la información nutricional del día de la compra**.

**Y las alertas de frecuencia también** (`HU-31`, `HU-34`, `TT-158` … `TT-161`): en cuántos
días distintos de los últimos catorce aparece cada categoría, con el mismo umbral para
todas —clasificarlas por lo saludables que son sería `ALC-OUT-20`— y con el descargo de
`INV-9` en el mismo fragmento, de modo que no hay forma de publicar una recomendación sin
él.

**Y la comparación con la referencia sanitaria** (`HU-32`, `TT-162` … `TT-164`): lo que
aportó, en promedio, un día de cafetería, frente a los valores diarios del **artículo 15 de
la Resolución 810 de 2021** del Ministerio de Salud. La cita está en pantalla, no solo en el
documento: sin ella la cifra es un número que hay que creerse.

**El inventario ya es trazable y los pedidos anticipados funcionan de punta a punta.** Toda
merma lleva motivo y lo impone la base (`HU-28`, `INV-8`); las existencias de cualquier
producto se desglosan renglón a renglón hasta el total (`HU-29`, `TST-4`); y el acudiente
reserva, la cafetería consulta y el cajero entrega sin volver a cobrar (`HU-23`, `HU-24`,
`HU-25`), que es `FUN-5` entero.

**Con `TST-4` quedan demostrados los cuatro escenarios críticos de `ENT-05`.**

**El control parental está completo: las tres restricciones se configuran y las tres
frenan la venta.** El producto bloqueado (`HU-60`), el alérgeno (`HU-18`, escenario
crítico `TST-1`) y el cupo del día (`HU-20`, `TST-2`) se rechazan dentro de la
transacción, sin descontar saldo ni existencias y sin ninguna acción que los omita
(`INV-4`). **Ya no queda en el sistema ninguna marca de «esto todavía no lo aplica la
caja»**, y hay pruebas que exigen su ausencia.

**El alérgeno se rechaza por la condición, no por una lista.** Se cruza al cobrar con lo
que cada producto declara (`INV-5`, `DT-7`): un producto nuevo con maní queda rechazado
desde el momento en que lo declara, y retirar la declaración lo devuelve a la normalidad.
Ninguna lista de productos prohibidos existe en ninguna parte, y esa ausencia es la
invariante.

`HU-60` no estaba en la planeación del sprint: se añadió al descubrirse, construyendo
`HU-10`, que `ALC-IN-09` pide aplicar las restricciones en la venta y ninguna historia lo
hacía para esa lista.

**El punto de venta vende.** Identifica por las dos vías (`HU-15`, `HU-16`), enseña la
fotografía (`HU-58`), el medio de pago (`HU-54`), y cobra descontando saldo y existencias
en una sola transacción (`HU-21`). **`HU-17` quedó cerrada con `TT-109`**: el panel enseña
los tres datos que su primer criterio pide —saldo, consumo del día y restricciones
vigentes—, y el tercero no existía hasta este sprint.

El bloque de restricciones nombra cada una y dice **si la caja la hace cumplir**: las
tres, desde `HU-20`. Las dos advertencias temporales —alérgeno y cupo— se retiraron con la
historia que las hizo falsas, y hay pruebas que exigen que ya no estén: una marca que
sobrevive a su historia miente igual que mentiría su ausencia cuando era cierta.

**El dinero del acudiente está completo, y el círculo se cierra**: recargar (`HU-06`), el
saldo derivado del historial (`HU-08`, `TST-3`), verlo en su panel (`HU-07`) y gastarlo —en
la caja (`HU-21`) o reservando por adelantado (`HU-23`)—. Cada gasto vuelve al panel como
movimiento, y el saldo sigue siendo su suma y nunca una cifra guardada (`INV-2`).

La app `reportes` **ya existe** (`TT-155`), y con ella están las ocho del proyecto: cada
una se creó en el sprint que la necesitó (`[S3]` de `./decisiones-tecnicas.md`). Entra **sin
modelos y sin migraciones**, porque un reporte es una lectura de hechos que otro dominio ya
asentó. `ventas` nació en `TT-57` para que la
pantalla tuviera dónde vivir y hoy tiene sus modelos (`TT-78`) y **su servicio** (`TT-80`):
la venta con su medio de pago y su estudiante opcional, la línea de venta, y la transacción
única que sostiene `INV-1`, `INV-2` e `INV-3` a la vez. La línea congela además el precio y los
nutrientes que el producto declaraba al venderse (`TT-84`, `HU-22`): editar el catálogo
mañana no reescribe lo que se cobró hoy. `billetera` e `inventario` tienen los suyos desde `TT-59` y
`TT-67`, y **ninguno es una columna `saldo` ni `existencias`**; desde `TT-78` los dos
señalan además la venta que origina cada movimiento.
