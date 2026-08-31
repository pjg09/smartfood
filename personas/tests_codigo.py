"""`TT-30` y `TT-31`. El código de tarjeta es aleatorio y no secuencial (`INV-7`).

`TT-31` pide «unicidad y no secuencialidad sobre un lote grande de códigos», y
son dos afirmaciones distintas. La unicidad es fácil de creer y fácil de probar.
La **no secuencialidad** es la que sostiene la invariante y la que se puede
romper sin que nadie lo note: una implementación que devolviera valores
correlacionados pasaría cualquier prueba de unicidad.

De ahí que estas pruebas ataquen la propiedad desde cuatro lados: que no se
repiten, que no van ordenados, que no se parecen entre sí y que no salen de un
generador predecible.

**Ninguna prueba de aquí es estadísticamente ajustada.** Todos los márgenes están
elegidos para que un fallo signifique «el generador cambió», no «hoy tuvimos mala
suerte»: la probabilidad de falso positivo de cada una está anotada donde no es
evidente. Una prueba de aleatoriedad intermitente se acaba desactivando, y
entonces `INV-7` deja de estar vigilada.
"""

import random
import uuid
from collections import Counter
from unittest import mock

from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase

from cuentas.models import Rol, Usuario
from cuentas.services import sincronizar_grupos_y_permisos
from personas.carga import COLUMNAS
from personas.codigo import ALFABETO, LONGITUD, generar_codigo_de_tarjeta
from personas.models import Acudiente, Estudiante
from personas.services import (
    cargar_estudiantes_y_acudientes,
    crear_estudiante,
    dar_de_alta_la_institucion,
)

# Suficiente para que las afirmaciones de abajo tengan margen sobrado, y bastante
# rápido: son 5.000 llamadas a `secrets.choice` por cada carácter.
LOTE = 5_000


def _lote(n=LOTE):
    return [generar_codigo_de_tarjeta() for _ in range(n)]


class FormaDelCodigoTest(SimpleTestCase):
    """Lo que el código **es**, antes de mirar cómo se distribuye."""

    def test_tiene_la_longitud_fijada(self):
        self.assertEqual(len(generar_codigo_de_tarjeta()), LONGITUD)

    def test_la_longitud_esta_dentro_del_rango_de_dt_17(self):
        self.assertGreaterEqual(LONGITUD, 12)
        self.assertLessEqual(LONGITUD, 16)

    def test_solo_usa_caracteres_del_alfabeto(self):
        for codigo in _lote(500):
            self.assertTrue(set(codigo) <= set(ALFABETO), f"«{codigo}» se sale del alfabeto")

    def test_es_imprimible_como_codigo_de_barras(self):
        """Tercer criterio de `HU-43`.

        Code 39 admite dígitos y mayúsculas sin extensiones; Code 128 los admite
        también. Un alfabeto con minúsculas o con signos obligaría a Code 128
        extendido y a una etiqueta más larga, y `INT-2` tiene una ventana de
        veinte a treinta minutos para atender la fila (`DT-17`).
        """
        imprimibles = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        self.assertTrue(set(ALFABETO) <= imprimibles)

    def test_el_alfabeto_no_tiene_caracteres_que_se_confundan(self):
        """`I`/`1` y `O`/`0` a simple vista, cuando alguien lo teclea."""
        for confuso in "ILOU":
            self.assertNotIn(confuso, ALFABETO)


class UnicidadTest(SimpleTestCase):
    """`TT-31`, primera mitad. La fácil."""

    def test_un_lote_grande_no_repite_ninguno(self):
        codigos = _lote()
        self.assertEqual(len(set(codigos)), len(codigos))

    def test_el_espacio_es_lo_bastante_grande(self):
        """Que no se repitan en 5.000 no serviría si el espacio fuera pequeño.

        Con 32 símbolos y 14 posiciones son 2^70 combinaciones. Es la cifra que
        hace que la unicidad no dependa de tener suerte.
        """
        self.assertGreater(len(ALFABETO) ** LONGITUD, 10**20)


