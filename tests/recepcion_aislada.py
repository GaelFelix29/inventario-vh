"""Pruebas aisladas: no cargan .env ni crean clientes de producción."""
import ast
import io
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
conexion = types.ModuleType('database.conexion')
conexion.engine = MagicMock()
supabase_config = types.ModuleType('supabase_config')
supabase_config.supabase = MagicMock()
sys.modules['database.conexion'] = conexion
sys.modules['supabase_config'] = supabase_config

from flask import Flask, render_template
from PIL import Image
from routes import solicitudes
from database import maquinarias, documentos

class RecepcionTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder=str(ROOT / 'templates'))
        self.app.secret_key = 'solo-pruebas'
        self.app.logger.disabled = True
        solicitudes.registrar_rutas_solicitudes(self.app, lambda f: f, lambda **kw: None)
        self.app.add_url_rule('/activo/<id_activo>', 'expediente_maquinaria', lambda id_activo: '')
        self.app.add_url_rule('/qr/<id_activo>', 'maquinaria_qr', lambda id_activo: '')
        self.client = self.app.test_client()
        self.rol('Mantenimiento')
        self.almacen = MagicMock()
        self.almacen.get_public_url.return_value = 'https://example.test/foto.png'
        self.storage_patch = patch.object(solicitudes, 'supabase')
        self.storage = self.storage_patch.start()
        self.storage.storage.from_.return_value = self.almacen
        self.addCleanup(self.storage_patch.stop)
        self.confirm_patch = patch.object(solicitudes, 'confirmar_recepcion_activo')
        self.confirmar = self.confirm_patch.start()
        self.addCleanup(self.confirm_patch.stop)

    def rol(self, rol):
        with self.client.session_transaction() as session:
            session['rol'] = rol
            session['nombre'] = 'Oscar'

    def post(self, contenido=None, nombre='foto.png', **extra):
        data = {'origen': 'qr', 'observaciones': '  Recibido completo  ', **extra}
        if contenido is not None:
            data['foto_recepcion'] = (io.BytesIO(contenido), nombre)
        return self.client.post('/maquinarias/ACT-1/confirmar-recepcion', data=data)

    def foto(self):
        data = io.BytesIO()
        Image.new('RGB', (2, 2)).save(data, format='PNG')
        return data.getvalue()

    def test_roles_autorizados_y_registro(self):
        for rol in ['Administrador', 'Mantenimiento']:
            with self.subTest(rol=rol):
                self.rol(rol)
                response = self.post(self.foto())
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.location.endswith('/qr/ACT-1'))
                args = self.confirmar.call_args.args
                self.assertEqual(args[:2], ('ACT-1', 'Oscar'))
                self.assertEqual(args[3], 'Recibido completo')
                self.assertEqual(args[2]['content_type'], 'image/png')

    def test_get_no_confirma(self):
        response = self.client.get('/maquinarias/ACT-1/confirmar-recepcion')
        self.assertEqual(response.status_code, 405)
        self.confirmar.assert_not_called()

    def test_rol_no_autorizado(self):
        self.rol('Consulta')
        self.post(self.foto())
        self.almacen.upload.assert_not_called()
        self.confirmar.assert_not_called()

    def test_sin_foto_o_imagen_falsa(self):
        self.post()
        self.post(b'no es imagen')
        self.post(self.foto(), nombre='foto.svg')
        self.post(b'x' * (8 * 1024 * 1024 + 1))
        self.post(self.foto(), observaciones='x' * 501)
        self.almacen.upload.assert_not_called()
        self.confirmar.assert_not_called()

    def test_error_upload_no_confirma(self):
        self.almacen.upload.side_effect = RuntimeError('fallo simulado')
        self.post(self.foto())
        self.confirmar.assert_not_called()
        self.almacen.remove.assert_not_called()

    def test_traslado_finalizado_limpia_solo_archivo_nuevo(self):
        self.confirmar.side_effect = ValueError('No existe un traslado en proceso')
        self.post(self.foto())
        ruta = self.almacen.upload.call_args.kwargs['path']
        self.almacen.remove.assert_called_once_with([ruta])

    def test_url_ausente_no_confirma(self):
        self.almacen.get_public_url.return_value = None
        self.post(self.foto())
        self.confirmar.assert_not_called()
        self.almacen.remove.assert_called_once()

    def test_formulario_render_y_sintaxis(self):
        with self.app.test_request_context():
            html = render_template('partials/recepcion.html',
                activo_recepcion={'id_activo': 'ACT-1'}, origen_recepcion='qr', csrf_token=lambda: 'csrf-prueba')
        self.assertIn('multipart/form-data', html)
        self.assertIn('capture', html)
        self.assertIn('csrf-prueba', html)
        for nombre in ['expediente_maquinaria.html', 'maquinaria_qr/inicio.html', 'maquinaria_qr/evidencias.html']:
            self.app.jinja_env.parse((ROOT / 'templates' / nombre).read_text(encoding='utf-8'))
        for nombre in ['routes/solicitudes.py', 'database/documentos.py', 'database/maquinarias.py']:
            ast.parse((ROOT / nombre).read_text(encoding='utf-8'))

