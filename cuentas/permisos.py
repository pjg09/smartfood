"""La matriz de permisos `[S11]` como dato (`TT-15`).

**Es la base de `INV-4`.** La invariante dice que la cafetería no desactiva las
restricciones alimentarias, y `DT-11` precisa cómo se sostiene: **con permisos en
la capa de datos, no ocultando un botón**. Un botón oculto lo salta cualquiera
con la URL; un permiso que no existe no se salta.

Por eso la matriz vive aquí, en un solo sitio y como estructura de datos, y no
repartida en decoradores por las vistas. Se puede leer entera, compararla con
`[S11]` del anteproyecto, y comprobarla con una prueba.

**Lo que hoy se puede conceder es poco, y conviene no disimularlo.** Varias
funciones de `[S11]` operan sobre modelos a los que ningún rol llega por el
admin: la billetera y las restricciones son del acudiente, y el acudiente no
entra a `INT-3` (`DT-2`). Lo que sí queda montado es el mecanismo y la forma de
la matriz, de modo que cada modelo nuevo entre por aquí y no por un decorador
suelto.
"""

from cuentas.models import Rol

# --- Lo que [S11] concede a cada rol, sobre los modelos que YA existen -------
#
# Formato: {rol: {"app.modelo": ["add", "change", "delete", "view"]}}
#
# Lo que no está, NO se concede. La prueba `test_ningun_rol_tiene_permisos_de
# _mas` compara los permisos efectivos contra esta tabla y falla si alguien
# concede algo por fuera.

