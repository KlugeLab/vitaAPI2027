from rest_framework.routers import DefaultRouter
from apps.identidad.api.views import (
    EmpleadoViewSet, RolViewSet, CatalogoPermisoViewSet,
    SucursalViewSet, AsignacionViewSet,
)

router = DefaultRouter()
router.register('empleados', EmpleadoViewSet, basename='empleados')
router.register('roles', RolViewSet, basename='roles')
router.register('permisos', CatalogoPermisoViewSet, basename='permisos')
router.register('sucursales', SucursalViewSet, basename='sucursales')
router.register('asignaciones', AsignacionViewSet, basename='asignaciones')
urlpatterns = router.urls
