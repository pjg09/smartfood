"""Vistas del control parental (`TT-96`, `TT-99`, `TT-102`, `HU-09` … `HU-11`).

Solo HTTP: parsear la petición, delegar en un servicio o un selector, y
renderizar. **Cero lógica de negocio** (`DT-15`): quién puede fijar el límite y
entre qué cifras lo decide `restricciones.services`, y esta vista solo traduce su
respuesta.

Una vista HTMX devuelve **un fragmento, nunca una página** (`DT-16`). Esta no lo
es: fijar el límite cambia el estado del sistema y termina en una redirección,
para que recargar el navegador no vuelva a escribirlo.
"""

from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from billetera.selectors import consumo_del_dia
from catalogo.models import Alergeno, Producto
from catalogo.selectors import productos_en_el_catalogo
from personas.models import Estudiante
from personas.selectors import estudiante_a_cargo
from restricciones.selectors import (
    identificadores_de_alergenos_bloqueados,
    identificadores_de_productos_bloqueados,
    limite_diario_de,
    productos_cubiertos_por_alergeno,
)
from restricciones.services import (
    MONTO_MAXIMO,
    bloquear_alergeno,
    bloquear_producto,
    desbloquear_alergeno,
    desbloquear_producto,
    fijar_limite_diario,
)

# Los atajos de importe de la pantalla del límite. **Son una comodidad de la
# interfaz, no una regla**: el rango que de verdad manda es el del servicio
# (`0,01` … `MONTO_MAXIMO`), y estos cuatro solo evitan teclear las cifras más
# habituales.
#
# Son más bajos que los de la recarga (`TT-61`) a propósito: allí se carga el
# saldo de una semana o un mes, y aquí se fija lo que puede gastarse **en un
# día**. Ofrecer los mismos cuatro importes sugeriría que un cupo diario de
# cien mil pesos es lo corriente.
MONTOS_SUGERIDOS = (Decimal("3000"), Decimal("5000"), Decimal("8000"), Decimal("12000"))


class LimiteDiarioForm(forms.Form):
    """El monto, y nada más.

    Los límites se repiten aquí para que el formulario los enseñe antes de
    enviar, pero **la regla vive en el servicio**: este formulario es una
    comodidad, no la validación (`DT-15`).
    """

    monto = forms.DecimalField(
        label="Cuánto puede gastar al día",
        min_value=Decimal("0.01"),
        max_value=MONTO_MAXIMO,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal"}),
    )


@login_required
@require_http_methods(["GET", "POST"])
def limite_diario(request, estudiante_id):
    """Pantalla del límite diario de un estudiante a cargo (`TT-96`, `HU-09`).

    **La autorización la hace el selector**, no un `if` de esta vista: un
    estudiante que no está a cargo de quien pregunta es un 404, igual que uno que
    no existe. Los dos casos se responden igual a propósito — distinguirlos
    confirmaría a un desconocido que ese estudiante existe.

    El servicio vuelve a comprobar quién escribe, y esa repetición no sobra: la
    vista corta antes para no enseñar un formulario que va a fallar, y el
    servicio corta siempre, entre por donde entre (`DT-15`). Es literalmente
    `INV-4`: la regla no puede depender de la puerta.
    """
    try:
        estudiante = estudiante_a_cargo(usuario=request.user, estudiante_id=estudiante_id)
    except Estudiante.DoesNotExist:
        raise Http404("Ese estudiante no está a tu cargo.") from None

    vigente = limite_diario_de(estudiante)

    if request.method == "POST":
        formulario = LimiteDiarioForm(request.POST)
    else:
        # Con límite ya fijado, el campo llega con la cifra vigente: modificarlo
        # es corregir un número que existe, no escribirlo de cero. Sin límite
        # llega vacío — **no con un cero**, que se leería como un cupo de cero
        # (ver `restricciones.models.LimiteDiario`).
        formulario = LimiteDiarioForm(
            initial={"monto": vigente.monto} if vigente is not None else None
        )

    if request.method == "POST" and formulario.is_valid():
        try:
            limite = fijar_limite_diario(
                actor=request.user,
                estudiante=estudiante,
                monto=formulario.cleaned_data["monto"],
            )
        except ValidationError as error:
            # No siempre es culpa de lo que se escribió en el campo, así que el
            # error no se cuelga de él.
            formulario.add_error(None, str(error))
        else:
            messages.success(
                request,
                f"{estudiante.nombre} puede gastar hasta {limite.monto:.2f} al día.",
            )
            return redirect("mis-estudiantes")

    return render(
        request,
        "restricciones/limite-diario.html",
        {
            "estudiante": estudiante,
            "form": formulario,
            "limite": vigente,
            # Lo que lleva gastado hoy, para que la cifra que se elija no salga
            # de la nada. Es lectura del mismo libro que el saldo (`INV-2`,
            # `DT-4`): no hay contador que poner a cero cada medianoche.
            #
            # **No es la aplicación del límite.** Comparar esta cifra con el
            # cupo dentro de la venta es `TT-116` (`PR-09`), y hasta entonces
            # esto es una referencia para decidir, no una regla en vigor. La
            # plantilla lo dice con todas las letras.
            "consumo_de_hoy": consumo_del_dia(estudiante),
            "montos_sugeridos": MONTOS_SUGERIDOS,
        },
    )