class NoSecuencialidadTest(SimpleTestCase):
    """`TT-31`, segunda mitad, y el motivo de que `INV-7` exista."""

    def test_los_codigos_no_salen_en_orden(self):
        """Un contador, un autoincremental o un UUIDv7 saldrían ordenados.

        Probabilidad de que 5.000 valores aleatorios salgan ya ordenados:
        1 entre 5.000!, que es cero a todos los efectos.
        """
        codigos = _lote()
        self.assertNotEqual(codigos, sorted(codigos))
        self.assertNotEqual(codigos, sorted(codigos, reverse=True))

    def test_un_uuid7_habria_fallado_esta_prueba(self):
        """Por qué `DT-17` declara el código como excepción a la clave primaria.

        No prueba nuestro generador: prueba que la alternativa descartada es
        efectivamente insegura para esto. Si algún día alguien «simplifica»
        usando la misma primitiva que el resto de las tablas, aquí está escrito
        lo que pasaría.
        """
        uuids = [str(uuid.uuid7()) for _ in range(200)]
        self.assertEqual(uuids, sorted(uuids), "UUIDv7 va ordenado por construcción")

        codigos = _lote(200)
        self.assertNotEqual(codigos, sorted(codigos))

    def test_dos_codigos_consecutivos_no_comparten_prefijo(self):
        """Deducir «el siguiente» a partir del propio es el ataque de `ALC-IN-12`.

        Se exige que ningún par consecutivo comparta seis caracteres iniciales.
        Probabilidad de que uno cualquiera los comparta: 32^-6, es decir 1 entre
        mil millones; sobre 5.000 pares, del orden de 10^-6.
        """
        codigos = _lote()
        for anterior, siguiente in zip(codigos, codigos[1:]):
            comun = 0
            for a, b in zip(anterior, siguiente):
                if a != b:
                    break
                comun += 1
            self.assertLess(
                comun, 6,
                f"«{anterior}» y «{siguiente}» comparten {comun} caracteres iniciales",
            )

    def test_ninguna_posicion_se_queda_encasillada(self):
        """Cada posición tiene que moverse por todo el alfabeto.

        Un generador que fijara un prefijo, o que derivara parte del código de la
        fecha, dejaría posiciones con muy pocos valores distintos. Con 5.000
        muestras y 32 símbolos se esperan los 32 en cada posición; se exige 25,
        que da margen de sobra sin dejar pasar un prefijo constante.
        """
        codigos = _lote()
        for posicion in range(LONGITUD):
            distintos = len({codigo[posicion] for codigo in codigos})
            self.assertGreaterEqual(
                distintos, 25,
                f"la posición {posicion} solo tomó {distintos} valores distintos",
            )

    def test_ningun_simbolo_domina(self):
        """El reparto es plano: ningún símbolo aparece el doble que la media."""
        contados = Counter("".join(_lote()))
        media = (LOTE * LONGITUD) / len(ALFABETO)

        self.assertEqual(len(contados), len(ALFABETO), "algún símbolo no salió nunca")
        self.assertLess(max(contados.values()), media * 1.5)
        self.assertGreater(min(contados.values()), media * 0.5)


class ElGeneradorEsCriptograficoTest(SimpleTestCase):
    """`DT-9`. No basta con que parezca aleatorio: tiene que ser impredecible."""

    def test_sembrar_random_no_reproduce_los_codigos(self):
        """La prueba que distingue `secrets` de `random`.

        `random` es un Mersenne Twister: con la misma semilla devuelve la misma
        secuencia, y observando unos cuantos valores se reconstruye su estado y
        se predicen los siguientes. Si el generador lo usara, estas dos llamadas
        darían el mismo código.
        """
        random.seed(42)
        primero = generar_codigo_de_tarjeta()
        random.seed(42)
        segundo = generar_codigo_de_tarjeta()

        self.assertNotEqual(
            primero, segundo,
            "el generador depende de `random`, que es predecible (DT-9, INV-7)",
        )

    def test_dos_llamadas_seguidas_no_coinciden(self):
        self.assertNotEqual(generar_codigo_de_tarjeta(), generar_codigo_de_tarjeta())


