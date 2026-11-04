"""Pruebas de integración contra PostgreSQL de pruebas configurado por Django."""
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.identidad.models import Rol, RolPermiso
from apps.identidad.services.asignaciones import asignar_rol_sucursal
from apps.identidad.services.empleados import crear_empleado, desactivar_empleado
from apps.identidad.services.roles import crear_permiso, crear_rol, reemplazar_permisos_rol
from apps.identidad.services.sucursales import crear_sucursal
from apps.sync_central.models import DestinoEvento, EventoSincronizacion, InstalacionSucursal


class ServiciosIdentidadTest(TestCase):
    def setUp(self):
        self.sucursal = crear_sucursal(codigo='SUC-001', nombre='Sucursal piloto')
        self.instalacion = InstalacionSucursal.objects.create(sucursal=self.sucursal)
        self.empleado = crear_empleado(
            username='cajero01', password='ClavePruebaSegura2026!',
            codigo_empleado='EMP-001', first_name='Juan', last_name='Pérez',
        )
        self.rol = crear_rol(codigo='CAJERO', nombre='Cajero')

    def test_no_registra_claves_en_outbox(self):
        eventos = EventoSincronizacion.objects.filter(tipo_entidad='empleado')
        self.assertEqual(eventos.count(), 1)
        self.assertNotIn('password', str(eventos.first().payload).lower())
        self.assertTrue(self.empleado.check_password('ClavePruebaSegura2026!'))

    def test_catalogo_y_permisos_rol(self):
        p = crear_permiso(app_label='ventas', modelo='venta',
                         codename='add_venta', descripcion='Registrar venta')
        rol = reemplazar_permisos_rol(rol_uuid=self.rol.pk, permisos_uuid=[p.pk])
        self.assertEqual(rol.version, 2)
        self.assertTrue(RolPermiso.objects.filter(rol=rol, permiso=p).exists())

    def test_asignacion_registra_destino_y_dependencias(self):
        asignacion = asignar_rol_sucursal(
            empleado_uuid=self.empleado.pk, rol_uuid=self.rol.pk,
            sucursal_uuid=self.sucursal.pk,
        )
        evento = EventoSincronizacion.objects.get(
            tipo_entidad='asignacion', entidad_uuid=asignacion.pk
        )
        self.assertTrue(DestinoEvento.objects.filter(
            evento=evento, instalacion=self.instalacion
        ).exists())
        self.assertEqual(evento.payload['empleado']['uuid'], str(self.empleado.pk))
        self.assertEqual(evento.payload['rol']['uuid'], str(self.rol.pk))
        self.assertNotIn('password', str(evento.payload).lower())

    def test_desactivacion_publica_a_sucursal(self):
        asignar_rol_sucursal(
            empleado_uuid=self.empleado.pk, rol_uuid=self.rol.pk,
            sucursal_uuid=self.sucursal.pk,
        )
        desactivar_empleado(empleado_uuid=self.empleado.pk)
        evento = EventoSincronizacion.objects.filter(
            tipo_entidad='empleado', tipo_operacion='deactivated'
        ).get()
        self.assertFalse(evento.payload['is_active'])
        self.assertEqual(evento.destinos.count(), 1)

    def test_fallo_outbox_revierte_alta(self):
        with patch('apps.identidad.services.empleados.registrar_evento',
                   side_effect=RuntimeError('Outbox no disponible')):
            with self.assertRaises(RuntimeError):
                crear_empleado(username='retroceso', password='ClavePruebaSegura2026!',
                               codigo_empleado='EMP-RET')
        self.assertFalse(get_user_model().objects.filter(username='retroceso').exists())


class EndpointsIdentidadTest(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username='administrador', password='AdminTemporalSeguro2026!',
            email='admin@example.invalid', codigo_empleado='ADM-001',
        )
        self.cliente = APIClient()
        self.cliente.force_authenticate(user=self.admin)

    def test_alta_de_empleado_por_api(self):
        respuesta = self.cliente.post('/api/v1/empleados/', {
            'username': 'empleado02', 'password': 'OtraClaveSegura2026!',
            'codigo_empleado': 'EMP-002', 'first_name': 'María',
        }, format='json')
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertNotIn('password', respuesta.data)
        self.assertEqual(EventoSincronizacion.objects.filter(
            tipo_entidad='empleado'
        ).count(), 1)

    def test_api_anonymous_no_permitida(self):
        cliente = APIClient()
        respuesta = cliente.get('/api/v1/empleados/')
        self.assertIn(respuesta.status_code, (401, 403))
