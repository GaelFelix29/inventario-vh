import unittest

from flask import Flask

from routes.movimientos_mobile import registrar_rutas_movimientos_mobile


def permitir_acceso(func):
    return func


def permitir_roles(*roles):
    return permitir_acceso


class RutasMovimientosMobileTest(unittest.TestCase):
    def test_conserva_rutas_y_endpoints(self):
        app = Flask(__name__)
        registrar_rutas_movimientos_mobile(
            app,
            permitir_acceso,
            permitir_roles,
        )

        rutas = {
            (
                regla.rule,
                regla.endpoint,
                tuple(sorted(regla.methods - {"HEAD", "OPTIONS"})),
            )
            for regla in app.url_map.iter_rules()
        }

        self.assertIn(
            (
                "/m/maquinarias/<id_activo>/movimiento/<tipo>",
                "formulario_movimiento_mobile",
                ("GET",),
            ),
            rutas,
        )
        self.assertIn(
            (
                "/m/maquinarias/<id_activo>/movimientos",
                "movimientos_mobile",
                ("GET",),
            ),
            rutas,
        )
        self.assertIn(
            (
                "/m/maquinarias/<id_activo>/actividad",
                "actividad_mobile",
                ("GET",),
            ),
            rutas,
        )


if __name__ == "__main__":
    unittest.main()
