from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.organizacion.models import Estado, Municipio, CodigoPostal, Colonia, Sucursal, Proveedor, LlaveProveedorSucursal
from apps.identidad.services.roles import crear_rol

class DatosSucursalTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username='admin_lab', codigo_empleado='ADM-LAB',email='admin@ejemplo.local',password='ClavePruebaNoReal#2026')
        self.client=APIClient()
        self.client.force_authenticate(user=self.admin)
        estado=Estado.objects.create(clave='31',nombre='Yucatán')
        muni=Municipio.objects.create(estado=estado,clave='050',nombre='Mérida')
        cp=CodigoPostal.objects.create(municipio=muni,codigo='97000')
        col=Colonia.objects.create(codigo_postal=cp,nombre='Centro')
        self.data={'codigo':'SUC-X','nombre':'Sucursal de prueba','tipo':'SUCURSAL',
                   'estado':'31','municipio':str(muni.pk),'codigo_postal':str(cp.pk),'colonia':str(col.pk),
                   'calle':'Calle 1','numero_exterior':'100','domicilio_fiscal':'Calle 1 No. 100, Centro',
                   'rfc':'ABCD800101AA1','correo':'prueba@example.local','telefono':'9991234567','activa':True}

    def test_crear_sucursal_con_domicilio(self):
        resp=self.client.post('/api/v1/sucursales/',self.data,format='json',HTTP_HOST='127.0.0.1')
        self.assertEqual(resp.status_code,201,resp.content)
        self.assertEqual(resp.data['estado_nombre'],'Yucatán')
        self.assertEqual(resp.data['codigo_postal_texto'],'97000')

    def test_rfc_invalido_no_se_guarda(self):
        data={**self.data,'rfc':'NO_VALIDO'}
        resp=self.client.post('/api/v1/sucursales/',data,format='json',HTTP_HOST='127.0.0.1')
        self.assertEqual(resp.status_code,400)
        self.assertEqual(Sucursal.objects.count(),0)

    def test_jerarquia_postal_debe_coincidir(self):
        otro=Estado.objects.create(clave='04',nombre='Campeche')
        data={**self.data,'estado':otro.pk}
        resp=self.client.post('/api/v1/sucursales/',data,format='json',HTTP_HOST='127.0.0.1')
        self.assertEqual(resp.status_code,400)

    def test_tipo_central_es_unico(self):
        d={**self.data,'tipo':'CENTRAL'}
        a=self.client.post('/api/v1/sucursales/',d,format='json',HTTP_HOST='127.0.0.1')
        self.assertEqual(a.status_code,201,a.content)
        d['codigo']='SUC-Y'
        b=self.client.post('/api/v1/sucursales/',d,format='json',HTTP_HOST='127.0.0.1')
        self.assertEqual(b.status_code,400)

    def test_proveedor_llave_oculta(self):
        creado=self.client.post('/api/v1/sucursales/',self.data,format='json',HTTP_HOST='127.0.0.1')
        self.assertEqual(creado.status_code,201,creado.content)
        prov=self.client.post('/api/v1/proveedores/',{'codigo':'PR01','nombre':'Mayorista prueba'},format='json',HTTP_HOST='127.0.0.1')
        self.assertEqual(prov.status_code,201,prov.content)
        llave=self.client.post('/api/v1/llaves-proveedor/',{'sucursal':creado.data['uuid'],'proveedor':prov.data['uuid'],'llave':'LLAVE-PRUEBA-1234'},format='json',HTTP_HOST='127.0.0.1')
        self.assertEqual(llave.status_code,201,llave.content)
        self.assertNotIn('llave',llave.data)
        self.assertTrue(llave.data['llave_mascara'].endswith('1234'))

class RolEstadoTests(TestCase):
    def test_rol_puede_desactivarse_y_reactivarse_con_evento(self):
        usuario=get_user_model().objects.create_superuser(username='adminrol',codigo_empleado='ADMROL',email='test@ejemplo.local',password='ClavePruebaNoReal#2026')
        cliente=APIClient();cliente.force_authenticate(user=usuario)
        rol=crear_rol(codigo='RTEST',nombre='Rol prueba')
        r=cliente.patch(f'/api/v1/roles/{rol.pk}/',{'activo':False},format='json',HTTP_HOST='127.0.0.1')
        self.assertEqual(r.status_code,200,r.content)
        self.assertFalse(r.data['activo'])
        r=cliente.patch(f'/api/v1/roles/{rol.pk}/',{'activo':True},format='json',HTTP_HOST='127.0.0.1')
        self.assertEqual(r.status_code,200,r.content)
        self.assertTrue(r.data['activo'])
