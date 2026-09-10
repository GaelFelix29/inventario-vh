import unittest

from flask import Flask

from routes.perfil import registrar_rutas_perfil


def permitir_acceso(func):
    return func


class RutasPerfilTest(unittest.TestCase):
    def test_conserva_rutas_y_metodos(self):
        app = Flask(__name__)
        registrar_rutas_perfil(
            app,
            permitir_acceso,
            lambda **kwargs: None,
            lambda: False,
        )
        rutas = {
            (
                regla.rule,
                regla.endpoint,
                tuple(sorted(regla.methods - {"HEAD", "OPTIONS"})),
            )
            for regla in app.url_map.iter_rules()
        }
        self.assertIn(("/perfil", "perfil", ("GET",)), rutas)
        self.assertIn(
            ("/perfil/editar", "editar_perfil", ("GET", "POST")),
            rutas,
        )


if __name__ == "__main__":
    unittest.main()
