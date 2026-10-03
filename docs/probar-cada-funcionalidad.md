# SmartFood — Probar cada funcionalidad en local

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-PROBAR |
| titulo | Cómo poner a prueba cada funcionalidad del prototipo en el entorno local |
| tipo_documento | **Documento operativo.** No es un artefacto de Scrum ni un entregable |
| documentos_fuente | `./desarrollo.md` (de donde sale); `./mapa-de-la-aplicacion.md`; `./decisiones-de-alcance.md` |
| actualizado | 2026-10-01 |
| idioma | es-CO |
| version | 1.2 |

**Qué hacer para ver funcionando cada cosa**, una por sección: qué cuenta usar, qué pantalla
abrir, qué tiene que pasar y qué hay que preparar antes. Es lo que se repasa para preparar
una demostración, y lo que se mira para comprobar a mano que una historia sigue en pie.

**Lo que da por hecho**: el stack levantado con `docker compose up -d` y sembrado
(`[S1]` de `./desarrollo.md`), con las cuentas de `[S2.1]` del mismo documento. Para cobrar
en el punto de venta hacen falta además existencias y saldo, que el seed no crea:
`[S1.2]` de `./desarrollo.md`.

**No es el recorrido de demostración.** Ese —el orden en que se enseña todo, de corrido—
es `[S5]` de `./mapa-de-la-aplicacion.md`. Aquí cada sección se sostiene sola.

Salió de `./desarrollo.md` el 2026-10-01, cuando ese documento mezclaba el entorno con
esto. Allí queda cómo se levanta y se opera el entorno.

---

## [S1] Entrar como acudiente

Los acudientes nacen de la carga masiva (`HU-01`), y **la carga le envía a cada uno su
invitación** (`HU-03`, `DEC-18`). Sus direcciones son ficticias, así que no la recibe ningún
buzón: la recibe Mailpit. Hay dos caminos, y sirven para cosas distintas.

**Para demostrar `HU-03`** —el recorrido real: invitación, contraseña propia, acceso—, se
carga un archivo desde `/carga/` como institución, **sin** contraseña asignada. Después:

1. En http://localhost:8025 hay un correo «Te damos acceso a SmartFood» por cada acudiente
   nuevo del archivo.
2. Su botón «Definir mi contraseña» lleva a `/invitacion/…`. Se define la contraseña.
3. Se entra por `/login/` con ese correo y esa contraseña, y se aterriza en
   `/mis-estudiantes/`.

> **Los acudientes que siembra `--estudiantes N` no sirven para esto.** El seed les asigna
> contraseña (`DEC-11`), así que no reciben invitación: no hay nada que activar. Es lo que
> se quiere para el día a día; para la demostración, carga un archivo.

**Sin Mailpit a mano** —la aplicación en el host sin el compose—, el enlace de una cuenta se
saca desde la terminal:

```bash
uv run python manage.py invitacion marta.ruiz@example.com
```

**Ese enlace es una credencial**: quien lo tenga puede fijar la contraseña de esa cuenta. Por
eso no aparece en el resultado de la carga ni en ninguna pantalla del sistema (`DEC-3`).

**Para trabajar el día a día**, la carga admite contraseña asignada (`DEC-11`), y entonces
no genera invitación porque la cuenta ya nace activada:

```python
# uv run python manage.py shell
from personas.models import Institucion
from personas.services import cargar_estudiantes_y_acudientes

actor = Institucion.objects.select_related("usuario").first().usuario
with open("estudiantes.csv", "rb") as f:
    print(cargar_estudiantes_y_acudientes(
        actor=actor, archivo=f, contrasena_de_desarrollo="smartfood-local-2026"
    ))
```

Después, `/login/` con el correo del acudiente y esa contraseña lleva a
`/mis-estudiantes/` (`TT-29`, `HU-04`).

## [S2] Recuperar una contraseña olvidada

