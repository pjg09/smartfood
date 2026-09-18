"""Vistas de institución educativa, estudiantes y acudientes.

Solo HTTP: parsear la petición, delegar en un servicio o un selector, y
renderizar. **Cero lógica de negocio** (`DT-15`).

Una vista HTMX devuelve **un fragmento, nunca una página** (`DT-16`).
"""

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from billetera.selectors import historial_de, saldo_de
from cuentas.models import Rol
from personas.carga import ArchivoIlegible
from personas.models import Estudiante, Institucion
from personas.selectors import (
    cuentas_sin_activar,
    estudiante_a_cargo,
    estudiante_para_la_institucion,
    estudiantes_a_cargo,
    padron,
)
from personas.services import (
    cargar_estudiantes_y_acudientes,
    desactivar,
    reactivar,
)
from personas.tarjeta import ancho_mm, svg_del_codigo
from personas.validacion import ArchivoInvalido
from restricciones.selectors import (
    alergenos_bloqueados_de,
    limite_diario_de,
    productos_bloqueados_de,
)
from ventas.selectors import pedidos_pendientes_de


class ArchivoDeCargaForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo de estudiantes",
        help_text="CSV en UTF-8, con las cinco columnas del formato acordado.",
    )


@login_required
@require_http_methods(["GET", "POST"])
def carga_de_estudiantes(request):
    """Pantalla de carga masiva (`TT-24`, `HU-01`).

    La vista **no decide quién puede cargar**: se lo pregunta al servicio, que
    es donde vive la regla (`DT-15`). Aquí solo se corta antes para no enseñar
    un formulario que va a fallar.
    """
    if request.user.rol != Rol.INSTITUCION:
        raise PermissionDenied(
            "Cargar estudiantes es función exclusiva de la institución educativa."
        )

    contexto = {
        "form": ArchivoDeCargaForm(),
        "resultado": None,
        "error": None,
        "errores": None,
    }

    if request.method == "POST":
        form = ArchivoDeCargaForm(request.POST, request.FILES)
        contexto["form"] = form

        if form.is_valid():
            try:
                contexto["resultado"] = cargar_estudiantes_y_acudientes(
                    actor=request.user,
                    archivo=form.cleaned_data["archivo"],
                )
            except ArchivoIlegible as error:
                # El archivo que ni siquiera se puede leer como CSV.
                contexto["error"] = str(error)
            except ArchivoInvalido as error:
                # `HU-02`, tercer criterio: el reporte identifica los errores
                # encontrados. Van todos, no el primero.
                contexto["errores"] = error.errores

    return render(request, "personas/carga-de-estudiantes.html", contexto)


# Cuántos movimientos se enseñan bajo el saldo (`TT-64`, `HU-07`).
#
# Cinco, y no «el historial»: lo que la historia pide es saber **si hace falta
# recargar**, y para eso basta con ver lo último que pasó. Un extracto completo
# en la misma pantalla empuja el resto del panel fuera de la vista en un
# teléfono, que es desde donde entra el acudiente (`INT-1`).
ULTIMOS_MOVIMIENTOS = 5


