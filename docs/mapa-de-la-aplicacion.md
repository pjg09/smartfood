# SmartFood — Mapa de la aplicación

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-MAPA |
| titulo | Qué pantallas existen, quién alcanza cada una y con qué cuenta se entra |
| tipo_documento | Documento operativo. **No es un artefacto de Scrum ni un entregable** |
| documentos_fuente | `config/urls.py`; `./smartfood.md` (`S11`, `S5`); `./decisiones-tecnicas.md` (`DT-2`, `DT-16`); `./desarrollo.md` |
| actualizado | 2026-09-01, al cierre del Sprint 1 |
| idioma | es-CO |
| version | 1.0 |

### [S0.1] Qué responde este documento

**Qué hay construido, por dónde se entra y qué ve cada rol.** `./desarrollo.md` dice cómo
levantar el entorno y con qué credenciales; esto dice qué encuentras una vez dentro.

**Cada código de respuesta de `[S2]` y `[S3]` se comprobó ejecutando**, con los cuatro roles
y con un anónimo, contra el entorno local sembrado. No hay ninguno supuesto.

---

## [S1] Por dónde se entra

**`/acceso/` es la puerta de los cuatro roles** (`TT-56`, `DEC-12`). Es la única por la que
puede entrar el acudiente: `/admin/login/` exige `is_staff` y lo rechaza siempre, porque
`INT-1` no es el admin (`DT-2`).

`/admin/` también acepta a la institución y al personal de la cafetería, y es donde
trabajan: `INT-3` es el admin de Django y no lleva plantillas propias.

**Las credenciales locales están en `[S2.1]` de `./desarrollo.md`.** No se repiten aquí para
que no envejezcan en dos sitios. Las cuentas que siembra `manage.py sembrar --estudiantes N`
son `institucion@example.com`, `administracion@example.com`, `cajero@example.com` y una por
acudiente ficticio.

---

## [S2] Las once rutas

Pantallas propias, con Tailwind y HTMX. Todo lo demás vive en el admin (`[S3]`).

| Ruta | Qué es | Quién | Tarea |
|---|---|---|---|
| `/` | Portada; reparte según el rol de quien mira | Todos | `TT-05` |
| `/acceso/` | Entrar. Redirige si ya hay sesión | Todos | `TT-56` |
| `/salir/` | Cerrar sesión. **Solo POST**: un `GET` responde `405` | Todos | `TT-56` |
| `/invitacion/<uid>/<token>/` | Definir la contraseña propia desde la invitación | Quien tenga el enlace | `TT-11` |
| `/invitacion/lista/` | Confirmación de que quedó definida | — | `TT-11` |
| `/carga/` | Carga masiva de estudiantes y acudientes por CSV | Institución | `TT-24` |
| `/mis-estudiantes/` | Panel del acudiente con sus estudiantes | Acudiente | `TT-29` |
| `/mis-estudiantes/<id>/` | Fragmento HTMX del estudiante elegido | Acudiente, **solo los suyos** | `TT-29` |
| `/estudiantes/<id>/tarjeta/` | Tarjeta imprimible con su código de barras | Institución | `TT-37` |
| `/catalogo/imagenes/<clave>` | Imagen de un producto, con caché de un mes | **Cualquiera** | `TT-53` |
| `/salud/` | Sonda del despliegue | Cualquiera | `TT-04` |

**Comprobado ejecutando**, con cada rol identificado y con un anónimo:

| Ruta | Institución | Administración | Cajero | Acudiente | Anónimo |
|---|---|---|---|---|---|
| `/` | 200 | 200 | 200 | 200 | 200 |
| `/carga/` | **200** | 403 | 403 | 403 | 302 → acceso |
| `/mis-estudiantes/` | 403 | 403 | 403 | **200** | 302 → acceso |
| `/estudiantes/<id>/tarjeta/` | **200** | 403 | 403 | 403 | 302 → acceso |
| `/catalogo/imagenes/<clave>` | 200 | 200 | 200 | 200 | **200** |

Dos filas piden explicación:

- **El acudiente recibe `403` en la tarjeta, también la de su propio hijo.** `HU-45` es de
  `USR-5`: quien produce la tarjeta es el colegio. Si algún día el acudiente tiene que
  verla, será con una historia que lo pida.
- **La imagen del producto se sirve sin sesión, a propósito** (`DT-21`). «Público» significa
  *no sensible*: es la fotografía de una empanada. Exigir sesión no protegería nada y
  rompería la caché que `INT-2` necesita. La clave no se adivina: la genera el servidor.

---

## [S3] Qué ve cada rol en el admin