En `/login/`, **¿Olvidaste tu contraseña?** (`HU-62`, `DEC-19`). Se escribe el correo de la
cuenta y el enlace llega a Mailpit; con él se elige la contraseña nueva y se entra con ella.
Para probarlo con las cuentas del seed: `cajero@example.com`, y el correo «Elige una
contraseña nueva para SmartFood» en http://localhost:8025.

**La pantalla responde lo mismo exista o no la cuenta**: no dice qué correos tienen cuenta,
porque eso diría quién es acudiente de la institución. Por eso «no llega nada» tiene tres
causas posibles y la pantalla no distingue ninguna: el correo no tiene cuenta, la cuenta
está desactivada (`HU-42`), o todavía no definió su contraseña —esa sigue entrando por su
invitación—.

**Ningún `up` te devuelve la contraseña del seed de una cuenta que cambiaste así**: el
personal y los acudientes ya sembrados no se tocan (`[S1.0.1]` de `./desarrollo.md`). Si la
necesitas otra vez, recupérala de nuevo o vuelve a empezar con `docker compose down -v`.

## [S3] Imprimir la tarjeta de un estudiante

En `/padron/`, **Editar** en la fila del estudiante, y en la ficha que se abre, **Imprimir
tarjeta** (`DT-40`). Abre `/estudiantes/<id>/tarjeta/` en otra pestaña, que es la vista
imprimible (`TT-37`).

Es de la institución, no del acudiente: quien produce la tarjeta es el colegio (`HU-45`).

**Al imprimir, al 100 %.** Si el navegador ajusta a la página, las barras se estrechan por
debajo de lo que resuelve un lector económico y la tarjeta deja de escanearse. El símbolo
mide 69 mm de ancho con sus zonas mudas, que son parte del código y no margen: recortar
por ahí lo inutiliza. El detalle está en `DT-22`.

## [S4] Reponer una tarjeta perdida

En `/padron/`, **Editar** en la fila del estudiante y, en la ficha, **Reasignar código**.
El navegador pide confirmación, porque **esto no se deshace**: el código actual deja de
identificar a nadie en ese mismo momento (`INVD-4`), y la tarjeta que el estudiante lleva
encima queda inservible. La ficha vuelve con el código nuevo y dice cuál murió; **lo que
estuvieras editando en ella sin guardar se descarta**. Después hay que imprimir la nueva,
con el enlace de al lado.

## [S5] Dar de baja a un estudiante que se retiró

En `/padron/`, **Editar** en su fila, apagar **Matriculado** y **Guardar**: el navegador pide
confirmación, y solo en ese caso. A un retirado la ficha ya no le enseña el interruptor sino
desde cuándo lo está (`DT-40`). La baja es **lógica**: no borra nada, el historial y el saldo se conservan y siguen siendo
consultables (`HU-51`, `HU-52`). Desde ese momento el estudiante no puede comprar ni
recargar (`INVD-2`).

**No confundir con la tarjeta perdida.** Eso es reasignar el código (`[S4]`), que es
otro estado y sí tiene vuelta. **La baja no se deshace**, y esa es la diferencia con la
desactivación: el tercer estado, que existe desde el Sprint 3. Se desactiva desde el padrón
(`HU-47`) o desde el panel del acudiente (`HU-48`), y **solo la institución reactiva**,
venga de donde venga la desactivación (`HU-49`, `INVD-3`). Desactivado tampoco compra ni
recibe recargas (`INVD-7`), pero su saldo le espera; el del retirado queda congelado.

## [S6] Cargar la fotografía de un estudiante

En `/padron/`, **Editar** en su fila y, en la ficha, **Subir foto** (o **Cambiar foto**):
la vista previa es local hasta que se guarda. Es opcional: sin ella todo funciona igual
(`HU-57`). Para quitarla, la casilla **Quitar la foto actual**. **Si la imagen no vale, no
se guarda nada de la ficha**, tampoco lo demás que se hubiera cambiado: un «Guardar» es una
sola transacción (`DT-40`).

