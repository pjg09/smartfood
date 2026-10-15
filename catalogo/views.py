"""Vistas de productos, categorías y alérgenos.

Solo HTTP: parsear la petición, delegar en un servicio o un selector, y
renderizar. **Cero lógica de negocio** (`DT-15`).

Una vista HTMX devuelve **un fragmento, nunca una página** (`DT-16`). Si un
endpoint devuelve a veces una cosa y a veces la otra, se parte en dos.
"""

import re

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.storage import storages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods, require_safe

from catalogo.models import Alergeno, Categoria
from catalogo.selectors import alergenos_del_catalogo, categorias_del_catalogo
from catalogo.services import (
    crear_alergeno,
    crear_categoria,
    editar_alergeno,
    editar_categoria,
    eliminar_categoria,
)
from config.imagenes import TIPO_SALIDA

# La forma exacta de las claves que produce la canalización: 32 dígitos
# hexadecimales y la extensión de salida (`config/imagenes.py`).
#
# **No es una comprobación de estilo: es lo que impide salir del prefijo.** El
# almacenamiento antepone `publico/` a lo que se le pida, así que una clave como
# `../privado/loquesea.webp` alcanzaría la fotografía de un estudiante. Se acepta
# lo que la canalización genera y nada más.
CLAVE_VALIDA = re.compile(r"^[0-9a-f]{32}\.webp$")


@require_safe
@cache_control(public=True, max_age=settings.CACHE_IMAGEN_PRODUCTO, immutable=True)
def imagen_del_producto(request, clave):
    """Sirve una imagen del catálogo (`TT-53`, `HU-59`, `DT-21`).

    **La sirve la aplicación y no una URL firmada.** La imagen de un producto no
    es sensible, y firmar cincuenta URL para pintar la lista del punto de venta
    es coste sin contrapartida (`DT-18`). Además una firma caduca, y el punto de
    venta tendría que volver a pedir el catálogo entero cada pocos minutos solo
    para renovar enlaces.

    **Sin sesión, a propósito.** «Público» aquí significa *no sensible*
    (`DT-21`): es la fotografía de una empanada. Exigir sesión no protegería
    nada y rompería la caché del navegador, que es justo lo que `INT-2` necesita
    para no descargar el catálogo en cada pintado. Lo que sí es cierto es que la
    clave no se puede adivinar: la genera el servidor y son 128 bits.

    **Inmutable.** La ruta lleva la clave, no el identificador del producto: al
    reemplazar la imagen cambia la clave y con ella la URL, así que no hay nada
    que invalidar y el navegador puede quedársela un mes.
    """
    if not CLAVE_VALIDA.match(clave):
        raise Http404("Esa no es una clave de imagen.")

    almacenamiento = storages["publico"]
    if not almacenamiento.exists(clave):
        raise Http404("No hay ninguna imagen con esa clave.")

    return FileResponse(almacenamiento.open(clave), content_type=TIPO_SALIDA)


# ──────────────────────────────────────────────────────────────────────────────
# LAS CATEGORÍAS (`DEC-25`, `DT-51`)
#
# Una pantalla propia, como `/inventario/`, y por lo mismo: sus modales
# necesitan el sistema visual entero. Ninguna vista escribe: crear, editar y
# eliminar son de `catalogo.services`. Cada escritura responde con la misma
# modal y `HX-Trigger: categorias-cambiado`, y el tablero de detrás se vuelve a
# pedir (`DT-16`, `DT-40`).
# ──────────────────────────────────────────────────────────────────────────────


class CategoriaForm(forms.Form):
    """Nombre y descripción de una categoría. **El nombre es único sin
    distinguir mayúsculas**: «bebidas» y «Bebidas» partirían las alertas de
    `HU-31` en dos grupos que son el mismo."""

    nombre = forms.CharField(label="Nombre", max_length=80)
    descripcion = forms.CharField(label="Descripción", max_length=200, required=False)

    def __init__(self, *args, categoria=None, **kwargs):
        self.categoria = categoria
        super().__init__(*args, **kwargs)

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        repetida = Categoria.objects.filter(nombre__iexact=nombre)
        if self.categoria is not None:
            repetida = repetida.exclude(pk=self.categoria.pk)
        if repetida.exists():
            raise ValidationError("Ya hay una categoría con ese nombre.")
        return nombre


