import pandas as pd
from sqlalchemy import create_engine

print("ESTOY EJECUTANDO ESTE SCRIPT")

# ==========================================
# CONFIGURACIÓN
# ==========================================

USUARIO = "root"
PASSWORD = "Jose2003."
HOST = "localhost"
PUERTO = "3306"
BASE_DATOS = "vital_health"

import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ARCHIVO_EXCEL = os.path.join(
    BASE_DIR,
    "INVENTARIO-MAQUINAS_GAEL Conteo.xlsx"
)
# ==========================================
# CONEXIÓN MYSQL
# ==========================================

engine = create_engine(
    f"mysql+pymysql://{USUARIO}:{PASSWORD}@{HOST}:{PUERTO}/{BASE_DATOS}"
)

# ==========================================
# LEER EXCEL
# ==========================================



# df = pd.read_excel(
#     ARCHIVO_EXCEL,
#     sheet_name="MAQUINARIAS",
#     header=6,
#     engine="openpyxl"
# )

# print(df.shape)
# print(df.tail(20))
# print(df.iloc[:,0].tail(30))
print("Archivo que estoy leyendo:")
print(ARCHIVO_EXCEL)

df = pd.read_excel(
    ARCHIVO_EXCEL,
    sheet_name="MAQUINARIAS",
    header=6,
    engine="openpyxl",
    keep_default_na=False
)

print("Filas:", len(df))
print(df.iloc[-20:])
# ==========================================
# LIMPIAR COLUMNAS
# ==========================================

df.columns = df.columns.str.strip()

# Eliminar columnas vacías
df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

print(df.columns.tolist())
print(df.head(15))

# ==========================================
# RENOMBRAR COLUMNAS
# ==========================================

df = df.rename(columns={

    "ID ACTIVO":"id_activo",
    "Categoría":"categoria",
    "Descripción":"descripcion",
    "Cantidad":"cantidad",
    "Marca":"marca",
    "Modelo":"modelo",
    "Numero de Serie":"numero_serie",
    "Proveedor":"proveedor",
    "Fecha Alta":"fecha_alta",
    "Estado":"estado",
    "Ultima actualización":"ultima_actualizacion",
    "Precio Unitario US":"precio_unitario_us",
    "Total US":"total_us",
    "Valor MX":"valor_mx",
    "Observaciones":"observaciones",
    "Fecha Baja":"fecha_baja",
    "Motivo Baja":"motivo_baja",
    "Ubicación Final":"ubicacion",
    "Responsable Baja":"responsable_baja",
    "Serie Interna":"serie_interna"

})

print(df.columns.tolist())
print(df[["id_activo"]].head(10))

# ==========================================
# AGREGAR COLUMNA SI NO EXISTE
# ==========================================

if "ultima_actualizacion" not in df.columns:
    df["ultima_actualizacion"] = None

# ==========================================
# FECHAS
# ==========================================

df["fecha_alta"] = pd.to_datetime(df["fecha_alta"], dayfirst=True, errors="coerce")
df["fecha_baja"] = pd.to_datetime(df["fecha_baja"], dayfirst=True, errors="coerce")
df["ultima_actualizacion"] = pd.to_datetime(
    df["ultima_actualizacion"],
    dayfirst=True,
    errors="coerce"
)

# ==========================================
# NUMÉRICOS
# ==========================================

for columna in [
    "cantidad",
    "precio_unitario_us",
    "total_us",
    "valor_mx"
]:
    df[columna] = (
        df[columna]
        .astype(str)
        .str.replace("$","",regex=False)
        .str.replace(",","",regex=False)
        .str.strip()
    )

    df[columna] = pd.to_numeric(
        df[columna],
        errors="coerce"
    )

# ==========================================
# REEMPLAZAR VACÍOS POR NULL
# ==========================================

df = df.where(pd.notnull(df), None)

# ==========================================
# SOLO COLUMNAS DE LA BD
# ==========================================

df = df[[
    "id_activo",
    "categoria",
    "descripcion",
    "cantidad",
    "marca",
    "modelo",
    "numero_serie",
    "serie_interna",
    "proveedor",
    "fecha_alta",
    "estado",
    "ubicacion",
    "ultima_actualizacion",
    "precio_unitario_us",
    "total_us",
    "valor_mx",
    "observaciones",
    "fecha_baja",
    "motivo_baja",
    "responsable_baja"
]]

# ==========================================
# ELIMINAR FILAS SIN ID
# ==========================================

df = df[df["id_activo"].notna()]
df = df[df["id_activo"] != ""]

# ==========================================
# ELIMINAR ESPACIOS
# ==========================================

df["id_activo"] = df["id_activo"].astype(str).str.strip()

# ==========================================
# BUSCAR DUPLICADOS
# ==========================================

duplicados = df[df["id_activo"].duplicated(keep=False)]

if not duplicados.empty:
    print("\n===== IDS DUPLICADOS =====")
    print(duplicados[["id_activo"]])
    print("==========================\n")

# ==========================================
# ELIMINAR DUPLICADOS
# ==========================================

df = df.drop_duplicates(subset=["id_activo"], keep="first")

print("Registros:", len(df))
print("IDs únicos:", df["id_activo"].nunique())

print("Total de filas:", len(df))
print("IDs únicos:", df["id_activo"].nunique())

duplicados = df[df.duplicated(subset=["id_activo"], keep=False)]

print("\nDUPLICADOS:")
print(duplicados[["id_activo"]])

df = df.drop_duplicates(subset=["id_activo"], keep="first")

print("\nDespués de eliminar duplicados:")
print("Filas:", len(df))
print("IDs únicos:", df["id_activo"].nunique())

# ==========================================
# INSERTAR
# ==========================================

print("ANTES DEL INSERT")
print(df.head())
print(df.tail())
print("Filas:", len(df))
print("Duplicados:", df["id_activo"].duplicated().sum())

df.to_sql(
    "maquinarias",
    con=engine,
    if_exists="append",
    index=False
)

print("==============================")
print("IMPORTACIÓN TERMINADA")
print("Registros:", len(df))
print("==============================")