Lo que se guarda no es el fichero que subiste: la canalización lo decodifica y lo vuelve a
codificar a WEBP, lo reduce al lado máximo y **le retira el EXIF**, la ubicación GPS
incluida (`DT-20`). Va al prefijo `privado/` del bucket y se sirve con URL firmada que
caduca en cinco minutos (`DT-18`, `DT-21`).

**En el prototipo son avatares generados, nunca personas reales** (`INVD-6`,
`ALC-OUT-07`). No es una preferencia: es la Ley 1581 de 2012 sobre datos de menores.

## [S7] Cargar la imagen de un producto

En la ficha del producto, campo **Imagen**. Es opcional: sin ella el producto se vende
igual (`HU-59`).

Pasa por la misma canalización que la fotografía del estudiante —se re-codifica a WEBP y
se reduce (`DT-20`)— pero va al prefijo `publico/`, que significa **no sensible**, no
accesible sin credenciales (`DT-21`). **La sirve la aplicación**, en
`/catalogo/imagenes/<clave>`, con caché de un mes y sin firma: una firma caduca, y el
punto de venta tendría que volver a pedir el catálogo entero solo para renovar enlaces.

La URL lleva la clave y no el identificador del producto: al reemplazar la imagen cambia
la clave, así que cambia la URL y no hay nada que invalidar.

## [S8] Reservar y pagar por adelantado

Como acudiente, en el panel de un estudiante: tarjeta **Reservas** → *Reservar consumo*. Se
escriben las cantidades y se envía una vez. **El saldo baja al confirmar**, no al recoger
(`HU-23`, `DT-33`), y el movimiento queda en el historial de la billetera como cualquier
venta.

La cifra que acompaña a cada producto es lo que queda **sin apartar** por otras reservas
pendientes, no las existencias: la pantalla no ofrece lo que el servicio va a rechazar.

**La reserva pasa por la misma validación que el cobro del mostrador.** Si el estudiante está
desactivado, si el producto lleva un alérgeno bloqueado, si está bloqueado, si se pasa del
cupo del día o si no alcanza el saldo, la reserva se rechaza igual que la venta — y sin que
`HU-23` mencione ninguna de esas reglas. Para verlo, bloquea un producto en
*Restricciones → Productos* e intenta reservarlo.

**El inventario no se mueve hasta la entrega** (`HU-25`, `[S10]`). Mientras tanto las
unidades siguen en el libro pero apartadas: las existencias reales no cambian y
`existencias_sin_reservar` sí.

## [S9] Ver qué hay que preparar para el descanso

Como cajero o como administración: entrada **Reservas** del menú. También está en la columna
de iconos del punto de venta, que es lo que el cajero tiene delante mientras cobra.

Enseña lo pagado y no recogido, **de lo más antiguo a lo más reciente** — es una cola de
trabajo, no un historial, y lo que importa es qué lleva más tiempo esperando. Un pedido
entregado sale de la lista.

**La consultan los dos roles de la cafetería** (`HU-24`, `FUN-5`): quien prepara y quien
entrega no tienen por qué ser la misma persona. La institución y el acudiente reciben `403`
aunque escriban la URL.

Para verla con datos, reserva desde un acudiente (`[S8]`) y entra con
`cajero@example.com`.

## [S10] Entregar un pedido en la caja

Como cajero, en el punto de venta: al identificar al estudiante, si tiene algo reservado sale
**antes del saldo**, con un botón **Entregar**. Va primero a propósito: lo primero que hay
que saber de alguien con un pedido es que viene a recogerlo. Si se monta una venta sin verlo,
se le cobra otra vez lo que su acudiente ya pagó.

**Entregar no descuenta saldo** (`HU-25`): el pedido se pagó al reservarse. Lo que mueve es
el inventario. Para comprobarlo a mano, mira el saldo antes y después — tiene que ser el
mismo— y las existencias del producto, que bajan.

