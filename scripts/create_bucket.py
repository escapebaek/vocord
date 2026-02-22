"""
Supabase Storage 버킷 생성 스크립트
실행 전 환경변수 설정:
  set SUPABASE_URL=https://YOUR_PROJECT.supabase.co
  set SUPABASE_KEY=YOUR_SECRET_KEY
"""
import os
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    exit(1)

from supabase import create_client
client = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    result = client.storage.create_bucket('profiles', options={'public': True})
    print('OK - bucket created')
except Exception as e:
    msg = str(e)
    if 'already exists' in msg.lower() or 'Duplicate' in msg or '23505' in msg:
        print('INFO - bucket already exists (OK)')
    else:
        print('ERROR:', msg[:200])

try:
    buckets = client.storage.list_buckets()
    print('Buckets:', [b.name for b in buckets])
except Exception as e:
    print('List failed:', str(e)[:100])
