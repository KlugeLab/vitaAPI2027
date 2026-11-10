"""Organización y catálogos postales nacionales administrados por SCentralAPI.

Los campos opcionales de Sucursal son deliberados para preservar sucursales
creadas en Etapa 4. El serializer exige datos completos en nuevas altas.
"""
import uuid
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q

rfc_formato = RegexValidator(
    regex=r'^(?:[A-ZÑ&]{3}[0-9]{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12][0-9]|3[01])[A-Z0-9]{3}|[A-ZÑ&]{4}[0-9]{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12][0-9]|3[01])[A-Z0-9]{3})$',
    message='RFC mexicano con formato inválido (12 caracteres moral o 13 física).',
)

class Estado(models.Model):
    clave = models.CharField(primary_key=True, max_length=2)
    nombre = models.CharField(max_length=100, unique=True)
    class Meta:
        ordering = ['nombre']
    def __str__(self): return self.nombre

class Municipio(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    estado = models.ForeignKey(Estado, on_delete=models.PROTECT, related_name='municipios')
    clave = models.CharField(max_length=4)
    nombre = models.CharField(max_length=110)
    class Meta:
        ordering = ['nombre']
        constraints = [models.UniqueConstraint(fields=['estado', 'clave'], name='uq_municipio_estado_clave')]
    def __str__(self): return f'{self.nombre}, {self.estado.nombre}'

class CodigoPostal(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT, related_name='codigos_postales')
    codigo = models.CharField(max_length=5, validators=[RegexValidator(r'^\d{5}$', 'Código postal de cinco dígitos.')])
    class Meta:
        ordering = ['codigo']
        constraints = [models.UniqueConstraint(fields=['municipio', 'codigo'], name='uq_cp_municipio_codigo')]
    def __str__(self): return self.codigo

class Colonia(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_postal = models.ForeignKey(CodigoPostal, on_delete=models.PROTECT, related_name='colonias')
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=80, blank=True)
    class Meta:
        ordering = ['nombre']
        constraints = [models.UniqueConstraint(fields=['codigo_postal', 'nombre'], name='uq_colonia_cp_nombre')]
    def __str__(self): return self.nombre

class Sucursal(models.Model):
    TIPO_SUCURSAL = 'SUCURSAL'
    TIPO_CENTRAL = 'CENTRAL'
    TIPOS = ((TIPO_SUCURSAL, 'Sucursal'), (TIPO_CENTRAL, 'Almacén central'))
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=10, choices=TIPOS, default=TIPO_SUCURSAL)
    # Se permiten nulos para datos migrados desde Etapa 4; nuevas altas exigen estos campos.
    estado = models.ForeignKey(Estado, on_delete=models.PROTECT, null=True, blank=True)
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT, null=True, blank=True)
    codigo_postal = models.ForeignKey(CodigoPostal, on_delete=models.PROTECT, null=True, blank=True)
    colonia = models.ForeignKey(Colonia, on_delete=models.PROTECT, null=True, blank=True)
    calle = models.CharField(max_length=150, blank=True)
    numero_exterior = models.CharField(max_length=20, blank=True)
    numero_interior = models.CharField(max_length=20, blank=True)
    domicilio_fiscal = models.TextField(blank=True)
    rfc = models.CharField(max_length=13, blank=True, validators=[rfc_formato])
    correo = models.EmailField(max_length=254, blank=True)
    telefono = models.CharField(max_length=25, blank=True)
    activa = models.BooleanField(default=True)
    version = models.PositiveBigIntegerField(default=1)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['codigo']
        verbose_name = 'Sucursal o almacén'
        verbose_name_plural = 'Sucursales y almacenes'
        constraints = [models.UniqueConstraint(fields=['tipo'], condition=Q(tipo='CENTRAL'), name='uq_unico_almacen_central')]
    def __str__(self): return f'{self.codigo} - {self.nombre}'

class Proveedor(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=180)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['nombre']
    def __str__(self): return f'{self.codigo} - {self.nombre}'

class LlaveProveedorSucursal(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, related_name='claves_proveedor')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='claves_sucursal')
    llave = models.CharField(max_length=120)
    activa = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['sucursal','proveedor'], name='uq_llave_sucursal_proveedor'),
            models.UniqueConstraint(fields=['proveedor','llave'], name='uq_llave_exclusiva_proveedor'),
        ]
    def __str__(self):return f'{self.sucursal.codigo} / {self.proveedor.codigo}'
