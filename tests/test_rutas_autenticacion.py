import unittest

from flask import Flask

from routes.autenticacion import registrar_rutas_autenticacion


def permitir_acceso(func):
    return func


class RutasAutenticacionTest(unittest.TestCase):
    def test_conserva_rutas_y_verificacion_global(self):
        app = Flask(__name__)
        registrar_rutas_autenticacion(
            app,
            permitir_acceso,
            lambda **kwargs: None,
            lambda destino: False,
        )
        rutas = {(regla.rule, regla.endpoint) for regla in app.url_map.iter_rules()}
        self.assertIn(("/login", "login"), rutas)
        self.assertIn(("/logout", "logout"), rutas)
        self.assertIn(
            (
                "/cambiar-password-obligatorio",
                "cambiar_password_obligatorio",
            ),
            rutas,
        )
        self.assertIn(
            "verificar_cambio_password_obligatorio",
            [funcion.__name__ for funcion in app.before_request_funcs[None]],
        )


if __name__ == "__main__":
    unittest.main()
