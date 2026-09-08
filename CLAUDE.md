# CLAUDE.md

Guía de trabajo para Claude Code en este repositorio.

## Qué es esto

**SmartFood**: prototipo de plataforma de gestión para cafeterías escolares con control parental y
trazabilidad digital. Proyecto de la asignatura *Proyecto Aplicado en TIC 1* (UPB, 202601).

Equipo de 4, de los cuales **2 desarrollan**. Cinco sprints de dos semanas, semanas 6 a 15.
**El Sprint 1 está cerrado** —56 de 56 tareas y 18 de 18 historias—. **Estamos en el Sprint 2**, semanas 8 y 9, con el **Avance 1** (`EVA-3`, 20 % de la nota) en la semana 10.

## Antes de escribir código, lee esto

`docs/` no es documentación decorativa: es el contrato del proyecto. Orden de lectura:

| Documento | Para qué |
|---|---|
| `docs/smartfood.md` | Contexto: problema, objetivos, alcance (`S9`), solución (`S10`), matriz de permisos (`S11`), usuarios (`S5`) |
| `docs/decisiones-de-alcance.md` | Alcance acordado **después** del anteproyecto (`DEC-1` … `DEC-12`) |
| `docs/decisiones-tecnicas.md` | Arquitectura, stack y modelo de datos (`DT-1` … `DT-25`) |
| `docs/backlog-historias-de-usuario.md` | Las 59 historias con sus criterios de aceptación |
| `docs/sprint-2-backlog.md` | **Las 37 tareas del sprint en curso** (`TT-57` … `TT-93`), con responsable |
| `docs/plan-de-pull-requests-sprint-2.md` | Esas 37 tareas agrupadas en 16 PR, y **el estado de cada una** |
| `docs/sprint-1-backlog.md` | El sprint anterior, cerrado. Consulta histórica |
| `docs/plan-de-pull-requests-sprint-1.md` | El plan del sprint anterior, cerrado. Documento de archivo |
| `docs/definicion-de-terminado.md` | Los seis criterios de cierre (`DoD-1` … `DoD-6`) |
| `docs/despliegue.md` | Estado real del entorno desplegado, sus restricciones y sus trampas |
| `docs/desarrollo.md` | Reconstrucción local, credenciales y comandos del día a día |
| `docs/mapa-de-la-aplicacion.md` | Qué pantallas hay, quién alcanza cada una y el recorrido de demostración |
| `docs/sistema-visual.md` | **Qué composición copiar al construir una pantalla**, y de qué plantilla (`DT-25`) |
| `docs/formato-de-carga.md` | Contrato del archivo de carga de estudiantes (`TT-22`) |
| `docs/campos-nutricionales.md` | Qué declara cada producto y por qué esos campos (`TT-44`) |
| `docs/recorrido-de-administracion-de-estudiantes.md` | Recorrido UX de la vista de estudiantes y qué cambió por él (`TT-35`) |
| `docs/prueba-de-concepto-del-lector.md` | Guion de `TT-72`: tarjetas impresas y lector físico (`ENT-02`) |
| `docs/convenciones-de-git.md` | Ramas, convención de commits y publicación de versiones (`TT-01`) |

**El alcance vigente es `[S9.1]` de `smartfood.md` MÁS `[S1]` de `decisiones-de-alcance.md`.** Ocho
decisiones amplían el anteproyecto y no están incorporadas a él. Para responder qué hace o no hace
el sistema hay que mirar los dos.

Las referencias con prefijo `corpus:` apuntan a documentos del corpus de la asignatura que **no
están en este repositorio** (material de clase, Guía de Scrum, el DOCX original). No son rutas rotas.

## Las invariantes no se negocian

Quince reglas que el sistema debe cumplir siempre. Están en `[S10.2]` de `smartfood.md` (`INV-1` …
`INV-9`) y en `[S2]` de `decisiones-de-alcance.md` (`INVD-1` … `INVD-6`). Las que más
condicionan el código:

