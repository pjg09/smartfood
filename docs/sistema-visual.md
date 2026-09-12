# SmartFood — Sistema visual

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-SISTEMA-VISUAL |
| titulo | Las composiciones de la interfaz: qué existe, de dónde se copia y qué no inventar |
| tipo_documento | Documento operativo. **No es un artefacto de Scrum ni un entregable** |
| documentos_fuente | `./decisiones-tecnicas.md` (`DT-16`, `DT-23`, `DT-25`); `./mapa-de-la-aplicacion.md`; `estilos/fuente.css` |
| cubre | `TT-05` — armazones y hoja de estilos, más lo que `DT-25` fijó encima |
| responsable | Carlos (plantillas y estilos) |
| idioma | es-CO |
| version | 1.0 |

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

Seis, y son las que usan dos o más pantallas. No hay más porque no hacen falta más.

| Composición | Se copia de | En una frase |
|---|---|---|
| Tarjeta de resumen | `templates/partials/estudiante-seleccionado.html` | Franja de serie arriba, icono en pastilla, rótulo, cifra en `font-display` y **enlace** de acento abajo |
| Tabla de datos | `templates/partials/estudiante-seleccionado.html` | Cabecera tintada con un icono por columna; **fichas por debajo de `tablet`** |
| Encabezado de sección | `templates/inicio.html` | Antetítulo en versalitas y acento, título en `font-display`, entradilla; centrado |
| Encabezado de pantalla | `templates/billetera/recarga.html` | `h1` y frase de apoyo, alineados a la izquierda, dentro del lienzo |
| Grupo de modos | `templates/partials/grupo-de-tema.html` | Botones con `aria-pressed`; icono **sobre** la etiqueta cuando la columna es estrecha |
| Bloque punteado | `templates/ventas/punto-de-venta.html` | Borde discontinuo, icono en pastilla, qué falta y **qué historia lo trae** |

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

## [ANEXO A] Las seis trampas que ya se pagaron

Las seis fallan **en silencio**: no dan error, y la pantalla simplemente se ve mal.

| Trampa | Qué pasa | Salida |
|---|---|---|
| Variante sobre una clase de `@layer components` | `escritorio:rejilla-caja` no se compila; la pantalla se queda en una columna | El punto de ruptura va dentro de la clase, en `fuente.css`. Si el efecto sí depende de un estado, se escribe con utilidades |
| `@container` en el mismo elemento que la rejilla | Un elemento nunca es su propio contenedor: las consultas no encuentran contra qué medirse | `@container` va en el envoltorio |
| `@container` puesto **demasiado arriba** | Peor que la anterior, porque sí hay contra qué medirse: la rejilla mide el lienzo entero y no su columna. El catálogo se partía en dos columnas de 145 px y los nombres salían «Empanada d…» | El contenedor es el ancestro **más cercano**: cada zona que responda a su propio ancho lleva el suyo |
| `tailwind build` sin `--force` | Compara la fecha de `fuente.css`, no la de las plantillas; contesta «up to date» y la clase nueva no está | `--force`, o `tailwind watch` en otra terminal |
| `{% now "F" %}` | Devuelve el mes capitalizado, y en una fecha en español va en minúscula | `{% now "F" as mes %}` y luego `{{ mes\|lower }}` |
| Fragmento HTMX que aterriza bajo el pliegue | En una columna con `overflow-y-auto`, lo que devuelve el intercambio puede nacer fuera de la vista — y `autofocus` mantiene el scroll donde está el campo | `hx-swap="… show:top"`, que sube el destino. Reordenar la columna **no** sirve: el foco vuelve a arrastrar el scroll |

La quinta se pagó en `TT-75`. Conviene saber la medida, porque la pantalla de `INT-2` no da
para más: **a 1024 × 600 la columna del estudiante deja 317 px visibles y la caja de
búsqueda ocupa 298**. Todo lo que un fragmento traiga nace por debajo del pliegue, así que
en el punto de venta un intercambio HTMX que no suba su destino es un intercambio que el
cajero no ve.

Para mirar una pantalla sin abrir el navegador —y para adjuntar la evidencia a un PR mientras
`DoD-4` esté suspendido— la receta está en `[S5.1]` de `./desarrollo.md`.
