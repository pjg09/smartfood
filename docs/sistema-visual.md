# SmartFood — Sistema visual

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-SISTEMA-VISUAL |
| titulo | Las composiciones de la interfaz: qué existe, de dónde se copia y qué no inventar |
| tipo_documento | Documento operativo. **No es un artefacto de Scrum ni un entregable** |
| documentos_fuente | `./decisiones-tecnicas.md` (`DT-16`, `DT-23`, `DT-25`); `./mapa-de-la-aplicacion.md`; `estilos/fuente.css` |
| actualizado | 2026-09-19; el Sprint 5 estrenó otras dos —`[S2.8]` y `[S2.9]`— en los reportes: el medidor del acudiente y el consolidado del admin |
| cubre | `TT-05` — armazones y hoja de estilos, más lo que `DT-25` fijó encima y lo que el control parental y los reportes añadieron |
| responsable | Carlos (plantillas y estilos) |
| idioma | es-CO |
| version | 1.2 |

### [S0.1] Qué responde este documento

Una sola pregunta: **voy a construir una pantalla nueva, ¿qué copio y de dónde?**

`DT-23` decidió *qué* sistema visual se adopta y `DT-25` declaró que adoptarlo incluye las
**composiciones**, no solo los colores. Lo que faltaba era el sitio donde mirar cuál es cada
una. Esto es ese sitio.

**Es un índice de punteros, no un catálogo de marcado.** Cada composición dice cuál es su
plantilla canónica y se copia de ahí. Duplicar el HTML aquí garantizaría que en dos sprints
este documento enseñe una versión que ya no existe — que es exactamente el fallo que `DT-25`
vino a evitar un piso más arriba.

> **Si una pantalla necesita algo que no está en `[S2]`, para.** Lo más probable es que ya
> exista con otro nombre. Lo segundo más probable es que la pantalla esté mal planteada. Que
> haga falta una composición nueva es lo tercero, y entonces se añade aquí al construirla.

### [S0.2] Mapa de secciones

| ID | Sección | Contenido |
|---|---|---|
| S1 | Antes de escribir una clase | Las tres reglas que no se negocian |
| S2 | Las composiciones | Qué existe y de dónde se copia |
| S3 | Los cuatro armazones | Qué pinta cada uno |
| S4 | Lo que no se dibuja | Descartes explícitos |

---

## [S1] Antes de escribir una clase

**1. Los colores viven en `estilos/fuente.css`, y solo ahí.** En una plantilla se usa el
alias de intención —`bg-superficie`, `text-texto`, `border-borde`, `text-error-fuerte`—,
nunca un hexadecimal ni la paleta de fábrica de Tailwind, que está borrada con
`--color-*: initial`. `bg-slate-500` **no pinta nada y no da ningún error**.
`config/tests_plantillas.py` vigila las dos reglas.

**2. Los puntos de ruptura son `tablet:`, `escritorio:` y `amplio:`.** `sm:` y `lg:` no
existen, y fallan igual de callados.

**3. El rojo y el ámbar significan algo.** Rojo es saldo insuficiente o alérgeno bloqueado
(`INV-1`, `INV-5`); ámbar es un límite a punto de agotarse o un estado que no es un fallo.
Para adornar están las cinco series (`serie-1` … `serie-5`), que no significan nada a
propósito. Gastar los de estado en decoración les quita fuerza donde hacen falta.

---

## [S2] Las composiciones

Doce, y diez tienen sección propia porque llevan una decisión o una trampa que hay que
conocer antes de copiarlas.

**Tres las usa una sola pantalla por ahora**, y se fijan igual. La **barra de filtros**,
porque el padrón estrenó a la vez el buscador que pide a cada tecla, el interruptor accesible
y el orden de los tres controles, y esas tres decisiones se toman una vez o se vuelven a
discutir en la siguiente pantalla que lleve una tabla. La **lista con cantidad**, porque es
una variante de la lista con interruptor y lo que la separa de ella —un solo envío en vez de
un gesto por fila— es justo lo que habría que volver a razonar en la próxima. Y el
**medidor de proporción**, porque lo que decide no es cómo se ve sino qué se recorta y qué
no, y eso hay que saberlo **antes** de dibujar el segundo.