| | Regla | Cómo se sostiene |
|---|---|---|
| `INV-1` | Ninguna venta deja saldo negativo | Validar **dentro** del bloqueo pesimista, nunca antes (`DT-6`) |
| `INV-2` | El saldo se reconstruye desde el historial | **No existe columna `saldo`**: es la suma de los movimientos (`DT-4`) |
| `INV-3` | Las existencias se explican desde el historial | **No existe columna `existencias`** (`DT-5`) |
| `INV-4` | Las restricciones no las desactiva la cafetería | Permisos en la capa de datos, **no ocultando botones** (`DT-11`) |
| `INV-5` | El bloqueo por alérgeno es sobre la condición | Relación evaluada en la venta, **nunca lista materializada** (`DT-7`) |
| `INV-6`, `INVD-1` | Ninguna cuenta por autorregistro | Las rutas de registro **no existen** (`DT-10`) |
| `INV-7` | Código de tarjeta aleatorio y no secuencial | Generador criptográfico. **Nunca UUIDv7**: lleva timestamp y va ordenado (`DT-9`, `DT-17`) |
| `INV-8` | Toda disminución manual lleva motivo | `CheckConstraint`, no un `if` (`DT-5`) |
| `INVD-6` | Ninguna fotografía es de una persona real | Avatares generados en el seed (`DT-14`) |

Si una tarea parece exigir romper una invariante, **no la rompas: dilo.** Es señal de que la tarea
está mal entendida o de que falta una decisión.

## Stack y arquitectura

**Django + PostgreSQL + HTMX + Tailwind.** Monolito, un repositorio, un despliegue. UUIDv7 como
clave primaria en todas las tablas (generado en la aplicación), **excepto el código de tarjeta**.

Una app por dominio, **y cada una se crea en el sprint que la necesita**: hoy existen
`cuentas`, `personas`, `catalogo`, `billetera`, `inventario` y `ventas`; `reportes` no.
Dentro de cada una:

| Archivo | Responsabilidad |
|---|---|
| `models.py` | Estructura e invariantes de datos (`CheckConstraint`, `UniqueConstraint`). Sin lógica de negocio |
| `services.py` | **Toda escritura.** Funciones, no clases; cada una abre su `transaction.atomic()` |
| `selectors.py` | **Toda lectura** no trivial. No conocen `request` |
| `views.py` | HTTP: parsear, delegar, renderizar. **Cero lógica de negocio** |

Tres reglas (`DT-15`):

1. **Una vista nunca escribe directamente**: llama a un servicio.
2. **La invariante que la base pueda imponer, la impone la base.** Un `if` se olvida en el siguiente
   camino de escritura; una restricción no.
3. **Los servicios no saben de HTTP.**
   Reciben `actor` como argumento y lanzan `PermissionDenied` si no procede; nunca leen
   `request.user`. El admin **también es una vista**: su `save_model` delega en el servicio.

Frontend (`DT-16`): **una vista HTMX devuelve un fragmento, nunca una página.** Si un endpoint
devuelve a veces una cosa y a veces otra, sepáralo en dos. El admin de Django cubre `INT-3`.

Diseño (`DT-23`, `DT-25`): el sistema visual —paleta, tipografía, armazones **y
composiciones**— se adopta entero de un producto en producción del mismo dominio, no se
inventa aquí. **`estilos/fuente.css` es el único fichero con colores literales**; en las
plantillas se usan alias de intención (`bg-superficie`, `text-texto`, `border-borde`,
`text-error-fuerte`). Cuatro armazones cuelgan de `base.html`: `base-publica.html`,
`base-acceso.html`, `base-aplicacion.html` y `base-punto-de-venta.html`.

**Antes de inventar una pantalla, mira `docs/sistema-visual.md`**: dice qué seis
composiciones existen y de qué plantilla se copia cada una. Dos que se olvidan: la acción de
una tarjeta de resumen es un **enlace** de acento abajo, no un botón sólido; y **un hueco
nunca es un botón deshabilitado** — dice qué falta y qué historia lo trae.

**No construyas**: hexagonal, repositorios sobre el ORM, interfaces «por si cambiamos de base»,
microservicios, GraphQL, autenticación propia, app nativa, ni nada que toque dinero real. Los
descartes están razonados en `[S4]` de `decisiones-tecnicas.md`.

### Trampas de este stack, ya pagadas

