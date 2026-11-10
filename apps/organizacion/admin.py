"""Consulta técnica; la escritura debe pasar por API/servicios para emitir eventos."""
from django.contrib import admin
from .models import Sucursal, Estado, Municipio, CodigoPostal, Colonia, Proveedor, LlaveProveedorSucursal

class SoloLectura(admin.ModelAdmin):
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False

@admin.register(Sucursal)
class SucursalAdmin(SoloLectura):
    list_display=('codigo','nombre','tipo','activa','version')

@admin.register(Proveedor)
class ProveedorAdmin(SoloLectura):
    list_display=('codigo','nombre','activo')

@admin.register(LlaveProveedorSucursal)
class LlaveProveedorSucursalAdmin(SoloLectura):
    list_display=('sucursal','proveedor','activa')  # No mostrar la llave íntegra.

for modelo in (Estado,Municipio,CodigoPostal,Colonia):
    admin.site.register(modelo,SoloLectura)
