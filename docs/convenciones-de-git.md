# SmartFood — Convenciones de Git

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-GIT |
| titulo | Estrategia de ramas, convención de commits y publicación de versiones |
| documentos_fuente | `./sprint-1-backlog.md` (`TT-01`, `[S2]`); `./decisiones-tecnicas.md` (`DT-13`) |
| tipo_documento | Convención de trabajo. No es un artefacto de Scrum |
| cubre | `TT-01` — Repositorio, estrategia de ramas y convención de commits |
| idioma | es-CO |
| version | 1.0 |

Este documento es el contrato de cómo entra código a `main`. Lo que aquí se decide lo
hace cumplir la automatización de `.github/workflows/`, no la buena voluntad.

---

## [S1] Estrategia de ramas: trunk based development

**Una sola rama de larga vida: `main`.** Siempre desplegable, siempre protegida.

| Regla | Consecuencia |
|---|---|
| `main` está protegida contra `push` directo | Todo entra por Pull Request, sin excepciones |
| Las ramas de trabajo son **cortas**: horas o un par de días | Si una rama vive más de dos días, el PR es demasiado grande: pártelo |
| Se ramifica **desde `main`**, nunca desde otra rama de trabajo | Sin ramas apiladas; sin `develop`, sin `release/*`, sin `hotfix/*` |
| Se integra con **squash merge** | Un PR = un commit en `main` = una entrada en el historial |
| La rama se borra al integrar | El repositorio no acumula ramas muertas |

**No hay GitFlow.** Con dos desarrolladores, cinco sprints y despliegue continuo a un
único entorno de pruebas (`DT-13`), una rama de integración intermedia solo añade
conflictos y ceremonia.

### [S1.1] Nombre de la rama

```
tipo/TT-nn-resumen-corto
```

Kebab-case ASCII, igual que los nombres de fichero. El identificador de la tarea va en
el nombre porque es lo que permite rastrear la rama hasta el backlog.

```
feat/TT-30-generador-codigo-tarjeta
feat/TT-21-modelos-estudiante-acudiente
fix/TT-25-validacion-todo-o-nada
docs/TT-07-definicion-de-terminado
```

Si el PR cubre varias tareas, se usa la **primera** del rango: `feat/TT-15-cuentas-de-personal`.

### [S1.2] Ciclo de trabajo

```bash
git switch main && git pull --ff-only          # 1. partir de main al día
git switch -c feat/TT-30-generador-codigo      # 2. rama corta
# ... commits siguiendo [S2] ...
git push -u origin feat/TT-30-generador-codigo # 3. subir
gh pr create --fill                            # 4. abrir PR (título = [S2])
# ... revisión del otro desarrollador + CI en verde ...
gh pr merge --squash --delete-branch           # 5. squash e integrar
```

**Rebase sobre `main`, no merge de `main` a la rama.** Mantiene el historial lineal y el
diff del PR limpio: `git pull --rebase origin main`.

---

## [S2] Convención de commits

Conventional Commits. **No es cosmética: es lo que decide el número de versión**
(`[S3]`). Un commit mal escrito no publica versión, o publica la equivocada.

```
tipo(ámbito): resumen en imperativo

Descripción de qué cambia y por qué, citando los identificadores del
backlog. Líneas de 72 caracteres o menos.

Refs: TT-30, HU-14, INV-7
```

Reglas:

1. **Los tipos y el separador van en inglés y en minúscula.** Es lo que la herramienta
   sabe leer. Todo lo demás —resumen, cuerpo, notas— va en **español**.
2. **El resumen va en imperativo y sin punto final**, máximo 72 caracteres:
   «generar el código de tarjeta», no «se generó» ni «generando».
3. **Línea en blanco obligatoria** entre el resumen y el cuerpo.
4. **El cuerpo cita los identificadores.** `HU-17` dice qué se construyó y por qué;
   `INV-5` dice qué no se puede romper. Un commit sin identificadores es un commit
   que nadie podrá auditar en la Sprint Review.

### [S2.1] Tipos

| Tipo | Cuándo | Versión que publica |
|---|---|---|
| `feat` | Funcionalidad nueva visible para algún usuario | **minor** |
| `fix` | Corrección de un defecto | **patch** |
| `perf` | Mejora de rendimiento sin cambiar el comportamiento | **patch** |
| `refactor` | Reorganización interna sin cambio de comportamiento | **patch** |
| `docs` | Solo documentación | ninguna |
| `test` | Solo casos de prueba | ninguna |
| `build` | Dependencias, `docker compose`, empaquetado | ninguna |
| `ci` | Workflows de GitHub Actions | ninguna |
| `style` | Formato, sin cambio de código | ninguna |
| `chore` | Mantenimiento que no encaja arriba | ninguna |
| `revert` | Revertir un commit anterior | **patch** |