| Composición | Se copia de | En una frase |
|---|---|---|
| Tarjeta de resumen | `templates/partials/estudiante-seleccionado.html` | Franja de serie arriba, icono en pastilla, rótulo, cifra en `font-display` y **enlace** de acento abajo |
| Tabla de datos | `templates/partials/estudiante-seleccionado.html` | Cabecera tintada con un icono por columna; **fichas por debajo de `tablet`** |
| Encabezado de sección | `templates/inicio.html` | Antetítulo en versalitas y acento, título en `font-display`, entradilla; centrado |
| Encabezado de pantalla | `templates/billetera/recarga.html` | `h1` y frase de apoyo, alineados a la izquierda, dentro del lienzo |
| Grupo de modos | `templates/partials/grupo-de-tema.html` | Botones con `aria-pressed`; icono **sobre** la etiqueta cuando la columna es estrecha |
| Bloque punteado | `templates/ventas/punto-de-venta.html` | Borde discontinuo, icono en pastilla, qué falta y **qué historia lo trae** |
| Barra de filtros | `templates/personas/padron.html` | Buscador con icono dentro, interruptor y acción **en una fila** desde `tablet`; apilados por debajo |
| Lista con interruptor | `templates/restricciones/partials/lista-de-productos.html` | Una fila por elemento, el estado pintado en el borde y el fondo, y un botón que dice **la acción**, no el estado |
| Lista con cantidad | `templates/ventas/reserva.html` | La fila de `[S2.6]` con un campo numérico en vez del interruptor; **un solo envío**, no un gesto por fila |
| Historial de cambios | `templates/restricciones/partials/historial-de-restricciones.html` | Lo último primero, con quién y cuándo; **dentro del fragmento que se intercambia**, nunca al lado |
| Medidor de proporción | `templates/reportes/partials/recomendaciones.html` | Barra fina bajo la cifra; **se recorta la barra a 100, nunca el número**, y el color no significa nada |
| Consolidado de reporte | `templates/admin/ventas/venta/change_list.html` | En el admin: cifra grande, la frase que dice de dónde sale, y tablas de desglose **completas** |

### [S2.1] Tarjeta de resumen

La acción va **abajo y es un enlace de acento con `mt-auto`**, no un botón sólido. En una
fila de tarjetas, un botón relleno es la pieza más pesada de la pantalla y se lleva la mirada
por delante de la cifra, que es a lo que se viene. `mt-auto` además iguala la altura de las
tarjetas aunque su texto mida distinto.

La franja superior usa una serie, **nunca `error`, `aviso` ni `exito`**: es decoración, y
esos tres significan algo (`[S1]`, regla 3).

**En el punto de venta la tarjeta va sin enlace y sin frase de apoyo**
(`templates/ventas/partials/estudiante-identificado.html`, `TT-75`). No es un descuido:

- No hay a dónde ir. Recargar es del acudiente (`HU-06`); ofrecérselo al cajero abriría una
  puerta que `[S11]` no le da.
- «Es la suma de sus movimientos» explica una cuenta a quien la consulta, no a quien cobra.
  Cuesta dos líneas por tarjeta, y a 1024 × 600 esas líneas empujan la cifra fuera de la
  vista. En una caja el texto que sobra tiene un precio medible: un gesto de scroll por
  venta.

Y ahí **la franja sí puede ser `error`**: un saldo en cero significa que no se le puede
cobrar nada (`INV-1`). Es la excepción que confirma la regla 3 — el color de estado se gasta
donde el estado existe, no como adorno.

**El segundo sitio sin enlace es el resumen de gasto** (`TT-166`), y por el mismo motivo:
no hay a dónde ir. Lo que explica esas tres cifras es el historial que está debajo, en la
misma pantalla. La regla que queda: **el enlace va cuando lleva a algo que no está a la
vista**; si el detalle ya está debajo, sobra.

### [S2.2] Tabla de datos

**Una tabla no se reflujar a 390 px sin volverse ilegible.** Desde `tablet` es una tabla con
la cabecera tintada; por debajo, cada fila es una ficha de dos franjas —arriba lo que se
busca de un vistazo, abajo el detalle sobre fondo hundido—.

