"""Catálogo de estados por clave INEGI/SEPOMEX; no incluye municipios ni CP."""
from django.core.management.base import BaseCommand
from apps.organizacion.models import Estado

ENTIDADES = [
('01','Aguascalientes'),('02','Baja California'),('03','Baja California Sur'),
('04','Campeche'),('05','Coahuila de Zaragoza'),('06','Colima'),('07','Chiapas'),
('08','Chihuahua'),('09','Ciudad de México'),('10','Durango'),('11','Guanajuato'),
('12','Guerrero'),('13','Hidalgo'),('14','Jalisco'),('15','México'),
('16','Michoacán de Ocampo'),('17','Morelos'),('18','Nayarit'),('19','Nuevo León'),
('20','Oaxaca'),('21','Puebla'),('22','Querétaro'),('23','Quintana Roo'),
('24','San Luis Potosí'),('25','Sinaloa'),('26','Sonora'),('27','Tabasco'),
('28','Tamaulipas'),('29','Tlaxcala'),('30','Veracruz de Ignacio de la Llave'),
('31','Yucatán'),('32','Zacatecas'),
]

class Command(BaseCommand):
    help='Registra las 32 entidades federativas. Comando idempotente.'
    def handle(self,*args,**kwargs):
        for clave, nombre in ENTIDADES:
            Estado.objects.update_or_create(clave=clave,defaults={'nombre':nombre})
        self.stdout.write(self.style.SUCCESS('32 entidades federativas registradas.'))
