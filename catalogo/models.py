"""Modelos de productos, categorías y alérgenos.

Aquí van la estructura y las invariantes que la base de datos puede imponer:
`CheckConstraint` y `UniqueConstraint`. **Sin lógica de negocio** (`DT-15`): una
invariante escrita como `if` se olvida en el siguiente camino de escritura; una
restricción de la base no.

La clave primaria de cada modelo es UUIDv7 generado en la aplicación (`DT-17`),
salvo el código de tarjeta, que tiene su propia regla (`INV-7`, `DT-9`).

**Lo que este módulo decide y no se puede deshacer barato.** `INV-5` dice que el
bloqueo por alérgeno se aplica **sobre la condición**, no sobre una lista fija de
productos, «de modo que cubra los productos que la cafetería agregue después».
Eso obliga a que el alérgeno sea una **relación** —`ProductoAlergeno`— y no una
lista materializada de productos bloqueados por estudiante (`DT-7`). Si se
modelara al revés, `HU-11` del Sprint 3 no se podría construir sin rehacer esto.
"""

import re
import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Categoria(models.Model):
    """Cómo se agrupa el catálogo. `HU-31` alerta **por categoría**.

    No es decoración: las alertas de frecuencia de consumo se calculan por
    categoría, así que esto es el eje de agrupación de los reportes del Sprint 4.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    nombre = models.CharField("nombre", max_length=80, unique=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Alergeno(models.Model):
    """Una condición, no una lista de productos.

    **Aquí no hay ni puede haber un campo con «los productos que lo
    contienen».** Esa lista es el resultado de una consulta sobre
    `ProductoAlergeno`, y esa diferencia es `INV-5` entera: una lista guardada se
    calcula una vez y deja fuera todo lo que se agregue después; una relación se
    evalúa en el momento de la venta y cubre lo que todavía no existe.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    nombre = models.CharField("nombre", max_length=80, unique=True)

    class Meta:
        verbose_name = "alérgeno"
        verbose_name_plural = "alérgenos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """Lo que se vende. Precio, categoría, información nutricional y alérgenos.

    Los cuatro salen del primer criterio de `HU-26` y de `ALC-IN-15`.

    **Los valores nutricionales son por porción vendible**, no por 100 g, y el
    porqué está en `./docs/campos-nutricionales.md` (`TT-44`): lo que se vende es
    una unidad, la venta copia estos valores (`DT-8`) y los reportes los suman.
    Con valores por 100 g cada suma necesitaría además el peso de la porción, y
    un dato que falta convierte el agregado en una cifra equivocada en vez de en
    un hueco visible.

    **Todos los nutrientes admiten nulo**, que significa «no declarado» y no
    «cero». El primer criterio de `HU-26` dice que el producto *admite*
    información nutricional; no dice que sea obligatoria, y una cafetería no
    tiene la ficha técnica de todo lo que vende el primer día.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    nombre = models.CharField("nombre", max_length=160, unique=True)

    # En pesos colombianos, que no tienen centavos en circulación. `Decimal` y
    # nunca `float`: con dinero, 0.1 + 0.2 no es 0.3.
    precio = models.DecimalField(
        "precio",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    # `PROTECT`: borrar una categoría no puede llevarse por delante los productos
    # que cuelgan de ella ni el historial de ventas que cuelga de esos productos.
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="productos",
        verbose_name="categoría",
    )

    # `INV-5`, `DT-7`. La relación que hace posible `HU-11`.
    alergenos = models.ManyToManyField(
        Alergeno,
        through="ProductoAlergeno",
        related_name="productos",
        verbose_name="alérgenos declarados",
        blank=True,
    )

    # --- Información nutricional, por porción vendible (`TT-44`) -------------

    porcion = models.CharField(
        "porción",
        max_length=60,
        blank=True,
        default="",
        help_text="Qué es una unidad vendible: «paquete de 30 g», «vaso de 200 ml».",
    )
    energia_kcal = models.PositiveIntegerField("energía (kcal)", null=True, blank=True)
    proteinas_g = models.DecimalField(
        "proteínas (g)", max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    carbohidratos_g = models.DecimalField(
        "carbohidratos (g)", max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    # Nutriente crítico del etiquetado frontal.
    azucares_g = models.DecimalField(
        "azúcares (g)", max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    grasas_totales_g = models.DecimalField(
        "grasas totales (g)", max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    # Nutriente crítico del etiquetado frontal.
    grasas_saturadas_g = models.DecimalField(
        "grasas saturadas (g)", max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    # Nutriente crítico del etiquetado frontal.
    sodio_mg = models.PositiveIntegerField("sodio (mg)", null=True, blank=True)

    # --- Imagen (`TT-53`, `HU-59`) ------------------------------------------

    # Como la fotografía del estudiante: **la base guarda la clave del objeto,
    # nunca el binario** (`DT-18`). Va al prefijo `publico/`, que no significa
    # accesible sin credenciales sino **no sensible** (`DT-21`).
    #
    # Vacío es un valor legítimo: segundo criterio de `HU-59`, un producto sin
    # imagen se vende igual.
    imagen_clave = models.CharField(
        "clave de la imagen", max_length=200, blank=True, default="", editable=False
    )

    # --- Estado -------------------------------------------------------------

    # Retirar del catálogo, no borrar. Un producto que ya se vendió no puede
    # desaparecer: la línea de venta copia sus datos (`DT-8`) pero el historial
    # de inventario lo referencia, y sin él las existencias dejan de explicarse
    # (`INV-3`).
    activo = models.BooleanField("en el catálogo", default=True)

    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(precio__gte=0), name="producto_precio_no_negativo"
            ),
            # Las saturadas son parte de las totales: declarar más de las que
            # hay es un error de captura, y la base puede verlo.
            models.CheckConstraint(
                condition=(
                    models.Q(grasas_saturadas_g__isnull=True)
                    | models.Q(grasas_totales_g__isnull=True)
                    | models.Q(grasas_saturadas_g__lte=models.F("grasas_totales_g"))
                ),
                name="producto_saturadas_no_superan_totales",
            ),
            # Los azúcares son parte de los carbohidratos, por lo mismo.
            models.CheckConstraint(
                condition=(
                    models.Q(azucares_g__isnull=True)
                    | models.Q(carbohidratos_g__isnull=True)
                    | models.Q(azucares_g__lte=models.F("carbohidratos_g"))
                ),
                name="producto_azucares_no_superan_carbohidratos",
            ),
        ]

    def __str__(self):
        return self.nombre

    @property
    def tiene_imagen(self):
        return bool(self.imagen_clave)

    @property
    def url_de_la_imagen(self):
        """La sirve **la aplicación**, no una URL firmada (`DT-21`).

        La imagen de un producto no es sensible, y firmar cincuenta URL para
        pintar la lista del punto de venta es coste sin contrapartida (`DT-18`).
        Además, una URL firmada caduca: el punto de venta tendría que volver a
        pedir la lista entera cada pocos minutos solo para renovar enlaces.

        La ruta lleva **la clave**, no el identificador del producto, y de ahí
        sale que la respuesta se pueda cachear como inmutable: al reemplazar la
        imagen cambia la clave, así que cambia la URL y no hay nada que
        invalidar.
        """
        if not self.imagen_clave:
            return None
        return reverse("imagen-del-producto", kwargs={"clave": self.imagen_clave})

    @property
    def declara_informacion_nutricional(self):
        """¿Hay algo declarado? Un producto sin nada no es un producto en ceros.

        Los reportes de `HU-32` tienen que poder distinguirlo: sumar un producto
        sin declarar como si fuera cero da un agregado más bajo que el real y
        parece un dato, no un hueco.
        """
        return any(
            getattr(self, campo) is not None
            for campo in (
                "energia_kcal", "proteinas_g", "carbohidratos_g", "azucares_g",
                "grasas_totales_g", "grasas_saturadas_g", "sodio_mg",
            )
        )


class ProductoAlergeno(models.Model):
    """Qué alérgeno declara qué producto. **La tabla que sostiene `INV-5`.**

    Existe como modelo propio y no como un `ManyToManyField` a secas por dos
    razones. La primera es que `DT-7` la nombra: es la mitad del cruce que
    `HU-18` consultará en el momento del cobro. La segunda es que aquí es donde
    vive la restricción de unicidad — un producto no declara dos veces el mismo
    alérgeno— y una restricción escrita es una regla que no depende de que nadie
    se despiste.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="declaraciones"
    )
    alergeno = models.ForeignKey(
        Alergeno, on_delete=models.PROTECT, related_name="declaraciones"
    )

    class Meta:
        verbose_name = "alérgeno declarado"
        verbose_name_plural = "alérgenos declarados"
        constraints = [
            models.UniqueConstraint(
                fields=["producto", "alergeno"], name="producto_alergeno_unico"
            ),
        ]

    def __str__(self):
        return f"{self.producto} declara {self.alergeno}"
