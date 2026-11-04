import uuid
from django.db import models

class InstalacionSucursal(models.Model):
    """Identidad técnica de la instalación; autenticación M2M pendiente."""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sucursal = models.OneToOneField('organizacion.Sucursal', on_delete=models.PROTECT, related_name='instalacion_api')
    activa = models.BooleanField(default=True)
    token_sha256 = models.CharField(max_length=64, blank=True, default='', help_text='SHA-256 de token aleatorio; nunca conservar token en claro.')
    ultima_conexion = models.DateTimeField(null=True, blank=True)
    version_contrato = models.PositiveIntegerField(default=1)

class EventoSincronizacion(models.Model):
    """Outbox transaccional; publicar después de confirmar la transacción.

    Una secuencia incremental global será asignada por el PUBLICADOR
    tras confirmar la transacción, no por el ID de inserción.
    """
    event_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo_entidad = models.CharField(max_length=50)
    tipo_operacion = models.CharField(max_length=30)
    entidad_uuid = models.UUIDField()
    version_entidad = models.PositiveBigIntegerField()
    schema_version = models.PositiveIntegerField(default=1)
    payload = models.JSONField(default=dict)
    creado_en = models.DateTimeField(auto_now_add=True)
    secuencia_publicacion = models.PositiveBigIntegerField(unique=True, null=True, blank=True)
    publicado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['secuencia_publicacion'])]

class DestinoEvento(models.Model):
    evento = models.ForeignKey(EventoSincronizacion, on_delete=models.CASCADE, related_name='destinos')
    instalacion = models.ForeignKey(InstalacionSucursal, on_delete=models.PROTECT, related_name='eventos_dirigidos')
    confirmado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['evento', 'instalacion'], name='uq_evento_instalacion')]


class ContadorPublicacion(models.Model):
    """Fila de bloqueo de publicación; serializa las secuencias de eventos.

    La fila con pk=1 se bloquea en PostgreSQL antes de publicar cada lote.
    No usar el ID de evento como cursor: los commits pueden intercalarse.
    """
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    ultimo_valor = models.PositiveBigIntegerField(default=0)