- **`instance.pk` no distingue un alta.** La clave primaria es UUIDv7 generado en la
  aplicación (`DT-17`): una instancia recién construida **ya la tiene**. Pregunta por
  `instance._state.adding`.
- **Ocultar un campo del admin no se hace borrándolo del formulario.** El admin arma sus
  secciones desde `base_fields`, antes de que exista instancia: un `del self.fields[...]`
  revienta al renderizar. Se decide en `get_fields()` / `get_fieldsets()`.
- **Un `ManyToMany` con `through` no se edita desde el admin**, y el campo del formulario que
  lo sustituya **no puede llamarse igual** que el del modelo: la comprobación `E013` mira el
  modelo, no el formulario.
- **En plantillas, `{# … #}` solo comenta dentro de una línea.** Un bloque de varias líneas se
  sirve al navegador como texto. Usa `{% comment %}`; hay prueba que lo vigila.
- **`{% now "F" %}` devuelve el mes capitalizado** («Septiembre»), y dentro de una fecha en
  español va en minúscula. No se le puede aplicar un filtro directamente: `{% now "F" as mes %}`
  y luego `{{ mes|lower }}`. La inicial de la frase se pone con `first-letter:uppercase`, nunca
  cortando la cadena — con acentos se rompe.
- **Al tocar plantillas, deja `uv run python manage.py tailwind watch` en otra terminal.**
  Sin él, una clase nueva no está en la hoja compilada y el cambio «no se ve». Si compilas
  a mano, **`tailwind build --force`**: sin la opción compara la fecha de `fuente.css` con
  la de la hoja y contesta «up to date», que es cierto para la fuente y falso para lo que
  importa —las clases salen de las plantillas, y ésas no las mira—.
- **La paleta de fábrica de Tailwind no existe**: `--color-*: initial` la borra. `bg-slate-500`
  no pinta nada **y no da ningún error**; lo mismo `sm:` y `lg:`, que se sustituyen por
  `tablet:`, `escritorio:` y `amplio:`. Hay prueba que vigila las dos cosas
  (`config/tests_plantillas.py`).
- **El rojo y el ámbar significan algo**: saldo insuficiente o alérgeno bloqueado (`INV-1`,
  `INV-5`) y límite a punto de agotarse. Para adornar hay cinco colores de serie sin
  significado; gastar los de estado en decoración les quita fuerza donde hacen falta.
- **Las variantes de Tailwind no alcanzan a las clases de `@layer components`.**
  `escritorio:rejilla-caja` no se compila **y no da ningún error**: la pantalla se queda en
  una columna. El punto de ruptura va dentro de la propia clase, en `estilos/fuente.css`.
  Si el efecto sí depende de un estado —el botón de cristal de la cabecera pública sobre el
  héroe—, la salida es la contraria: escribirlo con utilidades que Tailwind pueda variar.
- **Un elemento nunca es su propio contenedor de consulta.** `@container` marca al
  ANCESTRO, así que ponerlo en la misma caja que la rejilla deja las `@container (...)` de
  `fuente.css` sin nada contra qué medirse: no fallan, y la pantalla se queda en una
  columna. Va en el envoltorio (`base-punto-de-venta.html`).
- **El dinero se escribe en un solo sitio**, `billetera/templatetags/dinero.py`: `$25.000`,
  sin espacio, y `{{ x|dinero:"COP" }}` cuando la cifra es grande. No lo formatees en
  JavaScript ni en una plantilla — con dos formateadores, el día que cambie el formato la
  misma pantalla enseña dos monedas.
- **Al tocar la matriz `[S11]` hace falta `manage.py sincronizar_permisos`.** Los permisos
  van al grupo del rol, no al usuario: sin ese comando el admin responde `403` sobre el
  modelo nuevo y nada indica por qué.

## Cómo ejecutar

Con `docker compose up -d` levantado, y siempre por `uv run`:

```bash
set -a && source .env && set +a
uv run python manage.py <lo que sea>
```

Para tener una base con la que trabajar —institución, personal, familias con avatares y
catálogo, todo ficticio e idempotente—:

```bash
uv run python manage.py sembrar --contrasena-de-desarrollo 'smartfood-local-2026' \
  --estudiantes 12
```

