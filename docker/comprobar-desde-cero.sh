#!/usr/bin/env bash
# Levanta el stack desde cero en otra máquina «de mentira» y comprueba que sirve
# (`[S5.3]` de docs/desarrollo.md, DT-37, DT-39).
#
# Es lo que hacía el trabajo `pruebas` de la CI hasta que DT-39 lo retiró: aquí
# se corre a mano, **cuando el cambio toca la infraestructura**, antes de subir.
# Sin `.env`, sin imágenes de proyecto y sin volúmenes: si no levanta aquí, no
# levanta en la máquina del siguiente.
#
# Se ejecuta desde la raíz del repositorio y con tu stack apagado —usan los
# mismos puertos—:
#
#   docker compose down                 # libera los puertos; conserva tus datos
#   docker/comprobar-desde-cero.sh
#   docker compose up -d                # vuelve a lo tuyo
#
# **Tu base no se toca**: trabaja sobre una copia del árbol —con lo que no has
# commiteado— y con otro nombre de proyecto, que da volúmenes nuevos y los borra
# al terminar. Tarda unos seis minutos.
set -euo pipefail

PROYECTO="${COMPOSE_PROJECT_NAME:-smartfood-limpio}"
# Al terminar se borran los volúmenes del proyecto. Con el nombre de tu stack,
# eso sería tu base de trabajo.
if [[ "$PROYECTO" == "smartfood" ]]; then
  echo "Me niego: con COMPOSE_PROJECT_NAME=smartfood borraría tu base al terminar." >&2
  exit 2
fi
export COMPOSE_PROJECT_NAME="$PROYECTO"

if ! git rev-parse --show-toplevel >/dev/null 2>&1 || [[ "$(git rev-parse --show-toplevel)" != "$PWD" ]]; then
  echo "Ejecútalo desde la raíz del repositorio." >&2
  exit 2
fi

if curl --silent --output /dev/null --max-time 2 http://localhost:8000/salud/; then
  echo "El puerto 8000 está ocupado: apaga antes tu stack con «docker compose down»." >&2
  exit 2
fi

COPIA="$(mktemp -d)"
git ls-files -co --exclude-standard -z | rsync -a --from0 --files-from=- ./ "$COPIA/"
cd "$COPIA"

FALLO=1
terminar() {
  if [[ "$FALLO" != 0 ]]; then
    echo -e "\n==== Registros"
    docker compose logs --no-color || true
  fi
  echo -e "\n==== Apagar"
  docker compose down --volumes || true
  rm -rf "$COPIA"
  echo -e "\nRESULTADO: $([[ "$FALLO" == 0 ]] && echo VERDE || echo FALLO)"
}
trap terminar EXIT

paso() { echo -e "\n==== $*"; }

# Un compañero puede tener un Compose viejo. Una clave que solo conoce una
# versión nueva hace que las viejas rechacen el fichero ENTERO al validarlo
# —pasó con `build.provenance`—, así que se valida con la mínima declarada.
paso "Validar compose.yaml con el Compose mínimo (v2.20.3)"
docker compose version
MINIMO="${XDG_CACHE_HOME:-$HOME/.cache}/smartfood/compose-2.20.3"
if [[ ! -x "$MINIMO" ]]; then
  mkdir -p "$(dirname "$MINIMO")"
  curl --fail --silent --show-error --location --output "$MINIMO" \
    https://github.com/docker/compose/releases/download/v2.20.3/docker-compose-linux-x86_64
  chmod +x "$MINIMO"
fi
"$MINIMO" config --quiet

# Lo que «desde cero» en tu máquina no ve: `down --volumes` no borra imágenes, y
# una que ya no existe en el registro sigue levantando aquí porque la tienes en
# caché. Así cayó MinIO (DT-38). Se pregunta al registro por cada imagen que no
# se construye en local; la de la aplicación se construye, y no está en ninguno.
paso "Comprobar que cada imagen existe en el registro, no solo en tu caché"
docker compose config --format json \
  | python3 -c 'import json, sys; s = json.load(sys.stdin)["services"]; print("\n".join(sorted({v["image"] for v in s.values() if "image" in v and "build" not in v and v.get("pull_policy") != "never"})))' \
  | while read -r imagen; do
      if ! docker manifest inspect "$imagen" >/dev/null; then
        echo "No existe en el registro: $imagen" >&2
        exit 1
      fi
      echo "en el registro: $imagen"
    done

