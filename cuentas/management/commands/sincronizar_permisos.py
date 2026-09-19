"""Materializa la matriz `[S11]` en grupos de Django (`TT-15`).

Se ejecuta después de cada `migrate`, porque los permisos de un modelo nuevo no
existen hasta que su tabla está creada. `sembrar` lo llama por su cuenta, así
que en el uso normal no hay que acordarse de esto.
"""

from django.core.management.base import BaseCommand

from cuentas.services import sincronizar_grupos_y_permisos


class Command(BaseCommand):
    help = "Sincroniza los grupos y permisos con la matriz [S11] (TT-15, INV-4)."

    def handle(self, *args, **opciones):
        resultado = sincronizar_grupos_y_permisos()

        for grupo, permisos in sorted(resultado.items()):
            if permisos:
                self.stdout.write(f"{grupo}: {', '.join(permisos)}")
            else:
                # **No es que falten sus modelos**: el acudiente y el cajero
                # los tienen desde los Sprints 2 y 3. Es que ninguno de los dos
                # entra al admin —`INT-1` e `INT-2` son sus interfaces
                # (`DT-2`)—, así que un permiso aquí no protegería nada y
                # sugeriría un camino por `INT-3` que no existe. La explicación
                # larga está en `cuentas/permisos.py`.
                self.stdout.write(
                    f"{grupo}: sin permisos, y es lo correcto "
                    "(no entra al admin; ver cuentas/permisos.py)"
                )

        self.stdout.write(self.style.SUCCESS("Matriz [S11] sincronizada."))
