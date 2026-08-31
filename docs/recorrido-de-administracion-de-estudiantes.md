# SmartFood — Recorrido de la vista de administración de estudiantes

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-UX-ADMIN-ESTUDIANTES |
| titulo | Recorrido de experiencia de usuario de la vista de administración de estudiantes |
| tipo_documento | Documento derivado. Recorrido de experiencia de usuario |
| documentos_fuente | `./backlog-historias-de-usuario.md` (`HU-44`, `HU-45`, `HU-51`); `./decisiones-tecnicas.md` (`DT-2`, `DT-11`, `DT-12`, `DT-15`, `ANEXO A`); `./smartfood.md` (`S11`, `INT-3`) |
| cubre | `TT-35` — Recorrido de experiencia de usuario de la vista de administración |
| responsable | Alejandro (análisis y UX) |
| recorrido_el | 2026-08-31, sobre el entorno local |
| idioma | es-CO |
| version | 1.1 |

### [S0.1] Qué es este documento

**Lo que se recorrió es la vista construida, no un boceto.** Cada observación de `[S2]`
sale de abrir la pantalla y hacer la tarea; ninguna es una previsión. Las que se
corrigieron dentro de `PR-16` lo dicen, y **las que no, también**: un recorrido que solo
enumera lo que ya está arreglado no sirve de nada en la siguiente revisión.

De las seis, cuatro se corrigieron. `[UX-4]` es deliberada —el código de tarjeta llega en
`PR-17`— y `[UX-5]` es una limitación de estas dos semanas: falta la baja, que es `PR-19`.

`[UX-6]` no era de la vista y se corrigió igual: la cuenta institucional era superusuario
de Django, y eso le daba todos los permisos existan o no en la matriz. Se abrió como
«pendiente de decisión» y el equipo decidió el mismo día retirar el privilegio.

`INT-3` es el admin de Django (`DT-2`), así que aquí no se diseña una interfaz: se
comprueba que **la que el framework genera sirve para lo que `HU-44` pide**, y se ajusta
lo que no. El `ANEXO A` de `./decisiones-tecnicas.md` ya anticipaba que `TT-34` «se reduce
a declarar el modelo en el admin»; este recorrido es la comprobación de que esa reducción
era cierta.

---

## [S1] Quién recorre y qué viene a hacer

**`USR-5`, la institución educativa.** No es un usuario técnico y no entra todos los días:
entra en matrícula, y luego de forma esporádica cuando algo cambia. Eso define lo que hay
que optimizar — **encontrar rápido a un estudiante concreto** — y lo que no hace falta:
atajos de teclado, operaciones masivas o personalización de la vista.

Las tres tareas de `HU-44`, en el orden en que aparecen en un curso:

| | Tarea | Cuándo |
|---|---|---|
| `T1` | Matricular a un estudiante que llegó fuera de la carga inicial | Durante el año |
| `T2` | Corregir los datos de uno ya cargado | Durante el año |
| `T3` | Buscar a un estudiante concreto entre todos | Continuamente, y antes de `T2` |

`T3` no está escrita como criterio de aceptación, pero **`T2` no existe sin ella**: no se
puede editar a quien no se encuentra. Por eso `TT-34` nombra la búsqueda junto al listado.

---

## [S2] Lo que se observó

### `[UX-1]` El formulario de matrícula pedía campos que no se pueden llenar — **corregido**

Al abrir «Añadir estudiante», el formulario mostraba cinco filas: *Nombre*, *Documento*,
*Acudiente*, ***Id*** y ***Creado en***. Las dos últimas son de solo lectura y, en un alta,
están vacías: no le dicen nada a quien matricula y compiten por su atención con los tres
campos que sí tiene que llenar.

**Corregido en `PR-16`:** solo se muestran al editar, que es cuando tienen valor. Con
prueba, para que no vuelva.

### `[UX-2]` Elegir al acudiente era recorrer una lista de cientos de nombres — **corregido**

El campo *Acudiente* era un `<select>` con **todos** los acudientes del sistema, ordenados
por nombre. Con cinco de prueba se ve bien. Con un colegio real son cientos de opciones en
una lista desplegable, y la institución tiene que reconocer al de este estudiante a ojo,
sin poder buscar.

Es además el único campo del formulario que **no** se puede rellenar leyendo el papel que
la institución tiene delante: los otros dos se copian, este hay que encontrarlo.

**Corregido en `PR-16`:** el campo busca mientras se escribe, por nombre y por documento
del acudiente. Con prueba de que el buscador responde.

### `[UX-3]` Buscar por el acudiente era la búsqueda que faltaba — **corregido**

La pregunta que la institución se hace no es «el estudiante 1001234501», es **«los hijos de
Marta Ruiz»**. La búsqueda del listado cubre ahora nombre y documento del estudiante **y
del acudiente**: escribir «Marta» devuelve a sus dos hijos.

### `[UX-4]` El código de tarjeta no aparecía por ninguna parte — **resuelto en `PR-17`**

Cuando se recorrió la vista, el listado mostraba *Nombre*, *Documento*, *Acudiente* y
*Creado en*, y el código de tarjeta no estaba ni en el listado ni en la ficha.

No era un olvido: exponer el código vigente es `TT-36`, y `HU-45` es la historia que lo
pide. Adelantarlo en `PR-16` habría dejado a `PR-17` sin su primera tarea.

`PR-17` lo añadió al listado, a la ficha y a la búsqueda —buscar por el código responde a
la pregunta que se hace con una tarjeta suelta en la mano: **¿de quién es esta?**— y le
puso al lado el enlace a la vista imprimible. **Sigue sin poder escribirse**: verlo no es
poder editarlo (`HU-14`).

