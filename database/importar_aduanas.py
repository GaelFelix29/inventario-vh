import pandas as pd
from sqlalchemy import create_engine
import os

# ==========================================
# MYSQL
# ==========================================

USUARIO = "root"
PASSWORD = "Jose2003."
HOST = "localhost"
PUERTO = "3306"
BASE_DATOS = "vital_health"

engine = create_engine(
    f"mysql+pymysql://{USUARIO}:{PASSWORD}@{HOST}:{PUERTO}/{BASE_DATOS}"
)

# ==========================================
# EXCEL
# ==========================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ARCHIVO_EXCEL = os.path.join(
    BASE_DIR,
    "INVENTARIO-MAQUINAS_GAEL Conteo.xlsx"
)

df = pd.read_excel(
    ARCHIVO_EXCEL,
    sheet_name="ADUANA",
    header=6,
    engine="openpyxl",
    keep_default_na=False
)

# ==========================================
# LIMPIAR
# ==========================================

df.columns = df.columns.str.strip()
df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

# ==========================================
# RENOMBRAR
# ==========================================

df = df.rename(columns={

    "ID Activo": "id_activo",
    "Entrada MTZ": "entrada_mtz",
    "Factura": "factura",
    "ID IMP": "id_imp",
    "Pedimento": "pedimento",
    "Inbond": "inbond",
    "Origen": "origen",
    "Fechad de importacion": "fecha_importacion",
    "Fecha de importación": "fecha_importacion",
    "Documentación Completa": "documentacion_completa",
    "KG Bruto": "kg_bruto",
    "Total Bultos": "total_bultos"

})

# ==========================================
# FECHAS
# ==========================================

df["fecha_importacion"] = pd.to_datetime(
    df["fecha_importacion"],
    errors="coerce"
)

# ==========================================
# NUMERICOS
# ==========================================

df["kg_bruto"] = pd.to_numeric(
    df["kg_bruto"],
    errors="coerce"
)

df["total_bultos"] = pd.to_numeric(
    df["total_bultos"],
    errors="coerce"
)

# ==========================================
# NULL
# ==========================================

df = df.where(pd.notnull(df), None)

# ==========================================
# SOLO COLUMNAS BD
# ==========================================

df = df[[
    "id_activo",
    "entrada_mtz",
    "factura",
    "id_imp",
    "pedimento",
    "inbond",
    "origen",
    "fecha_importacion",
    "documentacion_completa",
    "kg_bruto",
    "total_bultos"
]]

# ==========================================
# INSERTAR
# ==========================================

df.to_sql(
    "aduanas",
    con=engine,
    if_exists="append",
    index=False
)

print("==========================")
print("IMPORTACIÓN TERMINADA")
print("Registros:", len(df))
print("==========================")