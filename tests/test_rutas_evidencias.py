import unittest

from flask import Flask

from routes.evidencias import registrar_rutas_evidencias


def permitir_acceso(func):
    return func


class RutasEvidenciasTest(unittest.TestCase):
    def test_conserva_urls_metodos_y_endpoints(self):
        app = Flask(__name__)
        registrar_rutas_evidencias(
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
        esperadas = {
            ("/qr/<id_activo>/evidencias", "qr_evidencias", ("GET",)),
            ("/qr/<id_activo>/evidencias", "subir_evidencia", ("POST",)),
            (
                "/evidencias/<int:id>/eliminar",
                "eliminar_evidencia",
                ("GET",),
            ),
        }
        self.assertTrue(esperadas.issubset(rutas))


if __name__ == "__main__":
    unittest.main()
