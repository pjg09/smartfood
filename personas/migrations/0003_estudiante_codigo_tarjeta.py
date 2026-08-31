"""`TT-32`. El código de tarjeta del estudiante (`HU-43`, `INV-7`).

**Escrita a mano y en tres pasos**, porque el campo es único y obligatorio y ya
hay estudiantes cargados. `makemigrations` habría pedido un valor por defecto, y
un valor por defecto es justo lo que no puede tener: todas las filas existentes
quedarían con el mismo código y el índice único fallaría. Peor aún si el defecto
fuera algo como una secuencia — sería `INV-7` rota desde la primera migración.

Los tres pasos: añadir el campo admitiendo nulo, generar un código distinto para
cada fila existente con el mismo generador que usa la aplicación, y solo entonces
exigir el índice único y la restricción de forma.
"""

from django.db import migrations, models

from personas.codigo import ALFABETO, LONGITUD, generar_codigo_de_tarjeta


def asignar_codigos_a_los_ya_cargados(apps, schema_editor):
    """Un código nuevo para cada estudiante que entró antes de esta migración.

    Reintenta ante colisión igual que el servicio: el índice único todavía no
    existe en este paso, así que la comprobación se hace contra lo ya asignado.
    """
    Estudiante = apps.get_model("personas", "Estudiante")

    asignados = set()
    for estudiante in Estudiante.objects.all().iterator():
        codigo = generar_codigo_de_tarjeta()
        while codigo in asignados:
            codigo = generar_codigo_de_tarjeta()
        asignados.add(codigo)

        estudiante.codigo_tarjeta = codigo
        estudiante.save(update_fields=["codigo_tarjeta"])


def quitar_los_codigos(apps, schema_editor):
    """La vuelta atrás. Los códigos no se conservan: se regeneran."""
    Estudiante = apps.get_model("personas", "Estudiante")
    Estudiante.objects.update(codigo_tarjeta=None)


class Migration(migrations.Migration):

    dependencies = [
        ("personas", "0002_acudiente_estudiante"),
    ]

    operations = [
        migrations.AddField(
            model_name="estudiante",
            name="codigo_tarjeta",
            field=models.CharField(
                editable=False,
                max_length=LONGITUD,
                null=True,
                verbose_name="código de tarjeta",
            ),
        ),
        migrations.RunPython(
            asignar_codigos_a_los_ya_cargados,
            quitar_los_codigos,
        ),
        migrations.AlterField(
            model_name="estudiante",
            name="codigo_tarjeta",
            field=models.CharField(
                editable=False,
                max_length=LONGITUD,
                unique=True,
                verbose_name="código de tarjeta",
            ),
        ),
        migrations.AddConstraint(
            model_name="estudiante",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    codigo_tarjeta__regex=rf"^[{ALFABETO}]{{{LONGITUD}}}$"
                ),
                name="estudiante_codigo_tarjeta_con_forma_valida",
            ),
        ),
    ]