def _contexto_del_estudiante(estudiante):
    """Lo que la ficha de un estudiante necesita, venga de la página o del fragmento.

    **La misma función para los dos caminos**, a propósito: la página y el
    fragmento HTMX pintan la misma plantilla (`DT-16`), y armar el contexto dos
    veces es cómo acaban enseñando cosas distintas.

    El saldo lo calcula `billetera`, sumando el historial (`INV-2`). Aquí es
    donde se juntan los dos dominios, y es el sitio correcto: **una vista
    compone**. La dependencia entre modelos sigue yendo en un solo sentido —
    `billetera` conoce a `personas` y no al revés.

    `TT-96` añade el límite diario por la misma puerta y con el mismo argumento:
    `restricciones` conoce a `personas`, y es la vista la que junta las dos
    lecturas para pintar la ficha. Puede ser `None`, y ese caso no es un hueco:
    significa que el acudiente no fijó cupo, que es distinto de un cupo de cero
    (`restricciones.models.LimiteDiario`).

    `TT-99` añade el recuento de productos bloqueados y `TT-102` el de alérgenos.
    Los dos son `count()` y no la lista: la tarjeta solo dice cuántos hay, y
    traerlos todos para contarlos sería pedirle a la base un trabajo que la
    pantalla no usa.

    **Son dos cifras y no una suma**, a propósito: una lista de productos y una
    condición no se agregan. Sumarlas daría un número que no significa nada y
    escondería justo la distinción que `HU-10` y `HU-11` existen para marcar.
    """
    return {
        "seleccionado": estudiante,
        "saldo": saldo_de(estudiante) if estudiante is not None else None,
        "limite": limite_diario_de(estudiante) if estudiante is not None else None,
        "productos_bloqueados": (
            productos_bloqueados_de(estudiante).count() if estudiante is not None else 0
        ),
        "alergenos_bloqueados": (
            alergenos_bloqueados_de(estudiante).count() if estudiante is not None else 0
        ),
        "movimientos": (
            historial_de(estudiante, limite=ULTIMOS_MOVIMIENTOS)
            if estudiante is not None
            else []
        ),
        # `TT-145`, `HU-23`. Un `count()` y no la lista, por lo mismo que los dos
        # recuentos de arriba: la tarjeta solo dice cuántas hay pendientes.
        "pedidos_pendientes": (
            pedidos_pendientes_de(estudiante).count() if estudiante is not None else 0
        ),
    }


@login_required
@require_http_methods(["GET"])
def panel_del_acudiente(request):
    """La página del acudiente con sus estudiantes a cargo (`TT-29`, `HU-04`).

    `INT-1`, y es como entra `USR-2`. Entrar es de `TT-56`: sin pantalla de
    acceso propia esta vista no tenía forma de alcanzarse, porque el formulario
    del admin exige `is_staff` y el acudiente no lo es (`DEC-12`).

    Quién puede verla lo decide el selector, que es donde vive la regla
    (`DT-15`): aquí solo se renderiza lo que devuelve.
    """
    estudiantes = estudiantes_a_cargo(usuario=request.user)

    # El primero queda seleccionado: con un solo hijo, el selector sobra y la
    # pantalla ya muestra lo que el acudiente venía a ver.
    seleccionado = estudiantes.first()

    return render(
        request,
        "personas/mis-estudiantes.html",
        {"estudiantes": estudiantes, **_contexto_del_estudiante(seleccionado)},
    )


@login_required
@require_http_methods(["GET"])
def estudiante_seleccionado(request, estudiante_id):
    """El fragmento del estudiante elegido en el selector (`TT-29`, `HU-04`).

    **Devuelve un fragmento, nunca una página** (`DT-16`): por eso es una ruta
    aparte de `panel_del_acudiente` y no la misma vista decidiendo según la
    cabecera de HTMX.

    Un estudiante que no está a cargo de quien pregunta es un 404, igual que uno
    que no existe: el selector no los distingue a propósito.
    """
    try:
        estudiante = estudiante_a_cargo(
            usuario=request.user, estudiante_id=estudiante_id
        )
    except Estudiante.DoesNotExist:
        raise Http404("Ese estudiante no está a tu cargo.") from None

    return render(
        request,
        "partials/estudiante-seleccionado.html",
        _contexto_del_estudiante(estudiante),
    )


