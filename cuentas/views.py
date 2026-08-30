"""Vistas de usuarios, roles, invitaciones y sesión.

Solo HTTP: parsear la petición, delegar en un servicio o un selector, y
renderizar. **Cero lógica de negocio** (`DT-15`).

Una vista HTMX devuelve **un fragmento, nunca una página** (`DT-16`). Si un
endpoint devuelve a veces una cosa y a veces la otra, se parte en dos.
"""
