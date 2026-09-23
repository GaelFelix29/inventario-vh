import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MensajesTest(unittest.TestCase):
    def test_archivos_python_tienen_sintaxis_valida(self):
        for ruta in (
            "database/mensajes.py",
            "routes/mensajes.py",
            "migrar_mensajes.py",
            "app.py",
        ):
            ast.parse((ROOT / ruta).read_text(encoding="utf-8"), ruta)

    def test_migracion_crea_tablas_relaciones_e_indices(self):
        contenido = (ROOT / "migrar_mensajes.py").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS conversaciones", contenido)
        self.assertIn("CREATE TABLE IF NOT EXISTS mensajes", contenido)
        self.assertIn("UNIQUE KEY uq_conversacion_usuarios", contenido)
        self.assertIn("KEY ix_mensajes_conversacion", contenido)
        self.assertIn("ON DELETE CASCADE", contenido)

    def test_consultas_limiten_resultados_y_validen_participante(self):
        contenido = (ROOT / "database/mensajes.py").read_text(encoding="utf-8")
        self.assertIn("LIMITE_CONVERSACIONES = 30", contenido)
        self.assertIn("LIMITE_MENSAJES = 50", contenido)
        self.assertGreaterEqual(contenido.count("OR :usuario_id = c.usuario_dos_id"), 2)
        self.assertIn("OR :remitente_id = usuario_dos_id", contenido)
        self.assertIn("len(contenido) > 2000", contenido)

    def test_rutas_requieren_login_y_formularios_csrf(self):
        rutas = (ROOT / "routes/mensajes.py").read_text(encoding="utf-8")
        self.assertEqual(rutas.count("@login_required"), 6)

        plantilla = (ROOT / "templates/mensajes.html").read_text(encoding="utf-8")
        self.assertEqual(plantilla.count('name="csrf_token"'), 2)
        self.assertIn('maxlength="2000"', plantilla)
        self.assertIn("window.setInterval(actualizar, 4000)", plantilla)
        self.assertIn("if (consultando || document.hidden) return", plantilla)
        self.assertIn("X-CSRFToken", plantilla)

    def test_menu_y_registro_de_rutas_estan_integrados(self):
        base = (ROOT / "templates/base.html").read_text(encoding="utf-8")
        self.assertEqual(base.count("url_for('mensajes')"), 2)
        self.assertIn("mensajes_no_leidos", base)

        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("registrar_rutas_mensajes(app, login_required)", app)
        self.assertIn("def contexto_mensajes", app)


if __name__ == "__main__":
    unittest.main()
