# SmartFood — El entorno de las exposiciones, y el que hubo antes

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-DESPLIEGUE |
| titulo | El entorno de las exposiciones en el Learner Lab de AWS, y por qué se retiró el que hubo en Railway |
| tipo_documento | **Documento operativo.** No es un artefacto de Scrum ni un entregable de la asignatura |
| documentos_fuente | `./decisiones-de-alcance.md` (`DEC-15`, `DEC-27`); `./decisiones-tecnicas.md` (`DT-13`, `DT-18`, `DT-21`, `DT-31`, `DT-61`); `./definicion-de-terminado.md` (`DoD-4`) |
| actualizado | 2026-10-26 · **desplegado en el Learner Lab, encendido solo para las exposiciones** (`DEC-27`). Antes, 2026-09-17, sin entorno (`DEC-15`) |
| idioma | es-CO |
| version | 3.0 |

### [S0.1] El estado, en una línea

**El prototipo está desplegado en una EC2 del AWS Academy Learner Lab de la Scrum Master, y
responde en <https://34-198-167-139.sslip.io> mientras el laboratorio tenga una sesión
abierta.** Lo decidió `DEC-27` el 2026-10-26, que corrige a `DEC-15`; la arquitectura es
`DT-61`. Fuera de las sesiones la instancia está parada y la URL no contesta: **basta con
que esté encendido durante las exposiciones**.

| | |
|---|---|
| `ENT-01` | Vuelve a estar desplegado en un entorno de pruebas (`DEC-27`) |
| `DoD-4` | **Vigente, sin cambios.** Se demuestra ejecutándolo, con la salida real del comando |
| El trabajo diario | **Sigue en local**, con `./desarrollo.md`. Este entorno no sustituye a ese |
| Antes de exponer | `[S7]`: abrir el laboratorio y esperar a que la URL conteste |

> **Queda una acción fuera del repositorio:** eliminar el proyecto de Railway, el entorno
> anterior. Hasta que se haga, ahí sigue habiendo un proyecto congelado con su base y su
> bucket. **No se despliega nada en él**, y la rama `main` ya no está conectada como
> origen de código desde el 2026-08-30.

---

### [S0.2] Qué es este documento

**La libreta de los dos entornos**: el de las exposiciones, que existe (`[S6]` … `[S10]`),
y el de Railway, que existió y se retiró (`[S1]` … `[S5]`). Del primero registra qué hay
montado, cómo se enciende, cómo se actualiza y cómo se monta desde cero; del segundo, por
qué se retiró, para que la decisión no haya que reconstruirla de memoria.

**No decide nada.** Las decisiones están en `./decisiones-de-alcance.md` y
`./decisiones-tecnicas.md` con su identificador. Aquí solo se registra el estado y se cita
de dónde sale.

Para levantar el entorno **local**, el de trabajo, el documento es `./desarrollo.md`.

---

## [S1] Railway: por qué se retiró

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

## [S2] Railway: las tres restricciones que tuvo el plan gratuito

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

> **`DT-21` sigue vigente y no depende del proveedor.** En local esa topología vive en el
> mismo `docker compose` que PostgreSQL: primero fue MinIO, y desde `DT-38` es SeaweedFS,
> porque las imágenes de MinIO dejaron de publicarse.

### [S2.3] Los servicios se dormían

Es el fallo 1 de `[S1]`. Se registró primero como molestia tolerable —«la primera petición
tras un rato devuelve `503` y la siguiente ya responde»— y resultó ser lo que hizo
inviable el entorno, porque quien no responde al despertar es PostgreSQL, no el proceso
web.

---

## [S3] Railway: qué había montado, si algo hiciera falta recuperarlo

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

## [S4] Railway: trampas que ya costaron un rato

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

## [S5] Railway: cómo se montaría de nuevo

**No es el camino que se tomó**: `DEC-27` volvió a desplegar en AWS, con `[S6]` … `[S10]`.
Se conserva por si el proyecto volviera a un PaaS, porque es lo que costó descubrir la
primera vez.

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

---

## [S6] El entorno de las exposiciones: qué hay montado

`DEC-27` y `DT-61`. Todo en la cuenta del AWS Academy Learner Lab de la Scrum Master,
región `us-east-1`, con la etiqueta `Proyecto=smartfood` en cada recurso.