| Modelo | Institución | Administración | Cajero | Acudiente |
|---|---|---|---|---|
| `personas.estudiante` | **200** | 403 | 403 | 302 |
| `personas.acudiente` | **200** (solo consulta) | 403 | 403 | 302 |
| `personas.institucion` | **200** | 403 | 403 | 302 |
| `cuentas.usuario` | **200** | 403 | 403 | 302 |
| `catalogo.producto` | 403 | **200** | 403 | 302 |
| `catalogo.categoria` | 403 | **200** | 403 | 302 |
| `catalogo.alergeno` | 403 | **200** | 403 | 302 |
| `auth.group` | **403** | 403 | 403 | 302 |

Es la matriz `[S11]` en la capa de datos (`DT-11`), no botones escondidos. Tres lecturas que
conviene no perder:

- **El catálogo es de quien lo vende.** La institución recibe `403`: `[S11]` no le da el
  catálogo, y desde `UX-6` ya no es superusuario, así que la matriz la vincula de verdad.
- **Nadie alcanza los grupos de permisos.** Esos grupos **son** la matriz con la que `DT-11`
  sostiene `INV-4`; quien los edita puede concederle al cajero lo que la invariante prohíbe.
- **El cajero entra al admin y ve una página vacía.** Es lo esperado: no tiene ningún modelo
  hasta el punto de venta del Sprint 2 (`HU-15`, `HU-17`).

---

## [S4] Lo que hace cada rol, pantalla por pantalla

### Institución educativa (`USR-5`)

Carga masiva en `/carga/`. En el admin: *Estudiantes* —listado con estado, código de tarjeta
y si tiene fotografía; búsqueda por nombre, documento, código o acudiente; alta individual
con autocompletado; acciones de **reasignar el código** y **dar de baja**, las dos con
confirmación—, *Acudientes* de solo consulta, y *Usuarios* para dar de alta al personal,
desactivarlo, reactivarlo y reenviarle la invitación.

### Administración de la cafetería (`USR-4`)

En el admin: productos con precio, categoría, ocho campos nutricionales por porción
(`./campos-nutricionales.md`), alérgenos declarados e imagen; categorías; alérgenos.
Acciones de retirar y devolver al catálogo. **Nada se borra**: retirar es un estado.

### Acudiente (`USR-2`)

`/mis-estudiantes/`: sus estudiantes, con selector cuando tiene más de uno. Si alguno está
de baja, lo dice. El saldo, el límite diario y las restricciones **son suyos y llegan en los
sprints 2 y 3**; hoy la pantalla declara dónde irán.

### Cajero (`USR-3`)

**Nada todavía.** Su cuenta existe, entra y se le puede desactivar (`HU-40`, `HU-41`,
`HU-42`), pero el punto de venta es del Sprint 2.

---

## [S5] El recorrido de demostración

El orden en que se enseña lo construido. Cada paso se comprobó de extremo a extremo.

1. **`/acceso/` como institución** → `/carga/`, subir un CSV con dos filas del mismo
   acudiente. `HU-01`, `HU-02`.
2. **`manage.py invitacion <correo del acudiente>`** → abrir el enlace, definir la
   contraseña. `HU-03`. **Tiene que ser un acudiente cargado por la pantalla**: a los que
   siembra `--estudiantes` se les asigna contraseña y el comando los rechaza (`DEC-11`).
3. **`/acceso/` con ese acudiente** → `/mis-estudiantes/`, con su selector. `HU-04`.
4. **Como institución**, *Estudiantes* → **Imprimir tarjeta**, al 100 %. `HU-43`, `HU-45`.
5. **Reasignar el código** y volver a imprimir: la tarjeta anterior deja de identificar a
   nadie en el mismo momento. `HU-46`, `INVD-4`.
6. **Dar de baja**: no borra nada y el acudiente lo ve en su panel. `HU-51`.
7. **`/acceso/` como administración** → el catálogo. `HU-26`, `HU-57`, `HU-59`.

---

## [S6] Lo que todavía no existe

Saldo y recargas (`HU-06`…`HU-08`), restricciones y límite diario (`HU-09`…`HU-13`), punto
de venta (`HU-15`…`HU-22`), inventario (`HU-27`…`HU-29`), reportes y recomendaciones
(`HU-30`…`HU-34`) y cierre de caja (`HU-55`, `HU-56`). Ninguno es del Sprint 1.

Las apps `billetera`, `inventario`, `ventas` y `reportes` **no están creadas**: cada una se
crea en el sprint que la necesita (`[S3]` de `./decisiones-tecnicas.md`).
