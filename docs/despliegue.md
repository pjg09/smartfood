# SmartFood — Topología de despliegue

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-DESPLIEGUE |
| titulo | Estado real del entorno de pruebas y cómo está montado |
| tipo_documento | **Documento operativo.** No es un artefacto de Scrum ni un entregable de la asignatura |
| documentos_fuente | `./decisiones-tecnicas.md` (`DT-13`, `DT-18`, `DT-20`, `DT-21`); `./convenciones-de-git.md`; `./definicion-de-terminado.md` (`DoD-4`) |
| actualizado | 2026-08-30 · **entorno congelado** |
| idioma | es-CO |
| version | 1.0 |

### [S0.1] ⏸ Entorno congelado desde el 2026-08-30

**El despliegue automático está desconectado y no debe tocarse Railway** hasta que Pedro
consulte con la docente si la asignatura exige un entorno desplegado.

El plan gratuito no lo sostiene, por dos fallos que **no son del código**:

1. **La base de datos duerme y no se puede evitar.** Al despertar rechaza conexiones con
   `FATAL: the database system is starting up`, y toda vista que toque el ORM devuelve
   500. Railway **prohíbe** desactivarlo: *«Free plan services must have
   "sleepApplication" set to "true" unless they have a cron schedule»*.
2. **`/app/staticfiles/` no existe en tiempo de ejecución**, aunque la construcción
   informa de «132 static files copied to '/app/staticfiles'». Toda página con
   `{% static %}` da 500. Candidato de arreglo **sin verificar**: mover `collectstatic`
   al `startCommand`. No rescata el entorno por sí solo: el fallo 1 sigue.

`DoD-4` quedó **suspendido** mientras tanto (`[S5]` de `./definicion-de-terminado.md`).
**Todo funciona en local**, así que el desarrollo no está bloqueado.

| Si la docente… | Qué hacer |
|---|---|
| **Exige despliegue** | Plan Hobby (~5 USD/mes). Resuelve el sueño **y** el bloqueo horario. Arreglar el fallo 2 y verificar |
| **No lo exige** | Limpiar: borrar el proyecto, quitar `railway.json`, y **retirar `ENT-01` y `TT-04`** del alcance con una decisión registrada |

> **Resto pendiente en la cuenta**, si se retoma: quedó un `preDeployCommand` con
> `migrate` como ajuste del servicio, de cuando se diagnosticaba. Con el `startCommand`
> actual correría dos veces —inofensivo, pero son dos fuentes de verdad—. Conviene
> quitarlo.

---

### [S0.2] Qué es y qué no es

Registra **lo que hay montado y por qué**, para que el contexto no viva solo en la
cabeza de quien lo montó. Si mañana se pierde la cuenta, o alguien —persona o agente—
llega al repositorio sin haber estado en las decisiones, esto es lo que necesita.

**No es el entregable de documentación técnica** (`ENT-03`, `ENT-06`). Ese se redactará
cuando se sepa qué forma tendrá y con qué criterio se evalúa. Esto es otra cosa: la
libreta del entorno.

**No decide nada.** Las decisiones están en `./decisiones-tecnicas.md` con su
identificador. Aquí solo se registra el estado y se cita de dónde sale.

---

## [S1] Qué hay montado

| Recurso | Valor |
|---|---|
| Proveedor | Railway — `DT-13` no lo fija, pero es el que se está usando |
| Proyecto | `smartfood` · `cd700c34-a0ca-42b6-86fb-f77a476aa9a3` |
| Entorno | `production` · `3b27f052-603b-4ceb-8afa-f1e304629753` |
| Servicio web | `web` · `dba5b8ef-04bb-4007-85e1-1d1f2462adb9` |
| Base de datos | `Postgres` · `3a0cd1dd-72fd-47d1-ae67-743e92f6c453` · PostgreSQL 18 gestionado |
| Bucket | `smartfood-privado` · `923dff5f-36e5-4b12-a35d-8881c15dee9e` · región `ams` |
| Región de los servicios | `europe-west4` — ver `[S2]` |
| URL | https://web-production-3db23.up.railway.app |
| Salud | `/salud/` — consulta la base, no solo el proceso |
| Origen del código | **Desconectado** el 2026-08-30. Era `pjg09/smartfood`, rama `main` |
| Plan | Gratuito — ver `[S2]` |

### [S1.1] Cómo se construye y arranca

En `railway.json`, versionado:

| Fase | Comando |
|---|---|
| Construcción | `manage.py tailwind build && manage.py collectstatic --noinput` |
| Arranque | `migrate` → `sembrar` → `gunicorn` |

