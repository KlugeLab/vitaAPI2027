from rest_framework.permissions import BasePermission


class PuedeAdministrarIdentidad(BasePermission):
    """Solo personal administrativo con permiso Django explícito por acción."""
    message = 'No dispone de permiso para esta operación administrativa.'

    def has_permission(self, request, view):
        usuario = request.user
        if not usuario or not usuario.is_authenticated or not usuario.is_active or not usuario.is_staff:
            return False
        mapa = getattr(view, 'permisos_por_accion', {})
        permiso = mapa.get(getattr(view, 'action', None))
        return bool(permiso and usuario.has_perm(permiso))
