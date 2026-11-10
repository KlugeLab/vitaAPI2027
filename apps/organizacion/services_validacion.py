"""Validación de jerarquía postal, RFC y contacto."""
import re
from datetime import datetime
from rest_framework import serializers
from apps.organizacion.models import Estado, Municipio, CodigoPostal, Colonia

RFC_RE=re.compile(r'^(?:[A-ZÑ&]{3}|[A-ZÑ&]{4})\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])[A-Z0-9]{3}$')
TELEFONO_RE=re.compile(r'^\+?[0-9][0-9() .\-]{6,24}$')

def validar_rfc(value):
    value=str(value or '').strip().upper()
    if not RFC_RE.fullmatch(value):
        raise serializers.ValidationError('RFC mexicano inválido: 12 o 13 caracteres, incluyendo fecha y homoclave.')
    # Verifica que el calendario sea coherente, sin simular validación ante el SAT.
    base=4 if len(value)==13 else 3
    fecha=value[base:base+6]
    try:
        yy=int(fecha[:2]); mes=int(fecha[2:4]); dia=int(fecha[4:6])
        datetime(2000+yy,mes,dia)
    except ValueError:
        raise serializers.ValidationError('La fecha incluida en el RFC no es válida.')
    return value

def validar_jerarquia(estado,municipio,cp,colonia):
    if not estado or not municipio or not cp or not colonia:
        raise serializers.ValidationError({'estado':'Selecciona Estado, Municipio, Código Postal y Colonia.'})
    if municipio.estado_id != estado.pk:
        raise serializers.ValidationError({'municipio':'El municipio no corresponde al estado seleccionado.'})
    if cp.municipio_id != municipio.pk:
        raise serializers.ValidationError({'codigo_postal':'El código postal no pertenece al municipio.'})
    if colonia.codigo_postal_id != cp.pk:
        raise serializers.ValidationError({'colonia':'La colonia no corresponde al código postal.'})
