# SmartFood — Guía de desarrollo

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-DESARROLLO |
| titulo | Reconstrucción del entorno local, credenciales y comandos del día a día |
| tipo_documento | **Documento operativo.** No es un artefacto de Scrum ni un entregable |
| documentos_fuente | `./despliegue.md`; `./convenciones-de-git.md`; `./decisiones-de-alcance.md` (`DEC-9` … `DEC-12`, `DEC-15`); `./decisiones-tecnicas.md` (`DT-37`) |
| actualizado | 2026-09-30 |
| idioma | es-CO |
| version | 1.3 |

Es la libreta del desarrollo: **cómo levantar el entorno desde cero, con qué se entra y
qué comandos hacen falta a diario.** Es el único entorno que hay: `DEC-15` retiró el
despliegue y `./despliegue.md` explica por qué.

---

## [S1] Reconstrucción desde cero

Una herramienta instalada: **Docker** con **Compose 2.20 o posterior** (`docker compose
version`). Nada más —ni uv, ni Python, ni `.env`— (`DT-37`).

```bash
git clone git@github.com:pjg09/smartfood.git
cd smartfood
docker compose up            # o `up -d`, para dejarlo en segundo plano
```

En <http://localhost:8000>, con las cuentas de `[S2.1]`. Administración en `/admin/`, salud
en `/salud/`. La primera vez tarda unos minutos —descarga imágenes y construye la de la
aplicación—; las siguientes, segundos.

**Qué hace ese comando**, para no tener que hacerlo a mano:

| Servicio | Qué hace |
|---|---|
| `postgres`, `seaweedfs` | La base (`DT-1`) y el almacenamiento de objetos compatible con S3 (`DT-18`, `DT-38`) |
| `mailpit` | Atrapa todo el correo que el sistema envía y lo enseña en http://localhost:8025, sin entregar nada fuera (`DEC-18`) |
| `almacenamiento-inicializar` | Crea el bucket privado si no existe y sale (`TT-50`, `DT-21`) |
| `estilos` | Compila **las dos** hojas de Tailwind (`DT-36`) y se queda vigilando las plantillas: es el `tailwind watch` de la segunda terminal |
| `app` | `migrate`, `sincronizar_permisos`, `sembrar` con 12 estudiantes y la contraseña de `[S2.1]`, `collectstatic` y `runserver` |

**El código no está en la imagen: está montado.** Guardar un fichero recarga `runserver`, y
guardar una plantilla recompila la hoja en un segundo. Reconstruir solo hace falta cuando
cambian las dependencias, y eso lo hace el propio `up` (`pull_policy: build`): tras un
`git pull` que traiga un `uv.lock` nuevo, `docker compose up` basta.

**Cualquier `uv run python manage.py X` de este documento es, con el stack del compose,
`docker compose exec app python manage.py X`.** Dentro del contenedor no hay `uv run`: el
entorno ya está activado.

### [S1.0.1] Ajustes del compose que se pueden cambiar

Todos opcionales, en un `.env` en la raíz —el compose lo lee solo— o en la línea de comandos:

| Variable | Por defecto | Para qué |
|---|---|---|
| `UID`, `GID` | `1000` | **Si tu usuario no es el 1000** (`id -u`). Los contenedores escriben en el repositorio con este usuario; con otro, las hojas compiladas quedarían a nombre de alguien que no eres tú |
| `SEMBRAR_ESTUDIANTES` | `12` | Cuántos estudiantes siembra |
| `SEMBRAR_CONTRASENA` | `smartfood-local-2026` | La contraseña de las cuentas del seed. **Vacía, no siembra** |
| `APP_PORT`, `POSTGRES_PORT`, `S3_PORT`, `MAILPIT_PORT`, `MAILPIT_SMTP_PORT` | `8000`, `5432`, `9000`, `8025`, `1025` | Si el puerto está ocupado |

**El arranque pasa `sembrar` en cada `up`, y eso solo restablece la contraseña de la
institución** (`[S1.1]`). Al personal y a los acudientes que ya existen no los toca: si
cambiaste la contraseña de una de esas cuentas —recuperándola (`[S2.4.1]`), por ejemplo—, se
queda la nueva.

### [S1.0.2] Sin contenedor para la aplicación

