# SmartFood — Cómo se escriben las pruebas

## [S0] Bloque de control del documento

| Campo | Valor |
|---|---|
| doc_id | SMARTFOOD-TIC1-PRUEBAS |
| titulo | Dónde va una prueba, cómo se ejecuta y los patrones que ya costaron una ronda |
| tipo_documento | **Documento operativo.** Convención de trabajo; no es el plan de pruebas de `ENT-05` |
| documentos_fuente | `../CLAUDE.md`, de donde sale; `./definicion-de-terminado.md` (`DoD-5`); `./trampas-del-stack.md` (`[S4]`); `./decisiones-tecnicas.md` (`DT-37`) |
| actualizado | 2026-10-01 |
| idioma | es-CO |
| version | 1.0 |

**Léelo antes de escribir o tocar una prueba.** Recoge dónde va, cómo se ejecuta y
**siete patrones** que el proyecto aprendió a fuerza de pruebas que pasaban sin probar nada,
o que fallaban por un motivo que no era el suyo.

Salió de `CLAUDE.md` el 2026-10-01: con el producto terminado se escriben pocas pruebas
nuevas, y estas reglas solo hacen falta al escribir una. Allí queda la regla que aplica
siempre —`[S2]`— y un puntero hasta aquí.

**No es el plan de pruebas.** Qué se prueba y con qué escenarios críticos (`TST-1` …
`TST-4`) es `ENT-05`; esto es **cómo** se escribe cualquier prueba del proyecto.

---

## [S1] Dónde va y cómo se ejecuta

**Una prueba va en `<app>/tests_<tema>.py`**, en una carpeta con `__init__.py`. Es lo único
que la hace entrar en la suite: `manage.py test` va sin argumentos y el
descubridor solo encuentra ficheros `test*.py` dentro de paquetes. **Una prueba con otro
nombre, o en una carpeta sin `__init__.py`, no se ejecuta nunca y nada avisa**: la suite
sale en verde con una prueba menos. Lo vigila `config/tests_descubrimiento.py`.

```bash
docker compose exec -T app python manage.py test --noinput            # la suite entera
docker compose exec -T app python manage.py test cuentas.tests_acceso --noinput
```

- **`--noinput` siempre**: sin él, una base de pruebas huérfana de una ejecución
  interrumpida deja el comando esperando una respuesta que nadie escribe.
- **La suite tarda entre tres y seis minutos**, por encima del tiempo de espera por defecto
  de muchas herramientas. Si se corta a los 120 s, no falló: no le dio tiempo.
- **Una prueba que falla con `assertContains` vuelca la página entera.** Filtra la salida
  con `grep -E '^(FAIL|ERROR):|^Ran|^OK|FAILED'` y abre el detalle solo de la que falle.
- **En el host, en un clon recién hecho, hace falta antes un `collectstatic`**: el ejecutor
  fuerza `DEBUG=False` y sin manifiesto salen 285 errores. El arranque del contenedor ya lo
  hace (`[S4]` de `./trampas-del-stack.md`).

**La CI no corre la suite** (`DT-39`): se corre aquí, antes de cada `push` a `main`, y nadie la repite
después. La versión se publica igual, pase o no (`[S3.0]` de `./convenciones-de-git.md`).

---

## [S2] La regla que aplica siempre: rompe lo que proteges

**Antes de afirmar `DoD-5`, introduce la violación a propósito y comprueba que la prueba
falla.** Una prueba que exige una ausencia —«ningún rol escribe aquí», «no existe tal
servicio»— pasa sola el día que deja de proteger.

**Y ponle contraprueba a toda prueba de ausencia**: que la misma búsqueda sí encuentre lo
que sí está. Sin ella, una expresión mal escrita que no encuentra nada pasa por una
garantía. `config/tests_contenedor.py` y `config/tests_descubrimiento.py` empiezan por la
suya.

---

## [S3] Siete patrones

### [S3.1] El correo sale al confirmar la transacción

**Todo lo que manda correo —crear cuentas, la carga masiva, la recuperación de
contraseña— lo difiere con `transaction.on_commit`** (`config/correo.py`). Una prueba que
mire `mail.outbox` sin envolverse en `self.captureOnCommitCallbacks(execute=True)` verá la
bandeja vacía y parecerá que no se envió.

Eso mismo sirve para probar lo que importa del diferido: **una operación que se revierte no
envía nada**. Se fuerza el fallo a mitad con `mock.patch` sobre un paso posterior y se
comprueba la bandeja vacía (`personas/tests_acudientes.py`).

**Un recorrido de extremo a extremo toma el enlace del correo que llegó**, no del
servicio que lo construye: así se prueba lo que de verdad le llega al titular.

### [S3.2] La cuenta del admin se crea por el camino real

`sincronizar_grupos_y_permisos()` y `crear_cuenta(..., accede_a_administracion=True)`.
Poner `is_staff` a mano deja una cuenta que entra pero no tiene ningún permiso, y todo
responde `403`.

### [S3.3] Una prueba de ausencia sobre el código mira el bytecode

No `inspect.getsource`: el fuente incluye el docstring, y ahí la ausencia **se explica**.
Buscar «no llama a X» encuentra la X de la explicación y la prueba pasa sola.
`inspect.unwrap(f).__code__.co_names` lista lo que la función usa de verdad. Contraprueba:
que sí encuentre lo que sí usa.

### [S3.4] La fecha se inyecta, no se lee del reloj

