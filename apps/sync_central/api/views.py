"""API exclusivamente servicio-a-servicio. No usa la sesión del admin."""
from django.db.models import Max
from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from apps.identidad.models import AsignacionSucursal
from apps.identidad.services.snapshots import asignacion_con_dependencias, sucursal_snapshot
from apps.sync_central.auth import AutenticacionInstalacion
from apps.sync_central.models import (ContadorPublicacion, DestinoEvento, EventoSincronizacion)
from apps.sync_central.services.publicador import publicar_todos


class VistaSyncBase(APIView):
    authentication_classes = [AutenticacionInstalacion]
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _instalacion(request):
        return request.auth


class BootstrapView(VistaSyncBase):
    """Snapshot del estado maestro actual, con cursor ANTERIOR al snapshot.

    Capturamos primero el watermark de eventos ya publicados. Cualquier
    cambio concurrente que se publique después tendrá una secuencia mayor.
    El cliente deberá usar el UUID+versión para omitir repeticiones.
    """
    def get(self, request):
        publicar_todos()
        instalacion = self._instalacion(request)
        # Capturar watermark ANTES de las lecturas de datos maestros.
        contador = ContadorPublicacion.objects.filter(pk=1).values_list('ultimo_valor', flat=True).first() or 0
        qs = (AsignacionSucursal.objects
              .filter(sucursal_id=instalacion.sucursal_id, activa=True,
                      empleado__is_staff=False, empleado__is_superuser=False)
              .select_related('empleado', 'rol__group', 'sucursal')
              .order_by('uuid'))
        asignaciones = [asignacion_con_dependencias(a) for a in qs]
        return Response({
            'schema_version': 1,
            'sucursal': sucursal_snapshot(instalacion.sucursal),
            'cursor': str(contador),
            'asignaciones': asignaciones,
        })


class CambiosView(VistaSyncBase):
    def get(self, request):
        try:
            cursor = int(request.query_params.get('cursor', '0'))
            limite = int(request.query_params.get('limit', '100'))
        except (ValueError, TypeError):
            raise ValidationError({'detail': 'cursor y limit deben ser números enteros.'})
        if cursor < 0 or not 1 <= limite <= 500:
            raise ValidationError({'detail': 'Cursor o límite inválidos.'})
        publicar_todos()
        instalacion = self._instalacion(request)
        ultimo = (ContadorPublicacion.objects.filter(pk=1)
                  .values_list('ultimo_valor', flat=True).first() or 0)
        if cursor > ultimo:
            raise ValidationError({'detail': 'Cursor mayor que la secuencia publicada.'})
        destinos = list(DestinoEvento.objects.filter(
            instalacion=instalacion,
            evento__secuencia_publicacion__gt=cursor,
            evento__secuencia_publicacion__lte=ultimo,
        ).select_related('evento').order_by('evento__secuencia_publicacion')[:limite + 1])
        hay_mas = len(destinos) > limite
        destinos = destinos[:limite]
        eventos = [{
            'event_id': str(d.evento.event_id),
            'sequence': d.evento.secuencia_publicacion,
            'entity': d.evento.tipo_entidad,
            'operation': d.evento.tipo_operacion,
            'entity_uuid': str(d.evento.entidad_uuid),
            'version': d.evento.version_entidad,
            'schema_version': d.evento.schema_version,
            'payload': d.evento.payload,
        } for d in destinos]
        siguiente = eventos[-1]['sequence'] if hay_mas else ultimo
        return Response({
            'schema_version': 1, 'events': eventos,
            'next_cursor': str(siguiente), 'has_more': hay_mas,
        })


class ConfirmacionView(VistaSyncBase):
    def post(self, request):
        try:
            cursor = int(request.data.get('cursor', ''))
        except (ValueError, TypeError):
            raise ValidationError({'detail': 'Cursor inválido.'})
        ultimo = (ContadorPublicacion.objects.filter(pk=1)
                  .values_list('ultimo_valor', flat=True).first() or 0)
        if cursor < 0 or cursor > ultimo:
            raise ValidationError({'detail': 'Cursor fuera de rango.'})
        with transaction.atomic():
            cantidad = DestinoEvento.objects.filter(
                instalacion=self._instalacion(request), confirmado_en__isnull=True,
                evento__secuencia_publicacion__lte=cursor,
            ).update(confirmado_en=timezone.now())
        return Response({'ok': True, 'confirmados': cantidad, 'cursor': str(cursor)})


class CredencialesView(VistaSyncBase):
    """Solo devuelve credenciales de empleados asignados a esta instalación.

    NO incluye credenciales en el outbox ni en el snapshot general. Exige TLS.
    """
    def post(self, request):
        versiones = request.data.get('versions', {})
        if not isinstance(versiones, dict) or len(versiones) > 10000:
            raise ValidationError({'detail': 'versions debe ser objeto de hasta 10000 entradas.'})
        from django.db.models import Q
        now = timezone.now()
        autorizados = set(AsignacionSucursal.objects.filter(
            sucursal_id=self._instalacion(request).sucursal_id,
            activa=True, rol__activo=True, empleado__is_active=True,
            empleado__is_staff=False, empleado__is_superuser=False,
        ).filter(
            Q(vigente_desde__isnull=True) | Q(vigente_desde__lte=now),
            Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gt=now),
        ).values_list('empleado_id', flat=True))
        from django.contrib.auth import get_user_model
        Empleado = get_user_model()
        datos = []
        for usuario in Empleado.objects.filter(pk__in=autorizados):
            if not usuario.has_usable_password():
                continue
            version_local = versiones.get(str(usuario.pk), 0)
            if type(version_local) is not int or version_local < 0:
                raise ValidationError({'detail': 'Cada versión debe ser entero positivo o cero.'})
            if usuario.version_credenciales > version_local:
                datos.append({
                    'empleado_uuid': str(usuario.pk),
                    'version_credenciales': usuario.version_credenciales,
                    'password_hash': usuario.password,
                })
        return Response({'schema_version': 1, 'credentials': datos})
