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

## Definición de Terminado `[S2]`

- [ ] Los criterios de aceptación de cada `HU-nn` se cumplen y se verificaron manualmente.
- [ ] No rompe nada de lo ya construido.
- [ ] Migraciones escritas y aplicadas en el entorno de pruebas.
- [ ] Demostrable en el entorno desplegado (`ENT-01`), no solo en local.
- [ ] Cada invariante que sostiene tiene un caso de prueba que la ejercita.
- [ ] Todos los datos son ficticios (`ALC-OUT-07`, Ley 1581 de 2012).

## Alcance

- [ ] No introduce alcance fuera de `[S9.1]` de `smartfood.md` + `[S1]` de `decisiones-de-alcance.md`.
- [ ] Respeta `DT-15`: la vista no escribe, el servicio no sabe de HTTP, la invariante la impone la base.

## Cómo se probó

<!-- Pasos concretos, o el comando de las pruebas y su salida. -->
