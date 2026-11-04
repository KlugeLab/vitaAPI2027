"""Altas, cambios, desactivación y claves de empleados con outbox."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from apps.identidad.models import AsignacionSucursal
from apps.identidad.services.common import ReglaNegocioError, validar_modelo
from apps.identidad.services.snapshots import empleado_snapshot
from apps.sync_central.services.outbox import registrar_evento


def sucursales_autorizadas(empleado):
    return list(AsignacionSucursal.objects.filter(
        empleado=empleado, activa=True
    ).values_list('sucursal_id', flat=True).distinct())


def _validar_password(password, empleado):
    if not password:
        raise ReglaNegocioError('La contraseña es obligatoria y no puede estar vacía.')
    try:
        validate_password(password, user=empleado)
    except DjangoValidationError as exc:
        raise ReglaNegocioError('; '.join(exc.messages)) from exc


@transaction.atomic
def crear_empleado(*, username, password, codigo_empleado,
                   first_name='', last_name='', email=''):
    Empleado = get_user_model()
    empleado = Empleado(
        username=username, codigo_empleado=codigo_empleado,
        first_name=first_name, last_name=last_name, email=email,
        is_active=True, is_staff=False, is_superuser=False,
    )
    _validar_password(password, empleado)
    empleado.set_password(password)
    validar_modelo(empleado)
    empleado.save()
    registrar_evento(
        tipo_entidad='empleado', tipo_operacion='created',
        entidad_uuid=empleado.pk, version_entidad=empleado.version,
        payload=empleado_snapshot(empleado), sucursales=(),
    )
    return empleado


@transaction.atomic
def actualizar_empleado(*, empleado_uuid, **cambios):
    Empleado = get_user_model()
    permitidos = {'username', 'first_name', 'last_name', 'email'}
    if not cambios or (set(cambios) - permitidos):
        raise ReglaNegocioError('Campos inválidos o no se proporcionaron cambios.')
    empleado = Empleado.objects.select_for_update().get(pk=empleado_uuid)
    for campo, valor in cambios.items():
        setattr(empleado, campo, valor)
    empleado.version += 1
    validar_modelo(empleado)
    empleado.save()
    registrar_evento(
        tipo_entidad='empleado', tipo_operacion='updated',
        entidad_uuid=empleado.pk, version_entidad=empleado.version,
        payload=empleado_snapshot(empleado),
        sucursales=sucursales_autorizadas(empleado),
    )
    return empleado


@transaction.atomic
def desactivar_empleado(*, empleado_uuid):
    Empleado = get_user_model()
    empleado = Empleado.objects.select_for_update().get(pk=empleado_uuid)
    if empleado.is_superuser:
        raise ReglaNegocioError('No es posible desactivar superusuarios mediante esta API.')
    if not empleado.is_active:
        return empleado
    empleado.is_active = False
    empleado.version += 1
    validar_modelo(empleado)
    empleado.save()
    registrar_evento(
        tipo_entidad='empleado', tipo_operacion='deactivated',
        entidad_uuid=empleado.pk, version_entidad=empleado.version,
        payload=empleado_snapshot(empleado),
        sucursales=sucursales_autorizadas(empleado),
    )
    return empleado


@transaction.atomic
def cambiar_password_empleado(*, empleado_uuid, nueva_password):
    Empleado = get_user_model()
    empleado = Empleado.objects.select_for_update().get(pk=empleado_uuid)
    if empleado.is_superuser:
        raise ReglaNegocioError('No modificar superusuarios por esta API.')
    _validar_password(nueva_password, empleado)
    empleado.set_password(nueva_password)
    empleado.version_credenciales += 1
    empleado.save(update_fields=['password', 'version_credenciales', 'actualizado_en'])
    registrar_evento(
        tipo_entidad='credencial', tipo_operacion='updated',
        entidad_uuid=empleado.pk, version_entidad=empleado.version_credenciales,
        payload={
            'empleado_uuid': str(empleado.pk),
            'version_credenciales': empleado.version_credenciales,
            'tipo': 'password_cambiada',
        },
        sucursales=sucursales_autorizadas(empleado),
    )
    return empleado