**Y no se entrega dos veces.** El segundo intento se rechaza con su motivo dentro de la
pantalla. Lo impiden dos capas: el servicio mira el estado dentro del bloqueo, y por debajo
una restricción no deja que una venta descuente el mismo producto dos veces.

**Si no hay existencias, se entrega igual** y el libro queda en negativo (`DT-35`). No es un
fallo: dice que salió mercancía que el inventario no tenía registrada, y se ve en la pantalla
de existencias (`[S11]`) con la venta que lo originó. El compromiso ya estaba cobrado.

## [S11] Averiguar de dónde salen unas existencias

En el listado de productos del admin, **la cifra de la columna «existencias» es un enlace**.
Lleva a una pantalla con esa misma cifra y, debajo, los movimientos que la suman: fecha,
tipo, cantidad con su signo, qué lo explica —el motivo, o la venta si salió por una— y las
**existencias que quedaban tras cada movimiento**.

Esa última columna es la que sirve para auditar (`HU-29`): se sigue de abajo arriba y tiene
que terminar en la cifra grande. Si no terminara, el renglón donde se tuerce es el problema.

**Las dos cifras salen de caminos distintos a propósito.** La de arriba es un `SUM` de
PostgreSQL; la columna se calcula en Python al pintar. No se guarda ningún acumulado: un
acumulado almacenado sería la segunda fuente de verdad que `DT-5` evita, y la que acabaría
discrepando del historial.

## [S12] Dar de baja unidades que se perdieron

En el admin, entrada **Mermas** → *Añadir merma*. Tres campos: producto, **unidades
perdidas** —en positivo— y **motivo**, que es obligatorio (`HU-28`, `INV-8`).

Es una entrada distinta de *Movimientos de inventario*, donde se registran los ingresos.
Las dos escriben en el mismo libro: la merma es un proxy, no otra tabla.

**Se pregunta en positivo y se asienta en negativo.** El servicio pone el signo, no quien
registra: un «3» donde iba «-3» **sumaría** existencias que nadie ingresó, y el libro lo
aceptaría como un ingreso cualquiera.

**No se puede mermar más de lo que hay.** El sistema rechaza la merma que dejaría las
existencias en negativo. Si de verdad había más de lo que dice el sistema, primero se
registra el ingreso que falta —que también tiene una explicación— y después la merma. Es la
misma regla con la que la venta rechaza por existencias insuficientes
(`[S4]` de `./reglas-de-la-venta.md`).

**Una merma registrada no se edita ni se borra**, y no es que el permiso esté sin conceder:
`change` y `delete` no existen para este modelo. Un asiento corregido a posteriori deja unas
existencias que ya no explican lo que pasó (`INV-3`). Un error se corrige con otro
movimiento.

## [S13] Ver las alertas de frecuencia

**Recién sembrado no sale ninguna, y no es un fallo:** la regla pide **cinco días distintos**
de la misma categoría dentro de los últimos catorce (`./reglas-de-frecuencia-de-consumo.md`),
y el seed no crea ventas. Hay que fabricar un historial repartido en varios días.

`creado_en` es `auto_now_add`, así que no se puede fijar al registrar la venta: se cobra
normal y después se le corrige la fecha con un `update()`, que es lo único que este script
hace fuera de los servicios.

```python
# guardar como sembrar-frecuencia.py y lanzar con `uv run python sembrar-frecuencia.py`
import django, os, sys
sys.path.insert(0, ".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from datetime import timedelta
from django.utils import timezone
from catalogo.models import Producto
from cuentas.models import Rol, Usuario
from personas.models import EstadoDelEstudiante, Estudiante
from ventas.models import Venta
from ventas.services import registrar_venta

cajero = Usuario.objects.filter(rol=Rol.CAJERO).first()
# **Activo, no `first()` a secas**: una base con la que ya se ha trasteado tiene
# estudiantes desactivados, y a esos no se les cobra ni se les recarga (`INVD-2`).
estudiante = Estudiante.objects.filter(estado=EstadoDelEstudiante.ACTIVO).first()
producto = Producto.objects.filter(categoria__nombre="Panadería").first()

for dia in range(9):                      # nueve días → frecuencia muy alta
    venta = registrar_venta(
        actor=cajero, estudiante=estudiante, lineas={producto.id: 1}
    )
    Venta.objects.filter(pk=venta.pk).update(
        creado_en=timezone.now() - timedelta(days=dia)
    )
```

