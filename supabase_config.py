import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("URL:", repr(SUPABASE_URL))
print("KEY:", repr(SUPABASE_KEY))

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)