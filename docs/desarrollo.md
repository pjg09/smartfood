# SmartFood — Guía de desarrollo

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-DESARROLLO |
| titulo | Reconstrucción del entorno local, credenciales y comandos del día a día |
| tipo_documento | **Documento operativo.** No es un artefacto de Scrum ni un entregable |
| documentos_fuente | `./despliegue.md`; `./convenciones-de-git.md`; `./decisiones-de-alcance.md` (`DEC-9`, `DEC-10`, `DEC-11`, `DEC-12`) |
| actualizado | 2026-08-31 |
| idioma | es-CO |
| version | 1.1 |

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
| Interfaz | http://localhost:8000/admin/ (`INT-3`) o http://localhost:8000/acceso/ |
| Usuario | `institucion@example.com` |
| Contraseña | `smartfood-local-2026` |
| Rol | `institucion` (`USR-5`), con acceso a la administración |

**Hay dos puertas y no son intercambiables** (`TT-56`, `DEC-12`). `/admin/login/` exige
`is_staff` y solo sirve a la institución y al personal de la cafetería. `/acceso/` es la
pantalla común a los cuatro roles y es **la única por la que entra el acudiente**, que no
accede a la administración porque `INT-1` no es el admin (`DT-2`).

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
URL pública en internet y esa cuenta administra el sistema entero: escribir su clave aquí
se la daría a cualquiera con acceso al repositorio —hoy cuatro personas, mañana quien
evalúe— y quedaría en el historial de git para siempre.

**No es superusuario de Django**, eso sí, desde el 2026-08-31: tiene exactamente los
permisos que declara `cuentas/permisos.py` y no puede editar los grupos con los que
`DT-11` sostiene `INV-4`. El razonamiento está en `UX-6` de
`./recorrido-de-administracion-de-estudiantes.md`. Si algún día el admin le devuelve un
`403` sobre algo que debería poder hacer, el sitio donde se arregla es la matriz, no la
cuenta.

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

### [S2.4] Entrar como acudiente

Los acudientes nacen de la carga masiva (`HU-01`) y su invitación **se genera pero no se
entrega** (`DEC-9`): sus direcciones son ficticias y no hay buzón que las reciba. Hay dos
caminos, y sirven para cosas distintas.

**Para demostrar `HU-03`** —el recorrido real: invitación, contraseña propia, acceso—, se
carga el archivo normalmente y se saca el enlace de un acudiente concreto:

```bash
uv run python manage.py invitacion marta.ruiz@example.com
```

Imprime la URL de `/invitacion/…`. Se abre en el navegador, se define la contraseña y se
entra por `/acceso/`. **Ese enlace es una credencial**: quien lo tenga puede fijar la
contraseña de esa cuenta. Por eso se saca de uno en uno desde la terminal y no se lista en
ninguna pantalla (`DEC-3`).

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

Después, `/acceso/` con el correo del acudiente y esa contraseña lleva a
`/mis-estudiantes/` (`TT-29`, `HU-04`).

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
otro estado y sí tiene vuelta. La baja no se deshace: la reactivación de `HU-49` es de la
desactivación, que es un tercer estado y llega en el Sprint 2.

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
| **Sacar un enlace de invitación** | `uv run python manage.py invitacion correo@example.com` |

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

Eso vale para las altas de una en una, que **sí** mandan correo. La carga masiva no manda
ninguno (`DEC-9`), así que ahí no hay nada que copiar de la terminal: el enlace se saca con
`manage.py invitacion` (`[S2.4]`).

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
