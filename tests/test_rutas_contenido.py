import unittest

from flask import Flask

from routes.contenido import registrar_rutas_contenido


def permitir_acceso(func):
    return func


def permitir_roles(*roles):
    return permitir_acceso


class RutasContenidoTest(unittest.TestCase):
    def test_conserva_las_siete_rutas(self):
        app = Flask(__name__)
        registrar_rutas_contenido(
            app,
            permitir_acceso,
            permitir_roles,
            lambda **kwargs: None,
        )
        rutas = {
            (regla.rule, regla.endpoint)
            for regla in app.url_map.iter_rules()
        }
        esperadas = {
            ("/buscar-activos", "buscar_activos_ajax"),
            (
                "/maquinarias/<id_activo>/revision-contenido/reabrir",
                "reabrir_revision_contenido_route",
            ),
            (
                "/maquinarias/<id_activo>/revision-contenido/iniciar",
                "iniciar_revision_contenido_route",
            ),
            (
                "/maquinarias/<id_activo>/revision-contenido/finalizar",
                "finalizar_revision_contenido_route",
            ),
            (
                "/maquinarias/<id_activo>/contenido/vincular",
                "vincular_contenido_route",
            ),
            (
                "/maquinarias/<id_activo>/contenido/<int:relacion_id>/retirar",
                "retirar_contenido_route",
            ),
            (
                "/maquinarias/<id_activo>/contenido/registrar",
                "registrar_accesorio_desde_contenido",
            ),
        }
        self.assertTrue(esperadas.issubset(rutas))


if __name__ == "__main__":
    unittest.main()