paso "docker compose up"
# El contenedor escribe en el árbol como el usuario del host.
GID="$(id -g)"
export UID GID
docker compose up --detach --wait --wait-timeout 420

paso "Comprobar que sirve"
curl --fail --silent --show-error http://localhost:8000/salud/
echo
curl --fail --silent --show-error --output /dev/null http://localhost:8000/login/
# Las dos hojas compiladas: sin ellas la aplicación responde 200 y sale sin
# estilos, que es el fallo que no se ve en un código de estado.
curl --fail --silent --show-error --output /dev/null http://localhost:8000/static/css/tailwind.css
curl --fail --silent --show-error --output /dev/null http://localhost:8000/static/css/admin.css

paso "Comprobar que sembró y que las fotografías se abren solo firmadas"
URL="$(docker compose exec -T app python manage.py shell -c \
  'from personas.models import Estudiante; print(Estudiante.objects.exclude(foto_clave="").first().url_de_la_foto)' \
  | tail -n 1)"
echo "${URL%%\?*}"
curl --fail --silent --show-error --output /dev/null "$URL"
# Y sin firma, no: el bucket es privado (DT-18, DT-21, DEC-8).
SIN_FIRMA="$(curl --silent --output /dev/null --write-out '%{http_code}' "${URL%%\?*}")"
echo "sin firma: $SIN_FIRMA"
test "$SIN_FIRMA" = 403

# El correo de verdad, hasta Mailpit (DEC-18): la recuperación pedida por la
# pantalla como la pediría un usuario (HU-62), y la invitación que la carga
# masiva envía a cada acudiente (HU-03).
paso "Comprobar que el correo llega a Mailpit"
B=http://localhost:8000
SESION="$(mktemp)"
token() { grep -o 'name="csrfmiddlewaretoken" value="[^"]*"' | head -1 | sed 's/.*value="//;s/"$//'; }
TOKEN="$(curl --silent --cookie-jar "$SESION" --cookie "$SESION" "$B/recuperar/" | token)"
curl --fail --silent --show-error --output /dev/null \
  --cookie-jar "$SESION" --cookie "$SESION" --header "Referer: $B/recuperar/" \
  --data-urlencode "csrfmiddlewaretoken=$TOKEN" \
  --data-urlencode "email=institucion@example.com" "$B/recuperar/"
rm -f "$SESION"

docker compose exec -T app python manage.py shell <<'PY'
from django.core.files.uploadedfile import SimpleUploadedFile
from cuentas.models import Rol, Usuario
from personas.services import cargar_estudiantes_y_acudientes
csv = (
    "documento_estudiante,nombre_estudiante,documento_acudiente,nombre_acudiente,correo_acudiente\n"
    "9990000001,Estudiante De Prueba,99900001,Acudiente De Prueba,acudiente.prueba@example.com\n"
)
actor = Usuario.objects.get(rol=Rol.INSTITUCION)
print(cargar_estudiantes_y_acudientes(
    actor=actor, archivo=SimpleUploadedFile("prueba.csv", csv.encode(), content_type="text/csv")))
PY

for destinatario in institucion@example.com acudiente.prueba@example.com; do
  N="$(curl --fail --silent "http://localhost:8025/api/v1/search?query=to:$destinatario" \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["messages_count"])')"
  echo "Mailpit, a $destinatario: $N"
  test "$N" = 1
done

paso "manage.py check"
docker compose exec -T app python manage.py check

paso "Sin cambios de modelo sin migrar (DoD-3)"
docker compose exec -T app python manage.py makemigrations --check --dry-run

# Sin etiquetas: la suite entera, descubierta en el momento. `--noinput` porque
# sin él una base de pruebas huérfana lo cuelga.
paso "Suite completa"
docker compose exec -T app python manage.py test --noinput

FALLO=0
