"""Almacenamiento S3 que firma con la dirección que ve el navegador (`DT-37`).

Vive en `config/` porque es infraestructura, como `config/imagenes.py`: lo usan
`personas` y `catalogo` a través de los alias de `STORAGES` y ninguna lo posee.

**El problema que resuelve.** Con la aplicación dentro de un contenedor, Django
llega a MinIO por la red de `compose.yaml` —`http://minio:9000`— y el navegador
por el puerto publicado —`http://localhost:9000`—. Son dos direcciones del
mismo servicio, y la firma de una URL prefirmada **incluye el host**: firmada
contra `minio:9000`, el navegador no resuelve el nombre; reescrita después a
`localhost:9000`, MinIO la rechaza porque la firma ya no cuadra.

La salida es firmar directamente contra la dirección pública. Prefirmar no abre
ninguna conexión —es un cálculo local con la clave—, así que el cliente de firma
no necesita alcanzar esa dirección desde dentro del contenedor.

**Todo lo demás sigue por la dirección interna**: subir, borrar, leer. Solo
`url()`, que es lo único que se entrega al navegador, cambia de host.

`django-storages` no lo trae: `custom_domain` cambia el host pero **desactiva
la firma** (solo firma con CloudFront), y la fotografía de un menor no puede
salir sin firma (`DEC-8`, `DT-18`).
"""

from storages.backends.s3 import S3Storage
from storages.utils import clean_name


class AlmacenamientoS3(S3Storage):
    """`S3Storage` con un `endpoint_url_publico` opcional para las URL firmadas.

    Sin él —la aplicación en el host, o las pruebas—, se comporta exactamente
    como `S3Storage`: el navegador y Django ven MinIO en la misma dirección.
    """

    def get_default_settings(self):
        return {**super().get_default_settings(), "endpoint_url_publico": ""}

    def __getstate__(self):
        # Un cliente de boto3 no se serializa; se vuelve a crear al usarlo.
        estado = super().__getstate__()
        estado.pop("_cliente_de_firma", None)
        return estado

    @property
    def cliente_de_firma(self):
        """Cliente contra la dirección pública. Los clientes de boto3 son
        seguros entre hilos —los recursos no—, así que basta uno por instancia."""
        cliente = getattr(self, "_cliente_de_firma", None)
        if cliente is None:
            cliente = self._create_session().client(
                "s3",
                region_name=self.region_name,
                use_ssl=self.use_ssl,
                endpoint_url=self.endpoint_url_publico,
                config=self.client_config,
                verify=self.verify,
            )
            self._cliente_de_firma = cliente
        return cliente

    def url(self, name, parameters=None, expire=None, http_method=None):
        if not self.endpoint_url_publico or not self.querystring_auth:
            return super().url(name, parameters, expire, http_method)

        params = parameters.copy() if parameters else {}
        params["Bucket"] = self.bucket_name
        params["Key"] = self._normalize_name(clean_name(name))
        return self.cliente_de_firma.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=self.querystring_expire if expire is None else expire,
            HttpMethod=http_method,
        )
