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

        esperadas = {
            ("/solicitudes-baja", "lista_solicitudes_baja", ("GET",)),
            (
                "/solicitudes-baja/<int:id>",
                "ver_solicitud",
                ("GET",),
            ),
            (
                "/solicitudes-baja/<int:id>/aprobar",
                "aprobar_solicitud_route",
                ("POST",),
            ),
            (
                "/solicitudes-baja/<int:id>/rechazar",
                "rechazar_solicitud_route",
                ("POST",),
            ),
        }
        self.assertTrue(esperadas.issubset(rutas))


if __name__ == "__main__":
    unittest.main()
