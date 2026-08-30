<!--
El TÍTULO de este PR es el mensaje de commit que quedará en main (squash merge)
y es lo que analiza semantic-release. Formato:

    tipo(ámbito): resumen en imperativo

Si el cambio es incompatible, el `!` va AQUÍ, en el título: `feat(ámbito)!: ...`.
Un `BREAKING CHANGE:` en el cuerpo de un commit de la rama no llega a main y no
dispara la versión mayor.

Ver docs/convenciones-de-git.md
-->

## Qué entrega

<!-- Una o dos frases. Qué hace el sistema ahora que antes no hacía. -->

## Tareas y trazabilidad

| Campo | Valor |
|---|---|
| PR del plan | `PR-nn` de `docs/plan-de-pull-requests.md` |
| Tareas | `TT-nn`, `TT-nn` |
| Historias | `HU-nn` |
| Invariantes que sostiene | `INV-n` / `INVD-n` — o «ninguna» |

## Definición de Terminado

<!--
Marca la casilla solo si lo comprobaste. Si un criterio NO aplica, di POR QUÉ en su
línea; «no aplica» a secas es lo que deja pasar el caso en el que sí aplicaba.
Detalle en docs/definicion-de-terminado.md
-->

- [ ] **`DoD-1`** Cierra `HU-nn`: sus criterios de aceptación se cumplen, verificados uno a uno.
      <!-- Si no cierra historias: qué habilita, y cómo se comprueba que lo habilita. -->
- [ ] **`DoD-2`** Integrado por PR y no rompe nada de lo ya construido. *(Siempre aplica.)*
- [ ] **`DoD-3`** Migraciones escritas, aplicadas, y `makemigrations --check` sin pendientes.
      <!-- No aplica si el PR no toca modelos. Dilo. -->
- [ ] **`DoD-4`** Demostrable en `ENT-01`, no solo en local. *(Siempre aplica.)*
      <!-- Si no tiene pantalla, demuéstralo por su efecto observable allí. -->
- [ ] **`DoD-5`** Cada invariante que sostiene tiene un caso de prueba que **falla si se rompe**.
      <!-- No aplica si no sostiene ninguna. Compruébalo antes de decirlo. -->
- [ ] **`DoD-6`** Todos los datos son ficticios. *(Siempre aplica — `ALC-OUT-07`, Ley 1581 de 2012.)*

## Alcance

- [ ] No introduce alcance fuera de `[S9.1]` de `smartfood.md` + `[S1]` de `decisiones-de-alcance.md`.
- [ ] Respeta `DT-15`: la vista no escribe, el servicio no sabe de HTTP, la invariante la impone la base.

## Cómo se probó

<!-- Pasos concretos, o el comando de las pruebas y su salida. -->
