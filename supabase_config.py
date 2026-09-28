from supabase import create_client
from dotenv import load_dotenv
import os

# Cargar variables del archivo .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# Cliente exclusivo del servidor para archivos financieros privados.
# La service role nunca debe enviarse al navegador ni guardarse en Git.
supabase_finanzas = (
    create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    if SUPABASE_SERVICE_ROLE_KEY
    else None
)

# Cliente privado general para operaciones del servidor que deben saltar las
# políticas públicas, como eliminar archivos físicos de Storage.
supabase_privado = supabase_finanzas
