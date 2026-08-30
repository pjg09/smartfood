# SmartFood — Definición de Terminado

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-DOD |
| titulo | Definición de Terminado del prototipo SmartFood |
| archivo_origen | — · documento derivado; extrae y reformula `[S2]` de `./sprint-1-backlog.md` |
| documentos_fuente | `./sprint-1-backlog.md` (`[S2]`); `corpus:guia-de-scrum-2020.md` (`COM-3`, `ART-3`); `./smartfood.md` (`ENT-01`, `ALC-OUT-07`) |
| tipo_documento | Compromiso del Incremento (`COM-3` de la Guía de Scrum) |
| cubre | `TT-07` — Redacción y acuerdo de la Definición de Terminado |
| criterios | 6 (`DoD-1` … `DoD-6`) |
| aplica a | Los cinco sprints. No se relaja durante el semestre |
| idioma | es-CO |
| version | 1.0 |

### [S0.1] Por qué es un documento aparte

Hasta ahora la Definición de Terminado vivía en `[S2]` de `./sprint-1-backlog.md`,
declarando en su primera línea que **aplica a los cinco sprints**. Un compromiso que
gobierna todo el semestre no puede vivir dentro del artefacto de un solo sprint: el
backlog del Sprint 2 tendría que duplicarlo —y entonces divergen— o apuntar al del
Sprint 1, que para entonces es historia.

`COM-3` de la Guía de Scrum la define como el **compromiso del Incremento**, no del
Sprint Backlog. Vive donde le corresponde.

---

## [S1] La regla

> **Nada está terminado hasta que cumple los seis criterios que aplican a su caso.**

Se aplica a la **unidad de trabajo**, que en este proyecto es **un Pull Request**
(`[S1]` de `./convenciones-de-git.md`). Un PR es lo que se integra, lo que se despliega
y lo que se revisa: es la unidad natural sobre la que preguntar «¿está terminado?».

Cada criterio dice **cuándo aplica**. Un criterio que no aplica no se salta en silencio:
se declara por qué no aplica. Es la diferencia entre «no había migraciones» y «no me
acordé de mirar si había migraciones».

---

## [S2] Los seis criterios

### `[DoD-1]` Los criterios de aceptación se cumplen

**Si el PR cierra una o más historias:** todos los criterios de aceptación de cada una
se cumplen y se han verificado **uno a uno**, no de vista. Los criterios son el
contrato: ni menos, ni más.

**Si el PR no cierra ninguna historia** —habilitación (`[S3]` del sprint backlog) o
gestión (`[S5]`)— declara **qué habilita** y **cómo se comprueba que lo habilita**. Una
tarea de habilitación sin comprobación es una promesa.

> `TT-04` no cerraba ninguna historia. Habilitaba `ENT-01`, y lo que lo comprobaba era
> una URL respondiendo y un endpoint de salud consultando la base gestionada.

### `[DoD-2]` Está integrado en la rama principal

El código está en `main`, integrado por **Pull Request** con revisión (`[S1]` de
`./convenciones-de-git.md`), y **no rompe nada de lo ya construido**.

Aplica **siempre**. Es el único criterio sin condición: mientras el trabajo viva en una
rama, no está terminado por definición.

### `[DoD-3]` Las migraciones están escritas y aplicadas

**Si el PR cambia el esquema de la base de datos:** sus migraciones están escritas,
aplicadas en el entorno de pruebas, y **no quedan cambios de modelo sin migrar**
—`manage.py makemigrations --check` no encuentra nada pendiente—.

Lo segundo no estaba en la redacción original y se añade por lo que enseña la práctica:
un modelo editado sin generar su migración no da error hasta que otra persona levanta el
proyecto, y para entonces el commit lleva días integrado.

**Si el PR no toca modelos**, no aplica. Decláralo.

### `[DoD-4]` Se demuestra en el entorno desplegado

Lo que el PR entrega se puede **enseñar en `ENT-01`**, no solo en local. Aplica
**siempre**, pero la forma de demostrarlo depende de lo que se entrega:

| Lo que entrega el PR | Cómo se demuestra |
|---|---|
| Funcionalidad para un usuario | Se usa, en el entorno desplegado |
| Configuración o infraestructura | Por su **efecto observable** allí, no por el diff |

Un PR que solo se puede enseñar en el portátil de quien lo escribió no está terminado:
el prototipo que se sustenta es el desplegado (`ENT-01`).

> `TT-06` no tiene pantalla. Se demostró por su efecto: un correo real llegando a una
> bandeja real.

### `[DoD-5]` Cada invariante que sostiene tiene su prueba

**Si el PR sostiene una invariante** (`INV-1` … `INV-9`, `INVD-1` … `INVD-6`): existe al
menos un caso de prueba que la ejercita, y que **falla si la invariante se rompe**. Una
prueba que pasaría igual con la invariante rota no prueba nada.

