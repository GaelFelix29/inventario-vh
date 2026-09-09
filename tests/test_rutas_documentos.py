import unittest

from flask import Flask

from routes.documentos import registrar_rutas_documentos


def permitir_acceso(func):
    return func


class RutasDocumentosTest(unittest.TestCase):
    def test_conserva_urls_metodos_y_endpoints(self):
        app = Flask(__name__)
        registrar_rutas_documentos(
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
            (
                "/maquinarias/<id_activo>/documentos",
                "subir_documento",
                ("POST",),
            ),
            (
                "/documentos/<int:id_documento>/eliminar",
                "borrar_documento",
                ("POST",),
            ),
            (
                "/qr/<id_activo>/documento/<tipo>",
                "qr_documento",
                ("GET",),
            ),
        }
        self.assertTrue(esperadas.issubset(rutas))


if __name__ == "__main__":
    unittest.main()
