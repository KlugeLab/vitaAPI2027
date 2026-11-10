"""Revoca acceso técnico de una sucursal de forma explícita y auditada."""
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from apps.organizacion.models import Sucursal
from apps.sync_central.models import InstalacionSucursal

class Command(BaseCommand):
    help='Desactiva la instalación técnica de una sucursal antes de desactivar la ubicación.'
    def add_arguments(self,parser):
        parser.add_argument('--codigo',required=True)
        parser.add_argument('--confirmar',action='store_true')
    @transaction.atomic
    def handle(self,*args,**opts):
        if not opts['confirmar']:
            raise CommandError('Requiere --confirmar. Esta acción impide sincronización de la sucursal.')
        try:sucursal=Sucursal.objects.get(codigo=opts['codigo'])
        except Sucursal.DoesNotExist as exc:raise CommandError('Sucursal no existe.') from exc
        n=InstalacionSucursal.objects.filter(sucursal=sucursal,activa=True).update(activa=False)
        self.stdout.write(self.style.SUCCESS(f'Instalaciones desactivadas: {n}.'))