PERMISOS_POR_ROL = {
    # `USR-5`. «Cargar estudiantes y crear cuentas de acudientes: Sí» y, por
    # `DEC-2`, también las cuentas del personal de la cafetería (`HU-40`).
    Rol.INSTITUCION: {
        "cuentas.usuario": ["add", "view", "change"],
        "personas.institucion": ["view", "change"],
        # `HU-44`, tercer criterio: administrar estudiantes es función
        # **exclusiva** de la institución educativa. Aquí es donde se hace
        # exclusiva; ningún otro rol la tiene, y esa ausencia es la mitad que
        # importa.
        #
        # **Sin `delete`, y a propósito.** El estudiante que se va no se borra:
        # se da de baja, que es un estado y conserva el historial (`DT-12`,
        # `HU-51`). Borrar la fila destruiría la trazabilidad que `OBJ-E2` pide,
        # y las claves ajenas van con `PROTECT` justamente por eso.
        "personas.estudiante": ["add", "view", "change"],
        # Ver al acudiente de un estudiante es parte de administrarlo. Escribirlo
        # no: la cuenta del acudiente se gestiona desde `cuentas.usuario`.
        "personas.acudiente": ["view"],
        # «Consultar restricciones de un estudiante: Sí» (`HU-38`, `TT-111`).
        # **Solo `view`, y no porque se haya elegido no dar más**: el proxy no
        # tiene otro permiso que conceder (`default_permissions`). Escribirlas
        # sigue siendo del acudiente (`INV-4`, `HU-13`).
        "restricciones.restriccionesdelestudiante": ["view"],
    },
    # `USR-4`. «Gestionar catálogo, precios e inventario» y «Consultar reportes
    # de ventas e inventario». El catálogo ya existe (`TT-43`); el inventario y
    # los reportes llegan en sprints posteriores.
    #
    # **Sin `delete` en ninguno de los tres**, y por el mismo motivo que en
    # `personas`: un producto que ya se vendió no puede desaparecer, porque el
    # historial de inventario lo referencia y sin él las existencias dejan de
    # explicarse (`INV-3`). Se retira del catálogo, que es un estado.
    Rol.ADMINISTRADOR: {
        "catalogo.producto": ["add", "view", "change"],
        "catalogo.categoria": ["add", "view", "change"],
        "catalogo.alergeno": ["add", "view", "change"],
        "catalogo.productoalergeno": ["add", "view", "change", "delete"],
        # `HU-27`, `TT-69`. **Sin `change` ni `delete`, y no es una omisión.**
        # Un asiento del libro corregido a posteriori deja unas existencias que
        # ya no explican lo que pasó, y `INV-3` dice justo lo contrario. Un error
        # se corrige con otro movimiento —una merma con su motivo (`INV-8`)—,
        # que es como se corrige un libro.
        "inventario.movimientoinventario": ["add", "view"],
        # `HU-28`, `TT-139`. La merma es un proxy del mismo libro con su propia
        # entrada en el admin, porque el motivo es obligatorio en ella y opcional
        # en el ingreso (`INV-8`). **Solo `add` y `view` existen**: `Merma.Meta`
        # declara `default_permissions = ("add", "view")`, así que Django no crea
        # `change_` ni `delete_` y esta matriz no podría concederlos ni queriendo
        # (`DT-11`). No amplía `[S11]`: cae dentro de «gestionar catálogo,
        # precios e inventario», igual que el ingreso.
        "inventario.merma": ["add", "view"],
        # «Consultar restricciones de un estudiante: Sí» (`HU-38`, `TT-111`).
        # Es la única entrada de esta fila fuera de `catalogo` e `inventario`, y
        # es de lectura: la cafetería **ve** quién es alérgico al maní y no
        # puede quitárselo (`INV-4`). El proxy no tiene otro permiso que `view`.
        "restricciones.restriccionesdelestudiante": ["view"],
    },
    # `USR-3`. «Registrar ventas» y «Consultar restricciones» —consultar, no
    # modificar: ahí está `INV-4`—. Las consulta en `INT-2`, al identificar al
    # estudiante (`TT-109`), no en el admin.
    #
    # **`ventas.Venta` ya existe (`TT-78`) y sigue sin haber permiso, igual que
    # la recarga del acudiente.** El cajero no entra al admin: `INT-2` es su
    # interfaz, y quién puede vender lo decide el servicio de venta con el
    # `actor` que recibe (`DT-15`). Un permiso aquí no protegería nada y
    # sugeriría un camino por el admin que no existe.
    #
    # **Y desde ahora tampoco tiene `is_staff`.** Este diccionario vacío decía
    # la verdad y la cuenta la contradecía: podía entrar al admin y ver un
    # índice sin un solo modelo. `crear_personal` se lo da solo a `USR-4`.
    Rol.CAJERO: {},
    # `USR-2`. «Recargar saldo», «fijar límite diario», «configurar y retirar
    # restricciones» y consultar los reportes de su hijo.
    #
    # **Sus modelos ya existen —`billetera` desde `TT-59`, `restricciones` desde
    # `TT-94`— y sigue sin tener un solo permiso, que es lo correcto.** El
    # acudiente no entra al admin: `INT-1` es su interfaz (`DT-2`), y quién puede
    # escribir lo decide `restricciones.services` con el `actor` que recibe
    # (`DT-15`). Un permiso aquí no protegería nada y sugeriría un camino por
    # `INT-3` que no existe.
    Rol.ACUDIENTE: {},
}

# --- Lo que [S11] concede pero todavía no tiene dónde -----------------------
#
# Se declara para que la matriz esté completa y para que nadie lea el diccionario
# de arriba y concluya que al cajero no le corresponde nada. Cuando el modelo
# aparezca, su fila se muda arriba; hasta entonces esto documenta la deuda.

