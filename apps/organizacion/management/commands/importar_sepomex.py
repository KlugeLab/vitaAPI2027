"""Importador del TXT separado por | del catálogo postal de Correos de México.

Se ejecuta conscientemente por el operador después de descargar el archivo
desde su fuente oficial. No se empaquetan ni inventan datos postales.
"""
import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.organizacion.models import Estado,Municipio,CodigoPostal,Colonia

class Command(BaseCommand):
    help='Importa archivo TXT SEPOMEX con columnas d_codigo, d_asenta, d_tipo_asenta, D_mnpio, d_estado, c_estado, c_mnpio.'
    def add_arguments(self,parser):
        parser.add_argument('--archivo',required=True)

    @transaction.atomic
    def handle(self,*args,**opts):
        path=Path(opts['archivo'])
        if not path.is_file():raise CommandError(f'Archivo no encontrado: {path}')
        raw=path.read_bytes()
        try: contenido=raw.decode('utf-8-sig')
        except UnicodeDecodeError:contenido=raw.decode('cp1252')
        import io
        lector=csv.DictReader(io.StringIO(contenido),delimiter='|')
        req={'d_codigo','d_asenta','d_tipo_asenta','D_mnpio','d_estado','c_estado','c_mnpio'}
        if not req.issubset(set(lector.fieldnames or [])):
            raise CommandError('Columnas SEPOMEX no reconocidas. Revisa que hayas descargado TXT delimitado por |.')
        total=0; omitidas=0
        for fila in lector:
            try:
                ec=(fila.get('c_estado') or '').strip().zfill(2)
                mc=(fila.get('c_mnpio') or '').strip().zfill(3)
                cp=(fila.get('d_codigo') or '').strip()
                colonia=(fila.get('d_asenta') or '').strip()
                municipio_nombre=(fila.get('D_mnpio') or '').strip()
                estado_nombre=(fila.get('d_estado') or '').strip()
                if not (len(ec)==2 and ec.isdigit() and len(mc)==3 and mc.isdigit() and
                        len(cp)==5 and cp.isdigit() and colonia and municipio_nombre and estado_nombre):
                    omitidas+=1;continue
                estado,_=Estado.objects.get_or_create(clave=ec,defaults={'nombre':estado_nombre})
                municipio,_=Municipio.objects.get_or_create(estado=estado,clave=mc,defaults={'nombre':municipio_nombre})
                codigo,_=CodigoPostal.objects.get_or_create(municipio=municipio,codigo=cp)
                Colonia.objects.get_or_create(codigo_postal=codigo,nombre=colonia,
                                             defaults={'tipo':(fila.get('d_tipo_asenta') or '')[:80]})
                total+=1
            except (ValueError,TypeError):
                omitidas+=1
        if not total:raise CommandError('No se importó ningún registro: comprueba el archivo.')
        self.stdout.write(self.style.SUCCESS(f'Registros leídos/importados: {total}; omitidos: {omitidas}.'))
