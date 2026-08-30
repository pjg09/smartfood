# Archivos de ejemplo para la carga masiva

`TT-27`. Tres archivos que ejercitan `HU-01` y `HU-02`. Los usan las pruebas
automáticas y sirven también para demostrar la carga a mano.

| Archivo | Qué contiene | Qué debe pasar |
|---|---|---|
| `carga-valida.csv` | 5 estudiantes, 3 acudientes, uno con dos hijos | Carga completa |
| `carga-con-errores.csv` | Todas las filas con algún problema | **No se escribe nada** |
| `carga-mixta.csv` | Filas correctas **y** filas con error | **No se escribe nada** |

El tercero es el que importa. Un validador que escribiera «lo que se puede»
dejaría el sistema con medio colegio dentro, y `HU-02` dice todo o nada. Si
`carga-mixta.csv` llegara a crear aunque fuera un estudiante, la historia no
se cumple.

Todos los datos son ficticios (`ALC-OUT-07`) y el dominio `example.com` está
reservado por la RFC 2606: nadie puede registrarlo.
