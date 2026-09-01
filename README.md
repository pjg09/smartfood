# SmartFood

Prototipo de plataforma de gestión para cafeterías escolares: billetera por estudiante,
control parental de gasto y alérgenos, punto de venta con lector de código de barras e
inventario trazable.

Proyecto de la asignatura *Proyecto Aplicado en TIC 1* — UPB, 202601. Equipo de cuatro,
cinco sprints de dos semanas.

**Django 6.1 · PostgreSQL 17 · HTMX · Tailwind · MinIO**

---

## Estado

| | |
|---|---|
| Sprint | **1 de 5** — registro, perfiles, vinculación y catálogo |
| Avance | 42 de 56 tareas · 18 de 24 Pull Requests |
| Entorno desplegado | ⏸ **congelado** — ver abajo |

> **El entorno desplegado está congelado desde el 2026-08-30** y su despliegue automático
> está desconectado. El plan gratuito del proveedor no lo sostiene: la base de datos se
> duerme y al despertar rechaza conexiones, y desactivarlo no está permitido en ese plan.
> No es un fallo del código. El motivo completo y las dos salidas posibles están en
> [`docs/despliegue.md`](./docs/despliegue.md).
>
> Mientras dure, `DoD-4` —demostrar en el entorno desplegado— está **suspendido**, y cada
> PR declara cómo se verificó en local. **Todo funciona en local**, así que el desarrollo
> no está bloqueado.

---

## Puesta en marcha

Dos herramientas: [Docker](https://docs.docker.com/get-docker/) con Compose y
[uv](https://docs.astral.sh/uv/getting-started/installation/). Nada más — uv descarga la
versión de Python que hace falta.

```bash
git clone git@github.com:pjg09/smartfood.git
cd smartfood

cp .env.example .env      # los valores por defecto sirven tal cual en local
docker compose up -d      # PostgreSQL, MinIO y el bucket
uv sync                   # dependencias exactas de uv.lock

uv run python manage.py migrate
uv run python manage.py sembrar --contrasena-de-desarrollo 'smartfood-local-2026'
uv run python manage.py runserver
```

En `http://localhost:8000`, y la administración en `/admin/` con
`institucion@example.com` / `smartfood-local-2026`.

**Los comandos del día a día, las credenciales y qué hacer cuando algo no arranca están
en [`docs/desarrollo.md`](./docs/desarrollo.md)**, que es la guía completa. Aquí solo está
lo justo para levantarlo.

---

## La documentación es el contrato

`docs/` no es decorativa: es donde vive lo que el sistema debe hacer y por qué. Ninguna
afirmación se inventa — cada una cita el identificador del que sale.

**Qué es el sistema**

| Documento | Para qué |
|---|---|
| [`smartfood.md`](./docs/smartfood.md) | El anteproyecto: problema, objetivos, alcance, invariantes, matriz de permisos |
| [`decisiones-de-alcance.md`](./docs/decisiones-de-alcance.md) | Lo acordado **después** del anteproyecto (`DEC-1` … `DEC-11`) |
| [`decisiones-tecnicas.md`](./docs/decisiones-tecnicas.md) | Arquitectura, stack y modelo de datos (`DT-1` … `DT-21`) |
| [`backlog-historias-de-usuario.md`](./docs/backlog-historias-de-usuario.md) | Las 59 historias con sus criterios de aceptación |

> **El alcance vigente es `[S9.1]` de `smartfood.md` MÁS `[S1]` de `decisiones-de-alcance.md`.**
> Once decisiones amplían el anteproyecto y no están incorporadas a él: para saber qué hace
> y qué no hace el sistema hay que mirar los dos.

**Cómo se está construyendo**

| Documento | Para qué |
|---|---|
| [`sprint-1-backlog.md`](./docs/sprint-1-backlog.md) | Las 56 tareas del sprint en curso, con responsable y estado |
| [`plan-de-pull-requests.md`](./docs/plan-de-pull-requests.md) | Esas 56 tareas agrupadas en 24 PR, y el estado de cada una |
| [`definicion-de-terminado.md`](./docs/definicion-de-terminado.md) | Los seis criterios de cierre (`DoD-1` … `DoD-6`) |

**Cómo se trabaja**

| Documento | Para qué |
|---|---|
| [`desarrollo.md`](./docs/desarrollo.md) | Reconstrucción local, credenciales y comandos |
| [`convenciones-de-git.md`](./docs/convenciones-de-git.md) | Ramas, commits y publicación de versiones |
| [`despliegue.md`](./docs/despliegue.md) | Estado del entorno desplegado, sus restricciones y sus trampas |
| [`recorrido-de-administracion-de-estudiantes.md`](./docs/recorrido-de-administracion-de-estudiantes.md) | Recorrido de experiencia de usuario de la vista de estudiantes (`TT-35`) |
| [`formato-de-carga.md`](./docs/formato-de-carga.md) | Contrato del archivo de carga de estudiantes |

---

## Tres cosas que no se negocian

**Datos ficticios, siempre.** Ningún dato real de ningún estudiante entra en este
repositorio ni en ningún entorno. No es una preferencia: es la Ley 1581 de 2012 sobre
tratamiento de datos de menores, y es la razón por la que el prototipo no se despliega en
un colegio real. Las fotografías son avatares generados.

**Nadie se registra.** No hay ninguna ruta de registro y no la habrá. Toda cuenta nace de
un alta hecha por otro actor más una invitación por correo con la que el titular define su
propia clave. Hay una prueba que recorre el mapa de URL entero y falla si aparece una.

**Quince invariantes.** Están en `[S10.2]` de `smartfood.md` y `[S2]` de
`decisiones-de-alcance.md`. Las que más condicionan el código: el saldo y las existencias
**no son columnas**, se reconstruyen del historial; ninguna venta deja saldo negativo; el
bloqueo por alérgeno se evalúa sobre la condición y nunca sobre una lista materializada.

Si una tarea parece exigir romper una invariante, **no la rompas: dilo.** Es señal de que
la tarea está mal entendida o de que falta una decisión.

---

## Cómo entra el código

`main` está protegida: **todo entra por Pull Request**, con revisión y squash merge. Ramas
cortas, commits en Conventional Commits —son los que disparan el versionado—. El detalle
está en [`convenciones-de-git.md`](./docs/convenciones-de-git.md).

Antes de abrir un PR, los tres tienen que pasar:

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py test
```