**La misma partición en dos franjas vale para una columna estrecha, no solo para el móvil.**
El renglón del ticket del punto de venta (`TT-81`) la usa: en 20 rem no caben el nombre del
producto, su importe y tres botones en una línea, y lo que se recorta es siempre el nombre
—«Empa…»—, que es justo lo que el cajero lee para saber si se equivocó. Arriba el nombre y
el importe; abajo la cantidad y los gestos.

El icono de cada rótulo va **siempre antes del texto**, también en la columna alineada a la
derecha: invertirlo deja el icono descolgado.

Si la tabla desborda, desborda **dentro de su caja** (`overflow-x-auto`), nunca en la página:
un desbordamiento de página mueve la barra lateral y la cabecera. Los anchos mínimos se
eligen por número de columnas —`tabla-sm`, `tabla-md`— y no por pantalla.

### [S2.3] Grupo de modos

Botones con `aria-pressed`, no radios ni un `<select>`. Las opciones se ven todas a la vez y
se cambia con un toque.

**El icono va encima de la etiqueta cuando la columna es estrecha.** En la columna del punto
de venta, un icono al lado de la palabra deja el texto recortado —«Tarj…»—, que es justo lo
que dice qué hace el botón.

Quién está pulsado lo mueve `assets/js/interfaz.js`, no el servidor, siempre que la elección
viva en el navegador (el tema) o en otro control (los atajos de importe de la recarga). Un
botón que sigue pulsado mientras el campo dice otra cosa miente sobre lo que se va a enviar.

**Qué opciones hay, en cambio, lo decide el servidor cuando es una regla.** El medio de pago
del punto de venta (`TT-79`) es el caso: con un estudiante identificado, efectivo y
transferencia **no son opciones deshabilitadas, no son opciones** —`HU-54` y `DEC-1` dicen
que su compra sale de la billetera—, así que el grupo desaparece y queda la afirmación de lo
que va a pasar, con su motivo. Calcularlo en el navegador pondría la regla en un tercer
sitio; el bloque llega repintado desde el servidor, en la misma respuesta de la
identificación (`hx-swap-oob`).

Esa es también la única excepción al montaje único de `interfaz.js`: un bloque que HTMX
reemplaza entero se lleva consigo el oyente que le cuelgue, así que este se delega desde
`document`. Sin error, sin aviso: los botones simplemente dejarían de responder tras el
primer escaneo.

### [S2.4] Bloque punteado

Es el hueco y el estado vacío. **Un hueco nunca es un botón deshabilitado**: una acción
apagada promete que un día hará algo y no dice cuándo ni de qué depende. El bloque dice qué
falta y qué historia lo trae —`HU-17`, `HU-21`—, que son las dos cosas.
`ventas/tests_acceso.py` lo vigila.

**También sirve para un dato que falta, no solo para una función que falta.** El estudiante
sin fotografía en el punto de venta (`TT-77`) lleva el mismo borde discontinuo en el sitio
donde iría la cara, con el rótulo «Sin foto». La alternativa —dibujar la silueta genérica
de la ficha del acudiente— le diría al cajero que la comprobación de identidad se hizo y
salió bien. **Un hueco silencioso miente; uno marcado, no.**

---

### [S2.5] Barra de filtros

Buscador, filtro y acción sobre una tabla, **en una sola fila desde `tablet`**: son las tres
cosas que se hacen sobre los datos de abajo, y leerlas juntas evita bajar la vista dos veces.
Por debajo se apilan, que es donde una fila de tres estrangula el campo.

**El buscador pide a cada tecla**, con 400 ms de espera, y reemplaza solo la tabla. Pero va
dentro de un `<form method="get">` de verdad, con su botón de envío en `sr-only`: sin
JavaScript sigue buscando al pulsar Enter, porque la vista lee el término de la URL venga de
donde venga. **HTMX acelera lo que ya funcionaba; no lo sustituye.**

El interruptor es un `<input type="checkbox">` con `sr-only` y el carril pintado desde `peer`.
No es un `<div>` con un `click`: así se enfoca con teclado y se alterna con espacio sin una
línea de JavaScript, y sin `role` ni `aria-checked` que mantener.

### [S2.6] Lista con interruptor

