"""Vistas de usuarios, roles, invitaciones y sesión.

Solo HTTP: parsear la petición, delegar en un servicio o un selector, y
renderizar. **Cero lógica de negocio** (`DT-15`).

Una vista HTMX devuelve **un fragmento, nunca una página** (`DT-16`). Si un
endpoint devuelve a veces una cosa y a veces la otra, se parte en dos.
"""

from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from cuentas.models import Rol, Usuario
from cuentas.selectors import personal_de_la_cafeteria
from cuentas.services import (
    ROLES_DE_PERSONAL,
    crear_cuenta_de_personal,
    desactivar_cuenta,
    enviar_recuperacion,
    reactivar_cuenta,
    reenviar_invitacion_de_personal,
)


class RecuperacionDeContrasenaForm(PasswordResetForm):
    """Pide el enlace para elegir una contraseña nueva (`HU-62`, `DEC-19`).

    **De Django se queda con la regla de a quién se envía**, y es la que
    `DEC-19` pide: `get_users` busca el correo sin distinguir mayúsculas y
    descarta las cuentas desactivadas (`HU-42`) y las que no tienen contraseña
    utilizable —las que todavía no usaron su invitación—. Si no encuentra a
    nadie, no hace nada y no lo dice: la vista responde lo mismo exista o no la
    cuenta.

    **Lo único que cambia es cómo se envía.** El `send_mail` de Django manda
    el correo en el acto y con sus plantillas en inglés; este delega en
    `enviar_recuperacion`, que va por `config/correo.py` como la invitación.
    """

    def send_mail(self, subject_template_name, email_template_name, context,
                  from_email, to_email, html_email_template_name=None):
        enviar_recuperacion(context["user"])

# Dónde trabaja cada rol. Es el reparto de `[S11]` leído como navegación: la
# pantalla que abre quien entra es la de su trabajo, no una portada que le
# obligue a elegir a dónde ir.
PANEL_DEL_ROL = {
    Rol.INSTITUCION: "padron",
    Rol.ADMINISTRADOR: "panel-de-la-cafeteria",
    Rol.CAJERO: "punto-de-venta",
    Rol.ACUDIENTE: "mis-estudiantes",
}


@login_required
def panel(request):
    """Reparte a quien acaba de entrar hacia su propio panel.

    **Es el destino de `LOGIN_REDIRECT_URL`**, y por eso existe como ruta en vez
    de como un `if` dentro de la pantalla de acceso: al reparto se llega también
    desde `/` con sesión abierta y desde cualquier enlace que quiera decir «a lo
    tuyo» sin saber quién mira.

    Un rol que no esté en el mapa no puede quedarse sin destino: el personal con
    acceso a la administración cae en ella, y quien no lo tenga, en la portada.
    """
    destino = PANEL_DEL_ROL.get(request.user.rol)
    if destino is None:
        destino = "admin:index" if request.user.is_staff else "inicio"
    return redirect(destino)


def inicio(request):
    """La portada, **una sola y siempre la misma** (`TT-05`).

    No cambia con la sesión: quien tiene una no la ve, porque se le reparte a su
    panel. Así la portada se puede escribir como lo que es —la cara pública del
    producto— sin media docena de condicionales que solo unos pocos alcanzan.
    """
    if request.user.is_authenticated:
        return redirect("panel")
    return render(request, "inicio.html")


# --- `/usuarios/`: el personal de la cafetería (`DT-45`) ------------------------
#
# Sustituye, para la institución, al listado de `cuentas.usuario` del admin, que
# mezclaba al personal con todos los acudientes y con la propia institución. La
# misma composición que el padrón y los acudientes (`DT-27`, `DEC-17`), y el
# alta en la misma modal. **Las reglas no se mueven**: alta, invitación y acceso
# siguen en `cuentas.services`, y quién llega lo decide el selector.


class AltaDePersonalForm(forms.Form):
    """Lo que la institución decide al dar de alta a alguien (`HU-40`).

    **La contraseña no aparece**: la define el titular con su invitación, y
    nadie más llega a conocerla (`DEC-3`, `HU-41`). El rol, solo entre los dos
    de personal: las cuentas de acudiente nacen de la carga (`HU-01`).
    """

    email = forms.EmailField(label="Correo", max_length=254)
    nombre = forms.CharField(label="Nombre completo", max_length=150)
    rol = forms.ChoiceField(
        label="Rol",
        choices=[(r.value, r.label) for r in Rol if r in ROLES_DE_PERSONAL],
        initial=Rol.CAJERO,
    )

    def clean_email(self):
        """Uno por persona, sin distinguir mayúsculas.

        La base solo impide el duplicado exacto, y `normalize_email` solo pasa a
        minúsculas el dominio: `Ana@` y `ana@` serían dos cuentas de la misma
        persona, con dos invitaciones.
        """
        email = self.cleaned_data["email"]
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya hay una cuenta con ese correo.")
        return email


