"""Retira el superusuario de la cuenta institucional (`UX-6` de `TT-35`).

La bandera dejó de concederse en `personas.services.dar_de_alta_la_institucion`,
pero el seed es **idempotente**: al encontrar la institución ya creada no la
vuelve a tocar. Sin esta migración, el arreglo solo valdría para entornos
nuevos, y el local y el desplegado —los dos que existen— seguirían con la cuenta
que puede editar los grupos de permisos.

Un superusuario de Django tiene todos los permisos por definición, se declaren o
no en la matriz `[S11]`. Con ellos, la institución alcanza `/admin/auth/group/`,
que es donde `DT-11` materializa `INV-4`.
"""

from django.db import migrations


def quitar_el_superusuario(apps, schema_editor):
    """Solo a las cuentas institucionales, no a cualquier superusuario.

    Si alguien creó uno a mano para trabajar en local, no es asunto de esta
    migración: lo que aquí se corrige es cómo nace la cuenta de `USR-5`.
    """
    Usuario = apps.get_model("cuentas", "Usuario")
    Usuario.objects.filter(rol="institucion", is_superuser=True).update(
        is_superuser=False
    )


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0002_usuario_usuario_contrasena_no_vacia"),
    ]

    operations = [
        # Sin vuelta atrás: deshacer esto sería volver a conceder el permiso
        # sobre los grupos que sostienen `INV-4`. Si hiciera falta revertir la
        # migración por otra razón, la cuenta se queda sin la bandera, que es el
        # estado correcto de todos modos.
        migrations.RunPython(quitar_el_superusuario, migrations.RunPython.noop),
    ]
