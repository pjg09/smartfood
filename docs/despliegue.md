# SmartFood — Por qué no hay entorno desplegado

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-DESPLIEGUE |
| titulo | Por qué el prototipo no se despliega, y qué quedaría por hacer si algún día se retoma |
| tipo_documento | **Documento operativo.** No es un artefacto de Scrum ni un entregable de la asignatura |
| documentos_fuente | `./decisiones-de-alcance.md` (`DEC-15`); `./decisiones-tecnicas.md` (`DT-13`, `DT-18`, `DT-21`, `DT-31`); `./definicion-de-terminado.md` (`DoD-4`) |
| actualizado | 2026-09-17 · **sin entorno desplegado, por decisión** |
| idioma | es-CO |
| version | 2.0 |

### [S0.1] El estado, en una línea

**El prototipo se ejecuta en local y no hay nada desplegado en internet.** Lo decidió
`DEC-15` el 2026-09-17, después de que la consulta con la docente confirmara que la
asignatura no exige entorno desplegado. `DT-31` retira el PaaS que `DT-13` había
decidido.

Lo que eso implica, en concreto:

| | |
|---|---|
| `ENT-01` | Se entrega **sin** la condición «desplegado en un entorno de pruebas». Todo lo demás del entregable sigue igual |
| `DoD-4` | **Vigente, no suspendido.** Pide demostrar ejecutándolo, con la salida real del comando |
| `TT-04` | Sin efecto. Se hizo y se cerró en el Sprint 1; lo que se retira es su resultado |
| `TT-137` | Cerrada por la decisión contraria a la que preveía: se retira en vez de restaurarse |
| El Avance 2 | Se demuestra desde un portátil del equipo, con el recorrido de `./mapa-de-la-aplicacion.md` |

> **Queda una acción fuera del repositorio:** eliminar el proyecto en la consola del
> proveedor. Hasta que se haga, ahí sigue habiendo un proyecto congelado con su base y su
> bucket. **No se despliega nada en él**, y la rama `main` ya no está conectada como
> origen de código desde el 2026-08-30.

---

### [S0.2] Qué es este documento

**La libreta de un entorno que existió y ya no.** Registra por qué se montó, por qué se
retiró y qué haría falta para rehacerlo, de modo que la decisión no haya que reconstruirla
de memoria si el proyecto se alarga o alguien pregunta en la sustentación.

**No decide nada.** Las decisiones están en `./decisiones-de-alcance.md` y
`./decisiones-tecnicas.md` con su identificador. Aquí solo se registra el estado y se cita
de dónde sale.

Para levantar el entorno **local**, que es el único que hay, el documento es
`./desarrollo.md`.

---

## [S1] Por qué se retiró

Tres hechos, en el orden en que ocurrieron.

**1. El plan gratuito del proveedor no sostenía el entorno.** Dos fallos, y ninguno era
del código:

- **La base de datos duerme y no se puede evitar.** Al despertar rechaza conexiones con
  `FATAL: the database system is starting up`, y toda vista que toque el ORM devuelve
  500. El proveedor **prohíbe** desactivarlo: *«Free plan services must have
  "sleepApplication" set to "true" unless they have a cron schedule»*.
- **`/app/staticfiles/` no existía en tiempo de ejecución**, aunque la construcción
  informara de «132 static files copied to '/app/staticfiles'». Toda página con
  `{% static %}` daba 500. El arreglo candidato —mover `collectstatic` al `startCommand`—
  **nunca se verificó**, y no rescataba el entorno por sí solo: el primer fallo seguía.

El entorno se congeló el 2026-08-30 y `DoD-4` quedó suspendido con él.

**2. La única salida técnica era pagar.** El plan Hobby (~5 USD/mes) resolvía las dos
causas y, de paso, el bloqueo horario de `[S2]`. No había arreglo desde el repositorio.

**3. La asignatura no lo exige.** Esa era la condición de caducidad que la propia caja de
`DoD-4` se puso: consultar con la docente antes de gastar dinero o tiempo. La consulta se
resolvió el 2026-09-17 y la respuesta hizo innecesario el gasto. `DEC-15` recoge la
decisión.

