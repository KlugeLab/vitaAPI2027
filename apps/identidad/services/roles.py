"""Roles locales Django Group + catálogo central y eventos."""
from django.contrib.auth.models import Group
from django.db import transaction
from apps.identidad.models import AsignacionSucursal, CatalogoPermiso, Rol, RolPermiso
from apps.identidad.services.common import ReglaNegocioError, validar_modelo
from apps.identidad.services.snapshots import permiso_snapshot, rol_snapshot
from apps.sync_central.services.outbox import registrar_evento


def sucursales_con_rol(rol):
    return list(AsignacionSucursal.objects.filter(
        rol=rol, activa=True
    ).values_list('sucursal_id', flat=True).distinct())


@transaction.atomic
def crear_permiso(*, app_label, modelo, codename, descripcion):
    permiso = CatalogoPermiso(
        app_label=app_label, modelo=modelo, codename=codename,
        descripcion=descripcion,
    )
    validar_modelo(permiso)
    permiso.save()
    registrar_evento(
        tipo_entidad='catalogo_permiso', tipo_operacion='created',
        entidad_uuid=permiso.pk, version_entidad=permiso.version,
        payload=permiso_snapshot(permiso), sucursales=(),
    )
    return permiso


@transaction.atomic
def crear_rol(*, codigo, nombre, descripcion=''):
    if not codigo or not nombre:
        raise ReglaNegocioError('Código y nombre de rol son obligatorios.')
    grupo = Group(name=nombre)
    validar_modelo(grupo)
    grupo.save()
    rol = Rol(group=grupo, codigo=codigo, descripcion=descripcion)
    validar_modelo(rol)
    rol.save()
    registrar_evento(
        tipo_entidad='rol', tipo_operacion='created',
        entidad_uuid=rol.pk, version_entidad=rol.version,
        payload=rol_snapshot(rol), sucursales=(),
    )
    return rol


@transaction.atomic
def actualizar_rol(*, rol_uuid, nombre=None, descripcion=None):
    if nombre is None and descripcion is None:
        raise ReglaNegocioError('Se requiere un cambio.')
    rol = Rol.objects.select_for_update().select_related('group').get(pk=rol_uuid)
    if nombre is not None:
        if not nombre.strip():
            raise ReglaNegocioError('El nombre no puede quedar vacío.')
        rol.group.name = nombre
        validar_modelo(rol.group)
        rol.group.save(update_fields=['name'])
    if descripcion is not None:
        rol.descripcion = descripcion
    rol.version += 1
    validar_modelo(rol)
    rol.save()
    registrar_evento(
        tipo_entidad='rol', tipo_operacion='updated',
        entidad_uuid=rol.pk, version_entidad=rol.version,
        payload=rol_snapshot(rol), sucursales=sucursales_con_rol(rol),
    )
    return rol


@transaction.atomic
def reemplazar_permisos_rol(*, rol_uuid, permisos_uuid):
    rol = Rol.objects.select_for_update().select_related('group').get(pk=rol_uuid)
    if not rol.activo:
        raise ReglaNegocioError('Un rol inactivo no puede recibir permisos.')
    identificadores = list(permisos_uuid)
    if len(identificadores) != len(set(identificadores)):
        raise ReglaNegocioError('La lista contiene permisos duplicados.')
    permisos = list(CatalogoPermiso.objects.filter(pk__in=identificadores, activo=True))
    if len(permisos) != len(identificadores):
        raise ReglaNegocioError('Uno o más permisos no existen o están inactivos.')
    RolPermiso.objects.filter(rol=rol).delete()
    RolPermiso.objects.bulk_create([
        RolPermiso(rol=rol, permiso=permiso) for permiso in permisos
    ])
    rol.version += 1
    rol.save(update_fields=['version', 'actualizado_en'])
    # En central, Group.permissions NO se rellena a la fuerza: algunos
    # permisos corresponden a modelos instalados solo en SSucursalAPI.
    registrar_evento(
        tipo_entidad='rol', tipo_operacion='updated',
        entidad_uuid=rol.pk, version_entidad=rol.version,
        payload=rol_snapshot(rol), sucursales=sucursales_con_rol(rol),
    )
    return rol


@transaction.atomic
def desactivar_rol(*, rol_uuid):
    rol = Rol.objects.select_for_update().select_related('group').get(pk=rol_uuid)
    if not rol.activo:
        return rol
    destinos = sucursales_con_rol(rol)
    rol.activo = False
    rol.version += 1
    rol.save(update_fields=['activo', 'version', 'actualizado_en'])
    registrar_evento(
        tipo_entidad='rol', tipo_operacion='deactivated',
        entidad_uuid=rol.pk, version_entidad=rol.version,
        payload=rol_snapshot(rol), sucursales=destinos,
    )
    return rol
