from django.core.management.base import BaseCommand
from apps.sync_central.services.publicador import publicar_todos

class Command(BaseCommand):
    help = 'Publica eventos outbox confirmados, asignando secuencia global.'

    def handle(self, *args, **kwargs):
        self.stdout.write(f'Eventos secuenciados: {publicar_todos()}')