@login_required
@require_http_methods(["GET"])
def productos_bloqueados(request, estudiante_id):
    """Pantalla de selección de productos a bloquear (`TT-99`, `HU-10`).

    **Dos rutas a la misma vista**, como el padrón (`DT-27`): la página y su
    lista. No es un endpoint que devuelva a veces una cosa y a veces otra
    (`DT-16`) — es la misma respuesta con y sin envoltorio, y la vista lo
    distingue por el nombre de la ruta, que resuelve Django y no puede falsear
    el cliente.

    La autorización la hace el selector: un estudiante que no está a cargo de
    quien pregunta es un 404, igual que uno que no existe.
    """
    try:
        estudiante = estudiante_a_cargo(usuario=request.user, estudiante_id=estudiante_id)
    except Estudiante.DoesNotExist:
        raise Http404("Ese estudiante no está a tu cargo.") from None

    contexto = _contexto_de_productos(estudiante, request.GET.get("busqueda", ""))

    if request.resolver_match.url_name == "productos-bloqueados-lista":
        return render(request, "restricciones/partials/lista-de-productos.html", contexto)

    return render(request, "restricciones/productos-bloqueados.html", contexto)


@login_required
@require_http_methods(["POST"])
def bloqueo_de_producto(request, estudiante_id):
    """Bloquea o desbloquea un producto y devuelve la lista repintada (`TT-99`).

    **Es `POST` y devuelve un fragmento** (`DT-16`): cambia el estado del
    sistema, así que un `GET` sería una URL que el navegador puede reproducir
    solo.

    Devuelve **la lista entera**, no el renglón que se tocó. Con el renglón
    bastaría para el interruptor, pero la cabecera lleva el recuento de
    bloqueados y quedaría diciendo una cifra vieja: dos intercambios
    coordinados (`hx-swap-oob`) por cada toque, para dieciséis productos, es más
    fragilidad que ahorro — y `hx-swap-oob` falla en silencio si el elemento no
    queda en el primer nivel de la respuesta.

    **La vista no decide quién puede**: llama al servicio, que corta entre por
    donde entre (`DT-15`, `INV-4`). Aquí solo se traduce la respuesta.
    """
    try:
        estudiante = estudiante_a_cargo(usuario=request.user, estudiante_id=estudiante_id)
    except Estudiante.DoesNotExist:
        raise Http404("Ese estudiante no está a tu cargo.") from None

    try:
        producto = Producto.objects.get(pk=request.POST.get("producto"))
    except (Producto.DoesNotExist, ValidationError, ValueError):
        # Un identificador que no es de ningún producto —o que ni siquiera es un
        # UUID— es una petición inválida, no un error del acudiente.
        raise Http404("Ese producto no existe.") from None

    if request.POST.get("accion") == "desbloquear":
        desbloquear_producto(actor=request.user, estudiante=estudiante, producto=producto)
    else:
        bloquear_producto(actor=request.user, estudiante=estudiante, producto=producto)

    return render(
        request,
        "restricciones/partials/lista-de-productos.html",
        _contexto_de_productos(estudiante, request.POST.get("busqueda", "")),
    )


