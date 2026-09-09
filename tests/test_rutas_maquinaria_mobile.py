import unittest

from flask import Flask

from routes.maquinaria_mobile import registrar_rutas_maquinaria_mobile


def permitir_acceso(func):
    return func


class RutasMaquinariaMobileTest(unittest.TestCase):
    def test_conserva_rutas_y_endpoints(self):
        app = Flask(__name__)
        registrar_rutas_maquinaria_mobile(app, permitir_acceso)

        rutas = {
            (
                regla.rule,
                regla.endpoint,
                tuple(sorted(regla.methods - {"HEAD", "OPTIONS"})),
            )
            for regla in app.url_map.iter_rules()
        }

        esperadas = {
            (
                "/m/maquinarias/cargar",
                "cargar_maquinarias_mobile",
                ("GET",),
            ),
            ("/m/maquinarias", "maquinarias_mobile", ("GET",)),
            (
                "/m/maquinarias/api",
                "api_maquinarias_mobile",
                ("GET",),
            ),
            (
                "/m/maquinarias/ubicaciones",
                "api_ubicaciones_mobile",
                ("GET",),
            ),
            ("/m/recientes", "api_activos_recientes", ("GET",)),
        }

        self.assertTrue(esperadas.issubset(rutas))


if __name__ == "__main__":
    unittest.main()