Un catálogo donde cada fila se enciende o se apaga: los productos bloqueados (`HU-10`) y los
alérgenos bloqueados (`HU-11`). **La misma composición en dos pantallas**, y por eso está
aquí: la segunda se copió de la primera en vez de inventarse.

**El estado se pinta en la fila entera** —borde y fondo en `error` cuando está bloqueado—, no
en un icono suelto: lo que el acudiente recorre es una lista larga, y el color de la fila se
lee sin detenerse en cada renglón. El rojo aquí significa lo que significa en todo el
sistema: una venta que se va a rechazar (`[S1]`, regla 3).

**El botón dice la acción, no el estado.** «Desbloquear» sobre uno bloqueado. Un botón que
dice el estado deja a quien lo lee sin saber qué pasa si lo pulsa; el estado ya lo dicen el
borde, el fondo y el texto de al lado.

Cada fila es un `<form>` con `hx-post` que devuelve **la lista entera**, no la fila: el
recuento de arriba y el historial de abajo cambian con cada gesto, y un intercambio por fila
los dejaría desfasados.

### [S2.6.1] Lista con cantidad

La variante de `[S2.6]` para cuando lo que se elige no es sí o no, sino cuántos: la reserva
anticipada (`HU-23`). **Misma fila** —nombre y precio a la izquierda, control a la derecha,
borde y fondo de superficie— cambiando el botón por un `<input type="number">`.

**Un solo envío, no un gesto por fila.** La lista con interruptor pide a cada clic porque
cada bloqueo es una decisión que vale por sí sola y hay que asentarla. Aquí no: las
cantidades son un único acto de compra, y enviarlas una a una cobraría por partes algo que
el acudiente piensa entero. Por eso el formulario es clásico y no lleva HTMX — no hay nada
que refrescar entre gesto y gesto.

**No es el carrito del punto de venta.** Aquel vive en la sesión (`DT-26`) porque el cajero
monta la venta gesto a gesto con una fila delante; aquí no hay fila y no hace falta estado
de servidor.

**El `max` de cada campo es lo que queda sin apartar**, no las existencias: ofrecer más de lo
que el servicio va a aceptar es enseñar un rechazo antes de tiempo. Y lo que se escribió se
devuelve escrito cuando hay un rechazo — quien acaba de leer un motivo no debería teclear
otra vez lo mismo.

### [S2.7] Historial de cambios

Lo que se hizo y quién lo hizo, debajo de la pantalla que lo hace: las tres del control
parental lo llevan (`HU-12`, `TT-105`). Lo último primero, que es como se lee un historial.

**Va DENTRO del fragmento que HTMX intercambia**, nunca al lado. Fuera se queda enseñando lo
de antes, y en un registro de auditoría eso es peor que no enseñarlo — `hx-swap-oob` tampoco
sirve: solo funciona en elementos de primer nivel de la respuesta y anidado falla en
silencio.

**Guarda el nombre tal como estaba** (`DT-8`): renombrar el catálogo no reescribe lo que el
acudiente vio al decidir. Y anota el bloqueo además del retiro, porque media historia no
reconstruye nada — «se retiró el bloqueo de maní el día 3» no dice si el niño estuvo
protegido antes.

### [S2.8] Medidor de proporción

Una cifra y, debajo, una barra fina que dice qué parte de una referencia representa: el
aporte nutricional frente a los valores diarios del etiquetado (`HU-32`, `TT-164`).

**Se recorta la barra a 100, nunca el número.** Un 140 % con la barra llena dice la verdad;
recortar también la cifra escondería justo el caso que más dice. El recorte se hace en el
selector y no en la plantilla — una plantilla de Django no compara.

**El ancho va en un estilo en línea, y es la única excepción del proyecto.** Tailwind compila
lo que encuentra **escrito** en las plantillas, y un ancho que sale de un dato no existe
hasta que corre la consulta: `w-[47%]` no se puede generar. No es una licencia para volver a
los estilos en línea en cualquier otro sitio.

**El color no significa nada, y ahí está el cuidado.** Se usa `serie-1` y no `serie-2`:
la segunda es naranja y a tamaño de barra **se lee como un aviso**, que es exactamente lo
que una comparación nutricional no puede decir (`ALC-OUT-20`). Las series no significan nada,
pero se parecen a cosas que sí.

