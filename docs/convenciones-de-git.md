# SmartFood — Convenciones de Git

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-GIT |
| titulo | Integración en `main`, convención de commits y publicación de versiones |
| documentos_fuente | `./sprint-1-backlog.md` (`TT-01`, `[S2]`); `./decisiones-tecnicas.md` (`DT-13`) |
| tipo_documento | Convención de trabajo. No es un artefacto de Scrum |
| cubre | `TT-01` — Repositorio, estrategia de ramas y convención de commits |
| idioma | es-CO |
| version | 1.4 |

Este documento es el contrato de cómo entra código a `main`. **Casi nada de lo que aquí se
decide lo hace cumplir una máquina**: `main` no tiene protección activa, la CI no corre
pruebas (`DT-39`) y se empuja directo (`DT-41`). Lo que se sostiene, se sostiene porque cada
uno lo cumple antes de empujar.

---

## [S1] Se integra empujando directo a `main`

**Una sola rama: `main`.** Desde `DT-41` el trabajo se commitea y se empuja directo a `main`,
sin ramas de trabajo ni Pull Requests. Es una decisión del equipo por tiempo, tomada sabiendo
lo que se pierde: la revisión del otro desarrollador antes de integrar y la validación
automática del mensaje (`[S2.5]`).

**Nada lo hace cumplir.** `main` no tiene protección activa en GitHub —las reglas `main` y
`main-protected` existen pero están desactivadas— y la CI ya no corre pruebas (`DT-39`). Lo
que se sostiene, se sostiene porque cada uno lo cumple antes de empujar:

| Regla | Por qué |
|---|---|
| **Antes de empujar, los tres comandos en verde** (`[S5]` de `./desarrollo.md`) | Nadie los repite después: lo que no pasó en tu máquina llega a `main` roto |
| **Cada commit cumple `[S2]`** | `semantic-release` lee cada commit tal cual, y nadie revisa el mensaje antes (`[S2.5]`) |
| **`git pull --rebase` antes de empujar** | Con dos personas empujando, el historial se mantiene lineal y los conflictos se resuelven en tu máquina, no en `main` |
| **Nunca `push --force` sobre `main`** | Borraría los commits que el otro ya empujó |
| **Commits pequeños y con un solo tema** | Sin squash, cada commit es una entrada del historial y del cálculo de la versión |

**Las ramas no están prohibidas**: para algo grande o para pedir revisión se puede abrir un
Pull Request, y el flujo de antes sigue funcionando —squash, título validado—. Pero no es
el camino por defecto.

### [S1.1] Ciclo de trabajo

```bash
git switch main && git pull --rebase           # 1. partir de main al día
# ... commits siguiendo [S2], uno por tema ...
# ... los tres comandos en verde (y el script de [S5.3] si tocas infraestructura) ...
git pull --rebase                              # 2. traer lo que empujó el otro
git push                                       # 3. integrar
```

**Si el `pull --rebase` trae cambios del otro, vuelve a correr la suite antes de empujar**:
lo que probaste ya no es lo que vas a integrar.

**Las tareas siguen siendo la unidad de trazabilidad.** El `TT-nn` y el `HU-nn` van en el
`Refs:` de cada commit (`[S2]`), y los `PR-nn` de los planes de sprint siguen siendo la forma
de agrupar el trabajo: ahora son un conjunto de commits empujados, no un Pull Request.

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
| `restricciones` | App `restricciones`: control parental —límite diario, productos y alérgenos bloqueados (`DT-28`) |
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

**Un `!` antes de los dos puntos, en el resumen del commit.**

```
feat(billetera)!: reconstruir el saldo desde el historial
```

**Ojo con tres notas en el cuerpo: ahora también cuentan.** Con push directo cada commit
llega a `main` entero, y `semantic-release` lee como cambio incompatible una línea que empiece
por `BREAKING CHANGE:`, `BREAKING-CHANGE:` o **`CAMBIO INCOMPATIBLE:`** (`noteKeywords` de
`.releaserc.json`). La última es la que se escribe sin querer en español, y cualquiera de las
tres, puesta para explicar algo, **publica una versión mayor**. Si el cambio es incompatible, usa el `!` y explícalo en el cuerpo con otras
palabras; si no lo es, no escribas esa nota.

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