Se entra por `/login/`, que es la puerta de los cuatro roles. Las credenciales locales y el
recorrido de cada rol están en `docs/desarrollo.md`.

Para mirarla a mano: `uv run python manage.py runserver` en <http://127.0.0.1:8000> y
**`tailwind watch` en otra terminal**, o cada cambio de plantilla se verá con la hoja vieja.

Al sacar una rama ajena, **`migrate` antes de nada**: una migración sin aplicar no falla al
arrancar, falla al abrir la pantalla que la usa.

Antes de cada PR, los tres tienen que pasar:

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run   # DoD-3, el que más se olvida
uv run python manage.py test --noinput   # sin --noinput, una BD de prueba huérfana lo cuelga
```

**Son la única red.** La CI solo valida el título del PR y publica la versión al integrar:
ningún workflow ejecuta las pruebas, así que lo que no compruebes aquí no lo comprueba nadie
—ni en el PR, ni después del merge—. Tampoco hay linter ni formateador configurados.

La suite completa son 533 pruebas y **tarda unos dos minutos**: por encima del tiempo de
espera por defecto de muchas herramientas. Si se corta a los 120 s no es que falle, es que no
le dio tiempo — dale margen o corre solo la app que tocaste.

Pruebas en `<app>/tests_<tema>.py`. **Todo lo que crea cuentas manda correo diferido con
`transaction.on_commit`** (`config/correo.py`): un test que mire `mail.outbox` sin envolverse en
`self.captureOnCommitCallbacks(execute=True)` verá la bandeja vacía y parecerá que no se envió.

**Una prueba que entra al admin crea la cuenta por el camino real**:
`sincronizar_grupos_y_permisos()` y `crear_cuenta(..., accede_a_administracion=True)`. Poner
`is_staff` a mano deja una cuenta que entra pero no tiene ningún permiso, y todo responde `403`.

**Una prueba sobre una página entera busca un `data-*` propio, no un atributo genérico.**
`assertNotContains(r, 'role="group"')` para decir «no se dibuja el selector de estudiante» se
rompe el día que el armazón estrena otro grupo — y se rompió. Busca
`data-selector-estudiante`, que sí es exclusivo de esa pantalla.

Para comprobar un flujo real sin navegador —el admin, sobre todo— va bien `manage.py shell -c`
con `django.test.Client`. Hace falta añadir el host que usa el cliente:

```bash
DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,testserver" uv run python manage.py shell -c '…'
```

**Para mirar una pantalla de verdad** sin navegador manual: renderízala con
`django.test.Client`, guarda el HTML con las rutas de `/static/` reescritas a `file://` y
dispara `google-chrome --headless --screenshot`. Tres detalles o la captura miente:
`--allow-file-access-from-files` —si no, el JS no corre— y desactivar transiciones y
animaciones, que el reloj virtual congela en su estado inicial. Y **`collectstatic` después de
`tailwind build --force`**: el HTML apunta a `/static/`, que se reescribe a `staticfiles/` —no
a `assets/`—, así que sin ese paso se fotografía la hoja anterior.

**Las pruebas que tocan imágenes no hablan con MinIO:** usan `override_settings(STORAGES=…)`
con `InMemoryStorage`. Por eso `foto_clave` e `imagen_clave` son `CharField` y no `FileField`
— este último ata el almacenamiento a la definición de la clase y el `override` no le llega.

## Definición de Terminado

En `docs/definicion-de-terminado.md`: seis criterios citables, `DoD-1` … `DoD-6`. Se aplican al
**Pull Request**, no a la historia, porque cinco de las 37 tareas del sprint no cuelgan de ninguna.

Cada criterio declara cuándo aplica. `DoD-2` (integrado en `main`) y `DoD-6` (datos ficticios)
aplican **siempre**; los demás son condicionales — y un criterio que no aplica **se declara, no se
salta**.

**`DoD-4` está suspendido** desde el 2026-08-30: el entorno desplegado se congeló porque el plan
gratuito del proveedor no lo sostiene (`[S2]` de `docs/despliegue.md`). Mientras dure, cada PR
declara **cómo se verificó en local, con la salida real del comando**.

**No ejecutes ninguna acción sobre Railway** mientras dure el congelamiento. El despliegue
automático está desconectado a propósito.

