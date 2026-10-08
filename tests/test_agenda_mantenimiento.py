import unittest

from services.agenda_mantenimiento import preparar_agenda


class AgendaMantenimientoTests(unittest.TestCase):
    def setUp(self):
        self.agenda = [
            {"semana": 1, "estado": "PROGRAMADO", "estado_ejecucion": None},
            {"semana": 2, "estado": "PROGRAMADO", "estado_ejecucion": "BORRADOR"},
            {"semana": 3, "estado": "PROGRAMADO", "estado_ejecucion": "COMPLETO"},
            {"semana": 4, "estado": "NO_REALIZADO", "estado_ejecucion": None},
            {"semana": 5, "estado": "REPROGRAMADO", "estado_ejecucion": None},
        ]

    def test_prioriza_el_estado_de_la_ejecucion_digital(self):
        resultado = preparar_agenda(self.agenda, por_pagina=8)
        estados = [item["estado_vista"] for item in resultado["items"]]
        self.assertEqual(
            estados,
            ["PROGRAMADO", "EN_PROCESO", "REALIZADO", "NO_REALIZADO", "REPROGRAMADO"],
        )

    def test_filtra_por_semana_y_estado(self):
        por_semana = preparar_agenda(self.agenda, semana=4)
        self.assertEqual([item["semana"] for item in por_semana["items"]], [4])

        por_estado = preparar_agenda(self.agenda, estado="REALIZADO")
        self.assertEqual([item["semana"] for item in por_estado["items"]], [3])

    def test_pagina_y_limita_resultados(self):
        agenda = [
            {"semana": semana, "estado": "PROGRAMADO", "estado_ejecucion": None}
            for semana in range(1, 21)
        ]
        resultado = preparar_agenda(agenda, pagina=2, por_pagina=8)
        self.assertEqual(resultado["paginas"], 3)
        self.assertEqual([item["semana"] for item in resultado["items"]], list(range(9, 17)))

    def test_normaliza_filtros_y_pagina_fuera_de_rango(self):
        resultado = preparar_agenda(self.agenda, semana=80, estado="INVALIDO", pagina=99, por_pagina=99)
        self.assertIsNone(resultado["semana"])
        self.assertEqual(resultado["estado"], "")
        self.assertEqual(resultado["por_pagina"], 8)
        self.assertEqual(resultado["pagina"], 1)


if __name__ == "__main__":
    unittest.main()
