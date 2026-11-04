"""Outbox de eventos centrales.

Este módulo NO publica ni secuencia eventos. Los escribe en la misma
transacción que el cambio de negocio; el publicador se hará en otra etapa.
"""
from django.db import transaction
from apps.sync_central.models import DestinoEvento, EventoSincronizacion, InstalacionSucursal


def registrar_evento(*, tipo_entidad, tipo_operacion, entidad_uuid,
                    version_entidad, payload, sucursales=()):
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError('registrar_evento requiere transaction.atomic()')

    evento = EventoSincronizacion.objects.create(
        tipo_entidad=tipo_entidad,
        tipo_operacion=tipo_operacion,
        entidad_uuid=entidad_uuid,
        version_entidad=version_entidad,
        schema_version=1,
        payload=payload,
    )
    identificadores = set(sucursales)
    if identificadores:
        instalaciones = InstalacionSucursal.objects.filter(
            activa=True, sucursal_id__in=identificadores
        )
        DestinoEvento.objects.bulk_create([
            DestinoEvento(evento=evento, instalacion=i) for i in instalaciones
        ])
    return evento
