import unittest
from datetime import date
from services.estado_aduanal import estado_expediente_aduanal


class EstadoAduanalTest(unittest.TestCase):
    def test_nacional_completo_sin_datos_importacion(self):
        resultado = estado_expediente_aduanal(
            {"origen": " nacional ", "factura": "F-100", "documentacion_completa": "Sí"})
        self.assertEqual((resultado["porcentaje"], resultado["total"]), (100, 3))
        self.assertEqual(resultado["faltantes"], [])
        self.assertTrue(resultado["nacional"])

    def test_conserva_factura_no_aplica(self):
        for factura in ("NA", "N/A", "No aplica"):
            with self.subTest(factura=factura):
                resultado = estado_expediente_aduanal(
                    {"origen": "NACIONAL", "factura": factura, "documentacion_completa": "SI"})
                self.assertEqual(resultado["estado"], "Completo")

    def test_nacional_no_completo_por_solo_tener_origen(self):
        resultado = estado_expediente_aduanal(
            {"origen": "NACIONAL", "factura": "PENDIENTE", "documentacion_completa": "NO"})
        self.assertEqual(resultado["porcentaje"], 33)
        self.assertEqual(resultado["faltantes"], ["Factura", "Documentación Completa"])

    def test_importado_y_fecha_espanola(self):
        datos = dict(factura="F1", pedimento="P1", entrada_mtz="E1", id_imp="I1",
                     inbond="B1", origen="CHINA", fecha_importacion=date(2026, 9, 15),
                     kg_bruto=10, total_bultos=2, documentacion_completa="SI")
        resultado = estado_expediente_aduanal(datos)
        self.assertEqual((resultado["porcentaje"], resultado["total"]), (100, 10))
        fecha = next(c for c in resultado["campos"] if c["clave"] == "fecha_importacion")
        self.assertEqual(fecha["valor"], "15/09/2026")
        datos.update(inbond="pendiente", origen="PENDIENTE", kg_bruto=-1, total_bultos=0,
                     fecha_importacion="2026-02-30")
        resultado = estado_expediente_aduanal(datos)
        self.assertEqual(resultado["pendientes"], 5)
        self.assertEqual(resultado["porcentaje"], 50)

    def test_expediente_existente_vacio_no_es_inexistente(self):
        self.assertEqual(estado_expediente_aduanal(None)["estado"], "Sin expediente")
        self.assertEqual(estado_expediente_aduanal({"origen": None})["estado"], "Incompleto")

    def test_porcentaje_y_lista_siempre_coinciden(self):
        for datos in (None, {"origen": "NACIONAL"}, {"origen": "CHINA"}):
            resultado = estado_expediente_aduanal(datos)
            self.assertEqual(resultado["pendientes"], len(resultado["faltantes"]))
            self.assertEqual(resultado["completos"] + resultado["pendientes"], resultado["total"])
            self.assertEqual(sum(c["completo"] for c in resultado["campos"]), resultado["completos"])


if __name__ == "__main__":
    unittest.main()

