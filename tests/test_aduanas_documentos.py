import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, text

import database.aduanas as modulo_aduanas


class DocumentosAduanasTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE aduanas (
                    id_activo TEXT PRIMARY KEY,
                    factura TEXT,
                    pedimento TEXT,
                    origen TEXT,
                    fecha_importacion TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE documentos_maquinaria (
                    id INTEGER PRIMARY KEY,
                    id_activo TEXT,
                    nombre_archivo TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE maquinarias (
                    id_activo TEXT PRIMARY KEY,
                    descripcion TEXT,
                    estado TEXT
                )
            """))
            conn.execute(
                text("""
                    INSERT INTO aduanas
                        (id_activo, factura, pedimento, origen, fecha_importacion)
                    VALUES
                        ('ACT-0312', 'A1 600099', '6011786', 'CHINA', '2026-09-25'),
                        ('ACT-0313', 'A1 600099', '6011786', 'CHINA', '2026-09-25')
                """)
            )
            conn.execute(text("""
                INSERT INTO maquinarias (id_activo, descripcion, estado)
                VALUES
                    ('ACT-0312', 'Equipo con documentos', 'ACTIVO'),
                    ('ACT-0313', 'Equipo sin documentos', 'ACTIVO')
            """))
            conn.execute(text("""
                INSERT INTO documentos_maquinaria
                    (id, id_activo, nombre_archivo)
                VALUES
                    (630, 'ACT-0312', 'factura.pdf'),
                    (631, 'ACT-0312', 'pedimento.pdf'),
                    (632, 'ACT-0312', 'packing-list.pdf')
            """))

    def tearDown(self):
        self.engine.dispose()

    def test_lista_escritorio_cuenta_documentos_del_expediente(self):
        with patch.object(modulo_aduanas, "engine", self.engine):
            registros = modulo_aduanas.obtener_aduanas().set_index("id_activo")

        self.assertEqual(int(registros.loc["ACT-0312", "total_documentos"]), 3)
        self.assertEqual(int(registros.loc["ACT-0313", "total_documentos"]), 0)

    def test_api_mobile_incluye_el_mismo_total(self):
        with patch.object(modulo_aduanas, "engine", self.engine):
            registros = modulo_aduanas.obtener_aduanas_mobile_filtrado(
                limite=20,
                offset=0,
            ).set_index("id_activo")

        self.assertEqual(int(registros.loc["ACT-0312", "total_documentos"]), 3)
        self.assertEqual(int(registros.loc["ACT-0313", "total_documentos"]), 0)


if __name__ == "__main__":
    unittest.main()