| Recurso | Valor |
|---|---|
| Instancia EC2 | `smartfood` · `i-015dae457f6772299` · `t3.medium`, Ubuntu 24.04, 30 GB `gp3` |
| Rol de la instancia | `LabInstanceProfile`, el que el laboratorio permite. La aplicación no lo usa |
| IP elástica | `34.198.167.139` · `eipalloc-0250f56e82140dace` |
| Grupo de seguridad | `smartfood-demo` · `sg-0d5b1ce10adf2b1b0` · 80 y 443 abiertos; 22 solo desde la IP de quien desplegó |
| Llave SSH | `vockey`, la del laboratorio: el `labsuser.pem` que se descarga desde él |
| Código | `~/smartfood` en la instancia, con su `.env` (permisos `600`) |
| Stack | `compose.produccion.yaml`, proyecto `smartfood-produccion` |

**Las direcciones**, todas con su certificado de Let's Encrypt:

| Dirección | Lleva a |
|---|---|
| <https://34-198-167-139.sslip.io> | La aplicación |
| `https://institucion.`, `administracion.`, `cajero.` y `acudiente.34-198-167-139.sslip.io` | La misma aplicación, con su propia cookie: un rol en cada pestaña (`[S2.1.1]` de `./desarrollo.md`) |
| `https://s3.34-198-167-139.sslip.io` | El API S3 de SeaweedFS, para las URL firmadas de las fotografías. Sin firma contesta `403` |
| `https://correo.34-198-167-139.sslip.io` | Mailpit, detrás de una contraseña: usuario `smartfood` y la contraseña de las cuentas sembradas |

**Las cuentas** son las sembradas, con la contraseña de `[S2.1]` de `./desarrollo.md`
(`DEC-27`): `institucion@`, `administracion@` y `cajero@example.com`, y los acudientes
sembrados, como `andres.uribe7@example.com`. **Tienen existencias y saldo**: se cargaron
40 unidades de cada producto y $50.000 a cada estudiante con el atajo de `[S1.2]` de
`./desarrollo.md`, el mismo que se usa en local.

---

## [S7] Antes de una exposición

1. **Abrir el Learner Lab** y pulsar *Start Lab*. La sesión dura unas cuatro horas y se
   puede alargar desde el propio laboratorio.
2. **Esperar a que la URL conteste.** El laboratorio arranca la instancia, Docker levanta
   el stack solo (`restart: unless-stopped`) y el arranque migra, siembra —sin cambiar
   nada: el seed es idempotente (`DEC-10`)— y recopila los estáticos. Medido el
   2026-10-26: **la instancia estuvo en marcha a los 20 s y la aplicación respondió 36 s
   después**, con la misma IP.

   ```bash
   curl https://34-198-167-139.sslip.io/salud/
   # {"estado": "ok", "base_de_datos": "conectada"}
   ```

3. **Si la instancia no arrancó con el laboratorio**, se arranca a mano desde la consola
   de EC2 o con `aws ec2 start-instances --instance-ids i-015dae457f6772299`, con las
   credenciales de la sesión en `~/.aws/credentials`.

**Al terminar no hay que hacer nada**: el laboratorio para la instancia al cerrar la
sesión. Los datos se quedan en su disco; lo que se haya hecho durante la exposición
sigue ahí en la siguiente.

---

## [S8] Cómo se actualiza el código

La instancia no clona el repositorio: recibe una copia de lo versionado y reinicia
`app`, que al arrancar compila las hojas, migra y recopila los estáticos (`DT-61`).
Desde la raíz del repositorio, en `main` y con los cambios ya integrados:

```bash
git archive HEAD | ssh -i ~/.ssh/labsuser.pem ubuntu@34.198.167.139 'tar -xf - -C ~/smartfood'
ssh -i ~/.ssh/labsuser.pem ubuntu@34.198.167.139 \
  'cd ~/smartfood && docker compose -f compose.produccion.yaml up -d --build'
```

`git archive` lleva lo commiteado, no lo que haya sin commitear en el disco. **Un fichero
que se borró del repositorio no se borra en la instancia**: la copia se superpone. Si eso
importa, se vacía `~/smartfood` antes —conservando el `.env`—.

**Si cambió `uv.lock`**, el `--build` lo reconstruye. Si no cambió nada de la imagen,
basta `docker compose -f compose.produccion.yaml restart app`. El registro:
`docker compose -f compose.produccion.yaml logs app`.

**El SSH solo se abre a una IP.** Si quien despliega cambia de red, hay que añadir la
nueva al grupo de seguridad `smartfood-demo`, o el `ssh` se queda esperando sin error.