### [S2.9] Consolidado de reporte

Los reportes de la cafetería viven en el admin (`HU-35`, `HU-36`, `HU-56`), así que **no
llevan Tailwind**: el admin no lo carga (`DT-23`). Se usan sus clases y estilos en línea, como en
`admin/catalogo/producto/historial.html`.

La forma es siempre la misma: **la cifra grande**, al lado **una frase que dice de dónde
sale** —y que cambia con los filtros de la pantalla—, y debajo **tablas de desglose**.

Tres decisiones que se copian con ella:

- **Las tablas de desglose llegan completas**: una categoría sin datos sale en cero, no
  desaparece. Que no se cobrara nada por transferencia es un dato del periodo; una fila
  ausente se lee como si el medio no existiera.
- **Sin datos no se pinta un cero**, se dice que el filtro no alcanzó nada. Un «$0» se lee
  como «se vendió cero», que es otra cosa.
- **La cifra grande es la que no se compensa sola.** En el reporte de cierres conviven dos
  descuadres —la suma con signo y la suma de valores absolutos—, y arriba va la segunda: con
  la primera, un sobrante y un faltante iguales dan cero y un periodo con veinte descuadres
  se lee como uno que cuadró. La otra se dice al lado, nombrando la diferencia.
- **Ninguna cifra cruda.** El admin pinta un `DecimalField` como el `Decimal` que es
  —«31500,00»—, así que una columna de dinero sin `dinero` deja dos formatos en la misma
  fila. Se vio en la captura de `TT-176`, como antes en `LineaVentaInline`.
- **Sin `<h1>` propio**: el admin ya pinta `title` del contexto como encabezado. Lo que sí
  se cambia es ese `title` desde `changelist_view`, porque el de fábrica —«Seleccione venta
  para ver»— describe lo que se hace con una tabla, no lo que es la pantalla.

---

## [S3] Los cuatro armazones

Todos cuelgan de `templates/base.html`, que solo pone `<head>`, tema e iconos.

| Armazón | Qué pinta |
|---|---|
| `base-publica.html` | Cabecera flotante que se opaca al bajar, y pie. Solo la portada |
| `base-acceso.html` | Dos columnas: panel de marca oscuro y formulario. Entrar y definir contraseña |
| `base-aplicacion.html` | Barra superior flotante, barra lateral oscura colapsable y cajón de móvil |
| `base-punto-de-venta.html` | Pantalla completa, columna de iconos que **no se despliega**, foco permanente |

**Una vista HTMX devuelve un fragmento, nunca una página** (`DT-16`). Los fragmentos viven en
`templates/partials/` y en `templates/<app>/partials/`.

---

## [S4] Lo que no se dibuja

- **Un botón deshabilitado en lugar de un hueco.** Ver `[S2.4]`.
- **Un diálogo de confirmación en el punto de venta.** `INT-2` los descarta: cada uno cuesta
  un clic y un segundo por venta, y roba el foco —que es del lector—. El botón de cobrar
  cobra (`TT-81`). Lo que protege de un cobro accidental no es un modal: es que el ticket
  diga después exactamente qué se cobró.
- **Una opción que la base va a rechazar**, ni siquiera apagada. Si no aplica, no se dibuja:
  ver `[S2.3]`. La diferencia con un hueco es que un hueco declara algo que llegará, y esto
  no va a llegar nunca — el efectivo no es un medio de pago pendiente para un estudiante.
- **Un color de estado como adorno.** Ver `[S1]`, regla 3.
- **Una recomendación sin su descargo.** `INV-9`. Y no se resuelve poniendo un párrafo en la
  pantalla: las recomendaciones y el aviso son **el mismo fragmento**
  (`templates/reportes/partials/recomendaciones.html`), de modo que quien las reutilice se
  lo lleve con ellas. El aviso se pinta **haya recomendaciones o no** — decir «ninguna
  categoría llega al umbral» sin él se lee como «todo está bien», que es una valoración
  igual que la contraria (`ALC-OUT-20`).
