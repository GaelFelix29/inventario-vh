import unittest

from flask import Flask

from routes.inicio import registrar_rutas_inicio


def permitir_acceso(func):
    return func


class RutasInicioTest(unittest.TestCase):
    def test_conserva_inicio_y_diagnostico(self):
        app = Flask(__name__)
        registrar_rutas_inicio(app, permitir_acceso, lambda: False)
        rutas = {(regla.rule, regla.endpoint) for regla in app.url_map.iter_rules()}
        self.assertIn(("/", "inicio"), rutas)
        self.assertIn(("/prueba", "prueba"), rutas)


if __name__ == "__main__":
    unittest.main()
