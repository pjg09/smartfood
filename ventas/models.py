"""Modelos de venta.

**Vacío a propósito, y esto no es un fichero olvidado.** La app nace en `TT-57`
y `TT-58` porque el punto de venta (`INT-2`) necesita un sitio donde vivir, pero
sus modelos —venta y línea de venta, con medio de pago y estudiante opcional—
son de `TT-78` (`PR-11`), y el servicio que los asienta dentro de una única
transacción con bloqueo pesimista es `TT-80` (`PR-12`, `INV-1`).

Cada app del proyecto se crea en el sprint que la necesita, y esta la necesita
ya la pantalla: sin ella, la vista del punto de venta tendría que colgar de otro
dominio o de `config`, y a la primera venta habría que mudarla.
"""
