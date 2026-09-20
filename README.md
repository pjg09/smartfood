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
| Sprint 1 | ✅ cerrado: 56 de 56 tareas y 18 de 18 historias |
| Sprint 2 | ✅ cerrado el 2026-09-12: 37 de 37 tareas, 16 de 16 PR y **14 de 14 historias** — la última, `HU-17`, la saldó el Sprint 3 |
| Sprint 3 | ✅ cerrado el 2026-09-17: **43 de 43 tareas y 16 de 16 PR**. Control parental, estado del estudiante y los escenarios críticos `TST-1` y `TST-2` |
| Historias terminadas | ✅ **las 61 de 61**, desde el 2026-09-19. Las cerró `HU-37`, el reporte de auditoría, en el último PR de producto del proyecto. El desglose de qué PR cerró cada una está en `[S4]` de [`backlog-historias-de-usuario.md`](./docs/backlog-historias-de-usuario.md) |
| Sprint 4 | ✅ cerrado el 2026-09-19: **18 de 18 tareas y 7 de 7 PR**. Inventario trazable, pedidos anticipados y `TST-4` |
| Plan de pruebas | Los cuatro escenarios críticos `TST-1` … `TST-4` están **construidos y cubiertos por la suite** desde el Sprint 4. `ENT-05` pide además **ejecutarlos y dejar evidencia**, y eso es `TT-179`, **todavía sin empezar** (`PR-10`) |
| **Sprint 5** | 🔨 **en curso**, semanas 14–15. **El producto ya está terminado**: 24 de 33 tareas y 9 de 13 PR. Lo que queda (`PR-10`…`PR-13`) **no toca el código** — plan de pruebas, arquitectura, artefactos de gestión, informe final y cierre. **El estado de cada tarea vive en su plan de PR** |
| **Lo siguiente** | **Entrega final** (`EVA-5`, 30 % de la nota), semana 16 |
| Entorno desplegado | ❌ **no hay, y no lo habrá** — ver abajo |

> **Al cerrar el Sprint 3 el control parental funciona de verdad.** El acudiente fija el
> cupo diario de su hijo, bloquea productos y bloquea alérgenos —la condición, no una lista:
> lo que la cafetería agregue mañana queda cubierto solo—, y **la caja lo hace cumplir**: la
> venta se rechaza dentro de la misma transacción que descuenta saldo y existencias, con un
> motivo distinto para cada causa y **sin ninguna acción que permita omitirla**.
>
> El cajero ve al identificar la fotografía, el saldo, el consumo del día y las restricciones
> vigentes; la institución bloquea y desbloquea tarjetas desde el padrón, y el acudiente
> bloquea la suya sin esperar a secretaría —desbloquear, no: eso pasa por el colegio—.

> **Al cerrar el Sprint 4, el acudiente reserva y la cafetería entrega.** Paga por
> adelantado desde su aplicación y el saldo baja **al reservar**; el personal consulta en una
> cola qué hay que preparar; y el cajero registra la entrega en la caja **sin volver a
> cobrar**. La reserva pasa por la misma validación que el cobro, así que hereda las seis
> comprobaciones del control parental sin que la historia mencione ninguna.
>
> El inventario, además, se explica: toda merma lleva motivo —lo impone la base de datos, no
> el formulario— y la cifra de existencias de cualquier producto se desglosa renglón a
> renglón hasta el total.

> **El plan de pruebas de `ENT-05` queda completo con el Sprint 4.** `TST-4` —las existencias
> de un producto coinciden exactamente con la suma de su historial— era el último de los
> cuatro escenarios críticos: `TST-3` se demostró en el Sprint 2, `TST-1` y `TST-2` en el 3.
> Los cuatro se ejercitan en la suite y fallan si la invariante que protegen se rompe.

> El avance de arriba envejece. **La fuente es el plan de PR de cada sprint**, que es donde
> vive el estado de cada tarea; esta tabla solo lo resume. Los cuatro están cerrados y cada
> uno lleva su revisión de cierre en `[S7]`; el último es
> [`docs/plan-de-pull-requests-sprint-4.md`](./docs/plan-de-pull-requests-sprint-4.md), que
> además trae el guion del Avance 2 en `[S8]`.

