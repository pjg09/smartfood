# SmartFood — Sprint Backlog del Sprint 5

## [S0] Bloque de control del documento

### [S0.1] Metadatos

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-SPRINT5 |
| titulo | Sprint Backlog del Sprint 5 — Reportes de consumo y cierre del proyecto |
| archivo_origen | — · documento derivado; no reexpresa ningún original |
| documentos_fuente | `./backlog-historias-de-usuario.md` (`[S5]`, Sprint 5); `./decisiones-de-alcance.md`; `./decisiones-tecnicas.md`; `./smartfood.md` (`S9.3`, `S11`, `S12`); `corpus:guia-de-scrum-2020.md` (`ART-2`, `COM-2`, `COM-3`) |
| tipo_documento | Sprint Backlog (`ART-2` de la Guía de Scrum) |
| sprint | **5 de 5 — el último** |
| semanas | 14 – 15 |
| hito | **Entrega final · semana 16** (`EVA-5`, 30 % de la nota) |
| historias | 10 (`HU-30`, `HU-31`, `HU-34`, `HU-32`, `HU-33`, `HU-35`, `HU-36`, `HU-55`, `HU-56`, `HU-37`) |
| tareas | 33 (`TT-155` … `TT-187`), de las que **6 son de cierre del proyecto** y no salen de ninguna historia |
| stack | Django + PostgreSQL + HTMX (`DT-2`, `DT-3` de `./decisiones-tecnicas.md`) |
| idioma | es-CO |
| version | 1.0 |

### [S0.2] Instrucciones de lectura para el agente

1. Documento **derivado**: no reexpresa ningún original y no lleva texto verbatim.
2. Es el **Sprint Backlog** en el sentido de `ART-2` de la Guía de Scrum.
3. **Ninguna tarea introduce alcance nuevo.** Cada una se deriva de una historia de `./backlog-historias-de-usuario.md`, o de un entregable declarado en `[S9.3]` de `./smartfood.md`, y lo declara.
4. **La serie `TT-` continúa**: los sprints anteriores terminaron en `TT-56`, `TT-93`, `TT-136` y `TT-154`.
5. Los responsables salen de la matriz `[S12]` de `./smartfood.md`.
6. **La columna `Estado` marca el avance.** El estado se lleva **también** en `./plan-de-pull-requests-sprint-5.md`; si hay discrepancia, manda ese documento.
7. Los identificadores `[TT-nn]` son estables y citables.

### [S0.3] Mapa de secciones

| ID | Sección | Contenido |
|---|---|---|
| S1 | Objetivo del Sprint | `COM-2` |
| S2 | Definición de Terminado | Puntero a `./definicion-de-terminado.md` (`COM-3`) |
| S3 | Tareas de habilitación | **Ninguna.** Se explica por qué |
| S4 | Tareas por historia | `TT-155` … `TT-178` |
| S5 | Tareas de cierre del proyecto | `TT-179` … `TT-184` — los entregables de `[S9.3]` |
| S6 | Tareas de gestión del Sprint | `TT-185` … `TT-187` |
| S7 | Reparto por responsable | Carga de cada integrante |
| ANEXO A | Riesgos del sprint | Es el último: lo que falle aquí no se recupera |
| ANEXO B | Nota de procedencia | Cómo se derivó |
| ANEXO C | Verificación del orden de construcción | Grafo de dependencias |

---

## [S1] Objetivo del Sprint `[COM-2]`

> Que el acudiente vea en qué se está gastando el dinero y qué está comiendo su hijo, que la cafetería cuadre su caja y audite su operación, y que el proyecto quede entregable: pruebas ejecutadas con evidencia, informe final escrito y sustentación preparada.

**Es el último sprint.** Cierra las diez historias que quedan y, sobre todo, convierte un prototipo que funciona en un proyecto entregado. La entrega final es la semana 16 y vale el **30 %** de la nota — más que cualquier otro hito del semestre.

---

## [S2] Definición de Terminado `[COM-3]`

La misma de todo el semestre: `./definicion-de-terminado.md`. **Los seis criterios están vigentes**: `DoD-4` dejó de estar suspendido al reescribirse en el Sprint 4 (`DEC-15`, `DT-31`).

---