> **`preDeployCommand` de `railway.json` se ignora en silencio.** Se probó: el plan que
> imprime Railpack en el registro de construcción muestra los pasos `install`, `build` y
> `Deploy`, **y ninguno de pre-despliegue**. `buildCommand` y `startCommand` del mismo
> fichero sí se aplican. El síntoma fue que las migraciones no se ejecutaron nunca y
> cualquier consulta al ORM devolvía 500, con el despliegue marcado como correcto.
>
> Como ajuste del servicio —fuera del repositorio— sí funciona, pero eso deja la
> configuración fuera de control de versiones. Por eso `migrate` y `sembrar` van
> encadenados en el `startCommand`, que sí se lee del fichero. Con una sola réplica no
> hay diferencia práctica; si algún día hubiera varias, habría que volver a mirarlo.

**El entorno se siembra solo.** El seed es idempotente y con contraseña **no envía
correo** (`DEC-10`), así que puede correr en cada despliegue: si hubiera que recrear el
entorno desde cero, la institución aparece sin que nadie ejecute nada a mano. La
contraseña se restablece en cada despliegue al valor de `SEED_CONTRASENA_INSTITUCION`,
que es la fuente de verdad — cambiarla desde el admin no dura.

Si esa variable no estuviera definida, el comando **genera una clave y la imprime en el
registro del despliegue** en lugar de caer al camino por defecto, que enviaría una
invitación a una dirección que no es de nadie. Falla del lado seguro.

> **`railway.json` está deprecado** en favor de `.railway/railway.ts`, y deja de
> funcionar el **2026-12-01**. Se decidió **no migrar**: el Sprint 5 termina alrededor
> del 2026-11-01, hay un mes de holgura, y `.railway/railway.ts` exige Node y el paquete
> npm `railway` —comprobado: `railway config pull` falla con `ERR_MODULE_NOT_FOUND`—,
> que es justo lo que este repositorio evita. La propia guía de Railway recomienda
> `railway.json` para repositorios sin TypeScript. **Revisar si el proyecto se alarga
> hasta diciembre**; `railway config migrate` traduce el fichero cuando haga falta.

---

## [S2] Las restricciones del plan gratuito, y qué obligan

Tres, y ninguna es un detalle.

### [S2.1] Los despliegues se bloquean 12 horas al día

El plan gratuito **no despliega entre las 8:00 y las 20:00 hora local de cada región**.

| Región | Ventana libre, en hora de Bogotá | Latencia aprox. |
|---|---|---|
| `us-east4` Virginia | 19:00 → 07:00 | ~70 ms |
| `us-west2` Oregón | 22:00 → 10:00 | ~110 ms |
| **`europe-west4` Ámsterdam** | **13:00 → 01:00** | ~130 ms |
| `southeast-asia` Singapur | 07:00 → 19:00 | ~280 ms |

**Por eso los servicios están en Ámsterdam y no en Virginia**, que estaría a la mitad de
latencia: es la única región cuya ventana libre cubre la tarde de trabajo del equipo.

> **Un merge a `main` antes de la 1 de la tarde hora de Bogotá falla el despliegue.**
> Con el plan Hobby desaparece el bloqueo y los servicios vuelven a `us-east4`.

### [S2.2] Un solo bucket por proyecto

`DT-18` preveía dos. Además, **los buckets de Railway son privados sin excepción y no
existe modo público en ningún plan**, así que la separación por política que preveía
`DT-18` no es realizable ni pagando. `DT-21` lo resuelve: un bucket con los prefijos
`privado/` y `publico/`, y dos almacenamientos lógicos en Django.

### [S2.3] Los servicios se duermen

`sleepApplication` está activo. **La primera petición tras un rato de inactividad
devuelve `503`** mientras PostgreSQL despierta; la siguiente ya responde. Es tolerable y
ahorra crédito.

> **Antes de una demostración o una Sprint Review, abre `/salud/` un par de veces para
> despertar la base.** Un `503` en mitad de una sustentación parece un sistema roto.

---

## [S3] Variables de entorno del servicio `web`

Los **nombres**; los valores viven solo en Railway y **ninguno está en el repositorio**.

