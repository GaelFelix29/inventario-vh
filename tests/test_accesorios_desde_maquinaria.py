"""Pruebas aisladas: no importan credenciales ni acceden a MySQL."""
import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask, render_template, session, abort
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import create_engine, event, text


class AccesoriosDesdeMaquinariaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        conexion = types.ModuleType('database.conexion')
        conexion.engine = None
        sys.modules['database.conexion'] = conexion
        cls.db = importlib.import_module('database.maquinarias')
        cls.servicio = importlib.import_module('services.accesorios_maquinaria')
        cls.rutas = importlib.import_module('routes.accesorios')

    def setUp(self):
        self.engine = create_engine('sqlite://')
        @event.listens_for(self.engine, 'before_cursor_execute', retval=True)
        def adaptar(conn, cursor, statement, parameters, context, executemany):
            if 'CAST(SUBSTRING' in statement:
                statement = "SELECT COALESCE(MAX(CAST(SUBSTR(id_activo, 5) AS INTEGER)),0)+1 FROM maquinarias"
            return statement.replace('FOR UPDATE', '').replace('NOW()', 'CURRENT_TIMESTAMP'), parameters
        self.patches = [patch.object(self.servicio, 'engine', self.engine),
                        patch.object(self.db, 'engine', self.engine)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.engine.dispose)
        with self.engine.begin() as conn:
            for sql in [
                '''CREATE TABLE maquinarias(id_activo TEXT PRIMARY KEY, categoria TEXT,
                   categoria_accesorio_id INTEGER, descripcion TEXT, cantidad INTEGER,
                   marca TEXT, modelo TEXT, numero_serie TEXT, serie_interna TEXT,
                   proveedor TEXT, ubicacion TEXT, fecha_alta TEXT, precio_unitario_us REAL,
                   total_us REAL, valor_mx REAL, observaciones TEXT,
                   es_contenedor INTEGER DEFAULT 0, estado TEXT DEFAULT 'ACTIVO')''',
                '''CREATE TABLE categorias_accesorios(id INTEGER PRIMARY KEY, codigo TEXT, activo INTEGER)''',
                '''CREATE TABLE asignaciones_accesorios(id INTEGER PRIMARY KEY,
                   id_accesorio TEXT NOT NULL REFERENCES maquinarias(id_activo),
                   id_maquinaria TEXT NOT NULL REFERENCES maquinarias(id_activo),
                   estado TEXT, fecha_asignacion TEXT DEFAULT CURRENT_TIMESTAMP,
                   fecha_fin TEXT, asignado_por TEXT, finalizado_por TEXT, observaciones TEXT,
                   CHECK(id_accesorio <> id_maquinaria))''',
                "CREATE UNIQUE INDEX uq_activa ON asignaciones_accesorios(id_accesorio) WHERE estado='ACTIVA'",
                '''CREATE TABLE auditoria(id INTEGER PRIMARY KEY, usuario TEXT, accion TEXT,
                   modulo TEXT, referencia TEXT)''',
                "INSERT INTO categorias_accesorios VALUES(1,'POR_CLASIFICAR',1)",
                "INSERT INTO maquinarias(id_activo,categoria,ubicacion) VALUES('ACT-0001','LLENADORA','PLANTA')",
                "INSERT INTO maquinarias(id_activo,categoria,ubicacion) VALUES('ACT-0002','ACCESORIO','PLANTA')",
                "INSERT INTO maquinarias(id_activo,categoria) VALUES('ACT-0003','LLENADORA')",
            ]:
                conn.execute(text(sql))

    def scalar(self, sql):
        with self.engine.connect() as conn:
            return conn.execute(text(sql)).scalar()

    def crear(self, **datos):
        return self.servicio.registrar_accesorio_maquinaria('ACT-0001', dict(descripcion='Boquilla', **datos), 'Ana')

    def test_alta_asignacion_auditoria_sin_inventar_valor_fecha(self):
        nuevo = self.crear()
        self.assertEqual(nuevo, 'ACT-0004')
        with self.engine.connect() as conn:
            row = conn.execute(text("SELECT * FROM maquinarias WHERE id_activo='ACT-0004'")).mappings().one()
        self.assertEqual(row['cantidad'], 1)
        self.assertEqual(row['ubicacion'], 'PLANTA')
        self.assertEqual(row['serie_interna'], 'SN-0004')
        self.assertIsNone(row['fecha_alta'])
        self.assertIsNone(row['valor_mx'])
        self.assertEqual(self.scalar('SELECT id_maquinaria FROM asignaciones_accesorios'), 'ACT-0001')
        self.assertIn('desconocida', self.scalar('SELECT observaciones FROM asignaciones_accesorios'))
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM auditoria'), 3)

    def test_fallo_asignacion_deshace_alta(self):
        with patch.object(self.servicio, 'asignar_accesorio_maquinaria', side_effect=RuntimeError('fallo')):
            with self.assertRaises(RuntimeError): self.crear()
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM maquinarias'), 3)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM auditoria'), 0)

    def test_fallo_auditoria_deshace_alta_y_asignacion(self):
        with patch.object(self.servicio, 'registrar_movimiento', side_effect=RuntimeError('fallo')):
            with self.assertRaises(RuntimeError): self.crear()
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM maquinarias'), 3)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM asignaciones_accesorios'), 0)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM auditoria'), 0)

    def test_rechaza_destinos_incorrectos(self):
        for destino in ('ACT-0002', 'ACT-9999'):
            with self.assertRaises(ValueError):
                self.servicio.registrar_accesorio_maquinaria(destino, {'descripcion':'Pieza'}, 'Ana')
        for cambio in ("estado='BAJA'", "estado='ACTIVO',es_contenedor=1"):
            with self.engine.begin() as conn:
                conn.execute(text('UPDATE maquinarias SET '+cambio+" WHERE id_activo='ACT-0001'"))
            with self.assertRaises(ValueError): self.crear()
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM maquinarias'), 3)

    def test_campos_invalidos_y_categoria_ausente(self):
        for datos in ({'descripcion':' '}, {'descripcion':'a'*256}, {'descripcion':'Pieza','numero_serie':'a'*151}):
            with self.assertRaises(ValueError):
                self.servicio.registrar_accesorio_maquinaria('ACT-0001', datos, 'Ana')
        with self.engine.begin() as conn: conn.execute(text('DELETE FROM categorias_accesorios'))
        with self.assertRaises(ValueError): self.crear()
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM maquinarias'), 3)

    def test_vinculo_existente_no_reasigna_ni_duplica(self):
        self.db.asignar_accesorio_maquinaria('ACT-0002','ACT-0001','Ana',permitir_reasignacion=False)
        for destino in ('ACT-0001','ACT-0003'):
            with self.assertRaises(ValueError):
                self.db.asignar_accesorio_maquinaria('ACT-0002',destino,'Ana',permitir_reasignacion=False)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM maquinarias'), 3)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM asignaciones_accesorios'), 1)
        # Existing explicit reassignment flow retains its original behavior.
        self.db.asignar_accesorio_maquinaria('ACT-0002','ACT-0003','Ana')
        self.assertEqual(self.scalar("SELECT id_maquinaria FROM asignaciones_accesorios WHERE estado='ACTIVA'"), 'ACT-0003')

    def app(self, csrf=False):
        app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates'))
        app.secret_key = 'pruebas-aisladas'
        app.config['TESTING'] = True
        if csrf: CSRFProtect(app)
        else: app.jinja_env.globals['csrf_token'] = lambda: 'test'
        def login(f):
            from functools import wraps
            @wraps(f)
            def wrapped(*args, **kwargs):
                if not session.get('nombre'): abort(401)
                return f(*args, **kwargs)
            return wrapped
        self.rutas.registrar_rutas_accesorios(app, login)
        app.add_url_rule('/exp/<id_activo>', 'expediente_maquinaria', lambda id_activo: '')
        app.add_url_rule('/qr/<id_activo>', 'maquinaria_qr', lambda id_activo: '')
        return app

    def test_ruta_permisos_y_retorno_web_qr(self):
        app = self.app()
        client = app.test_client()
        url = '/maquinarias/ACT-0001/accesorios/agregar'
        self.assertEqual(client.post(url).status_code,401)
        with client.session_transaction() as s: s.update(nombre='Ana',rol='Visualizador')
        self.assertEqual(client.post(url).status_code,403)
        for origen, prefijo, rol in [('web','/exp/','Administrador'),('qr','/qr/','Administrador')]:
            with client.session_transaction() as s: s['rol'] = rol
            res = client.post(url,data={'modo':'nuevo','descripcion':'Pieza','origen':origen})
            self.assertEqual(res.status_code,302)
            self.assertTrue(res.location.startswith(prefijo))
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM asignaciones_accesorios'),2)

    def test_csrf_y_formulario_por_rol(self):
        client = self.app(csrf=True).test_client()
        with client.session_transaction() as s: s.update(nombre='Ana',rol='Administrador')
        self.assertEqual(client.post('/maquinarias/ACT-0001/accesorios/agregar',data={'modo':'nuevo'}).status_code,400)
        app = self.app()
        with app.test_request_context():
            equipo = {'id_activo':'ACT-0001','estado':'ACTIVO'}
            for rol, esperado in [('Administrador',True),('Mantenimiento',False),('Visualizador',False)]:
                session['rol'] = rol
                html = render_template('partials/agregar_accesorio_maquinaria.html',equipo=equipo,origen_accesorio='web')
                self.assertEqual('Crear y asignar' in html,esperado)
                self.assertEqual('name="modo" value="existente"' in html, rol != 'Visualizador')
                self.assertEqual('name="modo" value="nuevo"' in html, esperado)
            session['rol'] = 'Administrador'
            equipo['estado'] = 'BAJA'
            self.assertNotIn('Crear y asignar',render_template('partials/agregar_accesorio_maquinaria.html',equipo=equipo,origen_accesorio='qr'))

    def test_mantenimiento_no_crea_por_post_directo_pero_asigna(self):
        client = self.app().test_client()
        with client.session_transaction() as s: s.update(nombre='Ana', rol='Mantenimiento')
        for origen in ('web', 'qr'):
            respuesta = client.post('/maquinarias/ACT-0001/accesorios/agregar',
                data={'modo':'nuevo','descripcion':'No crear','origen':origen})
            self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM maquinarias'), 3)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM asignaciones_accesorios'), 0)
        respuesta = client.post('/maquinarias/ACT-0001/accesorios/agregar',
            data={'modo':'existente','id_accesorio':'ACT-0002'})
        self.assertEqual(respuesta.status_code,302)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM asignaciones_accesorios'),1)

    def test_categorias_solo_administrador(self):
        client = self.app().test_client()
        for rol in ('Mantenimiento', 'Visualizador', 'Administrador'):
            with client.session_transaction() as s: s.update(nombre='Ana', rol=rol)
            for url, funcion in (
                ('/accesorios/ACT-0002/categoria/crear','crear_categoria_y_clasificar_accesorio'),
                ('/accesorios/ACT-0002/categoria','actualizar_categoria_accesorio')):
                with patch.object(self.rutas, funcion, return_value={'nombre':'Prueba'}) as ejecutar:
                    client.post(url, data={'nombre_categoria':'Prueba','categoria_accesorio_id':'1'})
                    self.assertEqual(ejecutar.call_count, int(rol == 'Administrador'))

    def test_mantenimiento_intercambia_y_libera(self):
        client = self.app().test_client()
        with client.session_transaction() as s: s.update(nombre='Ana', rol='Mantenimiento')
        for destino in ('ACT-0001','ACT-0003'):
            self.assertEqual(client.post('/accesorios/ACT-0002/asignacion',
                data={'id_maquinaria':destino}).status_code,302)
            self.assertEqual(self.scalar("SELECT id_maquinaria FROM asignaciones_accesorios WHERE estado='ACTIVA'"),destino)
        self.assertEqual(client.post('/accesorios/ACT-0002/asignacion/liberar').status_code,302)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM asignaciones_accesorios WHERE estado='ACTIVA'"),0)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM asignaciones_accesorios'),2)

    def test_busqueda_por_campos_y_disponibilidad(self):
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE maquinarias SET descripcion='Boquilla fina', marca='Acme', modelo='MX90', numero_serie='FAB123', serie_interna='SN-0002' WHERE id_activo='ACT-0002'"))
        for q in ('ACT-0', 'Boquilla', 'Acme', 'MX90', 'FAB123', 'SN-0002'):
            self.assertEqual([r['id'] for r in self.servicio.buscar_accesorios_asignables(q)], ['ACT-0002'])
        for q in ('', 'A', 'noexiste', "' OR 1=1 --"):
            self.assertEqual(self.servicio.buscar_accesorios_asignables(q), [])
        for cambio in ("estado='BAJA'", "estado='ACTIVO',es_contenedor=1"):
            with self.engine.begin() as conn:
                conn.execute(text('UPDATE maquinarias SET '+cambio+" WHERE id_activo='ACT-0002'"))
            self.assertEqual(self.servicio.buscar_accesorios_asignables('ACT-'), [])
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE maquinarias SET es_contenedor=0 WHERE id_activo='ACT-0002'"))
        self.db.asignar_accesorio_maquinaria('ACT-0002','ACT-0001','Ana')
        self.assertEqual(self.servicio.buscar_accesorios_asignables('ACT-'), [])

    def test_ruta_busqueda_y_formulario_conectado(self):
        app = self.app()
        client = app.test_client()
        url = '/accesorios/disponibles-maquinaria?q=ACT-0'
        self.assertEqual(client.get(url).status_code, 401)
        for rol in ('Visualizador','Mantenimiento','Administrador'):
            with client.session_transaction() as s: s.update(nombre='Ana',rol=rol)
            r = client.get(url)
            self.assertEqual(r.status_code, 403 if rol=='Visualizador' else 200)
            if rol != 'Visualizador': self.assertEqual(r.json[0]['id'], 'ACT-0002')
        with app.test_request_context():
            session['rol']='Mantenimiento'
            for origen in ('web','qr'):
                html = render_template('partials/agregar_accesorio_maquinaria.html',
                    equipo={'id_activo':'ACT-0001','estado':'ACTIVO'},origen_accesorio=origen)
                self.assertIn('data-buscar-contenido="/accesorios/disponibles-maquinaria"',html)
                self.assertIn('data-contenido-busqueda',html)
                self.assertIn('data-contenido-resultados',html)
                self.assertIn('data-contenido-id',html)


if __name__ == '__main__': unittest.main()