## [S3] Tareas de habilitación

**Ninguna.** La app `reportes` que este sprint necesita ya está declarada en `DT-15` desde el principio, así que crearla no es una desviación: entra como primera tarea de `HU-30`.

Lo que sí hay, y en ningún sprint anterior lo hubo, es una sección de **cierre del proyecto** (`[S5]`). Ver el aviso que la encabeza.

---

## [S4] Tareas por historia

**El orden en que están escritas es el orden en que se pueden desarrollar.** El `ANEXO C` lo verifica.

### `[HU-30]` Historial de consumo para el acudiente

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-155` | App `reportes` y selector del historial de consumo de un estudiante | Pedro | ☑ |
| `TT-156` | Pantalla del historial de consumo en la interfaz del acudiente | Carlos | ☑ |
| `TT-157` | Caso de prueba: el acudiente solo ve a los estudiantes a su cargo | Alejandro | ☑ |

El historial muestra **la información nutricional registrada al momento de cada venta**, no la actual: es lo que `TT-84` congeló en la línea de venta en el Sprint 2 (`DT-8`). Leer el producto actual en vez de la instantánea rompe `HU-22` retroactivamente.

`TT-157` es de control de acceso, no de presentación: la matriz `[S11]` da el consumo **solo** al acudiente, y solo de sus estudiantes.

### `[HU-31]` Alertas de frecuencia de consumo

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-158` | Definición de las reglas determinísticas de frecuencia por categoría, con sus umbrales | Alejandro | ☑ |
| `TT-159` | Motor que evalúa esas reglas sobre el historial | Pedro | ☑ |
| `TT-160` | Alertas en la pantalla del acudiente | Carlos | ☑ |

`TT-158` es de Alejandro porque `[S12]` le asigna «la definición de las reglas de recomendación». **No es una tarea de implementación**: es decidir cuántas veces por semana en una categoría dispara una alerta, y poder justificarlo.

> **Nada de modelos.** `OBJ-E3` y `ALC-IN-21` exigen **reglas determinísticas**. Un modelo probabilístico está fuera del alcance y además no tendría con qué entrenarse: los datos son ficticios (`ALC-OUT-07`).

### `[HU-34]` Aviso de carácter orientativo

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-161` | Aviso de carácter orientativo junto a las recomendaciones (`INV-9`) | Carlos | ☑ |

> ⚠ **Esta tarea no puede quedarse para después de `HU-31`.** `INV-9` exige que el aviso esté presente **desde la primera recomendación publicada**, y `ALC-OUT-20` excluye «cualquier forma de valoración nutricional individualizada» por ser acto profesional del área de la salud. Publicar alertas sin el descargo, aunque sea una semana, incumple la invariante.
>
> Por eso `TT-161` va **en el mismo Pull Request** que `HU-31`. Ver `PR-02` del plan.

### `[HU-32]` Comparación con valores de referencia

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-162` | Localizar y registrar los valores de referencia de la autoridad sanitaria colombiana, con su fuente | Alejandro | ☑ |
| `TT-163` | Cálculo determinístico de los agregados nutricionales frente a esa referencia | Pedro | ☑ |
| `TT-164` | Comparación en la pantalla del acudiente | Carlos | ☑ |

`TT-162` es **investigación documental, no código**, y es la tarea con más riesgo de quedarse a medias: la historia exige que la referencia sea «la publicada por la autoridad sanitaria colombiana», así que hay que ir a la normativa del Ministerio de Salud, elegir la tabla y **dejar registrada la fuente**. Si en la sustentación preguntan de dónde salen esas cifras, esta tarea es la respuesta.

### `[HU-33]` Resumen de gasto frente a saldo recargado

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-165` | Selector del gasto frente al saldo recargado en un periodo | Pedro | ☑ |
| `TT-166` | Resumen de gasto en la pantalla del acudiente | Carlos | ☑ |

Sale entero del libro de movimientos de la billetera: recargas contra ventas. No hay dato nuevo que capturar.

### `[HU-35]` Reporte de ventas

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-167` | Selector del reporte de ventas sobre las transacciones registradas | Pedro | ☑ |
| `TT-168` | Reporte de ventas en la interfaz administrativa | Carlos | ☑ |