> **La planeación del Sprint 4 describía un obstáculo más benigno del que era.** `[S3]` de
> `./sprint-4-backlog.md` y `[S3.1]` de `./plan-de-pull-requests-sprint-4.md` presentaban
> el bloqueo horario como el impedimento —«una restricción de ventana horaria, no de
> dinero»— cuando el impedimento real eran los dos fallos de arriba, que sí son de dinero.
> Los dos documentos quedan corregidos al cerrar `TT-137`. Vale la pena recordarlo: el
> obstáculo estaba registrado aquí desde agosto y la planeación no lo leyó.

---

## [S2] Las tres restricciones que tuvo el plan gratuito

Se conservan porque explican decisiones que siguen vigentes, `DT-21` entre ellas.

### [S2.1] Los despliegues se bloqueaban 12 horas al día

El plan gratuito **no despliega entre las 8:00 y las 20:00 hora local de cada región**.

| Región | Ventana libre, en hora de Bogotá | Latencia aprox. |
|---|---|---|
| `us-east4` Virginia | 19:00 → 07:00 | ~70 ms |
| `us-west2` Oregón | 22:00 → 10:00 | ~110 ms |
| **`europe-west4` Ámsterdam** | **13:00 → 01:00** | ~130 ms |
| `southeast-asia` Singapur | 07:00 → 19:00 | ~280 ms |

Por eso los servicios estaban en Ámsterdam y no en Virginia, que estaba a la mitad de
latencia: era la única región cuya ventana libre cubría la tarde de trabajo del equipo.

### [S2.2] Un solo bucket por proyecto

`DT-18` preveía dos. Además, **los buckets del proveedor son privados sin excepción y no
existe modo público en ningún plan**, así que la separación por política que preveía
`DT-18` no era realizable ni pagando. `DT-21` lo resolvió con un bucket y dos prefijos,
`privado/` y `publico/`, y dos almacenamientos lógicos en Django.

> **`DT-21` sigue vigente y no depende del proveedor.** En local esa topología es MinIO en
> el mismo `docker compose` que PostgreSQL, que es lo que el equipo usa desde `TT-02`.

### [S2.3] Los servicios se dormían

Es el fallo 1 de `[S1]`. Se registró primero como molestia tolerable —«la primera petición
tras un rato devuelve `503` y la siguiente ya responde»— y resultó ser lo que hizo
inviable el entorno, porque quien no responde al despertar es PostgreSQL, no el proceso
web.

---

## [S3] Qué había montado, si algo hiciera falta recuperarlo

| Recurso | Valor |
|---|---|
| Proveedor | Railway |
| Proyecto | `smartfood` · `cd700c34-a0ca-42b6-86fb-f77a476aa9a3` |
| Entorno | `production` · `3b27f052-603b-4ceb-8afa-f1e304629753` |
| Servicio web | `web` · `dba5b8ef-04bb-4007-85e1-1d1f2462adb9` |
| Base de datos | `Postgres` · `3a0cd1dd-72fd-47d1-ae67-743e92f6c453` · PostgreSQL 18 gestionada |
| Bucket | `smartfood-privado` · `923dff5f-36e5-4b12-a35d-8881c15dee9e` · región `ams` |
| Región de los servicios | `europe-west4` |
| URL | `https://web-production-3db23.up.railway.app` — **ya no se mantiene** |
| Origen del código | **Desconectado** el 2026-08-30. Era `pjg09/smartfood`, rama `main` |

**Las variables del servicio `web`** —sus nombres; ningún valor estuvo nunca en el
repositorio— eran `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DATABASE_URL`, `EMAIL_URL`,
`DJANGO_DEFAULT_FROM_EMAIL`, `DJANGO_EMAIL_TIMEOUT`, las seis `S3_*` del bucket,
`S3_CADUCIDAD_FIRMA`, `SEED_CONTRASENA_INSTITUCION`, `DJANGO_NIVEL_DE_REGISTRO` y la
`RAILWAY_PUBLIC_DOMAIN` que inyectaba el proveedor.

> **La clave de API de Resend sigue viva** y la usa el correo en local. Pasó por una
> conversación con un agente: conviene rotarla si ese historial se comparte. Es lo único
> de `[S3]` que no muere con el entorno.

---

## [S4] Trampas que ya costaron un rato

