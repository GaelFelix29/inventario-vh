import unittest
from pathlib import Path

from services.proteccion_historial_mantenimiento import (
    mantenimiento_protegido,
    validar_cambio_mantenimiento,
)


ROOT = Path(__file__).resolve().parent.parent


class ProteccionHistorialMantenimientoTests(unittest.TestCase):
    def test_permite_quitar_una_semana_sin_historial(self):
        registro = {
            "estado": "PROGRAMADO",
            "tiene_ejecucion": False,
            "tiene_documentos": False,
        }
        self.assertFalse(mantenimiento_protegido(registro))
        validar_cambio_mantenimiento(registro, None)

    def test_bloquea_borrado_con_formulario_documento_o_realizado(self):
        casos = (
            {"estado": "PROGRAMADO", "tiene_ejecucion": True, "tiene_documentos": False},
            {"estado": "PROGRAMADO", "tiene_ejecucion": False, "tiene_documentos": True},
            {"estado": "REALIZADO", "tiene_ejecucion": False, "tiene_documentos": False},
        )
        for registro in casos:
            with self.subTest(registro=registro):
                self.assertTrue(mantenimiento_protegido(registro))
                with self.assertRaisesRegex(ValueError, "historial quedó protegido"):
                    validar_cambio_mantenimiento(registro, None)

    def test_bloquea_cambio_de_estado_pero_permite_conservarlo(self):
        registro = {
            "estado": "REALIZADO",
            "tiene_ejecucion": True,
            "tiene_documentos": True,
        }
        validar_cambio_mantenimiento(registro, "REALIZADO")
        with self.assertRaisesRegex(ValueError, "historial de mantenimiento"):
            validar_cambio_mantenimiento(registro, "PROGRAMADO")

    def test_interfaz_y_esquema_tienen_doble_proteccion(self):
        plantilla = (ROOT / "templates" / "mantenimiento" / "index.html").read_text(
            encoding="utf-8"
        )
        migracion = (ROOT / "migrar_mantenimiento_preventivo.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("data-protegido", plantilla)
        self.assertIn("Historial protegido", plantilla)
        self.assertIn("Quitar del plan", plantilla)
        self.assertGreaterEqual(migracion.count("ON DELETE RESTRICT"), 2)


if __name__ == "__main__":
    unittest.main()