def _avisar_a_las_categorias(respuesta):
    respuesta["HX-Trigger"] = "categorias-cambiado"
    return respuesta


def _contexto_del_tablero(request):
    categorias = categorias_del_catalogo(actor=request.user)
    return {
        "categorias": categorias,
        "en_uso": sum(1 for c in categorias if c.cuantos),
    }


def _categoria(request, categoria_id):
    """La categoría, **después** de comprobar el rol: un `404` no puede
    contarle a otro rol qué existe."""
    categorias_del_catalogo(actor=request.user)
    return get_object_or_404(Categoria, pk=categoria_id)


@login_required
@require_http_methods(["GET"])
def categorias(request):
    """La pantalla: dos cifras y una fila por categoría."""
    return render(request, "catalogo/categorias.html", _contexto_del_tablero(request))


@login_required
@require_http_methods(["GET"])
def tablero_de_categorias(request):
    """Las cifras y la lista, como fragmento: se repintan tras cada escritura."""
    return render(request, "catalogo/partials/tablero-de-categorias.html", _contexto_del_tablero(request))


@login_required
@require_http_methods(["GET", "POST"])
def categoria_nueva(request):
    """Alta en la modal. Al crear vuelve vacía, con lo hecho arriba, lista para
    otra; un error vuelve junto al campo, en `200`."""
    categorias_del_catalogo(actor=request.user)

    if request.method == "GET":
        return render(request, "catalogo/partials/ficha-de-categoria.html", {"formulario": CategoriaForm()})

    formulario = CategoriaForm(request.POST)
    if not formulario.is_valid():
        return render(request, "catalogo/partials/ficha-de-categoria.html", {"formulario": formulario})

    creada = crear_categoria(actor=request.user, **formulario.cleaned_data)
    return _avisar_a_las_categorias(render(
        request, "catalogo/partials/ficha-de-categoria.html",
        {"formulario": CategoriaForm(), "creada": creada},
    ))


@login_required
@require_http_methods(["GET", "POST"])
def edicion_de_categoria(request, categoria_id):
    """Renombrar o describir una categoría, en la misma modal que el alta."""
    categoria = _categoria(request, categoria_id)

    def ficha(formulario, **extra):
        return render(request, "catalogo/partials/ficha-de-categoria.html", {
            "formulario": formulario, "categoria": categoria, **extra,
        })

    if request.method == "GET":
        return ficha(CategoriaForm(
            initial={"nombre": categoria.nombre, "descripcion": categoria.descripcion},
            categoria=categoria,
        ))

    formulario = CategoriaForm(request.POST, categoria=categoria)
    if not formulario.is_valid():
        return ficha(formulario)

    editar_categoria(actor=request.user, categoria=categoria, **formulario.cleaned_data)
    return _avisar_a_las_categorias(ficha(
        CategoriaForm(
            initial={"nombre": categoria.nombre, "descripcion": categoria.descripcion},
            categoria=categoria,
        ),
        guardada=True,
    ))


@login_required
@require_http_methods(["GET", "POST"])
def eliminacion_de_categoria(request, categoria_id):
    """Confirmar y eliminar una categoría **vacía** (`DT-51`).

    Con productos, la modal dice cuántos y no ofrece el botón: un botón que la
    base va a rechazar no se pinta (`[S4]` del sistema visual). Si alguien lo
    fuerza, el servicio lo rechaza y la modal vuelve con su motivo.
    """
    categoria = _categoria(request, categoria_id)
    cuantos = categoria.productos.count()

    if request.method == "GET":
        return render(request, "catalogo/partials/eliminacion-de-categoria.html", {
            "categoria": categoria, "cuantos": cuantos,
        })

    nombre = categoria.nombre
    try:
        eliminar_categoria(actor=request.user, categoria=categoria)
    except ValidationError as error:
        return render(request, "catalogo/partials/eliminacion-de-categoria.html", {
            "categoria": categoria, "cuantos": cuantos, "error": " ".join(error.messages),
        })
    return _avisar_a_las_categorias(render(
        request, "catalogo/partials/eliminacion-de-categoria.html",
        {"eliminada": nombre},
    ))


