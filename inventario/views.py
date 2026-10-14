"""`/inventario/`: productos, existencias y su libro, en una sola pantalla.

`DEC-25`, `DT-50`. Sustituye a tres pantallas del admin —productos, ingresos
de mercancía y mermas— que tocaban lo mismo desde tres sitios. **No añade
alcance**: crear y editar productos es `HU-26` y `HU-59`, el ingreso `HU-27`,
la merma `HU-28` y el historial `HU-29`. Lo que cambia es por dónde se llega.

Las reglas siguen donde estaban (`DT-15`): **ninguna vista escribe**. Cada
`POST` llama a un servicio de `catalogo` o de `inventario`, que son los que
exigen el rol, el motivo y el signo. Lo que hay aquí es parsear, delegar y
devolver la misma modal con el resultado.

**Una vista HTMX devuelve un fragmento, nunca una página** (`DT-16`). Cuando
una escritura cambia lo que hay detrás —las cifras, la lista—, la respuesta
lleva `HX-Trigger: inventario-cambiado` y esas zonas se vuelven a pedir
(`DT-40`).
"""

from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from catalogo.models import Alergeno, Categoria, Producto
from catalogo.services import (
    crear_producto,
    devolver_al_catalogo,
    editar_producto,
    guardar_imagen,
    quitar_imagen,
    retirar_del_catalogo,
)
from config.imagenes import ImagenInvalida
from inventario.selectors import (
    UMBRAL_DE_EXISTENCIAS_BAJAS,
    existencias_de,
    historial_del_producto,
    productos_del_inventario,
    tablero_del_inventario,
)
from inventario.services import ingresar_mercancia, registrar_merma

# Los campos nutricionales, en el orden del etiquetado (`TT-44`).
CAMPOS_NUTRICIONALES = (
    "porcion",
    "energia_kcal",
    "proteinas_g",
    "carbohidratos_g",
    "azucares_g",
    "grasas_totales_g",
    "grasas_saturadas_g",
    "sodio_mg",
)


def _gramos(etiqueta):
    """Un campo de gramos como los del modelo: opcional, sin negativos, dos
    decimales. **Vacío no es cero**: es «no declarado» (`TT-44`)."""
    return forms.DecimalField(
        label=etiqueta, required=False, min_value=0, max_digits=6, decimal_places=2
    )


