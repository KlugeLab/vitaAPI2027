"""Operaciones transaccionales: toda modificación conserva su outbox."""
from django.db import transaction
from apps.organizacion.models import Sucursal
from apps.identidad.models import AsignacionSucursal
from apps.identidad.services.common import ReglaNegocioError, validar_modelo
from apps.identidad.services.snapshots import sucursal_snapshot
from apps.sync_central.services.outbox import registrar_evento
from apps.sync_central.models import InstalacionSucursal


def _validar_baja(sucursal):
    if AsignacionSucursal.objects.filter(sucursal=sucursal, activa=True).exists():
        raise ReglaNegocioError('Revoca las asignaciones activas antes de desactivar la sucursal.')
    if InstalacionSucursal.objects.filter(sucursal=sucursal, activa=True).exists():
        raise ReglaNegocioError('Desactiva o desprovisiona primero la instalación técnica de sincronización.')

@transaction.atomic
def crear_sucursal(**datos):
    sucursal = Sucursal(**datos)
    validar_modelo(sucursal)
    sucursal.save()
    registrar_evento(tipo_entidad='sucursal', tipo_operacion='created',
                    entidad_uuid=sucursal.pk, version_entidad=sucursal.version,
                    payload=sucursal_snapshot(sucursal), sucursales=())
    return sucursal

@transaction.atomic
def actualizar_sucursal(*, sucursal_uuid, **cambios):
    sucursal = Sucursal.objects.select_for_update().get(pk=sucursal_uuid)
    if not cambios:
        raise ReglaNegocioError('Se requiere al menos un cambio.')
    if cambios.get('activa') is False and sucursal.activa:
        _validar_baja(sucursal)
    if cambios.get('tipo') is not None and cambios['tipo'] != sucursal.tipo:
        _validar_baja(sucursal)
    for campo, valor in cambios.items():
        setattr(sucursal, campo, valor)
    sucursal.version += 1
    validar_modelo(sucursal)
    sucursal.save()
    registrar_evento(tipo_entidad='sucursal', tipo_operacion='updated',
                    entidad_uuid=sucursal.pk, version_entidad=sucursal.version,
                    payload=sucursal_snapshot(sucursal), sucursales=[sucursal.pk])
    return sucursal