@login_required
@require_http_methods(["POST"])
def desactivacion_por_el_acudiente(request, estudiante_id):
    """El acudiente bloquea la tarjeta de su estudiante (`TT-122`, `HU-48`).

    **La otra vía de `DEC-5`**, y no es la misma pantalla con otro rol: el
    colegio desactiva desde el padrón cuando el niño avisa allí (`HU-47`); aquí
    el acudiente lo hace sin depender del horario de secretaría. Las dos llaman
    al mismo servicio, que es donde vive la regla (`DT-15`).

    Un estudiante que no está a su cargo es un `404`, igual que uno que no
    existe: `estudiante_a_cargo` no los distingue a propósito, porque un `403`
    le confirmaría a un desconocido que ese estudiante existe.

    **Devuelve el fragmento del estudiante, no una página** (`DT-16`): es el
    mismo que pinta el selector, así que el saldo, el cupo y las restricciones
    se repintan con el estado nuevo y la tarjeta deja de ofrecer recargar.

    **No hay vista para lo contrario.** Reactivar es exclusivo de la institución
    (`INVD-3`, `HU-49`) y esa ausencia es el segundo criterio de `HU-48`: no es
    que el botón esté escondido, es que la ruta no existe.
    """
    try:
        estudiante = estudiante_a_cargo(
            usuario=request.user, estudiante_id=estudiante_id
        )
    except Estudiante.DoesNotExist:
        raise Http404("Ese estudiante no está a tu cargo.") from None

    try:
        desactivar(actor=request.user, estudiante=estudiante)
    except ValidationError as error:
        # A un estudiante de baja no se le desactiva: no es un fallo del
        # sistema, es una transición que no existe. Vuelve en `200` con su
        # motivo dentro del fragmento, porque htmx no intercambia lo que llega
        # en `4xx` y la pantalla se quedaría igual y sin explicación.
        return render(
            request,
            "partials/estudiante-seleccionado.html",
            {
                **_contexto_del_estudiante(estudiante),
                "error": "; ".join(error.messages),
            },
        )

    estudiante.refresh_from_db()
    return render(
        request,
        "partials/estudiante-seleccionado.html",
        {**_contexto_del_estudiante(estudiante), "recien_desactivado": True},
    )


@login_required
@require_http_methods(["GET"])
def tarjeta_del_estudiante(request, estudiante_id):
    """Vista imprimible de la tarjeta de un estudiante (`TT-37`, `HU-45`).

    Habilita `ENT-02`: lo que sale de aquí se imprime y se pasa por un lector en
    el Sprint 2. No es una pantalla de consulta con un adorno, es el insumo
    físico de la siguiente demostración.

    **El código de barras se genera en cada petición, a partir del campo del
    estudiante.** Nada se almacena ni se cachea, y eso es lo que sostiene el
    segundo criterio de `HU-45`: se muestra el código **vigente**. Una imagen
    guardada seguiría enseñando un código correcto después de que `HU-46` lo
    reasignara, y esa tarjeta impresa ya no abre ningún saldo (`INVD-4`).

    **Una tarjeta por página, a propósito.** `ALC-OUT-04` excluye la producción
    masiva; `ALC-OUT-05` pide «un número limitado de tarjetas» para la prueba de
    concepto. Se imprimen de una en una, que para un conjunto reducido es
    suficiente y deja la exclusión donde está.
    """
    try:
        estudiante = estudiante_para_la_institucion(
            actor=request.user, estudiante_id=estudiante_id
        )
    except Estudiante.DoesNotExist:
        raise Http404("No hay ningún estudiante con ese identificador.") from None

    return render(
        request,
        "personas/tarjeta.html",
        {
            "estudiante": estudiante,
            "institucion": Institucion.objects.first(),
            "codigo_de_barras": svg_del_codigo(estudiante.codigo_tarjeta),
            "ancho_impreso_mm": ancho_mm(estudiante.codigo_tarjeta),
        },
    )


def _contexto_del_padron(actor, *, busqueda="", incluir_retirados=False):
    """Lo que la tabla del padrón necesita, venga de mirar o de desactivar.

    **La misma función para los dos caminos**, por lo mismo que
    `_contexto_del_estudiante` en el panel del acudiente: la página, el
    fragmento del buscador y la respuesta de `TT-120` pintan la misma tabla, y
    armar el contexto tres veces es cómo acaban enseñando cosas distintas.
    """
    estudiantes = list(
        padron(actor=actor, busqueda=busqueda, incluir_retirados=incluir_retirados)
    )

    return {
        "estudiantes": estudiantes,
        "busqueda": busqueda,
        "incluir_retirados": incluir_retirados,
        "sin_activar": cuentas_sin_activar(estudiantes),
        # El total sin filtrar, para poder decir «8 de 20» y que quien busca sepa
        # que hay más. Con la búsqueda vacía las dos cifras coinciden y la frase
        # sigue leyéndose bien.
        "total": padron(actor=actor, incluir_retirados=incluir_retirados).count(),
    }


