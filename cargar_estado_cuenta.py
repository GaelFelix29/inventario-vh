import argparse
from pathlib import Path

from database.estados_cuenta import importar_estado_cuenta
from services.importador_estados_cuenta import leer_estado_cuenta


parser = argparse.ArgumentParser(description="Carga un estado de cuenta Banregio conciliado.")
parser.add_argument("archivo", type=Path)
parser.add_argument("--usuario-id", type=int, required=True, help="Usuario Finanzas responsable")
argumentos = parser.parse_args()
with argumentos.archivo.open("rb") as archivo:
    estado = leer_estado_cuenta(archivo, argumentos.archivo.name)
estado_id = importar_estado_cuenta(estado, argumentos.usuario_id)
print(f"Estado {estado_id} importado: {len(estado['movimientos'])} movimientos.")