> **El prototipo no se despliega, por decisión tomada el 2026-09-17.** El entorno de
> pruebas estuvo congelado desde el 2026-08-30 —el plan gratuito del proveedor no lo
> sostiene: la base de datos se duerme, al despertar rechaza conexiones y desactivarlo no
> está permitido en ese plan—, y la única salida era pagar. La consulta con la docente
> confirmó que **la asignatura no lo exige**, así que se retira en vez de restaurarse.
>
> `DEC-15` recorta `ENT-01` para quitarle la condición de estar desplegado; el resto del
> entregable no cambia y se demuestra **en local**, que es donde el proyecto lleva
> funcionando todo el semestre. `DoD-4` vuelve a estar vigente pidiendo la salida real del
> comando. El motivo completo está en [`docs/despliegue.md`](./docs/despliegue.md).

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
uv run python manage.py sembrar --contrasena-de-desarrollo 'smartfood-local-2026' \
  --estudiantes 12
uv run python manage.py runserver
```

`--estudiantes` no es opcional si quieres algo que mirar: sin él solo se crea la cuenta de
la institución, y los listados salen vacíos. Con él quedan sembrados el personal de la
cafetería, doce estudiantes con sus acudientes y avatares, y el catálogo con imágenes.
Todo ficticio (`ALC-OUT-07`) y se puede volver a ejecutar sin duplicar nada.

> **`sembrar` no crea existencias ni saldo**, así que el punto de venta todavía no puede
> cobrar: los productos salen «Sin existencias» y cualquier venta se rechaza. Es correcto
> —las dos cifras son la suma de su historial, no un campo— pero hay que darles un primer
> movimiento. El atajo está en **[`docs/desarrollo.md`](./docs/desarrollo.md)**.

En `http://localhost:8000`. **Se entra por `/login/`**, que es la puerta de los cuatro
roles; el admin de `/admin/` acepta a la institución y a la administración de la cafetería,
nunca al acudiente ni al cajero —que cobra entero desde el punto de venta—. Empieza con `institucion@example.com` y la contraseña de arriba.

**Qué pantalla hay y quién alcanza cada una está en
[`docs/mapa-de-la-aplicacion.md`](./docs/mapa-de-la-aplicacion.md).** Los comandos del día
a día, las credenciales de los demás roles y qué hacer cuando algo no arranca, en
[`docs/desarrollo.md`](./docs/desarrollo.md). Aquí solo está lo justo para levantarlo.

---

## La documentación es el contrato

`docs/` no es decorativa: es donde vive lo que el sistema debe hacer y por qué. Ninguna
afirmación se inventa — cada una cita el identificador del que sale.

**Qué es el sistema**

| Documento | Para qué |
|---|---|
| [`smartfood.md`](./docs/smartfood.md) | El anteproyecto: problema, objetivos, alcance, invariantes, matriz de permisos |
| [`decisiones-de-alcance.md`](./docs/decisiones-de-alcance.md) | Lo acordado **después** del anteproyecto. **Nueve amplían el anteproyecto y dos lo recortan**; su `[S3]` dice cuál hace qué |
| [`decisiones-tecnicas.md`](./docs/decisiones-tecnicas.md) | Arquitectura, stack y modelo de datos. Una decisión posterior **no reescribe** a la anterior: se añade con su propio identificador y dice a cuál corrige |
| [`backlog-historias-de-usuario.md`](./docs/backlog-historias-de-usuario.md) | Las 61 historias con sus criterios de aceptación |

> **El alcance vigente es `[S9.1]` de `smartfood.md` MÁS `[S1]` de `decisiones-de-alcance.md`.**
> Ninguna de las decisiones de `[S1]` está incorporada al anteproyecto: para saber qué hace y
> qué no hace el sistema hay que mirar los dos. *(Antes esta línea decía «once decisiones»;
> era el número de entonces, y con cada `DEC` nueva hacía falta recordar actualizarlo.)*

**Cómo se está construyendo**

