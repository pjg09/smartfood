"""Escrituras del dominio de productos, categorías y alérgenos.

**Toda escritura pasa por aquí** (`DT-15`). Reglas que no se negocian:

1. Una vista nunca escribe directamente: llama a una función de este módulo.
2. Cada función abre su propia `transaction.atomic()`.
3. Estas funciones **no saben de HTTP**.

Funciones, no clases.
"""

from django.core.exceptions import PermissionDenied
from django.core.files.storage import storages
from django.db import transaction

from catalogo.models import Alergeno, Categoria, Producto, ProductoAlergeno
from config.imagenes import procesar_imagen
from cuentas.models import Rol


def _comprobar_que_gestiona_el_catalogo(actor, accion):
    """Tercer criterio de `HU-26`: solo la administración de la cafetería.

    `[S11]` se lo concede a `USR-4` y a nadie más. **Ni al cajero ni a la
    institución educativa**: el catálogo es de quien lo vende, y esa exclusión
    es parte de `INV-4` — el cajero no toca lo que condiciona una restricción.
    """
    if actor is None or actor.rol != Rol.ADMINISTRADOR:
        raise PermissionDenied(
            f"{accion} es función exclusiva de la administración de la cafetería "
            "(HU-26, [S11])."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")


@transaction.atomic
def crear_categoria(*, actor, nombre):
    _comprobar_que_gestiona_el_catalogo(actor, "Gestionar categorías")
    return Categoria.objects.create(nombre=nombre)


@transaction.atomic
def crear_alergeno(*, actor, nombre):
    _comprobar_que_gestiona_el_catalogo(actor, "Gestionar alérgenos")
    return Alergeno.objects.create(nombre=nombre)


@transaction.atomic
def crear_producto(*, actor, nombre, precio, categoria, alergenos=(), **nutricional):
    """Da de alta un producto con sus alérgenos declarados (`TT-43`, `HU-26`).

    Los alérgenos entran **por la relación**, nunca copiando nada al producto:
    es `INV-5` en el único camino de alta que hay.
    """
    _comprobar_que_gestiona_el_catalogo(actor, "Gestionar el catálogo")

    producto = Producto.objects.create(
        nombre=nombre, precio=precio, categoria=categoria, **nutricional
    )
    declarar_alergenos(actor=actor, producto=producto, alergenos=alergenos)
    return producto


@transaction.atomic
def editar_producto(*, actor, producto, **campos):
    """Cambia lo que la administración decide de un producto ya creado."""
    _comprobar_que_gestiona_el_catalogo(actor, "Gestionar el catálogo")

    alergenos = campos.pop("alergenos", None)

    cambiados = []
    for campo, valor in campos.items():
        if not hasattr(producto, campo):
            raise ValueError(f"«{campo}» no es un campo de un producto.")
        if getattr(producto, campo) != valor:
            setattr(producto, campo, valor)
            cambiados.append(campo)

    if cambiados:
        producto.save(update_fields=cambiados)

    if alergenos is not None:
        declarar_alergenos(actor=actor, producto=producto, alergenos=alergenos)

    return producto


@transaction.atomic
def declarar_alergenos(*, actor, producto, alergenos):
    """Deja el producto declarando **exactamente** esos alérgenos.

    Reemplaza, no acumula: si un producto deja de llevar lactosa, la declaración
    tiene que desaparecer o el bloqueo de `HU-11` seguiría rechazándolo para
    siempre.

    **Retirar una declaración no es «desbloquear» a nadie.** La restricción vive
    en el acudiente (`HU-11`) y no se toca desde aquí: `INV-4` dice que la
    cafetería no desactiva las restricciones, y este servicio no puede hacerlo ni
    queriendo, porque no escribe en esa tabla.
    """
    _comprobar_que_gestiona_el_catalogo(actor, "Declarar alérgenos")

    deseados = {a.pk for a in alergenos}
    actuales = set(
        ProductoAlergeno.objects.filter(producto=producto).values_list(
            "alergeno_id", flat=True
        )
    )

    ProductoAlergeno.objects.filter(
        producto=producto, alergeno_id__in=actuales - deseados
    ).delete()
    ProductoAlergeno.objects.bulk_create(
        [
            ProductoAlergeno(producto=producto, alergeno_id=pk)
            for pk in deseados - actuales
        ]
    )
    return producto


def _borrar_del_almacenamiento(clave):
    """Un fallo al borrar deja un huérfano, no un dato incorrecto: no propaga."""
    if not clave:
        return
    try:
        storages["publico"].delete(clave)
    except Exception:  # noqa: BLE001 — ver el docstring
        pass


@transaction.atomic
def guardar_imagen(*, actor, producto, archivo):
    """Carga o reemplaza la imagen de un producto (`TT-53`, `HU-59`).

    Misma canalización que la fotografía del estudiante (`DT-20`): se decodifica
    y se vuelve a codificar desde cero, así que se valida por contenido y no por
    nombre y se neutraliza cualquier fichero polígloto. Aquí no hay EXIF de un
    menor que retirar, pero la superficie de ataque es la misma: una imagen
    servida tal como se subió es un vector de XSS.

    Va al prefijo `publico/`, que no significa accesible sin credenciales sino
    **no sensible** (`DT-21`): la sirve la aplicación con caché larga.
    """
    _comprobar_que_gestiona_el_catalogo(actor, "Cargar la imagen de un producto")

    contenido, nombre = procesar_imagen(archivo)

    anterior = producto.imagen_clave
    clave = storages["publico"].save(nombre, contenido)

    producto.imagen_clave = clave
    producto.save(update_fields=["imagen_clave"])

    transaction.on_commit(lambda: _borrar_del_almacenamiento(anterior))
    return producto


@transaction.atomic
def quitar_imagen(*, actor, producto):
    """Deja el producto sin imagen. Se sigue vendiendo igual (`HU-59`)."""
    _comprobar_que_gestiona_el_catalogo(actor, "Quitar la imagen de un producto")

    anterior = producto.imagen_clave
    if not anterior:
        return producto

    producto.imagen_clave = ""
    producto.save(update_fields=["imagen_clave"])

    transaction.on_commit(lambda: _borrar_del_almacenamiento(anterior))
    return producto


@transaction.atomic
def retirar_del_catalogo(*, actor, producto):
    """Deja de ofrecerse, sin borrarse.

    Borrar un producto que ya se vendió dejaría el historial de inventario sin
    a qué referirse, y las existencias dejarían de explicarse (`INV-3`). La
    línea de venta copia sus datos (`DT-8`), pero el movimiento de inventario lo
    referencia.
    """
    _comprobar_que_gestiona_el_catalogo(actor, "Retirar productos del catálogo")

    if producto.activo:
        producto.activo = False
        producto.save(update_fields=["activo"])
    return producto


@transaction.atomic
def devolver_al_catalogo(*, actor, producto):
    _comprobar_que_gestiona_el_catalogo(actor, "Devolver productos al catálogo")

    if not producto.activo:
        producto.activo = True
        producto.save(update_fields=["activo"])
    return producto


__all__ = [
    "crear_alergeno",
    "crear_categoria",
    "crear_producto",
    "declarar_alergenos",
    "devolver_al_catalogo",
    "editar_producto",
    "guardar_imagen",
    "quitar_imagen",
    "retirar_del_catalogo",
]
