"""**Esta app no tiene modelos, y no es un olvido.**

Un reporte es una **lectura** de hechos que ya están escritos en otro sitio: la
venta y su instantánea nutricional (`ventas`, `DT-8`), el libro de la billetera
(`billetera`, `DT-4`) y el del inventario (`inventario`, `DT-5`). Guardar aquí
una tabla de «consumo» sería una segunda fuente de verdad de algo que ya se
puede reconstruir, que es justo lo que `INV-2` e `INV-3` impiden en los dos
libros y `DT-19` en el modelo entero.

Por eso la app entra sin migraciones: todo lo suyo vive en `selectors.py`.

La excepción llegará con `HU-55` —el cierre de caja tiene modelo propio
(`TT-171`)—, pero ese es de `ventas`: un cierre **no es un reporte**, es un
hecho nuevo que alguien registra. El reporte de cierres (`HU-56`) sí es de aquí,
y también será una lectura.
"""
