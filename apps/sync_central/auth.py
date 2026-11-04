"""Autenticación de servicio por instalación, distinta de las sesiones Django.

Solo puede utilizarse con HTTPS salvo en pruebas locales controladas.
"""
import hashlib
import hmac
import uuid
from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from apps.sync_central.models import InstalacionSucursal


class IdentidadTecnica:
    is_authenticated = True
    is_anonymous = False
    is_active = True
    is_staff = False

    def __str__(self):
        return 'vita-sync-service'


class AutenticacionInstalacion(BaseAuthentication):
    def authenticate(self, request):
        header = request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            raise AuthenticationFailed('Se requiere token de instalación.')
        token = header.removeprefix('Bearer ').strip()
        try:
            instalacion_id = uuid.UUID(request.headers.get('X-Vita-Installation', ''))
        except (ValueError, TypeError, AttributeError):
            raise AuthenticationFailed('Identificador de instalación inválido.')
        if len(token) < 32 or len(token) > 256:
            raise AuthenticationFailed('Credenciales inválidas.')
        try:
            instalacion = InstalacionSucursal.objects.select_related('sucursal').get(
                pk=instalacion_id, activa=True, sucursal__activa=True
            )
        except InstalacionSucursal.DoesNotExist:
            raise AuthenticationFailed('Instalación no autorizada.')
        digest = hashlib.sha256(token.encode('utf-8')).hexdigest()
        if instalacion.version_contrato != 1:
            raise AuthenticationFailed('Versión del contrato de instalación incompatible.')
        if not instalacion.token_sha256 or not hmac.compare_digest(
            digest, instalacion.token_sha256
        ):
            raise AuthenticationFailed('Credenciales inválidas.')
        permitir_http_lab = (settings.DEBUG and getattr(settings, 'VITA_SYNC_ALLOW_HTTP_DEV', False))
        if not request.is_secure() and not permitir_http_lab:
            raise AuthenticationFailed('La sincronización requiere HTTPS.')
        InstalacionSucursal.objects.filter(pk=instalacion.pk).update(
            ultima_conexion=timezone.now()
        )
        return (IdentidadTecnica(), instalacion)

    def authenticate_header(self, request):
        return 'Bearer realm="vita-sync"'
