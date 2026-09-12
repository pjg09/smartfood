"""Rutas del proyecto.

**No hay rutas de registro y no las habrá** (`INV-6`, `INVD-1`, `DT-10`): las
cuentas se crean por seed o por invitación. Si alguna vez aparece aquí una ruta
de alta pública, es un error, no una funcionalidad.
"""

from django.contrib import admin
from django.contrib.auth import views as vistas_de_auth
from django.urls import path, reverse_lazy
from django.views.generic import TemplateView

from billetera.views import recarga
from catalogo.views import imagen_del_producto
from config.salud import salud
from personas.views import (
    carga_de_estudiantes,
    estudiante_seleccionado,
    panel_del_acudiente,
    tarjeta_del_estudiante,
)
from ventas.views import carrito, cobrar, identificacion, punto_de_venta

# `INT-3` no lleva plantillas propias: lo cubre el admin generado (`DT-2`). Lo
# único que necesita es hablar en español y no llamarse «Django» (TT-05).
admin.site.site_header = "SmartFood · Administración"
admin.site.site_title = "SmartFood"
admin.site.index_title = "Gestión de la cafetería"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("salud/", salud, name="salud"),
    # Acceso al sistema (`TT-56`, `DEC-12`). **No es un camino de alta**: aquí
    # solo entra quien ya tiene cuenta y ya definió su contraseña con la
    # invitación. `INV-6` e `INVD-1` no se tocan.
    #
    # Existe porque `/admin/login/` exige `is_staff` y el acudiente no lo es
    # (`INT-1` no es el admin): sin esta ruta, `USR-2` no tiene por dónde entrar.
    # La ruta es `/login/` y el nombre sigue siendo `acceso`, y esa asimetría es
    # deliberada: la URL la lee quien usa el sistema y es la convención que
    # espera de un producto web; el nombre lo lee quien programa, y ahí manda la
    # convención en español del repositorio. Cambiar el nombre habría tocado
    # `LOGIN_URL`, doce `{% url %}` y once pruebas sin que nadie viera nada
    # distinto en pantalla.
    path(
        "login/",
        vistas_de_auth.LoginView.as_view(
            template_name="cuentas/acceso.html",
            redirect_authenticated_user=True,
        ),
        name="acceso",
    ),
    path("salir/", vistas_de_auth.LogoutView.as_view(), name="salir"),
    # Definición de contraseña a partir de la invitación (`TT-11`). La misma
    # pantalla sirve a los cuatro roles: el mecanismo de acceso es único
    # (`DEC-3`), y la reutilizan `HU-39`, `HU-41` y `HU-03`.
    #
    # Se apoya en las vistas de Django en lugar de escribir autenticación
    # propia, que `CLAUDE.md` descarta explícitamente. El token que usan ya se
    # invalida al cambiar la contraseña y caduca solo; `TT-18` lo revisa.
    path(
        "invitacion/<uidb64>/<token>/",
        vistas_de_auth.PasswordResetConfirmView.as_view(
            template_name="cuentas/definir-contrasena.html",
            success_url=reverse_lazy("contrasena-definida"),
        ),
        name="definir-contrasena",
    ),
    path(
        "invitacion/lista/",
        TemplateView.as_view(template_name="cuentas/contrasena-definida.html"),
        name="contrasena-definida",
    ),
    # Carga masiva de estudiantes y acudientes (`TT-24`, `HU-01`).
    path("carga/", carga_de_estudiantes, name="carga-de-estudiantes"),
    # Interfaz del acudiente (`TT-29`, `HU-04`, `INT-1`). La primera devuelve la
    # página; la segunda, el fragmento HTMX del estudiante elegido. Son dos
    # rutas y no una con dos comportamientos (`DT-16`).
    path("mis-estudiantes/", panel_del_acudiente, name="mis-estudiantes"),
    path(
        "mis-estudiantes/<uuid:estudiante_id>/",
        estudiante_seleccionado,
        name="estudiante-seleccionado",
    ),
    # Recarga de la billetera (`TT-61`, `HU-06`). Cuelga de la ruta del
    # estudiante porque **la billetera es individual por estudiante**, no de la
    # cuenta del acudiente: recargar sin decir a quién no significa nada.
    path(
        "mis-estudiantes/<uuid:estudiante_id>/recargar/",
        recarga,
        name="recarga",
    ),
    # Vista imprimible de la tarjeta (`TT-37`, `HU-45`). Es de la institución
    # (`USR-5`), no del acudiente: quien produce la tarjeta es el colegio.
    path(
        "estudiantes/<uuid:estudiante_id>/tarjeta/",
        tarjeta_del_estudiante,
        name="tarjeta-del-estudiante",
    ),
    # Imagen del producto (`TT-53`, `HU-59`, `DT-21`). La sirve la aplicación
    # con caché larga en lugar de firmar una URL: no es sensible, y una firma
    # caduca. La ruta lleva la clave, que cambia al reemplazar la imagen, así
    # que la respuesta puede cachearse como inmutable.
    path(
        "catalogo/imagenes/<str:clave>",
        imagen_del_producto,
        name="imagen-del-producto",
    ),
    # Punto de venta (`TT-57`, `TT-58`, `INT-2`). **Solo el cajero**: `[S11]` no
    # concede registrar ventas a ningún otro rol, y quien lo intente recibe un
    # `403` aunque llegue escribiendo la URL (`DT-11`).
    path("punto-de-venta/", punto_de_venta, name="punto-de-venta"),
    # El fragmento HTMX que devuelve al estudiante escaneado (`TT-71`, `HU-15`).
    # Es una ruta aparte y no la misma vista mirando una cabecera: **una vista
    # HTMX devuelve un fragmento, nunca una página** (`DT-16`).
    path(
        "punto-de-venta/identificacion/",
        identificacion,
        name="identificacion-en-el-punto-de-venta",
    ),
    # El carrito y el cobro (`TT-81`, `HU-21`). **Las dos son `POST`**: cambian
    # el estado de la sesión y de la base, y un `GET` que cambia algo es una URL
    # que el navegador puede reproducir solo.
    #
    # Son dos rutas y no una con un parámetro de acción: montar el carrito no
    # escribe en ninguna tabla, y cobrar abre la transacción que sostiene `INV-1`,
    # `INV-2` e `INV-3` a la vez. Juntarlas sería dejar la operación más delicada
    # del sistema detrás de un `if` sobre un campo del formulario.
    path("punto-de-venta/carrito/", carrito, name="carrito-del-punto-de-venta"),
    path("punto-de-venta/cobrar/", cobrar, name="cobrar"),
    path("", TemplateView.as_view(template_name="inicio.html"), name="inicio"),
]
