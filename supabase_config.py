import os

from supabase_config import supabase

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

print("================================")
print("SUPABASE CONECTADO")
print("URL:", SUPABASE_URL)
print("================================")