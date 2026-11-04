"""Consulta de empleados. Escrituras por servicios/REST para no saltar el outbox."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Empleado


@admin.register(Empleado)
class EmpleadoAdmin(UserAdmin):
    list_display = ('username', 'codigo_empleado', 'first_name', 'last_name', 'is_active', 'is_staff')
    search_fields = ('username', 'codigo_empleado', 'first_name', 'last_name')
    readonly_fields = ('id', 'version', 'version_credenciales', 'actualizado_en')
    fieldsets = UserAdmin.fieldsets + (
        ('Identidad Vita Suite', {'fields': (
            'id', 'codigo_empleado', 'version', 'version_credenciales', 'actualizado_en',
        )}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Identidad Vita Suite', {'fields': ('codigo_empleado',)}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Bloquear cambios de Group desde Django Admin: de otro modo se podrían
# modificar roles sin producir eventos de sincronización.
from django.contrib.auth.models import Group
from django.contrib.admin.sites import NotRegistered

try:
    admin.site.unregister(Group)
except NotRegistered:
    pass


@admin.register(Group)
class GrupoConsultaAdmin(admin.ModelAdmin):
    list_display = ('name',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
