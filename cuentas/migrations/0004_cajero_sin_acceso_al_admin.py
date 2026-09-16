"""El cajero deja de tener acceso a la administración.

`[S11]` concede `INT-3` a la administración de cafetería y a la institución; al
cajero le concede registrar ventas, y eso ocurre entero en `INT-2`. La matriz
`PERMISOS_POR_ROL` ya lo decía —su diccionario está vacío—, pero la cuenta lo
contradecía: nacía con `is_staff` y podía entrar a un admin sin un solo modelo.

`crear_personal` deja de dárselo, y esto arregla las cuentas que ya existen. Sin
esta migración la corrección solo valdría para las altas nuevas, y la puerta
seguiría abierta en todos los entornos que ya tienen un cajero.
"""

from django.db import migrations


def quitar_acceso_a_los_cajeros(apps, schema_editor):
    """`is_staff = False` a todo cajero.

    **No se toca `is_active` ni los grupos.** El cajero sigue entrando al sistema
    por `/login/` y cobrando en el punto de venta; lo único que pierde es una
    puerta que no llevaba a ninguna parte.
    """
    Usuario = apps.get_model("cuentas", "Usuario")
    Usuario.objects.filter(rol="cajero", is_staff=True).update(is_staff=False)


def devolver_el_acceso(apps, schema_editor):
    """La vuelta atrás, para que la migración sea reversible.

    Devuelve el estado anterior —todo cajero con `is_staff`— y no el de cada
    cuenta una por una: el estado anterior era exactamente ese, porque
    `crear_personal` se lo daba a todas sin excepción.
    """
    Usuario = apps.get_model("cuentas", "Usuario")
    Usuario.objects.filter(rol="cajero").update(is_staff=True)


class Migration(migrations.Migration):
    dependencies = [("cuentas", "0003_institucion_sin_superusuario")]

    operations = [
        migrations.RunPython(quitar_acceso_a_los_cajeros, devolver_el_acceso),
    ]
