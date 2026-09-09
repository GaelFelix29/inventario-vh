import unittest

from flask import Flask

from routes.usuarios import registrar_rutas_usuarios


def permitir_acceso(func):
    return func


class RutasUsuariosTest(unittest.TestCase):
    def test_conserva_urls_y_endpoints_publicos(self):
        app = Flask(__name__)
        registrar_rutas_usuarios(app, permitir_acceso, lambda **kwargs: None)

        rutas = {
            (regla.rule, regla.endpoint, tuple(sorted(regla.methods - {"HEAD", "OPTIONS"})))
            for regla in app.url_map.iter_rules()
        }

        esperadas = {
            ("/usuarios", "usuarios", ("GET",)),
            ("/m/usuarios", "usuarios_mobile", ("GET",)),
            ("/usuarios/nuevo", "nuevo_usuario", ("GET", "POST")),
            ("/m/usuarios/nuevo", "nuevo_usuario_mobile", ("GET", "POST")),
            ("/usuarios/editar/<int:id>", "editar_usuario", ("GET", "POST")),
            ("/usuarios/<int:id>/restablecer-password", "restablecer_password_usuario", ("POST",)),
            ("/usuarios/desactivar/<int:id>", "desactivar", ("GET",)),
            ("/usuarios/reactivar/<int:id>", "reactivar_usuario_route", ("GET",)),
        }

        self.assertTrue(esperadas.issubset(rutas))


if __name__ == "__main__":
    unittest.main()
