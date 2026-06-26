from sqlalchemy import create_engine

USUARIO = "root"
PASSWORD = "Jose2003."
HOST = "localhost"
PUERTO = "3306"
BASE_DATOS = "vital_health"

engine = create_engine(

    f"mysql+pymysql://{USUARIO}:{PASSWORD}@{HOST}:{PUERTO}/{BASE_DATOS}",

    pool_pre_ping=True,

    pool_recycle=3600,

    echo=False

)