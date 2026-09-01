"""Modelos de institución educativa, estudiantes y acudientes.

Aquí van la estructura y las invariantes que la base de datos puede imponer:
`CheckConstraint` y `UniqueConstraint`. **Sin lógica de negocio** (`DT-15`).

La clave primaria de cada modelo es UUIDv7 generado en la aplicación (`DT-17`),
salvo el código de tarjeta, que tiene su propia regla (`INV-7`, `DT-9`).
"""

import uuid

from django.conf import settings
from django.db import models

from personas.codigo import ALFABETO, LONGITUD


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


class EstadoDelEstudiante(models.TextChoices):
    """Los tres estados de `DT-12`. **No es un booleano, y esa es la decisión.**

    Un `activo = True/False` no distinguiría «perdió la tarjeta» de «se retiró
    del colegio», y `DEC-7` exige separarlos: la desactivación es reversible y
    la puede pedir el acudiente (`HU-47`, `HU-48`); la baja la da la institución
    cuando el estudiante deja el colegio, y conserva íntegro su historial.

    `INVD-2` los junta para una sola cosa: **ni desactivado ni de baja se puede
    comprar**. Para todo lo demás son estados distintos.
    """

    ACTIVO = "activo", "Activo"
    # `HU-47`, `HU-48` y `HU-49`, del Sprint 2. El estado existe desde ahora
    # porque la máquina de estados se declara entera o no es una máquina de
    # estados; lo que todavía no existe es el servicio que transita a él.
    DESACTIVADO = "desactivado", "Desactivado"
    BAJA = "baja", "De baja"


class Estudiante(models.Model):
    """El estudiante. **No tiene cuenta**: `USR-1` no inicia sesión (`[S10.1]`).

    Se identifica en el punto de venta con el código de su tarjeta. El estado de
    baja llega con `HU-51`, y la clave de la fotografía con `HU-57`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    nombre = models.CharField("nombre", max_length=200)
    documento = models.CharField("documento", max_length=20, unique=True)

    # `TT-32`, `HU-43`, `INV-7`. **No viene del archivo de carga**: lo genera el
    # sistema (`personas.codigo`), y por eso no es editable — ni en el admin, ni
    # en un formulario, ni por descuido. Primer criterio de `HU-14`: «el código
    # lo genera el sistema, no una persona».
    #
    # `unique=True` es la mitad de `DT-9` que la base puede imponer; la otra
    # mitad es el reintento ante colisión, que está en `services.py`.
    codigo_tarjeta = models.CharField(
        "código de tarjeta",
        max_length=LONGITUD,
        unique=True,
        editable=False,
    )

    # `PROTECT` y no `CASCADE`: borrar un acudiente no puede llevarse por
    # delante a sus estudiantes ni el historial que cuelga de ellos.
    acudiente = models.ForeignKey(
        Acudiente,
        on_delete=models.PROTECT,
        related_name="estudiantes",
        verbose_name="acudiente",
    )

    # `TT-41`, `HU-51`, `DT-12`. **Baja lógica, nunca borrado**: el historial de
    # consumo y de movimientos se conserva íntegro, que es lo que sostiene
    # `INV-2` —el saldo se reconstruye desde el historial— y la trazabilidad que
    # es el objeto del proyecto (`OBJ-E2`).
    estado = models.CharField(
        "estado",
        max_length=12,
        choices=EstadoDelEstudiante.choices,
        default=EstadoDelEstudiante.ACTIVO,
        editable=False,
    )

    # Cuándo se dio de baja. Nulo mientras no lo esté.
    #
    # No es adorno: «este estudiante está de baja» y «se retiró en tal fecha»
    # son dos hechos distintos, y el segundo es el que hace auditable el saldo
    # congelado de `HU-52`.
    dado_de_baja_en = models.DateTimeField("dado de baja en", null=True, blank=True, editable=False)

    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "estudiante"
        verbose_name_plural = "estudiantes"
        ordering = ["nombre"]
        constraints = [
            # La forma del código, impuesta por la base y no por un `if`
            # (`DT-15`). No puede comprobar que sea aleatorio —eso no es una
            # propiedad de un valor, sino de cómo se produjo, y lo vigila
            # `TT-31`—, pero sí que tenga la longitud fijada y que use solo
            # caracteres imprimibles como código de barras (`HU-43`).
            #
            # Sirve para lo que un `if` no serviría: el día que alguien escriba
            # un código a mano desde un `shell` o una migración, la base lo
            # rechaza.
            models.CheckConstraint(
                condition=models.Q(codigo_tarjeta__regex=rf"^[{ALFABETO}]{{{LONGITUD}}}$"),
                name="estudiante_codigo_tarjeta_con_forma_valida",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    estado__in=[e.value for e in EstadoDelEstudiante]
                ),
                name="estudiante_estado_valido",
            ),
            # La fecha de baja y el estado no pueden contradecirse. Lo impone la
            # base y no un `if` (`DT-15`): un `if` cubre el camino que hoy
            # conocemos —el servicio— y no el `update()` que alguien escriba
            # mañana en un `shell`.
            models.CheckConstraint(
                condition=(
                    models.Q(estado="baja", dado_de_baja_en__isnull=False)
                    | ~models.Q(estado="baja") & models.Q(dado_de_baja_en__isnull=True)
                ),
                name="estudiante_fecha_de_baja_coherente",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.documento})"

    @property
    def esta_de_baja(self):
        return self.estado == EstadoDelEstudiante.BAJA

    @property
    def puede_operar(self):
        """`INVD-2`. Ni desactivado ni de baja se compra o se recarga.

        Lo consultan los servicios que mueven dinero o existencias, que llegan
        en el Sprint 2. Vive aquí, junto al estado, para que ninguno tenga que
        reconstruir la regla por su cuenta.
        """
        return self.estado == EstadoDelEstudiante.ACTIVO


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
