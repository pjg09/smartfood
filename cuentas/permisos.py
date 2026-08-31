"""La matriz de permisos `[S11]` como dato (`TT-15`).

**Es la base de `INV-4`.** La invariante dice que la cafetería no desactiva las
restricciones alimentarias, y `DT-11` precisa cómo se sostiene: **con permisos en
la capa de datos, no ocultando un botón**. Un botón oculto lo salta cualquiera
con la URL; un permiso que no existe no se salta.

Por eso la matriz vive aquí, en un solo sitio y como estructura de datos, y no
repartida en decoradores por las vistas. Se puede leer entera, compararla con
`[S11]` del anteproyecto, y comprobarla con una prueba.

**Lo que hoy se puede conceder es poco, y conviene no disimularlo.** La mayoría
de las funciones de `[S11]` operan sobre modelos que aún no existen: billetera,
restricciones, catálogo, inventario y ventas llegan en sprints posteriores. Lo
que sí queda montado es el mecanismo y la forma de la matriz, de modo que cada
modelo nuevo entre por aquí y no por un decorador suelto.
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
    },
    # `USR-4`. «Gestionar catálogo, precios e inventario» y «Consultar reportes
    # de ventas e inventario». Ningún modelo suyo existe todavía.
    Rol.ADMINISTRADOR: {},
    # `USR-3`. «Registrar ventas» y «Consultar restricciones» —consultar, no
    # modificar: ahí está `INV-4`—. Ningún modelo suyo existe todavía.
    Rol.CAJERO: {},
    # `USR-2`. «Recargar saldo», «fijar límite diario», «configurar y retirar
    # restricciones» y consultar los reportes de su hijo. Ningún modelo suyo
    # existe todavía.
    Rol.ACUDIENTE: {},
}

# --- Lo que [S11] concede pero todavía no tiene dónde -----------------------
#
# Se declara para que la matriz esté completa y para que nadie lea el diccionario
# de arriba y concluya que al cajero no le corresponde nada. Cuando el modelo
# aparezca, su fila se muda arriba; hasta entonces esto documenta la deuda.

FUNCIONES_PENDIENTES_DE_MODELO = {
    Rol.ACUDIENTE: [
        "Recargar saldo y fijar límite diario",
        "Configurar y retirar restricciones alimentarias",
        "Consultar restricciones de un estudiante",
        "Consultar saldo de un estudiante",
        "Consultar reportes de consumo de su hijo",
    ],
    Rol.CAJERO: [
        "Registrar ventas en el punto de venta",
        "Consultar restricciones de un estudiante",
        "Consultar saldo de un estudiante (solo al cobrar)",
    ],
    Rol.ADMINISTRADOR: [
        "Gestionar catálogo, precios e inventario",
        "Consultar restricciones de un estudiante",
        "Consultar reportes de ventas e inventario",
    ],
    Rol.INSTITUCION: [
        "Consultar restricciones de un estudiante",
    ],
}

# --- Lo que NINGÚN rol de la cafetería puede hacer, nunca -------------------
#
# `INV-4` en negativo, y es la mitad que importa: la lista de arriba dice qué se
# concede; esta dice qué no se concede aunque alguien lo pida. Cuando exista el
# modelo de restricciones, escribir sobre él queda fuera del alcance de `USR-3`
# y `USR-4` **en la capa de datos**, no en la interfaz.

ESCRITURA_PROHIBIDA = {
    Rol.CAJERO: ["restricciones alimentarias", "saldo", "límite diario"],
    Rol.ADMINISTRADOR: ["restricciones alimentarias", "saldo", "límite diario"],
}


def nombre_del_grupo(rol):
    """El grupo de Django que materializa un rol."""
    return f"rol:{rol}"
