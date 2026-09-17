"""Pruebas aisladas: nunca cargan credenciales ni conectan a MySQL real.

SQLite verifica transacciones/reglas; los bloqueos FOR UPDATE requieren una
prueba adicional de integración en MySQL de pruebas antes del despliegue.
"""
import importlib
from functools import wraps
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

from flask import Flask, abort, render_template, session
from sqlalchemy import create_engine, event, text
from flask_wtf.csrf import CSRFProtect

ROOT = Path(__file__).resolve().parents[1]


class ConjuntosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        conexion = types.ModuleType('database.conexion')
        conexion.engine = None
        anterior = sys.modules.get('database.conexion')
        sys.modules['database.conexion'] = conexion
        try:
            cls.servicio = importlib.import_module('services.contenido_activos')
            cls.db = importlib.import_module('database.maquinarias')
            cls.rutas = importlib.import_module('routes.contenido')
        finally:
            if anterior is not None:
                sys.modules['database.conexion'] = anterior
            else:
                # Keep a disconnected module; no production credentials in tests.
                sys.modules['database.conexion'] = conexion

    def setUp(self):
        self.engine = create_engine('sqlite://')
        @event.listens_for(self.engine, 'before_cursor_execute', retval=True)
        def sql_compatible(conn, cursor, statement, parameters, context, executemany):
            return statement.replace(' FOR UPDATE', '').replace('NOW()', 'CURRENT_TIMESTAMP'), parameters
        self.patches = [patch.object(self.servicio, 'engine', self.engine),
                        patch.object(self.db, 'engine', self.engine)]
        for p in self.patches:
            p.start()
        with self.engine.begin() as conn:
            for sql in [
                '''CREATE TABLE maquinarias (id_activo TEXT PRIMARY KEY, categoria TEXT,
                    categoria_accesorio_id INTEGER, descripcion TEXT, cantidad INTEGER,
                    marca TEXT, modelo TEXT, numero_serie TEXT, serie_interna TEXT UNIQUE,
                    proveedor TEXT, ubicacion TEXT, fecha_alta TEXT, precio_unitario_us REAL,
                    total_us REAL, valor_mx REAL, observaciones TEXT,
                    es_contenedor INTEGER DEFAULT 0, estado TEXT DEFAULT 'ACTIVO',
                    estado_revision_contenido TEXT, fecha_revision_contenido TEXT, revisado_por TEXT)''',
                '''CREATE TABLE categorias_accesorios(id INTEGER PRIMARY KEY, codigo TEXT,
                    nombre TEXT, activo INTEGER)''',
                '''CREATE TABLE relaciones_activos(id INTEGER PRIMARY KEY, activo_origen TEXT,
                    activo_relacionado TEXT, tipo_relacion TEXT, estado TEXT, observaciones TEXT,
                    creado_por TEXT, fecha_inicio TEXT DEFAULT CURRENT_TIMESTAMP, fecha_fin TEXT)''',
                '''CREATE TABLE asignaciones_accesorios(id INTEGER PRIMARY KEY,
                    id_accesorio TEXT, id_maquinaria TEXT, estado TEXT,
                    fecha_asignacion TEXT, asignado_por TEXT)''',
                '''CREATE TABLE auditoria(id INTEGER PRIMARY KEY, usuario TEXT, accion TEXT,
                    modulo TEXT, referencia TEXT)''',
                "INSERT INTO categorias_accesorios VALUES(1,'POR_CLASIFICAR','Por clasificar',1)",
                "INSERT INTO maquinarias(id_activo,categoria,descripcion,ubicacion,es_contenedor,estado_revision_contenido,valor_mx) VALUES('ACT-0020','ACCESORIOS','Caja','AMAPOLAS',1,'EN_REVISION',9000)",
                "INSERT INTO maquinarias(id_activo,categoria,descripcion,ubicacion) VALUES('ACT-0021','ACCESORIOS','Pieza','AMAPOLAS')",
                "INSERT INTO maquinarias(id_activo,categoria,descripcion,es_contenedor,estado_revision_contenido) VALUES('ACT-0022','ACCESORIOS','Otra caja',1,'EN_REVISION')",
            ]:
                conn.execute(text(sql))

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.engine.dispose()

    def scalar(self, sql):
        with self.engine.connect() as conn:
            return conn.execute(text(sql)).scalar()

    def runsql(self, sql):
        with self.engine.begin() as conn:
            conn.execute(text(sql))

    def test_creacion_atomica_id_serie_ubicacion_y_valor(self):
        nuevo = self.servicio.registrar_accesorio_contenido('ACT-0020', {'descripcion':'Boquilla'}, 'Ana')
        self.assertEqual(nuevo, 'ACT-0023')
        self.assertEqual(self.scalar("SELECT serie_interna FROM maquinarias WHERE id_activo='ACT-0023'"), 'SN-0023')
        self.assertEqual(self.scalar("SELECT ubicacion FROM maquinarias WHERE id_activo='ACT-0023'"), 'AMAPOLAS')
        self.assertEqual(self.scalar("SELECT valor_mx FROM maquinarias WHERE id_activo='ACT-0020'"), 9000)
        self.assertEqual(self.scalar("SELECT valor_mx FROM maquinarias WHERE id_activo='ACT-0023'"), 0)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM relaciones_activos'), 1)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM auditoria'), 3)

    def test_fallo_vinculo_revierte_registro(self):
        with patch.object(self.servicio, 'vincular_en_transaccion', side_effect=RuntimeError('fallo')):
            with self.assertRaises(RuntimeError):
                self.servicio.registrar_accesorio_contenido('ACT-0020', {'descripcion':'Pieza'}, 'Ana')
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM maquinarias'), 3)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM relaciones_activos'), 0)

    def test_fallo_auditoria_revierte_todo(self):
        with patch.object(self.servicio, 'registrar_movimiento', side_effect=RuntimeError('fallo')):
            with self.assertRaises(RuntimeError):
                self.servicio.registrar_accesorio_contenido('ACT-0020', {'descripcion':'Pieza'}, 'Ana')
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM maquinarias'), 3)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM relaciones_activos'), 0)

    def test_validacion_descripcion(self):
        for datos in ({'descripcion':'  '}, {'descripcion':'x'*256}):
            with self.assertRaises(ValueError):
                self.servicio.registrar_accesorio_contenido('ACT-0020', datos, 'Ana')
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM maquinarias'), 3)

    def test_no_crear_sin_revision(self):
        self.runsql("UPDATE maquinarias SET estado_revision_contenido='VERIFICADO' WHERE id_activo='ACT-0020'")
        with self.assertRaises(ValueError):
            self.servicio.registrar_accesorio_contenido('ACT-0020', {'descripcion':'Pieza'}, 'Ana')

    def test_vinculo_duplicado_y_dos_contenedores(self):
        self.db.vincular_contenido_activo('ACT-0020','ACT-0021','Ana')
        for padre in ('ACT-0020','ACT-0022'):
            with self.assertRaises(ValueError):
                self.db.vincular_contenido_activo(padre,'ACT-0021','Ana')
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM relaciones_activos'),1)

    def test_busqueda_excluye_cajas_y_piezas_ya_vinculadas(self):
        self.assertEqual([a['id'] for a in self.servicio.buscar_accesorios_disponibles('ACT-')], ['ACT-0021'])
        self.db.vincular_contenido_activo('ACT-0020','ACT-0021','Ana')
        self.assertEqual(self.servicio.buscar_accesorios_disponibles('ACT-'), [])

    def test_retiro_no_permite_otro_conjunto(self):
        self.db.vincular_contenido_activo('ACT-0020','ACT-0021','Ana')
        with self.assertRaises(ValueError):
            self.db.retirar_contenido_activo('ACT-0022',1,'Ana')
        self.assertEqual(self.scalar('SELECT estado FROM relaciones_activos WHERE id=1'),'ACTIVA')

    def test_no_auto_vinculo_ni_cajas_anidadas(self):
        for hijo in ('ACT-0020','ACT-0022','ACT-9999'):
            with self.assertRaises(ValueError):
                self.db.vincular_contenido_activo('ACT-0020',hijo,'Ana')

    def test_no_maquinaria_ni_accesorio_baja(self):
        for cambio in ("categoria='LLENADORA'", "categoria='ACCESORIO',estado='BAJA'"):
            self.runsql(f"UPDATE maquinarias SET {cambio} WHERE id_activo='ACT-0021'")
            with self.assertRaises(ValueError):
                self.db.vincular_contenido_activo('ACT-0020','ACT-0021','Ana')

    def test_retiro_preserva_registro_e_historial(self):
        self.db.vincular_contenido_activo('ACT-0020','ACT-0021','Ana')
        self.db.retirar_contenido_activo('ACT-0020',1,'Luis')
        self.assertEqual(self.scalar("SELECT estado FROM relaciones_activos WHERE id=1"),'INACTIVA')
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM maquinarias'),3)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM auditoria WHERE referencia='ACT-0021'"),2)
        with self.assertRaises(ValueError):
            self.db.retirar_contenido_activo('ACT-0020',1,'Luis')
        self.db.vincular_contenido_activo('ACT-0022','ACT-0021','Ana')
        contexto = self.servicio.contexto_contenido('ACT-0021')
        self.assertEqual(contexto['conjunto_padre']['activo_origen'],'ACT-0022')

    def test_conversion_conserva_categoria_y_no_crea_piezas(self):
        self.servicio.convertir_en_conjunto('ACT-0021','Ana')
        self.assertEqual(self.scalar("SELECT categoria FROM maquinarias WHERE id_activo='ACT-0021'"),'ACCESORIOS')
        self.assertEqual(self.scalar("SELECT estado_revision_contenido FROM maquinarias WHERE id_activo='ACT-0021'"),'PENDIENTE')
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM maquinarias'),3)

    def test_conversion_rechaza_asignado_o_contenido(self):
        self.runsql("INSERT INTO asignaciones_accesorios VALUES(1,'ACT-0021','ACT-0090','ACTIVA',NULL,'Ana')")
        with self.assertRaises(ValueError):
            self.servicio.convertir_en_conjunto('ACT-0021','Ana')
        self.runsql("UPDATE asignaciones_accesorios SET estado='INACTIVA'")
        self.db.vincular_contenido_activo('ACT-0020','ACT-0021','Ana')
        with self.assertRaises(ValueError):
            self.servicio.convertir_en_conjunto('ACT-0021','Ana')

    def test_ciclo_revision(self):
        self.runsql("UPDATE maquinarias SET estado_revision_contenido='PENDIENTE' WHERE id_activo='ACT-0020'")
        self.db.iniciar_revision_contenido('ACT-0020','Ana')
        self.db.finalizar_revision_contenido('ACT-0020','Ana')
        self.assertEqual(self.scalar("SELECT estado_revision_contenido FROM maquinarias WHERE id_activo='ACT-0020'"),'VERIFICADO')
        self.db.reabrir_revision_contenido('ACT-0020','Luis')
        self.assertEqual(self.scalar("SELECT estado_revision_contenido FROM maquinarias WHERE id_activo='ACT-0020'"),'EN_REVISION')

    def app(self):
        app = Flask(__name__, template_folder=str(ROOT/'templates'), static_folder=str(ROOT/'static'))
        app.secret_key='solo-pruebas'
        def login(f):
            @wraps(f)
            def wrap(*a,**kw):
                if not session.get('nombre'): abort(401)
                return f(*a,**kw)
            return wrap
        def roles(*allowed):
            def decorator(f):
                @wraps(f)
                def wrap(*a,**kw):
                    if session.get('rol') not in allowed: abort(403)
                    return f(*a,**kw)
                return wrap
            return decorator
        self.rutas.registrar_rutas_contenido(app,login,roles,lambda **kw:None)
        for endpoint in ('expediente_maquinaria','maquinaria_qr','qr_contenido'):
            app.add_url_rule('/'+endpoint+'/<id_activo>',endpoint,lambda id_activo:'OK')
        return app

    def test_rutas_permisos_y_csrf(self):
        app=self.app()
        client=app.test_client()
        path='/maquinarias/ACT-0020/contenido/registrar'
        self.assertEqual(client.post(path).status_code,401)
        with client.session_transaction() as ses:
            ses['nombre']='Ana'; ses['rol']='Visualizador'
        self.assertEqual(client.post(path).status_code,403)
        with client.session_transaction() as ses: ses['rol']='Mantenimiento'
        with patch.object(self.rutas, 'registrar_accesorio_contenido') as crear:
            self.assertEqual(client.post(path,data={'descripcion':'No crear'}).status_code,403)
            crear.assert_not_called()
        with patch.object(self.rutas, 'convertir_en_conjunto') as convertir:
            self.assertEqual(client.post('/maquinarias/ACT-0021/contenido/configurar').status_code,403)
            convertir.assert_not_called()
        with client.session_transaction() as ses: ses['rol']='Administrador'
        app_csrf=self.app()
        CSRFProtect(app_csrf)
        self.assertEqual(app_csrf.test_client().post(path,data={'descripcion':'Pieza'}).status_code,400)

    def test_plantillas_todos_los_estados_y_roles(self):
        app=self.app()
        app.jinja_env.globals['csrf_token']=lambda:'token-de-prueba'
        for archivo in ('expediente_maquinaria.html','maquinaria_qr/contenido.html','maquinaria_qr/inicio.html'):
            app.jinja_env.get_template(archivo)
        with app.test_request_context('/'):
            for rol in ('Administrador','Mantenimiento','Visualizador'):
                session['rol']=rol
                for estado in ('PENDIENTE','EN_REVISION','VERIFICADO'):
                    caja=dict(id_activo='ACT-0020',ubicacion='AMAPOLAS',estado_revision_contenido=estado)
                    html=render_template('partials/conjunto_accesorios.html',caja=caja,
                        origen_contenido='web',contenido_activo=[],historial_contenido=[])
                    self.assertIn('Contenido del conjunto',html)
                    if rol=='Visualizador': self.assertNotIn('<form',html)
                    self.assertEqual('Registrar accesorio nuevo' in html,
                                     rol == 'Administrador' and estado == 'EN_REVISION')
                    self.assertEqual('Vincular accesorio existente' in html,
                                     rol != 'Visualizador' and estado == 'EN_REVISION')
                    if estado=='PENDIENTE': self.assertIn('no significa que la caja esté vacía',html)


if __name__=='__main__':
    unittest.main()
