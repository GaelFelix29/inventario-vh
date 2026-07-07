import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

USUARIO = os.getenv("MYSQLUSER")
PASSWORD = os.getenv("MYSQLPASSWORD")
HOST = os.getenv("MYSQLHOST")
PUERTO = os.getenv("MYSQLPORT")
BASE = os.getenv("MYSQLDATABASE")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SSL_CERT = os.path.join(BASE_DIR, "ca.pem")

BACKUPS = os.path.join(BASE_DIR, "backups")
os.makedirs(BACKUPS, exist_ok=True)


def crear_respaldo():

    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    archivo = os.path.join(
        BACKUPS,
        f"vitalhealth_{fecha}.sql"
    )

    comando = [

        "mysqldump",

        f"--host={HOST}",
        f"--port={PUERTO}",
        f"--user={USUARIO}",
        f"--password={PASSWORD}",
        f"--ssl-ca={SSL_CERT}",

        "--single-transaction",
        "--routines",
        "--events",
        "--triggers",

        BASE

    ]

    try:

        with open(archivo, "w", encoding="utf-8") as salida:

            subprocess.run(

                comando,

                stdout=salida,

                stderr=subprocess.PIPE,

                text=True,

                check=True

            )

        print("="*50)
        print("✅ RESPALDO CREADO CORRECTAMENTE")
        print("="*50)
        print(archivo)

        return archivo

    except Exception as e:

        print("=" * 50)
        print("ERROR")
        print("=" * 50)
        print(repr(e))

    raise


if __name__ == "__main__":

    crear_respaldo()