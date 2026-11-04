from django.db import transaction
from apps.organizacion.models import Sucursal
from apps.identidad.services.common import validar_modelo
from apps.identidad.services.snapshots import sucursal_snapshot
from apps.sync_central.services.outbox import registrar_evento


@transaction.atomic
def crear_sucursal(*, codigo, nombre):
    sucursal = Sucursal(codigo=codigo, nombre=nombre, activa=True)
    validar_modelo(sucursal)
    sucursal.save()
    registrar_evento(
        tipo_entidad='sucursal', tipo_operacion='created',
        entidad_uuid=sucursal.pk, version_entidad=1,
        payload=sucursal_snapshot(sucursal), sucursales=(),
    )
    return sucursal
