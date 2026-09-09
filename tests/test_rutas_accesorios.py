import unittest

from flask import Flask

from routes.accesorios import registrar_rutas_accesorios


def permitir_acceso(func):
    return func


class RutasAccesoriosTest(unittest.TestCase):
    def test_conserva_rutas_y_endpoints(self):
        app = Flask(__name__)
        registrar_rutas_accesorios(app, permitir_acceso)
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
                "/accesorios/<id_accesorio>/categoria",
                "actualizar_categoria_accesorio_route",
                ("POST",),
            ),
            (
                "/accesorios/<id_accesorio>/asignacion",
                "asignar_accesorio_maquinaria_route",
                ("POST",),
            ),
            (
                "/accesorios/<id_accesorio>/asignacion/liberar",
                "liberar_accesorio_maquinaria_route",
                ("POST",),
            ),
            (
                "/buscar-maquinarias-asignables",
                "buscar_maquinarias_asignables_ajax",
                ("GET",),
            ),
            (
                "/accesorios/<id_accesorio>/categoria/crear",
                "crear_categoria_accesorio_route",
                ("POST",),
            ),
        }
        self.assertTrue(esperadas.issubset(rutas))


if __name__ == "__main__":
    unittest.main()
