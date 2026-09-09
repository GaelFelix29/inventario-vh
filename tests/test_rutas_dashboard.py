import unittest

from flask import Flask

from routes.dashboard import registrar_rutas_dashboard


def permitir_acceso(func):
    return func


class RutasDashboardTest(unittest.TestCase):
    def test_conserva_urls_y_endpoints_publicos(self):
        app = Flask(__name__)
        registrar_rutas_dashboard(app, permitir_acceso)

        rutas = {
            (regla.rule, regla.endpoint)
            for regla in app.url_map.iter_rules()
        }

        self.assertIn(("/dashboard", "dashboard"), rutas)
        self.assertIn(("/dashboard/datos", "dashboard_datos"), rutas)
        self.assertIn(("/m/dashboard", "dashboard_mobil"), rutas)


if __name__ == "__main__":
    unittest.main()