**Una prueba de ventana o de periodo recibe la fecha.** El selector toma `hoy=` y las filas
se fechan a mano sobre una jornada fija: si mira `timezone.now()`, falla sola una madrugada
y nadie sabe por qué. `creado_en` es `auto_now_add` —no se puede fijar al crear—: se corrige
después con `update()`.

**Una caducidad se prueba adelantando el reloj, no poniéndola a cero.** Con
`PASSWORD_RESET_TIMEOUT=0`, un token creado y comprobado en el mismo segundo sigue valiendo.
Se parchea el reloj del generador —`mock.patch.object(PasswordResetTokenGenerator, "_now",
…)`— más allá de la caducidad, y con contraprueba antes de ella
(`cuentas/tests_recuperacion.py`).

**Una prueba de pantalla también recibe la fecha, aunque la vista no se la pase.** Si la vista
llama al selector sin `hoy=`, el selector toma el reloj, y unos datos fechados sobre un `HOY`
fijo se quedan fuera de la ventana en cuanto pasan los días. Así se rompió `main` el
2026-10-02, trece días después del `HOY` de `reportes/tests_frecuencia.py`. La fecha se inyecta
en el sitio donde la vista llama al selector, no moviendo el reloj de todo el proceso:

```python
con_fecha = partial(resumen_de_gasto, hoy=HOY)
with mock.patch("reportes.views.resumen_de_gasto", con_fecha):
    respuesta = self.client.get(reverse("historial-de-consumo", args=[...]))
```

Se parchea el nombre **en el módulo de la vista**, que es donde se busca: si un día la vista
deja de usarlo, `mock.patch` falla en vez de dejar pasar una prueba que ya no prueba nada
(`reportes/tests_gasto.py`).

**Para encontrar las que quedan, se adelanta el reloj y se corre la suite.** Una prueba que
depende de la fecha real pasa hoy y falla dentro de unas semanas. Con el reloj de Django
adelantado un mes —y un año— salen ahora:

```python
real = timezone.now
delta = timedelta(days=30)
with mock.patch("django.utils.timezone.now", lambda: real() + delta):
    get_runner(settings)(interactive=False).run_tests(["reportes"])
```

Se ejecuta con `manage.py shell` o con un script que haga `django.setup()`. `timezone.localdate()`
lee de `now()`, así que el parche alcanza también a los selectores que piden la fecha.

### [S3.5] «No hay forma de pintar A sin B» se fija sobre el fragmento

`render_to_string` sobre el `partial`, con y sin datos. Si alguien separa los dos bloques en
dos plantillas, la página seguiría trayendo los dos y una prueba sobre ella pasaría igual.
Así se sostiene `INV-9`, y así falla cuando se rompe.

### [S3.6] Sobre una página entera, un `data-*` propio

**No un atributo genérico.** `assertNotContains(r, 'role="group"')` para decir «no se
dibuja el selector de estudiante» se rompe el día que el armazón estrena otro grupo —y se
rompió—. Se busca `data-selector-estudiante`, que solo existe en esa pantalla.

- **Ojo con los nombres que Tailwind usa como variante**: buscar `disabled` casa con la
  clase `disabled:opacity-50`, así que la prueba pasa con el atributo ausente.
- **Nunca sobre la copia**: `assertContains(r, "Bloquear productos")` se rompe en cuanto
  alguien mejora la redacción, en un PR que no tenía nada que ver. Se afirma sobre la URL,
  sobre `response.context` o sobre un `data-*`.

### [S3.7] Las imágenes no hablan con el almacenamiento

Las pruebas usan `override_settings(STORAGES=…)` con `InMemoryStorage`. Por eso
`foto_clave` e `imagen_clave` son `CharField` y no `FileField`: este último ata el
almacenamiento a la definición de la clase, y el `override` no le llega. La firma contra la
dirección pública se prueba sin servidor, porque prefirmar es un cálculo local
(`config/tests_almacenamiento.py`).

---

## [S4] Comprobar a mano, sin navegador

Para un flujo real —el admin, sobre todo—, `django.test.Client` por stdin dentro del
contenedor, añadiendo el host que usa el cliente:

```bash
docker compose exec -T -e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,testserver app \
  python manage.py shell <<'PY'
from django.test import Client
print(Client().get("/login/").status_code)
PY
```

**`response.context` es `None` fuera del runner de pruebas.** La puebla la señal
`template_rendered`, que solo se conecta con `django.test.utils.setup_test_environment()`.
Sin esa llamada la respuesta llega con `200`, y leerla revienta con un
`TypeError: 'NoneType' object is not subscriptable` que no menciona la causa.

---

## [S5] Lo que la suite no ve

Tres cosas pasan las 1.500 pruebas y aun así pueden estar mal. Tienen su propia forma de
comprobarse:

| Qué | Por qué la suite no lo ve | Cómo se comprueba |
|---|---|---|
| **Cómo se ve una pantalla** | Una cifra cruda o una copia en masculino no rompen nada | Mirarla: Playwright contra el stack (`[S3.1]` de `./desarrollo.md`). En los Sprints 4 y 5 encontró quince defectos que ninguna prueba vio |
| **Que un correo salga de verdad** | La suite usa el buzón en memoria de Django, no SMTP | El API de Mailpit: `curl 'localhost:8025/api/v1/search?query=to:<correo>'`. `docker/comprobar-desde-cero.sh` lo hace con la recuperación y la carga |
| **Que el stack levante en otra máquina** | La suite corre dentro de un stack que ya levantó | `docker/comprobar-desde-cero.sh`, que además pregunta al registro por cada imagen (`[S5.3]` de `./desarrollo.md`) |
