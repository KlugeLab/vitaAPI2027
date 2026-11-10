"""Contratos JSON v1. NO se incluyen hashes ni secretos en eventos generales."""


def empleado_snapshot(empleado):
    return {
        'uuid': str(empleado.pk),
        'username': empleado.username,
        'codigo_empleado': empleado.codigo_empleado,
        'first_name': empleado.first_name,
        'last_name': empleado.last_name,
        'email': empleado.email,
        'is_active': empleado.is_active,
        'version': empleado.version,
        'version_credenciales': empleado.version_credenciales,
    }


def permiso_snapshot(permiso):
    return {
        'uuid': str(permiso.pk),
        'app_label': permiso.app_label,
        'modelo': permiso.modelo,
        'codename': permiso.codename,
        'descripcion': permiso.descripcion,
        'activo': permiso.activo,
        'version': permiso.version,
    }


def rol_snapshot(rol):
    from apps.identidad.models import RolPermiso
    reglas = RolPermiso.objects.filter(rol=rol, permiso__activo=True).select_related('permiso')
    permisos = [permiso_snapshot(regla.permiso) for regla in reglas]
    permisos.sort(key=lambda x: (x['app_label'], x['modelo'], x['codename']))
    return {
        'uuid': str(rol.pk),
        'codigo': rol.codigo,
        'nombre': rol.group.name,
        'descripcion': rol.descripcion,
        'activo': rol.activo,
        'version': rol.version,
        'permisos': permisos,
    }


def sucursal_snapshot(sucursal):
    # Contrato v1 ampliado: la sucursal antigua sigue aceptando las claves básicas.
    return {
        'uuid': str(sucursal.pk), 'codigo': sucursal.codigo,
        'nombre': sucursal.nombre, 'activa': sucursal.activa,
        'tipo': sucursal.tipo, 'version': sucursal.version,
        'estado': sucursal.estado.nombre if sucursal.estado_id else '',
        'municipio': sucursal.municipio.nombre if sucursal.municipio_id else '',
        'codigo_postal': sucursal.codigo_postal.codigo if sucursal.codigo_postal_id else '',
        'colonia': sucursal.colonia.nombre if sucursal.colonia_id else '',
        'calle': sucursal.calle,
        'numero_exterior': sucursal.numero_exterior,
        'numero_interior': sucursal.numero_interior,
        'domicilio_fiscal': sucursal.domicilio_fiscal,
        'rfc': sucursal.rfc,
        'correo': sucursal.correo,
        'telefono': sucursal.telefono,
        # Nunca exponer llaves de proveedores en el canal general de identidad.
    }


def asignacion_snapshot(asignacion):
    return {
        'uuid': str(asignacion.pk),
        'empleado_uuid': str(asignacion.empleado_id),
        'rol_uuid': str(asignacion.rol_id),
        'sucursal_uuid': str(asignacion.sucursal_id),
        'activa': asignacion.activa,
        'version': asignacion.version,
        'vigente_desde': asignacion.vigente_desde.isoformat() if asignacion.vigente_desde else None,
        'vigente_hasta': asignacion.vigente_hasta.isoformat() if asignacion.vigente_hasta else None,
    }


def asignacion_con_dependencias(asignacion):
    """Snapshot completo para alta/actualización de asignación en una sucursal."""
    return {
        'asignacion': asignacion_snapshot(asignacion),
        'empleado': empleado_snapshot(asignacion.empleado),
        'rol': rol_snapshot(asignacion.rol),
        'sucursal': sucursal_snapshot(asignacion.sucursal),
        # Credenciales y contraseña NO forman parte de este contrato.
    }
