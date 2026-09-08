"""Vistas de la billetera (`TT-61`, `HU-06`).

Solo HTTP: parsear la petición, delegar en un servicio o un selector, y
renderizar. **Cero lógica de negocio** (`DT-15`): quién puede recargar y por
cuánto lo decide `billetera.services`, y esta vista solo traduce su respuesta.

Una vista HTMX devuelve **un fragmento, nunca una página** (`DT-16`). Esta no lo
es: recargar cambia el estado del sistema y termina en una redirección, para que
recargar el navegador no vuelva a asentar el movimiento.
"""

from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from billetera.selectors import historial_de, saldo_de
from billetera.services import MONTO_MAXIMO, recargar
from personas.models import Estudiante
from personas.selectors import estudiante_a_cargo
from personas.services import EstudianteNoOperativo


# Los atajos de importe de la pantalla de recarga. **Son una comodidad de la
# interfaz, no una regla**: el rango que de verdad manda es el del servicio
# (`0,01` … `MONTO_MAXIMO`), y estos cuatro solo evitan teclear las cifras más
# habituales. Si el máximo cambia, esto no hay que tocarlo mientras siga
# quedando por debajo.
MONTOS_SUGERIDOS = (Decimal("10000"), Decimal("25000"), Decimal("50000"), Decimal("100000"))

# Cuántas recargas anteriores se enseñan al lado del formulario. Son las últimas,
# no el extracto: la pregunta que responden es «¿no acabo de recargar?», no
# auditar la cuenta — para eso está el historial completo del panel.
RECARGAS_VISIBLES = 6


class RecargaForm(forms.Form):
    """El monto, y nada más.

    **No hay campos de pago**: ni tarjeta, ni cuenta, ni medio. El flujo es
    simulado (`ALC-OUT-01`, `ALC-OUT-02`), y pedir datos que no se van a usar
    —menos aún de pago— sería recoger información sin ninguna necesidad.

    Los límites se repiten aquí para que el formulario los enseñe antes de
    enviar, pero **la regla vive en el servicio**: este formulario es una
    comodidad, no la validación (`DT-15`).
    """

    monto = forms.DecimalField(
        label="Cuánto quieres recargar",
        min_value=Decimal("0.01"),
        max_value=MONTO_MAXIMO,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal"}),
    )


@login_required
@require_http_methods(["GET", "POST"])
def recarga(request, estudiante_id):
    """Pantalla de recarga de un estudiante a cargo (`TT-61`, `HU-06`).

    **La autorización la hace el selector**, no un `if` de esta vista: un
    estudiante que no está a cargo de quien pregunta es un 404, igual que uno que
    no existe. Los dos casos se responden igual a propósito — distinguirlos
    confirmaría a un desconocido que ese estudiante existe.

    El servicio vuelve a comprobar quién recarga, y esa repetición no sobra: la
    vista corta antes para no enseñar un formulario que va a fallar, y el
    servicio corta siempre, entre por donde entre (`DT-15`).
    """
    try:
        estudiante = estudiante_a_cargo(usuario=request.user, estudiante_id=estudiante_id)
    except Estudiante.DoesNotExist:
        raise Http404("Ese estudiante no está a tu cargo.") from None

    formulario = RecargaForm(request.POST or None)

    if request.method == "POST" and formulario.is_valid():
        try:
            movimiento = recargar(
                actor=request.user,
                estudiante=estudiante,
                monto=formulario.cleaned_data["monto"],
            )
        except (ValidationError, EstudianteNoOperativo) as error:
            # `EstudianteNoOperativo` es `INVD-2`: de baja o desactivado no se
            # recarga. No es un fallo del monto, así que no se cuelga del campo.
            formulario.add_error(None, str(error))
        else:
            messages.success(
                request,
                f"Recarga de {movimiento.monto:.2f} asentada en la billetera de "
                f"{estudiante.nombre}.",
            )
            return redirect("mis-estudiantes")

    # El saldo y las últimas recargas son lectura del mismo historial que ya
    # sostiene `HU-07`: no hay consulta nueva ni columna nueva, es la suma de los
    # movimientos (`INV-2`) y sus últimos asientos. Se traen aquí para que la
    # pantalla pueda decir de cuánto se parte y qué se recargó antes, que es lo
    # que evita la recarga repetida por no acordarse de la anterior.
    return render(
        request,
        "billetera/recarga.html",
        {
            "estudiante": estudiante,
            "form": formulario,
            "saldo": saldo_de(estudiante),
            "recargas": historial_de(estudiante, limite=RECARGAS_VISIBLES),
            "montos_sugeridos": MONTOS_SUGERIDOS,
        },
    )
