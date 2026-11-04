from django.urls import path
from .views import BootstrapView, CambiosView, ConfirmacionView, CredencialesView

urlpatterns = [
    path('bootstrap/', BootstrapView.as_view(), name='sync-bootstrap'),
    path('cambios/', CambiosView.as_view(), name='sync-cambios'),
    path('ack/', ConfirmacionView.as_view(), name='sync-ack'),
    path('credenciales/', CredencialesView.as_view(), name='sync-credenciales'),
]
