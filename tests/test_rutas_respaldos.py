import unittest
from unittest.mock import patch

from flask import Flask
from werkzeug.security import generate_password_hash

from routes.respaldos import (
    SESION_ACCESO,
    SESION_BLOQUEO,
    registrar_rutas_respaldos,
)


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
            ("/respaldos/acceso", "acceso_respaldos", ("GET", "POST")),
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

    def crear_app(self):
        app = Flask(__name__, template_folder="../templates")
        app.config.update(TESTING=True, SECRET_KEY="pruebas", WTF_CSRF_ENABLED=False)
        self.movimientos = []
        registrar_rutas_respaldos(
            app,
            permitir_acceso,
            lambda **kwargs: self.movimientos.append(kwargs),
        )
        return app

    @staticmethod
    def autenticar_administrador(cliente):
        with cliente.session_transaction() as sesion:
            sesion["rol"] = "Administrador"
            sesion["nombre"] = "Gabriel"

    def test_solicita_segunda_clave_antes_de_mostrar_respaldos(self):
        app = self.crear_app()
        cliente = app.test_client()
        self.autenticar_administrador(cliente)

        respuesta = cliente.get("/respaldos")

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.location.endswith("/respaldos/acceso"))

        respuesta_ajax = cliente.post("/respaldos/crear")
        self.assertEqual(respuesta_ajax.status_code, 403)
        self.assertFalse(respuesta_ajax.get_json()["ok"])

    def test_clave_correcta_autoriza_temporalmente(self):
        app = self.crear_app()
        cliente = app.test_client()
        self.autenticar_administrador(cliente)
        clave_hash = generate_password_hash("Clave-de-prueba-2026")

        with patch.dict("os.environ", {"RESPALDOS_PASSWORD_HASH": clave_hash}):
            respuesta = cliente.post(
                "/respaldos/acceso",
                data={"password": "Clave-de-prueba-2026"},
            )

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.location.endswith("/respaldos"))
        with cliente.session_transaction() as sesion:
            self.assertIn(SESION_ACCESO, sesion)
        self.assertEqual(
            self.movimientos[-1]["accion"],
            "Autorizó acceso protegido a respaldos",
        )

    def test_bloquea_despues_de_cinco_intentos_incorrectos(self):
        app = self.crear_app()
        cliente = app.test_client()
        self.autenticar_administrador(cliente)
        clave_hash = generate_password_hash("Clave-de-prueba-2026")

        with (
            patch.dict("os.environ", {"RESPALDOS_PASSWORD_HASH": clave_hash}),
            patch("routes.respaldos.render_template", return_value="acceso protegido"),
        ):
            for _ in range(5):
                cliente.post(
                    "/respaldos/acceso",
                    data={"password": "incorrecta"},
                )

        with cliente.session_transaction() as sesion:
            self.assertIn(SESION_BLOQUEO, sesion)
            self.assertNotIn(SESION_ACCESO, sesion)


if __name__ == "__main__":
    unittest.main()
