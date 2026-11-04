from rest_framework import serializers
from apps.identidad.models import AsignacionSucursal, CatalogoPermiso, Rol
from apps.organizacion.models import Sucursal
from django.contrib.auth import get_user_model

Empleado = get_user_model()


class EmpleadoCrearSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    codigo_empleado = serializers.CharField(max_length=30)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)


class EmpleadoActualizarSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, max_length=150)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)


class EmpleadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empleado
        fields = ('id', 'username', 'codigo_empleado', 'first_name', 'last_name',
                  'email', 'is_active', 'version', 'version_credenciales')
        read_only_fields = fields


class RestablecerClaveSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class RolCrearSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=50)
    nombre = serializers.CharField(max_length=150)
    descripcion = serializers.CharField(required=False, allow_blank=True)


class RolActualizarSerializer(serializers.Serializer):
    nombre = serializers.CharField(required=False, max_length=150)
    descripcion = serializers.CharField(required=False, allow_blank=True)


class RolPermisosSerializer(serializers.Serializer):
    permisos = serializers.ListField(child=serializers.UUIDField(), allow_empty=True)


class RolSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='group.name', read_only=True)
    permisos = serializers.SerializerMethodField()

    class Meta:
        model = Rol
        fields = ('uuid', 'codigo', 'nombre', 'descripcion', 'activo', 'version', 'permisos')
        read_only_fields = fields

    def get_permisos(self, obj):
        return [str(x) for x in obj.reglas_permisos.values_list('permiso_id', flat=True)]


class CatalogoPermisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogoPermiso
        fields = ('uuid', 'app_label', 'modelo', 'codename', 'descripcion', 'activo', 'version')
        read_only_fields = ('uuid', 'activo', 'version')


class SucursalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sucursal
        fields = ('uuid', 'codigo', 'nombre', 'activa')
        read_only_fields = ('uuid', 'activa')


class AsignacionCrearSerializer(serializers.Serializer):
    empleado_uuid = serializers.UUIDField()
    rol_uuid = serializers.UUIDField()
    sucursal_uuid = serializers.UUIDField()
    vigente_desde = serializers.DateTimeField(required=False, allow_null=True)
    vigente_hasta = serializers.DateTimeField(required=False, allow_null=True)


class AsignacionSerializer(serializers.ModelSerializer):
    empleado_uuid = serializers.UUIDField(source='empleado_id', read_only=True)
    rol_uuid = serializers.UUIDField(source='rol_id', read_only=True)
    sucursal_uuid = serializers.UUIDField(source='sucursal_id', read_only=True)

    class Meta:
        model = AsignacionSucursal
        fields = ('uuid', 'empleado_uuid', 'rol_uuid', 'sucursal_uuid',
                  'activa', 'vigente_desde', 'vigente_hasta', 'version')
        read_only_fields = fields