class ProductoForm(forms.Form):
    """Lo que se pide para dar de alta o editar un producto (`HU-26`, `HU-59`).

    **Las reglas que la base ya impone se repiten aquí solo para decirlas
    antes**: nombre único, precio sin negativos, saturadas dentro de las grasas
    totales y azúcares dentro de los carbohidratos. La `CheckConstraint` sigue
    siendo la garantía (`DT-15`); esto es lo que evita que el usuario la
    encuentre como un error 500.

    Los alérgenos son casillas: el producto **declara** lo que contiene, y el
    bloqueo lo configura el acudiente sobre el alérgeno (`INV-5`, `DT-7`).
    """

    nombre = forms.CharField(label="Nombre", max_length=160)
    precio = forms.DecimalField(
        label="Precio", min_value=0, max_digits=10, decimal_places=2
    )
    categoria = forms.ModelChoiceField(
        label="Categoría",
        queryset=Categoria.objects.order_by("nombre"),
        empty_label="Elige una categoría",
    )
    alergenos = forms.ModelMultipleChoiceField(
        label="Alérgenos declarados",
        queryset=Alergeno.objects.order_by("nombre"),
        required=False,
    )
    porcion = forms.CharField(label="Porción", max_length=60, required=False)
    energia_kcal = forms.IntegerField(label="Energía (kcal)", required=False, min_value=0)
    proteinas_g = _gramos("Proteínas (g)")
    carbohidratos_g = _gramos("Carbohidratos (g)")
    azucares_g = _gramos("Azúcares (g)")
    grasas_totales_g = _gramos("Grasas totales (g)")
    grasas_saturadas_g = _gramos("Grasas saturadas (g)")
    sodio_mg = forms.IntegerField(label="Sodio (mg)", required=False, min_value=0)
    imagen = forms.ImageField(label="Imagen", required=False)
    quitar_imagen = forms.BooleanField(label="Quitar la imagen actual", required=False)
    # Solo en la edición: en el alta un producto nace en el catálogo.
    activo = forms.BooleanField(label="En el catálogo", required=False)

    def __init__(self, *args, producto=None, **kwargs):
        self.producto = producto
        super().__init__(*args, **kwargs)

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        repetido = Producto.objects.filter(nombre__iexact=nombre)
        if self.producto is not None:
            repetido = repetido.exclude(pk=self.producto.pk)
        if repetido.exists():
            raise ValidationError("Ya hay un producto con ese nombre.")
        return nombre

    def clean_imagen(self):
        """El tamaño, antes de procesarla: el resto lo mira `procesar_imagen`."""
        imagen = self.cleaned_data.get("imagen")
        if imagen and imagen.size > settings.IMAGEN_TAMANO_MAXIMO_BYTES:
            raise ValidationError(
                f"La imagen pesa más de {settings.IMAGEN_TAMANO_MAXIMO_BYTES // (1024 * 1024)} MB."
            )
        return imagen

    def clean(self):
        datos = super().clean()
        for parte, todo, aviso in (
            ("grasas_saturadas_g", "grasas_totales_g",
             "Las saturadas son parte de las grasas totales: no pueden ser más."),
            ("azucares_g", "carbohidratos_g",
             "Los azúcares son parte de los carbohidratos: no pueden ser más."),
        ):
            if datos.get(parte) is not None and datos.get(todo) is not None:
                if datos[parte] > datos[todo]:
                    self.add_error(parte, aviso)
        return datos

    def alergenos_marcados(self):
        """Los identificadores marcados, como texto: lo enviado si el
        formulario volvió con errores, lo declarado si se acaba de abrir."""
        return {str(valor) for valor in (self["alergenos"].value() or [])}

    @classmethod
    def desde(cls, producto):
        """El formulario de edición, lleno con lo que el producto tiene hoy.

        **Con sus alérgenos**: sin ellos, guardar cualquier otro cambio los
        borraría, porque `declarar_alergenos` reemplaza y no acumula — `INV-5`
        rota en silencio. Hay prueba que lo vigila.
        """
        inicial = {
            "nombre": producto.nombre,
            "precio": _sin_ceros(producto.precio),
            "categoria": producto.categoria_id,
            "alergenos": list(producto.alergenos.values_list("pk", flat=True)),
            "activo": producto.activo,
            **{campo: _sin_ceros(getattr(producto, campo)) for campo in CAMPOS_NUTRICIONALES},
        }
        return cls(initial=inicial, producto=producto)


def _sin_ceros(valor):
    """`Decimal("3450.00")` → `"3450"`; `Decimal("3.20")` → `"3.2"`.

    **Como texto y con punto**, que es lo que el campo acepta de vuelta. Pintado
    como `Decimal`, Django lo localiza —«3450,00»— y guardar la ficha sin tocar
    el precio fallaba: el formulario no entiende la coma. Lo vigila una prueba
    que devuelve la ficha tal como llega.
    """
    if not isinstance(valor, Decimal):
        return valor
    return format(valor.normalize(), "f")


class MovimientoForm(forms.Form):
    """Ingreso o merma de un producto (`HU-27`, `HU-28`).

    **Las dos cantidades se escriben en positivo**, y es el tipo el que decide
    el signo: el ingreso suma y la merma resta. Pedir el signo invita a escribir
    «3» donde iba «-3», y ese error no falla — sumaría existencias que nadie
    ingresó. Por eso el campo no admite más que dígitos.

    **El motivo es obligatorio en los dos.** En la merma lo impone la base
    (`INV-8`); en el ingreso no, pero `HU-29` pide que todo movimiento quede
    asentado con su motivo, y «pedido semanal» cuesta nada de escribir y
    explica el asiento seis meses después.
    """

    tipo = forms.ChoiceField(
        choices=(("ingreso", "Ingreso"), ("merma", "Merma")), initial="ingreso"
    )
    cantidad = forms.IntegerField(label="Unidades", min_value=1)
    motivo = forms.CharField(label="Motivo", max_length=200)