class TransaccionTest(unittest.TestCase):
    def test_evidencia_estado_auditoria_misma_transaccion(self):
        engine = MagicMock()
        conn = engine.begin.return_value.__enter__.return_value
        conn.execute.return_value.first.return_value = ('ACT-1',)
        conn.execute.return_value.mappings.return_value.first.return_value = {'id': 7, 'ubicacion_destino': 'Destino'}
        evidencia = dict(url='https://example.test/foto.png', nombre_original='foto.png', nombre_archivo='uuid.png', ruta='ACT-1/uuid.png')
        with patch.object(maquinarias, 'engine', engine), patch.object(maquinarias, 'registrar_movimiento') as auditoria:
            maquinarias.confirmar_recepcion_activo('ACT-1', 'Oscar', evidencia, 'Completo')
        llamadas = conn.execute.call_args_list
        self.assertIn('FOR UPDATE', str(llamadas[0].args[0]))
        self.assertIn('FOR UPDATE', str(llamadas[1].args[0]))
        self.assertIn('INSERT INTO documentos_maquinaria', str(llamadas[2].args[0]))
        self.assertEqual(llamadas[2].args[1]['usuario'], 'Oscar')
        self.assertIn('Traslado #7', llamadas[2].args[1]['descripcion'])
        self.assertIn('UPDATE maquinarias', str(llamadas[3].args[0]))
        self.assertEqual(llamadas[4].args[1], {'solicitud': 7, 'usuario': 'Oscar'})
        self.assertIn('fecha_finalizacion = NOW()', str(llamadas[4].args[0]))
        self.assertIs(auditoria.call_args.kwargs['conn'], conn)

    def test_sin_traslado_no_guarda_ni_actualiza(self):
        engine = MagicMock()
        conn = engine.begin.return_value.__enter__.return_value
        conn.execute.return_value.mappings.return_value.first.return_value = None
        with patch.object(maquinarias, 'engine', engine):
            with self.assertRaises(ValueError):
                maquinarias.confirmar_recepcion_activo('ACT-1', 'Oscar', {'url': 'url'})
        self.assertEqual(conn.execute.call_count, 2)
        self.assertIs(engine.begin.return_value.__exit__.call_args.args[0], ValueError)

    def test_fallo_documento_sale_con_error_antes_del_estado(self):
        engine = MagicMock()
        conn = engine.begin.return_value.__enter__.return_value
        conn.execute.return_value.mappings.return_value.first.return_value = {'id': 7}
        with patch.object(maquinarias, 'engine', engine), patch.object(maquinarias, 'guardar_documento_bd', side_effect=RuntimeError('fallo')):
            with self.assertRaises(RuntimeError):
                maquinarias.confirmar_recepcion_activo('ACT-1', 'Oscar', {'url': 'url', 'nombre_original': 'f', 'nombre_archivo': 'f', 'ruta': 'f'})
        self.assertEqual(conn.execute.call_count, 2)
        self.assertIs(engine.begin.return_value.__exit__.call_args.args[0], RuntimeError)

if __name__ == '__main__':
    unittest.main()