El camino anterior sigue funcionando, y es el cómodo para depurar con un punto de ruptura.
Hacen falta además [uv](https://docs.astral.sh/uv/getting-started/installation/) y el `.env`:

```bash
cp .env.example .env
docker compose up -d postgres seaweedfs almacenamiento-inicializar mailpit   # solo la infraestructura
uv sync
uv run python manage.py migrate
uv run python manage.py sembrar --contrasena-de-desarrollo 'smartfood-local-2026' \
  --estudiantes 12
uv run python manage.py runserver                          # y `tailwind watch` en otra terminal
```

**No mezcles los dos a la vez**: se pelean por el puerto 8000 y por la base de pruebas
`test_smartfood`.

### [S1.1] Empezar de verdad de cero

`docker compose down` **conserva** los datos. Para borrarlos:

```bash
docker compose down -v        # -v borra los volúmenes: base y bucket
```

Después, `docker compose up` otra vez: migra y siembra desde cero.

> **`sembrar` es idempotente y no cambia lo que ya existe.** Si la institución ya está
> creada con otro correo, una segunda pasada **no** lo actualiza: solo restablece la
> contraseña. Para cambiar el correo hay que borrar la base.

---

## [S2] Con qué se entra

### [S1.2] Dejar el punto de venta listo para cobrar

**`sembrar` no crea existencias ni saldo**, y hasta que las haya el punto de venta no puede
cobrar: los dieciséis productos salen «Sin existencias» y cualquier venta se rechaza.

No es un descuido del seed. **Ninguna de las dos cifras es un campo**: el saldo es la suma de
los movimientos de la billetera (`DT-4`, `INV-2`) y las existencias, la de los movimientos de
inventario (`DT-5`, `INV-3`). Sembrar un número sin su historial sería inventar un asiento, y
el primer `TST-3` lo cazaría.

Lo que hace falta es un primer movimiento **por el camino real**, no un `UPDATE`:

```bash
uv run python manage.py shell -c '
from decimal import Decimal
from billetera.services import recargar
from catalogo.models import Producto
from cuentas.models import Usuario
from inventario.services import ingresar_mercancia
from personas.models import Estudiante

admin = Usuario.objects.get(email="administracion@example.com")
for p in Producto.objects.filter(activo=True):
    ingresar_mercancia(actor=admin, producto=p, cantidad=40,
                       motivo="Carga inicial de demostración")

for e in Estudiante.objects.filter(estado="activo"):
    recargar(actor=e.acudiente.usuario, estudiante=e, monto=Decimal("50000"))
'
```

Pasa por `ingresar_mercancia` y `recargar`, así que respeta el punto único de asiento de
`DT-24` y deja el historial que `INV-2` e `INV-3` obligan a poder leer. Escribir esas filas a
mano —desde `dbshell` o pgAdmin— salta las comprobaciones de los servicios y es lo que rompe
el `migrate` de la semana siguiente cuando llegue una `CheckConstraint` nueva.

**Es lo primero que hay que correr antes de enseñar el punto de venta.** Sin esto, la
demostración se queda en la pantalla de identificación.

---

### [S2.1] Entorno local

La aplicación se sirve en <http://localhost:8000>, con dos puertas: `/login/` y `/admin/`
(`INT-3`). Cuál alcanza cada rol está en la tabla.

**Una sola contraseña para todas las cuentas del seed**: la que se le pasó a
`--contrasena-de-desarrollo`, que en la base de `[S1]` es `smartfood-local-2026`. No está
escrita en el código —`sembrar` no tiene ninguna por defecto (`DEC-11`)—, así que si
sembraste con otra, la buena es esa.

| Rol | Cuenta | Por dónde entra | Dónde aterriza |
|---|---|---|---|
| Institución (`USR-5`) | `institucion@example.com` | `/login/` **o** `/admin/` | `/padron/` |
| Administración de la cafetería (`USR-4`) | `administracion@example.com` | `/login/` **o** `/admin/` | `/admin/panel/` |
| Cajero (`USR-3`) | `cajero@example.com` | **solo `/login/`** | `/punto-de-venta/` |
| Acudiente (`USR-2`) | `nombre.apellido<n>@example.com` | **solo `/login/`** | `/mis-estudiantes/` |

**El cajero no entra al admin y no es un permiso que falte**: no es `is_staff`, así que
`/admin/` le responde una redirección a su propia pantalla de acceso. Lo suyo es `INT-2`, el
punto de venta, y `[S11]` no le concede nada del admin. Lo mismo el acudiente, cuya interfaz
es `INT-1` y no el admin (`DT-2`).

**Los correos de los acudientes dependen de cuántos sembraste.** Salen de
`correo_de()` en `config/datos_ficticios.py` con el patrón `nombre.apellido<índice>@example.com`
—el índice empieza en cero—, así que con `--estudiantes 12` no son los mismos que con 8. Los de
tu base, con el aviso de cuáles pueden entrar con la contraseña y cuáles solo por invitación:

```bash
uv run python manage.py shell -c '
from cuentas.models import Rol, Usuario
for u in Usuario.objects.filter(rol=Rol.ACUDIENTE).order_by("email"):
    print(u.email, "·", "clave del seed" if u.has_usable_password() else "solo por invitación")
'
```

**Los acudientes cargados por CSV no tienen contraseña y no la van a tener**: nacen sin ella
a propósito y entran por su enlace de invitación, que les llega al Mailpit del compose
(`[S2.4]`, `DEC-18`). Son los que aparecen arriba como «solo por invitación», y son los únicos con los
que se puede demostrar `HU-03`.

**Las rutas no están aquí: están en `[S2]` de `./mapa-de-la-aplicacion.md`**, todas, con
quién alcanza cada una y de qué tarea salió. No se repiten en este documento a
propósito — dos tablas de rutas se desincronizan en la primera pantalla que alguien añada, y
entonces ninguna de las dos sirve para responder quién llega a dónde.

**Hay dos puertas y no son intercambiables** (`TT-56`, `DEC-12`). `/admin/login/` exige
`is_staff` y solo sirve a la institución y a la administración de la cafetería — **el cajero
no, aunque sea personal de la cafetería**: `[S3]` de `./mapa-de-la-aplicacion.md` le da `302`
en todo el admin. `/login/` es la pantalla común a los cuatro roles y es **la única por la
que entran el cajero y el acudiente**, que no acceden a la administración porque `INT-1` e
`INT-2` no son el admin (`DT-2`).

**Esta credencial se escribe aquí a propósito y no es un descuido.** Solo sirve contra
`localhost`, sobre datos ficticios (`ALC-OUT-07`), en una base que se borra con un
comando. No abre nada de nadie.

El dominio `example.com` está reservado por la **RFC 2606**: nadie puede registrarlo, así
que ningún correo dirigido ahí llega a una persona real.

### [S2.2] No hay entorno desplegado

**El de `[S2.1]` es el único que existe.** `DEC-15` retiró el despliegue el 2026-09-17 y
`DT-31` recoge la consecuencia técnica: no hay URL pública, ni credenciales de producción,
ni variables que consultar en ningún proveedor. El porqué está en `./despliegue.md`.

Lo que eso cambia para el día a día: **nada**. El equipo lleva todo el semestre
desarrollando y demostrando contra `localhost`, y el Avance 2 se enseña desde un portátil.

La cuenta institucional local, la de `[S2.1]`, **no es superusuario de Django**: tiene
exactamente los permisos que declara `cuentas/permisos.py` y no puede editar los grupos
con los que `DT-11` sostiene `INV-4`. El razonamiento está en `UX-6` de
`./recorrido-de-administracion-de-estudiantes.md`. Si el admin le devuelve un `403` sobre
algo que debería poder hacer, el sitio donde se arregla es la matriz, no la cuenta.

### [S2.3] Por qué la institución tiene contraseña y las demás cuentas no

`DEC-10`. La dirección de la cuenta institucional no es de nadie: no hay quien abra esa
invitación. Y mandarla a una dirección inexistente produce un rebote que degrada la
reputación del remitente (`DEC-9`), justo la que hace falta intacta para lo único que sí
se demuestra por correo: la activación de un acudiente.

**Las cuentas de acudiente y de personal no tienen este atajo.** Se activan por
invitación, sin excepción (`HU-41`, `HU-03`, `INVD-1`). Quien crea esas cuentas no llega
a conocer nunca su clave, y eso no se relaja.

Para demostrar `HU-39` como está escrita —cuenta creada por seed, invitación por correo,
titular define su contraseña— se siembra **sin** contraseña sobre una base vacía, y la
invitación llega a Mailpit:

```bash
docker compose exec app python manage.py sembrar --email-institucion otra@example.com
```

Con `EMAIL_URL` apuntando a un proveedor real y `--email-institucion` a un buzón tuyo, llega
a una bandeja de verdad.

### [S2.3.1] Qué siembra `--estudiantes N`

Con esa opción, `sembrar` deja el prototipo listo para trabajar (`TT-08`):

| Qué | Cuánto |
|---|---|
| Personal de la cafetería | Un cajero y un administrador, con contraseña asignada |
| Acudientes y estudiantes | `N` estudiantes; uno de cada cuatro acudientes con dos hijos |
| Avatares | Uno por estudiante, **dibujado**, nunca descargado (`INVD-6`) |
| Catálogo | 5 categorías, 8 alérgenos y 16 productos con su nutricional e imagen |

**Es idempotente**: se puede ejecutar en cada despliegue sin duplicar nada ni volver a
subir imágenes. Todos los correos son `@example.com` y todos los datos son inventados
(`ALC-OUT-07`). Con `--sin-imagenes` va más rápido, si solo hacen falta los datos.

Las cuentas del personal son `cajero@example.com` y `administracion@example.com`, con la
misma contraseña que se le pase al comando.

### [S2.4] Entrar como acudiente

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

### [S2.4.1] Recuperar una contraseña olvidada

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
personal y los acudientes ya sembrados no se tocan (`[S1.0.1]`). Si la necesitas otra vez,
recupérala de nuevo o vuelve a empezar con `docker compose down -v`.

### [S2.5] Imprimir la tarjeta de un estudiante

Desde el admin, en el listado de estudiantes o en su ficha: **Imprimir tarjeta**. Abre
`/estudiantes/<id>/tarjeta/`, que es la vista imprimible (`TT-37`).

Es de la institución, no del acudiente: quien produce la tarjeta es el colegio (`HU-45`).

**Al imprimir, al 100 %.** Si el navegador ajusta a la página, las barras se estrechan por
debajo de lo que resuelve un lector económico y la tarjeta deja de escanearse. El símbolo
mide 69 mm de ancho con sus zonas mudas, que son parte del código y no margen: recortar
por ahí lo inutiliza. El detalle está en `DT-22`.

### [S2.6] Reponer una tarjeta perdida

En el listado de estudiantes del admin, se selecciona al estudiante y se elige
**Reasignar el código de tarjeta**. Hay una pantalla de confirmación que enseña el código
que se va a invalidar, porque **esto no se deshace**: el código actual deja de identificar
a nadie en ese mismo momento (`INVD-4`), y la tarjeta que el estudiante lleva encima queda
inservible. Después hay que imprimir la nueva; el mensaje trae el enlace.

### [S2.7] Dar de baja a un estudiante que se retiró

En el listado del admin, **Dar de baja (se retiró del colegio)**, con confirmación. La
baja es **lógica**: no borra nada, el historial y el saldo se conservan y siguen siendo
consultables (`HU-51`, `HU-52`). Desde ese momento el estudiante no puede comprar ni
recargar (`INVD-2`).

**No confundir con la tarjeta perdida.** Eso es reasignar el código (`[S2.6]`), que es
otro estado y sí tiene vuelta. **La baja no se deshace**, y esa es la diferencia con la
desactivación: el tercer estado, que existe desde el Sprint 3. Se desactiva desde el padrón
(`HU-47`) o desde el panel del acudiente (`HU-48`), y **solo la institución reactiva**,
venga de donde venga la desactivación (`HU-49`, `INVD-3`). Desactivado tampoco compra ni
recibe recargas (`INVD-7`), pero su saldo le espera; el del retirado queda congelado.

### [S2.8] Cargar la fotografía de un estudiante

En la ficha del estudiante, campo **Fotografía**. Es opcional: sin ella todo funciona
igual (`HU-57`). Para quitarla, la casilla **Quitar la fotografía actual**.

Lo que se guarda no es el fichero que subiste: la canalización lo decodifica y lo vuelve a
codificar a WEBP, lo reduce al lado máximo y **le retira el EXIF**, la ubicación GPS
incluida (`DT-20`). Va al prefijo `privado/` del bucket y se sirve con URL firmada que
caduca en cinco minutos (`DT-18`, `DT-21`).

**En el prototipo son avatares generados, nunca personas reales** (`INVD-6`,
`ALC-OUT-07`). No es una preferencia: es la Ley 1581 de 2012 sobre datos de menores.

### [S2.9] Cargar la imagen de un producto

En la ficha del producto, campo **Imagen**. Es opcional: sin ella el producto se vende
igual (`HU-59`).

Pasa por la misma canalización que la fotografía del estudiante —se re-codifica a WEBP y
se reduce (`DT-20`)— pero va al prefijo `publico/`, que significa **no sensible**, no
accesible sin credenciales (`DT-21`). **La sirve la aplicación**, en
`/catalogo/imagenes/<clave>`, con caché de un mes y sin firma: una firma caduca, y el
punto de venta tendría que volver a pedir el catálogo entero solo para renovar enlaces.

La URL lleva la clave y no el identificador del producto: al reemplazar la imagen cambia
la clave, así que cambia la URL y no hay nada que invalidar.

### [S2.9.1] Reservar y pagar por adelantado

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

**El inventario no se mueve hasta la entrega** (`HU-25`, `[S2.9.3]`). Mientras tanto las
unidades siguen en el libro pero apartadas: las existencias reales no cambian y
`existencias_sin_reservar` sí.

### [S2.9.2] Ver qué hay que preparar para el descanso

Como cajero o como administración: entrada **Reservas** del menú. También está en la columna
de iconos del punto de venta, que es lo que el cajero tiene delante mientras cobra.

Enseña lo pagado y no recogido, **de lo más antiguo a lo más reciente** — es una cola de
trabajo, no un historial, y lo que importa es qué lleva más tiempo esperando. Un pedido
entregado sale de la lista.

**La consultan los dos roles de la cafetería** (`HU-24`, `FUN-5`): quien prepara y quien
entrega no tienen por qué ser la misma persona. La institución y el acudiente reciben `403`
aunque escriban la URL.

Para verla con datos, reserva desde un acudiente (`[S2.9.1]`) y entra con
`cajero@example.com`.

### [S2.9.3] Entregar un pedido en la caja

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
de existencias (`[S2.10]`) con la venta que lo originó. El compromiso ya estaba cobrado.

### [S2.10] Averiguar de dónde salen unas existencias

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

### [S2.11] Dar de baja unidades que se perdieron

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

### [S2.12] Ver las alertas de frecuencia

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

Hace falta **saldo y existencias**, como cualquier venta: el atajo está en `[S1.2]`.

Después, entrando como el acudiente de ese estudiante: *Mis estudiantes* → tarjeta
**Consumo** → **Ver el historial**. Las alertas salen arriba, el **aporte nutricional**
debajo —ese sí aparece con una sola compra— y el descargo de `INV-9` al final: **ese sale
siempre**, haya recomendaciones o no.

**Para ver el «sin datos» del aporte y el renglón excluido**, vende además un producto sin
información nutricional: el seed crea el catálogo con ficha completa, así que hay que crear
uno a propósito. Un producto sin declarar no suma cero — se excluye y la pantalla dice
cuántos renglones dejó fuera (`[S4.3]` de `./valores-de-referencia-nutricional.md`).

---

## [S3] Comandos del día a día

`uv run` activa el entorno virtual: no hace falta `source .venv/bin/activate`.

Con el stack del compose. En la tabla, **`manage`** abrevia
`docker compose exec app python manage.py`:

| Qué | Comando |
|---|---|
| **Levantar todo** | `docker compose up -d` |
| Apagarlo | `docker compose down` |
| Borrarlo **con los datos** | `docker compose down -v` |
| Ver la aplicación | `docker compose logs -f app` |
| **Ver el correo** que el sistema envía | http://localhost:8025 (`DEC-18`) |
| Ver la compilación de estilos | `docker compose logs -f estilos` |
| Reiniciar la aplicación | `docker compose restart app` |
| Migrar | lo hace el arranque; a mano, `manage migrate` |
| Crear migraciones | `manage makemigrations` |
| Pruebas | `manage test --noinput` |
| Consola de PostgreSQL | `manage dbshell` |
| Consola de Django | `manage shell` |
| Añadir dependencia | `uv add nombre-del-paquete` en el host, y `docker compose up -d` |
| Probar el correo | `manage sendtestemail tu@correo.com`, y mirarlo en Mailpit |
| **Sacar un enlace de invitación** | `manage invitacion correo@example.com` |
| **Aplicar la matriz de permisos** | lo hace el arranque; a mano, `manage sincronizar_permisos` |

**Las dos hojas se recompilan solas** mientras el servicio `estilos` esté levantado. Sin el
compose —`[S1.0.2]`—, deja `uv run python manage.py tailwind watch` en una segunda terminal:
sin él, una clase nueva no aparece en la hoja compilada y el cambio no se ve.

**Y son DOS hojas, no una** (`DT-36`). `tailwind build` y `tailwind watch` solo conocen la de
la aplicación, la que declara `TAILWIND_CLI_SRC_CSS`. La del admin —Tailwind **sin
`preflight`**, porque ese reset desarma sus pantallas— se compila con su propio comando, que
el servicio `estilos` ya deja vigilando; sin el compose:

```bash
uv run python manage.py estilos_del_admin            # assets/css/admin.css
uv run python manage.py estilos_del_admin --watch    # mientras se trabaja
uv run python manage.py collectstatic --noinput      # o se sigue sirviendo la anterior
```

**Si tocas una plantilla de `templates/admin/` y no corres ese comando, el cambio no se ve y
nada lo indica**: la pantalla sale bien, con la hoja de antes. Las dos hojas comparten
`estilos/tokens.css`, así que un color de la marca sigue estando escrito una sola vez.

`assets/css/admin.css` es artefacto de build y está en `.gitignore`, igual que
`assets/css/tailwind.css`.

### [S3.1] Capturas del prototipo para un entregable

Los avances del curso piden evidencias en imagen, y las pantallas hay que capturarlas con
sesión iniciada. **No hace falta instalar nada**: no hay `pip`, pero sí `uv` y el Chrome del
sistema, así que Playwright se monta al vuelo y se le pasa ese Chrome.

```bash
uv run --with playwright python - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome")
    pg = b.new_page()
    pg.goto("http://localhost:8000/login/")
    pg.fill('input[name="username"]', "cajero@example.com")
    pg.fill('input[name="password"]', "smartfood-local-2026")
    pg.click('button[type="submit"]'); pg.wait_for_load_state("networkidle")
    pg.goto("http://localhost:8000/punto-de-venta/")
    pg.screenshot(path="captura.png")
    b.close()
PY
```

Tres cosas que ahorran una ronda:

- **`device_scale_factor=2`** en el `new_context`, o la imagen se ve borrosa impresa.
- **Las rutas que son fragmentos no se abren con `goto`**: salen sin estilos, y parece un
  fallo de Tailwind que no lo es. A la ficha de un estudiante se llega pulsándolo desde
  `/mis-estudiantes/`. Está explicado en «Trampas de este stack» del `CLAUDE.md` de la raíz.
- **Para añadir al carrito, el selector es el botón, no el nombre del producto**:
  `button[hx-vals*="<id-del-producto>"]`. Pulsar el texto no dispara nada.

**Si compilas a mano, usa `tailwind build --force`.** Sin la opción, el comando compara la
fecha de `estilos/fuente.css` con la de la hoja compilada y responde «All 1 stylesheet(s)
are up to date» — que es cierto para la hoja fuente y falso para lo que importa: las clases
salen de las PLANTILLAS, y ésas no se miran. El síntoma es desconcertante porque la
compilación dice que fue bien: la clase nueva simplemente no está, y el elemento se queda
sin estilo sin ningún error. `watch` no tiene el problema.

**Los colores y las medidas viven en `estilos/fuente.css`, y sólo ahí** (`DT-23`). En una
plantilla se usa el alias de intención —`bg-superficie`, `text-texto`, `border-borde`— nunca un
hexadecimal ni la paleta de fábrica de Tailwind, que está borrada: `bg-slate-500` **no pinta
nada y tampoco da error**. Los puntos de ruptura son `tablet:`, `escritorio:` y `amplio:`;
`sm:` y `lg:` no existen. `uv run python manage.py test config.tests_plantillas` comprueba las
dos reglas.

Para ver una pantalla en el otro tema no hace falta cambiar el sistema operativo: el selector
de la barra tiene tres estados —claro, oscuro y el del sistema— y la elección se guarda en el
navegador.

---

## [S4] Qué hay levantado en local

| Servicio | Dónde | Credenciales |
|---|---|---|
| **Aplicación** | http://localhost:8000 | las cuentas de `[S2.1]` |
| PostgreSQL | `localhost:5432` | `smartfood` / `smartfood-local`, base `smartfood` |
| SeaweedFS (API S3) | `localhost:9000` | `smartfood` / `smartfood-local` |
| Bucket | `smartfood`, prefijos `privado/` y `publico/` | lo crea `docker compose` |
| **Correo** (Mailpit) | http://localhost:8025, SMTP en `localhost:1025` | ninguna, y **solo desde esta máquina** |

Todas ficticias y solo válidas contra los contenedores de `compose.yaml`.

**No hay consola web del almacenamiento** (`DT-38`): la de SeaweedFS no pide credenciales y
dejaría las fotografías a la vista. Para mirar el bucket, cualquier cliente S3 con las
credenciales de la tabla contra `localhost:9000`.

**El correo no sale de tu máquina** (`DEC-18`). Todo lo que el sistema envía —las
invitaciones de las altas y de la carga masiva, el enlace de recuperación de contraseña—
lo atrapa Mailpit y se lee en http://localhost:8025. **Esa pantalla lista enlaces de
invitación, que son credenciales** (`DEC-3`): por eso escucha solo en `127.0.0.1`, y por
eso no hay que publicarla nunca en otra interfaz.

Para probar contra un buzón de verdad —enseñar que una invitación llega a un Gmail—, se
apunta `EMAIL_URL` a un proveedor real (`smtp+tls://usuario:clave@host:587`). **Nunca con
una carga masiva de por medio**: las direcciones del archivo son ficticias, y cada rebote
degrada la reputación del remitente (`DEC-9`).

---

## [S5] Antes de abrir un Pull Request

`main` está protegida: todo entra por PR (`./convenciones-de-git.md`).

```bash
docker compose exec app python manage.py check
docker compose exec app python manage.py makemigrations --check --dry-run   # sin cambios sin migrar
docker compose exec app python manage.py test --noinput
```

Los tres tienen que pasar —con `uv run python manage.py …` en el host, lo mismo—. La CI
los repite en cada PR, y sin ellos en verde no se publica versión (`[S3.0]` de
`./convenciones-de-git.md`). **Y si el
PR toca la infraestructura, un cuarto**: que el stack levante desde cero (`[S5.3]`). El segundo es `DoD-3` y es el que más se olvida: un modelo
editado sin su migración no da error hasta que otra persona levanta el proyecto.

`--noinput` en el tercero: si una ejecución anterior se interrumpió a media prueba, la base
de datos de prueba se queda creada y el comando siguiente **se queda esperando** una
respuesta que nadie escribe. Con la opción, la borra y sigue.

### [S5.1] Si tocas `locale/`

**Hay dos catálogos y no se eligen al azar**, porque resuelven dos problemas distintos:

| Catálogo | Qué arregla | Hoy |
|---|---|---|
| `locale/es/` | Lo que Django deja **sin traducir** en el admin | 5 cadenas de la 6.1 |
| `locale/es_CO/` | Lo que Django **traduce mal** | los 12 meses y «View %s» |

**Una corrección escrita en `es` no gana.** Con `LANGUAGE_CODE = "es-co"` el catálogo que
manda es el `es_CO` y el `es` solo actúa de reserva, así que lo que el `es_CO` de Django ya
traduce —aunque lo traduzca mal— pisa cualquier cosa que escribamos en `es`. Lo que sí
funciona desde `es` es lo que **no está en ninguno de los dos**: entonces la reserva es lo
único que responde. Es exactamente la diferencia entre las dos filas de la tabla.

El fichero que se edita es el `.po`; el que lee Django es el `.mo`, que hay que recompilar:

```bash
sudo apt install gettext        # una vez: msgfmt no viene con el sistema
uv run python manage.py compilemessages
```

**Sin recompilar, el cambio no se ve y nada falla**: Django sigue leyendo el `.mo` viejo.
Los dos ficheros van al repositorio, el `.po` porque es la fuente y el `.mo` porque no
todas las máquinas del equipo tienen `gettext` y `collectstatic` no compila mensajes.

`cuentas/tests_traducciones.py` comprueba que todas salen en español, que **ninguno de los
dos parches ha crecido** —si alguien empieza a traducir por su cuenta lo que Django ya trae,
se desincroniza a la primera versión— y que el reporte de cierres enseña «Filtrar por
jornada» y «14 de septiembre», que es donde se vieron los dos defectos.

**Los dos parches están pensados para borrarse.** Cuando Django traduzca esas cadenas y
deje de capitalizar los meses, los ficheros sobran. Por eso el `|lower` de las plantillas
se conserva aunque hoy sea redundante: las fechas del producto no deben depender de un
parche temporal.

---

### [S5.2] Mirar una pantalla sin abrir el navegador

Para revisar cómo queda algo **y para adjuntar la evidencia a un PR** —`DoD-4` está vigente y
pide demostrarlo ejecutándolo— no hace falta abrir el navegador a mano: se renderiza la
pantalla con el cliente de pruebas y se fotografía con Chrome sin interfaz.

```bash
# 1. Recompilar la hoja y publicarla, en este orden y con `--force`:
uv run python manage.py tailwind build --force
uv run python manage.py collectstatic --noinput
# 2. Renderizar con `django.test.Client` y guardar el HTML, reescribiendo las
#    rutas de `/static/` a `file:///…/staticfiles/`.
# 3. Fotografiar:
google-chrome --headless --disable-gpu --hide-scrollbars \
  --allow-file-access-from-files --window-size=1024,600 \
  --virtual-time-budget=3000 --screenshot=pantalla.png "file://$PWD/pantalla.html"
```

**Tres detalles sin los cuales la captura miente**, y los tres costaron una ronda de
diagnóstico:

- **`--allow-file-access-from-files`.** Sin él, el navegador no carga el JavaScript que vive
  en otra carpeta, así que no corre nada: el tema no se aplica, la cabecera de la portada no
  se vuelve transparente y el menú no responde. La página **parece rota** cuando lo que falta
  es un permiso del navegador.
- **Desactivar transiciones y animaciones**, inyectando
  `*{transition:none!important;animation:none!important}` en el `<head>`.
  `--virtual-time-budget` congela el reloj, así que toda transición se fotografía en su
  **estado inicial**: un elemento que cambia de color al cargar sale del color viejo. Es
  engañoso porque la captura sale bien formada y con el valor equivocado.
- **`tailwind build --force` y después `collectstatic`.** Son dos pasos y cada uno falla en
  silencio por su cuenta. Sin `--force`, el comando compara la fecha de `estilos/fuente.css`
  con la de la hoja compilada y responde «up to date»: cierto para la hoja fuente y falso
  para lo que importa, porque las clases salen de las **plantillas** y ésas no las mira. Y
  sin `collectstatic`, la reescritura de rutas del paso 2 apunta a `staticfiles/` —no a
  `assets/`—, así que se fotografía la hoja anterior. En los dos casos la captura sale
  perfecta y enseña el diseño de antes.

Para una pantalla con sesión basta `force_login` en el cliente. Y para un estado que no se
puede dejar en la base —dar de baja a un estudiante es irreversible por diseño (`DEC-7`)— se
envuelve todo en `transaction.atomic()` y se termina con `transaction.set_rollback(True)`: la
captura sale y la base queda como estaba.

**El punto de venta se mira a 1024 × 600** (`INT-2`) y la interfaz del acudiente a 390 px de
ancho (`INT-1`): son los aparatos para los que están diseñadas, no el monitor de quien
programa.

---

### [S5.3] Si tocas la infraestructura

**`docker compose up` tiene que levantar el stack en cualquier máquina, siempre** (`DT-37`).
Lo que lo rompe casi nunca es editar `compose.yaml` o el `Dockerfile`: es cambiar otra cosa
y no acordarse de ellos. Cuenta como infraestructura:

| Si cambias… | Revisa |
|---|---|
| Una variable que lee `config/settings.py` **sin `default=`** | `x-aplicacion.environment` de `compose.yaml` y `.env.example` |
| Una dependencia que necesita una librería del sistema | `Dockerfile` |
| `.python-version`, la versión de uv o `TAILWIND_CLI_VERSION` | `Dockerfile` (la de Tailwind se lee sola, pero hay que reconstruir) |
| Un paso que hay que hacer antes de servir —como `sincronizar_permisos`— | `docker/arrancar-aplicacion.sh` |
| El nombre o las opciones de un comando que el arranque llama | `docker/arrancar-aplicacion.sh` y `docker/vigilar-estilos.sh` |
| Un servicio nuevo —una cola, una caché— | `compose.yaml`, con su `healthcheck` y su `depends_on` |
| Una hoja de estilos nueva | `docker/vigilar-estilos.sh` |

**Dos cosas lo vigilan**, y ninguna depende de acordarse:

- **`config/tests_contenedor.py`**, dentro de la suite: una variable obligatoria que el compose
  no da, `localhost` donde tiene que ir un nombre de servicio, la versión de Python, el `.env`
  dentro de la imagen, un comando del arranque que ya no existe.
- **El flujo `integracion-continua` de la CI**, en cada PR: levanta el stack desde cero
  —sin `.env`, sin imágenes, sin volúmenes—, comprueba que sirve páginas y hojas, que sembró y
  que una fotografía firmada se abre desde fuera.

Para comprobarlo en local antes de subir, **sin tocar tu base**: un nombre de proyecto
distinto da volúmenes nuevos.

```bash
docker compose down                                    # libera los puertos; conserva tus datos
docker compose -p smartfood-limpio up -d --wait --wait-timeout 420
curl -f http://localhost:8000/salud/
docker compose -p smartfood-limpio down -v             # borra SOLO los volúmenes de la prueba
docker compose up -d                                   # vuelve a lo tuyo
```

---

## [S6] Cuando algo no arranca

| Síntoma | Causa probable |
|---|---|
| `connection refused` al puerto 5432 | `docker compose up -d` no está levantado |
| `port is already allocated` al levantar | Algo del host ocupa el puerto: otro `runserver`, otro PostgreSQL. Ciérralo o cambia el puerto (`[S1.0.1]`) |
| `Permission denied` al escribir `assets/css/` desde el host | Los contenedores escribieron con otro usuario: pon tu `UID` y `GID` en `.env` (`[S1.0.1]`) |
| `app` no llega a estar sano | `docker compose logs app`: casi siempre, una migración o `sembrar` que falla |
| `ModuleNotFoundError` en el contenedor tras un `git pull` | La imagen es anterior al `uv.lock`: `docker compose up -d` la reconstruye; con `start` o `restart` no |
| La fotografía de un estudiante no carga, y en el host sí | Falta `S3_ENDPOINT_URL_PUBLICO`: la URL se firmó contra `seaweedfs:8333`, que el navegador no resuelve (`DT-37`) |
| `Missing staticfiles manifest entry` en las pruebas | Nadie ha corrido `collectstatic` en este clon: el ejecutor fuerza `DEBUG=False` y el manifiesto hace falta. El compose lo hace al arrancar; en el host, a mano |
| `the database system is starting up` | PostgreSQL despertando; reintenta en unos segundos |
| Una clase de Tailwind no se aplica | Falta `tailwind build` o `tailwind watch` |
| `tailwind build` dice «up to date» y la clase sigue sin estar | Solo mira la fecha de `fuente.css`, no la de las plantillas: usa `--force` |
| Una consulta de contenedor no se aplica y la rejilla queda en una columna | `@container` está en el MISMO elemento que la rejilla; va en el envoltorio |
| Una clase de color no pinta nada, y no hay error | Es de la paleta de fábrica, que está borrada: usa un alias (`DT-23`) |
| El tema oscuro se queda pegado | La preferencia vive en `localStorage`; el selector de la barra la cambia |
| El correo no aparece | Míralo en http://localhost:8025, no en tu bandeja. Si tampoco está ahí, `docker compose logs app`: un fallo de envío queda registrado y no tumba el alta |
| Pido recuperar la contraseña y no llega nada a Mailpit | Es lo correcto si la cuenta no existe, está desactivada o no ha definido contraseña: la pantalla no lo distingue a propósito (`[S2.4.1]`) |
| `NoSuchBucket` al subir una imagen | `docker compose down -v` borró el bucket; vuelve a levantar |
| Las fotografías y las imágenes de producto no cargan tras actualizar la rama | La base viene de cuando el almacenamiento era MinIO, y sus objetos no están en SeaweedFS (`DT-38`): `docker compose down -v` y `up` —datos ficticios, se resiembran solos— |
| Al levantar, `port is already allocated` en el 9000 | Sigue vivo el contenedor de MinIO de antes de `DT-38`: `docker compose up -d --remove-orphans` |
| `seaweedfs` no llega a estar sano y el API responde desde fuera | El healthcheck usa `localhost`, que dentro del contenedor es `::1`, y SeaweedFS escucha solo en IPv4: va con `127.0.0.1` |
| El admin dice que no existe la tabla | Falta `migrate` |
| El admin da 403 sobre un modelo nuevo | La matriz `[S11]` cambió y falta `sincronizar_permisos` |