@login_required
@require_http_methods(["POST"])
def desactivacion_de_estudiante(request, estudiante_id):
    """Desactiva a un estudiante desde el padrón (`TT-120`, `HU-47`, `DT-29`).

    ── ESTA ES LA PRIMERA ESCRITURA DEL PADRÓN, Y ESTÁ DECLARADA ───────────
    `DT-27` decidió que el padrón **solo lee** y que escribir era del admin.
    `DT-29` corrige esa parte para esta acción y solo para ella: `HU-47` existe
    por la inmediatez —una tarjeta perdida en mitad de la jornada— y el padrón
    es la pantalla que secretaría tiene abierta. Mandarla al admin añade tres
    pantallas justo en el escenario que motiva la historia.

    Lo que **no** cambia es dónde vive la regla: esta vista no escribe, llama a
    `personas.services.desactivar`, que comprueba el rol (`DT-15`, `DT-11`). El
    resto del padrón sigue leyendo, y el alta, la edición, la baja y la
    reasignación siguen en el admin.
    ─────────────────────────────────────────────────────────────────────────

    **Devuelve el fragmento de la tabla, no una página** (`DT-16`), y con los
    mismos filtros que tenía puestos: quien desactiva estaba buscando a alguien,
    y devolverle el padrón entero le borra la búsqueda. Por eso llegan en el
    cuerpo del `POST`.

    ── EL RECHAZO VUELVE EN `200`, CON SU MOTIVO DENTRO DEL FRAGMENTO ──────
    Es el mismo precedente que el cobro (`ventas.views.cobrar`), y no es una
    comodidad: htmx **no intercambia** lo que llega en `4xx` —lo dice su
    configuración de `responseHandling`—, así que un `400` dejaría la pantalla
    exactamente igual y a secretaría sin saber por qué no pasó nada. El estado
    que devuelve la petición y lo que hay que enseñarle a quien pulsó son dos
    preguntas distintas.

    Un estudiante que no existe sí es un `404`: ahí no hay nada que pintar.
    ─────────────────────────────────────────────────────────────────────────
    """
    try:
        estudiante = Estudiante.objects.get(pk=estudiante_id)
    except Estudiante.DoesNotExist:
        raise Http404("No hay ningún estudiante con ese identificador.") from None

    return _transicion_desde_el_padron(
        request, estudiante, desactivar, "desactivado"
    )


@login_required
@require_http_methods(["POST"])
def reactivacion_de_estudiante(request, estudiante_id):
    """Devuelve a un estudiante desactivado a la normalidad (`TT-123`, `HU-49`).

    **Es la pareja de la desactivación y vive en la misma pantalla** (`DT-30`),
    por un motivo que no es la simetría: `INVD-3` reserva el desbloqueo a la
    institución porque pasa por una **verificación presencial**, y quien la hace
    es secretaría con la familia delante, mirando el padrón.

    `INVD-3` no se defiende aquí sino en el servicio, que exige el rol: esta
    vista solo delega (`DT-15`).
    """
    try:
        estudiante = Estudiante.objects.get(pk=estudiante_id)
    except Estudiante.DoesNotExist:
        raise Http404("No hay ningún estudiante con ese identificador.") from None

    return _transicion_desde_el_padron(request, estudiante, reactivar, "reactivado")


