import unittest

from flask import Flask

from routes.solicitudes import registrar_rutas_solicitudes


def permitir_acceso(func):
    return func


class RutasSolicitudesTest(unittest.TestCase):
    def test_conserva_ruta_de_creacion(self):
        app = Flask(__name__)
        registrar_rutas_solicitudes(
            app,
            permitir_acceso,
            lambda **kwargs: None,
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
                "/maquinarias/<id_activo>/solicitud-baja",
                "solicitud_baja",
                ("POST",),
            ),
            rutas,
        )


if __name__ == "__main__":
    unittest.main()