**Si el PR no sostiene ninguna**, no aplica. Decláralo — y comprueba de verdad que no
sostiene ninguna antes de declararlo.

> **Punto abierto, y no lo cierra este documento.** `[ANEXO B]` de
> `./decisiones-tecnicas.md` registra que **no se ha decidido si esos casos de prueba son
> automatizados o guiones manuales**, y que el plan de pruebas es de Alejandro (`[S12]`).
> Esta redacción no lo decide: dice «caso de prueba», igual que la original.
>
> La recomendación del equipo técnico es que sean **automatizados**, por una razón
> concreta: una prueba manual comprueba que hoy funciona; una automática comprueba que
> sigue funcionando dentro de tres sprints, cuando nadie recuerde por qué existía la
> regla. Las invariantes son justamente la parte del sistema que se degrada en silencio.
> Pero es una recomendación, no el contenido de `DoD-5`.

### `[DoD-6]` Todos los datos son ficticios

Todo dato usado, sembrado, mostrado o subido es **ficticio** (`ALC-OUT-07`). Incluye
fotografías: ninguna corresponde a una persona real (`INVD-6`).

Aplica **siempre**. No es una preferencia de calidad: es la Ley 1581 de 2012 sobre
tratamiento de datos de menores (`ALC-OUT-08`), y es la razón por la que el prototipo no
se despliega en una institución real (`ALC-OUT-06`).

Un PR que incumpla `DoD-6` no se corrige: se revierte.

---

## [S3] Cómo se usa

La plantilla de Pull Request (`.github/pull_request_template.md`) lleva los seis
criterios como lista de verificación, citando su identificador. Marcar una casilla es
afirmar que se comprobó; dejarla sin marcar y sin explicación es dejar el PR incompleto.

Para los criterios que no aplican, la plantilla pide **decir por qué**. La fórmula
«no aplica» sin motivo no vale: es la que deja pasar el caso en el que sí aplicaba.

---

## [S4] Acuerdo `[COM-3]`

La Guía de Scrum establece que, si la organización no proporciona una Definición de
Terminado, **el Scrum Team debe crear una**, y que los Developers deben conformarse a
ella. No es un documento que una persona escribe y los demás acatan: es un compromiso.

| Campo | Valor |
|---|---|
| Redactada por | Naomi (`TT-07`) |
| Extraída y reformulada de | `[S2]` de `./sprint-1-backlog.md`, versión 1.1 |
| Fecha de redacción | 2026-08-30 |
| **Acuerdo del equipo** | *Pendiente de registrar en la Daily o en el Sprint Planning* |

> **El acuerdo no lo da este fichero.** Mientras la fila de arriba diga «pendiente», lo
> que hay es un borrador redactado, no un compromiso adquirido. Naomi lo registra cuando
> los cuatro lo hayan discutido, con la fecha.

---

## [ANEXO A] Qué cambió respecto de la redacción original

`[S2]` de `./sprint-1-backlog.md` decía: *«Una **historia** está terminada cuando cumple
todo lo siguiente»*. **Doce de las cincuenta y cinco tareas del Sprint 1 (21 %) no
cuelgan de ninguna historia**: las nueve de habilitación y las tres de gestión.

No es un problema teórico. Los cinco primeros Pull Requests del proyecto —`PR-01` a
`PR-05`— fueron **todos** trabajo sin historia, y en los cinco hubo que declarar «no
aplica» en tres de los seis criterios. Cinco PR integrados bajo una definición que,
leída literalmente, no les aplicaba.

| Cambio | Antes | Ahora |
|---|---|---|
| Sujeto | «una historia» | la **unidad de trabajo**, que es un Pull Request |
| Aplicabilidad | implícita | cada criterio declara **cuándo aplica** |
| Criterios que no aplican | se saltaban | se declara **por qué** no aplican |
| Identificadores | ninguno | `DoD-1` … `DoD-6`, estables y citables |
| Ubicación | `[S2]` del backlog del Sprint 1 | documento propio, para los cinco sprints |
| `DoD-3` | «las migraciones están escritas y aplicadas» | añade que **no quedan cambios sin migrar** |

**No se añadió ningún criterio nuevo y no se relajó ninguno.** Los seis son los seis
originales; lo que cambia es que ahora cubren el 100 % del trabajo del sprint en vez del
79 %, y que `DoD-3` es más estricto que antes, no menos.

Tampoco se cerró ningún punto abierto. En particular, **`DoD-5` sigue sin decidir si los
casos de prueba son automatizados o manuales**: eso es plan de pruebas, es de Alejandro
(`[S12]`), y `[ANEXO B]` de `./decisiones-tecnicas.md` lo tiene registrado como
pendiente. Redactar la Definición de Terminado no es la ocasión para resolverlo de
tapadillo.