def _contexto_del_personal(actor, *, busqueda=""):
    """Lo que la tabla necesita, venga de la página, del buscador o de una acción.

    `total` es sin la búsqueda: es el «de N» de «2 de N».
    """
    personal = list(personal_de_la_cafeteria(actor=actor, busqueda=busqueda))
    return {
        "personal": personal,
        "busqueda": busqueda,
        "total": personal_de_la_cafeteria(actor=actor).count(),
        "sin_activar": sum(1 for u in personal if not u.tiene_contrasena_definida),
    }


@login_required
@require_http_methods(["GET"])
def usuarios_del_personal(request):
    """La lista del personal de la cafetería (`DT-45`, `HU-40`, `HU-42`).

    Dos rutas a la misma función —`/usuarios/` y `/usuarios/tabla/`—, como el
    padrón: lo que cambia es el envoltorio, y lo dice la ruta resuelta, no una
    cabecera que el cliente pueda falsear (`DT-16`).
    """
    contexto = _contexto_del_personal(
        request.user, busqueda=request.GET.get("busqueda", "")
    )
    if request.resolver_match.url_name == "usuarios-tabla":
        return render(request, "cuentas/partials/usuarios-tabla.html", contexto)
    return render(request, "cuentas/usuarios.html", contexto)


def _alta(request, formulario=None, **resultado):
    return render(request, "cuentas/partials/alta-de-personal.html", {
        "formulario": formulario or AltaDePersonalForm(),
        **resultado,
    })


@login_required
@require_http_methods(["GET", "POST"])
def alta_de_personal(request):
    """Da de alta a un cajero o a un administrador, en la modal (`HU-40`, `HU-41`).

    `GET` pinta el formulario vacío y `POST` crea; **los dos devuelven el
    formulario** (`DT-16`). Al crear vuelve vacío, con el resultado arriba, y la
    tabla se entera por `HX-Trigger`, como en el alta del padrón (`DT-40`).

    Quién puede se pregunta **antes de pintar nada**: el selector exige el rol.
    Un error de datos vuelve en `200`, porque htmx no intercambia un `4xx`.
    """
    personal_de_la_cafeteria(actor=request.user)

    if request.method == "GET":
        return _alta(request)

    formulario = AltaDePersonalForm(request.POST)
    if not formulario.is_valid():
        return _alta(request, formulario)

    datos = formulario.cleaned_data
    try:
        usuario = crear_cuenta_de_personal(
            actor=request.user,
            email=datos["email"],
            rol=datos["rol"],
            nombre=datos["nombre"],
        )
    except ValueError as error:
        formulario.add_error(None, str(error))
        return _alta(request, formulario)

    respuesta = _alta(request, creada=usuario)
    respuesta["HX-Trigger"] = "personal-cambiado"
    return respuesta


def _accion_sobre_el_personal(request, usuario_id, servicio, resultado):
    """Lo común a desactivar, reactivar y reenviar la invitación (`HU-41`, `HU-42`).

    **Se lee la lista antes de escribir**, como en el padrón: el selector exige
    el rol, y además acota a quién se llega. Un identificador de acudiente o de
    la institución da `404`, no un intento del servicio.

    El rechazo —la institución que intenta desactivarse, una invitación a quien
    ya tiene contraseña— vuelve en `200` con su motivo dentro de la tabla.
    """
    busqueda = request.POST.get("busqueda", "")
    usuario = get_object_or_404(personal_de_la_cafeteria(actor=request.user), pk=usuario_id)

    try:
        servicio(actor=request.user, usuario=usuario)
    except (PermissionDenied, ValueError) as error:
        contexto = _contexto_del_personal(request.user, busqueda=busqueda)
        contexto["error"] = str(error)
        return render(request, "cuentas/partials/usuarios-tabla.html", contexto)

    contexto = _contexto_del_personal(request.user, busqueda=busqueda)
    contexto[resultado] = usuario
    return render(request, "cuentas/partials/usuarios-tabla.html", contexto)


@login_required
@require_http_methods(["POST"])
def desactivacion_de_personal(request, usuario_id):
    """`HU-42`. Revoca el acceso; el historial se conserva."""
    return _accion_sobre_el_personal(request, usuario_id, desactivar_cuenta, "desactivada")


@login_required
@require_http_methods(["POST"])
def reactivacion_de_personal(request, usuario_id):
    """`HU-42`, segundo criterio."""
    return _accion_sobre_el_personal(request, usuario_id, reactivar_cuenta, "reactivada")


@login_required
@require_http_methods(["POST"])
def invitacion_de_personal(request, usuario_id):
    """`HU-41`. Vuelve a mandar la invitación a quien no definió su contraseña."""
    return _accion_sobre_el_personal(
        request, usuario_id, reenviar_invitacion_de_personal, "invitada"
    )
