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
| Añadir una dependencia | `uv add nombre-del-paquete` |

`uv run` activa el entorno virtual por ti: no hace falta `source .venv/bin/activate`.

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

## Todavía no se ejecuta `migrate`

**Es deliberado, no un olvido.** `TT-09` declara el modelo de usuario propio, y Django
exige fijar `AUTH_USER_MODEL` **antes de la primera migración**. Si alguien ejecuta
`migrate` ahora, se crean las tablas de `django.contrib.auth` con el usuario por
defecto y cambiarlo después obliga a **borrar la base de datos a los cuatro
integrantes**.

Hasta que `PR-08` esté integrado, para comprobar que la base responde usa:

```bash
uv run python manage.py check --database default
```

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
