from rest_framework.routers import DefaultRouter
from apps.identidad.api.views import (
    EmpleadoViewSet, RolViewSet, CatalogoPermisoViewSet,
    SucursalViewSet, AsignacionViewSet,
)

from apps.organizacion.api import (
    EstadoViewSet, MunicipioViewSet, CodigoPostalViewSet, ColoniaViewSet,
    ProveedorViewSet, LlaveProveedorViewSet,
)

router = DefaultRouter()
router.register('empleados', EmpleadoViewSet, basename='empleados')
router.register('roles', RolViewSet, basename='roles')
router.register('permisos', CatalogoPermisoViewSet, basename='permisos')
router.register('sucursales', SucursalViewSet, basename='sucursales')
router.register('asignaciones', AsignacionViewSet, basename='asignaciones')
router.register('ubicaciones/estados', EstadoViewSet, basename='ubicaciones-estados')
router.register('ubicaciones/municipios', MunicipioViewSet, basename='ubicaciones-municipios')
router.register('ubicaciones/codigos-postales', CodigoPostalViewSet, basename='ubicaciones-cp')
router.register('ubicaciones/colonias', ColoniaViewSet, basename='ubicaciones-colonias')
router.register('proveedores', ProveedorViewSet, basename='proveedores')
router.register('llaves-proveedor', LlaveProveedorViewSet, basename='llaves-proveedor')
urlpatterns = router.urls