| Variable | Para qué | Origen |
|---|---|---|
| `DJANGO_SECRET_KEY` | Firma de sesiones y tokens | Generada al montar el entorno |
| `DJANGO_DEBUG` | `False` en el entorno desplegado | Fijada a mano |
| `DATABASE_URL` | Conexión a PostgreSQL | Referencia `${{Postgres.DATABASE_URL}}` |
| `EMAIL_URL` | SMTP de Resend | Clave de API de Resend |
| `DJANGO_DEFAULT_FROM_EMAIL` · `DJANGO_EMAIL_TIMEOUT` | Remitente y tiempo límite | Fijadas a mano |
| `S3_ENDPOINT_URL` · `S3_BUCKET` · `S3_ACCESS_KEY_ID` · `S3_SECRET_ACCESS_KEY` · `S3_REGION` · `S3_ADDRESSING_STYLE` | Bucket | `railway bucket credentials` |
| `S3_CADUCIDAD_FIRMA` | Segundos que vive la URL firmada de una fotografía | Fijada a mano |
| `SEED_CONTRASENA_INSTITUCION` | Contraseña de la cuenta institucional (`DEC-10`) | Generada al sembrar |
| `DJANGO_NIVEL_DE_REGISTRO` | Nivel del registro raíz; `INFO` por defecto | Opcional |
| `RAILWAY_PUBLIC_DOMAIN` | El dominio del servicio | La inyecta Railway |

`config/settings.py` lee `RAILWAY_PUBLIC_DOMAIN` para completar `ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS` y `URL_BASE`. En local no existe y se usan los valores por
defecto.

---

## [S4] Trampas que ya costaron un rato

Registradas para que no vuelvan a costarlo.

| Trampa | Qué pasa | Cómo se resuelve |
|---|---|---|
| **`preDeployCommand` de `railway.json` se ignora** | Las migraciones no corren, el despliegue se marca correcto y toda consulta al ORM da 500 | Encadenarlo en el `startCommand` |
| **Un 500 no deja rastro** | Sin `LOGGING`, Django manda los errores a `mail_admins`; con `ADMINS` vacío se descartan en silencio | `LOGGING` con salida estándar, en `config/settings.py` |
| **`railway service scale` acumula** | Añade regiones en vez de sustituirlas; el servicio acaba con réplicas en tres y el despliegue falla por la región bloqueada | Poner a cero las que sobran: `us-east=0 us-west=0 eu-west=1` |
| **La sonda de salud va por HTTP interno** | Sin la cabecera `X-Forwarded-Proto`, `SECURE_SSL_REDIRECT` le devuelve `301` y el despliegue se marca como fallido con la aplicación viva | `SECURE_REDIRECT_EXEMPT = [r"^salud/$"]` |
| **La sonda manda `Host: healthcheck.railway.app`** | Sin estar en `ALLOWED_HOSTS`, responde `400` | Se añade junto al dominio público |
| **La fuente de Tailwind dentro de `STATICFILES_DIRS`** | `collectstatic` la recoge y el almacenamiento con manifiesto falla al resolver su `@import` | La fuente vive en `estilos/`, fuera de `assets/` |
| **La clave de API de Resend es de solo envío** | No permite consultar el estado de entrega | La confirmación de que un correo llegó es la bandeja, no la API |

---

## [S5] Cómo se reconstruiría desde cero

Si hubiera que rehacer el entorno:

1. Crear el proyecto y el PostgreSQL gestionado.
2. Crear el servicio web y **conectarlo al repositorio, rama `main`** — esto ya dispara
   el primer despliegue.
3. Generar el dominio **antes** de desplegar, para que `RAILWAY_PUBLIC_DOMAIN` exista ya
   durante la construcción.
4. Mover ambos servicios a la región elegida, **poniendo a cero las demás** (`[S4]`).
5. Crear el bucket en la misma región y volcar sus credenciales a las variables `S3_*`.
6. Fijar el resto de variables de `[S3]`. `DJANGO_SECRET_KEY` se genera nueva.
7. Fijar `SEED_CONTRASENA_INSTITUCION` con una clave generada. **La institución la siembra
   el propio despliegue**: no hay paso manual.

Para demostrar `HU-39` tal como está escrita —invitación por correo y titular que define
su contraseña— se ejecuta aparte, contra un buzón real:
`manage.py sembrar --email-institucion <buzón real>`. Eso sí dispara un correo, y por eso
no forma parte del despliegue.

---

## [S6] Qué está pendiente de decidir

- **Plan Hobby.** Resolvería el bloqueo horario y devolvería los servicios a `us-east4`.
  Pedro lo consulta con el equipo.
- **Rotación de la clave de Resend.** La clave pasó por una conversación con un agente.
  Funciona; conviene rotarla si el historial se comparte.
- **`railway.json` después del 2026-12-01.** Ver `[S1.1]`.