«Sobre las transacciones registradas, **no sobre datos capturados aparte**»: el reporte lee las ventas que ya existen. Incluye las genéricas de `HU-53` y distingue el medio de pago de `HU-54`.

### `[HU-36]` Reporte de movimientos de inventario

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-169` | Selector del reporte de movimientos, con su motivo | Pedro | ☑ |
| `TT-170` | Reporte de inventario en la interfaz administrativa | Carlos | ☑ |

Se apoya en `historial_de`, que existe desde el Sprint 2, y en la merma con motivo del Sprint 4.

### `[HU-55]` Cierre de caja diario

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-171` | Modelo de cierre de caja: fecha, cajero, base, efectivo contado, diferencia y motivo | Pedro | ☐ |
| `TT-172` | Servicio de cierre que calcula el efectivo esperado **desde las ventas registradas** (`INVD-5`) | Pedro | ☐ |
| `TT-173` | Pantalla de cierre de caja en el punto de venta | Carlos | ☐ |
| `TT-174` | Caso de prueba: diferencia ≠ 0 exige motivo, y las transferencias **no** entran en el cuadre | Alejandro | ☐ |

Es la historia más densa del sprint y la única que añade un modelo. Tres condiciones que se pierden fácil:

- **El efectivo esperado se calcula, no se digita** (`INVD-5`). Es la suma de las ventas en efectivo del día.
- **Las transferencias quedan fuera del cuadre**: ese dinero nunca pasó por la caja (`DEC-1`).
- **Motivo obligatorio si la diferencia no es cero**, con el mismo criterio que `ALC-IN-18` aplica al inventario.

> `PA-7` del anteproyecto describe lo que hace hoy la cafetería: cuadrar «el efectivo recaudado contra **su estimación** de lo vendido». Esta historia es la que convierte esa estimación en ventas registradas. Es una ruptura del proceso actual y conviene decirlo así en la sustentación.

