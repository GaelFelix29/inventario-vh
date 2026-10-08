import unittest
from unittest.mock import patch

from database import mantenimiento


class ResultadoFalso:
    def __init__(self, fila=None):
        self.fila = fila

    def mappings(self):
        return self

    def first(self):
        return self.fila


class ConexionFalsa:
    def __init__(self):
        self.parametros_actualizacion = None

    def execute(self, sentencia, parametros=None):
        sql = str(sentencia)
        if "FROM mantenimiento_ejecuciones me" in sql:
            return ResultadoFalso({
                "id": 8,
                "mantenimiento_id": 786,
                "estado": "BORRADOR",
                "semana": 41,
                "anio": 2026,
                "id_activo": "ACT-0240",
            })
        if "UPDATE mantenimiento_ejecuciones SET" in sql:
            self.parametros_actualizacion = parametros
        return ResultadoFalso()


class TransaccionFalsa:
    def __init__(self, conexion):
        self.conexion = conexion

    def __enter__(self):
        return self.conexion

    def __exit__(self, tipo, valor, traceback):
        return False


class MotorFalso:
    def __init__(self):
        self.conexion = ConexionFalsa()

    def begin(self):
        return TransaccionFalsa(self.conexion)


class GuardadoFormatoMantenimientoTest(unittest.TestCase):
    def setUp(self):
        self.motor = MotorFalso()
        self.datos = {
            "fecha_realizacion": "2026-10-08",
            "procedimiento": "CONVENCIONAL,KOSHER",
            "respuestas": {"uno": "REALIZADO", "dos": "CAMBIO"},
            "materiales": ["Herramienta"],
            "observaciones": "Prueba",
            "firma_tecnico": "data:image/png;base64,tecnico",
            "firma_supervisor": "data:image/png;base64,supervisor",
            "claves": ["uno", "dos"],
        }

    def guardar(self, datos, finalizar):
        with patch.object(mantenimiento, "engine", self.motor), patch.object(
            mantenimiento, "registrar_movimiento"
        ):
            return mantenimiento.guardar_formato_digital(
                8, datos, "Gabriel", finalizar, "TC-1"
            )

    def test_finaliza_con_procedimientos_multiples(self):
        self.guardar(self.datos, True)
        parametros = self.motor.conexion.parametros_actualizacion
        self.assertEqual(parametros["procedimiento"], "CONVENCIONAL,KOSHER")
        self.assertEqual(parametros["estado"], "COMPLETO")

    def test_intento_incompleto_conserva_borrador(self):
        datos = dict(self.datos, firma_supervisor="")
        with self.assertRaisesRegex(ValueError, "guardadas como borrador"):
            self.guardar(datos, True)
        parametros = self.motor.conexion.parametros_actualizacion
        self.assertEqual(parametros["estado"], "BORRADOR")
        self.assertIn('"uno": "REALIZADO"', parametros["respuestas"])


if __name__ == "__main__":
    unittest.main()
