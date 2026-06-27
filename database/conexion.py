from sqlalchemy import create_engine
import os

USUARIO = os.getenv("MYSQLUSER")
PASSWORD = os.getenv("MYSQLPASSWORD")
HOST = os.getenv("MYSQLHOST")
PUERTO = os.getenv("MYSQLPORT")
BASE_DATOS = os.getenv("MYSQLDATABASE")

engine = create_engine(
    f"mysql+pymysql://{USUARIO}:{PASSWORD}@{HOST}:{PUERTO}/{BASE_DATOS}",
    pool_pre_ping=True,
    pool_recycle=3600
)