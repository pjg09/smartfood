"""Modelos de institución educativa, estudiantes y acudientes.

Aquí van la estructura y las invariantes que la base de datos puede imponer:
`CheckConstraint` y `UniqueConstraint`. **Sin lógica de negocio** (`DT-15`).

La clave primaria de cada modelo es UUIDv7 generado en la aplicación (`DT-17`),
salvo el código de tarjeta, que tiene su propia regla (`INV-7`, `DT-9`).
"""

import uuid

from django.conf import settings
from django.db import models


class Acudiente(models.Model):
    """Quien responde por uno o varios estudiantes (`USR-2`).

    **Un acudiente, varios estudiantes** (`ALC-IN-04`, `HU-04`). La relación va
    en `Estudiante`, no aquí: es el estudiante el que tiene un responsable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="acudiente",
        verbose_name="cuenta",
    )
    nombre = models.CharField("nombre", max_length=200)
    documento = models.CharField("documento", max_length=20, unique=True)

    class Meta:
        verbose_name = "acudiente"
        verbose_name_plural = "acudientes"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.documento})"

    @property
    def email(self):
        return self.usuario.email


class Estudiante(models.Model):
    """El estudiante. **No tiene cuenta**: `USR-1` no inicia sesión (`[S10.1]`).

    Se identifica en el punto de venta con el código de su tarjeta, que llega en
    `TT-30` y `TT-32` — y que **no viene del archivo de carga**: generarlo es del
    sistema (`INV-7`). El estado de baja llega con `HU-51`, y la clave de la
    fotografía con `HU-57`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    nombre = models.CharField("nombre", max_length=200)
    documento = models.CharField("documento", max_length=20, unique=True)

    # `PROTECT` y no `CASCADE`: borrar un acudiente no puede llevarse por
    # delante a sus estudiantes ni el historial que cuelga de ellos.
    acudiente = models.ForeignKey(
        Acudiente,
        on_delete=models.PROTECT,
        related_name="estudiantes",
        verbose_name="acudiente",
    )

    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "estudiante"
        verbose_name_plural = "estudiantes"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.documento})"


class Institucion(models.Model):
    """La institución educativa. **El prototipo opera sobre una sola.**

    Es un criterio de aceptación de `HU-39` y sale de `ALC-OUT-10`. Lo impone la
    base, no un `if`: el campo `unica` es único y solo admite el valor 1, así que
    una segunda fila es un error de integridad y no algo que dependa de que
    todos los caminos de escritura se acuerden de comprobarlo (`DT-15`).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    nombre = models.CharField("nombre", max_length=200)

    # La cuenta con la que la institución opera el sistema (`HU-39`).
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="institucion",
        verbose_name="cuenta",
    )

    unica = models.PositiveSmallIntegerField(default=1, editable=False)

    class Meta:
        verbose_name = "institución educativa"
        verbose_name_plural = "instituciones educativas"
        constraints = [
            models.UniqueConstraint(fields=["unica"], name="institucion_unica"),
            models.CheckConstraint(condition=models.Q(unica=1), name="institucion_unica_es_uno"),
        ]

    def __str__(self):
        return self.nombre
