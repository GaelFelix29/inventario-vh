import unittest

from flask import Flask

from routes.maquinaria import registrar_rutas_maquinaria


def permitir_acceso(func):
    return func


def permitir_roles(*roles):
    return permitir_acceso


class RutasMaquinariaTest(unittest.TestCase):
    def test_conserva_listado_y_alta(self):
        app = Flask(__name__)
        registrar_rutas_maquinaria(
            app,
            permitir_acceso,
            permitir_roles,
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

        self.assertIn(
            ("/maquinarias", "lista_maquinarias", ("GET",)),
            rutas,
        )
        self.assertIn(
            (
                "/maquinarias/<id_activo>",
                "expediente_maquinaria",
                ("GET",),
            ),
            rutas,
        )
        self.assertIn(
            (
                "/maquinarias/<id_activo>/imprimir",
                "imprimir_maquinaria",
                ("GET",),
            ),
            rutas,
        )
        self.assertIn(
            (
                "/maquinarias/<id_activo>/qr",
                "qr_maquinaria",
                ("GET",),
            ),
            rutas,
        )
        self.assertIn(
            (
                "/maquinarias/<id_activo>/editar",
                "editar_maquinaria",
                ("GET", "POST"),
            ),
            rutas,
        )
        self.assertIn(
            (
                "/maquinarias/nuevo",
                "nueva_maquinaria",
                ("GET", "POST"),
            ),
            rutas,
        )
        self.assertIn(
            ("/<id_activo>", "redireccion_qr_antiguo", ("GET",)),
            rutas,
        )
        self.assertIn(
            (
                "/maquina/<id_activo>",
                "redireccion_qr_maquina",
                ("GET",),
            ),
            rutas,
        )
        self.assertIn(
            ("/qr/<id_activo>", "maquinaria_qr", ("GET",)),
            rutas,
        )
        self.assertIn(
            (
                "/qr/<id_activo>/contenido",
                "qr_contenido",
                ("GET",),
            ),
            rutas,
        )
        self.assertIn(
            (
                "/qr/<id_activo>/expediente",
                "qr_expediente",
                ("GET",),
            ),
            rutas,
        )


if __name__ == "__main__":
    unittest.main()