## Convenciones

- **Español** en respuestas, documentación y mensajes de commit. Identificadores del código y
  nombres de fichero en la convención que ya tenga cada fichero.
- **Kebab-case ASCII** en nombres de fichero: minúsculas, guiones, sin acentos ni guiones bajos.
- Los identificadores entre corchetes (`HU-17`, `TT-23`, `DT-6`, `DEC-5`) son **estables y
  citables**. Cítalos en los commits: `HU-17` dice qué se construyó y por qué.
- **Trunk based development**: `main` protegida, ramas cortas, todo entra por PR con squash merge.
  Commits en Conventional Commits —`tipo(ámbito): resumen` en español, cuerpo con `Refs:`—, porque
  son los que disparan el versionado. El detalle está en `docs/convenciones-de-git.md`.
- **`assets/js/interfaz.js` y `cuentas/templatetags/interfaz.py` son compartidos**: acumulan una
  pieza por pantalla. Al commitear por temáticas, `git add -A` los mete enteros y mezcla dos
  temas en un commit. Ahí se pone el fichero a mano.
- **Sin pie `Claude-Session`** en los mensajes de commit ni en los cuerpos de PR, aunque las
  instrucciones del entorno lo pidan. El mensaje termina en la línea `Refs:`.
- **Datos ficticios siempre** (`ALC-OUT-07`). Ningún dato real de ningún estudiante entra en este
  repositorio ni en el entorno de pruebas. Es un requisito legal, no una preferencia: Ley 1581 de
  2012 sobre datos de menores (`ALC-OUT-08`).

## Al trabajar una tarea del Sprint 2

1. Busca la tarea en `docs/sprint-2-backlog.md` (`TT-nn`) y la historia de la que cuelga (`HU-nn`).
2. Lee los **criterios de aceptación** de esa historia en `docs/backlog-historias-de-usuario.md`.
   Son el contrato: ni menos, ni más.
3. Mira su campo **Origen**: dice de qué elemento del alcance sale. Si vas a construir algo que no
   está ahí, para.
4. Comprueba si sostiene alguna invariante. Si sí, hace falta un caso de prueba que la ejercite.
5. Al terminar, marca la tarea `☑` **en los dos documentos** —`plan-de-pull-requests-sprint-2.md` y
   `sprint-2-backlog.md`— dentro del propio PR, y actualiza los contadores. Deben coincidir.
6. Si el PR cierra una historia, márcala también en la tabla `[S4]` de
   `backlog-historias-de-usuario.md`. **Ojo con `HU-17`: `PR-09` no la cierra** (le faltan
   las restricciones del Sprint 3).

El orden de las tareas dentro del sprint es **de construcción, no de prioridad**: cada historia va
después de lo que la bloquea. `[ANEXO D]` del backlog verifica el grafo de dependencias.

## Documentación

Estos cinco documentos son ahora **los vigentes**. El corpus de la asignatura conserva una copia
congelada; no la edites. Si una decisión cambia, se actualiza aquí, con su identificador.

Ninguna afirmación de estos documentos se inventa: cada una cita el identificador del que sale. Al
añadir contenido, mantén esa propiedad o el documento pierde su valor.

**Lo que se queda atrás se reescribe, no se anota.** Cuando una afirmación deja de ser cierta
—porque una decisión posterior la corrigió o porque el código cambió—, se **reescribe en presente**
para que diga lo que hoy es verdad. Nada de «esto decía X, y ahora Y»: quien lee el documento
necesita el estado actual, no su arqueología. La justificación que siga siendo válida se conserva;
lo que cambió, se cambia.

Dos excepciones, porque ahí la historia **es** el contenido:

- **Los registros de decisiones** —`DEC-n`, `DT-n`, `INVD-n`— no se reescriben: una decisión
  posterior que corrige a otra se añade con su propio identificador y dice a cuál corrige, como
  `DT-21` hace con `DT-18`. Borrar la anterior dejaría sin explicación por qué el código es así.
- **Las listas de puntos abiertos y de hallazgos** —`ANEXO B`, los `UX-n` del recorrido— marcan el
  punto como resuelto y dicen dónde. Que el punto llegó a estar abierto es información.
