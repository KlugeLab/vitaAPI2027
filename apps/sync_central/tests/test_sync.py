import hashlib
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from apps.organizacion.models import Sucursal
from apps.sync_central.models import InstalacionSucursal, EventoSincronizacion
from apps.sync_central.services.publicador import publicar_todos
from apps.identidad.services.sucursales import crear_sucursal
from apps.identidad.services.roles import crear_rol, crear_permiso, reemplazar_permisos_rol
from apps.identidad.services.empleados import crear_empleado
from apps.identidad.services.asignaciones import asignar_rol_sucursal


@override_settings(DEBUG=False)
class SyncCentralTest(TestCase):
    def setUp(self):
        self.sucursal = crear_sucursal(codigo='SUC-001', nombre='Prueba')
        self.instalacion = InstalacionSucursal.objects.create(
            sucursal=self.sucursal,
            token_sha256=hashlib.sha256(b'A'*64).hexdigest()
        )
        self.usuario = crear_empleado(
            username='caja01', password='PruebaSegura2026!A', codigo_empleado='EMP-001'
        )
        self.rol = crear_rol(codigo='CAJERO', nombre='Cajero')
        self.permiso = crear_permiso(
            app_label='identidad', modelo='empleado', codename='view_empleado',
            descripcion='Consultar empleados'
        )
        reemplazar_permisos_rol(rol_uuid=self.rol.pk, permisos_uuid=[self.permiso.pk])
        self.asignacion = asignar_rol_sucursal(
            empleado_uuid=self.usuario.pk, rol_uuid=self.rol.pk,
            sucursal_uuid=self.sucursal.pk,
        )
        self.client = APIClient()
        self.headers = {
            'HTTP_AUTHORIZATION': 'Bearer ' + 'A'*64,
            'HTTP_X_VITA_INSTALLATION': str(self.instalacion.pk),
            'HTTP_HOST': '127.0.0.1',
        }

    def test_bootstrap_filtrado_y_sin_hash(self):
        r = self.client.get('/api/v1/sync/bootstrap/', secure=True, **self.headers)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(len(r.data['asignaciones']), 1)
        self.assertNotIn('password', str(r.data).lower())
        self.assertEqual(r.data['asignaciones'][0]['rol']['codigo'], 'CAJERO')

    def test_token_incorrecto_no_autorizado(self):
        headers = dict(self.headers, HTTP_AUTHORIZATION='Bearer ' + 'B'*64)
        r = self.client.get('/api/v1/sync/bootstrap/', secure=True, **headers)
        self.assertEqual(r.status_code, 401)

    def test_credenciales_separadas(self):
        r = self.client.post('/api/v1/sync/credenciales/', {'versions': {}},
                             format='json', secure=True, **self.headers)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(len(r.data['credentials']), 1)
        self.assertEqual(r.data['credentials'][0]['password_hash'], self.usuario.password)

    def test_cambios_y_confirmacion(self):
        publicar_todos()
        r = self.client.get('/api/v1/sync/cambios/?cursor=0', secure=True, **self.headers)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn('asignacion', [e['entity'] for e in r.data['events']])
        ack = self.client.post('/api/v1/sync/ack/', {
            'cursor': r.data['next_cursor']
        }, format='json', secure=True, **self.headers)
        self.assertEqual(ack.status_code, 200, ack.content)
        self.assertGreater(ack.data['confirmados'], 0)

    def test_http_rechazado(self):
        r = self.client.get('/api/v1/sync/bootstrap/', secure=False, **self.headers)
        self.assertEqual(r.status_code, 401)
