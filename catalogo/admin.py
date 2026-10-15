"""`INT-3` es el admin de Django (`DT-2`): no lleva plantillas propias.

`TT-45`. **El catálogo ya no tiene ninguna pantalla aquí** (`DEC-25`,
`DEC-26`, `DT-50`, `DT-51`, `DT-52`). Los productos se crean, se editan y se
retiran en `/inventario/`, junto a sus existencias y su libro; las categorías,
en `/categorias/`, y los alérgenos, en `/alergenos/`. Las reglas no se
movieron —siguen en `catalogo.services`— y tampoco la que importa: **el
alérgeno se declara en el producto, no se copia**, y no existe en ninguna parte
una lista de «productos bloqueados» que alguien pudiera llenar a mano (`INV-5`).

El fichero se queda para que quien busque el admin del catálogo encuentre aquí
dónde está.
"""
