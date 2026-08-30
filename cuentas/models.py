"""Modelos de usuarios, roles, invitaciones y sesión.

Aquí van la estructura y las invariantes que la base de datos puede imponer:
`CheckConstraint` y `UniqueConstraint`. **Sin lógica de negocio** (`DT-15`): una
invariante escrita como `if` se olvida en el siguiente camino de escritura; una
restricción de la base no.

La clave primaria de cada modelo es UUIDv7 generado en la aplicación (`DT-17`),
salvo el código de tarjeta, que tiene su propia regla (`INV-7`, `DT-9`).
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class Rol(models.TextChoices):
    """Los cuatro roles que inician sesión.

    `USR-1`, el estudiante, **no está aquí**: no inicia sesión (`[S10.1]`). Se
    identifica con el código de su tarjeta en el punto de venta, que es otra
    cosa distinta de una cuenta.
    """

    ACUDIENTE = "acudiente", "Acudiente"          # USR-2
    CAJERO = "cajero", "Cajero"                   # USR-3
    ADMINISTRADOR = "administrador", "Administrador de la cafetería"  # USR-4
    INSTITUCION = "institucion", "Institución educativa"              # USR-5


class UsuarioManager(BaseUserManager):
    """Crea usuarios **sin contraseña utilizable**.

    No es un detalle de implementación: es `INV-6` e `INVD-1`. Ninguna cuenta
    del sistema nace de un autorregistro, y quien crea una cuenta **no llega a
    conocer nunca su clave** (`DEC-3`, `HU-41`). El titular la define después,
    con la invitación que le llega por correo.

    Por eso este manager no acepta un argumento `password`. Si alguien lo
    necesita algún día, tendrá que añadirlo a propósito y justificar por qué.
    """

    use_in_migrations = True

    def crear_usuario(self, email, rol, **extra):
        if not email:
            raise ValueError("Un usuario necesita un correo: es por donde le llega la invitación.")

        usuario = self.model(
            email=self.normalize_email(email),
            rol=rol,
            **extra,
        )
        usuario.set_unusable_password()
        usuario.save(using=self._db)
        return usuario

    # Django llama a este nombre desde algunos caminos internos.
    def create_user(self, email, rol=Rol.ACUDIENTE, **extra):
        return self.crear_usuario(email, rol, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)

    # El correo es la identidad: es por donde llega la invitación, y no hay
    # ningún camino de alta que no pase por ella.
    email = models.EmailField("correo electrónico", unique=True)
    nombre = models.CharField("nombre", max_length=150, blank=True)
    rol = models.CharField("rol", max_length=20, choices=Rol.choices)

    # `HU-42`: una cuenta desactivada no inicia sesión ni opera, pero conserva
    # su historial. Es baja lógica, no borrado. La acción de desactivar la
    # construye `TT-19`; el campo tiene que existir desde el principio porque
    # Django lo consulta en cada autenticación.
    is_active = models.BooleanField("activa", default=True)

    # `INT-3` es el admin de Django (`DT-2`): quien administra entra por ahí.
    is_staff = models.BooleanField("accede a la administración", default=False)

    creado_en = models.DateTimeField("creado en", default=timezone.now, editable=False)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["email"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rol__in=[r.value for r in Rol]),
                name="usuario_rol_valido",
            ),
            # `TT-13`. Un `Usuario` creado sin pasar por el manager —el formulario
            # de alta del admin, un script, una carga futura— queda con
            # `password=""`, y Django considera **usable** una contraseña vacía:
            # `is_password_usable("")` devuelve `True`. Esa cuenta reportaría
            # tener contraseña definida y `reenviar_invitacion` se negaría a
            # invitarla: una cuenta que nadie puede activar nunca.
            #
            # La impone la base y no un `if` (`DT-15`): un `if` cubre el camino
            # que hoy conocemos, la restricción cubre los que aún no existen.
            models.CheckConstraint(
                condition=~models.Q(password=""),
                name="usuario_contrasena_no_vacia",
            ),
        ]

    def __str__(self):
        return f"{self.email} ({self.get_rol_display()})"

    @property
    def tiene_contrasena_definida(self):
        """¿El titular ya usó su invitación?"""
        return self.has_usable_password()
