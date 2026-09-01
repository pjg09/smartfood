"""Siembra los datos de arranque del prototipo (`TT-08`).

Vive en `personas` porque la institución es lo primero que siembra, pero es
**transversal**: siembra cuentas, personal, acudientes con sus estudiantes y el
catálogo entero.

**Todo lo que produce es ficticio** (`ALC-OUT-07`, `DT-14`, `DoD-6`). Los
nombres están compuestos, los documentos son inventados y los correos van a
`example.com`, que la RFC 2606 reserva. Las imágenes **se dibujan aquí mismo**
—no se descarga ninguna—, que es como se sostiene `INVD-6`: ninguna fotografía
del prototipo corresponde a una persona real.

**Es idempotente.** Se ejecuta al levantar el entorno, después de un despliegue
y mientras se desarrolla: no puede duplicar filas ni reenviar invitaciones en
cada pasada.

Todo lo que siembra es ficticio (`ALC-OUT-07`, `DoD-6`).
"""

import secrets
import string

from django.core.management.base import BaseCommand

from catalogo.models import Alergeno, Categoria, Producto
from catalogo.services import crear_producto, guardar_imagen
from config.avatares import avatar, bodegon
from config.datos_ficticios import ALERGENOS, CATEGORIAS, PERSONAL, familias, productos
from cuentas.models import Rol, Usuario
from cuentas.services import (
    crear_cuenta,
    crear_cuenta_de_personal,
    sincronizar_grupos_y_permisos,
)
from personas.models import Acudiente, Estudiante
from personas.services import (
    crear_estudiante,
    dar_de_alta_la_institucion,
    guardar_fotografia,
)

# Centinela: distingue «no se pidió contraseña» de «se pidió sin dar valor».
GENERAR = object()


def generar_contrasena(longitud=24):
    """Clave fuerte y aleatoria. No hay ninguna por defecto en el código.

    Una contraseña escrita en el repositorio es una contraseña filtrada: acaba
    en el historial de git para siempre y nadie se acuerda de cambiarla.
    """
    alfabeto = string.ascii_letters + string.digits + "-_"
    return "".join(secrets.choice(alfabeto) for _ in range(longitud))

# La institución de referencia del prototipo. El nombre es inventado y el
# dominio es `example.com`, que la RFC 2606 reserva y nadie puede registrar.
#
# **No vale `example.edu.co` ni ningún otro que suene a reservado**: la RFC
# reserva `example.com`, `.net` y `.org` y los TLD `.test` e `.invalid`, y nada
# más. `example.edu.co` es un subdominio de `edu.co` que alguien puede
# registrar, y un correo dirigido ahí puede llegarle a un tercero.
INSTITUCION_NOMBRE = "Colegio San Bartolomé de Prueba"
INSTITUCION_EMAIL = "institucion@example.com"


