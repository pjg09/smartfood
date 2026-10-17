"""`INT-3` para las ventas: **ya no queda nada aquí**.

Los dos reportes que vivían en este fichero son pantallas propias: el de ventas
en `/ventas/` (`DT-54`) y el de cierres de caja en `/cierres/` (`DT-55`), con
barras, tarjetas y modales que el admin no carga. Sus selectores siguen en
`reportes.selectors`.

**Nadie escribe una venta ni un cierre**, y no porque no haya pantalla: un
asiento no se edita ni se borra (`INV-2`, `INV-3`, `INVD-5`), y `ventas` entra
en `APPS_SIN_ESCRITURA_PARA_NINGUN_ROL`, así que el permiso tampoco existe en
ningún grupo (`DT-11`).

El fichero se queda para que quien busque el admin de ventas encuentre aquí
dónde está.
"""
