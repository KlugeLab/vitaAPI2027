"""Ejemplo: python manage.py provisionar_sucursal --codigo SUC-001"""
import hashlib
import secrets
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.organizacion.models import Sucursal
from apps.sync_central.models import InstalacionSucursal


class Command(BaseCommand):
    help = 'Crea/rota la credencial técnica de una sucursal. Copiar token una sola vez.'

    def add_arguments(self, parser):
        parser.add_argument('--codigo', required=True)
        parser.add_argument('--rotar', action='store_true')

    def handle(self, *args, **options):
        try:
            sucursal = Sucursal.objects.get(codigo=options['codigo'], activa=True)
        except Sucursal.DoesNotExist as exc:
            raise CommandError('Sucursal inexistente o inactiva.') from exc
        with transaction.atomic():
            inst, creada = InstalacionSucursal.objects.select_for_update().get_or_create(
                sucursal=sucursal, defaults={'activa': True}
            )
            if not creada and not options['rotar'] and inst.token_sha256:
                raise CommandError('Ya existe; usa --rotar para sustituir el token anterior.')
            token = secrets.token_urlsafe(48)
            inst.token_sha256 = hashlib.sha256(token.encode('utf-8')).hexdigest()
            inst.activa = True
            inst.save(update_fields=['token_sha256','activa'])
        self.stdout.write('UUID_INSTALACION=' + str(inst.pk))
        self.stdout.write('TOKEN_INSTALACION=' + token)
        self.stdout.write(self.style.WARNING(
            'Guarda estos valores únicamente en el .env de SSucursalAPI. '            'El token NO puede recuperarse después; solo rotarse.'
        ))
