import unittest

from flask import Flask

from routes.respaldos import registrar_rutas_respaldos


def permitir_acceso(func):
    return func


class RutasRespaldosTest(unittest.TestCase):
    def test_conserva_urls_metodos_y_endpoints(self):
        app = Flask(__name__)
        registrar_rutas_respaldos(
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
            ("/respaldos", "vista_respaldos", ("GET",)),
            ("/respaldos/crear", "crear_respaldo_ajax", ("POST",)),
            (
                "/respaldos/descargar/<nombre>",
                "descargar_respaldo",
                ("GET",),
            ),
            (
                "/respaldos/eliminar/<nombre>",
                "eliminar_respaldo",
                ("POST",),
            ),
        }
        self.assertTrue(esperadas.issubset(rutas))


if __name__ == "__main__":
    unittest.main()
