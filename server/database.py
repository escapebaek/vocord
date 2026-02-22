import os
import sqlalchemy
from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime, ForeignKey, func
import databases

# ──────────────────────────────────────────────────────────────────────────────
# DATABASE URL 설정
#   - 환경변수 DATABASE_URL 이 있으면 PostgreSQL (Supabase 등)
#   - 없으면 로컬 SQLite
# ──────────────────────────────────────────────────────────────────────────────
_raw_url = os.getenv("DATABASE_URL", "sqlite:///./vocord.db")

# Supabase / Heroku 등은 "postgres://" 로 주는 경우가 있어서 변환
if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql://", 1)

# databases 라이브러리용 URL
#   PostgreSQL → asyncpg 드라이버로 변환
if _raw_url.startswith("postgresql://") or _raw_url.startswith("postgresql+"):
    # asyncpg 드라이버 명시
    _db_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1) \
        if "postgresql+asyncpg" not in _raw_url else _raw_url
    IS_POSTGRES = True
else:
    _db_url = _raw_url     # sqlite:///./vocord.db
    IS_POSTGRES = False

DATABASE_URL = _db_url

# databases.Database 객체 (비동기 쿼리용)
database = databases.Database(DATABASE_URL)

# sqlalchemy MetaData (테이블 스키마 정의용)
metadata = sqlalchemy.MetaData()

# ──────────────────────────────────────────────────────────────────────────────
# 테이블 정의
# ──────────────────────────────────────────────────────────────────────────────

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(50), unique=True, index=True),
    Column("password_hash", String(255)),
    Column("is_online", Boolean, default=False),
    Column("profile_image", String(500), nullable=True),   # 프로필 이미지 경로
    Column("user_status", String(20), default="online"),    # online / away
    Column("created_at", DateTime, default=func.now())
)

friends = Table(
    "friends",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("friend_id", Integer, ForeignKey("users.id")),
    Column("status", String(20), default="pending")
)

rooms = Table(
    "rooms",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100)),
    Column("created_by", Integer, ForeignKey("users.id")),
    Column("created_at", DateTime, default=func.now())
)

room_members = Table(
    "room_members",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("room_id", Integer, ForeignKey("rooms.id")),
    Column("user_id", Integer, ForeignKey("users.id"))
)

# ──────────────────────────────────────────────────────────────────────────────
# 테이블 생성 (syncronous engine으로 DDL 실행)
# ──────────────────────────────────────────────────────────────────────────────
if IS_POSTGRES:
    # PostgreSQL: psycopg2 (sync) 드라이버로 DDL 실행
    _sync_url = _raw_url  # postgresql://...
    engine = sqlalchemy.create_engine(_sync_url)
else:
    engine = sqlalchemy.create_engine(_raw_url)

metadata.create_all(engine)

# ──────────────────────────────────────────────────────────────────────────────
# SQLite 전용 마이그레이션 (새 컬럼 추가)
# ──────────────────────────────────────────────────────────────────────────────
if not IS_POSTGRES:
    import sqlite3

    def migrate_db():
        conn = sqlite3.connect("vocord.db")
        cursor = conn.cursor()
        for col_def in [
            "ALTER TABLE users ADD COLUMN profile_image TEXT",
            "ALTER TABLE users ADD COLUMN user_status TEXT DEFAULT 'online'",
        ]:
            try:
                cursor.execute(col_def)
            except sqlite3.OperationalError:
                pass  # 이미 존재하면 무시
        conn.commit()
        conn.close()

    migrate_db()