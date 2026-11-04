"""Publicador outbox de una única secuencia confirmada por transacción.

SELECT FOR UPDATE sobre ContadorPublicacion serializa a los concurrentes.
Si una transacción que produce un evento no ha confirmado, no es visible
para el publicador y se ordenará en un lote posterior.
"""
from django.db import transaction
from django.utils import timezone
from apps.sync_central.models import ContadorPublicacion, EventoSincronizacion


def publicar_pendientes(limite=500):
    if not 1 <= limite <= 2000:
        raise ValueError('limite fuera del rango 1..2000')
    with transaction.atomic():
        contador, _ = ContadorPublicacion.objects.get_or_create(pk=1, defaults={'ultimo_valor': 0})
        contador = ContadorPublicacion.objects.select_for_update().get(pk=1)
        pendientes = list(
            EventoSincronizacion.objects
            .select_for_update()
            .filter(secuencia_publicacion__isnull=True)
            .order_by('creado_en', 'event_id')[:limite]
        )
        for evento in pendientes:
            contador.ultimo_valor += 1
            evento.secuencia_publicacion = contador.ultimo_valor
            evento.publicado_en = timezone.now()
        if pendientes:
            EventoSincronizacion.objects.bulk_update(
                pendientes, ['secuencia_publicacion', 'publicado_en']
            )
            contador.save(update_fields=['ultimo_valor'])
        return len(pendientes)


def publicar_todos(limite=500):
    total = 0
    while True:
        n = publicar_pendientes(limite=limite)
        total += n
        if n < limite:
            return total
