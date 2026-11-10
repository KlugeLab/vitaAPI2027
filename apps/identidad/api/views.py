from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.identidad.api.permissions import PuedeAdministrarIdentidad
from apps.identidad.api.serializers import (
    EmpleadoCrearSerializer, EmpleadoActualizarSerializer, EmpleadoSerializer,
    RestablecerClaveSerializer, RolCrearSerializer, RolActualizarSerializer,
    RolPermisosSerializer, RolSerializer, CatalogoPermisoSerializer,
    SucursalSerializer, SucursalEscrituraSerializer, AsignacionCrearSerializer, AsignacionSerializer,
)
from apps.identidad.models import AsignacionSucursal, CatalogoPermiso, Rol
from apps.identidad.services import asignaciones, empleados, roles, sucursales
from apps.identidad.services.common import ReglaNegocioError
from apps.organizacion.models import Sucursal
from django.contrib.auth import get_user_model


def ejecutar(operacion, **kwargs):
    try:
        return operacion(**kwargs)
    except ReglaNegocioError as exc:
        raise ValidationError({'detail': str(exc)}) from exc
    except DjangoValidationError as exc:
        raise ValidationError({'detail': exc.messages}) from exc
    except ObjectDoesNotExist as exc:
        raise NotFound('El recurso referenciado no existe.') from exc
    except IntegrityError as exc:
        raise ValidationError({'detail': 'Conflicto de unicidad o integridad de datos.'}) from exc


class EmpleadoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = get_user_model().objects.filter(is_superuser=False).order_by('username')
    serializer_class = EmpleadoSerializer
    permission_classes = [PuedeAdministrarIdentidad]
    permisos_por_accion = {
        'list': 'identidad.view_empleado', 'retrieve': 'identidad.view_empleado',
        'create': 'identidad.add_empleado',
        'partial_update': 'identidad.change_empleado',
        'desactivar': 'identidad.change_empleado',
        'restablecer_clave': 'identidad.change_empleado',
    }

    def get_serializer_class(self):
        return {
            'create': EmpleadoCrearSerializer,
            'partial_update': EmpleadoActualizarSerializer,
            'restablecer_clave': RestablecerClaveSerializer,
        }.get(self.action, EmpleadoSerializer)

    def create(self, request, *args, **kwargs):
        entrada = EmpleadoCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        obj = ejecutar(empleados.crear_empleado, **entrada.validated_data)
        return Response(EmpleadoSerializer(obj).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        entrada = EmpleadoActualizarSerializer(data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        actualizado = ejecutar(empleados.actualizar_empleado,
                              empleado_uuid=obj.pk, **entrada.validated_data)
        return Response(EmpleadoSerializer(actualizado).data)

    @action(detail=True, methods=['post'], url_path='desactivar')
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        actualizado = ejecutar(empleados.desactivar_empleado, empleado_uuid=obj.pk)
        return Response(EmpleadoSerializer(actualizado).data)

    @action(detail=True, methods=['post'], url_path='restablecer-clave')
    def restablecer_clave(self, request, pk=None):
        obj = self.get_object()
        entrada = RestablecerClaveSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        ejecutar(empleados.cambiar_password_empleado,
                empleado_uuid=obj.pk, nueva_password=entrada.validated_data['password'])
        return Response({'detail': 'Credenciales actualizadas en central. Sincronización pendiente.'})


class RolViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                 mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Rol.objects.select_related('group').all().order_by('codigo')
    serializer_class = RolSerializer
    permission_classes = [PuedeAdministrarIdentidad]
    permisos_por_accion = {
        'list': 'identidad.view_rol', 'retrieve': 'identidad.view_rol',
        'create': 'identidad.add_rol', 'partial_update': 'identidad.change_rol',
        'permisos': 'identidad.change_rol', 'desactivar': 'identidad.change_rol',
    }

    def get_serializer_class(self):
        return {
            'create': RolCrearSerializer,
            'partial_update': RolActualizarSerializer,
            'permisos': RolPermisosSerializer,
        }.get(self.action, RolSerializer)

    def create(self, request, *args, **kwargs):
        entrada = RolCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        obj = ejecutar(roles.crear_rol, **entrada.validated_data)
        return Response(RolSerializer(obj).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        entrada = RolActualizarSerializer(data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        actualizado = ejecutar(roles.actualizar_rol, rol_uuid=obj.pk, **entrada.validated_data)
        return Response(RolSerializer(actualizado).data)

    @action(detail=True, methods=['put'], url_path='permisos')
    def permisos(self, request, pk=None):
        obj = self.get_object()
        entrada = RolPermisosSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        actualizado = ejecutar(roles.reemplazar_permisos_rol,
                              rol_uuid=obj.pk, permisos_uuid=entrada.validated_data['permisos'])
        return Response(RolSerializer(actualizado).data)

    @action(detail=True, methods=['post'], url_path='desactivar')
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        actualizado = ejecutar(roles.desactivar_rol, rol_uuid=obj.pk)
        return Response(RolSerializer(actualizado).data)


class CatalogoPermisoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                             mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = CatalogoPermiso.objects.all().order_by('app_label', 'modelo', 'codename')
    serializer_class = CatalogoPermisoSerializer
    permission_classes = [PuedeAdministrarIdentidad]
    permisos_por_accion = {
        'list': 'identidad.view_catalogopermiso',
        'retrieve': 'identidad.view_catalogopermiso',
        'create': 'identidad.add_catalogopermiso',
    }

    def create(self, request, *args, **kwargs):
        entrada = self.get_serializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        obj = ejecutar(roles.crear_permiso, **entrada.validated_data)
        return Response(CatalogoPermisoSerializer(obj).data, status=status.HTTP_201_CREATED)


class SucursalViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Sucursal.objects.select_related('estado','municipio','codigo_postal','colonia').all().order_by('codigo')
    serializer_class = SucursalSerializer
    permission_classes = [PuedeAdministrarIdentidad]
    permisos_por_accion = {
        'list': 'organizacion.view_sucursal',
        'retrieve': 'organizacion.view_sucursal',
        'create': 'organizacion.add_sucursal',
        'partial_update': 'organizacion.change_sucursal',
    }

    def create(self, request, *args, **kwargs):
        entrada = SucursalEscrituraSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        obj = ejecutar(sucursales.crear_sucursal, **entrada.validated_data)
        return Response(SucursalSerializer(obj).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        entrada = SucursalEscrituraSerializer(obj, data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        actualizado = ejecutar(sucursales.actualizar_sucursal,
                              sucursal_uuid=obj.pk, **entrada.validated_data)
        return Response(SucursalSerializer(actualizado).data)


class AsignacionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = AsignacionSucursal.objects.all().order_by('-actualizado_en')
    serializer_class = AsignacionSerializer
    permission_classes = [PuedeAdministrarIdentidad]
    permisos_por_accion = {
        'list': 'identidad.view_asignacionsucursal',
        'retrieve': 'identidad.view_asignacionsucursal',
        'create': 'identidad.add_asignacionsucursal',
        'desactivar': 'identidad.change_asignacionsucursal',
    }

    def get_serializer_class(self):
        if self.action == 'create':
            return AsignacionCrearSerializer
        return AsignacionSerializer

    def create(self, request, *args, **kwargs):
        entrada = AsignacionCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        obj = ejecutar(asignaciones.asignar_rol_sucursal, **entrada.validated_data)
        return Response(AsignacionSerializer(obj).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='desactivar')
    def desactivar(self, request, pk=None):
        obj = self.get_object()
        actualizado = ejecutar(asignaciones.desactivar_asignacion, asignacion_uuid=obj.pk)
        return Response(AsignacionSerializer(actualizado).data)
