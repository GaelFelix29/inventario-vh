from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

USUARIO = os.getenv("MYSQLUSER")
PASSWORD = os.getenv("MYSQLPASSWORD")
HOST = os.getenv("MYSQLHOST")
PUERTO = os.getenv("MYSQLPORT")
BASE_DATOS = os.getenv("MYSQLDATABASE")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSL_CERT = os.path.join(BASE_DIR, "ca.pem")

engine = create_engine(
    f"mysql+pymysql://{USUARIO}:{PASSWORD}@{HOST}:{PUERTO}/{BASE_DATOS}",
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "ssl": {
            "ca": SSL_CERT
        }
    }
)