### `[HU-56]` Reporte de cierres de caja

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-175` | Selector de los cierres registrados | Pedro | ☐ |
| `TT-176` | Reporte de cierres en la interfaz administrativa | Carlos | ☐ |

### `[HU-37]` Reporte de auditoría

| ID | Tarea | Responsable | Estado |
|---|---|---|---|
| `TT-177` | Selector de auditoría que consolida ventas, movimientos de inventario y cierres de caja | Pedro | ☐ |
| `TT-178` | Reporte de auditoría en la interfaz administrativa | Carlos | ☐ |

**Va la última porque consolida las tres anteriores.** Al integrarse, `ALC-IN-22` queda cubierto entero y **las 61 historias del proyecto están terminadas**.

---

## [S5] Tareas de cierre del proyecto

> **Esta sección no existe en ningún sprint anterior, y es la razón por la que este backlog no son solo diez historias.**
>
> `[S9.3]` de `./smartfood.md` declara **siete entregables** (`ENT-01` … `ENT-07`). Tres de ellos —el plan de pruebas ejecutado, el informe final y la sustentación— **no son historias de usuario y ningún sprint los ha planificado**. Si este backlog cubriera solo `[S4]`, el equipo llegaría a la semana 16 con el prototipo terminado y sin entregable.
>
> Estado de los siete al abrir este sprint: `ENT-01` cumplido en local (`DEC-15`), `ENT-02` cerrado en el Sprint 2 con la prueba del lector, `ENT-03` y `ENT-04` **parciales**, y `ENT-05`, `ENT-06` y `ENT-07` **sin empezar**.

| ID | Tarea | Responsable | Entregable | Estado |
|---|---|---|---|---|
| `TT-179` | Ejecución del plan de pruebas y evidencia de los cuatro escenarios críticos `TST-1` … `TST-4` | Alejandro | `ENT-05` | ☐ |
| `TT-180` | Diagrama de arquitectura — lo que falta de la documentación técnica | Pedro | `ENT-03` | ☐ |
| `TT-181` | Mapa de stakeholders y matriz de riesgos del proyecto | Naomi | `ENT-04` | ☐ |
| `TT-182` | Recorrido de experiencia de usuario e indicadores de desempeño (KPI) | Alejandro | `ENT-04` | ☐ |
| `TT-183` | Informe técnico final: resultados, limitaciones identificadas y trabajo futuro | Naomi | `ENT-06` | ☐ |
| `TT-184` | Preparación de la sustentación y la demostración en vivo | Naomi | `ENT-07`, `EVA-5` | ☐ |

**`TT-179` puede empezar el primer día.** Los cuatro escenarios críticos están construidos desde el Sprint 4; lo que falta es **ejecutarlos y dejar evidencia**, que es lo que `ENT-05` pide.

**`TT-183` es el que más fácil se queda corto.** `ENT-06` pide «resultados, limitaciones identificadas y trabajo futuro». Las limitaciones ya están escritas y dispersas: los `ANEXO B` de `./decisiones-de-alcance.md` y `./decisiones-tecnicas.md` llevan todo el semestre acumulando puntos abiertos, y `DEC-15` documenta que el prototipo no se despliega. **El informe se redacta recogiéndolos, no inventándolos.**

---

## [S6] Tareas de gestión del Sprint

| ID | Tarea | Responsable | Origen | Estado |
|---|---|---|---|---|
| `TT-185` | Tablero Kanban del Sprint 5 | Naomi | `CUR-3` | ☐ |
| `TT-186` | Registro de riesgos del Sprint 5 | Naomi | `ENT-04` | ☐ |
| `TT-187` | Sprint Review y Retrospective **finales** del proyecto | Naomi | `EVT-3`, `EVT-4` | ☐ |

`TT-186` alimenta `TT-181`: la matriz de riesgos del proyecto es la consolidación de los cinco registros de sprint, no un documento nuevo.

---

## [S7] Reparto por responsable

| Integrante | Rol `[S12]` | Tareas | Cuáles |
|---|---|---|---|
| **Pedro** | Desarrollador backend | **11** | `TT-155`, `TT-159`, `TT-163`, `TT-165`, `TT-167`, `TT-169`, `TT-171`, `TT-172`, `TT-175`, `TT-177`, `TT-180` |
| **Carlos** | Desarrollador frontend | **10** | `TT-156`, `TT-160`, `TT-161`, `TT-164`, `TT-166`, `TT-168`, `TT-170`, `TT-173`, `TT-176`, `TT-178` |
| **Alejandro** | Analista de datos y UX | **6** | `TT-157`, `TT-158`, `TT-162`, `TT-174`, `TT-179`, `TT-182` |
| **Naomi** | Líder de proyecto | **6** | `TT-181`, `TT-183`, `TT-184`, `TT-185`, `TT-186`, `TT-187` |

**Total: 33 tareas.**

Es el sprint en que más pesan Alejandro y Naomi, y no por casualidad: `[S12]` les asigna los reportes de consumo, las reglas de recomendación, el plan de pruebas y la documentación de gestión. **Todo eso vence ahora.** En los cuatro sprints anteriores sumaron 25 tareas entre los dos; aquí suman 12.

---

## [ANEXO A] Riesgos del sprint

**1. Es el último: lo que falle aquí no se recupera.** No hay sprint siguiente al que mover una historia. Si algo tiene que caerse, que sean los `Should` de reportes —`HU-33`, `HU-36`, `HU-56`— y **nunca** las tareas de `[S5]`: sin `ENT-05` y `ENT-06` no hay entrega, por mucho prototipo que haya.

**2. El cierre del proyecto compite con las historias por las mismas dos semanas.** Seis tareas de `[S5]` más tres de gestión son nueve de las 33. Casi todas son de Naomi y Alejandro, así que el desarrollo no se bloquea — pero **el informe final no se escribe en el último fin de semana**. `TT-179` y `TT-183` deberían arrancar en la primera semana.

**3. `TT-162` puede no tener respuesta limpia.** Los valores de referencia de la autoridad sanitaria colombiana pueden no existir en la forma que la historia asume. Si no se encuentran, hay que decirlo y declarar qué se usó en su lugar, no inventar una cifra: `HU-32` exige que la fuente sea citable.

**4. `INV-9` se rompe con un corte de Pull Request mal puesto.** Ver el aviso de `HU-34`. Publicar recomendaciones sin el descargo, aunque sea entre dos PR, incumple la invariante y toca lo único del proyecto con implicación legal directa (`ALC-OUT-20`).

**5. Un defecto del backlog que conviene corregir.** La línea de reparto de `[S5]` de `./backlog-historias-de-usuario.md` dice «18 + 14 + **12** + 5 + 10 = **59** historias». El Sprint 3 tiene **14** desde que se le añadieron `HU-60` y `HU-61`, y el total es **61**. La cifra no se actualizó al añadirlas. No bloquea nada, pero es la línea que alguien citará en la sustentación.

---

## [ANEXO B] Nota de procedencia

Documento producido por el equipo el 2026-09-19, al cerrar el Sprint 4.

Las 24 tareas de `[S4]` se derivaron de las 10 historias del Sprint 5 de `[S5]` de `./backlog-historias-de-usuario.md`, contrastadas contra el código construido. Las 6 de `[S5]` se derivaron de los entregables `ENT-03` … `ENT-07` de `[S9.3]` de `./smartfood.md`, que ningún sprint había planificado; cada una declara a cuál corresponde. Las 3 de gestión no provienen de ninguna historia.

La serie `TT-` continúa: este sprint va de `TT-155` a `TT-187`.

**Ninguna tarea introduce alcance.** Las de `[S5]` no amplían el proyecto: recogen entregables que el anteproyecto declaró desde el principio y que hasta ahora no tenían plan.

---

## [ANEXO C] Verificación del orden de construcción

| Comprobación | Resultado |
|---|---|
| Tareas colocadas | 33 de 33, ninguna repetida |
| Tareas situadas antes de algo que las bloquea | **0** |

### Dependencias dentro del sprint

| Tarea | Necesita | De |
|---|---|---|
| `TT-159` Motor de reglas | `TT-155` App `reportes`, `TT-158` Reglas | `HU-30`, `HU-31` |
| `TT-160` Alertas en pantalla | `TT-159`, `TT-156` | `HU-31`, `HU-30` |
| `TT-161` Aviso orientativo | `TT-160` Alertas | `HU-31` |
| `TT-163` Cálculo nutricional | `TT-155`, `TT-162` Referencia | `HU-30`, `HU-32` |
| `TT-164` Comparación en pantalla | `TT-163`, `TT-156` | `HU-32`, `HU-30` |
| `TT-165` Gasto frente a recargas | `TT-155` App `reportes` | `HU-30` |
| `TT-172` Servicio de cierre | `TT-171` Modelo de cierre | `HU-55` |
| `TT-175` Selector de cierres | `TT-171` Modelo de cierre | `HU-55` |
| `TT-177` Auditoría | `TT-167`, `TT-169`, `TT-175` | `HU-35`, `HU-36`, `HU-56` |
| `TT-183` Informe final | `TT-179`, `TT-180`, `TT-181`, `TT-182` | `[S5]` |
| `TT-184` Sustentación | `TT-183` Informe final | `[S5]` |

### Dependencias con sprints anteriores

| Necesita | De |
|---|---|
| `TT-155` Historial con nutricional congelada | `TT-84` Instantánea en la línea de venta (S2) |
| `TT-165` Gasto frente a recargas | `TT-59`, `TT-60` Billetera y recarga (S2) |
| `TT-167` Reporte de ventas | `TT-80`, `TT-88` Venta y venta genérica (S2) |
| `TT-169` Reporte de inventario | `TT-67` Libro de inventario (S2), `TT-138` Merma (S4) |
| `TT-172` Efectivo esperado | `TT-54` Medio de pago en toda venta (S2) |
| `TT-179` Plan de pruebas | `TST-1` … `TST-4`, cerrados en los Sprints 2, 3 y 4 |

### Trabajo en paralelo

**Trece raíces** sin dependencia dentro del sprint: diez técnicas —`TT-155`, `TT-158`, `TT-162`, `TT-167`, `TT-169`, `TT-171`, `TT-179`, `TT-180`, `TT-181` y `TT-182`— más las tres de gestión.

Es el sprint con más frentes independientes de los cinco: los reportes de la cafetería (`TT-167`, `TT-169`), el cierre de caja (`TT-171`) y todo el cierre del proyecto (`[S5]`) no se tocan entre sí hasta `TT-177` y `TT-183`.