Hace falta **saldo y existencias**, como cualquier venta: el atajo está en `[S1.2]` de
`./desarrollo.md`.

Después, entrando como el acudiente de ese estudiante: *Mis estudiantes* → tarjeta
**Consumo** → **Ver el historial**. Las alertas salen arriba, el **aporte nutricional**
debajo —ese sí aparece con una sola compra— y el descargo de `INV-9` al final: **ese sale
siempre**, haya recomendaciones o no.

**Para ver el «sin datos» del aporte y el renglón excluido**, vende además un producto sin
información nutricional: el seed crea el catálogo con ficha completa, así que hay que crear
uno a propósito. Un producto sin declarar no suma cero — se excluye y la pantalla dice
cuántos renglones dejó fuera (`[S4.3]` de `./valores-de-referencia-nutricional.md`).

## [S14] Cortar el acceso de un acudiente

Como institución, en `/padron/`, **Editar** en la fila de cualquiera de sus estudiantes y, en
el recuadro del acudiente, apagar **Acceso a la aplicación** y **Guardar** (`HU-63`,
`DEC-20`). Sin confirmación: se deshace con el mismo interruptor. La frase de al lado dice a
cuántos estudiantes alcanza, porque la cuenta es una para todos ellos (`HU-04`).

Lo que tiene que pasar: el acudiente **no entra** en `/login/`, la sesión que tuviera abierta
deja de servir en la siguiente petición, y **no recibe** el correo de recuperación aunque lo
pida (`DEC-19`; se comprueba en Mailpit, `[S2]`). Sus estudiantes **siguen comprando** con el
saldo que tengan y con sus restricciones; lo que pierden es quien les recargue.

**No es la desactivación del estudiante** (`HU-47`), que bloquea la tarjeta y se hace desde
la fila. Esto corta la cuenta del adulto. Y **no es para el personal**: un cajero o la
administración se desactivan desde *Usuarios* (`HU-42`).

## [S15] Matricular a un solo estudiante

Como institución, en `/padron/`, **Cargar un solo estudiante** (`HU-44`, `DT-40`). Se abre la
ficha vacía, con los tres campos obligatorios en rojo y **Matricular** deshabilitado. Cada
aviso desaparece cuando su campo cumple: el nombre, escrito; el documento, **entre 5 y 20
caracteres**, las mismas longitudes que la carga masiva; el acudiente, **elegido** de la
lista que sale al buscarlo por nombre, documento o correo —escribirlo no es elegirlo—.

Al matricular, la ficha vuelve vacía para el siguiente y dice el **código generado**, con
**Imprimir tarjeta** y **Abrir su ficha** al lado; la tabla de detrás ya lo trae.

Lo que tiene que rechazar, y con su motivo junto al campo: un documento que ya es de otro
estudiante, y una fotografía que no se puede procesar —en ese caso **no queda nadie
matriculado**, tampoco sin foto—.

**El acudiente tiene que existir.** Si la familia es nueva, entra con la carga masiva
(`[S1]`, `HU-01`), que es lo único que crea cuentas de acudiente.

**El estudiante de prueba no se puede borrar desde la aplicación**: ninguna pantalla lo hace,
a propósito (`DT-12`). En la base de trabajo, uno recién creado y sin movimientos se borra
desde la consola de Django; con historia, no hay forma, y lo que procede es la baja.