---

## [S9] Cómo se monta desde cero

Lo que se hizo el 2026-10-26, por si hubiera que repetirlo en otra cuenta.

1. **El grupo de seguridad**: 80 y 443 desde cualquier sitio, 22 solo desde la IP propia.
2. **La instancia**: Ubuntu 24.04, `t3.medium`, 30 GB `gp3`, la llave `vockey`, el perfil
   `LabInstanceProfile` e IMDSv2 obligatorio. Un *user data* que instale `docker.io` y
   `docker-compose-v2` y añada `ubuntu` al grupo `docker`.
3. **La IP elástica**, asociada a la instancia. Sin ella, la IP cambia en cada arranque y
   con ella el nombre y los certificados.
4. **El código**, con `git archive` como en `[S8]`.
5. **El `.env` del servidor**, en `~/smartfood`, con permisos `600`. Los secretos se
   generan **en la instancia** y no salen de ella:

   | Variable | Qué es |
   |---|---|
   | `DOMINIO` | `<ip-con-guiones>.sslip.io` |
   | `DJANGO_SECRET_KEY` | Nueva: `openssl rand -base64 48` |
   | `POSTGRES_PASSWORD` | Nueva: `openssl rand -hex 24` |
   | `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | Nuevas. **Nunca las de `compose.yaml`**: este API S3 es alcanzable desde internet |
   | `SEMBRAR_CONTRASENA` | La de las cuentas sembradas (`DEC-27`). Vacía, no siembra |
   | `CORREO_USUARIO`, `CORREO_CLAVE_HASH` | La contraseña de Mailpit, como hash de `caddy hash-password`, **entre comillas simples**: lleva `$` y sin ellas `compose` la interpolaría |

   `compose.produccion.yaml` se niega a arrancar si falta una de las obligatorias, y
   `config/tests_contenedor.py` vigila que siga siendo así.
6. **Levantar**: `docker compose -f compose.produccion.yaml up -d --build`. El primer
   arranque construye la imagen, pide los siete certificados y siembra: unos cinco
   minutos.
7. **Cargar existencias y saldo** con el atajo de `[S1.2]` de `./desarrollo.md`, dentro
   de `app`: `docker compose -f compose.produccion.yaml exec -T app python manage.py shell`.

**Cómo se comprobó**: las cinco direcciones de la aplicación con `200` y certificado
válido; HTTP redirige a HTTPS con `308`; `/salud/` conectada; `/.env` da `404`; Mailpit
`401` sin contraseña y `200` con ella; el API S3 `403` sin firma; desde fuera solo
responden el 80, el 443 y el 22. Y en Chrome, una sola ventana con cuatro pestañas —una
por subdominio y rol—: cuatro cookies de sesión `Secure`, cada rol en su panel tras
recargar, y la fotografía del estudiante cargada desde `s3.` con su URL firmada.

---

## [S10] Trampas del entorno de las exposiciones

| Trampa | Qué pasa | Cómo se resuelve |
|---|---|---|
| **Un nombre que no es suyo recibe `200` de Caddy** | Caddy contesta `200` vacío a un `Host` que no sirve, en vez de `400`. Parece que la aplicación acepta cualquier nombre | No llega a Django, que con ese `Host` daría `400`. Se comprueba desde dentro: `docker compose … exec caddy wget --header "Host: x" http://app:8000/` |
| **Los escáneres llegan antes que nadie** | En cuanto se emite un certificado, el nombre aparece en los registros públicos de certificados, y en minutos hay peticiones a `/graphql`, `/.env` o `/actuator/env` | Contestan `404`. Es ruido en `logs app`, no un ataque dirigido |
| **sslip.io no está en la Public Suffix List** | El límite de Let's Encrypt —50 certificados por semana— se cuenta para todo `sslip.io`, compartido con todos sus usuarios | Los certificados se guardan en el volumen `caddy-datos` y no se piden en cada arranque. Si un día no salen, un nombre de DuckDNS, que sí está en la lista |
| **El hash de la contraseña lleva `$`** | Sin comillas simples en el `.env`, `compose` lo interpreta como variables y Caddy recibe un hash roto | `CORREO_CLAVE_HASH='$2a$14$…'` |
| **Las credenciales del laboratorio caducan** | Las de `~/.aws/credentials` valen una sesión | No van en ningún fichero del servidor: la aplicación no usa AWS, y la instancia, si lo necesitara, tiene su rol |
