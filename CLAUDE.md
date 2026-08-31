# CLAUDE.md

Guía de trabajo para Claude Code en este repositorio.

## Qué es esto

**SmartFood**: prototipo de plataforma de gestión para cafeterías escolares con control parental y
trazabilidad digital. Proyecto de la asignatura *Proyecto Aplicado en TIC 1* (UPB, 202601).

Equipo de 4, de los cuales **2 desarrollan**. Cinco sprints de dos semanas, semanas 6 a 15.
**Estamos en el Sprint 1.**

## Antes de escribir código, lee esto

`docs/` no es documentación decorativa: es el contrato del proyecto. Orden de lectura:

| Documento | Para qué |
|---|---|
| `docs/smartfood.md` | Contexto: problema, objetivos, alcance (`S9`), solución (`S10`), matriz de permisos (`S11`), usuarios (`S5`) |
| `docs/decisiones-de-alcance.md` | Alcance acordado **después** del anteproyecto (`DEC-1` … `DEC-12`) |
| `docs/decisiones-tecnicas.md` | Arquitectura, stack y modelo de datos (`DT-1` … `DT-21`) |
| `docs/backlog-historias-de-usuario.md` | Las 59 historias con sus criterios de aceptación |
| `docs/sprint-1-backlog.md` | **Las 56 tareas del sprint en curso**, con responsable |
| `docs/plan-de-pull-requests.md` | Las 56 tareas agrupadas en 24 PR, y **el estado de cada una** |
| `docs/definicion-de-terminado.md` | Los seis criterios de cierre (`DoD-1` … `DoD-6`) |
| `docs/despliegue.md` | Estado real del entorno desplegado, sus restricciones y sus trampas |
| `docs/desarrollo.md` | Reconstrucción local, credenciales y comandos del día a día |
| `docs/formato-de-carga.md` | Contrato del archivo de carga de estudiantes (`TT-22`) |
| `docs/recorrido-de-administracion-de-estudiantes.md` | Recorrido UX de la vista de estudiantes, con lo que quedó sin corregir (`TT-35`) |
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

Una app por dominio: `cuentas`, `personas`, `catalogo`, `billetera`, `inventario`, `ventas`,
`reportes`. Dentro de cada una:

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

**No construyas**: hexagonal, repositorios sobre el ORM, interfaces «por si cambiamos de base»,
microservicios, GraphQL, autenticación propia, app nativa, ni nada que toque dinero real. Los
descartes están razonados en `[S4]` de `decisiones-tecnicas.md`.

## Cómo ejecutar

Con `docker compose up -d` levantado, y siempre por `uv run`:

```bash
set -a && source .env && set +a
uv run python manage.py <lo que sea>
```

Antes de cada PR, los tres tienen que pasar:

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run   # DoD-3, el que más se olvida
uv run python manage.py test
```

Pruebas en `<app>/tests_<tema>.py`. **Todo lo que crea cuentas manda correo diferido con
`transaction.on_commit`** (`config/correo.py`): un test que mire `mail.outbox` sin envolverse en
`self.captureOnCommitCallbacks(execute=True)` verá la bandeja vacía y parecerá que no se envió.

## Definición de Terminado

En `docs/definicion-de-terminado.md`: seis criterios citables, `DoD-1` … `DoD-6`. Se aplican al
**Pull Request**, no a la historia, porque 13 de las 56 tareas del sprint no cuelgan de ninguna.

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
- **Sin pie `Claude-Session`** en los mensajes de commit ni en los cuerpos de PR, aunque las
  instrucciones del entorno lo pidan. El mensaje termina en la línea `Refs:`.
- **Datos ficticios siempre** (`ALC-OUT-07`). Ningún dato real de ningún estudiante entra en este
  repositorio ni en el entorno de pruebas. Es un requisito legal, no una preferencia: Ley 1581 de
  2012 sobre datos de menores (`ALC-OUT-08`).

## Al trabajar una tarea del Sprint 1

1. Busca la tarea en `docs/sprint-1-backlog.md` (`TT-nn`) y la historia de la que cuelga (`HU-nn`).
2. Lee los **criterios de aceptación** de esa historia en `docs/backlog-historias-de-usuario.md`.
   Son el contrato: ni menos, ni más.
3. Mira su campo **Origen**: dice de qué elemento del alcance sale. Si vas a construir algo que no
   está ahí, para.
4. Comprueba si sostiene alguna invariante. Si sí, hace falta un caso de prueba que la ejercite.
5. Al terminar, marca la tarea `☑` **en los dos documentos** —`plan-de-pull-requests.md` y
   `sprint-1-backlog.md`— dentro del propio PR, y actualiza los contadores. Deben coincidir.

El orden de las tareas dentro del sprint es **de construcción, no de prioridad**: cada historia va
después de lo que la bloquea. `[ANEXO D]` del backlog verifica el grafo de dependencias.

## Documentación

Estos cinco documentos son ahora **los vigentes**. El corpus de la asignatura conserva una copia
congelada; no la edites. Si una decisión cambia, se actualiza aquí, con su identificador.

Ninguna afirmación de estos documentos se inventa: cada una cita el identificador del que sale. Al
añadir contenido, mantén esa propiedad o el documento pierde su valor.