def _contexto_de_productos(estudiante, busqueda):
    """Lo que la lista necesita, venga de la página, del buscador o de un toque.

    **La misma función para los tres caminos**, a propósito: los tres pintan la
    misma plantilla, y armar el contexto tres veces es cómo acaban enseñando
    cosas distintas.

    Se ofrecen **solo los productos en el catálogo** (`activo=True`): ofrecer
    bloquear algo que ya no se vende es ruido. El servicio sí admite bloquear un
    retirado —ver `bloquear_producto`—, que es lo que mantiene la restricción si
    el producto vuelve.
    """
    busqueda = (busqueda or "").strip()

    productos = productos_en_el_catalogo()
    if busqueda:
        productos = productos.filter(nombre__icontains=busqueda)

    bloqueados = identificadores_de_productos_bloqueados(estudiante)

    return {
        "estudiante": estudiante,
        "busqueda": busqueda,
        # Se anota en cada producto si está bloqueado, en lugar de dejar que la
        # plantilla lo pregunte: una plantilla no debería poder disparar una
        # consulta por fila.
        "productos": [
            {"producto": p, "bloqueado": p.id in bloqueados} for p in productos
        ],
        "total_bloqueados": len(bloqueados),
    }


@login_required
@require_http_methods(["GET"])
def alergenos_bloqueados(request, estudiante_id):
    """Pantalla de selección de alérgenos a bloquear (`TT-102`, `HU-11`).

    **Sin buscador, y no por descuido.** La barra de filtros de `TT-99` existe
    porque el catálogo tiene decenas de productos; los alérgenos son ocho y caben
    de un vistazo. Una fila de filtros sobre una lista que no se filtra es la
    composición vacía.
    """
    try:
        estudiante = estudiante_a_cargo(usuario=request.user, estudiante_id=estudiante_id)
    except Estudiante.DoesNotExist:
        raise Http404("Ese estudiante no está a tu cargo.") from None

    return render(
        request,
        "restricciones/alergenos-bloqueados.html",
        _contexto_de_alergenos(estudiante),
    )


@login_required
@require_http_methods(["POST"])
def bloqueo_de_alergeno(request, estudiante_id):
    """Bloquea o desbloquea un alérgeno y devuelve la lista repintada (`TT-102`).

    Como su pareja de `TT-99`: `POST` porque escribe, y devuelve la lista entera
    para que el recuento de la cabecera no quede diciendo una cifra vieja
    (`DT-16`).
    """
    try:
        estudiante = estudiante_a_cargo(usuario=request.user, estudiante_id=estudiante_id)
    except Estudiante.DoesNotExist:
        raise Http404("Ese estudiante no está a tu cargo.") from None

    try:
        alergeno = Alergeno.objects.get(pk=request.POST.get("alergeno"))
    except (Alergeno.DoesNotExist, ValidationError, ValueError):
        raise Http404("Ese alérgeno no existe.") from None

    if request.POST.get("accion") == "desbloquear":
        desbloquear_alergeno(actor=request.user, estudiante=estudiante, alergeno=alergeno)
    else:
        bloquear_alergeno(actor=request.user, estudiante=estudiante, alergeno=alergeno)

    return render(
        request,
        "restricciones/partials/lista-de-alergenos.html",
        _contexto_de_alergenos(estudiante),
    )


def _contexto_de_alergenos(estudiante):
    """Lo que la lista necesita, venga de la página o de un toque.

    Cada alérgeno llega con **cuántos productos lo declaran hoy**, anotado en una
    sola consulta. Esa cifra es informativa y la pantalla lo dice con todas las
    letras: **hoy**. Lo que el bloqueo cubre no es esa lista, es la condición
    (`INV-5`), y lo que entre mañana queda dentro sin que nadie haga nada.

    `productos_cubiertos_por_alergeno` se cuenta aparte porque no es la suma de
    las cifras de arriba: un producto que declare dos alérgenos bloqueados se
    contaría dos veces.
    """
    bloqueados = identificadores_de_alergenos_bloqueados(estudiante)

    alergenos = Alergeno.objects.annotate(
        productos_que_lo_declaran=Count("declaraciones", distinct=True)
    ).order_by("nombre")

    return {
        "estudiante": estudiante,
        "alergenos": [
            {"alergeno": a, "bloqueado": a.id in bloqueados} for a in alergenos
        ],
        "total_bloqueados": len(bloqueados),
        "productos_cubiertos": productos_cubiertos_por_alergeno(estudiante).count(),
    }
