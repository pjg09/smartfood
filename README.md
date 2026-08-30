# SmartFood

Prototipo de plataforma de gestión para cafeterías escolares: billetera por estudiante,
control parental de gasto y alérgenos, punto de venta con lector de código de barras e
inventario trazable.

Proyecto de la asignatura *Proyecto Aplicado en TIC 1* — UPB, 202601.

**Django 6.1 · PostgreSQL 17 · HTMX · Tailwind · MinIO**

> La documentación del proyecto está en [`docs/`](./docs). No es decorativa: es el
> contrato. Empieza por [`docs/smartfood.md`](./docs/smartfood.md) y
> [`docs/decisiones-tecnicas.md`](./docs/decisiones-tecnicas.md).

---

## Puesta en marcha

Necesitas **dos** cosas instaladas: [Docker](https://docs.docker.com/get-docker/) con
Compose, y [uv](https://docs.astral.sh/uv/getting-started/installation/). Nada más —
uv descarga la versión de Python que hace falta.

```bash
git clone git@github.com:pjg09/smartfood.git
cd smartfood

cp .env.example .env      # los valores por defecto sirven tal cual en local

docker compose up -d      # PostgreSQL y MinIO
uv sync                   # dependencias, exactamente las de uv.lock

uv run python manage.py check --database default   # comprueba la conexión
uv run python manage.py runserver
```

En `http://localhost:8000`. La consola de MinIO está en `http://localhost:9001`
(usuario y contraseña, los de tu `.env`).

### Comandos del día a día

| Qué | Comando |
|---|---|
| Levantar la infraestructura | `docker compose up -d` |
| Apagarla | `docker compose down` |
| Borrarla **con los datos** | `docker compose down -v` |
| Ver los registros | `docker compose logs -f postgres` |
| Consola de PostgreSQL | `uv run python manage.py dbshell` |
| Servidor de desarrollo | `uv run python manage.py runserver` |
| **Recompilar los estilos al vuelo** | `uv run python manage.py tailwind watch` |
| Compilar los estilos una vez | `uv run python manage.py tailwind build` |
| Añadir una dependencia | `uv add nombre-del-paquete` |

Trabajando en plantillas, deja `tailwind watch` corriendo en una segunda terminal: sin
él, una clase nueva no aparece en la hoja compilada y el cambio no se ve.

`uv run` activa el entorno virtual por ti: no hace falta `source .venv/bin/activate`.

---

## Almacenamiento de imágenes

La base guarda **la clave del objeto, nunca el binario** (`DT-18`).

| Almacenamiento | Contiene | Cómo llega al navegador |
|---|---|---|
| `privado/` | Fotografías de estudiantes (`HU-57`) | URL firmada, caduca en 5 min |
| `publico/` | Imágenes de producto (`HU-59`) | Servidas por la aplicación, caché larga |

**Un solo bucket con dos prefijos, y ninguno accesible sin credenciales** (`DT-21`). Los
buckets de Railway son privados sin excepción: no existe modo público en ningún plan. En
local, MinIO replica la misma topología —aunque sí soportaría un bucket público— porque
la razón de usar MinIO es que el control de acceso se comporte igual aquí que desplegado.

> `publico` significa **«no sensible»**, no «accesible sin credenciales». Ningún objeto
> del prototipo lo es.

El bucket local lo crea `docker compose` al levantar; no hay que tocar la consola de MinIO.

### Ninguna imagen se guarda tal cual

Todo lo que sube un usuario pasa por `config/imagenes.py`, que **la decodifica y la
vuelve a codificar desde cero** (`DT-20`). Eso hace tres cosas a la vez:

- **Valida por contenido.** La extensión y el `Content-Type` los elige quien sube el
  fichero: no son evidencia de nada.
- **Neutraliza los ficheros políglotos.** Al reconstruir la imagen desde sus píxeles, lo
  que no era píxel desaparece.
- **Retira el EXIF.** La foto de un menor tomada con un teléfono lleva dentro, por
  defecto, la ubicación GPS donde se tomó (`ALC-OUT-08`, Ley 1581 de 2012).

La orientación del EXIF se aplica **antes** de retirarlo, o las fotos de móvil saldrían
giradas. La salida es siempre WEBP, con el lado mayor limitado y nombre generado por el
servidor.

---

## Correo

Una sola variable describe el envío entero, igual que `DATABASE_URL` describe la base:

| Entorno | `EMAIL_URL` | Efecto |
|---|---|---|
| Local | `consolemail://` | El correo se imprime por la consola |
| Desplegado | `smtp+tls://resend:<clave>@smtp.resend.com:587` | Envío real por Resend |

**En local nadie necesita credenciales**, y ningún correo sale de una máquina de
desarrollo por accidente. Para probar la configuración:

```bash
uv run python manage.py sendtestemail tu-correo@ejemplo.com
```

Todo envío pasa por `config/correo.py`, **nunca por `send_mail` directamente**. Ese
módulo difiere el correo con `transaction.on_commit`: los servicios escriben dentro de
`transaction.atomic()` (`DT-15`), y un correo enviado dentro de la transacción sale
aunque esta se deshaga. En `HU-03` eso sería invitar a un acudiente cuya carga se
revirtió. Un correo no se puede deshacer; una fila sí.

> **Límite conocido del prototipo.** Resend en plan gratuito, sin dominio verificado,
> **solo entrega a la dirección del titular de la cuenta**. `HU-03` envía una invitación
> por acudiente cargado: en el entorno de pruebas llegarán todas a un único buzón. Es
> una limitación aceptada, no un defecto — los datos son ficticios (`ALC-OUT-07`) y
> ningún acudiente real existe.

---

## Dónde va cada cosa del frontend

Servidor renderiza, HTMX actualiza fragmentos, Tailwind compila con su binario autónomo.
**No hay Node ni `package.json`** (`DT-16`).

| Ruta | Qué es |
|---|---|
| `templates/base.html` | Tronco común del que cuelga toda página |
| `templates/partials/` | Fragmentos que devuelven las vistas HTMX — **nunca páginas** |
| `<app>/templates/<app>/` | Plantillas propias de cada dominio |
| `estilos/fuente.css` | **Fuente** de Tailwind: paleta, tipografía, `@source` |
| `assets/js/htmx.min.js` | HTMX 2.0.9, vendorizado, sin CDN |
| `assets/css/tailwind.css` | **Salida compilada.** No se versiona: la genera el build |

`estilos/` está fuera de `assets/` a propósito. Dentro, `collectstatic` recogería la
fuente y el almacenamiento con manifiesto fallaría al resolver su `@import
"tailwindcss"` — la construcción del despliegue se cae. El propio paquete lo avisa con
su comprobación `W001`.

`INT-3` no lleva plantillas: lo cubre el admin de Django (`DT-2`), aquí solo traducido.

---

## Entorno de pruebas

**https://web-production-3db23.up.railway.app** — `ENT-01`, desplegado en Railway
(`DT-13`). Se actualiza solo en cada integración a `main`.

| | |
|---|---|
| Salud del servicio | [`/salud/`](https://web-production-3db23.up.railway.app/salud/) — consulta la base, no solo el proceso |
| Proyecto en Railway | `smartfood` · `cd700c34-a0ca-42b6-86fb-f77a476aa9a3` |
| Región | `europe-west4` — ver la nota de abajo |
| Base de datos | PostgreSQL 18 gestionado, en la misma región |

Las variables (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DATABASE_URL`) viven en Railway.
**Ninguna está en el repositorio.**

> **Por qué Ámsterdam y no Virginia.** El plan gratuito de Railway bloquea los
> despliegues entre las 8:00 y las 20:00 de la hora local de cada región. Ámsterdam es
> la única cuya ventana libre —13:00 a 01:00 hora de Bogotá— cubre la tarde de trabajo
> del equipo. Es un apaño, no una decisión de arquitectura: con el plan Hobby el
> servicio vuelve a `us-east4`, que está a 70 ms de Bogotá en vez de 130 ms.

---

## Cuentas: nadie se registra

**No hay ninguna ruta de registro y no la habrá** (`INV-6`, `INVD-1`, `DT-10`). Toda
cuenta nace de un alta hecha por otro actor, **sin contraseña utilizable**, más una
invitación por correo con la que el titular define su propia clave (`DEC-3`). Quien crea
la cuenta no llega a conocer nunca esa clave.

La primera cuenta —la de la institución educativa— la crea el seed:

```bash
uv run python manage.py migrate
uv run python manage.py sembrar
```

`sembrar` es **idempotente**: en la segunda pasada no duplica nada ni reenvía el correo.
Con `EMAIL_URL=consolemail://` la invitación se imprime por la terminal; copia el enlace
`/invitacion/…` y ábrelo en el navegador.

Para dirigir la invitación a un buzón real al demostrar `HU-39`:

```bash
uv run python manage.py sembrar --email-institucion tu-correo@ejemplo.com
```

Los datos que siembra son ficticios (`ALC-OUT-07`). El dominio `example.edu.co` está
reservado por la RFC 2606 justamente para esto: nunca corresponde a un buzón real.

---

## Cómo se trabaja aquí

`main` está protegida: **todo entra por Pull Request**. Ramas cortas, squash merge y
commits en Conventional Commits, que son los que disparan el versionado.

| Documento | Para qué |
|---|---|
| [`docs/convenciones-de-git.md`](./docs/convenciones-de-git.md) | Ramas, commits y publicación de versiones |
| [`docs/plan-de-pull-requests.md`](./docs/plan-de-pull-requests.md) | Las 55 tareas del Sprint 1 en 24 PR, y el estado de cada una |
| [`docs/sprint-1-backlog.md`](./docs/sprint-1-backlog.md) | El sprint en curso |

---

## Datos ficticios, siempre

Ningún dato real de ningún estudiante entra en este repositorio ni en el entorno de
pruebas. No es una preferencia: es la Ley 1581 de 2012 sobre tratamiento de datos de
menores (`ALC-OUT-07`, `ALC-OUT-08`). Las fotografías del prototipo son avatares
generados (`INVD-6`).
