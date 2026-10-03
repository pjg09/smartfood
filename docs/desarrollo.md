# SmartFood — Guía de desarrollo

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-DESARROLLO |
| titulo | Reconstrucción del entorno local, credenciales, comandos del día a día y la comprobación desde cero |
| tipo_documento | **Documento operativo.** No es un artefacto de Scrum ni un entregable |
| documentos_fuente | `./despliegue.md`; `./convenciones-de-git.md`; `./decisiones-de-alcance.md` (`DEC-9` … `DEC-12`, `DEC-15`); `./decisiones-tecnicas.md` (`DT-37`, `DT-38`) |
| actualizado | 2026-10-02 |
| idioma | es-CO |
| version | 1.5 |

Es la libreta del desarrollo: **cómo levantar el entorno desde cero, con qué se entra y
qué comandos hacen falta a diario.** Es el único entorno que hay: `DEC-15` retiró el
despliegue y `./despliegue.md` explica por qué.

**Cómo poner a prueba cada funcionalidad** —entrar como acudiente, recuperar una contraseña,
reservar, entregar, mermas, alertas— está en `./probar-cada-funcionalidad.md`.

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
cambiaste la contraseña de una de esas cuentas —recuperándola (`[S2]` de
`./probar-cada-funcionalidad.md`), por ejemplo—, se queda la nueva.

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

---

## [S2] Con qué se entra

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
(`[S1]` de `./probar-cada-funcionalidad.md`, `DEC-18`). Son los que aparecen arriba como
«solo por invitación», y son los únicos con los que se puede demostrar `HU-03`.

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
| Consola de PostgreSQL | `docker compose exec postgres psql -U smartfood -d smartfood` —`manage dbshell` no: la imagen no lleva `psql`— |
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

Todo entra por PR (`./convenciones-de-git.md`). Es una convención: `main` no tiene protección
activa en GitHub, así que nada rechaza un `push` directo, y desde `DT-39` tampoco hay CI que
corra estos tres comandos por ti.

```bash
docker compose exec app python manage.py check
docker compose exec app python manage.py makemigrations --check --dry-run   # sin cambios sin migrar
docker compose exec app python manage.py test --noinput
```

Los tres tienen que pasar —con `uv run python manage.py …` en el host, lo mismo—. **Nadie
los repite después**: la CI ya no corre pruebas y la versión se publica igual (`DT-39`,
`[S3.0]` de `./convenciones-de-git.md`), así que lo que no pasó aquí llega a `main` roto. **Y si el
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

**Dos cosas lo vigilan**, y la segunda depende de acordarse de correrla (`DT-39`):

- **`config/tests_contenedor.py`**, dentro de la suite: una variable obligatoria que el compose
  no da, `localhost` donde tiene que ir un nombre de servicio, la versión de Python, el `.env`
  dentro de la imagen, un comando del arranque que ya no existe.
- **`docker/comprobar-desde-cero.sh`**, a mano y antes de subir: levanta el stack desde cero
  —sin `.env` y sin volúmenes—, comprueba que sirve páginas y hojas, que sembró, que una
  fotografía firmada se abre desde fuera y que cada imagen sigue en su registro. La receta,
  abajo.

Para comprobarlo en local antes de subir, **sin tocar tu base**: un nombre de proyecto
distinto da volúmenes nuevos.

```bash
docker compose down                                    # libera los puertos; conserva tus datos
docker compose -p smartfood-limpio up -d --wait --wait-timeout 420
curl -f http://localhost:8000/salud/
docker compose -p smartfood-limpio down -v             # borra SOLO los volúmenes de la prueba
docker compose up -d                                   # vuelve a lo tuyo
```

**Y la comprobación entera, antes de subir: `docker/comprobar-desde-cero.sh`.** Es lo que
hacía el trabajo `pruebas` de la CI hasta que `DT-39` lo retiró, con los mismos pasos:
pregunta al registro por cada imagen —lo que un `up` en tu máquina no ve, porque las tienes en
caché—, valida el compose con el mínimo, levanta desde cero, comprueba páginas, hojas,
fotografías firmadas y correo, y corre `check`, migraciones y la suite. Trabaja sobre una
copia del árbol —con lo que no has commiteado— y con otro nombre de proyecto, así que tu base
no se toca; **se niega a correr** con el nombre de tu stack, que al terminar borraría tus
volúmenes. Tarda unos seis minutos.

```bash
docker compose down                                   # libera los puertos; conserva tus datos
docker/comprobar-desde-cero.sh
docker compose up -d                                  # vuelve a lo tuyo
```

Termina con `RESULTADO: VERDE` o `FALLO`; si falla, vuelca los registros de todos los
servicios. **Es la única comprobación que queda de que el stack levanta en otra máquina**, y
esa es la condición de que el prototipo se pueda demostrar (`DEC-15`): córrelo siempre que el
PR toque la infraestructura, y antes de cada entrega aunque no la haya tocado.

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
| Pido recuperar la contraseña y no llega nada a Mailpit | Es lo correcto si la cuenta no existe, está desactivada o no ha definido contraseña: la pantalla no lo distingue a propósito (`[S2]` de `./probar-cada-funcionalidad.md`) |
| `NoSuchBucket` al subir una imagen | `docker compose down -v` borró el bucket; vuelve a levantar |
| Las fotografías y las imágenes de producto no cargan tras actualizar la rama | La base viene de cuando el almacenamiento era MinIO, y sus objetos no están en SeaweedFS (`DT-38`): `docker compose down -v` y `up` —datos ficticios, se resiembran solos— |
| Al levantar, `port is already allocated` en el 9000 | Sigue vivo el contenedor de MinIO de antes de `DT-38`: `docker compose up -d --remove-orphans` |
| `seaweedfs` no llega a estar sano y el API responde desde fuera | El healthcheck usa `localhost`, que dentro del contenedor es `::1`, y SeaweedFS escucha solo en IPv4: va con `127.0.0.1` |
| El admin dice que no existe la tabla | Falta `migrate` |
| El admin da 403 sobre un modelo nuevo | La matriz `[S11]` cambió y falta `sincronizar_permisos` |