- **Una cifra de dinero formateada fuera de `billetera/templatetags/dinero.py`.** Ni en
  JavaScript ni en una plantilla: con dos formateadores, el día que cambie el formato la
  misma pantalla enseña dos monedas.
- **Un dato que el sistema todavía no tiene, puesto a cero.** Un saldo en cero y un saldo que
  no existe no son lo mismo, y en la caja esa confusión cuesta una venta mal cobrada.
- **Una fotografía de una persona real.** `INVD-6`. Los avatares se generan en el seed y los
  huecos de imagen los cubre la clase `lamina`.
- **Un retrato en redondo donde la cara es el dato.** En la ficha del acudiente la
  fotografía es identidad visual y va circular; en el punto de venta (`TT-77`) es lo que se
  compara con la persona que está enfrente, y el recorte circular se come las sienes y las
  orejas. Va cuadrada, por la misma razón por la que un carné no la lleva en redondo.
- **Un `<img>` con el `src` vacío** cuando no hay imagen. El navegador pide la página a sí
  misma y deja un icono de imagen rota justo donde debería estar el dato.

---

## [ANEXO A] Las ocho trampas que ya se pagaron

Las ocho fallan **en silencio**: no dan error, y la pantalla simplemente se ve mal.

| Trampa | Qué pasa | Salida |
|---|---|---|
| Variante sobre una clase de `@layer components` | `escritorio:rejilla-caja` no se compila; la pantalla se queda en una columna | El punto de ruptura va dentro de la clase, en `fuente.css`. Si el efecto sí depende de un estado, se escribe con utilidades |
| `@container` en el mismo elemento que la rejilla | Un elemento nunca es su propio contenedor: las consultas no encuentran contra qué medirse | `@container` va en el envoltorio |
| `@container` puesto **demasiado arriba** | Peor que la anterior, porque sí hay contra qué medirse: la rejilla mide el lienzo entero y no su columna. El catálogo se partía en dos columnas de 145 px y los nombres salían «Empanada d…» | El contenedor es el ancestro **más cercano**: cada zona que responda a su propio ancho lleva el suyo |
| `tailwind build` sin `--force` | Compara la fecha de `fuente.css`, no la de las plantillas; contesta «up to date» y la clase nueva no está | `--force`, o `tailwind watch` en otra terminal |
| `{% now "F" %}` | Devolvía el mes capitalizado porque el catálogo `es_CO` de Django lo capitaliza. Lo corrige `locale/es_CO/` | El `\|lower` se conserva: ese parche es temporal por diseño y las fechas no deben depender de él |
| `floatformat:"-2"` sobre una cifra ya redondeada | Vuelve a poner dos decimales: «12,40 g» donde el selector había dejado «12,4 g». Con cuántos decimales se enseña algo se decide **en un sitio**, y si ya lo decidió el selector, la plantilla no lo toca |
| Una anchura que sale de un dato | Tailwind compila lo que encuentra **escrito** en la plantilla: `w-[47%]` calculado no existe hasta que corre la consulta, y la barra sale sin ancho. Es la única excepción del proyecto al estilo en línea (`[S2.8]`) |
| Fragmento HTMX que aterriza bajo el pliegue | En una columna con `overflow-y-auto`, lo que devuelve el intercambio puede nacer fuera de la vista — y `autofocus` mantiene el scroll donde está el campo | `hx-swap="… show:top"`, que sube el destino. Reordenar la columna **no** sirve: el foco vuelve a arrastrar el scroll |

La del fragmento bajo el pliegue se pagó en `TT-75`. Conviene saber la medida, porque la pantalla de `INT-2` no da
para más: **a 1024 × 600 la columna del estudiante deja 317 px visibles y la caja de
búsqueda ocupa 298**. Todo lo que un fragmento traiga nace por debajo del pliegue, así que
en el punto de venta un intercambio HTMX que no suba su destino es un intercambio que el
cajero no ve.

Para mirar una pantalla sin abrir el navegador, la receta está en `[S5.2]` de
`./desarrollo.md`. **No es opcional**: `DoD-4` está vigente y pide demostrar lo que el PR
entrega ejecutándolo, y en los Sprints 4 y 5 mirar la pantalla encontró **diez defectos** que
ninguna prueba vio — uno de ellos, de cifras.
