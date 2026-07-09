import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("=" * 50)
print("URL:", repr(SUPABASE_URL))
print("KEY:", repr(SUPABASE_KEY))
print("LONGITUD:", len(SUPABASE_KEY) if SUPABASE_KEY else 0)
print("=" * 50)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)