> Con push directo, **cada commit que empujas llega a `main` tal cual**, con su cuerpo, y
> `semantic-release` analiza todos los que entraron desde la última versión.

**Nadie valida el mensaje antes de que llegue.** `.github/workflows/convencion-de-commits.yml`
solo comprueba el título de un Pull Request, y en el flujo habitual no hay ninguno. Un
`tipo` mal escrito —`feature:` en vez de `feat:`, un ámbito con mayúsculas— no da error: ese
commit simplemente no cuenta para la versión, o cuenta como otra cosa. Revisa el mensaje
antes de empujar: `git log origin/main..HEAD --format='%s'`.

**El cuerpo del commit sí se conserva**, y con él los `Refs: TT-nn`: la trazabilidad queda
en el historial de `main`, sin depender de un Pull Request.

**Si se abre un Pull Request**, rige lo de siempre: el repositorio solo permite squash, con el
título del PR como mensaje y el cuerpo vacío, así que lo que cuenta es el título, y la
validación sí corre.

---

## [S3] Publicación de versiones

`semantic-release` corre en **cada `push` a `main`**. Configuración en `.releaserc.json`, workflow en `.github/workflows/publicar-version.yml`.

### [S3.0] La versión no espera a las pruebas: las pruebas van antes, en local

**La CI no corre pruebas** (`DT-39`). El workflow tiene un solo trabajo, `release`, y
publica con lo que haya en `main`. Con push directo (`DT-41`) GitHub no comprueba nada antes:
ni la suite ni el mensaje del commit (`[S2.5]`).

**Que se publique una versión no dice que la suite pase: lo dice quien la corrió.** Antes de
integrar, en local, los tres comandos de `[S5]` de `./desarrollo.md` —`check`,
`makemigrations --check` y la suite entera—, y **si el cambio toca la infraestructura**,
`docker/comprobar-desde-cero.sh`, que levanta el stack desde cero como lo haría otra máquina
(`[S5.3]` del mismo documento). Lo que antes hacía la CI lo hace ahora quien empuja, y solo
cuando hace falta.

**La suite no se enumera en ninguna parte.** `manage.py test` sin argumentos descubre todo
`test*.py` en cada app, así que una prueba nueva entra sola. Las dos formas de que una prueba
se quede fuera sin avisar —un fichero que no casa con el patrón y una carpeta sin
`__init__.py`— las vigila `config/tests_descubrimiento.py`.

| Aspecto | Decisión |
|---|---|
| Rama | `main`, y solo `main` |
| Etiqueta | `v1.4.0` (`tagFormat: v${version}`) |
| Notas | Se generan en la **Release de GitHub**, agrupadas por tipo y en español |
| `CHANGELOG.md` | **No se genera.** Decisión explícita del equipo |
| Publicación a un registro | Ninguna. No hay paquete que publicar |
| Node en local | **No hace falta.** Solo existe dentro del runner de GitHub Actions |

Sin `@semantic-release/changelog` ni `@semantic-release/git`, el proceso **no escribe de
vuelta en el repositorio**: solo crea la etiqueta y la Release. Por eso no necesita permiso
para empujar a `main`: si algún día se reactiva su protección, no hará falta ninguna excepción
para el bot.

### [S3.1] Cómo se calcula la versión

Se leen los commits desde la última etiqueta y gana el de mayor impacto:

| Hay al menos un… | Versión |
|---|---|
| Cambio incompatible: `!` en el resumen, o una nota `BREAKING CHANGE:` en el cuerpo (`[S2.3]`) | `major` — `1.4.2` → `2.0.0` |
| `feat` | `minor` — `1.4.2` → `1.5.0` |
| `fix`, `perf`, `refactor`, `revert` | `patch` — `1.4.2` → `1.4.3` |
| Solo `docs`, `test`, `build`, `ci`, `style`, `chore` | **No se publica nada** |

Que un commit de solo documentación no publique versión es intencional: el número de versión
mide el sistema, no la actividad.
