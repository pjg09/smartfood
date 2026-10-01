#!/usr/bin/env bash
# Servicio `estilos` de `compose.yaml` (DT-37, DT-36).
#
# Compila las DOS hojas —la de la aplicación y la del admin— y se queda
# recompilándolas cuando cambia una plantilla. Es el `tailwind watch` que antes
# había que dejar abierto en otra terminal.
set -euo pipefail

# Primero una compilación completa. `--force` porque sin él el comando solo mira
# la fecha de `fuente.css`, no las plantillas, y contesta «up to date».
python manage.py tailwind build --force
python manage.py estilos_del_admin
touch /tmp/estilos-listos

# `tailwind watch` se para en cuanto su stdin se cierra, sin decirlo y con el
# proceso vivo (`[S1]` de docs/trampas-del-stack.md). En un script, un proceso
# en segundo plano recibe /dev/null como stdin: se le da uno que no se cierre.
# Con `< <(…)` y no con una tubería: en una tubería el trabajo no termina hasta
# que termina `tail`, que no termina nunca, y la muerte del vigilante no se vería.
python manage.py estilos_del_admin --watch < <(tail -f /dev/null) &
python manage.py tailwind watch < <(tail -f /dev/null) &

# Si cualquiera de los dos muere, el servicio cae y `restart:` lo levanta.
# Más vale un reinicio visible que un vigilante muerto en silencio.
wait -n
exit 1
