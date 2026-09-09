import unittest

from flask import Flask

from routes.actividad import registrar_rutas_actividad


def permitir_acceso(func):
    return func


class RutasActividadTest(unittest.TestCase):
    def test_conserva_urls_y_endpoints_publicos(self):
        app = Flask(__name__)
        registrar_rutas_actividad(app, permitir_acceso)

        rutas = {
            (regla.rule, regla.endpoint)
            for regla in app.url_map.iter_rules()
        }

        self.assertIn(("/actividad", "actividad_sistema"), rutas)
        self.assertIn(
            ("/m/actividad", "actividad_sistema_mobile"),
            rutas,
        )


if __name__ == "__main__":
    unittest.main()