class Command(BaseCommand):
    help = "Siembra la institución de referencia y dispara su invitación (HU-39, TT-10)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email-institucion",
            default=INSTITUCION_EMAIL,
            help=(
                "Correo de la cuenta institucional. Útil para dirigir la invitación "
                "a un buzón real al demostrar HU-39."
            ),
        )
        parser.add_argument(
            "--nombre-institucion",
            default=INSTITUCION_NOMBRE,
            help="Nombre de la institución de referencia.",
        )
        parser.add_argument(
            "--contrasena-de-desarrollo",
            nargs="?",
            const=GENERAR,
            default=None,
            metavar="CLAVE",
            help=(
                "DEC-10 y DEC-11. Fija una contraseña conocida en las cuentas que "
                "siembra y NO envía invitación. Sin valor, genera una fuerte y la "
                "imprime una sola vez. Es la opción con nombre que DEC-11 exige: "
                "por el camino normal, sin ella, cada cuenta se activa por "
                "invitación (HU-39, HU-41, HU-03)."
            ),
        )
        parser.add_argument(
            "--estudiantes",
            type=int,
            default=0,
            metavar="N",
            help=(
                "Cuántos estudiantes ficticios sembrar, con sus acudientes, el "
                "personal de la cafetería y el catálogo. Sin esto solo se siembra "
                "la institución."
            ),
        )
        parser.add_argument(
            "--sin-imagenes",
            action="store_true",
            help=(
                "No genera avatares ni imágenes de producto. Más rápido cuando "
                "solo hacen falta los datos."
            ),
        )

    def handle(self, *args, **opciones):
        contrasena = opciones["contrasena_de_desarrollo"]

        # Una cadena vacía significa que se pidió contraseña pero la variable de
        # entorno que la traía no estaba definida. Se genera una en vez de caer
        # al camino por defecto: ese enviaría una invitación a una dirección que
        # no es de nadie, y cada rebote degrada la reputación del remitente
        # hasta que el proveedor suspende la cuenta (DEC-9). Falla del lado
        # seguro: sin correo, y con la clave impresa en el registro.
        if contrasena is GENERAR or contrasena == "":
            contrasena = generar_contrasena()

        # La matriz [S11] primero: la cuenta institucional se crea ya dentro de
        # su grupo, y no como un usuario suelto al que hay que arreglar después.
        sincronizar_grupos_y_permisos()

        institucion, creada = dar_de_alta_la_institucion(
            nombre=opciones["nombre_institucion"],
            email=opciones["email_institucion"],
            contrasena_de_desarrollo=contrasena,
        )

        if creada:
            self.stdout.write(self.style.SUCCESS(f"Institución «{institucion.nombre}» creada."))
        else:
            self.stdout.write(f"La institución «{institucion.nombre}» ya existía.")

        if contrasena:
            self.stdout.write(f"  cuenta     : {institucion.usuario.email}")
            self.stdout.write(self.style.WARNING(f"  contraseña : {contrasena}"))
            self.stdout.write(
                "  Se muestra UNA vez y no se guarda en claro en ninguna parte. "
                "Anótala donde corresponda (docs/desarrollo.md)."
            )
            self.stdout.write("  No se envió invitación por correo (DEC-10).")
        elif creada:
            self.stdout.write(f"  Invitación enviada a {institucion.usuario.email}.")
        else:
            self.stdout.write("  No se reenvía la invitación.")

        if not opciones["estudiantes"]:
            return

        con_imagenes = not opciones["sin_imagenes"]
        personal = self._sembrar_personal(institucion.usuario, contrasena)
        self._sembrar_familias(
            institucion.usuario, opciones["estudiantes"], contrasena, con_imagenes
        )
        self._sembrar_catalogo(personal[Rol.ADMINISTRADOR], con_imagenes)

    # --- Las tres partes, todas idempotentes -------------------------------
    #
    # El seed se ejecuta al levantar el entorno, después de cada despliegue y
    # mientras se desarrolla. Ninguna puede duplicar filas, reenviar
    # invitaciones ni volver a subir una imagen que ya está.

    def _sembrar_personal(self, institucion, contrasena):
        """Cajero y administrador de la cafetería (`HU-40`, `DEC-2`).

        Hace falta antes que el catálogo: `crear_producto` exige un actor con
        rol de administración, que es donde `[S11]` pone el catálogo.

        **Sin invitación por correo.** Las direcciones son ficticias y no
        corresponden a ningún buzón; cada rebote degrada la reputación del
        remitente hasta que el proveedor suspende la cuenta (`DEC-9`). Por eso
        el seed asigna contraseña, que es lo que `DEC-11` prevé.
        """
        cuentas, creadas = {}, 0
        for email, rol, nombre in PERSONAL:
            existente = Usuario.objects.filter(email=email).first()
            if existente is not None:
                cuentas[rol] = existente
                continue

            cuentas[rol] = crear_cuenta_de_personal(
                actor=institucion,
                email=email,
                rol=rol,
                nombre=nombre,
                contrasena_de_desarrollo=contrasena,
            )
            creadas += 1

        self.stdout.write(
            self.style.SUCCESS(f"Personal de la cafetería: {creadas} cuenta(s) nueva(s).")
            if creadas
            else "El personal de la cafetería ya estaba sembrado."
        )
        return cuentas

    def _sembrar_familias(self, institucion, cuantos, contrasena, con_imagenes):
        """Acudientes con sus estudiantes, y el avatar de cada estudiante.

        Uno de cada cuatro acudientes queda con **dos** estudiantes a su cargo:
        es el caso de `HU-04`, y sin él la pantalla del acudiente nunca enseña
        su selector.
        """
        acudientes, estudiantes, avatares = 0, 0, 0

        for familia in familias(cuantos):
            acudiente = Acudiente.objects.filter(documento=familia["documento"]).first()
            if acudiente is None:
                cuenta = crear_cuenta(
                    email=familia["correo"],
                    rol=Rol.ACUDIENTE,
                    nombre=familia["nombre"],
                    contrasena_de_desarrollo=contrasena,
                    # `DEC-9`: no se entrega correo a direcciones ficticias.
                    enviar_invitacion=False,
                )
                acudiente = Acudiente.objects.create(
                    usuario=cuenta,
                    nombre=familia["nombre"],
                    documento=familia["documento"],
                )
                acudientes += 1

            for datos in familia["estudiantes"]:
                estudiante = Estudiante.objects.filter(
                    documento=datos["documento"]
                ).first()
                if estudiante is None:
                    estudiante = crear_estudiante(
                        actor=institucion,
                        nombre=datos["nombre"],
                        documento=datos["documento"],
                        acudiente=acudiente,
                    )
                    estudiantes += 1

                # Solo si le falta: volver a subirla en cada pasada dejaría un
                # objeto huérfano por despliegue.
                if con_imagenes and not estudiante.tiene_foto:
                    guardar_fotografia(
                        actor=institucion,
                        estudiante=estudiante,
                        archivo=avatar(estudiante.documento),
                    )
                    avatares += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Familias: {acudientes} acudiente(s) y {estudiantes} estudiante(s) "
                f"nuevo(s), {avatares} avatar(es) generado(s)."
            )
        )
        if avatares:
            self.stdout.write(
                "  Los avatares se dibujan aquí: ninguna fotografía del prototipo "
                "corresponde a una persona real (INVD-6)."
            )

    def _sembrar_catalogo(self, administracion, con_imagenes):
        """Categorías, alérgenos y productos con su información nutricional.

        Los alérgenos entran **por la relación** (`DT-7`, `INV-5`): declarar que
        un producto lleva lactosa no bloquea nada, y el bloqueo lo configurará
        el acudiente sobre el alérgeno (`HU-11`).
        """
        for nombre in CATEGORIAS:
            Categoria.objects.get_or_create(nombre=nombre)
        for nombre in ALERGENOS:
            Alergeno.objects.get_or_create(nombre=nombre)

        creados, imagenes = 0, 0
        for nombre, categoria, precio, alergenos, nutricional in productos():
            producto = Producto.objects.filter(nombre=nombre).first()
            if producto is None:
                producto = crear_producto(
                    actor=administracion,
                    nombre=nombre,
                    precio=precio,
                    categoria=Categoria.objects.get(nombre=categoria),
                    alergenos=[Alergeno.objects.get(nombre=a) for a in alergenos],
                    **nutricional,
                )
                creados += 1

            if con_imagenes and not producto.tiene_imagen:
                guardar_imagen(
                    actor=administracion, producto=producto, archivo=bodegon(nombre)
                )
                imagenes += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Catálogo: {Categoria.objects.count()} categoría(s), "
                f"{Alergeno.objects.count()} alérgeno(s), {creados} producto(s) "
                f"nuevo(s), {imagenes} imagen(es) generada(s)."
            )
        )