#: Cómo se pinta cada campo nutricional: la forma del número y, si la tiene, el
#: campo que no puede superar. Las dos reglas cruzadas son las dos
#: `CheckConstraint` de `Producto`, dichas antes de guardar.
FORMA_DE_LO_NUTRICIONAL = {
    "porcion": {},
    "energia_kcal": {"numero": "entero"},
    "proteinas_g": {"numero": "decimal"},
    "carbohidratos_g": {"numero": "decimal"},
    "azucares_g": {
        "numero": "decimal",
        "tope": "#id_carbohidratos_g",
        "aviso_mayor": "No pueden pasar de los carbohidratos: son parte de ellos.",
    },
    "grasas_totales_g": {"numero": "decimal"},
    "grasas_saturadas_g": {
        "numero": "decimal",
        "tope": "#id_grasas_totales_g",
        "aviso_mayor": "No pueden pasar de las grasas totales: son parte de ellas.",
    },
    "sodio_mg": {"numero": "entero"},
}


def _contexto_de_la_ficha(formulario, producto=None, **extra):
    return {
        "formulario": formulario,
        "producto": producto,
        "nutricion": [
            {"campo": formulario[nombre], **forma}
            for nombre, forma in FORMA_DE_LO_NUTRICIONAL.items()
        ],
        "tamano_maximo_mb": settings.IMAGEN_TAMANO_MAXIMO_BYTES // (1024 * 1024),
        "lado_maximo": settings.IMAGEN_LADO_MAXIMO,
        **extra,
    }


def _avisar(respuesta):
    """Que las cifras y la lista de detrás se vuelvan a pedir (`DT-40`)."""
    respuesta["HX-Trigger"] = "inventario-cambiado"
    return respuesta


def _filtros(request):
    """Los filtros de la lista, de la URL. **Un precio mal escrito se ignora**,
    no rompe la pantalla: es un filtro, y lo que se ve sin él sigue siendo
    cierto."""

    def precio(clave):
        # El campo es `type="number"`: el navegador manda el punto decimal.
        valor = request.GET.get(clave, "").strip()
        try:
            numero = Decimal(valor) if valor else None
        except ArithmeticError:
            return None
        return numero if numero is not None and numero.is_finite() and numero >= 0 else None

    try:
        categoria = Categoria.objects.filter(pk=request.GET.get("categoria") or None).first()
    except ValidationError:
        # Un identificador mal formado: como un precio mal escrito, se ignora.
        categoria = None

    return {
        "nombre": request.GET.get("nombre", "").strip(),
        "categoria": categoria,
        "precio_minimo": precio("precio_minimo"),
        "precio_maximo": precio("precio_maximo"),
        "retirados": request.GET.get("retirados") == "1",
    }


def _contexto_de_la_lista(request):
    filtros = _filtros(request)
    return {
        "productos": productos_del_inventario(actor=request.user, **filtros),
        "filtros": filtros,
        "umbral": UMBRAL_DE_EXISTENCIAS_BAJAS,
    }


@login_required
@require_http_methods(["GET"])
def inventario(request):
    """La pantalla (`DEC-25`). Cifras, filtros y la lista de productos."""
    contexto = _contexto_de_la_lista(request)
    return render(
        request,
        "inventario/inventario.html",
        {
            **contexto,
            "tablero": tablero_del_inventario(actor=request.user),
            "categorias": Categoria.objects.order_by("nombre"),
        },
    )


@login_required
@require_http_methods(["GET"])
def cifras_del_inventario(request):
    """Las cuatro tarjetas, como fragmento: se repintan tras cada escritura."""
    return render(
        request,
        "inventario/partials/cifras.html",
        {"tablero": tablero_del_inventario(actor=request.user), "umbral": UMBRAL_DE_EXISTENCIAS_BAJAS},
    )


