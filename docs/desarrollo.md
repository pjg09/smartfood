# SmartFood — Guía de desarrollo

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-DESARROLLO |
| titulo | Reconstrucción del entorno local, credenciales y comandos del día a día |
| tipo_documento | **Documento operativo.** No es un artefacto de Scrum ni un entregable |
| documentos_fuente | `./despliegue.md`; `./convenciones-de-git.md`; `./decisiones-de-alcance.md` (`DEC-10`) |
| actualizado | 2026-08-30 |
| idioma | es-CO |
| version | 1.0 |

Es la libreta del desarrollo: **cómo levantar el entorno desde cero, con qué se entra y
qué comandos hacen falta a diario.** Si `./despliegue.md` describe el entorno desplegado,
esto describe el tuyo.

---

## [S1] Reconstrucción desde cero

Probado tal cual el 2026-08-30. Dos herramientas instaladas: **Docker** con Compose y
[**uv**](https://docs.astral.sh/uv/getting-started/installation/). Nada más — uv descarga
el Python que hace falta.

```bash
git clone git@github.com:pjg09/smartfood.git
cd smartfood

cp .env.example .env          # los valores por defecto sirven tal cual

docker compose up -d          # PostgreSQL, MinIO y el bucket
uv sync                       # dependencias exactas de uv.lock

uv run python manage.py migrate
uv run python manage.py sembrar --contrasena-de-desarrollo 'smartfood-local-2026'

uv run python manage.py runserver
```

En `http://localhost:8000`. Administración en `/admin/`, salud en `/salud/`.

### [S1.1] Empezar de verdad de cero

`docker compose down` **conserva** los datos. Para borrarlos:

```bash
docker compose down -v        # -v borra los volúmenes: base y bucket
```

Después, repetir desde `docker compose up -d`.

> **`sembrar` es idempotente y no cambia lo que ya existe.** Si la institución ya está
> creada con otro correo, una segunda pasada **no** lo actualiza: solo restablece la
> contraseña. Para cambiar el correo hay que borrar la base.

---

## [S2] Con qué se entra

### [S2.1] Entorno local

| | |
|---|---|
| Interfaz | http://localhost:8000/admin/ |
| Usuario | `institucion@example.com` |
| Contraseña | `smartfood-local-2026` |
| Rol | `institucion` (`USR-5`), con acceso a la administración |

**Esta credencial se escribe aquí a propósito y no es un descuido.** Solo sirve contra
`localhost`, sobre datos ficticios (`ALC-OUT-07`), en una base que se borra con un
comando. No abre nada de nadie.

El dominio `example.com` está reservado por la **RFC 2606**: nadie puede registrarlo, así
que ningún correo dirigido ahí llega a una persona real.

### [S2.2] Entorno desplegado

| | |
|---|---|
| Interfaz | https://web-production-3db23.up.railway.app/admin/ |
| Usuario | `institucion@example.com` |
| Contraseña | **No está en este documento.** Ver abajo |

```bash
railway variables --service web --environment production --json | grep SEED_CONTRASENA
```

Esa variable es la **fuente de verdad**: el despliegue siembra la institución en cada
integración y restablece la contraseña a ese valor. Cambiarla desde el admin no dura
hasta el siguiente despliegue; para cambiarla de verdad, se cambia la variable.

**Está en Railway y no en el repositorio, deliberadamente.** El entorno desplegado es una
URL pública en internet y esa cuenta es superusuario del admin: escribir su clave aquí se
la daría a cualquiera con acceso al repositorio —hoy cuatro personas, mañana quien
evalúe— y quedaría en el historial de git para siempre.

### [S2.3] Por qué la institución tiene contraseña y las demás cuentas no

`DEC-10`. La dirección de la cuenta institucional no es de nadie: no hay quien abra esa
invitación. Y mandarla a una dirección inexistente produce un rebote que degrada la
reputación del remitente (`DEC-9`), justo la que hace falta intacta para lo único que sí
se demuestra por correo: la activación de un acudiente.

**Las cuentas de acudiente y de personal no tienen este atajo.** Se activan por
invitación, sin excepción (`HU-41`, `HU-03`, `INVD-1`). Quien crea esas cuentas no llega
a conocer nunca su clave, y eso no se relaja.

Para demostrar `HU-39` como está escrita —cuenta creada por seed, invitación por correo,
titular define su contraseña— se dirige la invitación a un buzón real:

```bash
uv run python manage.py sembrar --email-institucion tu-correo@ejemplo.com
```

---

## [S3] Comandos del día a día

`uv run` activa el entorno virtual: no hace falta `source .venv/bin/activate`.

| Qué | Comando |
|---|---|
| Levantar la infraestructura | `docker compose up -d` |
| Apagarla | `docker compose down` |
| Borrarla **con los datos** | `docker compose down -v` |
| Servidor de desarrollo | `uv run python manage.py runserver` |
| **Recompilar estilos al vuelo** | `uv run python manage.py tailwind watch` |
| Migrar | `uv run python manage.py migrate` |
| Crear migraciones | `uv run python manage.py makemigrations` |
| Pruebas | `uv run python manage.py test` |
| Consola de PostgreSQL | `uv run python manage.py dbshell` |
| Consola de Django | `uv run python manage.py shell` |
| Añadir dependencia | `uv add nombre-del-paquete` |
| Probar el correo | `uv run python manage.py sendtestemail tu@correo.com` |

Trabajando en plantillas, deja `tailwind watch` en una segunda terminal: sin él, una clase
nueva no aparece en la hoja compilada y el cambio no se ve.

---

## [S4] Qué hay levantado en local

| Servicio | Dónde | Credenciales |
|---|---|---|
| PostgreSQL | `localhost:5432` | `smartfood` / `smartfood-local`, base `smartfood` |
| MinIO (API S3) | `localhost:9000` | `smartfood` / `smartfood-local` |
| MinIO (consola) | http://localhost:9001 | las mismas |
| Bucket | `smartfood`, prefijos `privado/` y `publico/` | lo crea `docker compose` |
| Correo | Se imprime por la terminal | `EMAIL_URL=consolemail://` |

Todas ficticias y solo válidas contra los contenedores de `compose.yaml`.

**El correo no sale de tu máquina** mientras `EMAIL_URL` sea `consolemail://`. La
invitación aparece en la terminal donde corre `runserver` o el comando: copia el enlace
`/invitacion/…` y ábrelo en el navegador.

---

## [S5] Antes de abrir un Pull Request

`main` está protegida: todo entra por PR (`./convenciones-de-git.md`).

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run   # sin cambios sin migrar
uv run python manage.py test
```

Los tres tienen que pasar. El segundo es `DoD-3` y es el que más se olvida: un modelo
editado sin su migración no da error hasta que otra persona levanta el proyecto.

---

## [S6] Cuando algo no arranca

| Síntoma | Causa probable |
|---|---|
| `connection refused` al puerto 5432 | `docker compose up -d` no está levantado |
| `the database system is starting up` | PostgreSQL despertando; reintenta en unos segundos |
| Una clase de Tailwind no se aplica | Falta `tailwind build` o `tailwind watch` |
| El correo no aparece | Mira la terminal, no tu bandeja: en local va a consola |
| `NoSuchBucket` al subir una imagen | `docker compose down -v` borró el bucket; vuelve a levantar |
| El admin dice que no existe la tabla | Falta `migrate` |
