import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("URL:", SUPABASE_URL)
print("KEY empieza con:", SUPABASE_KEY[:15] if SUPABASE_KEY else None)
print("KEY longitud:", len(SUPABASE_KEY) if SUPABASE_KEY else 0)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)