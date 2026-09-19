# SmartFood — Las reglas de frecuencia de consumo

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-REGLAS-FRECUENCIA |
| titulo | Qué alerta de frecuencia se genera, con qué umbrales y por qué esos |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./smartfood.md` (`OBJ-E3`, `ALC-IN-21`, `ALC-OUT-20`, `INV-9`); `./backlog-historias-de-usuario.md` (`HU-30`, `HU-31`, `HU-34`); `./decisiones-tecnicas.md` (`DT-8`, `DT-32`); `./campos-nutricionales.md` |
| tipo_documento | Documento derivado. **Definición de reglas para análisis** |
| cubre | `TT-158` — Definición de las reglas determinísticas de frecuencia por categoría, con sus umbrales |
| responsable | Alejandro (análisis), `[S12]` — «definición de las reglas de recomendación» |
| creado | 2026-09-19, con `PR-02` del Sprint 5 |
| idioma | es-CO |
| version | 1.0 |

### [S0.1] Qué decide este documento

**Cuántas veces en una categoría dispara una alerta, y por qué ese número y no otro.**

`TT-158` **no es una tarea de implementación**: es la decisión que el motor de `TT-159`
ejecuta. Si en la sustentación preguntan «¿por qué cinco días y no cuatro?», la respuesta
está aquí y no en el código.

Lo escribe quien hace el análisis porque el umbral no sale de lo que es cómodo consultar,
sino de a qué se parece la semana de un estudiante. El código se limita a contar.

---

## [S1] Lo que la regla NO puede hacer

Va primero porque acota todo lo demás, y porque es lo único de este documento con
implicación legal.

`ALC-OUT-20` excluye **«cualquier forma de valoración nutricional individualizada o
prescripción dietaria, por constituir un acto profesional del área de la salud»**, e `INV-9`
obliga a que lo que se publique se declare orientativo. De ahí salen cuatro prohibiciones
que la regla cumple **por construcción, no por cuidado al redactar**:

| No puede | Por qué | Cómo se evita |
|---|---|---|
| Decir que una categoría es sana o no lo es | Es una valoración nutricional | **La regla no mira qué hay dentro de la categoría**: cuenta días. El mismo umbral vale para `Frutas` y para `Snacks` |
| Recomendar qué comer o dejar de comer | Es prescripción dietaria | La alerta **describe un patrón**; no propone ninguna acción |
| Comparar al estudiante con otros | Es perfilar a un menor, y no lo pide ninguna historia | La consulta solo alcanza a un estudiante |
| Publicarse sin descargo | `INV-9` | El aviso y las alertas son **el mismo bloque** de plantilla (`TT-161`). Ver `[S5]` |

> **La frase que separa lo que se puede decir de lo que no:** «compró de Panadería 6 de los
> últimos 14 días» es **un hecho**; «tu hijo come demasiada panadería» es **una valoración**.
> La regla produce lo primero, y por eso el umbral se llama «frecuencia alta» y nunca
> «consumo excesivo».

---

## [S2] La regla

**Una sola, con dos niveles.** `ALC-IN-21` pide «alertas de frecuencia de consumo por
categoría», en singular de familia: no hay una segunda regla de otra naturaleza, y este
documento no se inventa ninguna.

> **En cuántos días distintos de los últimos 14 aparece una compra de la misma categoría.**

| Nivel | Umbral | Qué significa |
|---|---|---|
| **Frecuencia alta** | **5 o más** días distintos de 14 | La mitad de los días lectivos del periodo, o más |
| **Frecuencia muy alta** | **8 o más** días distintos de 14 | Cuatro de cada cinco días lectivos |

Por debajo de 5 no se dice nada. **No hay un nivel «normal» y no se publica ninguna
categoría por estar por debajo**: decir «esto está bien» es tan valoración como decir lo
contrario (`[S1]`).

### [S2.1] Se cuentan días, no unidades ni dinero

Dos empanadas el mismo martes son **un** día de consumo de `Almuerzo`, no dos.

La frecuencia es cada cuánto se repite algo, y contar unidades respondería a otra pregunta
—cuánto— que ya responden el gasto (`HU-33`) y los agregados nutricionales (`HU-32`). Contar
unidades además penalizaría al estudiante que compra el almuerzo de dos días juntos, que no
es un patrón de consumo sino un recado.

### [S2.2] La ventana es de 14 días naturales, la de hoy incluida

**Y no «dos semanas escolares», porque el sistema no conoce el calendario escolar.** No hay
en ninguna parte qué días hay clase, cuáles son festivos ni cuándo son vacaciones, y no se
va a inventar: un festivo mal supuesto movería el umbral sin que nadie lo notara.

Catorce días naturales contienen **diez días lectivos típicos**, y de ahí salen los dos
umbrales de `[S2]`: cinco es la mitad de diez, ocho es cuatro de cada cinco.

Que la ventana sea de días naturales y los umbrales estén pensados en días lectivos tiene una
consecuencia que conviene decir en voz alta: **una semana de vacaciones dentro de la ventana
baja la frecuencia observada**. Es el error del lado seguro — deja de avisar, nunca avisa de
más.

### [S2.3] Qué compra cuenta, y con qué fecha

| Origen | ¿Cuenta? | Con qué fecha |
|---|---|---|
| Venta del mostrador | Sí | La de la venta |
| Reserva **entregada** | Sí | **La de la entrega** |
| Reserva **pendiente** | **No** | — |

Una reserva es una venta (`DT-32`), pero esta regla no habla de compras: habla de
**consumo**. Una reserva pagada que sigue en el mostrador todavía no se ha consumido, y
contarla diría que el estudiante comió algo que no ha recogido.

Por lo mismo, la reserva entregada cuenta **el día en que se recogió** y no el día en que se
pagó: el acudiente puede reservar el domingo por la noche lo del lunes.

> El historial de `HU-30` sí las enseña todas, incluidas las pendientes y marcadas como
> tales. **No es una contradicción**: un historial responde «qué se ha comprado» y esta regla
> responde «con qué frecuencia se ha consumido». Son dos preguntas distintas sobre las mismas
> filas.

### [S2.4] La categoría es la del producto, hoy

Es la única cifra de todo el módulo de reportes que **no** sale de la instantánea de la venta
(`DT-8`), y es deliberado: `TT-84` congeló el precio y los nutrientes, **no la categoría**.

No hay nada que congelar. Si la cafetería mueve «Arepa de choclo» de `Panadería` a
`Almuerzo`, la pregunta que el acudiente hace —«¿cada cuánto come de esto?»— se responde con
la clasificación vigente, no con la que había. Cambiar de categoría no reescribe lo que el
niño comió; sólo cambia cómo se agrupa.

**Si algún día hiciera falta congelarla**, eso es un campo nuevo en `LineaVenta`, una
migración y una decisión registrada — no un ajuste de esta regla.

### [S2.5] El orden es fijo, y eso es parte de la regla

De más días a menos; a igual número de días, por nombre de categoría en orden alfabético.

`OBJ-E3` pide reglas **determinísticas**, y determinístico no es solo que el umbral no
cambie: es que **la misma consulta dé el mismo resultado, en el mismo orden, siempre**. Un
orden que dependa de cómo la base devuelva las filas convertiría dos capturas idénticas en
dos pantallas distintas.

---

## [S3] Por qué el umbral es el mismo para todas las categorías

Es la decisión de fondo de este documento y la que más fácil se discute, así que va con su
argumento entero.

**La alternativa sería un umbral por categoría** —avisar antes de `Snacks` que de `Frutas`—,
y se descartó por tres razones, en este orden:

1. **Exige clasificar las categorías por lo saludables que son, y eso es `ALC-OUT-20`.**
   Poner un umbral más bajo a `Snacks` es afirmar que conviene menos, que es exactamente la
   valoración nutricional que el alcance excluye. No hay forma de hacerlo sin cruzar la línea.
2. **Las categorías las crea la cafetería y son texto libre.** Hoy son cinco; mañana pueden
   ser ocho con otros nombres. Un umbral por nombre de categoría se quedaría desalineado del
   catálogo en silencio, que es la peor forma de quedarse desalineado.
3. **Le daría a la cafetería el control de lo que se le dice al acudiente.** Renombrar una
   categoría cambiaría el aviso. Es el mismo razonamiento de `INV-4`: lo que protege al
   estudiante no lo configura quien le vende.

**Lo que se pierde con el umbral único**, y hay que reconocerlo: la alerta de `Frutas` es tan
alta como la de `Snacks`, y a un acudiente eso puede parecerle raro. **Es el precio correcto.**
La pantalla enseña el patrón y quien lo interpreta es la familia —o su médico—, que es
justamente el reparto de papeles que `INV-9` describe.

---

## [S4] Qué ve el acudiente

Cada alerta dice **cuatro cosas**, y ninguna más:

1. La categoría.
2. En cuántos días distintos de los 14 apareció.
3. El umbral con el que se comparó — para que la alerta sea **comprobable contra el
   historial que está debajo**, que es lo que la hace determinística a ojos de quien la lee.
4. Que es información orientativa (`[S5]`).

**No dice qué hacer.** Ninguna alerta termina en una recomendación, y esa ausencia es la
regla, no un hueco pendiente de rellenar.

---

## [S5] El aviso de `INV-9` no es un texto: es dónde está

`TT-161` cumple `HU-34`, y su criterio —«el aviso aparece en la interfaz, junto a las
recomendaciones»— se puede cumplir de dos maneras muy distintas:

- **Poniendo un párrafo en la pantalla.** Funciona hasta que alguien enseñe una alerta en
  otro sitio.
- **Haciendo que no exista ninguna forma de pintar una alerta sin el aviso.** Es lo que se
  hizo: las alertas y el descargo son **el mismo fragmento de plantilla**, y quien reutilice
  las alertas se lleva el aviso con ellas.

`INV-9` dice «las recomendaciones **son** orientativas», no «se acompañan de un aviso». Un
descargo que se puede olvidar en la siguiente pantalla no sostiene una invariante.

**El aviso se pinta siempre que se pinta el bloque**, incluso cuando no hay ninguna alerta
que mostrar. Decir «no hay ningún patrón que destacar» sin el descargo se leería como «todo
está bien», que es una valoración (`[S1]`).

---

## [S6] Lo que este documento NO decide

- **Los agregados nutricionales y su referencia sanitaria.** Es `HU-32`, y su tabla de
  valores tiene que salir de la autoridad sanitaria colombiana con su fuente citable
  (`TT-162`). Esta regla no mira ni un nutriente.
- **El resumen de gasto.** Es `HU-33`: otra pregunta y otros datos —el libro de la billetera,
  no las líneas de venta—.
- **Notificar.** Nada de esto sale a buscar al acudiente: las alertas se ven cuando entra a
  la pantalla. El correo del prototipo es solo para invitaciones (`DEC-9`).

---

## [ANEXO A] Cómo se comprueba un umbral a mano

Con el historial de `HU-30` delante, en la misma pantalla:

1. Tomar la categoría de la alerta.
2. Contar en el historial **los días distintos** —no las compras— con al menos un renglón de
   esa categoría, dentro de los últimos 14 días.
3. Descontar las reservas marcadas «sin recoger», que no cuentan (`[S2.3]`).

El número tiene que ser el mismo que enseña la alerta. **Que esto se pueda hacer a mano es la
prueba de que la regla es determinística**, y es el motivo por el que las alertas viven
encima del historial y no en otra pantalla.