def _transicion_desde_el_padron(request, estudiante, servicio, resultado):
    """Lo común a desactivar y reactivar desde el padrón (`DT-29`, `DT-30`).

    Las dos hacen exactamente lo mismo alrededor del servicio: leer los filtros
    que había puestos, delegar, y devolver la tabla con el estado nuevo. Estaba
    escrito una vez cuando solo existía la desactivación; con la segunda, o se
    comparte o el día que cambie una de las dos la otra se queda vieja.

    **El rechazo vuelve en `200`, con su motivo dentro del fragmento.** htmx no
    intercambia lo que llega en `4xx` —lo dice su configuración de
    `responseHandling`—, así que un `400` dejaría la pantalla igual y a
    secretaría sin saber por qué no pasó nada.
    """
    filtros = {
        "busqueda": request.POST.get("busqueda", ""),
        "incluir_retirados": request.POST.get("retirados") == "1",
    }

    # ── SE LEE EL PADRÓN ANTES DE ESCRIBIR, Y EL ORDEN ES LA REGLA ──────────
    # `_contexto_del_padron` llama a `padron()`, que **exige el rol institución**
    # (`DT-11`): es lo que convierte esta ruta en `403` para todos los demás.
    # Llamar antes al servicio dejaría pasar al acudiente sobre su propio
    # estudiante —`desactivar` sí se lo permite desde `HU-48`—, y el `403`
    # llegaría con el cambio ya escrito: una respuesta que dice «no puedes»
    # sobre algo que sí pasó. Se descubrió al compartir esta función entre las
    # dos transiciones, y hay prueba que lo vigila.
    # ───────────────────────────────────────────────────────────────────────
    _contexto_del_padron(request.user, **filtros)

    try:
        servicio(actor=request.user, estudiante=estudiante)
    except ValidationError as error:
        contexto = _contexto_del_padron(request.user, **filtros)
        contexto["error"] = "; ".join(error.messages)
        return render(request, "personas/partials/padron-tabla.html", contexto)

    # El contexto se rearma **después** de escribir: la tabla que se devuelve
    # tiene que traer el estado nuevo.
    contexto = _contexto_del_padron(request.user, **filtros)
    contexto[resultado] = estudiante
    return render(request, "personas/partials/padron-tabla.html", contexto)


@login_required
@require_http_methods(["GET"])
def padron_de_estudiantes(request):
    """El padrón de la institución (`DT-27`, `HU-44`).

    **Quién puede verlo lo decide el selector**, que es donde vive la regla
    (`DT-15`): aquí no se comprueba el rol dos veces. El `PermissionDenied` que
    lanza sale como `403`, también para quien escriba la URL a mano (`DT-11`).

    ── DEVUELVE PÁGINA O FRAGMENTO, Y SON DOS COSAS DISTINTAS ──────────────
    `DT-16` prohíbe que **un mismo endpoint** devuelva a veces una página y a
    veces un fragmento. Aquí no pasa eso: son **dos rutas** —`/padron/` y
    `/padron/tabla/`— apuntando a la misma función porque lo que cambia es el
    envoltorio, no lo que se responde. La lista es la misma consulta y el mismo
    contexto; repetirla en dos funciones sería garantizar que un día divergen.

    Lo dice `request.resolver_match.url_name`, no una cabecera de HTMX: una
    cabecera la pone el cliente y se puede falsear; la ruta la resuelve Django.
    ─────────────────────────────────────────────────────────────────────────

    El buscador **no es un formulario que se envíe**: cada tecla pide la tabla y
    reemplaza solo esa zona. Sin eso, secretaría teclea, pulsa Enter, espera a
    que repinte la página entera y pierde el foco del campo en cada intento.
    """
    contexto = _contexto_del_padron(
        request.user,
        busqueda=request.GET.get("busqueda", ""),
        # La casilla solo llega cuando está marcada, que es como el navegador
        # manda los checkbox. Su ausencia significa «no», no «no lo sé».
        incluir_retirados=request.GET.get("retirados") == "1",
    )

    if request.resolver_match.url_name == "padron-tabla":
        return render(request, "personas/partials/padron-tabla.html", contexto)

    return render(request, "personas/padron.html", contexto)
