"""Vistas del control parental (`TT-96`, `HU-09`).

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
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from billetera.selectors import consumo_del_dia
from personas.models import Estudiante
from personas.selectors import estudiante_a_cargo
from restricciones.selectors import limite_diario_de
from restricciones.services import MONTO_MAXIMO, fijar_limite_diario

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