### [S2.2] Ámbitos

El ámbito es **dónde** se hizo el cambio. Minúsculas, kebab-case ASCII, sin acentos.

| Ámbito | Corresponde a |
|---|---|
| `cuentas` | App `cuentas`: usuarios, roles, invitaciones, sesión |
| `personas` | App `personas`: estudiantes, acudientes, institución |
| `catalogo` | App `catalogo`: productos, categorías, alérgenos |
| `billetera` | App `billetera`: saldo y movimientos |
| `inventario` | App `inventario`: existencias |
| `ventas` | App `ventas`: punto de venta |
| `reportes` | App `reportes` |
| `almacenamiento` | Buckets, `django-storages`, canalización de imágenes (`DT-18`, `DT-20`) |
| `correo` | Envío de correo |
| `seed` | Generador de datos ficticios (`TT-08`, `DT-14`) |
| `plantillas` | Plantillas base, layout, Tailwind, HTMX |
| `infra` | `docker compose`, ajustes del proyecto, despliegue |
| `ci` | Workflows |
| `docs` | Documentos de `docs/` |

El ámbito es **opcional** cuando el cambio es transversal: `feat: ...`.

### [S2.3] Cambios incompatibles

Un `!` antes de los dos puntos, o una nota `BREAKING CHANGE:` al final del cuerpo.
Publican una versión **major**.

```
feat(billetera)!: reconstruir el saldo desde el historial

Se elimina la columna `saldo` de la tabla. El saldo pasa a ser la suma de
los movimientos, según INV-2 y DT-4. Toda lectura del saldo debe pasar por
el selector correspondiente.

BREAKING CHANGE: `Billetera.saldo` deja de existir.
Refs: TT-23, INV-2, DT-4
```

### [S2.4] Ejemplos completos

```
feat(personas): generar el código de tarjeta de forma aleatoria

Generador criptográfico con índice único y reintento ante colisión. No usa
secuencia ni deriva el código del identificador del estudiante: INV-7 lo
prohíbe porque el código opera como credencial de acceso al saldo. Tampoco
UUIDv7, que lleva timestamp y va ordenado (DT-9, DT-17).

Refs: TT-30, HU-14, INV-7
```

```
fix(personas): rechazar la carga completa si una fila falla

El validador acumulaba los errores pero el servicio ya había escrito las
filas anteriores. Se mueve la validación completa antes de abrir la
escritura, dentro de la misma transacción.

Refs: TT-25, HU-02
```

```
test(catalogo): comprobar que el alérgeno se relaciona, no se copia

Caso de prueba de INV-5: un producto creado después de definir la
restricción queda bloqueado sin tocar la restricción.

Refs: TT-46, HU-26, INV-5
```

### [S2.5] Lo que importa al integrar

> Con **squash merge**, lo que queda en `main` —y lo que analiza `semantic-release`— es
> el **título del Pull Request**, no tus commits locales.

El título del PR debe cumplir `[S2]`. `.github/workflows/convencion-de-commits.yml` lo
verifica en cada apertura y edición del PR y falla si no cumple. Los commits dentro de
la rama son tuyos: escríbelos bien igualmente, pero el que cuenta es el título.

---

## [S3] Publicación de versiones

`semantic-release` corre en **cada `push` a `main`**, es decir, cada vez que se integra
un PR. Configuración en `.releaserc.json`, workflow en `.github/workflows/release.yml`.

| Aspecto | Decisión |
|---|---|
| Rama | `main`, y solo `main` |
| Etiqueta | `v1.4.0` (`tagFormat: v${version}`) |
| Notas | Se generan en la **Release de GitHub**, agrupadas por tipo y en español |
| `CHANGELOG.md` | **No se genera.** Decisión explícita del equipo |
| Publicación a un registro | Ninguna. No hay paquete que publicar |
| Node en local | **No hace falta.** Solo existe dentro del runner de GitHub Actions |

Sin `@semantic-release/changelog` ni `@semantic-release/git`, el proceso **no escribe de
vuelta en el repositorio**: solo crea la etiqueta y la Release. Es lo que permite que
`main` siga protegida sin excepciones para el bot.

### [S3.1] Cómo se calcula la versión

Se leen los commits desde la última etiqueta y gana el de mayor impacto:

| Hay al menos un… | Versión |
|---|---|
| Cambio incompatible (`!` o `BREAKING CHANGE`) | `major` — `1.4.2` → `2.0.0` |
| `feat` | `minor` — `1.4.2` → `1.5.0` |
| `fix`, `perf`, `refactor`, `revert` | `patch` — `1.4.2` → `1.4.3` |
| Solo `docs`, `test`, `build`, `ci`, `style`, `chore` | **No se publica nada** |

Que un PR de solo documentación no publique versión es intencional: el número de versión
mide el sistema, no la actividad.
