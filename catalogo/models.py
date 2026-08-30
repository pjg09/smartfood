"""Modelos de productos, categorías y alérgenos.

Aquí van la estructura y las invariantes que la base de datos puede imponer:
`CheckConstraint` y `UniqueConstraint`. **Sin lógica de negocio** (`DT-15`): una
invariante escrita como `if` se olvida en el siguiente camino de escritura; una
restricción de la base no.

La clave primaria de cada modelo es UUIDv7 generado en la aplicación (`DT-17`),
salvo el código de tarjeta, que tiene su propia regla (`INV-7`, `DT-9`).
"""
