from django.contrib import admin
from django.urls import include, path
from .views import health

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/health/', health, name='health'),
    path('api/v1/', include('apps.identidad.api.urls')),
    path('api/v1/sync/', include('apps.sync_central.api.urls')),
]
