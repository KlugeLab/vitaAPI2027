"""Endpoints administrativos de ubicación postal y proveedores."""
from django.db import transaction, IntegrityError
import uuid
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.identidad.api.permissions import PuedeAdministrarIdentidad
from apps.organizacion.models import Estado, Municipio, CodigoPostal, Colonia, Proveedor, LlaveProveedorSucursal, Sucursal


class EstadoSerializer(serializers.ModelSerializer):
    class Meta:
        model=Estado;fields=('clave','nombre')

class MunicipioSerializer(serializers.ModelSerializer):
    class Meta:
        model=Municipio;fields=('uuid','estado','clave','nombre')

class CodigoPostalSerializer(serializers.ModelSerializer):
    class Meta:
        model=CodigoPostal;fields=('uuid','municipio','codigo')

class ColoniaSerializer(serializers.ModelSerializer):
    class Meta:
        model=Colonia;fields=('uuid','codigo_postal','nombre','tipo')

class CatalogoPostalBase(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes=[PuedeAdministrarIdentidad]
    permisos_por_accion={'list':'organizacion.view_sucursal'}

class EstadoViewSet(CatalogoPostalBase):
    queryset=Estado.objects.all().order_by('nombre')
    serializer_class=EstadoSerializer

class MunicipioViewSet(CatalogoPostalBase):
    serializer_class=MunicipioSerializer
    def get_queryset(self):
        estado=self.request.query_params.get('estado')
        return Municipio.objects.filter(estado_id=estado).order_by('nombre') if estado else Municipio.objects.none()

class CodigoPostalViewSet(CatalogoPostalBase):
    serializer_class=CodigoPostalSerializer
    def get_queryset(self):
        municipio=self.request.query_params.get('municipio')
        try: uuid.UUID(municipio)
        except (TypeError, ValueError, AttributeError): return CodigoPostal.objects.none()
        return CodigoPostal.objects.filter(municipio_id=municipio).order_by('codigo')

class ColoniaViewSet(CatalogoPostalBase):
    serializer_class=ColoniaSerializer
    def get_queryset(self):
        cp=self.request.query_params.get('codigo_postal')
        try: uuid.UUID(cp)
        except (TypeError, ValueError, AttributeError): return Colonia.objects.none()
        return Colonia.objects.filter(codigo_postal_id=cp).order_by('nombre')


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model=Proveedor
        fields=('uuid','codigo','nombre','activo')
        read_only_fields=('uuid',)

class ProveedorViewSet(mixins.ListModelMixin,mixins.RetrieveModelMixin,
                       mixins.CreateModelMixin,mixins.UpdateModelMixin,viewsets.GenericViewSet):
    queryset=Proveedor.objects.all().order_by('nombre')
    serializer_class=ProveedorSerializer
    permission_classes=[PuedeAdministrarIdentidad]
    permisos_por_accion={
        'list':'organizacion.view_proveedor','retrieve':'organizacion.view_proveedor',
        'create':'organizacion.add_proveedor','partial_update':'organizacion.change_proveedor',
    }
    http_method_names=['get','post','patch','head','options']


class LlaveProveedorSerializer(serializers.ModelSerializer):
    llave=serializers.CharField(max_length=120,write_only=True,required=False,trim_whitespace=True)
    llave_mascara=serializers.SerializerMethodField()
    class Meta:
        model=LlaveProveedorSucursal
        fields=('uuid','sucursal','proveedor','llave','llave_mascara','activa')
        read_only_fields=('uuid','llave_mascara')
    def get_llave_mascara(self,obj):
        return ('••••' + obj.llave[-4:]) if obj.llave else ''
    def validate(self,attrs):
        if self.instance is None and not attrs.get('llave'):
            raise serializers.ValidationError({'llave':'La llave de proveedor es obligatoria.'})
        if self.instance is not None:
            if 'sucursal' in attrs and attrs['sucursal'].pk != self.instance.sucursal_id:
                raise serializers.ValidationError({'sucursal':'La sucursal no puede cambiar; crea una llave nueva.'})
            if 'proveedor' in attrs and attrs['proveedor'].pk != self.instance.proveedor_id:
                raise serializers.ValidationError({'proveedor':'El proveedor no puede cambiar; crea una llave nueva.'})
        return attrs

class LlaveProveedorViewSet(mixins.ListModelMixin,mixins.RetrieveModelMixin,
                            mixins.CreateModelMixin,mixins.UpdateModelMixin,viewsets.GenericViewSet):
    permission_classes=[PuedeAdministrarIdentidad]
    serializer_class=LlaveProveedorSerializer
    permisos_por_accion={
        'list':'organizacion.view_llaveproveedorsucursal',
        'retrieve':'organizacion.view_llaveproveedorsucursal',
        'create':'organizacion.add_llaveproveedorsucursal',
        'partial_update':'organizacion.change_llaveproveedorsucursal',
    }
    http_method_names=['get','post','patch','head','options']
    def get_queryset(self):
        qs=LlaveProveedorSucursal.objects.select_related('proveedor','sucursal').all()
        sucursal=self.request.query_params.get('sucursal')
        if sucursal:
            try: uuid.UUID(sucursal)
            except (TypeError, ValueError): return qs.none()
            qs=qs.filter(sucursal_id=sucursal)
        return qs.order_by('proveedor__nombre')
    def perform_create(self,serializer):
        try:
            with transaction.atomic(): serializer.save()
        except IntegrityError as exc:
            raise ValidationError({'detail':'Ya existe llave para ese proveedor/sucursal o se repite su identificador.'}) from exc
    def perform_update(self,serializer):
        try:
            with transaction.atomic(): serializer.save()
        except IntegrityError as exc:
            raise ValidationError({'detail':'La llave ya está asignada a otra sucursal del mismo proveedor.'}) from exc
