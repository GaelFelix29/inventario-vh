import unittest

from flask import Flask

from routes.aduanas import registrar_rutas_aduanas


def permitir_acceso(func):
    return func


class RutasAduanasTest(unittest.TestCase):
    def test_conserva_urls_metodos_y_endpoints(self):
        app = Flask(__name__)
        registrar_rutas_aduanas(
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
            ("/aduanas", "lista_aduanas", ("GET",)),
            (
                "/aduanas/<id_activo>/editar",
                "editar_aduana",
                ("GET", "POST"),
            ),
            ("/aduanas/nuevo", "nueva_aduana", ("GET", "POST")),
            ("/aduanas/datos/<id_activo>", "datos_aduana", ("GET",)),
            ("/m/aduanas", "aduanas_mobile", ("GET",)),
            ("/m/aduanas/api", "api_aduanas_mobile", ("GET",)),
            (
                "/m/aduanas/origenes",
                "api_origenes_mobile",
                ("GET",),
            ),
        }
        self.assertTrue(esperadas.issubset(rutas))


if __name__ == "__main__":
    unittest.main()