### `[UX-5]` No hay forma de borrar a un estudiante, y no debe haberla

Ni el listado ofrece la acción de borrar, ni la ficha el botón, ni la URL de borrado
responde: es un `403`.

Es correcto. El estudiante que se va del colegio se da de **baja**, que es un estado
distinto de «desactivado» y conserva íntegro su historial (`DT-12`, `DEC-7`, `HU-51`).
Borrar la fila se llevaría por delante su billetera y sus compras, que es justo la
trazabilidad que `OBJ-E2` pide del sistema.

**Falta el camino sancionado**, eso sí: la baja llega en `PR-19` (`TT-41`, `TT-42`). Hasta
entonces, un estudiante matriculado por error se corrige editándolo, y uno matriculado de
más se queda. Es una limitación real de estas dos semanas, no un defecto de la vista.

### `[UX-6]` La institución podía editar los grupos de permisos — **corregido**

En el índice del admin, junto a *Estudiantes*, *Acudientes*, *Usuarios* e *Instituciones
educativas*, la institución veía **Grupos** de Django, y podía entrar a crearlos y
modificarlos: `/admin/auth/group/add/` respondía `200`.

**Por qué importaba.** Esos grupos **son** la matriz `[S11]`: `DT-11` sostiene `INV-4`
—«las restricciones alimentarias no las desactiva la cafetería»— concediendo permisos por
rol en la capa de datos. Quien puede editar un grupo puede concederle al cajero el permiso
de escritura sobre las restricciones el día que ese modelo exista, y entonces `INV-4` se
sostiene sobre una puerta que está abierta.

**Por qué ocurría.** La cuenta institucional se creaba con `is_superuser=True` en el seed
(`TT-10`, `HU-39`), con el argumento de que es el actor con más permisos del prototipo. Es
cierto que lo es; el problema es lo que esa bandera significa: un superusuario de Django
tiene **todos** los permisos por definición, se declaren o no en la matriz.

**Qué se hizo.** Se retiró la bandera. La institución tiene ahora exactamente los nueve
permisos que `cuentas/permisos.py` declara, conserva `is_staff` —entra al admin, que es
`INT-3`— y una migración de datos la retira también de las bases ya sembradas, porque el
seed es idempotente y no vuelve a tocar una institución que ya existe.

**Eran dos puertas, no una.** Quitar la bandera habría sido cosmético mientras el
formulario de usuario siguiera ofreciendo `is_superuser`, `groups` y `user_permissions`:
la institución se la habría devuelto con dos clics, o le habría concedido al cajero los
permisos directamente sobre su cuenta, sin pasar por ningún grupo. Esos tres campos, más
`rol` e `is_staff`, pasan a **solo lectura**: se ven —saber en qué grupo está una cuenta
es parte de administrarla— pero no se editan, porque se derivan del rol y los asigna
`asignar_grupo_del_rol`.

**Y apareció un tercero por el camino.** La casilla `is_active` también era editable, y
eso saltaba por encima de `desactivar_cuenta`, que se niega a que la institución se
desactive a sí misma porque después nadie podría reactivarla (`TT-19`, `HU-42`). Una
casilla y la institución quedaba fuera del sistema sin forma de volver a entrar. También
pasa a solo lectura: se cambia con las acciones del listado, que sí pasan por el servicio.

**Lo que queda del formulario de usuario son dos campos editables**, `correo` y `nombre`.
Todo lo demás, o se deriva del rol, o tiene un servicio con reglas propias. Es la forma
que toma `DT-15` cuando se aplica de verdad al admin.

**Lo que sigue siendo cierto y conviene no olvidar:** con la bandera puesta, la prueba
`test_ningun_rol_tiene_permisos_de_mas` pasaba sobre un actor al que los permisos no le
aplicaban. Es decir, el rol más poderoso del sistema era el único que esa prueba no
vigilaba. Ahora sí, y hay una prueba que compara sus permisos efectivos contra la matriz.

---

## [S3] Lo que la vista hace bien y conviene no tocar

Se registra porque un recorrido que solo lista problemas invita a rehacer lo que ya
funciona.

- **Está en español, entera**, incluidos los mensajes de error y los formatos de fecha
  («31 de Agosto de 2026 a las 12:56»). Es `TT-05`, y en el admin generado no era gratis.
- **El listado ordena por nombre**, que es como la institución piensa en sus estudiantes,
  y no por fecha de creación, que es como los guardó la carga.
- **La columna *Acudiente* muestra nombre y documento** —«Marta Ruiz Ochoa (43512345)»—,
  que resuelve el caso de dos acudientes homónimos sin abrir la ficha.
- **El alta confirma con un mensaje que explica el código de tarjeta**: «su código se
  generó automáticamente y no se puede escribir a mano». Es donde la institución se entera
  de que ese campo no le corresponde, y llega en el momento en que se lo preguntaría.

---

## [S4] Lo que este recorrido no cubre

- **La vista imprimible del código de barras** (`TT-37`), que entró en `PR-17` después de
  este recorrido. Merece el suyo propio, y solo se puede hacer entero con una impresora y
  un lector delante: es el insumo físico de `ENT-02`.
- **La fotografía del estudiante** (`TT-52`, `PR-20`). Cambia la ficha y el listado.
- **La baja** (`TT-42`, `PR-19`). Añade la acción que hoy `[UX-5]` echa en falta.
- **Uso en móvil.** El admin de Django es responsivo, pero `INT-3` es de escritorio por
  decisión (`DT-16`): la institución administra desde un computador. No se recorrió en
  pantalla pequeña y no se declara que funcione ahí.
