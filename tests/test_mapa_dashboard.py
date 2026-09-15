import unittest

from services.mapa_dashboard import normalizar_ubicacion, resumir_mapa


class MapaDashboardTest(unittest.TestCase):
    def test_agrupa_variantes_de_una_ubicacion(self):
        resultado = resumir_mapa(
            [
                {"ubicacion": " Amapolas ", "estado": "ACTIVO"},
                {"ubicacion": "AMÁPOLAS", "estado": "BAJA"},
            ],
            {"AMAPOLAS": {"lat": 19.4, "lng": -99.1}},
        )
        self.assertEqual(resultado["total"], 2)
        self.assertEqual(resultado["localizadas"], 1)
        self.assertEqual(resultado["ubicaciones"][0]["activos"], 1)
        self.assertEqual(resultado["ubicaciones"][0]["bajas"], 1)

    def test_no_inventa_coordenadas_para_nombres_ambiguos(self):
        resultado = resumir_mapa(
            [{"ubicacion": "Naranjo", "estado": "ACTIVO"}], {}
        )
        self.assertIsNone(resultado["ubicaciones"][0]["coordenadas"])
        self.assertEqual(resultado["sin_localizar"], 1)

    def test_descarta_coordenadas_invalidas(self):
        resultado = resumir_mapa(
            [{"ubicacion": "Campeche", "estado": "ACTIVO"}],
            {"Campeche": {"lat": 150, "lng": -90}},
        )
        self.assertEqual(resultado["localizadas"], 0)

    def test_normaliza_vacios(self):
        self.assertEqual(normalizar_ubicacion(None), "SIN UBICACION")
        self.assertEqual(normalizar_ubicacion("  "), "SIN UBICACION")


if __name__ == "__main__":
    unittest.main()
