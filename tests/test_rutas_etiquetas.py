import unittest

from flask import Flask

from routes.etiquetas import registrar_rutas_etiquetas


def permitir_acceso(func):
    return func


class RutasEtiquetasTest(unittest.TestCase):
    def test_conserva_urls_metodos_y_endpoints(self):
        app = Flask(__name__)
        registrar_rutas_etiquetas(app, permitir_acceso)

        rutas = {
            (
                regla.rule,
                regla.endpoint,
                tuple(sorted(regla.methods - {"HEAD", "OPTIONS"})),
            )
            for regla in app.url_map.iter_rules()
        }

        esperadas = {
            ("/imprimir", "imprimir_qr", ("GET",)),
            ("/etiquetas", "etiquetas", ("POST",)),
            ("/fichas", "fichas", ("POST",)),
        }
        self.assertTrue(esperadas.issubset(rutas))


if __name__ == "__main__":
    unittest.main()
