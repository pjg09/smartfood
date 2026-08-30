"""Escrituras del dominio de usuarios, roles, invitaciones y sesión.

**Toda escritura pasa por aquí** (`DT-15`). Reglas que no se negocian:

1. Una vista nunca escribe directamente: llama a una función de este módulo.
2. Cada función abre su propia `transaction.atomic()`.
3. Estas funciones **no saben de HTTP**: no reciben `request`, no devuelven
   `HttpResponse` y no leen `request.user` —el usuario se pasa como argumento—.

Funciones, no clases.
"""