@login_required
@require_http_methods(["GET"])
def lista_del_inventario(request):
    """La lista filtrada, como fragmento: la piden los filtros a cada tecla y
    las escrituras al terminar."""
    return render(request, "inventario/partials/lista.html", _contexto_de_la_lista(request))


def _producto(request, producto_id):
    """El producto, **después** de comprobar que quien pide gestiona el
    inventario: un `404` no puede contarle a otro rol qué existe."""
    tablero_del_inventario(actor=request.user)
    return get_object_or_404(
        Producto.objects.select_related("categoria").prefetch_related("alergenos"),
        pk=producto_id,
    )


def _aplicar_imagen(request, producto, formulario):
    """Guarda o quita la imagen. **Un fallo no deshace el resto**: la imagen no
    es obligatoria (`HU-59`), así que vuelve como error de su campo y el
    producto queda guardado."""
    imagen = formulario.cleaned_data.get("imagen")
    if formulario.cleaned_data.get("quitar_imagen") and not imagen:
        quitar_imagen(actor=request.user, producto=producto)
        return None
    if not imagen:
        return None
    try:
        guardar_imagen(actor=request.user, producto=producto, archivo=imagen)
    except ImagenInvalida as error:
        return " ".join(error.messages)
    return None


@login_required
@require_http_methods(["GET", "POST"])
def producto_nuevo(request):
    """Alta de un producto en la modal (`HU-26`). `GET` y `POST` devuelven la
    ficha; al crear, vuelve como ficha de edición del producto nuevo, con el
    aviso arriba, y las cifras y la lista se enteran."""
    tablero_del_inventario(actor=request.user)

    if request.method == "GET":
        return render(
            request, "inventario/partials/ficha-del-producto.html",
            _contexto_de_la_ficha(ProductoForm(initial={"activo": True})),
        )

    formulario = ProductoForm(request.POST, request.FILES)
    if not formulario.is_valid():
        return render(
            request, "inventario/partials/ficha-del-producto.html",
            _contexto_de_la_ficha(formulario),
        )

    datos = formulario.cleaned_data
    producto = crear_producto(
        actor=request.user,
        nombre=datos["nombre"],
        precio=datos["precio"],
        categoria=datos["categoria"],
        alergenos=datos["alergenos"],
        **{campo: datos[campo] for campo in CAMPOS_NUTRICIONALES},
    )
    error_de_imagen = _aplicar_imagen(request, producto, formulario)
    producto.refresh_from_db()

    return _avisar(render(
        request, "inventario/partials/ficha-del-producto.html",
        _contexto_de_la_ficha(
            ProductoForm.desde(producto), producto, creado=True,
            error_de_imagen=error_de_imagen and f"El producto se creó, pero la imagen no: {error_de_imagen}",
        ),
    ))


@login_required
@require_http_methods(["GET", "POST"])
def edicion_del_producto(request, producto_id):
    """Edición del producto en la misma modal que el alta (`HU-26`, `HU-59`)."""
    producto = _producto(request, producto_id)

    if request.method == "GET":
        return render(
            request, "inventario/partials/ficha-del-producto.html",
            _contexto_de_la_ficha(ProductoForm.desde(producto), producto),
        )

    formulario = ProductoForm(request.POST, request.FILES, producto=producto)
    if not formulario.is_valid():
        return render(
            request, "inventario/partials/ficha-del-producto.html",
            _contexto_de_la_ficha(formulario, producto),
        )

    datos = formulario.cleaned_data
    editar_producto(
        actor=request.user,
        producto=producto,
        nombre=datos["nombre"],
        precio=datos["precio"],
        categoria=datos["categoria"],
        activo=datos["activo"],
        alergenos=datos["alergenos"],
        **{campo: datos[campo] for campo in CAMPOS_NUTRICIONALES},
    )
    error_de_imagen = _aplicar_imagen(request, producto, formulario)
    producto.refresh_from_db()

    return _avisar(render(
        request, "inventario/partials/ficha-del-producto.html",
        _contexto_de_la_ficha(
            ProductoForm.desde(producto), producto, guardado=True,
            error_de_imagen=error_de_imagen and f"Lo demás se guardó, pero la imagen no: {error_de_imagen}",
        ),
    ))