| Documento | Para qué |
|---|---|
| [`sprint-5-backlog.md`](./docs/sprint-5-backlog.md) | **Las 33 tareas del sprint en curso** (`TT-155`…`TT-187`), con el cierre del proyecto en `[S5]` |
| [`plan-de-pull-requests-sprint-5.md`](./docs/plan-de-pull-requests-sprint-5.md) | Esas 33 tareas en 13 PR. **Es donde vive el estado** |
| [`sprint-4-backlog.md`](./docs/sprint-4-backlog.md) | Sprint 4, cerrado: 18 tareas (`TT-137`…`TT-154`) |
| [`plan-de-pull-requests-sprint-4.md`](./docs/plan-de-pull-requests-sprint-4.md) | Su plan de PR, cerrado: 7 PR, con la revisión de cierre y el guion del Avance 2 |
| [`sprint-3-backlog.md`](./docs/sprint-3-backlog.md) | Sprint 3, cerrado: 43 tareas (`TT-94`…`TT-136`) y el cierre de su registro de riesgos |
| [`plan-de-pull-requests-sprint-3.md`](./docs/plan-de-pull-requests-sprint-3.md) | Esas 43 tareas en 16 PR, con el estado de cada una y la **revisión de cierre** (`[S7]`) |
| [`sprint-2-backlog.md`](./docs/sprint-2-backlog.md) | Sprint 2, cerrado: 37 tareas y 14 de 14 historias |
| [`plan-de-pull-requests-sprint-2.md`](./docs/plan-de-pull-requests-sprint-2.md) | Su plan de PR, cerrado: 16 PR |
| [`sprint-1-backlog.md`](./docs/sprint-1-backlog.md) | El Sprint 1, cerrado: 56 tareas y 18 historias |
| [`plan-de-pull-requests-sprint-1.md`](./docs/plan-de-pull-requests-sprint-1.md) | Su plan de PR, cerrado: 25 PR |
| [`definicion-de-terminado.md`](./docs/definicion-de-terminado.md) | Los seis criterios de cierre (`DoD-1` … `DoD-6`) |

**Cómo se trabaja**

| Documento | Para qué |
|---|---|
| [`desarrollo.md`](./docs/desarrollo.md) | Reconstrucción local, credenciales y comandos |
| [`mapa-de-la-aplicacion.md`](./docs/mapa-de-la-aplicacion.md) | Qué pantallas hay, quién alcanza cada una y el recorrido de demostración |
| [`convenciones-de-git.md`](./docs/convenciones-de-git.md) | Ramas, commits y publicación de versiones |
| [`despliegue.md`](./docs/despliegue.md) | Por qué no hay entorno desplegado, y qué costó el que hubo |
| [`recorrido-de-administracion-de-estudiantes.md`](./docs/recorrido-de-administracion-de-estudiantes.md) | Recorrido de experiencia de usuario de la vista de estudiantes (`TT-35`) |
| [`campos-nutricionales.md`](./docs/campos-nutricionales.md) | Qué declara cada producto y por qué esos campos (`TT-44`) |
| [`sistema-visual.md`](./docs/sistema-visual.md) | Qué composición copiar al construir una pantalla, y de dónde |
| [`reglas-de-la-venta.md`](./docs/reglas-de-la-venta.md) | Qué comprueba la venta, **en qué orden y por qué** |
| [`reglas-del-pedido-anticipado.md`](./docs/reglas-del-pedido-anticipado.md) | Qué mueve reservar, consultar y entregar — y qué **no** mueve cada uno |
| [`reglas-del-cierre-de-caja.md`](./docs/reglas-del-cierre-de-caja.md) | Qué entra en el cuadre de la caja y qué no, y **por qué el efectivo esperado no se digita** |
| [`reglas-de-frecuencia-de-consumo.md`](./docs/reglas-de-frecuencia-de-consumo.md) | Qué alerta de frecuencia se publica y con qué umbral, y **por qué el umbral es el mismo para todas las categorías** |
| [`valores-de-referencia-nutricional.md`](./docs/valores-de-referencia-nutricional.md) | Contra qué cifras se comparan los agregados: la norma que las publica, y las tres salvedades declaradas |
| [`formato-de-carga.md`](./docs/formato-de-carga.md) | Contrato del archivo de carga de estudiantes |
| [`prueba-de-concepto-del-lector.md`](./docs/prueba-de-concepto-del-lector.md) | Guion de la validación con tarjetas impresas y lector físico (`ENT-02`) |

---

## Tres cosas que no se negocian

**Datos ficticios, siempre.** Ningún dato real de ningún estudiante entra en este
repositorio ni en ningún entorno. No es una preferencia: es la Ley 1581 de 2012 sobre
tratamiento de datos de menores, y es la razón por la que el prototipo no se despliega en
un colegio real. Las fotografías son avatares generados.

**Nadie se registra.** No hay ninguna ruta de registro y no la habrá. Toda cuenta nace de
un alta hecha por otro actor más una invitación por correo con la que el titular define su
propia clave. Hay una prueba que recorre el mapa de URL entero y falla si aparece una.

**Dieciséis invariantes.** Están en `[S10.2]` de `smartfood.md` y `[S2]` de
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
uv run python manage.py test --noinput
```