# --- `TT-32`. La asignación, que ya toca la base de datos --------------------


class AsignacionDelCodigoTest(TestCase):
    """`HU-43`. El código se asigna solo, en los dos caminos de alta."""

    def setUp(self):
        sincronizar_grupos_y_permisos()
        with self.captureOnCommitCallbacks(execute=True):
            institucion, _ = dar_de_alta_la_institucion(
                nombre="Colegio de Prueba",
                email="institucion@example.com",
                contrasena_de_desarrollo="clave-de-prueba-2026",
            )
        self.actor = institucion.usuario

        usuario = Usuario.objects.crear_usuario(
            email="marta.ruiz@example.com", rol=Rol.ACUDIENTE, nombre="Marta Ruiz Ochoa"
        )
        self.acudiente = Acudiente.objects.create(
            usuario=usuario, nombre="Marta Ruiz Ochoa", documento="43512345"
        )

    def _alta(self, documento="1001234501", nombre="Ana Sofía Restrepo Ruiz"):
        return crear_estudiante(
            actor=self.actor,
            nombre=nombre,
            documento=documento,
            acudiente=self.acudiente,
        )

    # --- Primer criterio: automática en los dos caminos --------------------

    def test_el_alta_individual_asigna_el_codigo(self):
        estudiante = self._alta()

        self.assertEqual(len(estudiante.codigo_tarjeta), LONGITUD)
        self.assertTrue(set(estudiante.codigo_tarjeta) <= set(ALFABETO))

    def test_la_carga_masiva_asigna_el_codigo_a_cada_estudiante(self):
        archivo = SimpleUploadedFile(
            "estudiantes.csv",
            (
                "documento_estudiante,nombre_estudiante,documento_acudiente,"
                "nombre_acudiente,correo_acudiente\n"
                "1001234501,Ana Sofía Restrepo Ruiz,43512345,Marta Ruiz Ochoa,marta.ruiz@example.com\n"
                "1001234502,Tomás Restrepo Ruiz,43512345,Marta Ruiz Ochoa,marta.ruiz@example.com\n"
                "1001234503,Julián Ospina Vélez,71234567,Andrés Ospina Mesa,andres.ospina@example.com\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )
        with self.captureOnCommitCallbacks(execute=True):
            cargar_estudiantes_y_acudientes(actor=self.actor, archivo=archivo)

        codigos = list(Estudiante.objects.values_list("codigo_tarjeta", flat=True))
        self.assertEqual(len(codigos), 3)
        self.assertEqual(len(set(codigos)), 3, "tres estudiantes, tres códigos distintos")
        for codigo in codigos:
            self.assertEqual(len(codigo), LONGITUD)

    def test_el_codigo_no_viene_del_archivo_de_carga(self):
        """El formato acordado no tiene columna para él (`TT-22`)."""
        self.assertNotIn("codigo_tarjeta", COLUMNAS)
        self.assertNotIn("codigo", "".join(COLUMNAS))

    # --- Segundo criterio: aleatorio y no derivado -------------------------

    def test_dos_estudiantes_con_los_mismos_datos_reciben_codigos_distintos(self):
        """El código no se deriva de ningún campo del estudiante (`ALC-IN-12`)."""
        primero = self._alta(documento="1001234501", nombre="Homónima Pérez")
        segundo = self._alta(documento="1001234502", nombre="Homónima Pérez")

        self.assertNotEqual(primero.codigo_tarjeta, segundo.codigo_tarjeta)

    def test_el_codigo_no_se_deriva_del_identificador(self):
        estudiante = self._alta()
        identificador = str(estudiante.id).replace("-", "").upper()

        self.assertNotIn(estudiante.codigo_tarjeta, identificador)
        for trozo in range(0, len(identificador) - 4, 4):
            self.assertNotIn(identificador[trozo:trozo + 5], estudiante.codigo_tarjeta)

    # --- `DT-9`: índice único y reintento ----------------------------------

    def test_la_base_rechaza_dos_codigos_iguales(self):
        """La mitad de `DT-9` que impone la base, no un `if` (`DT-15`)."""
        primero = self._alta()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Estudiante.objects.create(
                    nombre="Otra Estudiante",
                    documento="1009999999",
                    acudiente=self.acudiente,
                    codigo_tarjeta=primero.codigo_tarjeta,
                )

    def test_el_alta_sortea_otro_codigo_si_el_primero_ya_existia(self):
        """La otra mitad de `DT-9`: el reintento.

        Se fuerza la colisión devolviendo un código ya usado en el primer sorteo
        y uno libre en el segundo. Sin el punto de guardado interno, la
        `IntegrityError` dejaría la transacción abortada y el alta fallaría en
        vez de reintentar.
        """
        ocupado = self._alta().codigo_tarjeta
        libre = "ZZZZZZZZZZZZZZ"

        with mock.patch(
            "personas.services.generar_codigo_de_tarjeta",
            side_effect=[ocupado, libre],
        ) as generador:
            estudiante = self._alta(documento="1001234502", nombre="Tomás Restrepo Ruiz")

        self.assertEqual(generador.call_count, 2)
        self.assertEqual(estudiante.codigo_tarjeta, libre)

    def test_un_choque_que_no_es_del_codigo_no_se_reintenta(self):
        """Un documento repetido no se arregla sorteando otro código."""
        self._alta(documento="1001234501")

        with mock.patch(
            "personas.services.generar_codigo_de_tarjeta",
            wraps=generar_codigo_de_tarjeta,
        ) as generador:
            with self.assertRaises(IntegrityError):
                self._alta(documento="1001234501", nombre="Documento Repetido")

        self.assertEqual(
            generador.call_count, 1,
            "se reintentó un choque que no era de código: cinco intentos en balde",
        )

    def test_se_rinde_con_un_mensaje_util_si_el_generador_esta_roto(self):
        """Cinco colisiones seguidas no ocurren por azar: ocurren por un fallo."""
        ocupado = self._alta().codigo_tarjeta

        with mock.patch(
            "personas.services.generar_codigo_de_tarjeta", return_value=ocupado
        ):
            with self.assertRaises(RuntimeError) as ctx:
                self._alta(documento="1001234502")

        self.assertIn("INV-7", str(ctx.exception))

    # --- Primer criterio de `HU-14`: lo genera el sistema, no una persona ---

    def test_el_campo_no_es_editable_en_ningun_formulario(self):
        campo = Estudiante._meta.get_field("codigo_tarjeta")
        self.assertFalse(
            campo.editable,
            "un campo editable acaba en un formulario del admin y HU-14 dice "
            "que el código lo genera el sistema, no una persona",
        )

    def test_la_base_rechaza_un_codigo_con_forma_invalida(self):
        """La restricción de forma, que sostiene el tercer criterio de `HU-43`."""
        # Todos de 14 caracteres salvo el primero, que es el caso de longitud.
        for invalido in ["corto", "minusculasminu", "CON-GUION-1234", "IIIIIIIIIIIIII"]:
            with self.subTest(codigo=invalido):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        Estudiante.objects.create(
                            nombre="Código A Mano",
                            documento=f"100{invalido[:7]}",
                            acudiente=self.acudiente,
                            codigo_tarjeta=invalido,
                        )

    # --- Quién puede matricular -------------------------------------------

    def test_solo_la_institucion_matricula(self):
        cajero = Usuario.objects.crear_usuario(
            email="cajero@example.com", rol=Rol.CAJERO, is_staff=True
        )
        with self.assertRaises(PermissionDenied):
            crear_estudiante(
                actor=cajero,
                nombre="Ana Sofía Restrepo Ruiz",
                documento="1001234501",
                acudiente=self.acudiente,
            )