@login_required
@require_http_methods(["GET", "POST"])
def movimiento_del_producto(request, producto_id):
    """Ingreso o merma de un producto (`HU-27`, `HU-28`), en la modal.

    Al registrar vuelve vacía, con lo que se hizo y las existencias que quedan
    arriba, lista para otro. Un rechazo del servicio —quedan menos de las que se
    dan de baja, por ejemplo— vuelve junto al campo, en `200`: HTMX no
    intercambia un `4xx`.
    """
    producto = _producto(request, producto_id)

    def ficha(formulario, **extra):
        return render(request, "inventario/partials/movimiento.html", {
            "producto": producto,
            "formulario": formulario,
            "existencias": existencias_de(producto),
            **extra,
        })

    if request.method == "GET":
        return ficha(MovimientoForm())

    formulario = MovimientoForm(request.POST)
    if not formulario.is_valid():
        return ficha(formulario)

    datos = formulario.cleaned_data
    registrar = ingresar_mercancia if datos["tipo"] == "ingreso" else registrar_merma
    try:
        movimiento = registrar(
            actor=request.user,
            producto=producto,
            cantidad=datos["cantidad"],
            motivo=datos["motivo"],
        )
    except ValidationError as error:
        formulario.add_error("cantidad", error)
        return ficha(formulario)

    return _avisar(ficha(MovimientoForm(initial={"tipo": datos["tipo"]}), registrado=movimiento))


@login_required
@require_http_methods(["GET"])
def historial_del_producto_en_la_modal(request, producto_id):
    """El libro de un producto (`HU-29`): cada línea suma o resta, y el total es
    exactamente sus existencias (`INV-3`, `TST-4`)."""
    producto = _producto(request, producto_id)
    movimientos = historial_del_producto(actor=request.user, producto=producto)
    return render(request, "inventario/partials/historial.html", {
        "producto": producto,
        "movimientos": movimientos,
        # Dos caminos a la misma cifra, a propósito: el `SUM` de la base y la
        # cuenta de las líneas que se enseñan. Si divergen, la modal lo dice.
        "existencias": existencias_de(producto),
        "suma": sum(movimiento.cantidad for movimiento in movimientos),
    })


@login_required
@require_http_methods(["GET", "POST"])
def retiro_del_producto(request, producto_id):
    """Retirar del catálogo, con confirmación (`HU-26`).

    **No borra nada**: el producto deja de venderse y de ofrecerse, y su
    historial, sus ventas y los bloqueos que le pusieron los acudientes se
    conservan. Un producto que ya se vendió no puede desaparecer (`INV-3`).
    """
    producto = _producto(request, producto_id)
    if request.method == "GET":
        return render(request, "inventario/partials/retiro.html", {"producto": producto})

    retirar_del_catalogo(actor=request.user, producto=producto)
    return _avisar(render(
        request, "inventario/partials/retiro.html", {"producto": producto, "retirado": True}
    ))


@login_required
@require_http_methods(["POST"])
def devolucion_al_catalogo(request, producto_id):
    """Devuelve al catálogo un producto retirado. Sin confirmación: se deshace
    retirándolo otra vez, y no mueve dinero ni existencias (`DT-30`).

    **Responde `204` y nada más**: la lista se vuelve a pedir sola con sus
    filtros (`HX-Trigger`). Devolverla desde aquí obligaría a reconstruir unos
    filtros que un `POST` no trae.
    """
    producto = _producto(request, producto_id)
    devolver_al_catalogo(actor=request.user, producto=producto)
    return _avisar(HttpResponse(status=204))
