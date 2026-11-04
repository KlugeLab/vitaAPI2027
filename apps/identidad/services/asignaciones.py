from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.identidad.models import AsignacionSucursal, Rol
from apps.organizacion.models import Sucursal
from apps.identidad.services.common import ReglaNegocioError, validar_modelo
from apps.identidad.services.snapshots import asignacion_con_dependencias, asignacion_snapshot
from apps.sync_central.services.outbox import registrar_evento


@transaction.atomic
def asignar_rol_sucursal(*, empleado_uuid, rol_uuid, sucursal_uuid,
                         vigente_desde=None, vigente_hasta=None):
    Empleado = get_user_model()
    empleado = Empleado.objects.select_for_update().get(pk=empleado_uuid)
    rol = Rol.objects.select_for_update().get(pk=rol_uuid)
    sucursal = Sucursal.objects.get(pk=sucursal_uuid)
    if not empleado.is_active or empleado.is_superuser or empleado.is_staff:
        raise ReglaNegocioError('Solo se permiten empleados operativos activos (no administradores).')
    if not rol.activo or not sucursal.activa:
        raise ReglaNegocioError('El rol y la sucursal deben estar activos.')
    if vigente_hasta and vigente_hasta <= timezone.now():
        raise ReglaNegocioError('La fecha de fin no puede estar en el pasado.')

    existente = AsignacionSucursal.objects.select_for_update().filter(
        empleado=empleado, rol=rol, sucursal=sucursal
    ).first()
    if existente and existente.activa:
        raise ReglaNegocioError('El empleado ya tiene este rol activo en esta sucursal.')
    if existente:
        asignacion = existente
        asignacion.activa = True
        asignacion.version += 1
        asignacion.vigente_desde = vigente_desde
        asignacion.vigente_hasta = vigente_hasta
    else:
        asignacion = AsignacionSucursal(
            empleado=empleado, rol=rol, sucursal=sucursal,
            vigente_desde=vigente_desde, vigente_hasta=vigente_hasta,
        )
    validar_modelo(asignacion)
    asignacion.save()
    registrar_evento(
        tipo_entidad='asignacion',
        tipo_operacion='created' if existente is None else 'reactivated',
        entidad_uuid=asignacion.pk, version_entidad=asignacion.version,
        payload=asignacion_con_dependencias(asignacion),
        sucursales=[sucursal.pk],
    )
    return asignacion


@transaction.atomic
def desactivar_asignacion(*, asignacion_uuid):
    asignacion = AsignacionSucursal.objects.select_for_update().select_related(
        'empleado', 'rol__group', 'sucursal'
    ).get(pk=asignacion_uuid)
    if not asignacion.activa:
        return asignacion
    asignacion.activa = False
    asignacion.version += 1
    asignacion.save(update_fields=['activa', 'version', 'actualizado_en'])
    registrar_evento(
        tipo_entidad='asignacion', tipo_operacion='deactivated',
        entidad_uuid=asignacion.pk, version_entidad=asignacion.version,
        payload=asignacion_snapshot(asignacion),
        sucursales=[asignacion.sucursal_id],
    )
    return asignacion
