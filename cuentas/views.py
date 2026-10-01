"""Vistas de usuarios, roles, invitaciones y sesión.

Solo HTTP: parsear la petición, delegar en un servicio o un selector, y
renderizar. **Cero lógica de negocio** (`DT-15`).

Una vista HTMX devuelve **un fragmento, nunca una página** (`DT-16`). Si un
endpoint devuelve a veces una cosa y a veces la otra, se parte en dos.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.shortcuts import redirect, render

from cuentas.models import Rol
from cuentas.services import enviar_recuperacion


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
