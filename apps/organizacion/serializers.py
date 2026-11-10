"""Campos exigidos para nuevas sucursales, compatibles con filas heredadas."""
from rest_framework import serializers
from apps.organizacion.models import Sucursal, Estado, Municipio, CodigoPostal, Colonia
from apps.organizacion.services_validacion import validar_rfc, validar_jerarquia, TELEFONO_RE

class SucursalLecturaSerializer(serializers.ModelSerializer):
    estado_nombre=serializers.CharField(source='estado.nombre',read_only=True,default='')
    municipio_nombre=serializers.CharField(source='municipio.nombre',read_only=True,default='')
    codigo_postal_texto=serializers.CharField(source='codigo_postal.codigo',read_only=True,default='')
    colonia_nombre=serializers.CharField(source='colonia.nombre',read_only=True,default='')
    class Meta:
        model=Sucursal
        fields=('uuid','codigo','nombre','tipo','activa','version',
                'estado','municipio','codigo_postal','colonia',
                'estado_nombre','municipio_nombre','codigo_postal_texto','colonia_nombre',
                'calle','numero_exterior','numero_interior',
                'domicilio_fiscal','rfc','correo','telefono')
        read_only_fields=fields

class SucursalEscrituraSerializer(serializers.ModelSerializer):
    estado=serializers.PrimaryKeyRelatedField(queryset=Estado.objects.all(),required=False)
    municipio=serializers.PrimaryKeyRelatedField(queryset=Municipio.objects.all(),required=False)
    codigo_postal=serializers.PrimaryKeyRelatedField(queryset=CodigoPostal.objects.all(),required=False)
    colonia=serializers.PrimaryKeyRelatedField(queryset=Colonia.objects.all(),required=False)
    rfc=serializers.CharField(max_length=13,required=False)
    telefono=serializers.CharField(max_length=25,required=False)
    class Meta:
        model=Sucursal
        fields=('codigo','nombre','tipo','activa','estado','municipio','codigo_postal','colonia',
                'calle','numero_exterior','numero_interior','domicilio_fiscal','rfc','correo','telefono')
        extra_kwargs={
            'calle':{'required':False},'numero_exterior':{'required':False},
            'domicilio_fiscal':{'required':False},'correo':{'required':False},
            'codigo':{'required':False},'nombre':{'required':False},
        }
    def validate(self,attrs):
        if self.instance is None:
            obligatorios=('codigo','nombre','estado','municipio','codigo_postal','colonia',
                          'calle','numero_exterior','domicilio_fiscal','rfc','correo','telefono')
            errores={k:'Campo obligatorio.' for k in obligatorios if not attrs.get(k)}
            if errores: raise serializers.ValidationError(errores)
        if 'codigo' in attrs and self.instance is not None and attrs['codigo'] != self.instance.codigo:
            raise serializers.ValidationError({'codigo':'El código no puede cambiar después del alta.'})
        data={k:attrs.get(k,getattr(self.instance,k,None) if self.instance else None)
              for k in ('estado','municipio','codigo_postal','colonia')}
        if any(v is not None for v in data.values()):
            validar_jerarquia(**{'estado':data['estado'],'municipio':data['municipio'],
                                 'cp':data['codigo_postal'],'colonia':data['colonia']})
        if 'rfc' in attrs:
            attrs['rfc']=validar_rfc(attrs['rfc'])
        if 'telefono' in attrs and not TELEFONO_RE.fullmatch(attrs['telefono'].strip()):
            raise serializers.ValidationError({'telefono':'Introduce teléfono válido, con 7 a 25 caracteres.'})
        if 'tipo' in attrs and attrs['tipo']==Sucursal.TIPO_CENTRAL:
            centrales=Sucursal.objects.filter(tipo=Sucursal.TIPO_CENTRAL)
            if self.instance: centrales=centrales.exclude(pk=self.instance.pk)
            if centrales.exists():
                raise serializers.ValidationError({'tipo':'Ya existe un almacén central.'})
        return attrs