Se conservan porque **cuatro de las siete no son del proveedor**: son de Django, y siguen
siendo ciertas en cualquier ejecución con `DEBUG = False`.

| Trampa | Qué pasa | Cómo se resuelve | ¿Sigue vigente? |
|---|---|---|---|
| **Un 500 no deja rastro** | Sin `LOGGING`, Django manda los errores a `mail_admins`; con `ADMINS` vacío se descartan en silencio | `LOGGING` con salida estándar, en `config/settings.py` | **Sí** |
| **La fuente de Tailwind dentro de `STATICFILES_DIRS`** | `collectstatic` la recoge y el almacenamiento con manifiesto falla al resolver su `@import` | La fuente vive en `estilos/`, fuera de `assets/` | **Sí** |
| **La clave de API de Resend es de solo envío** | No permite consultar el estado de entrega | La confirmación de que un correo llegó es la bandeja, no la API | **Sí** |
| **Detrás de un proxy, la sonda de salud recibe un 301** | `SECURE_SSL_REDIRECT` redirige lo que llega por HTTP interno sin `X-Forwarded-Proto` | `SECURE_REDIRECT_EXEMPT = [r"^salud/$"]`, ya en `config/settings.py` | **Sí**, ante cualquier proxy |
| **`preDeployCommand` de `railway.json` se ignoraba** | Las migraciones no corrían, el despliegue se marcaba correcto y toda consulta al ORM daba 500 | Encadenarlo en el `startCommand` | No — `railway.json` ya no existe |
| **`railway service scale` acumula regiones** | Añade en vez de sustituir; el servicio acaba con réplicas en tres y el despliegue falla por la región bloqueada | Poner a cero las que sobran | No |
| **La sonda mandaba `Host: healthcheck.railway.app`** | Sin estar en `ALLOWED_HOSTS`, respondía `400` | Se añadía junto al dominio público | No — ese bloque se retiró de `config/settings.py` |

---

## [S5] Cómo se montaría de nuevo

`DEC-15` **no prohíbe desplegar más adelante**: retira la obligación. Si el proyecto se
alarga o alguien decide retomarlo, esto es lo que costó descubrir la primera vez.

1. Crear el proyecto y el PostgreSQL gestionado. **En un plan de pago**, o se repiten los
   dos fallos de `[S1]`.
2. Crear el servicio web y **conectarlo al repositorio, rama `main`** — eso ya dispara el
   primer despliegue.
3. Generar el dominio **antes** de desplegar, para que la variable de dominio exista ya
   durante la construcción, y volver a añadir en `config/settings.py` el bloque que la
   lee: `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `URL_BASE` dependían de ella.
4. Volver a crear `railway.json`, o el equivalente del proveedor que se elija. El que
   había construía con `tailwind build && collectstatic` y arrancaba con
   `migrate` → `sembrar` → `gunicorn`, encadenados porque el `preDeployCommand` del
   fichero se ignoraba (`[S4]`).
5. Mover los servicios a la región elegida **poniendo a cero las demás** (`[S4]`).
6. Crear el bucket en la misma región y volcar sus credenciales a las variables `S3_*`.
7. Fijar el resto de variables de `[S3]`. `DJANGO_SECRET_KEY` se genera nueva.
8. Fijar `SEED_CONTRASENA_INSTITUCION` con una clave generada. **La institución la siembra
   el propio despliegue**: el seed es idempotente y con contraseña no envía correo
   (`DEC-10`), así que puede correr en cada arranque. Si la variable no existiera, el
   comando genera una clave y la imprime en el registro en vez de invitar por correo a una
   dirección que no es de nadie: falla del lado seguro.

> **El arreglo pendiente.** `/app/staticfiles/` no existía en ejecución y el candidato
> —mover `collectstatic` del `buildCommand` al `startCommand`— **nunca se verificó**.
> Quien retome esto lo encontrará ahí.

> **`railway.json` estaba deprecado** en favor de `.railway/railway.ts` y dejaba de
> funcionar el **2026-12-01**. Se decidió no migrar porque el Sprint 5 termina alrededor
> del 2026-11-01 y `.railway/railway.ts` exige Node y el paquete npm `railway`, que es
> justo lo que este repositorio evita. Si alguien retoma el despliegue después de esa
> fecha, el fichero que había ya no sirve.
