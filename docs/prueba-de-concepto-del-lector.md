# SmartFood — Prueba de concepto del lector de código de barras

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-POC-LECTOR |
| titulo | Guion de la validación con tarjetas impresas y lector físico |
| documentos_fuente | `./backlog-historias-de-usuario.md` (`HU-15`, `HU-45`); `./decisiones-tecnicas.md` (`DT-22`, `DT-9`); `./smartfood.md` (`ENT-02`, `ALC-OUT-05`) |
| tipo_documento | Guion de prueba. **Es el insumo de `ENT-02`**, no un artefacto de Scrum |
| tarea | `TT-72` (`PR-07`), responsable Alejandro |
| estado | ☑ **Ejecutada** el 2026-09-11, con impresora, tarjetas de papel y lector USB |
| idioma | es-CO |
| version | 1.1 |

### [S0.1] Por qué existe este documento

`TT-72` es la única tarea del Sprint 2 que **no se puede automatizar**: hace falta una
impresora, papel y un lector USB. El software que la hace posible está construido y
probado —`TT-37` imprime la tarjeta, `TT-70` y `TT-71` la leen—, pero *que el aparato
teclee lo que hay impreso* solo se comprueba pasándolo.

**Ya se pasó.** El guion se ejecutó el 2026-09-11 y `ENT-02` queda cerrado con él. El
documento se conserva porque sigue siendo el guion: si hay que repetir la prueba —otro
lector, otra impresora, o el día de la demostración del Avance 1— estos son los pasos, y
`[S1]` sigue diciendo qué puede fallar.

---

## [S1] Qué se está validando

`HU-15`, tercer criterio: **la validación se realiza a escala reducida, con un número
limitado de tarjetas**. `ALC-OUT-05` excluye la producción masiva a propósito: cinco
tarjetas bastan para saber si el símbolo se lee, y mil no dirían nada más.

Lo que puede fallar y esto detecta:

| Riesgo | Cómo se manifiesta |
|---|---|
| El navegador reescala al imprimir | Las barras salen más estrechas y el lector no engancha |
| Ancho de módulo insuficiente | Lee a veces, según el ángulo o la distancia |
| Zona muda recortada | El lector no encuentra dónde empieza el símbolo |
| El lector añade prefijo o sufijo | Llega un código con caracteres de más y no encuentra a nadie |
| El lector no envía Enter | El código aparece en el campo pero la búsqueda no se dispara |

Los tres primeros son de `DT-22`; los dos últimos, de configuración del aparato.

---

## [S2] Qué hace falta

- Una impresora láser o de inyección corriente. **No** una de credenciales.
- Papel normal. Si hay cartulina, mejor: aguanta más pases.
- Un lector USB de código de barras, de los que se comportan como teclado. **No hace
  falta driver ni SDK** — el aparato teclea el código y envía Enter, y por eso el campo
  del punto de venta dispara con esa tecla (`TT-71`).
- El entorno local levantado y sembrado (`./desarrollo.md`).

---

## [S3] El guion

1. **Imprimir cinco tarjetas.** Como institución, en el admin: *Estudiantes* →
   **Imprimir tarjeta** de cinco estudiantes distintos. En el diálogo del navegador,
   **escala 100 %** y sin «ajustar a la página»: es lo que la propia pantalla avisa, y
   es el fallo más probable de toda la prueba.
2. **Comprobar el ancho impreso.** El símbolo mide 69 mm con las zonas mudas. Medirlo
   con una regla: si sale más estrecho, el navegador reescaló y hay que repetir el
   paso 1.
3. **Recortar sin invadir los márgenes blancos laterales.** Son parte del código.
4. **Entrar al punto de venta como cajero** (`/punto-de-venta/`, ver credenciales en
   `./desarrollo.md`) y comprobar que el cursor está en el campo de escaneo **sin
   tocar nada**.
5. **Pasar cada tarjeta una vez.** Anotar para cada una: si leyó a la primera, cuántos
   intentos hicieron falta y si el nombre que apareció es el del estudiante correcto.
6. **Pasar dos tarjetas seguidas, sin tocar el teclado entre una y otra.** Es el caso
   que importa de verdad: si el campo no se vaciara, la segunda se concatenaría con la
   primera y no encontraría a nadie.
7. **Probar una tarjeta de un estudiante dado de baja.** Tiene que identificarlo y
   avisar de que no se le puede vender (`INVD-2`), no decir que la tarjeta no es de
   nadie.
8. **Probar el reverso del caso**: teclear un código a mano y pulsar Enter. Es lo que
   se hace cuando una tarjeta está gastada, y tiene que funcionar igual.

---

## [S4] Dónde está el resultado

**La evidencia vive en `ENT-05`**, junto con los otros tres escenarios críticos, no en
este repositorio: una tabla con una fila por tarjeta —estudiante, intentos, resultado— y
una nota con la marca y el modelo del lector. Aquí solo consta que la ejecución ocurrió y
cuándo; el detalle lo aporta `corpus:ENT-05`, que es donde la asignatura lo pide.

Se registra **tal cual salga**: una prueba de concepto que solo se apunta cuando sale bien
no es evidencia de nada. Si alguna tarjeta no leyó, lo que hay que anotar es **qué se
cambió para que leyera** —reimprimir al 100 %, cambiar el ángulo, limpiar el lector—,
porque eso es lo que tendrá que saber quien opere la caja.
