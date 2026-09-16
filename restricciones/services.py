"""Escrituras del control parental (`TT-95`, `TT-98`, `TT-101`, `HU-09` … `HU-11`).

**Toda escritura pasa por aquí** (`DT-15`). Reglas que no se negocian:

1. Una vista nunca escribe directamente: llama a una función de este módulo.
2. Cada función abre su propia `transaction.atomic()`.
3. Estas funciones **no saben de HTTP**: reciben `actor` como argumento y lanzan
   `PermissionDenied` si no procede; nunca leen `request.user`.

═══════════════════════════════════════════════════════════════════════════
**AQUÍ EMPIEZA `INV-4`, Y CONVIENE DECIR DÓNDE ACABA.**

La invariante dice que las restricciones no las desactiva la cafetería. Este
módulo pone la primera mitad: el servicio exige que quien escribe sea el
acudiente **de ese estudiante**, entre por donde entre. La segunda mitad son los
permisos de `[S11]` en la capa de datos, y los cierra `TT-107` (`PR-05`).

No basta con esto solo, y no conviene creer que sí: un servicio protege el
camino que pasa por él. Lo que impide que aparezca un segundo camino es que el
permiso no exista (`DT-11`).
═══════════════════════════════════════════════════════════════════════════
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from cuentas.models import Rol
from restricciones.models import (
    LimiteDiario,
    RestriccionAlergeno,
    RestriccionProducto,
)

# Tope de un límite diario. **No es una regla de negocio disfrazada**: ninguna
# historia fija un máximo, y un límite altísimo es indistinguible de no tener
# ninguno, que es una opción legítima y gratuita —basta con no configurarlo—.
#
# Existe por algo más prosaico: `monto` es `DecimalField(max_digits=10)`, así
# que por encima de ocho enteros la base contesta `NumericValueOutOfRange`, que
# es un error de Postgres y no una frase que un acudiente pueda leer. El tope
# convierte ese fallo en un mensaje, y de paso frena el cero de más de un dedo
# torpe en un teléfono, que es desde donde entra `INT-1`.
MONTO_MAXIMO = Decimal("1000000.00")


def _comprobar_que_es_su_acudiente(actor, estudiante, accion, historia):
    """**La única puerta de escritura del control parental.** Es `INV-4`.

    Segundo criterio de `HU-09` y regla de `HU-10` y `HU-11`: quien escribe una
    restricción es el acudiente, y no cualquiera: **el de ese estudiante**.
    `[S11]` da «fijar límite diario» y «configurar y retirar restricciones
    alimentarias» únicamente a `USR-2`, así que ni el cajero, ni la
    administración de la cafetería, ni la institución educativa pasan de aquí.
    No es un olvido: es la matriz.

    **Una sola puerta para las tres restricciones, y ese es el nivel correcto.**
    `INV-4` no dice «el límite no lo toca la cafetería»: dice que no toca las
    restricciones, en plural. Con una comprobación por servicio, la tercera se
    escribe distinta el día que alguien tenga prisa. `accion` e `historia` solo
    cambian la frase del error; la regla es la misma para todas.

    Vive en el servicio y no en la vista porque `DT-15` no admite reglas que
    dependan de por dónde se entre: el admin también es una vista.

    **No se comparte con `billetera.services`, que hace este mismo control sobre
    la recarga, y es deliberado.** Compartirlo obligaría a que `restricciones`
    importara de `billetera` —dos dominios que no se tocan—. Lo que tienen en
    común no es la implementación, son tres filas de `[S11]`; el día que una de
    ellas cambie, la otra no tiene por qué seguirla.
    """
    if actor is None or not actor.is_authenticated:
        raise PermissionDenied(f"{accion} exige una cuenta identificada.")
    if actor.rol != Rol.ACUDIENTE:
        raise PermissionDenied(
            f"{accion} es función exclusiva del acudiente ({historia}, INV-4, [S11])."
        )
    if not actor.is_active:
        raise PermissionDenied("Una cuenta desactivada no opera (HU-42).")

    # El vínculo se comprueba contra la base, no contra lo que traiga la
    # petición: es la misma regla que sostiene `estudiantes_a_cargo` (`DT-11`).
    if not hasattr(actor, "acudiente") or estudiante.acudiente_id != actor.acudiente.id:
        raise PermissionDenied(
            f"{accion} solo vale sobre un estudiante a cargo ({historia}, [S11])."
        )


def _monto_valido(monto):
    """El monto, normalizado, o `ValidationError` con una frase que se entienda."""
    try:
        monto = Decimal(monto)
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("El límite diario tiene que ser una cifra.") from None

    if not monto.is_finite():
        raise ValidationError("El límite diario tiene que ser una cifra.")
    if monto <= 0:
        raise ValidationError(
            "Un límite diario de cero no es un límite: es no poder comprar nada. "
            "Si no quieres límite, retíralo en lugar de ponerlo a cero."
        )
    if monto > MONTO_MAXIMO:
        raise ValidationError(f"El límite diario máximo es {MONTO_MAXIMO:.0f}.")
    # Dos decimales, ni uno más. Sin esto, un tercer decimal entra y la base lo
    # redondea en silencio: la pantalla diría una cifra y el cupo sería otra.
    if monto != monto.quantize(Decimal("0.01")):
        raise ValidationError("El límite admite como mucho dos decimales.")

    return monto


@transaction.atomic
def fijar_limite_diario(*, actor, estudiante, monto):
    """Fija o modifica el límite diario de un estudiante (`TT-95`, `HU-09`).

    Devuelve el `LimiteDiario` vigente tras la operación.

    **Fijar y modificar son la misma operación**, y por eso hay una función y no
    dos. Lo que el acudiente hace es declarar cuál es el cupo de hoy en adelante;
    que antes hubiera otro número o ninguno no cambia ni quién puede hacerlo ni
    qué queda escrito. Dos servicios habrían obligado a la pantalla a preguntar
    primero si existía fila, que es una pregunta sobre la base y no sobre lo que
    el acudiente quiere.

    `update_or_create` dentro de la transacción cierra la carrera entre dos
    envíos simultáneos del mismo formulario; el `OneToOneField` la cierra del
    todo por si acaso.

    ── NO COMPRUEBA `INVD-2`, Y ES UNA DECISIÓN ────────────────────────────
    Un estudiante desactivado o de baja no compra ni recarga (`INVD-2`), y
    `billetera.services.asentar` lo exige antes de mover un peso. Aquí no se
    exige: configurar un cupo no mueve dinero ni existencias, no puede dejar un
    saldo negativo y no tiene efecto hasta que haya una venta — que es justo lo
    que `INVD-2` ya impide. Bloquearlo obligaría al acudiente de un estudiante
    reactivado a recordar que tiene que volver a configurarlo todo, y le quitaría
    protección al hijo en el momento de volver.
    ─────────────────────────────────────────────────────────────────────────

    **El límite no se aplica todavía en la venta.** La comparación contra el
    consumo del día —tercer criterio de `HU-09` y razón de ser de `HU-20`— la
    construye `TT-116` dentro del bloqueo de `registrar_venta` (`PR-09`, `DT-6`).
    Hasta entonces esto guarda una cifra que nadie consulta al cobrar, y las
    pantallas lo dicen: prometerle al acudiente una protección que aún no existe
    sería peor que no ofrecerle el campo.
    """
    _comprobar_que_es_su_acudiente(
        actor, estudiante, "Fijar el límite diario de gasto", "HU-09"
    )

    monto = _monto_valido(monto)

    limite, _ = LimiteDiario.objects.update_or_create(
        estudiante=estudiante, defaults={"monto": monto}
    )
    return limite


@transaction.atomic
def bloquear_producto(*, actor, estudiante, producto):
    """Impide que el estudiante compre ese producto (`TT-98`, `HU-10`).

    Devuelve la `RestriccionProducto` vigente tras la operación.

    Primer criterio de `HU-10`: **el bloqueo aplica a un producto identificado
    del catálogo**. Por eso recibe un `Producto` y no un nombre ni un texto: lo
    que queda escrito es una clave ajena, y un producto renombrado mañana sigue
    bloqueado.

    ── ES IDEMPOTENTE, Y NO ES PEREZA ──────────────────────────────────────
    Bloquear lo ya bloqueado devuelve la restricción que había, sin error. La
    pantalla de `TT-99` es un interruptor por producto, y en un teléfono —que es
    desde donde entra `INT-1`— el doble toque es lo normal, no la excepción. Un
    error aquí obligaría a la vista a preguntar antes si ya estaba, que es una
    pregunta sobre la base y no sobre lo que el acudiente quiere.

    Lo que impide de verdad la fila duplicada es la `UniqueConstraint`; esto
    solo evita que el camino normal choque contra ella (`DT-15`).
    ─────────────────────────────────────────────────────────────────────────

    **No comprueba `INVD-2`**, por lo mismo que `fijar_limite_diario`:
    configurar una restricción no mueve dinero ni existencias, y no tiene efecto
    hasta que haya una venta, que es lo que esa invariante ya impide.

    **Se puede bloquear un producto retirado del catálogo** (`activo=False`).
    Parece inútil y no lo es: un producto retirado puede volver, y lo que la
    familia declaró sobre él no debería evaporarse entre tanto. La pantalla no
    los ofrece; el servicio no los prohíbe.
    """
    _comprobar_que_es_su_acudiente(
        actor, estudiante, "Bloquear un producto", "HU-10"
    )

    restriccion, _ = RestriccionProducto.objects.get_or_create(
        estudiante=estudiante, producto=producto
    )
    return restriccion


@transaction.atomic
def desbloquear_producto(*, actor, estudiante, producto):
    """Retira el bloqueo de ese producto (`TT-98`, `HU-10`).

    Devuelve `True` si había un bloqueo y se retiró, `False` si no lo había.

    Idempotente como su pareja, y por el mismo motivo: el interruptor de
    `TT-99`. Desbloquear lo que no estaba bloqueado no es un error, es el estado
    que se pedía.

    ═══════════════════════════════════════════════════════════════════════
    **EL RETIRO TODAVÍA NO DEJA ASIENTO, Y ESO ES UNA DEUDA DECLARADA.**

    El segundo criterio de `HU-12` exige que retirar una restricción quede
    asentado, por ser una acción auditable sobre la seguridad alimentaria de un
    menor. Aquí se borra la fila y no queda constancia de que existió.

    Lo construye `TT-104`, en `PR-04`, que es donde el plan del sprint puso la
    historia del retiro. Hasta entonces hay una ventana en la que un desbloqueo
    no se puede reconstruir. **No es un olvido: es el reparto del sprint**, y se
    escribe aquí para que quien llegue a `TT-104` sepa que este es el sitio.
    ═══════════════════════════════════════════════════════════════════════
    """
    _comprobar_que_es_su_acudiente(
        actor, estudiante, "Retirar el bloqueo de un producto", "HU-10"
    )

    borradas, _ = RestriccionProducto.objects.filter(
        estudiante=estudiante, producto=producto
    ).delete()
    return borradas > 0


@transaction.atomic
def bloquear_alergeno(*, actor, estudiante, alergeno):
    """Bloquea un alérgeno completo para el estudiante (`TT-101`, `HU-11`).

    Devuelve la `RestriccionAlergeno` vigente tras la operación.

    ═══════════════════════════════════════════════════════════════════════
    **LO QUE ESTE SERVICIO NO HACE ES LA MITAD DE `INV-5`.**

    No recorre el catálogo. No crea una `RestriccionProducto` por cada producto
    que hoy declara ese alérgeno. No guarda ninguna lista en ninguna parte.
    Escribe **una fila con dos claves ajenas** y nada más.

    Si algún día alguien añade aquí un bucle que materialice los productos
    —porque así la venta consulta más rápido—, `INV-5` queda rota en ese mismo
    commit y ninguna prueba de las que miran productos existentes lo notará. La
    que sí lo nota es `TT-103`, que crea el producto **después**.
    ═══════════════════════════════════════════════════════════════════════

    Idempotente, como sus dos hermanas: la pantalla de `TT-102` es un
    interruptor y el doble toque en un teléfono es lo normal. Lo que impide la
    fila duplicada es la `UniqueConstraint`.

    **Se puede bloquear un alérgeno que hoy no declara ningún producto**, y es
    deliberado: el acudiente declara la alergia de su hijo, no el menú de la
    cafetería. El día que entre un producto con esa condición, ya está cubierto
    — que es exactamente lo que la historia pide.
    """
    _comprobar_que_es_su_acudiente(
        actor, estudiante, "Bloquear un alérgeno", "HU-11"
    )

    restriccion, _ = RestriccionAlergeno.objects.get_or_create(
        estudiante=estudiante, alergeno=alergeno
    )
    return restriccion


@transaction.atomic
def desbloquear_alergeno(*, actor, estudiante, alergeno):
    """Retira el bloqueo de ese alérgeno (`TT-101`, `HU-11`).

    Devuelve `True` si había un bloqueo y se retiró, `False` si no lo había.

    Borra **una fila**. Como no hay lista materializada que deshacer, no hay
    forma de que el retiro deje productos bloqueados por error: lo que se
    consulta vuelve a calcularse desde cero en la siguiente pregunta (`INV-5`).

    **El retiro todavía no deja asiento**, igual que el de producto: el segundo
    criterio de `HU-12` lo exige y lo construye `TT-104`, en `PR-04`.
    """
    _comprobar_que_es_su_acudiente(
        actor, estudiante, "Retirar el bloqueo de un alérgeno", "HU-11"
    )

    borradas, _ = RestriccionAlergeno.objects.filter(
        estudiante=estudiante, alergeno=alergeno
    ).delete()
    return borradas > 0