# ──────────────────────────────────────────────────────────────────────────────
# LOS ALÉRGENOS (`DEC-26`, `DT-52`)
#
# La composición de las categorías, con una diferencia que es toda la decisión:
# **no hay eliminar**. Ni ruta, ni modal, ni servicio. Crear y renombrar son de
# `catalogo.services`; cada escritura responde con la misma modal y
# `HX-Trigger: alergenos-cambiado`, y el tablero de detrás se vuelve a pedir.
# ──────────────────────────────────────────────────────────────────────────────


class AlergenoForm(forms.Form):
    """El nombre de un alérgeno. **Único sin distinguir mayúsculas**: lo impone
    la base (`DT-52`); aquí se comprueba antes para dar el mensaje junto al
    campo en vez de un `500`."""

    nombre = forms.CharField(label="Nombre", max_length=80)

    def __init__(self, *args, alergeno=None, **kwargs):
        self.alergeno = alergeno
        super().__init__(*args, **kwargs)

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        repetido = Alergeno.objects.filter(nombre__iexact=nombre)
        if self.alergeno is not None:
            repetido = repetido.exclude(pk=self.alergeno.pk)
        if repetido.exists():
            raise ValidationError("Ya hay un alérgeno con ese nombre.")
        return nombre


def _avisar_a_los_alergenos(respuesta):
    respuesta["HX-Trigger"] = "alergenos-cambiado"
    return respuesta


def _contexto_de_los_alergenos(request):
    alergenos = alergenos_del_catalogo(actor=request.user)
    return {
        "alergenos": alergenos,
        "declarados": sum(1 for a in alergenos if a.cuantos_productos),
    }


def _alergeno(request, alergeno_id):
    """El alérgeno con sus dos recuentos, **después** de comprobar el rol: un
    `404` no puede contarle a otro rol qué existe."""
    for alergeno in alergenos_del_catalogo(actor=request.user):
        if alergeno.pk == alergeno_id:
            return alergeno
    raise Http404("No hay ningún alérgeno con ese identificador.")


@login_required
@require_http_methods(["GET"])
def alergenos(request):
    """La pantalla: dos cifras y una fila por alérgeno."""
    return render(request, "catalogo/alergenos.html", _contexto_de_los_alergenos(request))


@login_required
@require_http_methods(["GET"])
def tablero_de_alergenos(request):
    """Las cifras y la lista, como fragmento: se repintan tras cada escritura."""
    return render(
        request, "catalogo/partials/tablero-de-alergenos.html", _contexto_de_los_alergenos(request)
    )


@login_required
@require_http_methods(["GET", "POST"])
def alergeno_nuevo(request):
    """Alta en la modal. Al crear vuelve vacía, con lo hecho arriba, lista para
    otro; un error vuelve junto al campo, en `200`."""
    alergenos_del_catalogo(actor=request.user)

    if request.method == "GET":
        return render(request, "catalogo/partials/ficha-de-alergeno.html", {"formulario": AlergenoForm()})

    formulario = AlergenoForm(request.POST)
    if not formulario.is_valid():
        return render(request, "catalogo/partials/ficha-de-alergeno.html", {"formulario": formulario})

    creado = crear_alergeno(actor=request.user, **formulario.cleaned_data)
    return _avisar_a_los_alergenos(render(
        request, "catalogo/partials/ficha-de-alergeno.html",
        {"formulario": AlergenoForm(), "creado": creado},
    ))


@login_required
@require_http_methods(["GET", "POST"])
def edicion_de_alergeno(request, alergeno_id):
    """Renombrar un alérgeno, en la misma modal que el alta, con el aviso de a
    cuántos productos y estudiantes alcanza el nombre nuevo (`DEC-26`)."""
    alergeno = _alergeno(request, alergeno_id)

    def ficha(formulario, **extra):
        return render(request, "catalogo/partials/ficha-de-alergeno.html", {
            "formulario": formulario, "alergeno": alergeno, **extra,
        })

    if request.method == "GET":
        return ficha(AlergenoForm(initial={"nombre": alergeno.nombre}, alergeno=alergeno))

    formulario = AlergenoForm(request.POST, alergeno=alergeno)
    if not formulario.is_valid():
        return ficha(formulario)

    editar_alergeno(actor=request.user, alergeno=alergeno, **formulario.cleaned_data)
    return _avisar_a_los_alergenos(ficha(
        AlergenoForm(initial={"nombre": alergeno.nombre}, alergeno=alergeno),
        guardado=True,
    ))