FUNCIONES_PENDIENTES_DE_MODELO = {
    Rol.ACUDIENTE: [
        # **Construidas y con modelo desde el Sprint 3** (`TT-94`, `TT-97`,
        # `TT-100`, `TT-104`), y aun así siguen aquí: lo que no tienen es permiso
        # de Django, por lo mismo que la recarga. Ver `Rol.ACUDIENTE` arriba.
        # **«Recargar saldo» ya está construida** (`HU-06`, `TT-60`), y aun así
        # sigue en esta lista: lo que no tiene es un permiso de Django, porque el
        # acudiente no entra al admin. `INT-1` es su interfaz (`DT-2`), y quién
        # puede recargar lo decide `billetera.services` con el `actor` que
        # recibe. Un permiso aquí no protegería nada y sugeriría un camino por el
        # admin que no existe.
        "Recargar saldo (hecha en INT-1, sin permiso de admin) y fijar límite diario",
        "Configurar y retirar restricciones alimentarias (hecha en INT-1, sin permiso)",
        "Consultar restricciones de sus estudiantes (hecha en INT-1, sin permiso)",
        "Consultar saldo de un estudiante",
        "Consultar reportes de consumo de su hijo",
    ],
    Rol.CAJERO: [
        # Como la recarga del acudiente: **construida, y sin permiso de admin**.
        # El modelo existe desde `TT-78` y el cobro llega con `TT-80`; lo que no
        # hay ni habrá es una puerta por `INT-3` para el cajero.
        "Registrar ventas (modelo desde TT-78, sin permiso de admin)",
        # Hecha en `INT-2` (`TT-109`, `HU-38`), por el mismo camino que el saldo.
        # A diferencia del saldo, `[S11]` no la limita al cobro: la ve al
        # identificar, cobre o no.
        "Consultar restricciones de un estudiante (hecha en INT-2, al identificar)",
        # Hecha en `INT-2` (`HU-17`, `TT-74`): la concede
        # `ventas.selectors.informacion_de_cobro`, que exige el rol, no un
        # permiso de Django.
        "Consultar saldo de un estudiante (hecha en INT-2, solo al cobrar)",
    ],
    # «Consultar restricciones de un estudiante» ya no está en ninguno de los dos:
    # se mudó arriba con `TT-111`, como `view` sobre
    # `restricciones.restriccionesdelestudiante`.
    Rol.ADMINISTRADOR: [
        "Consultar reportes de ventas e inventario",
    ],
    Rol.INSTITUCION: [],
}

# --- Lo que NINGÚN rol de la cafetería puede hacer, nunca -------------------
#
# `INV-4` en negativo, y es la mitad que importa: la lista de arriba dice qué se
# concede; esta dice qué no se concede aunque alguien lo pida. Cuando exista el
# modelo de restricciones, escribir sobre él queda fuera del alcance de `USR-3`
# y `USR-4` **en la capa de datos**, no en la interfaz.

ESCRITURA_PROHIBIDA = {
    # «Saldo» sigue aquí **aunque el cajero acabe de estrenar el medio de pago**
    # (`TT-79`): elegir con qué se cobra no es escribir el saldo. El movimiento
    # lo asienta el servicio de venta contra el libro, y sobre él el cajero no
    # tiene ninguna otra vía (`INV-2`, `DT-24`).
    Rol.CAJERO: ["restricciones alimentarias", "saldo", "límite diario"],
    Rol.ADMINISTRADOR: ["restricciones alimentarias", "saldo", "límite diario"],
    # **La institución educativa faltaba, y no es un detalle** (`TT-107`).
    # `INV-4` dice «ni el personal de la cafetería **ni la institución**», y el
    # tercer criterio de `HU-13` lo repite: «la institución educativa tampoco
    # puede modificarlas». Este diccionario solo tenía los dos roles de la
    # cafetería, así que la mitad de la invariante estaba declarada y la otra no.
    #
    # La institución sí administra estudiantes (`HU-44`), y eso invita a pensar
    # que las restricciones de sus estudiantes son suyas. No lo son: el control
    # parental es del acudiente, y que el colegio pueda levantarlo lo convertiría
    # en una sugerencia.
    Rol.INSTITUCION: ["restricciones alimentarias", "límite diario"],
}

# --- La app entera, cerrada a la escritura por el admin ---------------------
#
# `ESCRITURA_PROHIBIDA` nombra conceptos y la prueba los busca por subcadena.
# Servía mientras los modelos no existían y sigue sirviendo, pero ahora se puede
# decir algo más fuerte que no depende de acertar con el nombre: **ningún rol
# tiene escritura sobre ningún modelo de `restricciones`.**
#
# No es una lista de modelos, es el prefijo de la app. Un modelo nuevo ahí dentro
# —el asiento de `TT-104` lo fue— queda cubierto sin que nadie se acuerde de
# añadirlo, que es la diferencia entre una regla y una foto del momento.
APPS_SIN_ESCRITURA_PARA_NINGUN_ROL = ["restricciones"]


def nombre_del_grupo(rol):
    """El grupo de Django que materializa un rol."""
    return f"rol:{rol}"
